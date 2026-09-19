# Exit Code Masking by Bash Pipe — Critical Subagent Verification Failure (2026-09-11)

> This is the most expensive session-level mistake I made. It directly caused master HEAD to be broken after merging 14 PRs, requiring emergency PR #197 ("fix post-merge build breaks") to recover. The user paid the cost in rebase friction, lost trust, and ~10 minutes of investigation time. The fix is trivial; the lesson is mandatory.

## The bug

Standard shell pattern:

```bash
cargo check -p euv -p euv-core --target wasm32-unknown-unknown 2>&1 | tail -20
```

The `| tail -20` **swallows the cargo check exit code**. `$?` after this pipeline equals `tail`'s exit code (always 0), not `cargo check`'s exit code (could be 101 on compile failure).

Concrete instance (2026-09-11):

```bash
# I ran this 14+ times across the 14-PR batch:
cargo check -p euv ... | tail -20
echo "exit: $?"  # I thought this echoed cargo's exit code

# Reality: $? = tail's exit code (0)
# Cargo check actually failed with E0425 (cannot find DATA_EUV_SIGNAL_ADDRS) — exit 101
# Subagent reports all "exit 0"; orchestrator trusts; master merges; broken.
```

I caught it only when I ran `cargo check ... > /tmp/c.log 2>&1; echo "exit: $?"` (no pipe) and saw `exit: 101`. By that time 14 PRs were merged into a broken master.

## The fix (always use this form)

```bash
cargo check ... > /tmp/cargo-check.log 2>&1
echo "cargo check exit: $?"   # MUST be 0
cat /tmp/cargo-check.log | tail -20   # pipe is fine AFTER capturing exit
```

Or with `tee` if you want to see output AND capture exit:

```bash
cargo check ... 2>&1 | tee /tmp/cargo-check.log >/dev/null
echo "cargo check exit: $?"
```

Or capture into shell variable:

```bash
EXIT=0
cargo check ... > /tmp/cargo-check.log 2>&1 || EXIT=$?
echo "cargo check exit: $EXIT"
```

## When this bites hardest

1. **Subagents running pre-commit sequences**: every subagent in this session was told to run `cargo check ... 2>&1 | tail -5` for status. None of them could have caught the failure. The "exit: $?" line came AFTER another command (`git status --short`) which masked the problem further.

2. **Sequential batch merges**: when subagents each report "all checks exit 0" but they were using the broken pipe pattern, the orchestrator trusts all reports and proceeds. Master becomes broken at scale.

3. **Cargo's output is verbose**: `cargo check` produces ~50 lines of "Checking ..." output. Subagents naturally pipe to `tail` to see just the end. This is the most common place the bug bites.

## Rule (now mandatory for ALL cargo / rustc / clippy commands)

**Any command that ends with `cargo`, `rustc`, `clippy`, or `wasm-pack` MUST be invoked without a pipe to `tail`/`head`/`grep`/`awk`.** The exit code of these tools is the source of truth for "did it compile?" — and the source of truth is lost the moment a pipe is appended.

Acceptable patterns:
```bash
# Pattern A (preferred — capture then read)
cargo check ... > /tmp/c.log 2>&1; echo "exit: $?"
# Then optionally inspect:
grep -E '^error' /tmp/c.log | head

# Pattern B (tee then capture)
cargo check ... 2>&1 | tee /tmp/c.log >/dev/null; echo "exit: $?"

# Pattern C (variable capture)
cargo check ... > /tmp/c.log 2>&1
EXIT=$?
echo "exit: $EXIT"
```

Unacceptable patterns:
```bash
# BAD — exit code lost
cargo check ... 2>&1 | tail -20

# BAD — exit code lost, output truncated
cargo check ... | grep '^error'

# BAD — subagent may "verify" but `$?` is wrong
cargo check ... 2>&1 | tail -5 && echo "exit: $?"   # $? is tail's, not cargo's
```

## How this skill should be used

When you dispatch a subagent for any Rust work, **explicitly require the unpiped pattern** in the goal:

```text
MANDATORY: All cargo / rustc / clippy / wasm-pack invocations must use:
  cmd < <command> > /tmp/c.log 2>&1; echo "exit: $?"
or:
  cmd < <command> 2>&1 | tee /tmp/c.log >/dev/null; echo "exit: $?"

NEVER pipe to tail/head/grep — those swallow the exit code.
Report ALL exit codes (audit, cargo check wasm, cargo test --no-run,
euv fmt, cargo fmt --all, clippy) explicitly with their actual values
in your final summary. Do not infer "exit 0" from successful output
truncation.
```

When you yourself verify subagent work, **re-run cargo with the unpiped pattern on local** before declaring the batch complete.

## Why this didn't break earlier batches

In earlier sessions (single-PR work, not batches), each PR's `cargo check` was followed by other commands that **did** propagate exit codes (e.g. `cargo test --no-run 2>&1 | tail -5 && git commit`). Git commit would fail if cargo test failed, providing a backstop. **In a batch where the orchestrator doesn't commit between subagent runs, the backstop is gone** — the exit code is the only signal.

## Patch applied

This file is referenced from `rust-wasm-perf-audit/SKILL.md` §"落地优化点时的硬性流程" (rule 2 about cargo check wasm) — the SKILL.md now says cargo invocations must use the unpiped pattern, and points here for the full incident. See git log for the patch commit.

## Related

- `references/post-merge-cross-pr-integration-check.md` (pitfall 6) — the master-broken outcome that this verification bug enabled
- `references/pr-194-scope-leak-from-stale-base.md` (pitfall 5) — same class of "subagent reports green, reality is broken"
- `references/euv-fmt-non-idempotent-block-comments.md` (pitfall 3) — subagent workaround that includes the `git checkout HEAD -- ui/src/style/class/fn.rs` discipline; this rule applies analogously to "report actual exit codes, not inferred"