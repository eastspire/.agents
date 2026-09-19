# Lessons learned — PR-batch delivery 2026-09-10

> Companion to `lessons-from-pr182.md`. Captures the 3-phase audit → batched-PR
> delivery pattern + the shared-checkout sister-agent collision pitfall, both of
> which bit during the v0.21.1 b108fa10 batch (PRs #182-#189, 8 PRs / 26 items).

## 1. The 3-phase fan-out pattern

When a perf audit produces N items, don't try to fix them all in one pass. Use:

**Phase 1: Audit (parallel subagents)**. 4 subagents each audit a slice
(euv: core renderer+noderef / reactive+vdom+app / macros+ui / engine). Output:
a single `euv-perf-findings-X.Y.Z.md` ranked by impact.

**Phase 2: Verification (single subagent)**. Reads the audit report and walks every
numbered finding against **actual master** (not the audit baseline). For each item
produces CLOSED (with closing PR + commit SHA + file:line evidence) or OPEN (with
current file:line + diff-size estimate + risk + blockers). Output: a verification
report like `euv-perf-verification-<short-SHA>.md`.

**Phase 3: Batched PR delivery (serial subagents, one PR each)**. For each tier
(easy wins / mid-pack / heavy), one subagent per PR. Each gets:
- exact `file:line` from the verification report (not the audit report)
- 5 pre-commit checks before commit (audit_rust_standards.py → cargo check wasm →
  cargo test --no-run → euv fmt + cargo fmt idempotent → clippy)
- explicit "DO NOT merge" instruction (Track 2 default = wait for maintainer)
- "report back with actual exit codes" — never accept fabricated status

**Skip Phase 2 and you waste subagent time re-verifying audit claims that were
already closed by earlier PRs (#178/#179)** — every batched PR subagent will then
have to recheck, multiplying wall-clock by N.

**Observed throughput (2026-09-10)**: 8 PRs in ~3.5 hours wall-clock for 26 items,
all 5/5 CI green. Phase 2 was the single biggest time-saver.

## 2. Sister-agent collision on shared checkout

When multiple `delegate_task` subagents work on the **same git checkout** in parallel
(each on its own branch, but pushing/pulling from the same upstream master), they
race on the working tree.

**Incident (PR-H vs PR-B, 2026-09-11 00:49)**: PR-H's subagent (event-walk + bridge)
started ~1 minute after PR-B's (signal-addr). Both touched
`core/src/renderer/render/impl.rs`. PR-H stashed and discarded PR-B's pending
edits; PR-B's commit was pop'd back into its own branch unscratched (each branch
had its own files staged, `git stash pop` recovered cleanly). PR-H landed clean;
PR-B landed separately. **No data lost, but ~3 minutes of wasted stash/discard
work**.

**Mitigations**:
- **Sequence the subagents** (wait for completion before dispatching the next) —
  adds wall-clock but eliminates the race entirely. **Default for PR-batch work**.
- If parallelism is required, run each subagent in a separate worktree
  (`git worktree add ../euv-PR-A perf/branch-A`) — adds setup overhead per subagent.
- Don't dispatch PR-N+1 until PR-N's subagent reports back with PR URL confirmed.

## 3. Per-PR scope discipline with multi-item batches

When batching 10+ low-risk items into one PR (PR-A, 11 items in one commit):

- `git diff --stat` must contain ONLY the intended files (no `Cargo.toml`, no
  `example/`, no unrelated files).
- `euv fmt` is macro-aware and WILL reformat comments in files like
  `ui/src/style/class/fn.rs` even when your change is unrelated. After running
  `euv fmt`, check `git status --short`; if unrelated files show up, revert with
  `git checkout HEAD -- <file>` to keep PR diff scope-clean.
- Track 2 default = **wait for maintainer review**, do NOT `gh pr merge --admin`
  even if you're an org admin.

## 4. Batch-PR subagent goal template

Goal that worked for 8 PRs without re-spec:

```
Execute PR-X: <one-line description>.

**Strict scope: exactly these N items, ONE PR, nothing else.**

# Items
<for each: file:line in master, current state, exact fix, diff size, type, risk>

# Workflow
1. Load skills: rust-standards, rust-wasm-perf-audit, euv-standards [+euv-ui-standards for ui/].
2. cd to repo, switch to clean origin/master:
   git checkout master && git pull --rebase && git fetch origin master
   git checkout -b perf/<branch-name> origin/master
3. Verify each item's current state at master (read_file on file:line).
4. Implement all items.
5. DO NOT: touch Cargo.toml (no version bump), break public API,
   touch files unrelated to N items.
6. Pre-commit:
   python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py .
   cargo check -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example --target wasm32-unknown-unknown
   cargo test --no-run -p euv -p euv-core -p euv-macros
   euv fmt && cargo fmt --all && euv fmt && cargo fmt --all
   cargo clippy -p euv-core -p euv-engine -p euv-macros -p euv-ui --all-targets --offline
7. Commit (single, English):
   <commit message>
8. Verify git diff --stat clean.
9. git push origin <branch-name>
10. gh pr create --repo <upstream> --head eastspire:<branch> --base master
    --title "..." --body-file pr-body.md
11. DO NOT MERGE. Track 2 default.
12. Report:
    - PR URL
    - All 5 pre-commit check exit codes
    - git diff --stat
    - commit hash
    - Any blockers
```