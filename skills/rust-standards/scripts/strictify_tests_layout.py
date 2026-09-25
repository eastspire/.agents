#!/usr/bin/env python3
"""
Strictify every tests/**/*.rs file in the repo against rust-standards §14
(testing). Idempotent — re-running produces no diff once §14 is satisfied.
NEVER call on src/ — only tests/.

Rules enforced (see references/14-testing.md for prose):

 1. Delete every `//` / `///` / `//!` line (regardless of indentation) from
    every file under tests/. Per §14.5 test fn = its own documentation; no
    inline // is allowed, ever.
 2. `tests/<sub>/mod.rs` keeps any `pub use xxx;` re-exports at the top
    (these are required by §14.7 to make non-super items visible from
    `fn.rs`), and ends with exactly two lines: `mod r#fn;` then
    `use super::*;`. No blank lines, no comments.
 3. `tests/<sub>/fn.rs`:
    - First non-comment line must be `use super::*;`.
    - All `use` statements grouped at top, with one blank line before the
      first `#[test]` / `#[wasm_bindgen_test]`.
    - Drop redundant blank lines between code blocks (single blank line
      between test fns only).
 4. Root loose files under `tests/<file>.rs`:
    - Strip any `use super::*;` (E0433 — `super` undefined at crate root).
    - Drop comments. Leave other imports as-is.
    - These are the integration-test crate root; only files inside
      `tests/<sub>/` get the `use super::*;` treatment.

Run from repo root:

    python3 <skill>/scripts/strictify_tests_layout.py <repo_root>

It rewrites files in place. Re-running on a clean repo exits 0 with all
counts = 0.
"""
import re
import sys
from pathlib import Path


COMMENT_PREFIXES = ("///", "//!", "//")

MOD_DECL_LINE = "mod r#fn;"
MOD_TAIL = "use super::*;"


def is_comment_line(line: str) -> bool:
    stripped = line.lstrip()
    return any(stripped.startswith(p) for p in COMMENT_PREFIXES)


def strip_comments(text: str) -> str:
    out: list[str] = []
    prev_blank = False
    for line in text.splitlines():
        if is_comment_line(line):
            continue
        if not line.strip():
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        out.append(line)
    return "\n".join(out).rstrip() + ("\n" if out else "")


def normalize_sub_mod_rs(text: str) -> str:
    """Enforce: `pub use ...;` block at top (preserved verbatim in input
    order), then `mod r#fn;`, then `use super::*;`. Empty lines and comments
    are stripped; `mod r#fn;` is inserted if missing; trailing `use super::*;`
    is always present exactly once at the end.
    """
    pub_uses: list[str] = []
    has_mod_decl = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or is_comment_line(raw):
            continue
        if stripped.startswith("pub use "):
            # dedupe, preserve order
            if stripped not in pub_uses:
                pub_uses.append(stripped)
        elif stripped == MOD_DECL_LINE:
            has_mod_decl = True
        # any other statement (use std::xxx; without pub, mod xxx; without
        # r#, etc.) is dropped: the only legal content is `pub use ...;`,
        # the `mod r#fn;` declaration, and the trailing `use super::*;`.
    lines = list(pub_uses)
    if has_mod_decl:
        if MOD_DECL_LINE not in lines:
            lines.append(MOD_DECL_LINE)
    else:
        if MOD_DECL_LINE not in lines:
            lines.append(MOD_DECL_LINE)
    lines.append(MOD_TAIL)
    return "\n".join(lines) + "\n"


def clean_sub_fn_rs(text: str) -> str:
    """Enforce §14.7 + §14.5 on tests/<sub>/fn.rs:
    - Strip comments.
    - First non-comment line must be `use super::*;`; strip any other `use`.
    - Group remaining `use` (none should remain after stripping) then body.
    - Single blank line between test fns.
    """
    lines = [line for line in text.splitlines() if not is_comment_line(line)]
    if not lines:
        return ""

    # Per §14.7: tests/<sub>/fn.rs may contain ONLY `use super::*;` as a
    # top-level use statement. Drop every other `use xxx;` here — they
    # belong in tests/<sub>/mod.rs as `pub use xxx;`.
    filtered = [
        line for line in lines
        if not (line.lstrip().startswith("use ") and line.strip() != MOD_TAIL)
    ]

    use_lines: list[str] = []
    body: list[str] = []
    if filtered and filtered[0].strip() == MOD_TAIL:
        use_lines = [MOD_TAIL]
        rest = filtered[1:]
    else:
        use_lines = [MOD_TAIL]
        rest = filtered

    saw_non_use = False
    for line in rest:
        if not saw_non_use and line.lstrip().startswith("use "):
            # Any leftover `use` (shouldn't exist post-strip) silently dropped.
            continue
        saw_non_use = True
        body.append(line)

    out: list[str] = list(use_lines) + [""]
    prev_blank = True
    for line in body:
        if not line.strip():
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        out.append(line)
    return "\n".join(out).rstrip() + "\n"


def clean_loose_rs(text: str) -> str:
    text = re.sub(r"^use super::\*;\s*\n", "", text, flags=re.MULTILINE)
    return strip_comments(text)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: strictify_tests_layout.py <repo_root>")
        return 2
    repo_root = Path(argv[1])
    if not repo_root.is_dir():
        print(f"FAIL: {repo_root} is not a directory")
        return 2

    total_sub_mod = total_sub_fn = total_loose = 0

    for test_root in repo_root.glob("tests"):
        if not test_root.is_dir():
            continue

        for sub_dir in sorted(p for p in test_root.iterdir() if p.is_dir()):
            mod_path = sub_dir / "mod.rs"
            if mod_path.is_file():
                current = mod_path.read_text()
                cleaned = normalize_sub_mod_rs(current)
                if cleaned != current:
                    mod_path.write_text(cleaned)
                    total_sub_mod += 1

            fn_path = sub_dir / "fn.rs"
            if fn_path.is_file():
                current = fn_path.read_text()
                cleaned = clean_sub_fn_rs(current)
                if cleaned != current:
                    fn_path.write_text(cleaned)
                    total_sub_fn += 1

        for loose in sorted(test_root.glob("*.rs")):
            if loose.name == "mod.rs":
                continue
            current = loose.read_text()
            cleaned = clean_loose_rs(current)
            if cleaned != current:
                loose.write_text(cleaned)
                total_loose += 1

    print(f"sub mod.rs rewritten: {total_sub_mod}")
    print(f"sub fn.rs rewritten:  {total_sub_fn}")
    print(f"loose .rs rewritten:  {total_loose}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
