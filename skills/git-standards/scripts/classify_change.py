#!/usr/bin/env python3
"""classify_change.py — route a git diff to DIRECT_PUSH or NEEDS_PR by its CONTENT.

Why this exists
---------------
The git submission policy is decided by **what the diff changes** — not by
which repo it lands in, not by the file extension. User rule (2026-09-27):

    "对于修改文档和修改配置的改动请直接提交不要创建 pr，只有对于代码造成了改动
     才需要创建 pr"
    "修改代码的注释也是直接提交不需要创建 pr"

So a `.rs` file is NOT automatically a code change: a diff that only adds
`///` doc comments is a documentation change and commits straight to the default
branch. A diff that touches a statement needs a PR. Extension is a *hint*;
content is the *judge*.

Usage
-----
    classify_change.py                      # uncommitted changes vs HEAD (staged + unstaged)
    classify_change.py --staged             # index vs HEAD only
    classify_change.py --base origin/master # any ref as the base
    classify_change.py --repo ~/code/euv    # classify another repo
    classify_change.py --strict-warnings    # a risky-config warning escalates to NEEDS_PR
    classify_change.py -- path/to/a.rs ...  # limit to specific paths
    classify_change.py --json               # machine-readable
    classify_change.py --self-test          # built-in fixtures, no repo required

Exit codes
----------
    0 — DIRECT_PUSH: no changed line of executable code.
    1 — NEEDS_PR: at least one changed line of executable code.
    2 — error (not a git repo, git failed, unreadable file, ...).

Exit 1 for NEEDS_PR is a routing signal, not a failure — read the printed
verdict. Environment problems always exit 2 so a broken run can never be
mistaken for a clean bill of health.

The two layers
--------------
**Layer A — declarative data (path allowlist) → DIRECT_PUSH, content ignored.**
Markdown/text, YAML, TOML, JSON, dotfiles, `.gitignore`, `*.svg`, `*.po`.
These formats have no executable statements: a value is read by a parser, not
run. Bad values are caught by schema/CI checks, not by eyeballing diff shape.

**Layer B — everything else → decided by diff content.**
Source files, scripts, build files, Dockerfiles, lockfiles, binary blobs. The
file is lexed on both sides of the diff and every line is tagged
`code` / `comment` / `blank`; a *fingerprint* (the line with comment characters
removed) is compared per hunk. The change is DIRECT_PUSH only when no changed
code line exists anywhere in the diff.

Layer A is the only path-based shortcut, and it is deliberately narrow. If a
file is lexable, its content decides — which is what makes "a comment-only edit
to a shell script" and "a comment-only edit to a `.rs` file" behave the same.

Comment detection is string-aware
---------------------------------
`"https://example.com"` is code, not a comment. The lexer tracks string state,
so a `//` inside a literal never opens a comment, while a `//` inside a
`///` comment that *mentions* a URL stays a comment. The lexer is
language-profiled: Rust has **no** `#` line comments, so `#[derive(Debug)]` and
`#![no_std]` are code, whereas `#` starts a comment in Python, shell, YAML and
TOML. A Python docstring is documentation; a plain multi-line string is code.

Mixed diffs resolve to NEEDS_PR automatically and always — 从严
(strict-first). One changed code line anywhere forces the whole change through a
PR, because a reviewer who sees a comment-only diff and finds code in it stops
trusting the label.

This is a routing classifier, not an audit verifier: no `audit_one()` contract,
no baseline diff, cheap enough for a pre-commit hook or an agent to call on
every save.
"""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# language profiles
# --------------------------------------------------------------------------
# `line_comments` are true line-comment tokens for this language.
# Rust deliberately has none: `#` starts an attribute, not a comment.
# `triple_quotes` enables Python-style docstring recognition.

C_LIKE = {"line_comments": ("//",), "blocks": (("/*", "*/"),), "nesting": True, "triple": False}
HTML_LIKE = {"line_comments": ("//",), "blocks": (("/*", "*/"), ("<!--", "-->")), "nesting": False, "triple": False}
SQL_LIKE = {"line_comments": ("--",), "blocks": (("/*", "*/"),), "nesting": True, "triple": False}
HASH_LIKE = {"line_comments": ("#",), "blocks": (), "nesting": False, "triple": True}
SEMI_LIKE = {"line_comments": (";",), "blocks": (), "nesting": False, "triple": False}

PROFILES = {}
for _e in (".rs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".c", ".h", ".cc",
           ".cpp", ".hpp", ".cxx", ".java", ".kt", ".kts", ".go", ".swift", ".scala",
           ".cs", ".zig", ".dart", ".sol", ".glsl", ".wgsl", ".proto", ".thrift",
           ".css", ".scss", ".less"):
    PROFILES[_e] = C_LIKE
for _e in (".html", ".htm", ".xml", ".svg", ".vue", ".svelte", ".astro"):
    PROFILES[_e] = HTML_LIKE
for _e in (".py", ".pyi", ".sh", ".bash", ".zsh", ".fish", ".rb", ".pl", ".pm", ".r",
           ".yaml", ".yml", ".toml", ".cfg", ".ini", ".conf", ".ex", ".exs", ".erl",
           ".jl", ".nix", ".tf", ".tfvars", ".cmake", ".gradle", ".groovy", ".ps1",
           ".psm1", ".mk", ".just", ".tcl", ".awk", ".sed", ".sass", ".dockerfile"):
    PROFILES[_e] = HASH_LIKE
for _e in (".el", ".lisp", ".lsp", ".clj", ".scm", ".asm", ".s"):
    PROFILES[_e] = SEMI_LIKE
PROFILES[".sql"] = SQL_LIKE


def profile_for(path: str) -> dict:
    name = Path(path).name.lower()
    if name in ("dockerfile", "containerfile"):
        return HASH_LIKE
    if name in ("makefile", "gnumakefile", "cmakelists.txt", "justfile", "rakefile"):
        return HASH_LIKE
    return PROFILES.get(Path(path).suffix.lower(), C_LIKE)


# --------------------------------------------------------------------------
# lexer
# --------------------------------------------------------------------------

def _is_ident(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _docstring_opening(lines: list, i: int) -> bool:
    """True when the triple-quoted string starting on lines[i] is a docstring.

    Structural, not textual: the quotes are the first statement of the file, or
    they are the body of a `def` / `async def` / `class` header.
    """
    line = lines[i]
    positions = [p for p in (line.find('"'), line.find("'")) if p != -1]
    if not positions:
        return False
    if line[: min(positions)].strip():
        return False
    prev = ""
    for back in range(i - 1, -1, -1):
        if lines[back].strip():
            prev = lines[back].strip()
            break
    if not prev:
        return True
    if prev.endswith(":"):
        head = prev.rstrip(":")
        head = head.split("(")[0].strip()
        if head.split(" ")[-1:] and head.split(" ")[-1] in ("def", "class"):
            return True
        if head.split(" ")[0:1] and head.split(" ")[0] == "def":
            return True
    return False


def lex(text: str, path: str) -> list:
    """Lex a whole file into [(kind, fingerprint)]; kind ∈ {code, comment, blank}."""
    prof = profile_for(path)
    line_comments = prof["line_comments"]
    blocks = prof["blocks"]
    nesting = prof["nesting"]
    triple = prof["triple"]

    lines = text.split("\n")
    out = []
    block_end = None
    depth = 0
    quote = None
    raw_hashes = 0
    in_triple = False
    string_is_doc = False

    for idx, line in enumerate(lines):
        code_chars = []
        saw_comment = False
        saw_code = False
        i = 0
        n = len(line)

        while i < n:
            ch = line[i]

            # ---- inside a block comment ----
            if block_end is not None:
                if line.startswith(block_end, i):
                    i += len(block_end)
                    if nesting:
                        depth -= 1
                        if depth <= 0:
                            block_end = None
                    else:
                        block_end = None
                    saw_comment = True
                    continue
                opened = False
                for start, _end in blocks:
                    if line.startswith(start, i):
                        depth += 1
                        block_end = dict(blocks)[start]
                        i += len(start)
                        opened = True
                        break
                if not opened:
                    i += 1
                continue

            # ---- inside a string literal ----
            if quote is not None:
                if string_is_doc:
                    saw_comment = True
                else:
                    code_chars.append(ch)
                    saw_code = True
                if raw_hashes:
                    if ch == '"':
                        j = i + 1
                        hashes = 0
                        while j < n and line[j] == "#" and hashes < raw_hashes:
                            hashes += 1
                            j += 1
                        if hashes == raw_hashes:
                            if not string_is_doc:
                                # the opening `"` above is already in code_chars;
                                # only the closing hashes are still missing
                                code_chars.append("#" * raw_hashes)
                                saw_code = True
                            quote = None
                            raw_hashes = 0
                            i = j
                            continue
                elif ch == "\\":
                    if i + 1 < n and not string_is_doc:
                        code_chars.append(line[i + 1])
                        i += 2
                        continue
                elif ch == quote:
                    if in_triple and line.startswith(quote * 3, i):
                        if not string_is_doc:
                            # one quote char is already in code_chars, add the other two
                            code_chars.append(quote * 2)
                            saw_code = True
                        i += 3
                        quote = None
                        in_triple = False
                        string_is_doc = False
                        continue
                    if not in_triple:
                        quote = None
                        i += 1
                        continue
                i += 1
                continue

            # ---- normal code position ----
            hit = False
            for lc in line_comments:
                if line.startswith(lc, i):
                    saw_comment = True
                    i = n
                    hit = True
                    break
            if hit:
                continue

            for start, end in blocks:
                if line.startswith(start, i):
                    block_end = end
                    depth = 1
                    saw_comment = True
                    i += len(start)
                    hit = True
                    break
            if hit:
                continue

            if ch in ('"', "'"):
                run = 1
                while i + run < n and line[i + run] == ch:
                    run += 1
                is_triple = triple and run >= 3
                # detect a Rust raw string prefix: r"..", r#".."#, br#".."#
                j = i - 1
                hashes = 0
                while j >= 0 and line[j] == "#":
                    hashes += 1
                    j -= 1
                ident = ""
                while j >= 0 and _is_ident(line[j]):
                    ident = line[j] + ident
                    j -= 1
                if "r" in ident.lower() and ident.lower().rstrip("#") in ("r", "br", "rb", "cr", "fr"):
                    raw_hashes = hashes
                string_is_doc = is_triple and _docstring_opening(lines, idx)
                if string_is_doc:
                    saw_comment = True
                else:
                    code_chars.append(ch * run)
                    saw_code = True
                quote = ch
                in_triple = is_triple
                i += 3 if is_triple else 1
                continue

            code_chars.append(ch)
            saw_code = True
            i += 1

        fingerprint = "".join(code_chars).strip()
        if saw_code or fingerprint:
            kind = "code"
        elif saw_comment or quote is not None or block_end is not None:
            kind = "comment"
        else:
            kind = "blank"
        out.append((kind, fingerprint))

    return out


# --------------------------------------------------------------------------
# Layer A: declarative-data allowlist
# --------------------------------------------------------------------------

DOC_EXTS = {
    ".md", ".markdown", ".mdx", ".rst", ".adoc", ".txt", ".text", ".csv", ".tsv",
    ".json", ".jsonc", ".json5", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".properties", ".env", ".po", ".pot",
}
DOTFILE_NAMES = {
    ".gitignore", ".gitattributes", ".gitmodules", ".editorconfig", ".gitkeep",
    ".git-blame-ignore-revs", ".npmrc", ".nvmrc", ".rustfmt.toml", ".clippy.toml",
    ".dockerignore", ".prettierrc", ".prettierignore", ".eslintrc", ".eslintrc.json",
    ".babelrc", ".browserslistrc", ".license", "license", "notice", ".env",
}
DATA_NAMES = {"dockerfile", "containerfile", ".terraformrc"}


def is_declarative(path: str) -> bool:
    """Layer A: the file is pure data — a parser reads it, nothing executes it."""
    p = Path(path)
    if p.name.lower() in DOTFILE_NAMES or p.name.lower() in DATA_NAMES:
        return True
    return p.suffix.lower() in DOC_EXTS


# --------------------------------------------------------------------------
# strict categories (decided before any content analysis)
# --------------------------------------------------------------------------

GENERATED_SUFFIXES = (
    "cargo.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "poetry.lock", "gemfile.lock", "composer.lock", "go.sum", "flake.lock",
    "pubspec.lock", "mix.lock", "gradle.lockfile",
)
GENERATED_DIRS = (
    "dist", "build", "target", "node_modules", "out", ".next", "__pycache__",
    ".venv", "vendor", "coverage", ".svelte-kit", "pkg", "site", "pages",
)


def is_generated(path: str) -> bool:
    p = Path(path)
    if p.name.lower() in GENERATED_SUFFIXES:
        return True
    parts = [x.lower() for x in p.parts[:-1]]
    return any(seg in GENERATED_DIRS for seg in parts)


WARN_SUBSTRINGS = (
    ("pull_request_target", "runs with a write token on fork PRs"),
    ("workflow_run", "chains a privileged workflow"),
    ("write-all", "grants write-all token permissions"),
    ("permissions:", "changes workflow token permissions"),
    ("secrets.", "references CI secrets"),
    ("git =", "adds a git dependency (supply chain)"),
    ("replace-with", "dependency replacement redirect"),
    ("--registry", "custom package registry"),
)


# --------------------------------------------------------------------------
# git plumbing
# --------------------------------------------------------------------------

def git(repo: Path, args: list) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo)] + args,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError("git %s failed (%d): %s" % (
            " ".join(args), proc.returncode,
            proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout.decode("utf-8", "replace")


def is_binary_diff(diff_text: str) -> bool:
    return any(l.startswith("Binary files ") or l.startswith("GIT binary patch")
               for l in diff_text.split("\n"))


def read_blob(repo: Path, rev: str) -> str:
    return git(repo, ["show", rev])


# --------------------------------------------------------------------------
# the core decision: per-hunk fingerprint comparison
# --------------------------------------------------------------------------

def code_sequence(lexed: list) -> list:
    """The file's executable fingerprint sequence, in order, blanks/comments dropped.

    This — not the diff hunks — is the unit of comparison. Comparing whole
    sequences is immune to the way git chooses to align a diff: when only
    blank lines move, git's minimal edit may relocate an unchanged *code* line
    across the hunk boundary, which a hunk-local comparison would misread as
    a code change.
    """
    return [fp for kind, fp in lexed if kind == "code" and fp]


def decide(pre_lex: list, post_lex: list) -> tuple:
    """Decide from the two whole-file code sequences.

    DIRECT_PUSH iff the sequences are identical. That is exactly "no changed
    line of executable code": added, removed, edited and reordered code all
    perturb the sequence, while comments, blank lines and trailing whitespace
    never enter it. Sequence equality (not set equality) is deliberate — moving
    a statement reorders the sequence, and reordering executable lines changes
    behaviour.
    """
    pre_seq = code_sequence(pre_lex)
    post_seq = code_sequence(post_lex)
    if pre_seq == post_seq:
        return True, []

    evidence = []
    matcher = difflib.SequenceMatcher(None, pre_seq, post_seq, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        for line in pre_seq[i1:i2][:2]:
            evidence.append("- %s" % line[:70])
        for line in post_seq[j1:j2][:2]:
            evidence.append("+ %s" % line[:70])
        if len(evidence) >= 4:
            break
    if not evidence:
        evidence = ["code sequence differs"]
    return False, evidence


def classify_text(path: str, pre: str, post: str, hunks=None) -> dict:
    """Classify a pre/post pair. `hunks` is accepted for API symmetry and ignored."""
    pre_lex = lex(pre, path)
    post_lex = lex(post, path)
    direct, evidence = decide(pre_lex, post_lex)
    return {
        "direct": direct,
        "evidence": evidence[:4],
        "pre_kinds": pre_lex,
        "post_kinds": post_lex,
    }


# --------------------------------------------------------------------------
# per-file classification
# --------------------------------------------------------------------------

MAX_EVIDENCE = 3


def classify_file(repo: Path, path: str, base: str, staged: bool) -> dict:
    res = {"path": path, "category": None, "route": None, "reason": "",
           "evidence": [], "warnings": []}

    def setverdict(category, route, reason):
        res.update(category=category, route=route, reason=reason)

    tracked = False
    try:
        git(repo, ["ls-files", "--error-unmatch", "--", path])
        tracked = True
    except RuntimeError:
        tracked = False

    if tracked:
        diff_text = git(repo, ["diff", "-U0", "-M"] + (["--cached"] if staged else []) + [base, "--", path])
        pre = read_blob(repo, base + ":" + path)
    else:
        diff_text = ""
        pre = ""
    post_path = repo / path
    if staged and tracked:
        post = read_blob(repo, ":" + path)
    elif post_path.exists():
        try:
            post = post_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise RuntimeError("cannot read %s: %s" % (path, exc))
    else:
        post = ""

    # 1. generated / lockfile
    if is_generated(path):
        setverdict("generated", "NEEDS_PR",
                   "generated or lockfile output — not an authored edit. Reset it if "
                   "the change is accidental; if it is real, it belongs inside the PR "
                   "that caused it (supply-chain sensitive, a human must read the diff)")
        return res

    # 2. binary
    if is_binary_diff(diff_text) or "\0" in (post[:8192] + pre[:8192]):
        setverdict("binary", "NEEDS_PR",
                   "binary file — the code/docs question is undecidable, so the strict "
                   "default is a PR. Override deliberately; do not silently direct-push "
                   "an unreadable diff")
        return res

    # 3. rename of a non-declarative file
    if "rename from " in diff_text and not is_declarative(path):
        setverdict("code", "NEEDS_PR",
                   "rename or copy of a non-document file — moving code is a code change "
                   "even when not one character of it was edited")
        return res

    # 4. Layer A — declarative data
    if is_declarative(path):
        category = "documentation" if Path(path).suffix.lower() in (
            ".md", ".markdown", ".mdx", ".rst", ".adoc", ".txt", ".text", ".po", ".pot") else "configuration"
        setverdict(category, "DIRECT_PUSH",
                   "declarative data file: a parser reads it, nothing executes it. "
                   "Content is not inspected; risky keys are flagged as warnings below")
        for line in post.split("\n"):
            for needle, why in WARN_SUBSTRINGS:
                if needle in line:
                    msg = "contains %r — %s" % (needle, why)
                    if msg not in res["warnings"]:
                        res["warnings"].append(msg)
                    break
        return res

    # 5. Layer B — content decides
    if not tracked:
        pass
    elif not diff_text.strip():
        return res  # nothing to say about this path

    verdict = classify_text(path, pre, post)
    if verdict["direct"]:
        kinds = {k for k, _f in verdict["post_kinds"]}
        setverdict("documentation", "DIRECT_PUSH",
                   "every changed line is a comment, a blank line or trailing whitespace — "
                   "the code fingerprint is unchanged across the whole diff")
        comments = [f for k, f in verdict["post_kinds"] if k == "comment"]
        res["evidence"] = ["(comment-only diff)"] if comments else []
        return res

    setverdict("code", "NEEDS_PR",
               "at least one changed line of executable code (statement, signature, macro, "
               "attribute, type, or the string data that reaches it)")
    res["evidence"] = verdict["evidence"][:MAX_EVIDENCE]
    return res


def list_paths(repo: Path, base: str, staged: bool, explicit: list) -> list:
    if explicit:
        return explicit
    args = ["diff", "--name-only", "-M"] + (["--cached"] if staged else []) + [base]
    tracked = [l for l in git(repo, args).split("\n") if l.strip()]
    if staged:
        return tracked
    untracked = [l for l in git(repo, ["ls-files", "--others", "--exclude-standard"]).split("\n") if l.strip()]
    return sorted(set(tracked) | set(untracked))


# --------------------------------------------------------------------------
# self test — repo free, exercises the real lex + decision code
# --------------------------------------------------------------------------

LEX_FIXTURES = [
    # (filename, source, expected fingerprints, note)
    ("url-literal.rs",
     'let base = "https://example.com";\n',
     ['let base = "https://example.com";'],
     "// inside a string literal must not open a comment"),
    ("url-in-comment.rs",
     '// see https://example.com/docs\nlet x = 1;\n',
     ['let x = 1;'],
     "URL inside a // comment stays a comment"),
    ("derive.rs",
     "#[derive(Debug)]\npub struct S;\n",
     ['#[derive(Debug)]', 'pub struct S;'],
     "Rust # is an attribute, NOT a line comment"),
    ("no-std.rs",
     "#![no_std]\npub fn f() {}\n",
     ['#![no_std]', 'pub fn f() {}'],
     "Rust #! inner attribute is code"),
    ("py-comment.py",
     "# a note\nx = 1\n",
     ['x = 1'],
     "Python # is a line comment"),
    ("py-docstring.py",
     'def f():\n    """Doc."""\n    return 1\n',
     ['def f():', 'return 1'],
     "docstring is documentation"),
    ("py-plain-string.py",
     'def f():\n    x = """\n    not a doc\n    """\n    return x\n',
     ['def f():', 'x = """', 'not a doc', '"""', 'return x'],
     "a plain multi-line string is code, not a docstring"),
    ("raw-string.rs",
     'let s = r#"a // not a comment"#;\nlet t = 1;\n',
     ['let s = r#"a // not a comment"#;', 'let t = 1;'],
     "Rust raw string hides //"),
    ("nested-block.rs",
     "/* a /* b */ c */\nlet x = 1;\n",
     ['let x = 1;'],
     "nested block comment (Rust/C family)"),
    ("html-comment.html",
     "<!-- hidden -->\n<div>hi</div>\n",
     ['<div>hi</div>'],
     "HTML comment"),
    ("semicolon.el",
     ";; a note\n(+ 1 2)\n",
     ['(+ 1 2)'],
     "Lisp ; comment"),
]

DECIDE_FIXTURES = [
    # (name, pre, post, expected_route, note)
    ("doc-comment-added.rs",
     "pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n",
     "/// Adds two numbers.\n/// Returns the sum.\npub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n",
     "DIRECT_PUSH", "/// doc comment above an untouched fn"),
    ("statement-changed.rs",
     "pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n",
     "pub fn add(a: i32, b: i32) -> i32 {\n    a - b\n}\n",
     "NEEDS_PR", "statement changed"),
    ("url-changed.rs",
     'const BASE: &str = "https://example.com";\n',
     'const BASE: &str = "https://example.org";\n',
     "NEEDS_PR", "// inside a literal is data, and the data changed"),
    ("url-in-comment-edited.rs",
     '/// see https://example.com\nconst BASE: &str = "https://example.com";\n',
     '/// see https://example.com/docs\nconst BASE: &str = "https://example.com";\n',
     "DIRECT_PUSH", "URL inside a // comment is still a comment"),
    ("block-comment.rs",
     "fn f() {\n    // old block\n    let x = 1;\n    let _ = x;\n}\n",
     "fn f() {\n    /* brand new\n       multiline\n       block comment */\n    let x = 1;\n    let _ = x;\n}\n",
     "DIRECT_PUSH", "multi-line /* */ block comment"),
    ("mixed.rs",
     "fn f() {\n    let x = 1;\n    let _ = x;\n}\n",
     "/// doc\nfn f() {\n    let x = 1;\n    let y = 2;\n    let _ = x + y;\n}\n",
     "NEEDS_PR", "doc comment + code in one diff (从严)"),
    ("trailing-comment.rs",
     "let x = 1; // one\n",
     "let x = 1; // the one\n",
     "DIRECT_PUSH", "only the trailing comment of a code line changed"),
    ("blank-lines.rs",
     "fn f() {\n\n\n    let x = 1;\n    let _ = x;\n}\n",
     "fn f() {\n    let x = 1;\n\n\n    let _ = x;\n}\n",
     "DIRECT_PUSH", "blank line moves only"),
    ("statements-swapped.rs",
     "fn f() {\n    let a = first();\n    let b = second();\n    a + b\n}\n",
     "fn f() {\n    let b = second();\n    let a = first();\n    a + b\n}\n",
     "NEEDS_PR", "reordered statements (order matters)"),
    ("code-moved.rs",
     "fn f() {\n    first();\n    second();\n}\n",
     "fn f() {\n    second();\n    first();\n}\n",
     "NEEDS_PR", "a code line moved: still a code change"),
    ("crate-doc.rs",
     "//! old crate docs\n\npub fn f() {}\n",
     "//! new crate docs\n//! more crate docs\n\npub fn f() {}\n",
     "DIRECT_PUSH", "//! crate-level doc comment"),
    ("docstring-changed.py",
     'def f():\n    """Old."""\n    return 1\n',
     'def f():\n    """New."""\n    return 1\n',
     "DIRECT_PUSH", "python docstring edit"),
    ("py-return-changed.py",
     "def f():\n    return 1\n",
     "def f():\n    return 2\n",
     "NEEDS_PR", "python return value changed"),
    ("shell-comment-only.sh",
     "#!/usr/bin/env bash\nset -euo pipefail\necho hi\n",
     "#!/usr/bin/env bash\n# runs the thing\nset -euo pipefail\necho hi\n",
     "DIRECT_PUSH", "comment-only edit to an executable script"),
    ("shell-logic.sh",
     "#!/usr/bin/env bash\necho hi\n",
     "#!/usr/bin/env bash\necho hello\n",
     "NEEDS_PR", "command changed in a script"),
    ("whole-file-deleted.rs",
     "fn f() {\n    let x = 1;\n    let _ = x;\n}\n",
     "",
     "NEEDS_PR", "deleting a code file"),
    ("comment-only-file-deleted.rs",
     "fn f() {\n    let x = 1;\n}\n// trailing note\n",
     "fn f() {\n    let x = 1;\n}\n",
     "DIRECT_PUSH", "deleting only a trailing comment"),
    ("py-docstring-plus-code.py",
     'def f():\n    """A."""\n    return 1\n',
     'def f():\n    """B."""\n    return 2\n',
     "NEEDS_PR", "docstring + statement changed together"),
]


def self_test() -> int:
    print("classify_change.py --self-test  (no git repo involved)")
    print("=" * 78)
    failures = 0

    print("-- lexer: comment vs code fingerprints " + "-" * 42)
    for name, src, expected, why in LEX_FIXTURES:
        got = [f for _k, f in lex(src, "fixture/" + name) if f]
        ok = got == expected
        failures += 0 if ok else 1
        print("  %-4s %-26s %s" % ("PASS" if ok else "FAIL", name, why))
        if not ok:
            print("       expected %r" % (expected,))
            print("       got      %r" % (got,))

    print("-- decision: DIRECT_PUSH vs NEEDS_PR " + "-" * 39)
    for name, pre, post, expected, why in DECIDE_FIXTURES:
        got = "DIRECT_PUSH" if classify_text(name, pre, post)["direct"] else "NEEDS_PR"
        ok = got == expected
        failures += 0 if ok else 1
        print("  %-4s %-26s -> %-11s %s" % ("PASS" if ok else "FAIL", name, got, why))

    print("=" * 78)
    total = len(LEX_FIXTURES) + len(DECIDE_FIXTURES)
    print("%d/%d fixtures passed" % (total - failures, total))
    return 1 if failures else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Classify a git diff as DIRECT_PUSH (docs/config/comments) or NEEDS_PR (code).")
    ap.add_argument("--repo", default=".", help="repository root (default: cwd)")
    ap.add_argument("--base", default="HEAD", help="base ref for the diff (default: HEAD)")
    ap.add_argument("--staged", action="store_true", help="classify the index instead of the worktree")
    ap.add_argument("--strict-warnings", action="store_true",
                    help="escalate a risky-config warning to NEEDS_PR")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    ap.add_argument("--self-test", action="store_true", help="run built-in fixtures and exit")
    ap.add_argument("paths", nargs="*", help="limit classification to these paths")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        sys.stderr.write("error: %s is not a git repository\n" % repo)
        return 2

    try:
        paths = list_paths(repo, args.base, args.staged, args.paths)
        files = [classify_file(repo, p, args.base, args.staged) for p in paths]
        files = [f for f in files if f["route"]]
        if args.strict_warnings:
            for f in files:
                if f["route"] == "DIRECT_PUSH" and f["warnings"]:
                    f["route"] = "NEEDS_PR"
                    f["reason"] += " (escalated by --strict-warnings: risky config keys present)"
        verdict = "NEEDS_PR" if any(f["route"] == "NEEDS_PR" for f in files) else "DIRECT_PUSH"
    except RuntimeError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2
    except OSError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2

    if args.json:
        print(json.dumps({"verdict": verdict, "base": args.base, "staged": args.staged,
                          "files": files}, indent=2, ensure_ascii=False))
    else:
        for f in files:
            print("%-11s %-13s %s" % (f["route"], f["category"], f["path"]))
            print("            %s" % f["reason"])
            for ev in f["evidence"]:
                print("            evidence: %s" % ev)
            for w in f["warnings"]:
                print("            WARNING: %s" % w)
        if not files:
            print("(no changes to classify)")
        print("-" * 78)
        print("VERDICT: %s" % verdict)
        if verdict == "DIRECT_PUSH":
            print("next: commit on the default branch, no PR. Conventional Commits still apply (git-standards §1).")
        else:
            print("next: branch off the default branch, push, open a PR, then merge with "
                  "'gh pr merge --squash --delete-branch' (see gh-pr-creation-workflow §6).")

    return 0 if verdict == "DIRECT_PUSH" else 1


if __name__ == "__main__":
    sys.exit(main())
