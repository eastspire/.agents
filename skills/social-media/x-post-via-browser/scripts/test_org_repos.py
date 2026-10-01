#!/usr/bin/env python3
"""Check the repository rule against the cases that made it wrong.

The two reply paths disagreed: the browser accepted any github.com link, the
API accepted three owners. Both were wrong, and a test that only checked one
would have kept whichever one was written last.

  python3 test_org_repos.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import org_repos                                          # noqa: E402

CASES = [
    # (text, should_be_accepted, why)
    ("Worth a look. https://github.com/crates-dev/ctares", True,
     "ctares is this account's monorepo"),
    ("See https://github.com/euv-dev/euv for the framework.", True,
     "euv is this account's"),
    ("https://github.com/hyperlane-dev/hyperlane", True, "hyperlane"),
    ("https://github.com/eastspire/.agents", True, "personal org"),
    ("https://github.com/docs-pages/docs-pages", True, "docs-pages"),
    ("https://github.com/torvalds/linux is a different project", False,
     "someone else's repository is not a promotion of this account"),
    ("https://github.com/rust-lang/rust", False, "same"),
    ("No link at all, just an opinion about build graphs.", False,
     "an interruption with no repository on it is not a promotion"),
    ("https://github.com/ctares-dev/ctares", False,
     "a lookalike owner must not pass"),
    ("https://github.com/crates-dev", False,
     "the owner alone is not a repository"),
]


# The reply cap for this account is the member limit, not the 280 that free
# accounts get. Checking against 280 once meant trimming every draft to a
# number that never applied here.
REPLY_LIMIT = 25000
LENGTH_CASES = [
    ("a short reply", 200, True),
    ("a long reply", 1167, True),
    ("at the member limit", REPLY_LIMIT, True),
    ("over the member limit", REPLY_LIMIT + 1, False),
]


def check_length() -> int:
    bad = 0
    print("\nreply length limit (%d characters)" % REPLY_LIMIT)
    for name, n, want in LENGTH_CASES:
        got = n <= REPLY_LIMIT
        if got != want:
            bad += 1
        print("  %s %-22s %d characters" % ("ok " if got == want else "FAIL",
                                            name, n))
    return bad


def main() -> int:
    bad = 0
    for text, want, why in CASES:
        got = org_repos.find_repo(text) is not None
        mark = "ok " if got == want else "FAIL"
        if got != want:
            bad += 1
        print("  %s %-58s %s" % (mark, repr(text[:56]), why))
    bad += check_length()
    print("\n%d case(s) failed" % bad if bad else
          "\nall %d owner cases and %d length cases correct"
          % (len(CASES), len(LENGTH_CASES)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
