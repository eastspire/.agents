---
name: docs-github-url-audit
description: Audit + fix stale github URLs across multi-repo docs sites.
license: MIT
metadata:
  hermes:
    tags: [github, docs, url-audit, monorepo, readme, crates.io]
    related_skills: [gh-pr-creation-workflow, euv-docs-contribution, docs-pages-docs-contribution, rust-crate-use]
---

# Docs GitHub URL Audit

Bulk-audit github URLs across a docs site (README.md, badges, source files), classify each as EXISTS / MERGED / DELETED / AMBIGUOUS using multi-source API verification, then apply targeted fixes that respect both the docs site layout and the upstream repo topology.

## When to Use

- A multi-repo docs site (e.g. `docs-pages/docs`, `euv-docs`, an org-level docs site) has many `https://github.com/<org>/<repo>` URLs that the user reports are stale ("仓库已经移动或者删除了").
- A monorepo consolidation (`git-subtree-monorepo-merge` style) was just performed and downstream docs still reference the old per-crate repos.
- README templates use a fixed `GITHUB 地址` link + `workflows/Rust/badge.svg` + `actions?query=workflow=Rust` triple pattern (very common for Rust crate docs sites) and all three need to be remapped together.
- The user asks for "audit + 真实验证" / "确认真实正确的" / "verify with API, not from memory".

## Don't Use For

- Single-crate README updates where the user already knows the new URL — just edit, no audit needed.
- README content rewrites (prose, structure) — this skill is URL-only.
- `git-subtree-monorepo-merge` — that skill is the **source side** (importing repos into a monorepo). This skill is the **docs side** (updating docs that referenced the old per-crate repos after a merge).
- Marking old repos as archived — that's `git-subtree-monorepo-merge` Phase 7.

## Procedure

### Step 1 — Discover every URL worth checking

Walk the docs tree and extract every `github.com/<org>/<repo>` reference. Don't trust any single extension — many docs sites mix `.md`, `.html`, `.yml`, `.json`, `.toml`, `.sh` and config files like `build.sh` / `.github/workflows/*.yml` also reference repos.

```python
import os, re
from collections import defaultdict

ROOT = '<docs-site-root>'
gh_pattern = re.compile(
    r'github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)'
    r'(?:[/#?"\')\s.,;\]}>]|$)'
)

repos = defaultdict(set)
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in ('.git', 'dist', 'node_modules', '.deploy', '__docs_pages')]
    for f in files:
        if not f.endswith(('.md', '.yml', '.yaml', '.toml', '.json', '.html', '.sh')):
            continue
        path = os.path.join(base, f)
        try:
            text = open(path, errors='ignore').read()
        except Exception:
            continue
        for m in gh_pattern.finditer(text):
            org, repo = m.group(1), m.group(2)
            if org in ('sponsors', 'settings', 'notifications', 'orgs', 'users', 'search', 'marketplace'):
                continue
            if repo.endswith('.git'):
                repo = repo[:-4]
            repos[f"{org}/{repo}"].add(path)
```

Completion criterion: a unique list of `<org>/<repo>` strings with the files that reference each.

### Step 2 — Multi-source verification (NEVER trust memory)

For every distinct `<org>/<repo>` reference, verify against authoritative sources. Don't trust the URL in the README; don't trust your own knowledge of what was merged where. Verify.

**Source A — GitHub REST API** (direct existence check):

```python
import urllib.request, urllib.error, json
url = f'https://api.github.com/repos/{org}/{repo}'
req = urllib.request.Request(url, headers={
    'Authorization': f'Bearer {token}',
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'docs-audit',
})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        # status: EXISTS
        # archived: bool (may be true even if URL resolves)
        # default_branch: str
except urllib.error.HTTPError as e:
    if e.code == 404: status = 'NOT_FOUND'
    elif e.code == 301: status = 'MOVED'; location = e.headers.get('Location')
    else: status = f'HTTP_{e.code}'
```

Token discovery: read `$GH_TOKEN` env, fall back to `git credential fill` for `github.com` (or `gh auth token`) — `github-pat-scope-check` skill is the canonical reference.

**Source B — crates.io API** (when the referenced repo is a Rust crate):

```python
# For docs sites that document crates by README frontmatter, the crates.io
# `repository` field is more authoritative than the README's own URL.
# crates.io URLs are kebab-case OR snake_case; try both against the
# directory name, the frontmatter crate name, AND the GitHub repo segment.
crate_name_candidates = [
    repo,                                    # as-is from URL
    repo.replace('-', '_'),                  # snake_case variant
    <crate-from-frontmatter>,                # if README has frontmatter
]
for cname in candidates:
    url = f'https://crates.io/api/v1/crates/{cname}'
    req = urllib.request.Request(url, headers={'User-Agent': 'docs-audit/1.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        repository = data['crate']['repository']   # e.g. "https://github.com/X/Y.git"
        # THIS is the authoritative destination repo
```

crates.io metadata is sometimes stale (the crate may have moved to a new monorepo AFTER the last publish), so always cross-check the resulting GitHub URL with Source A.

**Source C — the org's own repo list** (for "which monorepo absorbed X"):

```python
# Once you suspect a monorepo absorbed several per-crate repos, list the
# org's repos and check which still exist independently:
for repo in itertools.chain(suspected_independent, suspected_monorepo):
    url = f'https://api.github.com/repos/{org}/{repo}'
    # ... same pattern as Source A
```

Completion criterion: every distinct `<org>/<repo>` reference has a status (EXISTS / MERGED / DELETED / AMBIGUOUS) backed by at least one API response.

### Step 3 — Classify and pick the mapping

For each stale reference, classify into one of four buckets and decide the new URL:

| Status | Meaning | Action |
|---|---|---|
| EXISTS | GitHub returns 200 | Leave the URL alone (verify archived=false too) |
| MERGED — known destination | The repo was consolidated into a known monorepo (e.g. `crates-dev/ctares` absorbs 21 single crates; `hyperlane-dev/hyperlane` absorbs 6 hyperlane sub-crates) | Rewrite to the monorepo URL in ALL files referencing it |
| DELETED — no destination | crates.io 404 + GitHub 404 — the crate is gone from both | Preserve the URL, add a `> 注意：本项目仓库地址可能不再准确...` callout to the README; never invent a wrong URL |
| AMBIGUOUS — crate alive but source repo gone | crates.io returns 200 (crate still installable), but GitHub returns 404 (source repo archived/deleted) | Preserve the URL, add a Note callout pointing readers to crates.io/docs.rs as the source of truth |

**Don't** invent a destination repo URL when the destination is unknown. A wrong URL pointing at an unrelated repo is worse than a 404 — it silently leads readers away from the truth.

**Don't** auto-redirect via a URL shortener or wayback machine link either — those decay.

Completion criterion: every distinct `<org>/<repo>` has a target URL or an explicit "leave + annotate" decision with the reason recorded.

### Step 4 — Rewrite in THREE places per README, not one

Rust crate README templates almost always embed the github URL in three places that must move together:

```markdown
[GITHUB 地址](https://github.com/<org>/<repo>)                  ← main link, line 6-8

[![](.../workflows/Rust/badge.svg)](.../<org>/<repo>/workflows/Rust/badge.svg)    ← badge image src
[![](.../workflows/Rust/badge.svg)](.../<org>/<repo>/actions?query=workflow:Rust) ← badge link target
```

Always patch all three with the same new org/repo. Missing the badge URLs leaves dead links visible in the rendered badges (broken images + 404 links on click).

For non-Rust-ecosystem docs sites the URL pattern differs — adapt: still scan for `github.com/<org>/<repo>` everywhere it appears, but don't assume the three-line template.

**Watch for kebab vs snake case** in the URL segment itself. A single repo can have the URL written as `compare-version` (kebab) OR `compare_version` (snake) in different files / lines. Pattern-match against the frontmatter crate name AND the crates.io canonical name, NOT just the directory name.

```python
# When patching, search both forms in the same file:
for variant in [crate_kebab, crate_snake]:
    if old_url == f"github.com/{org}/{variant}":
        # also patch the other variant if it appears
```

Completion criterion: `grep -r '<old-url>' <docs-root>` returns zero hits after the patch.

### Step 5 — Annotate ambiguous cases consistently

For DELETED and AMBIGUOUS references, add a single callout (VuePress `> [!NOTE]`, euv-docs `> [!tip]`, GitHub `> NOTE:` — pick whatever the docs site already uses) right after the frontmatter block, BEFORE the existing `GITHUB 地址` link:

```markdown
---
title: hyperlane广播
---

> 注意：本项目仓库地址可能不再准确（hyperlane-dev/hyperlane-broadcast — github 仓库已 404，crates.io 仍可访问），请以 crates.io / docs.rs 上的信息为准。

[GITHUB 地址](https://github.com/hyperlane-dev/hyperlane-broadcast)
...
```

The callout goes between the frontmatter close (`---`) and the rest of the body. Don't bury it at the end of the README — readers won't see it before clicking the broken link.

Completion criterion: every ambiguous/dead README has exactly one callout, in the right place, with the URL/crate name written in the callout text.

### Step 6 — Commit + push via the site's own workflow

Different docs sites use different PR conventions:

- `euv-dev/euv-docs` — branch + PR + squash + delete-branch (single-track via `gh-pr-creation-workflow`)
- `docs-pages/docs` — direct push to master (admin-only, see `docs-pages-docs-contribution`)
- `docs-pages/docs-euv` — same as `euv-dev/euv-docs` workflow

Before committing, check the latest `git log --oneline -5` to confirm the local branch state matches the site's documented flow. Don't auto-merge — the user owns the merge decision.

## Verification

After the patch, run a final grep to prove nothing was missed:

```bash
# Should return zero results
grep -rn "github.com/<org>/<old-repo>" <docs-root>/ \
    --include='*.md' --include='*.yml' --include='*.json' --include='*.sh' --include='*.html' \
    --exclude-dir=dist --exclude-dir=__docs_pages --exclude-dir=.git
```

For each MERGED rewrite, verify the new URL also resolves:

```bash
for url in $(grep -oh 'github.com/[A-Za-z0-9_.-]*' <docs-root>/docs -r | sort -u); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "https://api.github.com/repos/${url#github.com/}")
    echo "$code $url"
done | sort
# All lines should start with 200
```

For ambiguous callouts, spot-check one file manually — read the callout, confirm the URL it warns about is actually still in the document (the callout is supposed to be next to the URL it's warning about, not somewhere unrelated).

## Pitfalls

- **Don't trust the URL in the README as truth.** Many README URLs are copy-paste from when the crate was first created and never updated. Treat them as hypotheses to verify, not facts.

- **Don't trust your memory of "what was merged where".** Even if you remember that `crates-dev/ctares` is a monorepo, you don't remember the exact list of 21 absorbed crates without checking. Verify via crates.io → `repository` field, then via GitHub API on the claimed monorepo.

- **Don't conflate "crate still published on crates.io" with "source repo still exists".** `hyperlane-broadcast` (max_stable 2.0.13) was still downloadable while its `github.com/hyperlane-dev/hyperlane-broadcast` repo was 404. The crates.io metadata field can lag the source deletion by months. Always cross-check both APIs.

- **Don't auto-merge after rewrite.** A wrong mapping silently sends readers to an unrelated repo. The user owns the merge decision; present the audit table first.

- **`grep` recursion must exclude `dist/`, `node_modules/`, `__docs_pages/`, `.git/`**. These directories contain stale build artifacts that look like real references but should not be edited. The standard `--exclude-dir` flags above cover the common cases.

- **Cargo workspace subdirs also reference the monorepo URL.** After `crates-dev/ctares` consolidation, every internal sub-crate's README likely still references the old per-crate URL. Walk the whole monorepo, not just the docs site — the workspace's own READMEs are part of the truth.

- **README badge URLs follow the main URL but with a different path.** `https://github.com/<org>/<repo>/workflows/Rust/badge.svg` and `https://github.com/<org>/<repo>/actions?query=workflow=Rust` are TWO additional URLs per README, often missed. When patching, search for both forms in addition to the main link.

- **Document the ambiguous cases in the audit report.** When the user asks "what was left behind", they'll want a clean table: which URLs were moved where, which were preserved + annotated, and why. Don't just say "I fixed what I could"; produce the table.

## References

- `references/api-recipes.md` — exact code blocks for GitHub REST API org/repo listing, crates.io API crate→repo resolution, and the multi-source verification table. Includes the GitHub `x-ratelimit-remaining: 0` failure mode and how to back off.
- `references/audit-report-template.md` — markdown table template for presenting the audit to the user. Columns: original URL, status (EXISTS / MERGED / DELETED / AMBIGUOUS), new URL, files affected, reason. Sorted by status, then alphabetically by original URL.
