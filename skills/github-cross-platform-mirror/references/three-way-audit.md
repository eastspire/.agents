# Three-way SHA audit (GitHub ↔ gitee ↔ gitcode)

Run after every batch deploy (and after manual retries) to confirm all three
platforms have the same HEAD on the default branch. Anything not matching needs
investigation before declaring done — a SHA mismatch means either the push
silently failed or the platform's `default_branch` was set to a non-master
branch (the API `/commits?per_page=1` returns the default branch's tip, not
master's tip, so the SHA differs even when the push worked).

## Script

```python
import json, subprocess, time

# Read each host's credential from git's own helper — no local path, no hardcoded token.
def token_for(host):
    out = subprocess.run(['git', 'credential', 'fill'],
                         input=f'protocol=https\nhost={host}\n\n',
                         capture_output=True, text=True)
    return dict(l.split('=', 1) for l in out.stdout.splitlines() if '=' in l).get('password')

GH_TOKEN = token_for('github.com')
GITEE    = "<gitee_token>"
GITCODE  = "<gitcode_token>"

def safe_curl(url, headers=None, retries=5, timeout=12):
    cmd = ["curl", "-sS", "-L", "--max-time", str(timeout)]
    if headers:
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    for _ in range(retries):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+3)
            return r.stdout
        except subprocess.TimeoutExpired:
            time.sleep(1.5)
            continue
    return None

def gh_head(repo):
    r = safe_curl(f"https://api.github.com/repos/{repo}/commits?per_page=1",
                  headers={"Authorization": f"Bearer {GH_TOKEN}"})
    if r:
        try:
            j = json.loads(r)
            if isinstance(j, list) and j:
                return j[0]["sha"][:10]
        except Exception:
            pass
    return "?"

def gitee_top(name):
    r = safe_curl(f"https://gitee.com/api/v5/repos/{NS}/{name}/commits?access_token={GITEE}&per_page=1")
    if r:
        try:
            j = json.loads(r)
            if isinstance(j, list) and j:
                return j[0]["sha"][:10]
        except Exception:
            pass
    return "?"

def gitcode_top(name):
    r = safe_curl(f"https://gitcode.com/api/v5/repos/{NS}/{name}/commits?access_token={GITCODE}&per_page=1")
    if r:
        try:
            j = json.loads(r)
            if isinstance(j, list) and j:
                return j[0]["sha"][:10]
        except Exception:
            pass
    return "?"

NS = "<target namespace, e.g. eastspire>"
results = []
for repo in REPO_LIST:
    src_owner, name = repo.split("/", 1)
    gh = gh_head(repo)
    g  = gitee_top(name)
    c  = gitcode_top(name)
    match = "✓" if (gh == g == c and gh != "?") else "✗"
    results.append((repo, gh, g, c, match))

print(f"{'REPO':45} {'GitHub':10} {'gitee':10} {'gitcode':10} {'match':5}")
print("-" * 85)
for r in results:
    print(f"{r[0]:45} {r[1]:10} {r[2]:10} {r[3]:10} {r[4]:5}")

with open("mirror-audit.json", "w") as f:
    json.dump([{"repo": r[0], "github": r[1], "gitee": r[2],
                "gitcode": r[3], "match": r[4]} for r in results], f, indent=2)

matched = sum(1 for r in results if r[4] == "✓")
print(f"\n{matched}/{len(results)} three-way consistent")
```

## Reading a mismatch

`?` in any column: the API call timed out (5 retries exhausted). Re-run; if it
persists, the platform's API is degraded or the token lost scope.

A specific mismatch where GitHub matches gitee but not gitcode (or vice versa):
- The platform's `default_branch` is set to a feature branch. Fix with
  `PATCH /repos/{ns}/{name}` setting `default_branch: "master"` and re-audit.
- The push genuinely failed on that side. Check the Actions log for the run.

A specific mismatch where GitHub differs from both gitee and gitcode:
- Someone pushed to GitHub after the audit baseline. Re-run the audit; do
  nothing if it's a fresh push that the workflow hasn't seen yet (wait 30 s and
  re-run).

A match where gitee matches gitcode but both differ from GitHub:
- Both platforms got pushed to at the same earlier commit (e.g. mid-batch)
  and a new GitHub commit happened after. Wait and re-audit.

## Save per-run

Each audit run overwrites `mirror-audit.json` in the working directory. To
keep history, copy it to `mirror-audit-YYYYMMDD-HHMMSS.json` before re-running
on a different repo set.