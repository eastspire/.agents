---
name: git-standards
description: 'Git commit + PR conventions for eastspire/.agents skill repo. **All commits and PR descriptions must be written in English** (no Chinese in commit message subject/body, no Chinese in PR title/body, per user preference). Commit subject MUST follow Conventional Commits v1.0.0: `<type>(<scope>): <subject>` where type ∈ {feat, fix, refactor, perf, docs, test, build, ci, chore, style, revert} and scope is the skill name (singular or short area). Subject ≤ 72 chars, imperative mood, no trailing period, no all-caps. Body wrapped at 72 cols, explain *what* and *why* not *how*, use bullet lists for multi-point changes. PR body uses 4-section template: Summary / Changes / Verification / Notes. Footer MUST include `🤖 Generated with [Hermes](https://...)` line (drop if not applicable). Triggers: git commit, commit message, PR body, PR description, Conventional Commits, git push, gh pr create, commit prefix, commit type, chore:, feat:, fix:, refactor:, docs:, ci:.'
license: MIT
---
# git-standards — English-only commit + PR conventions

> **Hard rule: all commit subjects, commit bodies, PR titles, and PR bodies MUST be in English.** No Chinese characters. No bilingual mix. Even when discussing Chinese-source material, the commit/PR text is English.

## 1. Commit message format (Conventional Commits v1.0.0)

```
<type>(<scope>): <subject>

<body wrapped at 72 cols>

<footer>
```

### 1.1 `type` (required, lowercase, one of)

| type | when to use |
|---|---|
| `feat` | new feature, new skill, new command, new public API |
| `fix` | bug fix in code, docs, or config (NOT refactor) |
| `refactor` | restructuring code without changing behavior (split skill, rename, restructure) |
| `perf` | performance improvement |
| `docs` | docs-only change (README, comments) |
| `test` | add or fix tests |
| `build` | build system or external deps (Cargo.toml, package.json, Dockerfile) |
| `ci` | CI config (.github/workflows, hooks) |
| `chore` | maintenance, deps update, tooling, no src/prod code change |
| `style` | formatting only (whitespace, semicolons) — prefer `refactor` if it changes structure |
| `revert` | revert a previous commit |

### 1.2 `scope` (optional but recommended)

- Prefer the **skill name** if change is scoped to one skill: `euv`, `euv-standards`, `hyperlane`, `hyperlane-standards`, `rust-standards`, `git-standards`
- Use a short area: `skills`, `references`, `scripts`, `templates`, `docs`, `ci`
- Skip scope if change is repo-wide

### 1.3 `subject`

- ≤ 72 characters (hard limit)
- Imperative mood: "add", not "added" or "adds"
- Lowercase first letter (after the type/scope)
- No trailing period
- No all-caps words (acronyms OK: `WASM`, `CI`, `HTTP`)
- No "WIP" / "draft" in committed message (use draft PR instead)

### 1.4 `body`

- Blank line after subject (required)
- Wrap at 72 columns
- Explain **what** and **why**, not **how**
- Use `-` bullet lists for multi-point changes
- Reference related issues/PRs: `Refs #123`, `Closes #456`

### 1.5 `footer`

- `BREAKING CHANGE: <description>` for breaking changes (also allowed after `!`: `feat(api)!: remove v1 endpoint`)
- `Refs #<num>` / `Closes #<num>` / `Fixes #<num>`
- `🤖 Generated with [Hermes](...)` — optional, only when AI-assisted

### 1.6 Examples

✅ good:
```
feat(hyperlane-standards): add full Server/Context/Hook API cheatsheet
```
```
refactor(skills): rewire euv and hyperlane skills into mutual-lock entry chain

Restructure the euv and hyperlane skill groups so any euv or hyperlane
task automatically loads the corresponding standards skill (euv-standards
or hyperlane-standards) and the UI standards skill (euv-ui-standards) when
UI work is in scope.

- euv: description now forces loading of euv-standards and euv-ui-standards
- euv-standards: expand trigger keywords to cover full framework API
- euv-ui-standards: expand trigger keywords for class!, design tokens,
  page templates, and example routes
- hyperlane: description now forces loading of hyperlane-standards
- hyperlane-standards: new skill, extracted from hyperlane/SKILL.md
- rust-standards: add euv, hyperlane, html!, class!, ServerHook, Signal,
  tokio, wasm-pack as strong trigger keywords

Refs #4
```

❌ bad (Chinese in subject/body):
```
refactor(skills): 把 euv/hyperlane 改成互锁入口链
```
❌ bad (no type, no scope):
```
update skills
```
❌ bad (subject too long, trailing period):
```
feat(hyperlane-standards): add the full Server/Context/Hook/Route/Config API cheatsheet with 22 common pitfalls and 7 ecosystem crates covered in this new skill.
```

## 2. PR title + body (English only)

### 2.1 Title

- Same format as commit subject: `<type>(<scope>): <subject>`
- Keep ≤ 72 chars
- For multi-commit PRs, the title summarizes the whole PR, not just head commit

### 2.2 Body template (4 sections, in this order)

```markdown
## Summary
<1-3 sentences describing the overall change>

## Changes
- `<file>`: <what changed>
- `<file>`: <what changed>
- new: `<path>` — <what it is>

## Verification
- [ ] <how you verified, e.g. frontmatter parses, scripts run, tests pass>
- [ ] <second verification step>

## Notes
<design trade-offs, follow-up work, migration steps, anything reviewers need to know>
```

### 2.3 Style rules

- **All English** — no Chinese, no emoji-only, no bilingual mix
- Bullet lists, not prose paragraphs
- Code blocks use `path/to/file.rs` or `command --flag` format
- Reference issues/PRs with `Refs #N` / `Closes #N` / `Fixes #N`
- Do NOT ping reviewers (`@user`); maintainers opt in themselves
- Do NOT add "happy to address feedback" or "let me know" filler
- Do NOT use marketing language ("revolutionary", "blazing fast")

## 3. End-to-end workflow (gh CLI)

### 3.1 Pre-commit cleanup
```bash
cd ~/.agents/skills
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
```

### 3.2 Commit
```bash
git add -A
git commit -m "<type>(<scope>): <subject>" \
           -m "<body line 1>" \
           -m "<body line 2>" \
           -m "" \
           -m "<footer>"
# Or use a temp file for long messages
git commit -F /tmp/commit-msg.txt
```

### 3.3 Push + open PR
```bash
git push -u origin <branch>

gh pr create \
  --title "<type>(<scope>): <subject>" \
  --body "$(cat <<'EOF'
## Summary
...

## Changes
- ...

## Verification
- [ ] ...

## Notes
...
EOF
)" \
  --base master \
  --head <branch>
```

### 3.4 After PR is open
- Do NOT add "ping" or "bump" comments
- Do NOT add "ready for review" comment
- Just stop. Wait for maintainer.

## 4. Common pitfalls

1. **Chinese in commit body** — auto-fail. Rewrite in English. Use technical terms (e.g. "mutual-lock chain", "trigger keywords", "frontmatter") not literal translation.
2. **Subject over 72 chars** — `git log --oneline` will truncate it; reviewers see a half-sentence.
3. **Subject with trailing period** — not a hard error but inconsistent with Angular/Karma convention.
4. **Type `update` / `change` / `modify`** — not in Conventional Commits; use `feat` / `fix` / `refactor` / `chore`.
5. **Scope = file path** — scope is a logical area, not a file path. `feat(skills)` not `feat(skills/euv-standards/SKILL.md)`.
6. **PR body via echo / printf** — use `cat <<'EOF'` with single-quoted EOF to prevent `$` and backtick expansion. Without `<<'EOF'`, the shell will eat `${VAR}` in body text.
7. **Forgetting `--base master`** — `gh pr create` defaults to the default branch, but on personal repos with `main` as default this matters. Always pass `--base` explicitly.
8. **Force-pushing after review** — never `git push --force` after a PR has comments; use `--force-with-lease` and only when amending a commit before any review.
9. **Auto-merging own PR or merging before user confirms** — never `gh pr merge --auto`, `gh pr merge --squash`, or `enablePullRequestAutoMerge` unless the user has just typed "merge it" / "go ahead". Default = "stop at green, wait for the user". If the next task depends on this PR landing, report and wait — do not unstick yourself by force-merging. Full rule in `skills/github/github-pr-workflow/SKILL.md` §6.
10. **Committing `__pycache__/` or `.pyc`** — clean before every commit; the `.gitignore` should already cover these but stale files leak through.
11. **Listing branches with `/branches` instead of `/git/refs/heads`** — `/branches` only returns protected/default branches, silently hiding the chore/fix branches you came to audit. Always `gh api repos/<owner>/<repo>/git/refs/heads` for full enumeration. Verified 2026-08-29: deleting "all non-master branches" under `euv-dev/euv` reported only `master` via `/branches`; `/git/refs/heads` exposed 2 leftover branches.
12. **Cleaning branches on the wrong remote (source vs fork)** — when the user says "clean up branches under org X", they mean source repos (`X/<repo>`), not your personal fork (`<user>/<repo>`). Run `git remote -v` to confirm: `origin` = fork, `upstream` = source. Cross-check the target org on GitHub before deleting. Verified 2026-08-29: deleted a branch on `eastspire/euv-docs` thinking it was the source, but the source was `euv-dev/euv-docs` (no such branch there). **(2026-09-05)** `docs-pages/*` no longer has a fork concept (Track 1 direct-push), so the "source vs fork" question is moot for that org — `git remote -v` will only show `origin = docs-pages/<repo>`. The pitfall still applies to `euv-dev`/`hyperlane-dev`/`crates-dev`/third-party repos where fork layout is normal.
13. **Resetting `master` to a stale local tip before push** — the user's personal skill repos (`eastspire/.agents`) get direct-pushed to master. Other sessions often leave working-tree noise (`git status` shows 6+ modified files unrelated to yours). Flow: `git diff --stat` to identify YOUR files, `git add <only-yours>` precisely, commit on a feature branch, then `git checkout master && git reset --hard origin/master && git cherry-pick <your-sha> && git push origin master && git branch -D <branch>`. For conflicts use `git show <sha>:<file> > /tmp/v && cp /tmp/v <file> && git add` to take your version verbatim.

## 5. Quick reference card

```
type:     feat | fix | refactor | perf | docs | test | build | ci | chore | style | revert
scope:    <skill-name> | <area>      (optional)
subject:  ≤ 72 chars, imperative, lowercase first, no trailing period
body:     wrapped 72, what + why, bullet lists
footer:   BREAKING CHANGE: | Refs #N | Closes #N | Fixes #N
PR body:  Summary | Changes | Verification | Notes  (all English)
```
