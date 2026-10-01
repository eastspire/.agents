#!/usr/bin/env python3
"""Block a commit that would break one of X's non-negotiable browser rules.

Each rule here exists because breaking it had a concrete, measured cost. They
are not style preferences.

  no page load      every refresh, navigate or tab spawn makes the user
                    confirm it in their UI. One named exemption:
                    ensure_browser.py may launch the browser and open the
                    single tab the flow needs, because without it a nightly
                    run dies whenever the browser is closed — and it is a
                    separate file with one job so the exemption cannot
                    spread. The self-test asserts that the same code under
                    any other name is still blocked.
  no clearing       clearing the composer raises Chrome's unsaved-changes
                    dialog (系统可能不会保存您所做的更改), and that modal then
                    blocks every later CDP call until the user dismisses it
  no open IME       imeSetComposition STARTS a composition; uncommitted it
                    makes Chrome treat the page as holding unsaved input
  no mouse/keys     the user's pointer and OS focus are never taken
  no clipboard      paste hangs in this environment and bypasses Draft's
                    own input path, which is the only path that works
  verify            CLICKED is not evidence a post happened

The check is syntactic on purpose. A behavioural check would have to run the
publisher against the live site, which is exactly what must not happen on a
commit. Syntactic rules can be defeated by a determined editor, but they hold
against the ordinary failure mode, which is a new script written months from
now by someone who does not remember why the rule exists — and every rule in
this file was broken by exactly that.

Usage:
    verify_no_unsafe_posting.py --staged     check the staged diff
    verify_no_unsafe_posting.py PATH ...      check the given files/dirs
    verify_no_unsafe_posting.py --self-test   prove each rule fires

Exit codes: 0 clean, 1 violations, 2 self-test failed.
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

# Each entry: (id, what is banned, why, how to spot it).
# The pattern is matched against the source with comments and docstrings
# removed first, so prose that MENTIONS a banned call (the skill's own notes do)
# is not a violation while an actual call is.
RULES: list[tuple[str, str, str, str]] = [
    (
        "no-page-load",
        "location.assign / Page.reload / Page.navigate / opening a tab",
        "every page load makes the user confirm it in their UI",
        r"\blocation\.(assign|replace)\s*\(|"
        r"""\bsend\s*\(\s*["']Page\.(reload|navigate)["']|"""
        r"""["']Page\.(reload|navigate)["']\s*[,)]|"""
        r"\bnew_tab\s*\(|\bTarget\.createTarget\b|"
        r"""\bsend\s*\(\s*["']Target\.createTarget["']""",
    ),
    (
        "no-clearing",
        "emptying the composer (clear(), select-all + delete, Backspace loop)",
        "raises Chrome's unsaved-changes dialog, which then blocks every "
        "later CDP call",
        r"\b(?:def\s+)?clear\s*\(\s*c\s*\)|"
        r"""\bexecCommand\s*\(\s*["'](delete|selectAll)["']\s*\)|"""
        r"""\bsend\s*\([^\)]{0,400}?Backspace""",
    ),
    (
        "no-open-ime",
        "imeSetComposition without a commit",
        "an uncommitted IME composition makes Chrome claim the page holds "
        "unsaved input, and Escape discards the whole post",
        r"\bimeSetComposition\b",
    ),
    (
        "no-mouse-keyboard",
        "taking the mouse or the OS keyboard",
        "the user's pointer and focus are never taken from them",
        r"""\bsend\s*\(\s*["']Page\.bringToFront["']|"""
        r"""\bsend\s*\(\s*["']Input\.dispatchMouseEvent["']|"""
        r"\bbring_to_front\b|\bclick_at_xy\b",
    ),
    (
        "no-clipboard",
        "the clipboard",
        "paste hangs in this environment and bypasses the only input path "
        "that works",
        r"\bpbcopy\b|\bpbpaste\b|"
        r"""\bsend\s*\([^\)]{0,400}?["']paste["']""",
    ),
]

# imeSetComposition is legal ONLY when the same file also closes the
# composition. close_composition() is the sanctioned helper; an explicit
# insertText right after the composition counts too.
COMMIT_EVIDENCE = re.compile(
    r"close_composition|commitText|insertText", re.IGNORECASE)


def _docstring_lines(src: str) -> list[tuple[int, int]]:
    """Line ranges covered by module/class/function docstrings."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    spans: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef,
                                 ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", [])
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            d = body[0]
            spans.append((d.lineno, getattr(d, "end_lineno", d.lineno)))
    return spans


def code_tokens(src: str):
    """(line_number, text) for every real token, with its true position.

    Comments, indentation and NEWLINE are dropped. String literals are KEPT:
    the banned CDP method names and the "paste" command are string ARGUMENTS,
    so dropping them would drop the evidence. Docstrings are excluded by line
    range instead — the AST knows exactly which strings are docstrings, and
    the skill's own notes mention banned calls in prose that must not count.

    ast.unparse() is the wrong tool here: it rebuilds the source from the AST,
    so a match's line number points at a line unrelated to the original. That
    reported a clean file as violating at lines 382/574/789.
    """
    import io
    import tokenize
    doc_lines = _docstring_lines(src)
    skip = (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
            tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER)
    out: list[tuple[int, str]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in skip:
                continue
            if tok.type == tokenize.STRING:
                line = tok.start[0]
                if any(lo <= line <= hi for lo, hi in doc_lines):
                    continue
            out.append((tok.start[0], tok.string))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return [(n + 1, line) for n, line in enumerate(src.splitlines())]
    return out


def check_syntax(path: Path) -> list[str]:
    try:
        ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        return [f"{path}: does not parse ({exc.msg} line {exc.lineno})"]
    return []


# The ONE file allowed to load a page. Launching a browser and opening a
# composer is a different act from driving one: it happens once, before
# anything is typed, and it is what makes a nightly run possible at all. Every
# other script stays forbidden, so "the publisher opened a tab" is still a
# defect rather than a shortcut — and a new script cannot opt in by naming
# itself, because the exemption is by exact filename here.
PAGE_LOAD_EXEMPT = {"ensure_browser"}


def _may_load_pages(path: Path) -> bool:
    return path.stem in PAGE_LOAD_EXEMPT


def check_file(path: Path) -> list[str]:
    """Report every banned call in one file, with its real line number.

    Matches run over the joined token text (so a banned name split across lines
    is still found) and each hit is mapped back to the line its FIRST token
    starts on — which is why line numbers are trustworthy here.
    """
    problems: list[str] = []
    src = path.read_text(encoding="utf-8", errors="replace")
    toks = code_tokens(src)
    # Join with a space: a newline between tokens would split `send(` from
    # `"Page.reload"` and most patterns would stop matching.
    code = " ".join(tok for _, tok in toks)
    tok_line = [ln for ln, _ in toks]

    for rid, banned, why, pattern in RULES:
        rx = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        lines: set[int] = set()
        # Map each match back to the line its first token starts on. A space
        # separator means one token per "word", so walk the code alongside the
        # token list rather than counting newlines.
        starts = []
        pos = 0
        for tok in toks:
            starts.append(pos)
            pos += len(tok[1]) + 1
        for m in rx.finditer(code):
            i = max((j for j, s in enumerate(starts) if s <= m.start()),
                    default=None)
            if i is not None and i < len(tok_line):
                lines.add(tok_line[i])
        if not lines:
            continue
        if rid == "no-open-ime" and COMMIT_EVIDENCE.search(code):
            continue                      # committed, therefore fine
        if rid == "no-page-load" and _may_load_pages(path):
            continue                      # bringing the browser up is its job
        shown = sorted(lines)[:6]
        problems.append(
            f"{path}: [{rid}] {banned} — {why}"
            f" (line{'s' if len(shown) > 1 else ''} "
            f"{', '.join(str(n) for n in shown)})")
    return problems


def staged_files(repo: str | None) -> list[Path]:
    root = Path(repo or subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True).stdout.strip() or ".")
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=root, capture_output=True, text=True).stdout
    files = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.endswith(".lock"):
            continue
        p = root / line
        # Only the browser-driving scripts can break these rules; prose and
        # copy files cannot.
        if p.suffix == ".py" and ("scripts" in p.parts or "hooks" in p.parts):
            files.append(p)
    return files


def collect(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob("*.py")))
        elif p.suffix == ".py":
            files.append(p)
    return files


# --- self-test: each rule must actually fire ---------------------------
FIXTURES = {
    "no-page-load": 'c.js("location.assign(\'https://x.com/compose/post\')")',
    "no-page-load-2": 'c.send("Page.reload", wait=20)',
    "no-page-load-3": "tab = C.new_tab(url)",
    "no-clearing": "clear(c)",
    "no-clearing-def": "def clear(c):\n    return True\n\nclear(c)\n",
    "no-clearing-2": """c.js("document.execCommand('delete')")""",
    "no-clearing-3": ('c.send("Input.dispatchKeyEvent", type="rawKeyDown", '
                      'key="Backspace")'),
    "no-open-ime": ('c.send("Input.imeSetComposition", text=u)  # no commit '
                    'follows'),
    "no-mouse-keyboard": 'c.send("Page.bringToFront")',
    "no-mouse-keyboard-2": 'c.send("Input.dispatchMouseEvent", type="mousePressed")',
    "no-clipboard": "subprocess.run(['pbcopy'], input=text)",
    "no-clipboard-2": 'c.send("Input.dispatchKeyEvent", commands=["paste"])',
}
# These must NOT fire: prose that mentions a banned call, and a legal IME use.
CLEAN = {
    "prose-mentions-navigation":
        "'''Do not use location.assign — it reloads the page.'''\n"
        "import os\nprint(os.getcwd())\n",
    "ime-with-commit":
        'c.send("Input.imeSetComposition", text=u)\n'
        'c.send("Input.insertText", text=u)\nc.close_composition("")\n',
    "read-only-helpers":
        "import json, re\n"
        "def canon(s):\n    return re.sub(r'\\s+', '', s or '')\n"
        "def show_tabs(port):\n    return [t for t in port]\n",
}


def self_test() -> int:
    failures: list[str] = []
    for name, body in FIXTURES.items():
        rid = next(r for r, *_ in RULES if name.startswith(r))
        p = Path(f"/tmp/_xguard_{name}.py")
        p.write_text("import time, subprocess\n" + body + "\n", encoding="utf-8")
        hits = check_file(p)
        if not any(f"[{rid}]" in h for h in hits):
            failures.append(
                f"rule {rid} did NOT fire on fixture {name} "
                f"(got: {hits or 'nothing'})")
        p.unlink(missing_ok=True)
    # The page-load exemption is by exact filename, so the same code under
    # any other name must still be blocked. Without this the exemption is a
    # hole: a new script could name itself whatever it liked.
    body = FIXTURES["no-page-load"]
    d = Path("/tmp/_xguard_exempt")
    d.mkdir(exist_ok=True)
    for fname, should_fire in (("ensure_browser.py", False),
                               ("publish.py", True),
                               ("ensure_browser_helper.py", True)):
        p = d / fname
        p.write_text("import time\n" + body + "\n", encoding="utf-8")
        hits = [h for h in check_file(p) if "[no-page-load]" in h]
        p.unlink(missing_ok=True)
        if should_fire and not hits:
            failures.append(
                f"page-load exemption leaked: {fname} was allowed to load a "
                f"page")
        if not should_fire and hits:
            failures.append(
                f"page-load exemption did not apply to {fname}: {hits}")

    for name, body in CLEAN.items():
        p = Path(f"/tmp/_xguard_clean_{name}.py")
        p.write_text(body, encoding="utf-8")
        got = check_file(p)
        if got:
            failures.append(f"false positive on {name}: {got}")
        p.unlink(missing_ok=True)
    if failures:
        print("SELF-TEST FAILED", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 2
    print(f"self-test ok — {len(FIXTURES)} fixtures fire, "
          f"{len(CLEAN)} clean cases stay clean")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--repo")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    files = staged_files(args.repo) if args.staged else collect(
        [Path(p) for p in args.paths])
    if not files:
        print("x-posting guard: no browser-driving scripts among the changes")
        return 0

    problems: list[str] = []
    me = Path(__file__).resolve()
    for f in files:
        if not f.exists():
            continue
        if f.resolve() == me:
            continue          # the rule table is the checker; do not scan it
        problems.extend(check_syntax(f))
        problems.extend(check_file(f))

    if not problems:
        print(f"x-posting guard: {len(files)} script(s) clean")
        return 0

    print("x-posting guard: BLOCKED", file=sys.stderr)
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    print("", file=sys.stderr)
    print("These are the rules that keep the user's browser and account safe.",
          file=sys.stderr)
    print("Each one was learned from a concrete failure — see the comment on",
          file=sys.stderr)
    print("each rule in verify_no_unsafe_posting.py for what it costs.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
