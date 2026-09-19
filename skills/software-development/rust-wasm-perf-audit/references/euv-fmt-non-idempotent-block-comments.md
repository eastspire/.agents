# Bug: `euv fmt` is non-idempotent on macro bodies with block comments containing internal whitespace

> Captured 2026-09-11. Reproducer, root cause, in-flight fix, and workaround for users stuck on the pre-fix `euv-cli`.

## TL;DR

`euv fmt` (the `euv` CLI's `fmt` subcommand) is **not idempotent** on source files containing `class!` / `html!` / `vars!` blocks whose bodies contain `/* ... */` block comments with multi-space internal alignment. Every invocation of `euv fmt` adds **one extra space** to such comment lines (135 → 136 → 137 → 138 → ...), because the formatter's `add_indentation` re-processes the block comment's internal newlines as if they were macro-body newlines, rewriting the comment's leading whitespace to `depth * 4` on every pass.

`euv fmt --check` reports "Needs formatting" even immediately after a fresh `euv fmt` run.

This caused every subagent in the 12-PR perf batch to do `git checkout HEAD -- ui/src/style/class/fn.rs` to keep PR diffs clean — the file's line-3592 area had been drifting between runs.

## Reproduction (independent of euv version)

```bash
mkdir -p /tmp/fmt-repro/src
cat > /tmp/fmt-repro/src/lib.rs << 'EOF'
class! {
    pub c_test {
        /* `width: 100%` instead of `min-width: 140px` so the menu
                                                                                                                                                           matches the dropdown container (and therefore the
                                                                                                                                                           trigger button) width exactly. With only `min-width`,
                                                                                                                                                           a trigger wider than 140px (e.g. the 206px-wide
                                                                                                                                                           nav-column locale switcher button) leaves a large
                                                                                                                                                           empty gap on the left of the menu, since `right: 0`
                                                                                                                                                           anchors only the right edge to the container. With
                                                                                                                                                           `width: 100%`, the menu's left edge lines up with the
                                                                                                                                                           trigger's left edge. The default minimum content width
                                                                                                                                                           is still guaranteed by the inner items' own padding,
                                                                                                                                                           so we keep the rule without an explicit min. */
        color: "red";
    }
}
EOF
cd /tmp/fmt-repro
for i in 1 2 3 4; do
  euv fmt --path . > /dev/null
  md5sum src/lib.rs
done
# 4 different MD5s — bug confirmed
```

Same reproducer on euv's own `master ui/src/style/class/fn.rs` line 3592 (the long dropdown-trigger-width comment). Pre-fix fmt is non-idempotent.

## Root cause location (euv-cli source)

`cli/src/fmt/fn.rs`:

- **`extract_block_comment`** at line 456: extracts `/* ... */` contents verbatim, preserving newlines + the internal whitespace that follows each newline.
- **`format_macro_body_raw`** (line 512) calls `extract_block_comment` and embeds the extracted text into the macro body.
- **`add_indentation`** at line 818: re-scans the formatted body char-by-char.
  - On every `CHAR_NEWLINE` (line 874), it skips all `CHAR_SPACE` / `CHAR_TAB` after the newline (line 877-879).
  - Then pushes `(depth - closing_count).max(0) * 4` spaces (line 890-893).

The bug: when a block comment is **inside** a macro body, the comment's internal `\n` characters reach `add_indentation`'s newline handler. The handler skips the comment's pre-existing alignment whitespace and writes `depth * 4` spaces instead. On subsequent fmt runs, the comment line's whitespace is smaller (or larger, depending on prior depth), so the cycle continues compounding.

A short block comment (`/* hi */`, no internal newlines) does **not** trigger the bug — verified with `euv fmt` running 5× produces same MD5.

## Fix in flight (PR subagent dispatched 2026-09-11)

PR branch: `fix/euv-fmt-non-idempotent-block-comments` (PR under creation when this file was written).

Recommended fix (Option C from the dispatch): in `add_indentation`, treat extracted block comments as **opaque regions** — track `inside_block_comment: bool` state. While inside `/* ... */`, do not trigger the indent recalculation on newlines. Just append the chars verbatim.

Alternative fixes that were considered:
- **Option A**: in `extract_block_comment`, strip leading whitespace from each extracted comment line. Simple but loses intentional alignment that the user wrote for readability.
- **Option B**: in `add_indentation`, recognize `/*...*/` regions and skip them entirely. Similar to Option C but coarser (skips the entire comment region even on a single line, breaking the case where the comment contains `{`/`}` markers).

## Workaround for users stuck on pre-fix `euv-cli`

Until the fix lands:

```bash
# After every euv fmt, revert any noise files
euv fmt
git status --short  # check for noise files
# Common offender: ui/src/style/class/fn.rs (line 3592 area in v0.21.1)
git checkout HEAD -- ui/src/style/class/fn.rs
```

CI pipelines that run `euv fmt` then `git diff --exit-code` to enforce clean state should add the `git checkout HEAD --` revert OR skip the long-comment areas until the fix lands.

## Why the existing `rust-wasm-perf-audit` SKILL.md pitfall #3 ("euv fmt 后看 git status") is insufficient

The existing pitfall warns that `euv fmt` re-formats unrelated files (`ui/src/style/class/fn.rs`). That advice is still correct — `git checkout HEAD --` is the right workaround. But the underlying *mechanism* is more specific than "macro-aware formatter touches unrelated files":

- The unrelated-file touch on `ui/src/style/class/fn.rs` is **caused by the same bug** (block comments with internal whitespace inside a class! body).
- Other files without long block comments inside macros are **not** affected by `euv fmt` — they're truly idempotent.

So `euv fmt` is **partially** idempotent: idempotent on files without such comments, non-idempotent on files with them. The existing pitfall should add this distinction once the fix lands.

## Test that should exist post-fix

`cli/tests/fmt/format_block_comment.rs`:

```rust
#[test]
fn fmt_is_idempotent_on_long_block_comments_in_class_body() {
    let input = "class! { pub c_x { /* hi\n                                                                                                                                                                                                                                                                                                                                                                                    comment */ color: \"red\"; } }";
    let r1 = euv_cli::fmt::fn::format_source(input);
    let r2 = euv_cli::fmt::fn::format_source(&r1.get_output());
    assert!(r2.get_changed() == false,
        "fmt non-idempotent: first pass produced {} chars, second pass produced {} chars",
        r1.get_output().len(), r2.get_output().len());
}
```

## Related

- PRs in the 12-PR perf batch all carry a `git checkout HEAD -- ui/src/style/class/fn.rs` step that becomes unnecessary post-fix.
- The bug also affects `html!` and `vars!` bodies (same `add_indentation` path), not just `class!`.
- The `rust-wasm-perf-audit` SKILL.md pitfall #3 should add "verify fmt is idempotent before assuming noise revert is sufficient" once the fix lands.

## Post-fix observed state at master HEAD b108fa10 (2026-09-11)

After PR #194 fix lands, running `euv fmt --path .` on a clean master tree produces:

- **1 file changed**: `ui/src/style/class/fn.rs` (+1/-1, the only change)
- **Specifically**: line 3592 — the `/* */` opener line's leading whitespace goes from 8 spaces to 4 spaces (e.g. `        /* ...` → `    /* ...`). Comment contents unchanged.
- **All other files**: stable.

This 1-file change is the long-commented dropdown menu class! whose indent was already drifting pre-fix. The fix's binary normalizes it once (8→4) and is then stable. **For maintainers**: PR #194 merge is sufficient; the 1-line noise is best handled by a separate small "chore: euv fmt one-pass cleanup" commit in the same merge window (or just amend the fix commit to include the 1-line normaliz[e]).

For subagents running in batches **before** PR #194 merges: keep the `git checkout HEAD -- ui/src/style/class/fn.rs` step in pre-commit. **After** PR #194 merges: the same line WILL change on the first fmt run (one-time normalize), but not on subsequent runs — switch to `git diff --stat | grep "ui/src/style/class/fn.rs"` as the trigger instead of unconditional revert.