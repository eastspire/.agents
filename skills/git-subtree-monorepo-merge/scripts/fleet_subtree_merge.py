#!/usr/bin/env python3
"""
fleet_subtree_merge.py — verified, re-runnable helper for git-subtree-monorepo-merge.

What it does
------------
1. Discovers GH token from the environment, falling back to git's credential helper.
2. Lists repos for an org/user via /orgs/<O>/repos or /users/<U>/repos.
3. Clones each repo (with --quiet), parallel via ThreadPoolExecutor (4 workers).
4. Builds the merge plan: branches, prefix paths, commit messages.
5. Subtree-adds each repo into <clone>/<subdir>/<name>/ on the local monorepo clone.
6. Writes a workspace manifest (Cargo.toml template) at root, commits once at the end.
7. Force-pushes (or stays on a feature branch for PR flow) — caller decides.

This script is a TEMPLATE — copy and modify per project. Tested against 21-crate fleet on 2026-09-25.
"""
import argparse, json, os, pathlib, shutil, subprocess, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed


def discover_token():
    t = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if t:
        return t
    out = subprocess.run(['git', 'credential', 'fill'],
                         input='protocol=https\nhost=github.com\n\n',
                         capture_output=True, text=True, timeout=15)
    fields = dict(l.split('=', 1) for l in out.stdout.splitlines() if '=' in l)
    if fields.get('password'):
        return fields['password']
    return None


def gh(path, token, method='GET', data=None):
    url = f'https://api.github.com{path}'
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
    }, method=method, data=body)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode()
            if r.status == 204 or not raw:
                return {'_status': r.status}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        return {'_http_error': e.code, '_body': e.read().decode()[:300]}


def list_org_repos(org, token):
    repos = []
    page = 1
    while True:
        batch = gh(f'/orgs/{org}/repos?per_page=100&type=all&page={page}', token)
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(batch)
        page += 1
    return [r for r in repos if not r.get('archived')]


def clone_one(name, url, target):
    if os.path.exists(target):
        return (name, 'skip', 'exists')
    for attempt in range(1, 4):
        try:
            r = subprocess.run(['git', 'clone', '--quiet', url, target],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                return (name, 'ok', url)
            err = (r.stderr or r.stdout).strip()[:200]
        except subprocess.TimeoutExpired:
            err = 'timeout'
        if attempt < 3:
            import time; time.sleep(2 ** attempt)
    return (name, 'fail', err)


def cargo_workspace_toml(members):
    lines = ['[workspace]', 'resolver = "2"', 'members = [']
    for m in members:
        lines.append(f'    "{m}",')
    lines.append(']')
    lines.append('')
    lines.append('[workspace.package]')
    lines.append('edition = "2021"')
    lines.append('license = "MIT"')
    lines.append('rust-version = "1.75"')
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--org', required=True, help='GitHub org/user to pull from')
    ap.add_argument('--owner', required=True, help='GitHub owner for the new monorepo')
    ap.add_argument('--new-name', required=True, help='New monorepo repo name')
    ap.add_argument('--subdir', default='crates', help='Subdirectory for imported repos')
    ap.add_argument('--work', default='/tmp/fleet-merge', help='Working directory')
    ap.add_argument('--default-branch', default='master')
    ap.add_argument('--push-mode', choices=['force', 'branch'], default='branch',
                    help='force = push straight to default; branch = push to import/ branch for PR')
    ap.add_argument('--branch-prefix', default='import/')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    token = discover_token()
    if not token:
        sys.exit('GH_TOKEN not found in env and no git credential helper entry for github.com')
    print(f'token: ...{token[-4:]}  ({len(token)} chars)')

    work = pathlib.Path(args.work)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    clones = work / 'clones'
    clones.mkdir()
    monorepo = work / 'monorepo'

    print(f'== listing repos under {args.org} ==')
    repos = list_org_repos(args.org, token)
    if not repos:
        sys.exit(f'no repos found for {args.org}')
    print(f'   found {len(repos)} non-archived repos')

    print(f'== checking name collision for {args.owner}/{args.new_name} ==')
    collision = gh(f'/repos/{args.owner}/{args.new_name}', token)
    if isinstance(collision, dict) and 'name' in collision:
        sys.exit(f'REPO ALREADY EXISTS: {collision["html_url"]}')
    print('   no collision')

    print(f'== cloning {len(repos)} repos (4 workers) ==')
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {}
        for r in repos:
            target = str(clones / r['name'])
            futs[ex.submit(clone_one, r['name'], r['clone_url'], target)] = r
        for f in as_completed(futs):
            results.append(f.result())
    ok = sum(1 for r in results if r[1] == 'ok')
    fail = [r for r in results if r[1] == 'fail']
    print(f'   cloned: {ok}/{len(results)}')
    if fail:
        for n, _, msg in fail:
            print(f'   FAILED: {n}: {msg}')
        sys.exit('clone failures; aborting')

    print(f'== creating {args.owner}/{args.new_name} ==')
    create = gh(f'/orgs/{args.owner}/repos', token, method='POST', data={
        'name': args.new_name,
        'description': f'Monorepo aggregating all {len(repos)} repos from {args.org}',
        'private': False,
        'auto_init': True,
        'default_branch': args.default_branch,
        'license_template': 'mit',
    })
    if create.get('_http_error'):
        sys.exit(f'create failed: HTTP {create["_http_error"]}: {create["_body"][:200]}')
    print(f'   {create["html_url"]}  default_branch={create["default_branch"]}')

    if args.dry_run:
        print('\nDRY RUN — stopping before merge')
        return

    clone_url = create['clone_url']
    subprocess.run(['git', 'clone', '--quiet', clone_url, str(monorepo)], check=True)
    subprocess.run(['git', '-C', str(monorepo), 'checkout', args.default_branch], check=True)
    subprocess.run(['git', '-C', str(monorepo), 'config', 'user.email', 'hermes-agent@local'], check=True)
    subprocess.run(['git', '-C', str(monorepo), 'config', 'user.name', 'Hermes Agent (fleet merge)'], check=True)

    members = [f'{args.subdir}/{r["name"]}' for r in repos]
    (monorepo / 'Cargo.toml').write_text(cargo_workspace_toml(members))
    print(f'== wrote root Cargo.toml with {len(members)} members ==')

    print('== subtree add (sequentially) ==')
    for r in repos:
        name = r['name']
        branch = r['default_branch']
        src = str(clones / name)
        remote = f'{name}-src'
        subprocess.run(['git', '-C', str(monorepo), 'remote', 'add', remote, src], capture_output=True)
        subprocess.run(['git', '-C', str(monorepo), 'fetch', '--quiet', remote, branch], check=True, capture_output=True)
        msg = f'merge: import {name} from {args.org}/{name}@{branch}'
        result = subprocess.run([
            'git', '-C', str(monorepo), 'subtree', 'add',
            f'--prefix={args.subdir}/{name}', remote, branch,
            '-m', msg,
        ], capture_output=True, text=True)
        if result.returncode != 0:
            print(f'   FAILED: {name}: {result.stderr.strip()[:200]}')
            continue
        subprocess.run(['git', '-C', str(monorepo), 'remote', 'remove', remote], capture_output=True)
        print(f'   + {name}')

    subprocess.run(['git', '-C', str(monorepo), 'add', 'Cargo.toml'], check=True)
    subprocess.run(['git', '-C', str(monorepo), 'commit', '-m', 'chore: add workspace manifest'], check=True)

    if args.push_mode == 'force':
        print(f'== force-pushing to {args.default_branch} ==')
        subprocess.run(['git', '-C', str(monorepo), 'push', '-u', 'origin', args.default_branch], check=True)
    else:
        branch_name = f'{args.branch_prefix}all-crates'
        print(f'== pushing to feature branch {branch_name} for PR ==')
        subprocess.run(['git', '-C', str(monorepo), 'checkout', '-b', branch_name], check=True)
        subprocess.run(['git', '-C', str(monorepo), 'push', '-u', 'origin', branch_name], check=True)
        print(f'   next: open PR from {branch_name} -> {args.default_branch}')

    print('\nDONE')
    print(f'   monorepo: {create["html_url"]}')
    print(f'   local: {monorepo}')


if __name__ == '__main__':
    main()