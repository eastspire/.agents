#!/usr/bin/env python3
"""Check euv-docs README.md (or any md) frontmatter parses correctly.

Catches坑 17: 2-vs-4 space indent silently dropping the entire `features:` array.

Usage:
    python3 scripts/check-frontmatter.py [docs_root]
    # default docs_root = ./docs

Exit codes:
    0 = all md frontmatter parses, home pages have non-empty features
    1 = at least one md has broken YAML or empty features on a home page
"""
import os
import sys
import yaml

def main():
    docs_root = sys.argv[1] if len(sys.argv) > 1 else 'docs'
    if not os.path.isdir(docs_root):
        print(f'ERROR: {docs_root} is not a directory', file=sys.stderr)
        sys.exit(2)

    broken = []
    total = 0
    home_pages = 0
    for root, _, files in os.walk(docs_root):
        for f in files:
            if not f.endswith('.md'):
                continue
            p = os.path.join(root, f)
            try:
                with open(p, encoding='utf-8') as fh:
                    txt = fh.read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue

            if not txt.startswith('---\n'):
                continue

            # find closing ---
            end = txt.find('\n---', 4)
            if end == -1:
                broken.append(f'{p}: frontmatter open but no closing ---')
                continue

            fm = txt[4:end]
            try:
                d = yaml.safe_load(fm)
            except yaml.YAMLError as e:
                broken.append(f'{p}: YAML error {e}')
                continue

            if d is None:
                continue

            total += 1

            # detect home=true but features silently dropped to []
            if d.get('home') is True:
                home_pages += 1
                features = d.get('features')
                if features is not None and len(features) == 0:
                    broken.append(
                        f'{p}: home=true but features=0 (likely 2-vs-4-space '
                        f'indent drop in list-of-mapping)'
                    )

    print(f'scanned {total} md files ({home_pages} home pages)')
    if broken:
        print(f'\n{len(broken)} broken:')
        for b in broken:
            print(f'  - {b}')
        sys.exit(1)
    print('OK: all frontmatter parses, home pages have non-empty features')


if __name__ == '__main__':
    main()