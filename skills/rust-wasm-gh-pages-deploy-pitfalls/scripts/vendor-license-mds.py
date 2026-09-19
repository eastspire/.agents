#!/usr/bin/env python3
"""Vendor each crate's LICENSE from its GitHub repo into docs/<crate>/LICENSE.md.

For every docs/<dir>/README.md that links to a bare LICENSE (](./LICENSE) or
](LICENSE)), extract the repo from the README's [GITHUB 地址](...) link,
download the LICENSE via the GitHub Contents API (follows the default branch),
and write docs/<dir>/LICENSE.md with `sidebar: false` frontmatter so the page
is routable but stays out of the auto-generated sidebar tree. README links are
rewritten to ./LICENSE.md so euv-docs rewrite_link routes them to
#/<dir>/LICENSE.html.

Idempotent: skips dirs whose LICENSE.md already exists (use --force to redo).

Usage: python3 vendor-license-mds.py [docs_root] [--force]
Default docs_root: ~/github/docs-pages/docs/docs
Needs GH_TOKEN in env or /root/.bashrc.d/gh_token.sh.
"""
import os
import re
import subprocess
import sys
import urllib.request

def get_token():
    tok = os.environ.get('GH_TOKEN', '').strip()
    if tok:
        return tok
    r = subprocess.run(
        ['bash', '-c', 'grep -oP \'export GH_TOKEN="\\K[^"]+\' /root/.bashrc.d/gh_token.sh 2>/dev/null || true'],
        capture_output=True, text=True)
    return r.stdout.strip()

def fetch_license(token, owner, repo):
    for name in ('LICENSE', 'LICENSE-MIT', 'LICENSE.md', 'LICENSE.txt'):
        url = f'https://api.github.com/repos/{owner}/{repo}/contents/{name}'
        req = urllib.request.Request(url, headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github.v3.raw',
            'User-Agent': 'hermes-agent'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode('utf-8'), name
        except Exception:
            continue
    return None, None

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    force = '--force' in sys.argv
    root = os.path.expanduser(args[0]) if args else os.path.expanduser('~/github/docs-pages/docs/docs')
    token = get_token()
    if not token:
        sys.exit('GH_TOKEN not found')
    ok = skipped = failed = 0
    for d in sorted(os.listdir(root)):
        rdm = os.path.join(root, d, 'README.md')
        if not os.path.isfile(rdm):
            continue
        with open(rdm) as f:
            txt = f.read()
        has_bare = '](LICENSE)' in txt or '](./LICENSE)' in txt
        out = os.path.join(root, d, 'LICENSE.md')
        if not has_bare and not (force and os.path.isfile(out)):
            continue
        if os.path.isfile(out) and not force and not has_bare:
            skipped += 1
            continue
        m = re.search(r'GITHUB 地址\]\((https://github\.com/[^)]+)\)', txt)
        if not m:
            print(f'{d}: NO_REPO'); failed += 1; continue
        owner, repo = m.group(1).rstrip('/').replace('https://github.com/', '').split('/', 1)
        content, fname = fetch_license(token, owner, repo)
        if content is None:
            print(f'{d}: DOWNLOAD_FAIL {owner}/{repo}'); failed += 1; continue
        with open(out, 'w') as f:
            f.write('---\ntitle: 开源许可证\nsidebar: false\n---\n\n```text\n' + content.rstrip('\n') + '\n```\n')
        new = txt.replace('](./LICENSE)', '](./LICENSE.md)').replace('](LICENSE)', '](LICENSE.md)')
        if new != txt:
            with open(rdm, 'w') as f:
                f.write(new)
        print(f'{d}: OK ({owner}/{repo} {fname})')
        ok += 1
    print(f'\nok={ok} skipped={skipped} failed={failed}')

if __name__ == '__main__':
    main()
