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

## When the stale PR is superseded — extract unique files, drop the conflict

A different pattern from stacked PRs: an open PR sat unmerged while *another PR* that covered the same files landed first. The stale branch now has `mergeable=False` with `mergeable_state=dirty` because every overlapping file conflicts against master. The naive fix is "rebase + resolve N conflicts" — but that's wrong. The right move is to recognize that master already has the newer / correct / authoritative version of every overlapping file, and the only useful content in the stale branch is what master does NOT have.

**Tell**: `GET /repos/<o>/<r>/pulls/<N>` returns `mergeable=False`, `mergeable_state=dirty`, AND the PR has many overlapping files with recent merged PRs into master.

**Procedure:**

1. **Inventory the stale branch's file set vs master.** Run on each side:
   ```bash
   git ls-tree -r --name-only <stale-branch> <scope> | sort > /tmp/stale.txt
   git ls-tree -r --name-only <default>      <scope> | sort > /tmp/master.txt
   diff /tmp/stale.txt /tmp/master.txt
   ```
   The files that appear ONLY in `stale.txt` are the unique-content candidates. Line-count diffs (`wc -l`) on shared files flag which side is more authoritative (usually the larger = the version that absorbed the others' work).

2. **Compare overlapping files line-by-line** to confirm master is the authoritative version. Read 1-2 overlapping files and check: does master's version have newer commit messages referenced in the file header / later timestamps / more pitfall entries? If yes, master wins for every overlapping file — no need to merge the content.

3. **Extract only the unique files onto master:**
   ```bash
   git checkout <default>
   git checkout <stale-branch> -- \
     <unique-file-1> <unique-file-2> <unique-file-3>
   git status   # confirm only those files staged
   ```
   **Do NOT checkout overlapping files** — they conflict and master already has the right version.

4. **Verify each unique file actually loads/runs.** If a unique file is a script (`*.py` / `*.sh`), run it once with `--help` or against a sample target to confirm it doesn't depend on an older companion script that master has since refactored. Verified 2026-09-26: `fix_dep_order.py` from a stale branch depended on `verify_dep_order._entry_chars` attribute that master's simplified `verify_dep_order.py` no longer exported → `AttributeError` at import → file unusable. **Auto-fixers can silently break when their companion verifier gets simplified**; check the verifier's public attribute list before committing the fixer.

5. **Commit + push + close the stale PR + delete its branch.**
   ```bash
   git add <unique-files>
   git commit -m "chore(<scope>): bring in <PR> unique files (<list>)..."
   git push origin <default>
   # Close the PR via REST (state=closed, merged=false — direct-commit superseded merge)
   curl -X PATCH -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/<o>/<r>/pulls/<N> \
        -d '{"state":"closed"}'
   # Delete the branch
   curl -X DELETE -H "Authorization: token $TOKEN" \
        https://api.github.com/repos/<o>/<r>/git/refs/heads/<branch>
   git fetch origin --prune
   git branch -D <stale-branch>
   ```

**Why this beats "resolve all the conflicts":** A stale PR with `mergeable_state=dirty` and 18 conflicting files is rarely worth 18 file-by-file conflict resolutions — every overlapping file's right side is on master already. The cost of resolution is `O(conflicts × lines)`, the cost of extract-and-discard is `O(unique files)`, which is usually < 5. The procedure preserves every piece of unique work from the stale branch while avoiding any risk of overwriting master's authoritative version.

**Anti-pattern:** "I can resolve all 18 conflicts file-by-file" — when master is the authoritative state for every overlapping file, manual conflict resolution is pure busywork. Resolve only when master is wrong or when both sides add legitimately new content to the same anchor.

## Auto-fixers break when their companion verifier changes

Verified 2026-09-26: a stale branch's `fix_dep_order.py` imported a private attribute `_entry_chars` from `verify_dep_order.py`. Master had simplified `verify_dep_order.py` and removed that attribute. Importing the fixer raised `AttributeError` at module load — every call to the fixer failed before reaching the dep-order logic.

**Rule:** Before checking out a fixer from a stale branch, sanity-test it against the verifier that's now in master:

```bash
python3 -c "import importlib.util, sys
spec = importlib.util.spec_from_file_location('vd', 'master-path/verify_X.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print([n for n in dir(m) if not n.startswith('__')])
" | grep -q '<attribute-the-fixer-needs>' \
  || { echo "FATAL: verifier public API changed; fixer will AttributeError"; exit 1; }
```

If the verifier's public surface has changed since the fixer was authored, **drop the fixer** (the verifier is still in master and still works; users can manually apply edits). Don't try to port the fixer forward — its logic is usually coupled to the old verifier's parse output in ways that aren't visible from outside.

## After the rebase lands — validation checklist

1. `cargo check --workspace` (or whatever your build is) — the rebase can introduce subtle issues if upstream renamed identifiers your branch referenced.
3. Run your existing audit/format scripts — layer-3 / layer-4 commits in stacked-PR setups almost always produce the same diff against the rebased tree, so audits pass with the same numbers as before rebase.
4. Force-push with `--force-with-lease` (see above).
5. Update PR body via REST API (see above) to reflect the new base SHA.
6. `mergeable_state` from `GET /repos/<o>/<r>/pulls/<N>` should be `"clean"` before requesting review.

## Related

- `references/gfw-throttled-github-fetch.md` — when rebase also requires fresh data from a throttled host.
- SKILL.md `Pitfalls` section — main entry point; this reference is the deep dive on one specific pitfall class.