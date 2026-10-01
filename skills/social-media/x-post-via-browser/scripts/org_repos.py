#!/usr/bin/env python3
"""The GitHub owners whose repositories this account is allowed to promote.

Both reply paths read this list. They disagreed once: the browser checked for
any github.com link at all, the API checked three names. A reply that carried
someone else's repository passed one and failed the other, which is the shape
of a rule that is only accidentally enforced.

Every owner here is read off a real remote in ~/code, not guessed:

    crates-dev     ctares
    euv-dev        euv
    hyperlane-dev  hyperlane
    docs-pages     docs-pages
    eastspire      .agents and other personal repos

Adding an owner is one line. Removing one is one line, and a reply naming it
is then refused.
"""
from __future__ import annotations

import re

OWNERS = (
    "crates-dev",
    "euv-dev",
    "hyperlane-dev",
    "docs-pages",
    "eastspire",
)

# A repository URL the account is allowed to put in a post or a reply.
REPO_RE = re.compile(
    r"https://github\.com/(" + "|".join(OWNERS) + r")/[\w.-]+")


def find_repo(text: str) -> str | None:
    """Return the organisation repository in this text, or None.

    A bare github.com link to somewhere else is not a promotion of this
    account's work, and one that names no repository at all is not a
    promotion of anything.
    """
    m = REPO_RE.search(text or "")
    return m.group(0) if m else None


def check(text: str) -> str | None:
    """Return the repository if the text carries one, else a reason."""
    return find_repo(text) or (
        "no repository from this account's GitHub owners: " + ", ".join(OWNERS))
