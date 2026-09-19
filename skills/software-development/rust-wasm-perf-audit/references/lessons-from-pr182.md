# Lessons learned — closing the v0.20.6 audit delta (2026-09-10)

> Operational lessons from PR #178 → #182 work. These are pitfalls that bit during
> execution but were not captured in the original `euv-perf-findings-0.20.6.md` report.

## 1. `#[cfg(test)]` gate for wasm dead-code elimination BREAKS integration tests

**Pattern observed**: When the audit says "remove dead code from wasm" for items only
referenced by `core/tests/<name>.rs`, the obvious first instinct is to add
`#[cfg(test)]` to the items. This **does not work** and the failure mode is subtle.

**Why it fails**: Rust integration tests (`tests/` directory) compile the lib as a
**regular dependency**, not as `cfg(test)`. So:

```rust
// lib.rs
pub fn diff_children(...) -> Vec<DiffOp> { ... }    // audited "dead in wasm"

// tests/keyed.rs
use mycrate::diff_children;                        // ← compilation FAILS after #[cfg(test)] gate
```

`#[cfg(test)]` only takes effect when the lib is compiled with `--test`, which only
happens for `cargo test --lib` / `cargo test --bin`, **not** for `cargo test --test <name>`
which compiles the test file as a separate crate pulling in the lib.

**Fix options, in order of preference**:

1. **Just delete the items + delete the integration tests** if those tests aren't pulling
   their weight (often the case for "dead code" — if the tests were the only consumer,
   the tests may be testing obsolete behavior).
2. **`#[cfg(not(target_arch = "wasm32"))]`** — inverse gate. Compiles for native tests,
   stripped for wasm. Slightly verbose at the call site, but harmless.
3. **Don't gate at all** — rely on wasm-pack's LTO + dead-code-elimination. This works
   **iff** the items are not re-exported through `pub use` chains and are only referenced
   from `core/tests/`. Test visibility is preserved via `pub use r#module::*;` in the
   lib's `pub mod`. PR #182 final approach for `diff_children`/`diff_keyed`/
   `LruCache`: demoted `pub mod` → `mod`, kept `pub use` re-export so tests still
   resolve `crate::vdom::DiffOp` etc., and wasm-pack eliminated the items automatically.

**2026-09-10 PR #182 incident**: I told the subagent "use `#[cfg(test)]` gate" (the
audit report's exact wording). Subagent dutifully gated `DiffOp`, `diff_children`,
`diff_keyed`, `diff_positional`, `LruCache` and its impl. Then `cargo test --no-run`
exploded with 5× `error[E0432]: unresolved import`. Subagent reverted, then had to
rework `mod`/`pub use` to expose items to tests while keeping them absent from
wasm. ~25 minutes wasted on the round-trip. The fix worked, but the lesson is to
pre-validate the recommended fix against the crate's test setup before delegating.

**Delegation principle**: When the audit recommendation says "X technique", do NOT
copy-paste that into the subagent's `goal` as a binding instruction. Instead:

- State the **goal** ("remove these items from the wasm artifact without breaking
  tests")
- State the **constraints** ("lib has integration tests in `core/tests/<name>.rs` that
  exercise these items via `use mycrate::*`")
- Let the subagent pick the technique that satisfies both

This forces the subagent to verify the technique against the actual crate layout
before committing to it.

## 2. Single-PR batch of N low-risk items: SUBMIT, do not self-merge

PR #182 submitted with **11 items in one commit, one PR, CI 5/5 green**. Key
constraints:

- `git diff --stat` must contain ONLY the intended files (no `Cargo.toml`, no
  `example/`, no unrelated files)
- `euv fmt` is macro-aware and WILL reformat comments in files like
  `ui/src/style/class/fn.rs` even when your change is unrelated. After running
  `euv fmt`, check `git status --short`; if unrelated files show up, revert them
  with `git checkout HEAD -- <file>` to keep PR diff scope-clean
- Track 2 default = **wait for maintainer review**, do NOT `gh pr merge --admin`
  even if you're an org admin (per 2026-09-08 user correction on PR #20
  hyperlane-quick-start)

## 3. Verification checklist order matters

After a non-trivial patch, run checks in this order (rust-standards pre-commit):

1. `python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py .`
   — fastest feedback, catches 13 hard-rule violations without compilation
2. `cargo check -p <wasm-entries> --target wasm32-unknown-unknown`
   — confirms macros + types compile for wasm
3. `cargo test --no-run -p <test-entries>`
   — confirms tests compile (the `#[cfg(test)]` integration-test pitfall surfaces here)
4. `euv fmt && cargo fmt --all` (run twice for idempotency check)
5. `cargo clippy --all-targets --offline`
6. THEN commit. THEN push. THEN `gh pr create`.

Skipping step 3 is how the `#[cfg(test)]` integration-test breakage was missed in
PR #182's first attempt.