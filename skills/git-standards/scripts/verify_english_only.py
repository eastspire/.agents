#!/usr/bin/env python3
"""Enforce the English-only rule for commit messages, PR titles and PR bodies.

User rule (2026-09-28): 「更新 git 提交规范,创建 pr,标题和说明必须要纯英文。
commit 作者必须要是我的个人账号,提交信息必须要英文,符合 git 提交规范」

Why a script and not just prose: `git-standards` §1/§2/§7 already stated
"all English" and "canonical author identity", and both were still violated
in practice — the two PRs opened minutes earlier had Chinese titles and
Chinese bodies. A rule that is only written down fails silently at exactly
the moment it is needed. This checker is the enforcement point.

Three sub-checks:

1. `text`     — the given text contains no CJK / full-width characters.
2. `commit`   — a commit message file passes §1 (Conventional Commits,
               subject <= 72 chars, imperative, no trailing period) and §7
               (author identity comes from ~/.gitconfig).
3. `pr`       — a PR title + body pass §2 (conventional-commit title,
               <= 72 chars, 4-section template present, no CJK).

Usage:
    verify_english_only.py text  <file>...              # just the CJK scan
    verify_english_only.py commit <msgfile> [--repo R]  # + format + author
    verify_english_only.py pr <title> --body <file>     # + template shape

Exit 0 = clean, 1 = violations (one per line), 2 = usage error.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# CJK detection
# --------------------------------------------------------------------------

# Ranges that must never appear in a commit message or PR text. Each entry is
# (label, lo, hi) as code points, so the table is readable and the ranges stay
# contiguous.
CJK_RANGES = (
    ("CJK Unified Ideographs", 0x4E00, 0x9FFF),
    ("CJK Ext A", 0x3400, 0x4DBF),
    ("CJK Compatibility Ideographs", 0xF900, 0xFAFF),
    ("CJK Unified Ext B", 0x20000, 0x2A6DF),
    ("Kangxi Radicals", 0x2F00, 0x2FDF),
    ("CJK Radicals Supplement", 0x2E80, 0x2EFF),
    ("Halfwidth/Fullwidth Forms", 0xFF00, 0xFFEF),
    ("Hiragana", 0x3040, 0x309F),
    ("Katakana", 0x30A0, 0x30FF),
    ("Hangul Syllables", 0xAC00, 0xD7AF),
    ("Hangul Jamo", 0x1100, 0x11FF),
    ("Bopomofo", 0x3100, 0x312F),
    ("Fullwidth punctuation", 0x3000, 0x303F),
    ("Yi Syllables", 0xA000, 0xA48F),
)

CANONICAL_NAME = "eastspire"
CANONICAL_EMAIL = "root@ltpp.vip"
TYPES = (
    "feat fix refactor perf docs test build ci chore style revert".split()
)
MAX_SUBJECT = 72


def find_non_english(text: str) -> list:
    """Return [(line_no, col, label, char)] for every CJK-ish codepoint."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for col, ch in enumerate(line, 1):
            cp = ord(ch)
            for label, lo, hi in CJK_RANGES:
                if lo <= cp <= hi:
                    out.append((i, col, label, ch))
                    break
    return out


def scan_text(text: str, label: str) -> list:
    hits = find_non_english(text)
    return [
        "{}: line {} col {} has {} char {!r} — commit/PR text must be English".format(
            label, ln, col, name, ch
        )
        for ln, col, name, ch in hits
    ]


# --------------------------------------------------------------------------
# Commit message checks (§1)
# --------------------------------------------------------------------------

SUBJECT_RE = re.compile(
    r"^(?P<type>" + "|".join(TYPES) + r")(?:\((?P<scope>[^()]+)\))?(?P<bang>!)?: (?P<subject>.+)$"
)


def check_commit_message(text: str, label: str = "commit message") -> list:
    out = []
    lines = text.splitlines()
    subject = lines[0] if lines else ""
    if not subject.strip():
        return ["{}: is empty".format(label)]

    m = SUBJECT_RE.match(subject)
    if not m:
        out.append(
            "{}: subject {!r} does not match Conventional Commits "
            "'<type>(<scope>): <subject>' with type in [{}]".format(
                label, subject, ", ".join(TYPES)
            )
        )
    else:
        if len(subject) > MAX_SUBJECT:
            out.append(
                "{}: subject is {} chars, limit is {}: {!r}".format(
                    label, len(subject), MAX_SUBJECT, subject
                )
            )
        s = m.group("subject")
        if s.endswith("."):
            out.append("{}: subject must not end with a period: {!r}".format(label, subject))
        # imperative mood: the first word should be a base verb, not a
        # third-person form. Deliberately a light heuristic — an allowlist of
        # legitimate -s words is safer than trying to detect every verb ending.
        first = s.split()[0] if s.split() else ""
        if first.endswith("s") and not first.endswith("ss") and first.lower() not in (
            "adds", "removes", "updates", "uses", "this", "its", "docs", "less", "class",
        ):
            out.append(
                "{}: subject should be imperative mood, {!r} looks third-person: {!r}".format(
                    label, first, subject
                )
            )

    for i, line in enumerate(lines[1:], 2):
        if len(line) > 72:
            out.append(
                "{}: line {} is {} chars, body must wrap at 72: {!r}".format(
                    label, i, len(line), line[:60] + "…"
                )
            )
    return out


# --------------------------------------------------------------------------
# Author identity (§7)
# --------------------------------------------------------------------------


def check_author(repo: Path | None, explicit: str | None) -> list:
    out = []
    if explicit:
        if explicit != CANONICAL_EMAIL:
            out.append(
                "author: commit email {!r} is not the canonical personal account "
                "{!r} (§7 — no per-commit override)".format(explicit, CANONICAL_EMAIL)
            )
        return out
    if repo is None:
        return out
    try:
        got = subprocess.run(
            ["git", "-C", str(repo), "config", "user.email"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        name = subprocess.run(
            ["git", "-C", str(repo), "config", "user.name"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
    except OSError as exc:  # pragma: no cover - defensive
        return ["author: could not read git config: {}".format(exc)]
    if got != CANONICAL_EMAIL:
        out.append(
            "author: repo author is {!r}, expected the canonical personal account "
            "{!r} (§7)".format(got or "<unset>", CANONICAL_EMAIL)
        )
    if name != CANONICAL_NAME:
        out.append("author: user.name is {!r}, expected {!r} (§7)".format(name or "<unset>", CANONICAL_NAME))
    return out


# --------------------------------------------------------------------------
# PR checks (§2)
# --------------------------------------------------------------------------

REQUIRED_SECTIONS = ("Summary", "Changes", "Verification", "Notes")


def check_pr(title: str, body: str) -> list:
    out = list(scan_text(title, "PR title"))
    out += list(scan_text(body, "PR body"))

    if len(title) > MAX_SUBJECT:
        out.append("PR title: {} chars, limit is {}".format(len(title), MAX_SUBJECT))
    if not SUBJECT_RE.match(title):
        out.append(
            "PR title: {!r} does not match '<type>(<scope>): <subject>'".format(title)
        )

    present = set(re.findall(r"^#{1,3}\s+(\w+)\s*$", body, re.M))
    for sec in REQUIRED_SECTIONS:
        if sec not in present:
            out.append(
                "PR body: missing required '## {}' section (§2.2 — all four are "
                "required: {})".format(sec, ", ".join(REQUIRED_SECTIONS))
            )
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _read(p: str) -> str:
    path = Path(p)
    if not path.exists():
        sys.stderr.write("verify_english_only: no such file: {}\n".format(p))
        raise SystemExit(2)
    return path.read_text(encoding="utf-8", errors="replace")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        sys.stderr.write(__doc__)
        return 2
    mode, rest = argv[0], argv[1:]

    if mode == "text":
        violations = []
        for p in rest:
            violations += scan_text(_read(p), p)
    elif mode == "commit":
        repo = None
        author = None
        if "--repo" in rest:
            i = rest.index("--repo")
            repo, rest = Path(rest[i + 1]), rest[:i] + rest[i + 2:]
        if "--author" in rest:
            i = rest.index("--author")
            author, rest = rest[i + 1], rest[:i] + rest[i + 2:]
        if not rest:
            sys.stderr.write("verify_english_only: commit needs a message file\n")
            return 2
        msg = _read(rest[0])
        violations = scan_text(msg, rest[0]) + check_commit_message(msg, rest[0]) + check_author(repo, author)
    elif mode == "pr":
        if not rest:
            sys.stderr.write("verify_english_only: pr needs a title\n")
            return 2
        title = rest[0]
        body = ""
        if "--body" in rest:
            body = _read(rest[rest.index("--body") + 1])
        violations = check_pr(title, body)
    else:
        sys.stderr.write("verify_english_only: unknown mode {!r}\n".format(mode))
        return 2

    for v in violations:
        print(v)
    if violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
