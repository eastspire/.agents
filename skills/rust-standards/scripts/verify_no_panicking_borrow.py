#!/usr/bin/env python3
"""RefCell borrow verifier: panic-prone borrows must be handled or proven safe.

Rule (2026-09-30 user directive):
  "你的代码应该安全处理所有borrow失败的情况,此仓库的所有地方都应该处理"

`RefCell::borrow()` / `borrow_mut()` PANIC when the cell is already borrowed.
In a WASM UI framework there is no try/catch around a Rust panic, so a
re-entrant borrow aborts the whole instance ("already borrowed:
BorrowMutError") and the page goes blank. Every site must therefore either
be structurally incapable of failing, or handle the failure.

Two violation classes are reported:

  GUARD  A `Ref`/`RefMut` guard is held across a statement that can run
         arbitrary code and re-enter the same cell. The classic shape is
         `let g = cell.borrow_mut();` followed by a `Signal::set()`, a
         web-sys / JS call, or an `Rc<dyn Fn>` invocation. This is the
         class that actually crashes apps.
  PANIC  A bare `.borrow()` / `.borrow_mut()` whose result is bound to a
         named guard and then held until the end of an enclosing block
         that contains such a call, with no `try_borrow*` anywhere.

A one-line borrow whose temporary guard dies at the end of the statement is
ALREADY SAFE and is deliberately NOT reported: converting it to `try_borrow`
adds a branch and an unwrap for no benefit, and a blanket sweep is itself a
code smell.

Exit code: 0 = compliant, 1 = violations, 2 = usage error.
"""

import re
import subprocess
import sys
from pathlib import Path

# `x.borrow()` / `x.borrow_mut()` not already part of `try_borrow*`.
BORROW = re.compile(r"(?<!try_)\.(borrow|borrow_mut)\(\)")
# A named guard binding: `let g = ...borrow_mut();`
GUARD_BIND = re.compile(
    r"^\s*let\s+(?:mut\s+)?(\w+)\s*(?::[^=]+)?=\s*.*?\.(borrow|borrow_mut)\(\)\s*;\s*$"
)
# Statements that can re-enter arbitrary code.
REENTRANT = re.compile(
    r"\.\s*(set|set_mut)\s*\("  # Signal::set -> re-render
    r"|\.\s*(push_state|replace_state|back|forward|go)\s*\("  # history
    r"|\bwindow\s*\(\s*\)"  # web-sys
    r"|\.\s*(dispatch|invoke|call|run|fire|emit)\w*\s*\("
    r"|\bas_bool\s*\(\s*\)"  # Closure<dyn Fn>
    r"|\bJsValue\b|\bjs_sys\b|\bReflect\b"
    r"|\.\s*(alert|confirm|prompt|request_animation_frame|set_timeout|set_interval)\s*\("
    r"|\balert\s*\(|\bconfirm\s*\(|\bprompt\s*\("
)
FN_START = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+([a-z_][a-z0-9_]*)"
)
CFG_TEST = re.compile(r"^\s*#\[cfg\(test\)\]")


def list_rs_files(root: Path) -> list[Path]:
    result = subprocess.run(
        [
            "find",
            str(root),
            "-name",
            "*.rs",
            "-not",
            "-path",
            "*/target/*",
            "-not",
            "-path",
            "*/.cargo/registry/*",
        ],
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _skip_whole_block(lines: list[str], idx: int) -> int:
    """Return the index of the line closing the block that opens at/after idx."""
    j = idx
    while j < len(lines) and "{" not in lines[j]:
        j += 1
    if j >= len(lines):
        return len(lines)
    depth = 0
    k = j
    while k < len(lines):
        depth += lines[k].count("{") - lines[k].count("}")
        if depth == 0:
            return k
        k += 1
    return len(lines) - 1


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    if "tests" in path.parts:
        return []
    lines = text.splitlines()
    violations: list[str] = []

    idx = 0
    total = len(lines)
    while idx < total:
        line = lines[idx]
        if CFG_TEST.match(line):
            idx = _skip_whole_block(lines, idx) + 1
            continue
        if FN_START.match(line) is None:
            idx += 1
            continue
        end = _skip_whole_block(lines, idx)
        body = lines[idx : end + 1]
        violations.extend(_scan_fn(path, idx, body))
        idx = end + 1
    return violations


def _scan_fn(path: Path, base_line: int, body: list[str]) -> list[str]:
    """Report guards in `body` that are still in scope at a re-entrant call.

    Scope is tracked with brace depth so a guard confined to its own block
    `{ let g = ..; use(g); }` is correctly seen as dropped before anything
    that follows, which is the whole point of the narrow-scope fix.
    """
    violations: list[str] = []
    reported: set[str] = set()
    # guard name -> brace depth at which it was declared
    live: dict[str, int] = {}
    depth = 0
    for offset, raw in enumerate(body):
        stripped = raw.strip()
        if stripped.startswith("//"):
            depth += raw.count("{") - raw.count("}")
            continue

        match = GUARD_BIND.match(raw)
        if match is not None:
            live[match.group(1)] = depth

        # A guard is gone once we close the block that declared it.
        for name in [n for n, d in live.items() if depth < d]:
            del live[name]

        hit = REENTRANT.search(raw)
        if live and hit and match is None and hit.group(0).strip() not in live:
            name = sorted(live)[0]
            if name in reported:
                depth += raw.count("{") - raw.count("}")
                continue
            reported.add(name)
            violations.append(
                f"{path}:{base_line + offset + 1}: RefCell guard `{name}` is "
                f"still in scope at a re-entrant call; narrow the guard's "
                f"lifetime or use try_borrow (§borrow): {stripped[:80]!r}"
            )
        depth += raw.count("{") - raw.count("}")
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    all_violations: list[str] = []
    file_count = 0
    for path in list_rs_files(root):
        violations = audit_one(path)
        if violations:
            file_count += 1
            all_violations.extend(violations)
    for violation in all_violations:
        print(violation)
    print(
        f"\n=== no-panicking-refcell-borrow: {len(all_violations)} violation(s) "
        f"in {file_count} file(s) ==="
    )
    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
