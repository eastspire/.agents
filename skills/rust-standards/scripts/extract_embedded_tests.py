#!/usr/bin/env python3
"""Extract `#[cfg(test)] mod tests { ... }` blocks from production source files
into a target `tests/<sub>/{fn,mod}.rs` directory.

Why this exists: rust-standards §14.0 forbids `#[test]` inside production
source files. When a developer (or prior agent) left `#[cfg(test)] mod tests`
inline, this script moves the test bodies into the right `tests/<sub>/`
location and dedents them.

Usage:
    python3 extract_embedded_tests.py --moves <json>

Where <json> is a JSON list of objects: `[{"src": "src/foo.rs", "dst": "tests/foo"}, ...]`

The script writes:
    <dst>/mod.rs   -> mod r#fn;\n\npub use super::*;
    <dst>/fn.rs    -> use super::*;\n\n<dedented inner tests>

It also strips the `#[cfg(test)] mod tests { ... }` block from the source file.
"""

import argparse
import json
import os
import re
import sys


def find_matching_brace_smart(content: str, start_pos: int) -> int:
    """Find matching close brace, skipping braces inside strings, char
    literals, and comments. Returns absolute byte position of the char AFTER
    the matching `}`, or -1 if not found.

    Why "smart": a naïve `{` / `}` counter breaks on Rust test code that
    contains JSON fixtures like `"{\"entries\":{}}"`. We skip braces inside
    `"..."`, `r"..."`, `r#"..."#`, `'x'` (but not `'static`), and `//` and
    `/* ... */` comments.
    """
    depth = 0
    found_open = False
    i = start_pos
    n = len(content)
    while i < n:
        c = content[i]
        nxt = content[i + 1] if i + 1 < n else ""
        # Line comment
        if c == "/" and nxt == "/":
            while i < n and content[i] != "\n":
                i += 1
            continue
        # Block comment
        if c == "/" and nxt == "*":
            i += 2
            while i < n - 1:
                if content[i] == "*" and content[i + 1] == "/":
                    i += 2
                    break
                i += 1
            continue
        # Raw string with hashes: r#"..."# or r##"..."##
        if c == "r" and nxt == "#":
            i += 2
            hash_count = 0
            while i < n and content[i] == "#":
                hash_count += 1
                i += 1
            if i < n and content[i] == '"':
                i += 1
                while i < n:
                    if content[i] == '"':
                        is_end = True
                        for k in range(hash_count):
                            if i + 1 + k >= n or content[i + 1 + k] != "#":
                                is_end = False
                                break
                        if is_end:
                            i += 1 + hash_count
                            break
                    i += 1
            continue
        # Raw string without hashes: r"..."
        if c == "r" and nxt == '"':
            i += 2
            while i < n:
                if content[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        # Regular string literal
        if c == '"':
            i += 1
            while i < n:
                if content[i] == "\\" and i + 1 < n:
                    i += 2
                elif content[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            continue
        # Char literal: 'x' but NOT lifetimes like 'static
        if c == "'":
            if nxt == "\\":
                # Escape: '\\', '\n' — skip 4 chars (', \, char, ')
                i += 4
                continue
            if nxt and not (nxt.isalpha() and nxt.islower()):
                # Likely a char literal 'X' where X is non-lowercase
                i += 3
                continue
            # Else: it's a lifetime 'static — treat as regular char
        if c == "{":
            depth += 1
            found_open = True
        elif c == "}":
            depth -= 1
            if found_open and depth == 0:
                return i + 1
        i += 1
    return -1


def extract_tests(src_path: str, dst_dir: str) -> int:
    """Move `#[cfg(test)] mod tests { ... }` from src_path to dst_dir/{fn,mod}.rs.

    Returns number of lines written to fn.rs (excluding the use super::* header).
    """
    with open(src_path) as f:
        content = f.read()

    pattern = re.compile(r"#\[cfg\(test\)\]\s*\n\s*mod\s+\w+\s*\{", re.M)
    m = pattern.search(content)
    if not m:
        print(f"  SKIP {src_path} (no #[cfg(test)] mod block)")
        return 0

    start = m.start()
    end = find_matching_brace_smart(content, start)
    if end == -1:
        print(f"  FAIL {src_path} (could not find matching brace)")
        return 0

    block = content[start:end]
    lines = block.split("\n")

    # Skip until `mod <name> {` then take everything until final `}`
    inner_lines: list[str] = []
    in_inner = False
    for line in lines:
        if not in_inner:
            if re.match(r"mod\s+\w+\s*\{", line.strip()):
                in_inner = True
            continue
        inner_lines.append(line)
    if inner_lines and inner_lines[-1].strip() == "}":
        inner_lines = inner_lines[:-1]

    # Remove the first `use super::*;` (we add it at top of fn.rs)
    cleaned: list[str] = []
    skipped = False
    for line in inner_lines:
        if not skipped and line.strip() == "use super::*;":
            skipped = True
            continue
        cleaned.append(line)

    # Dedent 4 spaces
    dedented = []
    for line in cleaned:
        if line.startswith("    "):
            dedented.append(line[4:])
        else:
            dedented.append(line)

    # Write mod.rs + fn.rs
    os.makedirs(dst_dir, exist_ok=True)
    with open(os.path.join(dst_dir, "mod.rs"), "w") as f:
        f.write("mod r#fn;\n\npub use super::*;\n")
    with open(os.path.join(dst_dir, "fn.rs"), "w") as f:
        f.write("use super::*;\n\n")
        f.write("\n".join(dedented))

    # Strip the test block from source file
    prod = content[:start].rstrip() + "\n"
    with open(src_path, "w") as f:
        f.write(prod)

    n_tests = sum(1 for line in dedented if line.strip().startswith("#[test]"))
    print(f"  {src_path} -> {dst_dir}/fn.rs ({len(dedented)} lines, ~{n_tests} tests)")
    return len(dedented)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--moves",
        required=True,
        help='JSON list of {"src": "...", "dst": "..."} objects',
    )
    args = ap.parse_args()

    moves = json.loads(args.moves)
    for move in moves:
        extract_tests(move["src"], move["dst"])
    return 0


if __name__ == "__main__":
    sys.exit(main())