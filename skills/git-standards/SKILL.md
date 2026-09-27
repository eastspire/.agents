---
name: git-standards
description: 'Git commit + PR routing + text conventions for eastspire-owned repos. **Route by change type, not by repo: docs / config / frontend-style / comment-only changes commit straight to the default branch with no PR; only changes to executable code need a PR (branch → push → PR → merge → delete branch). `.css`/`.scss`/`.less` count as presentation, but a `.tsx` with a changed handler is still a PR. A comment-only edit to a `.rs` file is a docs change; a statement change is a code change. Mechanical classifier: `scripts/classify_change.py` (DIRECT_PUSH | NEEDS_PR).** **All commits and PR descriptions must be written in English** (no Chinese in commit message subject/body, no Chinese in PR title/body, per user preference) — enforced by `scripts/verify_english_only.py`, not just documented. **All commits must use the canonical author identity from `~/.gitconfig` (`eastspire <root@ltpp.vip>`, the personal account of the user) — never a bot identity, never per-commit `-c user.email=…` or `GIT_AUTHOR_EMAIL` overrides (see §7).** Commit subject MUST follow Conventional Commits v1.0.0: `<type>(<scope>): <subject>` where type ∈ {feat, fix, refactor, perf, docs, test, build, ci, chore, style, revert} and scope is the skill name (singular or short area). Subject ≤ 72 chars, imperative mood, no trailing period, no all-caps. Body wrapped at 72 cols, explain *what* and *why* not *how*, use bullet lists for multi-point changes. PR body uses 4-section template: Summary / Changes / Verification / Notes. Footer MUST include `🤖 Generated with [Hermes](https://...)` line (drop if not applicable). **`git commit --no-verify` is FORBIDDEN in every owned project** — the personal account `eastspire/*` and the four owned orgs `hyperlane-dev/*`, `euv-dev/*`, `crates-dev/*`, `docs-pages/*`. The single exemption is a fork of an external project (`fork: true` whose parent lives outside those owners), because that codebase belongs to someone else. Owned repos are enforced by a `prepare-commit-msg` hook that git does NOT let `--no-verify` suppress, so a bypassing commit is still blocked — when a gate fires, fix the code, never bypass (see §3.6, `scripts/guard_no_verify.py`). Triggers: git commit, commit message, PR body, PR description, Conventional Commits, git push, gh pr create, commit prefix, commit type, chore:, feat:, fix:, refactor:, docs:, ci:, 文档直推, 代码 PR, 注释改动, 前端样式, css 提交, 需要 PR 还是直接提交, doc vs code, direct push, delete branch after merge, git author, user.email, user.name, eastspire, no-verify, 绕过 hook, 跳过校验, 跳过提交校验, skip hook, bypass pre-commit, 绕过提交前校验.'
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

**Author identity must come from the global git config**, never from
`-c user.name=…` / `-c user.email=…` / `GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL`
overrides. See §7.

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

### 3.3a Route by change type, not by repo — 文档/配置直推,代码走 PR

**This is the routing rule. It replaces every older "which repo are we in"
heuristic, including the retired `.agents`-only exception.** The decision axis
is *what the diff changes*, not which repository it lands in.

User rule (recorded 2026-09-28, verbatim):

> **「更新 git 提交规范,创建 pr,标题和说明必须要纯英文。commit 作者必须要是我的
> 个人账号,提交信息必须要英文,符合 git 提交规范」**

Three obligations, all enforceable by `scripts/verify_english_only.py`:

1. **Every commit message and every PR title/body is pure English** — no CJK
   characters, no bilingual mix, not even inside a quoted user instruction.
   This is the obligation most often broken: §1/§2/§7 already stated it in
   prose, and prose stops nothing. The two PRs opened earlier on 2026-09-28
   had Chinese titles and Chinese bodies *while the rule was already in the
   file*. Verify before `git commit` and before `gh pr create`.
2. **The commit author is the user's personal account** — `eastspire <
   root@ltpp.vip>`, read from `~/.gitconfig` (§7). Never a bot identity, never
   a GitHub-anonymized `noreply` address, never a per-commit override.
3. **Commit messages follow Conventional Commits** — `<type>(<scope>): <subject>`,
   subject ≤ 72 chars, imperative, no trailing period (§1).

```bash
# before git commit
python3 scripts/verify_english_only.py commit /tmp/msg.txt --repo .
# before gh pr create
python3 scripts/verify_english_only.py pr "<title>" --body /tmp/pr-body.md
```

`pr` mode also enforces the 4-section template (§2.2), so one call covers both
the language rule and the shape rule. Exit 0 = clean, 1 = violations (one per
line, each naming the line/column and the character), 2 = usage error.

A rule written only in prose is not a rule, it is a suggestion. The
`rust-standards` skill hit the same lesson twice in one session: §17.14.1's
table named `#[get]` as the fix for `#[get(pub)]`, which the next check
forbids. Here the fix is that the language rule has a script, not a
paragraph.

User rule (recorded 2026-09-27):

> **「对于修改文档和修改配置的改动请直接提交不要创建 pr，只有对于代码造成了改动
> 才需要创建 pr,pr 合并之后分支需要删除」**
>
> **「修改代码的注释也是直接提交不需要创建 pr」**
>
> **「如果是修改前端样式代码也直接提交，不需要创建 pr」** (added 2026-09-27 —
> frontend **style** sheets are presentation, so they direct-push too)

Three obligations:

1. **Docs / config / comment-only / frontend-style changes → commit straight to
   the default branch.** No feature branch, no PR. Applies to *every* repo, not
   just `eastspire/.agents`.
2. **Code changes → full PR cycle** (§3.3 above, plus
   `gh-pr-creation-workflow`): branch → push → PR → merge.
3. **After a PR merges, delete the branch** — remote and local
   (`gh pr merge --squash --delete-branch`, then `git branch -D`). See
   `gh-pr-creation-workflow` §6 and pitfall 15: `--delete-branch` is a no-op
   unless the repo has `delete_branch_on_merge=true`.

Note the second quote: **a comment-only edit to a `.rs` file is a docs change.**
This is why the file extension cannot be the test — see §3.3b.

Note the third quote: **a `.css`/`.scss`/`.less` change is a presentation
change** (§3.3a.1a), for the same structural reason: a stylesheet has no
statements to change. "前端样式代码" means the stylesheet, NOT JavaScript
component logic — a `.tsx` file with a changed `onClick` is still a PR.

#### 3.3a.1 Layer A — declarative data files (path decides)

A file whose format has **no executable statements** — a parser reads it,
nothing runs it. The file cannot decide what the program does; wrong values
are caught by schema checks and CI, not by eyeballing the diff. These are
always DIRECT_PUSH, content not inspected.

| File type / path | Category | Route | Example |
|---|---|---|---|
| `*.md`, `*.mdx`, `*.rst`, `*.adoc` | 文档 | 直推 | `README.md`, `skills/git-standards/SKILL.md` |
| `*.txt`, `*.csv`, `*.tsv`, `*.po`, `*.pot` | 文档 | 直推 | `CHANGELOG.txt`, `i18n/messages.pot` |
| `*.yaml`, `*.yml` | 配置 | 直推 | `.github/workflows/ci.yml`, `mkdocs.yml` |
| `*.json`, `*.jsonc`, `*.json5` | 配置 | 直推 | `tsconfig.json`, `.eslintrc.json` |
| `*.toml`, `*.ini`, `*.cfg`, `*.conf`, `*.properties` | 配置 | 直推 | `Cargo.toml`, `rustfmt.toml`, `pyproject.toml` |
| dotfiles: `.gitignore`, `.gitattributes`, `.gitmodules`, `.editorconfig` | 配置 | 直推 | `.gitignore`, `.gitattributes` |
| `Dockerfile`, `.terraformrc` (config *as data*) | 配置 | 直推 | `Dockerfile` — see the note below |

**Why `Cargo.toml` / `rustfmt.toml` / `.gitignore` / CI workflows count as
配置, not 代码.** A dependency version bump or a CI trigger change introduces
no new statement that the compiler or interpreter runs. It changes the *inputs*
to a build, which is the definition of configuration. The risky part is
trust, not code review: `git = "…"` adds a supply-chain dependency,
`permissions: write-all` widens a token. Those get flagged as **warnings** (§3.3a.4),
not reclassified as code.

**`Dockerfile` — the one real conflict.** It is named like a build file but
every meaningful instruction (`RUN`, `COPY`, `ENTRYPOINT`) *is* an executable
step in the image build, and a `RUN curl … | sh` line is a supply-chain
hazard. It is therefore treated as **declarative data with warning scanning**:
default DIRECT_PUSH, but every `RUN` line deserves a PR on sight. If the change
adds a `RUN` step, split it: the pure `ENV`/`LABEL`/`WORKDIR` half can go
direct, the `RUN` half goes through a PR.

#### 3.3a.1a Layer A' — presentation-only sources (path decides)

| File type | Category | Route | Example |
|---|---|---|---|
| `*.css`, `*.scss`, `*.less` | 样式 | 直推 | `theme.css`, `_variables.scss`, `legacy.less` |

**Why a stylesheet is a structural path decision, like Layer A.** A stylesheet
holds no business logic: a parser reads selectors, declarations and at-rules,
and nothing *runs*. Changing a colour, a spacing token, a media query or a
whole component block cannot alter program behaviour, so it commits straight to
the default branch. The category is structural (no statements exist to change),
not a judgement about what a particular diff did — a full stylesheet rewrite is
still presentation, so the classifier does not lex it.

**What "前端样式代码" does NOT cover.** The rule is about the *stylesheet*, not
the component that uses it:

| File | Changed | Route |
|---|---|---|
| `App.tsx` | `<div className="hero">`, layout wrappers, prop types only | PR (component logic is code) |
| `App.tsx` | nothing — styles moved to `app.css` | 直推 for the `.css` file |
| `theme.css` | `--brand-color: #6f5` | 直推 |
| `theme.css` | `@import` of a JS module, or `url(javascript:…)` | PR — that is code reaching the browser |
| `*.sass` | indented syntax | PR — not lexable by the C-like comment profile; treat as code |
| `*.js` / `*.ts` with a `<style>` block | the style string | PR — the container decides, same argument as a comment inside `.rs` |

The escape hatch is narrow on purpose: a stylesheet that starts *executing*
something (`@import` of a script, `url()` pulling in a `.js`, a `behavior:`
binding) has crossed from presentation into code and routes to a PR.

#### 3.3a.2 Layer B — everything else (diff content decides)

Source files, scripts, build files, lockfiles and binaries are **lexed** and
judged by their content. The file extension is only a hint at which lexer to
use.

```
DIRECT_PUSH  ⇔  改动行全部是注释 / 空行 / 纯空白
NEEDS_PR     ⇔  改动行中存在任何一行可执行代码
```

Concretely, per file:

1. Lex the **old** and **new** content, tagging each line `code` / `comment` / `blank`.
   A `comment` line's **fingerprint is the line with comment characters
   removed** — for a pure comment line that leaves nothing.
2. Build each side's **code sequence** = the ordered fingerprints of its
   `code` lines.
3. **The two code sequences are identical → DIRECT_PUSH. Any difference → NEEDS_PR.**

Sequence identity is exactly "no changed line of executable code": added,
removed, edited *and reordered* code all perturb the sequence, while comments,
blank lines and trailing whitespace never enter it. Comparing whole sequences
rather than diff hunks is deliberate — git's minimal diff will happily relocate
an *unchanged* code line across a hunk boundary when only blank lines moved,
which a hunk-local comparison would misread as a code change.

| Changed content | Route | Real example |
|---|---|---|
| Added `///` / `//!` doc comments | 直推 | `/// Adds two numbers.` above an untouched `fn add` |
| Added `//` or `/* … */` comments | 直推 | a block comment inserted above a `let x = 1;` |
| Edited an existing comment | 直推 | `let x = 1; // one` → `// the one` |
| Edited a Python docstring (module/class/def doc) | 直推 | `"""Old."""` → `"""New."""` |
| Blank lines added/removed/moved; trailing-whitespace or EOF-newline fix | 直推 | re-indenting blank lines between two statements |
| Changed a statement, signature, macro call, attribute, type | PR | `a + b` → `a - b`; `pub fn f(x: u32)` → `(x: u64)` |
| Added `#[derive(Debug)]` / `#![no_std]` | PR | attributes are code, not comments |
| Changed string-literal contents (incl. a URL) | PR | `"https://a.example"` → `"https://b.example"` |
| Moved a code line (same lines, different order) | PR | reordering statements changes behaviour |
| Deleted/renamed a code file or a code block | PR | `rm src/old.rs`; `git mv` of a `.rs` file |
| New executable file (untracked `.rs`, `.sh`, …) | PR | a brand-new `src/new.rs` |

**The `//`-inside-a-string trap.** `"https://example.com"` is **code**, not a
comment — the string *is* the data the program ships. The lexer is
string-aware, so a `//` inside a literal never opens a comment, while a `//`
inside a `///` comment that merely mentions a URL stays a comment. Rust raw
strings (`r#"a // b"#`), Python docstrings vs. plain triple-quoted strings, and
per-language comment sigils are all handled: **Rust has no `#` line comments**,
so `#[derive(Debug)]` is code, whereas `#` opens a comment in Python, shell,
YAML and TOML.

#### 3.3a.3 Mixed changes — 从严, always NEEDS_PR

If one change touches both comments and code → **NEEDS_PR, no exceptions and
no splitting.** The rule is asymmetric on purpose:

- A reviewer who is told "docs only" and then finds a statement change stops
  trusting the label — every subsequent "docs only" claim gets re-verified by
  hand, which costs more than the PR ceremony ever saved.
- The cost of a needless PR is one round-trip. The cost of a silent code change
  shipped direct is an unreviewed behaviour change on the default branch.
- Splitting a coherent change into "the doc part" and "the code part" produces
  two commits where the second is unbuildable or the first is a lie.

So: **直推 only when the entire diff is comments, docs, or config.** A single
changed code line anywhere in the change sends the whole change through a PR.

#### 3.3a.4 Generated files, binaries, and risky config

| Case | Route | Rule |
|---|---|---|
| `Cargo.lock`, `package-lock.json`, `yarn.lock`, `go.sum`, `flake.lock` | PR | Generated output, not an authored edit. `git checkout --` it if accidental; if the change is real it belongs inside the PR that caused it. Supply-chain sensitive → a human reads the diff. |
| `dist/`, `build/`, `target/`, `node_modules/`, `__pycache__/`, `coverage/`, Vercel build output (`docs-pages/pages/`) | PR | Same reasoning, plus §4 pitfall 10: never commit these at all. |
| Binary / undecodable (`.png`, `.pdf`, `.bin`, images) | PR | The code-vs-docs question is undecidable, so the strict default is a PR. Override *deliberately*; never silently direct-push a diff nobody can read. |
| `pull_request_target`, `workflow_run`, `write-all`, `permissions:`, `secrets.`, `git =`, `--registry` inside a config file | 直推 + **WARNING** | Flagged, not reclassified. Use `--strict-warnings` to make any warning escalate the verdict to NEEDS_PR. |

#### 3.3a.5 The classifier — `scripts/classify_change.py`

The rules above are implemented, not aspirational:

```bash
# what am I about to commit?  (exit 0 = DIRECT_PUSH, 1 = NEEDS_PR, 2 = error)
python3 ~/.agents/skills/git-standards/scripts/classify_change.py

# staged changes only / another repo / any base ref
python3 ~/.agents/skills/git-standards/scripts/classify_change.py --staged
python3 ~/.agents/skills/git-standards/scripts/classify_change.py --repo ~/code/euv --base origin/master

# machine-readable, for hooks and agents
python3 ~/.agents/skills/git-standards/scripts/classify_change.py --json

# the 29 built-in fixtures (no repo required)
python3 ~/.agents/skills/git-standards/scripts/classify_change.py --self-test
```

Exit `1` for NEEDS_PR is a **routing signal, not a failure** — read the verdict.
Environment errors always exit `2`, so a broken run can never be mistaken for
"safe to direct-push". This is a routing classifier, not an audit verifier: it
does not follow rust-standards' `audit_one()` contract and has no baseline diff.

Verified output on a scratch repo (2026-09-27):

```
$ classify_change.py --repo <fixture>
DIRECT_PUSH configuration .github/workflows/ci.yml
DIRECT_PUSH configuration Cargo.toml
DIRECT_PUSH documentation README.md
DIRECT_PUSH documentation src/lib.rs          # only a /// doc comment added
VERDICT: DIRECT_PUSH

# a + b -> a - b in src/lib.rs
NEEDS_PR    code          src/lib.rs
            evidence: - a + b
            evidence: + a - b
VERDICT: NEEDS_PR

# "https://a.example" -> "https://b.example"
NEEDS_PR    code          src/lib.rs
            evidence: - let _ = "https://a.example";
            evidence: + let _ = "https://b.example";
VERDICT: NEEDS_PR
```

#### 3.3a.6 Direct-push flow (docs / config / comments)

```bash
cd ~/.agents
git status --short                              # review what's staged
git add <only-your-files>                       # stage precisely, no -A
git commit -m "<type>(<scope>): <subject>" \
           -m "<body>" -m "" -m "<footer>"
git fetch origin master && git rebase origin/master   # if master moved
git push origin master                          # direct to the default branch, no PR
```

`.agents` (the skill library) is the canonical example of this route: every
`SKILL.md`, `references/`, `scripts/` and frontmatter change lands on `master`
directly. That is a *consequence* of the rule, not a repo-specific exemption —
the same flow applies to a `README.md` fix in `euv-dev/euv` or a
`Cargo.toml` bump in `crates-dev/*`.

For code changes the §3.3 PR flow applies unchanged, and the branch is deleted
after merge (`gh-pr-creation-workflow` §6).

Pitfalls specific to the direct-push route:

- **The `🤖 Generated with [Hermes](...)` footer is OPTIONAL on direct pushes**,
  not required (§1.5 marks it optional; omit unless the user asks).
- **`<scope>` is the skill name**, not a file path. `feat(rust-standards)` not
  `feat(skills/rust-standards/scripts)`. Several files in one skill → one
  commit, `<scope>` = skill name, with a `## Changes` bullet list in the body.
- **`skills/_pending/` is intentionally untracked** — the daily skill-sync cron
  writes there as a staging area. Leave it alone if it appears in `git status`.
- **Comment-only does not mean unreviewable.** A comment can rot: a rewritten
  doc comment that no longer matches the function is worse than no comment.
  Reading your own diff before pushing is still expected.

### 3.3b Why the file extension cannot be the test

An earlier draft of this rule classified by extension — "`.rs`/`.ts`/`.py` =
code, `.md`/`.yml` = docs". The user rule **「修改代码的注释也是直接提交不需要创建
pr」** breaks that axis outright: a `///` doc comment lives *inside* a `.rs` file,
so an extension test would send every comment improvement through a PR while the
user has explicitly said it should not be.

Hence the two-layer design:

- **Layer A (§3.3a.1)** — a *format* allowlist for files that contain no
  executable statements at all. Here the path genuinely is the right question,
  because there is nothing to lex.
- **Layer B (§3.3a.2)** — everything else is decided by lexing the diff's actual
  content. The extension only selects the lexer (Rust `//` vs. Python `#` vs.
  HTML `<!-- -->`).

The auxiliary table below is for **fast pre-judgment only. When it conflicts
with the diff content, the content wins.**

| Looks like | Usual verdict | But the content can override |
|---|---|---|
| `*.md`, `*.mdx`, `*.rst` | 文档 → 直推 | — (Layer A, never overridden) |
| `*.yml`, `*.yaml`, `*.toml`, `*.json` | 配置 → 直推 | — (Layer A; risky *keys* raise a warning) |
| `*.css`, `*.scss`, `*.less` | 样式 → 直推 | — (Layer A′; a stylesheet importing/executing JS is a PR) |
| `*.sass` | 代码 → PR | indented syntax is not lexable; treat as code |
| `*.rs`, `*.ts`, `*.py`, `*.go` | 代码 → PR | **comment-only or docstring-only edit → 直推** |
| `*.sh`, `*.py` (script) | 代码 → PR | **comment-only edit → 直推** |
| `*.rs` (Rust) | 代码 → PR | **`#` is an attribute, not a comment** — `#[derive(Debug)]` is always code |
| `*.tsx`, `*.jsx` | 代码 → PR | a `<style>` block or inline style is still component code |
| Binary / generated | PR | never overridden without a deliberate decision |

**Example that breaks intuition:** editing the comment above a function in
`euv-engine/src/vdom/mod.rs` is a 直推. Changing the `match` arm under that
comment is a PR. Same file, same `git diff`, different route — decided purely by
which lines moved.

### 3.4 After PR is open
- Do NOT add "ping" or "bump" comments
- Do NOT add "ready for review" comment
- Just stop. Wait for maintainer.

For a direct push (docs / config / frontend-style / comment-only) there is no
PR — after `git push origin master`, just report the commit hash + summary and
stop.

### 3.5 Quick routing check

Before committing, one command answers "PR or direct push?":

```bash
python3 ~/.agents/skills/git-standards/scripts/classify_change.py
# VERDICT: DIRECT_PUSH  → commit on the default branch, no PR
# VERDICT: NEEDS_PR     → branch → push → PR → merge --squash --delete-branch
```

When the script and your reading disagree, the **script wins** and you should
find out why you misread the diff — §3.3a.2 has the full rule, and §3.3a.3
explains why a mixed change is never direct-pushed.

## 3.6 `--no-verify` is forbidden in owned projects — forking is the only escape

**In the user's own projects, bypassing the pre-commit hook is not an option
at any point. This is a hard prohibition, not a discouraged shortcut.**

User rule (recorded 2026-09-28, verbatim intent):

> **禁止个人项目和个人组织下（hyperlane-dev，euv-dev，crates-dev，docs-pages）
> 的项目绕过 git 提交前的 hook 校验，只有 fork 的外部仓库提交可以不遵守规范**

### 3.6.1 What counts as an owned project

An **owned** project is any repo the user authors, under either the personal
account or one of the four owned orgs:

| Scope | Owner | Enumerate |
|---|---|---|
| Personal account | `eastspire/*` | `gh api "users/eastspire/repos?per_page=100&affiliation=owner"` |
| Owned orgs | `hyperlane-dev/*`, `euv-dev/*`, `crates-dev/*`, `docs-pages/*` | `gh api "orgs/<org>/repos?per_page=100"` |

Verified 2026-09-28 — the orgs hold exactly:

```
hyperlane-dev/hyperlane          euv-dev/euv           crates-dev/ctares
hyperlane-dev/hyperlane-ai       euv-dev/euv-app       docs-pages/docs
hyperlane-dev/hyperlane-mcp-upload                      docs-pages/pages
hyperlane-dev/hyperlane-quick-start
```

All six org repos report `"fork": false`. **Every repo under these five owners
is subject to the no-bypass rule with no exceptions.**

### 3.6.2 The one exemption — a fork of an external project

A repo is exempt **only** when it is a fork of a project the user did not
author, i.e. GitHub reports `"fork": true` with a `parent` outside the five
owners above. Verified 2026-09-28 on this machine:

| Repo | `fork` | `parent` | Verdict |
|---|---|---|---|
| `eastspire/FrameworkBenchmarks` | `true` | `TechEmpower/FrameworkBenchmarks` | **exempt** |
| `eastspire/web-frameworks` | `true` | `the-benchmarker/web-frameworks` | **exempt** |
| `eastspire/mac-studio-model` | `false` | — | enforced |
| `eastspire/stripe-pay-sdk` | `false` | — | enforced |
| `euv-dev/euv` | `false` | — | enforced |
| `crates-dev/ctares` | `false` | — | enforced |

Check the field, do not guess from the name:

```bash
gh api repos/<owner>/<repo> --jq '{fork, parent: (.parent.full_name // "none")}'
```

A repo under an owned name that is still a fork (`eastspire/serde`,
`eastspire/clap` — upstream `serde-rs/*`, `clap-rs/*`) is **exempt**, because
the upstream project and its conventions belong to someone else. A repo the
user created from scratch is never a fork, however personal it looks.

### 3.6.3 Why the exemption exists — and its limit

The exemption is about **not imposing the user's own house style on someone
else's codebase**. `FrameworkBenchmarks` is TechEmpower's benchmark suite;
reformatting it to this user's doc-comment and type-annotation rules would
produce a fork nobody asked for and a diff that fights upstream. The hook is
disabled there, and the agent follows the upstream project's own conventions
instead.

The exemption is about the *hook and the rules*, **not** about basic git
hygiene. English commit subjects, the `eastspire <root@ltpp.vip>` author
identity (§7), and never committing `__pycache__` / `dist/` / `target/`
(§4 pitfall 10) still apply in a fork. Only the project's-specific
verifiers — the rust-standards audit, the staged-file gate — are skipped.

### 3.6.4 The banned command

```bash
# FORBIDDEN in any owned project — no exceptions, no "just this once"
git commit --no-verify
git -c core.hooksPath=/dev/null commit      # same bypass, looks cleverer
git commit --no-verify --no-gpg-sign        # ditto
SKIP_HOOKS=1 git commit                     # a wrapper's opt-out, same thing
```

`--no-verify` skips `pre-commit` and `commit-msg`, but **not**
`prepare-commit-msg` or `post-commit` — verified on this machine with
throwaway repos:

| Hook | Runs under `--no-verify`? |
|---|---|
| `pre-commit` | **no** — suppressed |
| `commit-msg` | **no** — suppressed |
| `prepare-commit-msg` | **yes** |
| `post-commit` | **yes** |

`prepare-commit-msg` is the enforcement point: git gives it no way to be
skipped, and a non-zero exit aborts the commit. That is why the guard
described in §3.6.5 lives there and not in `pre-commit`.

### 3.6.5 Guard script — `scripts/guard_no_verify.py`

The hook directory on this machine is a **global** `core.hooksPath`
(`~/.git-hooks`, set with `git config --global core.hooksPath`). That has a
non-obvious consequence: a local `.git/hooks/pre-commit` in a repo is
**silently ignored**, so a guard added only there would protect nothing.
Verified 2026-09-28 — a throwaway repo's own `pre-commit` never ran until
`core.hooksPath` was pointed at it explicitly.

The guard therefore lives in `~/.git-hooks/prepare-commit-msg` (the global
path, which nothing shadows) and asks one question per commit:

```
is this repo owned (five owners) AND not a fork → --no-verify is a violation
```

```bash
# what the guard decides for the current repo
python3 ~/.agents/skills/git-standards/scripts/guard_no_verify.py --repo .
# VERDICT: ENFORCED   (owned, non-fork — the hook must run)
# VERDICT: EXEMPT     (external fork — hook may be skipped)
# VERDICT: ERROR      (cannot classify — treat as ENFORCED, never as EXEMPT)
```

**Default to `ENFORCED` on any uncertainty.** A repo whose origin cannot be
resolved, whose `fork` field cannot be read, or that lives outside the five
owners but is not a known external fork, is treated as owned. Only a
positively-identified `fork: true` with a `parent` outside the owners
downgrades to `EXEMPT` — the same asymmetry as §3.3a.3 (从严).

`--no-verify` is not observable from inside the hook: git exposes no env var
for it, and by the time `prepare-commit-msg` runs the commit already
succeeded. So the guard does **not** try to detect the bypass at runtime.
It instead does the thing that actually stops one: `prepare-commit-msg` runs
the gate itself, and the *behaviour* rule — never type `--no-verify` in an
owned repo — is on the agent. The script's job is to answer "is this repo
exempt", so the answer is one command instead of a judgement call.

### 3.6.6 When the hook blocks you

The gate is staged-vs-HEAD, so it fires only on violations **this commit
introduces** — legacy debt never blocks a commit. When it does fire, the fix
is to fix the code, not to bypass:

```bash
# see exactly what is wrong
python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py <repo>
# or the full auto-fix loop, before staging
python3 ~/.agents/skills/rust-standards/scripts/rust_pre_commit.py <repo>
```

Report the violation to the user and fix it. If the gate looks wrong, verify
it against `cargo check` / `cargo clippy` before concluding the *code* is
wrong — the audit script is the source of truth, not your reading of it.

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
12. **Cleaning branches on the wrong remote (source vs fork)** — when the user says "clean up branches under org X", they mean source repos (`X/<repo>`), not your personal fork (`<user>/<repo>`). Run `git remote -v` to confirm: `origin` = fork, `upstream` = source. Cross-check the target org on GitHub before deleting. Verified 2026-08-29: deleted a branch on `eastspire/euv-docs` thinking it was the source, but the source was `euv-dev/euv-docs` (no such branch there). `docs-pages/*` has never had a fork concept (single remote), so the "source vs fork" question is moot for that org — `git remote -v` will only show `origin = docs-pages/<repo>`. The pitfall still applies to `euv-dev`/`hyperlane-dev`/`crates-dev`/third-party repos, and to the legacy Track 2 fork layout.
13. **Resetting `master` to a stale local tip before push** — direct-push repos get commits straight onto `master`, and other sessions often leave working-tree noise (`git status` shows 6+ modified files unrelated to yours). Flow: `git diff --stat` to identify YOUR files, `git add <only-yours>` precisely, then commit. If `master` is ahead of `origin/master` with commits that aren't yours, do NOT push blindly: `git fetch origin master && git rebase origin/master` (or, to take only your own commit: `git checkout master && git reset --hard origin/master && git cherry-pick <your-sha> && git push origin master && git branch -D <branch>`). For conflicts use `git show <sha>:<file> > /tmp/v && cp /tmp/v <file> && git add` to take your version verbatim.
14. **Routing by repo instead of by change type** — the current rule (§3.3a) is: docs / config / frontend-style / comment-only → direct push; code → PR. Three failure modes to avoid in both directions. (a) Assuming a `.rs` / `.sh` / `.toml` edit always needs a PR — a comment-only or dependency-bump change does not. (b) Assuming "it's just docs" because most of a diff is prose — one changed code line anywhere sends the whole change through a PR (§3.3a.3, 从严). (c) Reading "frontend style" as "any file in a frontend repo" — only the stylesheet direct-pushes; a `.tsx` with a changed handler is still a PR (§3.3a.1a). Run `scripts/classify_change.py` rather than eyeballing it.
15. **Per-commit author identity override** — the commit author must come from `~/.gitconfig`'s `[user]` block (`git config --global user.name "eastspire"` + `user.email "root@ltpp.vip"`); never use `git -c user.email=… commit`, `GIT_AUTHOR_EMAIL=… git commit`, or `git commit --amend --author=…` (see §7). Verified 2026-09-27: a `chore: bump version` commit on `euv-dev/euv` was authored as `eastspire@users.noreply.github.com` because of a forgotten `-c` override, which leaks the GitHub-anonymized address into history and doesn't match the canonical identity the user wants on every commit.
16. **The classifier exited 2 on a brand-new file** — a path that exists on disk but not in the base ref has no `base:path` blob, and `read_blob` raised, aborting the WHOLE run so even the other paths went unclassified. It presented as "the script is broken" when it was one missing guard. Fixed by testing `git cat-file -e <base>:<path>` (does the BASE REF have this path) instead of `git ls-files` (does the INDEX have it) — a *staged* new file is already in `ls-files`, so the ls-files test never fired and the crash survived the first attempt at the fix. Layer A / A′ now reach a verdict before any base read, and a new code file gets an empty pre-image (→ NEEDS_PR) instead of a traceback. Verified 2026-09-27: new `.md` / `.css` / `.yml` / `.rs` all classify correctly and `permissions: write-all` still warns on a brand-new workflow.
17. **Commit or PR text contained Chinese** — §1/§2/§7 stated the English-only rule in prose, and two PRs were still opened with Chinese titles and Chinese bodies on 2026-09-28. The failure is not ignorance of the rule — the rule was already in the file when it was violated. Prose has no enforcement point. Run `python3 scripts/verify_english_only.py commit <msgfile> --repo .` before committing and `… pr "<title>" --body <file>` before `gh pr create`; exit 1 is the gate. Quoting the user's Chinese instruction verbatim in the commit body is still a violation — translate it.
18. **`bash` reported `exit=126` on a fresh script** — "Permission denied", which reads like a path or filesystem problem but is a missing execute bit. `chmod +x scripts/verify_english_only.py` before first use.
19. **A fixture loop reported every case as passing** — the loop body ended in `echo "… exit=$?"`, so `$?` was the status of `basename` (or whatever ran last), not the verifier under test. Capture it immediately: `v …; rc=$?`. This one nearly shipped a verifier believed to be broken (it wasn't) and, in the other direction, would have shipped one believed to be working when it wasn't.
20. **`--no-verify` used in an owned project** — §3.6 forbids it outright; the only exemption is a fork of an external project (`fork: true` with a parent outside `eastspire` / `hyperlane-dev` / `euv-dev` / `crates-dev` / `docs-pages`). When a gate blocks a commit, the fix is to fix the code — not to bypass. `git commit --no-verify` is *not* a way out: a `prepare-commit-msg` hook runs the gate again and aborts the commit, because git does not let `--no-verify` suppress that hook. Verified 2026-09-28 in a copy of `ctares`: a `--no-verify` commit carrying a doc-comment violation was blocked (exit 1, commit unrecorded), and the same commit passed once the violation was fixed. Cosmetic variants (`-c core.hooksPath=/dev/null`, `SKIP_HOOKS=1`) are the same bypass and are equally forbidden.
21. **Adding a guard to `.git/hooks/` in a repo on this machine** — `core.hooksPath` is set **globally** to `~/.git-hooks`, so every repo-local hook file is silently ignored and the guard protects nothing. It looks installed and runs never. Verified 2026-09-28: a throwaway repo's own `pre-commit` produced no output across several commits until `core.hooksPath` was overridden explicitly. Any new hook must go in `~/.git-hooks/` (or the repo must first set its own `core.hooksPath`). Confirm with `git config --get core.hooksPath` before debugging why a hook "does not run".
22. **Guessing whether a repo is a fork from its name** — `eastspire/serde` and `eastspire/clap` are forks of `serde-rs/*` and `clap-rs/*` and are therefore exempt, while `eastspire/stripe-pay-sdk` and `eastspire/mac-studio-model` are original work and are enforced. The names look equally personal. Read the field: `gh api repos/<owner>/<repo> --jq '{fork, parent: (.parent.full_name // "none")}'`, or just run `scripts/guard_no_verify.py --repo .`, which defaults to ENFORCED unless an external fork is positively proven.

## 5. Quick reference card

```
type:     feat | fix | refactor | perf | docs | test | build | ci | chore | style | revert
scope:    <skill-name> | <area>      (optional)
subject:  ≤ 72 chars, imperative, lowercase first, no trailing period
body:     wrapped 72, what + why, bullet lists
footer:   BREAKING CHANGE: | Refs #N | Closes #N | Fixes #N
PR body:  Summary | Changes | Verification | Notes  (all English)

route:    docs / config / frontend-style / comment-only  → default branch, NO PR
          any executable code line (.js/.ts/.tsx/.rs/.py) → branch + PR, then --squash --delete-branch
          mixed                         → PR (从严), never split
          binary / generated / lockfile → PR
author:   git config --global user.name  "eastspire"
          git config --global user.email "root@ltpp.vip"
          (never -c user.email=… or GIT_AUTHOR_EMAIL, see §7)
check:    python3 ~/.agents/skills/git-standards/scripts/classify_change.py
          → VERDICT: DIRECT_PUSH | NEEDS_PR   (exit 0 / 1 / 2=error)
bypass:   git commit --no-verify   FORBIDDEN in owned projects (§3.6)
          owned = eastspire/* | hyperlane-dev/* | euv-dev/* | crates-dev/* | docs-pages/*
          exempt = fork:true with a parent outside those owners
          check: python3 ~/.agents/skills/git-standards/scripts/guard_no_verify.py --repo .
```

## 6. Index

| Section | Topic |
|---|---|
| [§1](#1-commit-message-format-conventional-commits-v100) | Commit message format (Conventional Commits v1.0.0), `type` / `scope` / subject / body / footer |
| [§2](#2-pr-title--body-english-only) | PR title + 4-section body template, English-only |
| [§3.3a](#33a-route-by-change-type-not-by-repo--文档配置直推代码走-pr) | **Routing rule** — 文档/配置/样式直推, 代码走 PR; classifier script; **the 2026-09-28 English-only + personal-account rule** and `scripts/verify_english_only.py` |
| [§3.1](#31-pre-commit-cleanup) | Pre-commit cleanup (`__pycache__`, `.pyc`) |
| [§3.2](#32-commit) | Commit invocation |
| [§3.3](#33-push--open-pr) | Full PR flow (code changes) |
| [§3.3a](#33a-route-by-change-type-not-by-repo--文档配置直推代码走-pr) | **Routing rule** — 文档/配置/样式直推, 代码走 PR; classifier script |
| [§3.3a.1a](#33a1a-layer-a--presentation-only-sources-path-decides) | **Layer A′** — `.css`/`.scss`/`.less` frontend style direct-push, and what it excludes |
| [§3.3b](#33b-why-the-file-extension-cannot-be-the-test) | Why extension is not the test; auxiliary pre-judgment table |
| [§3.4](#34-after-pr-is-open) | After the PR is open |
| [§3.5](#35-quick-routing-check) | One-command routing check |
| [§3.6](#36---no-verify-is-forbidden-in-owned-projects--forking-is-the-only-escape) | **`--no-verify` is forbidden in owned projects**; external forks are the only exemption; `prepare-commit-msg` guard |
| [§4](#4-common-pitfalls) | Common pitfalls (15) |
| [§5](#5-quick-reference-card) | Quick reference card |
| [§6](#6-index) | This index |
| [§7](#7-author-identity-global-config-only) | Author identity — global config only, no per-commit override |

Companion skills: `gh-pr-creation-workflow` (branch/PR/merge/delete-branch
end-to-end, and the change-type dimension of the decision tree),
`github/github-pr-workflow` (PR lifecycle and merge approval rules).

## 7. Author identity — global config only, no per-commit override

**Every commit in every eastspire-owned repo MUST have the canonical author
identity set in the global git config.** Per-commit overrides (flag or env)
are forbidden — the identity must come from one source so it can never drift.

User rule (recorded 2026-09-27):

> **「代码的提交用户只能是eastspire，邮箱是root@ltpp.vip ,设置到全局git」**
>
> **「所有仓库的代码提交用户必须是我自己」**

### 7.1 The required identity

```
name:     eastspire
email:    root@ltpp.vip
scope:    --global (in ~/.gitconfig)
```

### 7.2 One-time setup on a fresh machine

```bash
git config --global user.name  "eastspire"
git config --global user.email "root@ltpp.vip"
```

Verify:

```bash
git config --global --get user.name    # eastspire
git config --global --get user.email   # root@ltpp.vip
```

The values land in `~/.gitconfig` under `[user]`. Repo-local overrides
(`git config user.email …` inside a single repo) are not used in the
eastspire-owned namespaces; if one ever appears it is treated as a defect.

### 7.3 Forbidden — and the historical accident to avoid

| Form | Result | Why forbidden |
|---|---|---|
| `git commit -c user.email="eastspire@users.noreply.github.com"` | writes the **GitHub noreply** address into the commit | The noreply address is GitHub's web-only anonymized alias; it doesn't reach the user, doesn't match `~/.gitconfig`, and doesn't survive `git config --global` resets. |
| `GIT_AUTHOR_EMAIL=… GIT_COMMITTER_EMAIL=… git commit` | writes whatever env var says | One env var on one shell session drifts the identity from the global config; the next session silently goes back, leaving mixed authorship across a single PR. |
| `git -c user.email=… commit && git -c user.email=… push` | same as above, just via flag | Same drift problem. |
| `gh repo clone` then commit without `git config` set up first | inherits system / no identity | Fails with `Please tell me who you are`, or commits as the OS user (`sqs@hostname`). |

### 7.4 Verification before any push

The commit author is decided when `git commit` runs, not when `git push` runs,
so verification goes after the commit but before the push:

```bash
git log -1 --format='%an <%ae>'
# MUST print exactly:  eastspire <root@ltpp.vip>

# machine-readable for hooks / CI
git log -1 --format='%an%n%ae' | { read an; read ae;
  [ "$an" = "eastspire" ] && [ "$ae" = "root@ltpp.vip" ] || {
    echo "REJECT: commit author is $an <$ae>, expected eastspire <root@ltpp.vip>" >&2; exit 1;
  }
}
```

A commit that fails this check must be rewritten before push. The cheapest
rewrite is `git commit --amend --reset-author` (only works if the env / flags
were the only thing setting the wrong identity — i.e. `GIT_AUTHOR_EMAIL` was
not set, and the override flags were not used). If the override was via
`-c user.email=…` you must redo the commit without the flag.

### 7.5 What about merge commits?

Merge commits opened via `gh pr merge --squash` keep the **author** of the
squashed commits and set the **committer** to the GitHub user who clicked
merge — that is correct and expected. The identity rule applies to the
**author** field, which is the human who wrote the change. The committer
field is the GitHub machine identity, and remains `eastspire <root@ltpp.vip>`
in practice because the user is the one clicking merge.

### 7.6 What about bot commits?

Bot commits (`github-actions[bot]`, `dependabot[bot]`) are not subject to this
rule — they are machine identities set by the workflow itself, never by a
human override of `--global` config. CI workflows that commit on behalf of
the user must use the global identity too (`git config user.name
"github-actions[bot]"` *inside the workflow step* is fine; the workflow is
not the user).

### 7.7 What if the global config is missing?

Stop and ask the user. Do NOT silently set it from the agent's own knowledge —
the user may want a different identity for a specific period of work, and the
choice belongs to them. The verify-then-commit script in §7.4 will fail loudly
when the identity is unset; that failure is a feature, not a bug.
