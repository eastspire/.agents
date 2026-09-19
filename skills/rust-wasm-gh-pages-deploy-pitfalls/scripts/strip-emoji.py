#!/usr/bin/env python3
"""Strip all emoji from a docs-euv (or any markdown-heavy) repo.

Catches坑 20: emoji codepoints in md / build.rs / config.toml / src/ that headless
Chromium renders as boxes (no NotoColorEmoji), Pages CDN caches the boxes for 10min,
and the user's clear preference is "no emoji anywhere".

Covers:
- U+1F000..U+1FFFF  (most emoji planes — Pictographs, Emoticons, Transport,
                       Supplemental Symbols-Pictographs, Symbols-Pictographs Extended-A)
- U+2600..U+27BF    (Misc Symbols + Dingbats — ☰ ✕ ★ ☆ ♪ etc.)
- U+2300..U+23FF    (Misc Technical — ⌨ ⏏ ⏳ etc.)
- U+FE00..U+FE0F    (Variation Selectors — turn base char into emoji-style)
- U+200B..U+200D    (Zero-width space / non-joiner / joiner)
- U+2060, U+00AD    (Word joiner, soft hyphen)

Usage:
    python3 scripts/strip-emoji.py [root]
    # default root = .

Exit codes:
    0 = stripped (or nothing to strip)
    2 = error (e.g. invalid path)
"""
import os
import re
import sys

EMOJI_PAT = re.compile(
    r'[\U0001F000-\U0001FFFF'   # most emoji planes
    r'\u2600-\u27BF'              # misc symbols + dingbats
    r'\u2300-\u23FF'              # misc technical
    r'\uFE00-\uFE0F'              # variation selectors
    r'\u200B-\u200D\u2060\u00AD]'  # zero-width + soft hyphen
)

TEXT_EXTS = {'.md', '.rs', '.toml', '.html', '.yml', '.yaml', '.json', '.txt'}
SKIP_PARTS = {'www', '.git', 'target', 'node_modules', '__pycache__', 'Cargo.lock'}


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    if not os.path.isdir(root):
        print(f'ERROR: {root} is not a directory', file=sys.stderr)
        sys.exit(2)

    modified = 0
    total_emoji_removed = 0
    for dirpath, dirnames, filenames in os.walk(root):
        parts = os.path.relpath(dirpath, root).split(os.sep)
        if any(p in SKIP_PARTS for p in parts):
            continue
        for f in filenames:
            if not any(f.endswith(ext) for ext in TEXT_EXTS):
                continue
            path = os.path.join(dirpath, f)
            try:
                with open(path, encoding='utf-8') as fh:
                    content = fh.read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue

            n = EMOJI_PAT.sub('', content)
            if n != content:
                removed = len(EMOJI_PAT.findall(content))
                total_emoji_removed += removed
                modified += 1
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(n)

    print(f'modified: {modified} files')
    print(f'emoji removed: {total_emoji_removed}')

    # verify nothing
    leftover = 0
    for dirpath, dirnames, filenames in os.walk(root):
        parts = os.path.relpath(dirpath, root).split(os.sep)
        if any(p in SKIP_PARTS for p in parts):
            continue
        for f in filenames:
            if not any(f.endswith(ext) for ext in TEXT_EXTS):
                continue
            path = os.path.join(dirpath, f)
            try:
                with open(path, encoding='utf-8') as fh:
                    leftover += len(EMOJI_PAT.findall(fh.read()))
            except UnicodeDecodeError:
                pass
    print(f'remaining emoji: {leftover}')


if __name__ == '__main__':
    main()