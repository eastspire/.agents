#!/usr/bin/env python3
"""§9.2 — fn parameters must not use `impl Trait`.

Rule (2026-09-26 user tightening):

    fn f(x: impl AsRef<str>)          # forbidden
    fn f<T>(x: T) where T: AsRef<str> # required

`impl Trait` in argument position is an opaque type chosen by the *caller* at
each call site.  That defeats the "every function names its bounds explicitly"
property §9.2 is about: a `-> impl Trait` return still hides a bound from the
caller, but an `impl Trait` *parameter* additionally forbids the caller from
naming the type at all, so the bound can never be stated anywhere.

Deliberately NOT reported:
  - `-> impl Trait` in return position (that is idiomatic and is not §9.2)
  - `impl Trait` inside a `where` clause bound (a legal, explicit spelling)
  - occurrences inside `#[cfg(test)]` blocks and files under `tests/`
  - occurrences in comments, doc comments, string literals and raw strings

Exit code: 0 = compliant, 1 = violations, 2 = usage error.
"""

import re
import subprocess
import sys
from pathlib import Path

# `impl Trait` occurring anywhere.  Callers filter the allow-listed contexts.
IMPL_TRAIT = re.compile(r"\bimpl\s+(?:&\s*(?:'\w+\s+)?)?[A-Za-z_][A-Za-z0-9_:<>,\s]*")

FN_START = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?"
    r"(?:extern\s+\"[^\"]*\"\s+)?fn\s+"
)
CFG_TEST = re.compile(r"^\s*#\[cfg\(test\)\]")
# `-> impl Trait` is a RETURN position, explicitly allowed by §9.2.
RETURN_IMPL = re.compile(r"->\s*impl\b")


def _strip_code_noise(text: str) -> str:
    """Blank out comments, strings and raw strings, preserving line structure.

    A regex that ignored string state would flag `let s = "impl Iterator";`
    and — worse — a raw-string delimiter like `r"miter"` would eat the next
    real quote and desynchronise every later offset on the line.
    """
    out = []
    i, n = 0, len(text)
    line_start = True
    while i < n:
        ch = text[i]
        if ch == "\n":
            out.append("\n")
            line_start = True
            i += 1
            continue
        if not line_start and ch in " \t":
            out.append(" ")
            i += 1
            continue
        line_start = False
        # raw string r"..." / r#"..."# / br#"..."#
        m = re.match(r'(?:b?r)(#*)"', text[i:])
        if m:
            hashes = m.group(1)
            end = text.find('"' + hashes, i + m.end())
            end = n if end == -1 else end + 1 + len(hashes)
            out.append(" " * (end - i))
            i = end
            continue
        # ordinary string
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i = min(i + 1, n)
            out.append('"')
            continue
        # char literal
        if ch == "'":
            m2 = re.match(r"'(?:\\.|[^'\\])'", text[i:])
            if m2:
                out.append(" " * len(m2.group(0)))
                i += m2.end()
                continue
        # line comment
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            end = text.find("\n", i)
            end = n if end == -1 else end
            out.append(" " * (end - i))
            i = end
            continue
        # block comment
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            seg = text[i:end]
            out.append("".join(c if c == "\n" else " " for c in seg))
            i = end
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def list_rs_files(root: Path) -> list[Path]:
    result = subprocess.run(
        [
            "find", str(root), "-name", "*.rs",
            "-not", "-path", "*/target/*",
            "-not", "-path", "*/.cargo/registry/*",
        ],
        capture_output=True, text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _skip_whole_block(lines: list[str], idx: int) -> int:
    j = idx
    while j < len(lines) and "{" not in lines[j]:
        j += 1
    if j >= len(lines):
        return len(lines)
    depth, k = 0, j
    while k < len(lines):
        depth += lines[k].count("{") - lines[k].count("}")
        if depth == 0:
            return k
        k += 1
    return len(lines) - 1


def audit_one(path: Path) -> list[str]:
    try:
        raw = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    if "tests" in path.parts:
        return []
    lines = _strip_code_noise(raw).splitlines()
    violations: list[str] = []
    idx, total = 0, len(lines)
    while idx < total:
        if CFG_TEST.match(lines[idx]):
            idx = _skip_whole_block(lines, idx) + 1
            continue
        if FN_START.match(lines[idx]) is None:
            idx += 1
            continue
        end = _skip_whole_block(lines, idx)
        # `_skip_whole_block` returns len(lines) when the body never closes
        # (a macro fragment, a truncated file); clamp so the scan below cannot
        # index past the end.
        end = min(end, total - 1)
        # the signature is everything up to the `{` that opens the body
        sig_end = end
        for k in range(idx, end + 1):
            if "{" in lines[k]:
                sig_end = k
                break
        for k in range(idx, sig_end + 1):
            # a `->` before the `impl` makes it a return type, not a parameter
            for m in IMPL_TRAIT.finditer(lines[k]):
                head = lines[k][: m.start()]
                if RETURN_IMPL.search(head) or (RETURN_IMPL.search(lines[k]) and
                                                lines[k].index("->") < m.start()):
                    continue
                raw_lines = raw.splitlines()
                stripped = raw_lines[k].strip() if k < len(raw_lines) else lines[k].strip()
                violations.append(
                    f"{path}:{k + 1}: `impl Trait` in a fn parameter is forbidden "
                    f"(§9.2) — declare the bound explicitly instead: "
                    f"{stripped[:90]!r}"
                )
                break
        idx = end + 1
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    all_violations: list[str] = []
    file_count = 0
    for path in list_rs_files(root):
        found = audit_one(path)
        if found:
            file_count += 1
            all_violations.extend(found)
    for violation in all_violations:
        print(violation)
    print(
        f"\n=== no-impl-trait-fn-params: {len(all_violations)} violation(s) "
        f"in {file_count} file(s) ==="
    )
    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
