#!/usr/bin/env python3
"""Push only specific source files (src/*.rs, docs/config.toml, etc.) to a
target branch via the Git Data API, when local git push fails because remote
has commits you don't have locally.

Use case: You edited 2 source files in a non-git-fast-forwardable state (e.g.
remote master is ahead by a Pages-source-branch flip). The workflow listens to
master, so you must get the changes onto master. `git push origin master` will
fail with "fetch first". Git Data API bypasses that — you POST blobs, build a
new tree on top of remote master tree, create a commit, then PATCH the ref.

Usage:
  GH_TOKEN=... python3 push-source-only.py \\
      --owner docs-pages --repo docs-euv \\
      --branch master \\
      --file src/lib.rs:/path/to/local/lib.rs \\
      --file docs/config.toml:/path/to/local/config.toml \\
      --message "fix(site): sidebar top align + footer vuepress"

Args:
  --owner / --repo: target repository
  --branch: target branch (must be where workflow listens, usually master)
  --file: SRC_PATH:LOCAL_PATH (repeatable)
  --message: commit message

Implementation notes:
- Uses --data-binary '@-' with stdin to avoid "Argument list too long" on large files
- base_tree = remote branch head tree → new tree only replaces the named files
- New commit's parent = current remote branch head
- PATCH /git/refs/heads/<branch> updates the ref (must be fast-forward,
  but since new commit parent = current head, this is always fast-forward)
"""
import argparse, base64, json, mimetypes, os, subprocess, sys

def gh_token():
    out = subprocess.run(['bash', '-c', 'source /root/.bashrc.d/gh_token.sh && echo $GH_TOKEN'],
                         capture_output=True, text=True).stdout.strip()
    if not out:
        sys.exit('GH_TOKEN not found in /root/.bashrc.d/gh_token.sh')
    return out

def api(method, url, body=None, token=None):
    cmd = ['curl', '-sS', '-X', method,
           '-H', f'Authorization: token {token}',
           '-H', 'Content-Type: application/json']
    if body is not None:
        cmd += ['--data-binary', '@-']
    cmd.append(url)
    data = json.dumps(body).encode('utf-8') if isinstance(body, (dict, list)) else body
    if isinstance(body, str):
        data = body.encode('utf-8')
    r = subprocess.run(cmd, input=data, capture_output=True)
    return json.loads(r.stdout.decode('utf-8', errors='replace'))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--owner', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--branch', default='master')
    ap.add_argument('--file', action='append', required=True,
                    help='REPO_PATH:LOCAL_PATH (repeatable)')
    ap.add_argument('--message', required=True)
    args = ap.parse_args()

    token = gh_token()
    base = f'https://api.github.com/repos/{args.owner}/{args.repo}'

    # 1. Read current branch head
    ref = api('GET', f'{base}/git/refs/heads/{args.branch}', token=token)
    parent_sha = ref['object']['sha']
    print(f'parent: {parent_sha}')

    # 2. Get parent commit tree
    commit = api('GET', f'{base}/git/commits/{parent_sha}', token=token)
    base_tree = commit['tree']['sha']
    print(f'base_tree: {base_tree}')

    # 3. For each file, POST blob + record
    tree_items = []
    for spec in args.file:
        repo_path, local_path = spec.split(':', 1)
        with open(local_path, 'rb') as fp:
            content = fp.read()
        blob = api('POST', f'{base}/git/blobs',
                   body={'encoding': 'base64',
                         'content': base64.b64encode(content).decode('ascii')},
                   token=token)
        if 'sha' not in blob:
            sys.exit(f'blob create failed for {repo_path}: {blob}')
        tree_items.append({
            'path': repo_path, 'mode': '100644', 'type': 'blob', 'sha': blob['sha'],
        })
        print(f'  uploaded {repo_path} (sha {blob["sha"][:8]})')

    # 4. Create new tree on top of base_tree
    new_tree = api('POST', f'{base}/git/trees',
                   body={'base_tree': base_tree, 'tree': tree_items},
                   token=token)
    print(f'new tree: {new_tree["sha"]}')

    # 5. Create commit
    new_commit = api('POST', f'{base}/git/commits',
                     body={'message': args.message,
                           'parents': [parent_sha],
                           'tree': new_tree['sha']},
                     token=token)
    print(f'new commit: {new_commit["sha"]}')

    # 6. Update ref
    api('PATCH', f'{base}/git/refs/heads/{args.branch}',
        body={'sha': new_commit['sha']}, token=token)
    print(f'updated {args.branch} → {new_commit["sha"]}')

if __name__ == '__main__':
    main()
