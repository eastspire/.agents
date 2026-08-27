# Stacked PR Rebase Conflict Resolution

When your PR sits on a base branch that gets a merge from a "step 1" PR while your branch is open, you get massive conflict overlap. This reference documents the diagnosis, the conflict pattern, and a deterministic rebase resolver for the common case.

## When this happens

Classic three-step pattern that triggers it:
1. You open PR-A at commit `X` doing **step N** of a planned series.
2. While PR-A is open, the user merges PR-A-step-1 (commit `Y`, based on the same `X`).
3. You open PR-A-step-2 (your "step N+1") on top of `X`, but the merge moves master to `Y` (now containing `Y`'s content).
4. PR-A is still open, **based on `X`** — its diffs overlap with `Y` for the same files.

Concretely this session saw:
- PR #23 (commit `9cd81ee`) merged at 03:12 UTC, adding single-line `///` to 161 fns.
- PR #24 (commits `df0a745` + `41da42e` + `e58d9dd`) was created at 03:29 UTC **based on `13193d2`** — pre-#23.
- PR #24's layer-3 commit tried to insert `# Arguments` / `# Returns` sections immediately below `///` lines that **didn't exist yet** on PR #24's base, but **already existed** on master after #23 merge.

Result: 41 files conflicted, 140 conflict hunks, all the same shape.

## Conflict pattern (the §2.2 doc-comment case)

PR #23 already added: `/// brief line` (one line, no newline after).

PR #24 wanted to add right below:
```
///
/// # Arguments
///
/// - `X` - desc.
/// - `Y` - desc.
///
/// # Returns
///
/// - `Type`: desc.
```

The merge conflict in `<<<<<<< HEAD` `=======` `>>>>>>>` shape:

```
<<<<<<< HEAD                                       (= master with PR #23 merged)
/// brief line                                      (= PR #23 added)
=======
///                                                 (= blank `///` line)
/// # Arguments                                    (= PR #24's section header)
/// - `X` - desc.
/// ...
>>>>>>> df0a745 (...)
```

**Resolution rule**: keep HEAD's `/// brief line` and append PR #24's section block **without** PR #24's leading `///` (blank `///` line is already implicit at the brief's tail):

```python
def resolve_one(head: str, pr24: str) -> str:
    if pr24.startswith("///\n"):
        pr24 = pr24[len("///\n"):]   # drop the redundant blank `///`
    return head + pr24
```

Result is `/// brief\n///\n/// # Arguments\n...` — exactly the §2.2 template the docs are trying to reach.

## Generic rebase resolver (re-runnable)

`/tmp/resolve_rebase_conflict.py` — a deterministic, file-by-file conflict matcher for this exact pattern. Works because (a) the conflict format is stable and (b) every conflict in the layer-3 commit followed the same shape:

```python
import re, subprocess

CONFLICT_RE = re.compile(
    r"<<<<<<< HEAD\n"
    r"(.*?)"
    r"=======\n"
    r"(.*?)"
    r">>>>>>> df0a745[^\n]*\n",
    re.DOTALL,
)

def resolve_conflict(text):
    return CONFLICT_RE.subn(
        lambda m: m.group(1) + (m.group(2).lstrip("///\n") if m.group(2).startswith("///\n") else m.group(2)),
        text,
    )

for f in subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], capture_output=True, text=True).stdout.splitlines():
    p = "/path/to/repo/" + f
    txt = open(p).read()
    new, n = resolve_conflict(txt)
    if n:
        open(p, "w").write(new)
        print(f"{f}: {n} conflict(s) resolved")
```

Adapt to:
- Different upstream commit SHA → swap `df0a745` in `CONFLICT_RE` and the leading `///\n` strip logic for whatever the layer-3 commit produced.
- Different conflict shape → see "If your conflict looks different" below.

## The whole sequence in one block

```bash
# 1. Confirm master moved
git fetch origin
git log --oneline origin/master -5

# 2. Identify what the new commits on master are (so you know what conflicts are coming)
git diff <your-pr-base-sha>..origin/master --stat

# 3. Begin rebase
git rebase origin/master
# Expect: "Auto-merging ..." for some files, "CONFLICT (content)" for the rest.

# 4. Apply the conflict resolver
python3 /tmp/resolve_rebase_conflict.py   # or your equivalent
git add -u

# 5. Continue. If the rebase is in a TTY-less environment (Hermes agent shells),
#    force the editor to no-op so git uses the original commit message:
GIT_EDITOR=true git rebase --continue
```

## `git push --force-with-lease` "stale info" rejection

After rebase, `--force-with-lease` may be rejected with **"stale info"** even when you've freshly fetched. Cause: the local branch's `branch.<name>.merge` ref-store still tracks the **pre-rebase** remote SHA, so the lease check fails.

Fix:

```bash
# Refresh the local copy of the remote-tracking ref explicitly
git fetch origin +refs/heads/<your-branch>:refs/remotes/origin/<your-branch>
git push --force-with-lease origin <your-branch>
# If that still rejects, fall back to:
git push --force origin <your-branch>
```

Use `--force-with-lease` whenever you can — it's a small safety net against clobbering a teammate's force-push that landed in the gap. Only fall back to `--force` when the lease is stale due to your own rebase.

## `gh pr edit` fails with `read:org` scope

`gh pr edit N --body-file ...` (and `gh pr view N --json ...`) requires the GraphQL `read:org` (and `read:discussion` for comment lists) scopes. If the user's token only has `notifications`/`repo`/`workflow`, GraphQL endpoints reject the query with `"Your token has not been granted the required scopes"`.

**Fallback** — REST API works with the same token:

```python
import urllib.request, json, os

req = urllib.request.Request(
    "https://api.github.com/repos/<owner>/<repo>/pulls/<N>",
    method="PATCH",
    data=json.dumps({"body": body_text}).encode(),
    headers={
        "Authorization": "Bearer " + os.environ["GH_TOKEN"],
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    },
)
data = json.loads(urllib.request.urlopen(req).read())
```

Update fields via `{"body": "..."}` for body, `{"state": "closed"}` to close, `{"title": "..."}` for title.

## If your conflict looks different

The §2.2-double-doc pattern is one shape. Other stacked-PR patterns you'll see:

| Conflict shape | Resolution |
|----------------|------------|
| Both sides add different new lines at the same anchor | take both — concatenate HEAD-side and incoming-side blocks, then manually dedupe identical lines |
| HEAD rewrote a function body, incoming only added a doc | take HEAD's body; merge incoming's doc lines (run `git diff --theirs -- path/to/file` to see exactly what they added) |
| HEAD removed a file, incoming modified it | take HEAD's removal — `git rm` the file, then `git rebase --continue` |
| HEAD moved code into a new module, incoming patched the old location | move the patch to the new module by hand — the resolver script can't help here |

Always check with `git diff --theirs -- <file>` and `git diff --ours -- <file>` to see exactly which lines came from which side before resolving.

## After the rebase lands — validation checklist

1. `cargo check --workspace` (or whatever your build is) — the rebase can introduce subtle issues if upstream renamed identifiers your branch referenced.
3. Run your existing audit/format scripts — layer-3 / layer-4 commits in stacked-PR setups almost always produce the same diff against the rebased tree, so audits pass with the same numbers as before rebase.
4. Force-push with `--force-with-lease` (see above).
5. Update PR body via REST API (see above) to reflect the new base SHA.
6. `mergeable_state` from `GET /repos/<o>/<r>/pulls/<N>` should be `"clean"` before requesting review.

## Related

- `references/gfw-throttled-github-fetch.md` — when rebase also requires fresh data from a throttled host.
- SKILL.md `Pitfalls` section — main entry point; this reference is the deep dive on one specific pitfall class.