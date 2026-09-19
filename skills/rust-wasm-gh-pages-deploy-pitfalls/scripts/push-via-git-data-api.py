#!/usr/bin/env python3
"""Push a local directory's file tree to a GitHub repo branch via Git Data API.

Bypasses GFW HTTPS git push handshake (135s timeout typical) and SSH agent
requirements. Use when:
- SSH key not in ssh-agent / not configured for target repo
- `git push origin <branch>` hangs 30+ seconds in network handshake
- Source dir is 50MB+ (large repos where clone also hangs)
- Want atomic multi-file commit without local git clone

Equivalent to:
  git init && git add -A && git commit -m "..." && git push origin <branch>

But via API: Blobs → Tree → Commit → Ref update. All changes in ONE commit.

Usage:
  export GH_TOKEN=ghp_xxx     # or source /root/.bashrc.d/gh_token.sh
  python3 push-via-git-data-api.py \
    --src /root/<local-repo> \
    --repo <owner>/<name> \
    --branch master \
    --base-tree <optional: commit sha to base from> \
    --message "chore: initial commit"

If --base-tree omitted, auto-fetches HEAD of --branch from remote. Pass
explicit sha to base on a different commit (e.g. when forking an existing repo).

Output:
  Pushes one commit, advances --branch ref. Run from a terminal that stays
  alive for ~5 minutes for 300-file trees.

Pitfalls:
- Sequential POST per file is slow (~1 req/sec). 1000 files = 15+ minutes.
- For >1000 files: chunk into multiple commits or use Contents API per file
  (slower per-file but parallel-friendly via async).
- Token must have `repo` scope; `public_repo` only works for public repos.
- `Cargo.lock` is auto-skipped if --skip-pattern is unset (typical case:
  Rust projects gitignore it).
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"


def get_token():
    tok = os.environ.get("GH_TOKEN")
    if tok:
        return tok.strip()
    r = subprocess.run(
        ["bash", "-c", "source /root/.bashrc.d/gh_token.sh && echo $GH_TOKEN"],
        capture_output=True, text=True,
    )
    return r.stdout.strip()


def req(method, path, body=None, token=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "docs-euv-push-fix",
    }
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode()
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                wait = int(e.headers.get("Retry-After", "5"))
                time.sleep(wait)
                continue
            print(f"HTTP {e.code} on {method} {path}: {body_text[:500]}", file=sys.stderr)
            raise


def collect_files(src_dir, skip_dirs=None, skip_patterns=None):
    """Walk src_dir, return relative paths in forward-slash form."""
    skip_dirs = set(skip_dirs or {".git", "target", "node_modules", "__pycache__", "www"})
    skip_patterns = skip_patterns or ["Cargo.lock"]
    files = []
    for root, dirs, fs in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        if any(part in skip_dirs for part in rel.split(os.sep)):
            continue
        for f in fs:
            full = os.path.join(root, f)
            rel_path = os.path.relpath(full, src_dir).replace(os.sep, "/")
            if any(rel_path == p or rel_path.endswith("/" + p) for p in skip_patterns):
                continue
            files.append(rel_path)
    files.sort()
    return files


def create_blob(path, token):
    with open(path, "rb") as fh:
        data = fh.read()
    # Heuristic: if file has null bytes in first 8KB, treat as binary
    if b"\x00" in data[:8000]:
        encoded = base64.b64encode(data).decode("ascii")
        return req("POST", f"/repos/{REPO}/git/blobs",
                   {"content": encoded, "encoding": "base64"}, token)["sha"]
    try:
        text = data.decode("utf-8")
        return req("POST", f"/repos/{REPO}/git/blobs",
                   {"content": text, "encoding": "utf-8"}, token)["sha"]
    except UnicodeDecodeError:
        encoded = base64.b64encode(data).decode("ascii")
        return req("POST", f"/repos/{REPO}/git/blobs",
                   {"content": encoded, "encoding": "base64"}, token)["sha"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", required=True, help="local source dir")
    p.add_argument("--repo", required=True, help="owner/name")
    p.add_argument("--branch", default="master")
    p.add_argument("--base-tree", default=None,
                   help="commit sha to base tree from (default: HEAD of branch)")
    p.add_argument("--message", default="chore: push via git data API")
    p.add_argument("--skip-dirs", nargs="*", default=None,
                   help="dir names to skip (default: .git, target, node_modules, __pycache__, www)")
    p.add_argument("--skip-patterns", nargs="*", default=None,
                   help="file path patterns to skip (default: Cargo.lock)")
    args = p.parse_args()

    global REPO
    REPO = args.repo
    token = get_token()
    if not token:
        sys.exit("GH_TOKEN not set")

    files = collect_files(args.src, args.skip_dirs, args.skip_patterns)
    print(f"files to push: {len(files)}", flush=True)

    # Get HEAD of branch
    if args.base_tree:
        base_commit_sha = args.base_tree
    else:
        try:
            ref = req("GET", f"/repos/{REPO}/git/refs/heads/{args.branch}", token=token)
            base_commit_sha = ref["object"]["sha"]
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            base_commit_sha = None

    base_tree = None
    if base_commit_sha:
        bc = req("GET", f"/repos/{REPO}/git/commits/{base_commit_sha}", token=token)
        base_tree = bc["tree"]["sha"]
        print(f"base commit: {base_commit_sha[:8]}, base tree: {base_tree[:8]}", flush=True)
    else:
        print(f"branch {args.branch} does not exist; creating initial commit", flush=True)

    # Upload blobs
    tree_entries = []
    total_size = 0
    for i, rel in enumerate(files):
        full = os.path.join(args.src, rel)
        total_size += os.path.getsize(full)
        sha = create_blob(full, token)
        tree_entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": sha})
        if (i + 1) % 20 == 0 or (i + 1) == len(files):
            print(f"  uploaded {i+1}/{len(files)} (cumulative {total_size//1024} KB)",
                  flush=True)

    # Create tree
    tree_body = {"tree": tree_entries}
    if base_tree:
        tree_body["base_tree"] = base_tree
    new_tree = req("POST", f"/repos/{REPO}/git/trees", tree_body, token)
    print(f"new tree: {new_tree['sha'][:8]}", flush=True)

    # Create commit
    commit_body = {
        "message": args.message,
        "tree": new_tree["sha"],
    }
    if base_commit_sha:
        commit_body["parents"] = [base_commit_sha]
    new_commit = req("POST", f"/repos/{REPO}/git/commits", commit_body, token)
    print(f"new commit: {new_commit['sha'][:8]}", flush=True)

    # Update ref
    if base_commit_sha:
        req("PATCH", f"/repos/{REPO}/git/refs/heads/{args.branch}",
            {"sha": new_commit["sha"]}, token)
    else:
        req("POST", f"/repos/{REPO}/git/refs",
            {"ref": f"refs/heads/{args.branch}", "sha": new_commit["sha"]}, token)
    print("done!", flush=True)


if __name__ == "__main__":
    main()