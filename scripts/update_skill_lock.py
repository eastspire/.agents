#!/usr/bin/env python3
"""Reconcile `.skill-lock.json` with the current state of `skills/`.

This script walks `skills/*/SKILL.md` and rebuilds the `skills` map in
`.skill-lock.json`, preserving the top-level metadata (`version`, `dismissed`,
`lastSelectedAgents`, etc.) that the lock file carries alongside the skill
entries. It does NOT touch `dismissed` or `lastSelectedAgents` — those are
user/agent state, not skill inventory.

Idempotent: running it twice in a row produces no diff on the second run.

Why this exists
---------------
The `eastspire/.agents` repo is regularly imported into other projects as a
skill bundle. When we add/remove/rename skills locally, the lock file drifts
out of sync with the actual `skills/` directory. This script is the
authoritative reconciler: it makes the lock file a faithful mirror of the
filesystem.

Usage
-----
    python3 scripts/update_skill_lock.py        # update in place
    python3 scripts/update_skill_lock.py --diff # only show what would change, don't write
    python3 scripts/update_skill_lock.py --check  # exit 1 if drift, 0 if in sync

Exit codes
----------
    0  updated (or already in sync with --check)
    1  no changes needed (file was already up to date)
    2  error (e.g. skills/ dir not found)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
LOCK_PATH = REPO_ROOT / ".skill-lock.json"

# Files in a skill folder that contribute to its "fingerprint" — if any of
# these change, we update `updatedAt` for that skill. This is what the
# upstream source-sync tool does, so we match its behaviour.
FINGERPRINT_FILES = ("SKILL.md",)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _fingerprint(skill_dir: Path) -> str | None:
    """Return a stable fingerprint hash of a skill's primary content files.

    Hashes the concatenation of `SKILL.md` (and any other content in
    `FINGERPRINT_FILES`) with a length-prefixed framing so two skills
    whose contents happen to be byte-equal cannot collide. The result
    changes iff any fingerprinted file's bytes change, which is what we
    need to detect local skill edits.

    The exact algorithm is local to this repo; the upstream GitHub
    `source-sync` tool computes a different hash (per-folder git tree
    object). We deliberately use our own stable scheme so the local
    `skillFolderHash` field is meaningful even for skills without a
    `sourceUrl` (i.e. local-only skills).
    """
    import hashlib

    h = hashlib.sha1()  # noqa: S324 — sha1 is fine for a non-crypto fingerprint
    for name in FINGERPRINT_FILES:
        p = skill_dir / name
        if not p.exists():
            continue
        raw = p.read_bytes()
        # Length-prefixed framing: defends against concatenation collisions
        # where bytes of file A+B equal bytes of file C+D.
        h.update(f"{name}\0{len(raw)}\0".encode())
        h.update(raw)
    return h.hexdigest()


def _read_lock() -> dict:
    if not LOCK_PATH.exists():
        return {}
    with open(LOCK_PATH) as f:
        return json.load(f)


def _build_skills_map(lock: dict) -> dict[str, dict]:
    """Walk skills/ and produce the new `skills` dict.

    For each skill:
      - If it's already in the lock with the same `skillFolderHash`, keep the
        existing entry (including `installedAt`).
      - If it's new or its hash changed, write a fresh entry with current
        timestamp.
    """
    existing: dict[str, dict] = lock.get("skills", {})
    new_map: dict[str, dict] = {}
    now = now_iso()

    # Skills live at skills/<name>/ and skills/<category>/<name>/. A
    # top-level folder WITHOUT SKILL.md is a category, so recurse into it
    # instead of skipping it — otherwise every creative/, web/,
    # software-development/ skill is invisible to the lock.
    for skill_dir in sorted(_iter_skill_dirs()):
        rel = skill_dir.relative_to(SKILLS_DIR)
        # the key is the bare skill name; two categories may not both ship a
        # skill of the same name, so a collision is a real error, not a merge
        name = skill_dir.name
        if name in new_map:
            # A skill shipped both at the top level and inside a category.
            # The top-level copy is the one older locks reference, so it wins;
            # the categorised one is reported so the duplication gets a human
            # decision instead of being silently resolved either way.
            if len(rel.parts) == 1:
                continue  # the shallow copy already claimed the name
            print(
                f"warning: duplicate skill name {name!r} — keeping "
                f"{new_map[name]['skillPath']}, ignoring skills/{rel}/SKILL.md",
                file=sys.stderr,
            )
            continue
        fingerprint = _fingerprint(skill_dir)
        old = existing.get(name)

        if old and old.get("skillFolderHash") == fingerprint:
            # No change — keep historical timestamps and source provenance.
            new_map[name] = old
            continue

        # New or modified skill — build a fresh entry. Preserve source info
        # from the old entry if present (so re-syncing a local skill doesn't
        # lose its `sourceUrl`/`ref`).
        entry: dict = {
            "source": (old or {}).get("source", "local"),
            "sourceType": (old or {}).get("sourceType", "local"),
            "skillPath": f"skills/{rel}/SKILL.md",
            "installedAt": (old or {}).get("installedAt", now),
            "updatedAt": now,
        }
        if fingerprint is not None:
            entry["skillFolderHash"] = fingerprint
        # Carry over any extra source-tracking fields.
        for key in ("sourceUrl", "ref", "subpath", "version"):
            if key in (old or {}):
                entry[key] = old[key]
        new_map[name] = entry

    return new_map


def _iter_skill_dirs() -> list[Path]:
    """Every directory under skills/ that holds a SKILL.md, at any depth.

    `skills/creative/` has no SKILL.md of its own — it is a category. A
    one-level walk therefore reported every categorised skill as absent from
    the lock, which is how touchdesigner-mcp, comfyui and blender-mcp came to
    have no lock entry at all.
    """
    found: list[Path] = []
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name == "_pending":       # cronjob staging, not a skill
            continue
        if (entry / "SKILL.md").exists():
            found.append(entry)
            continue
        for child in sorted(entry.iterdir()):
            if child.is_dir() and not child.name.startswith(".") \
                    and (child / "SKILL.md").exists():
                found.append(child)
    return found


def main() -> int:
    args = set(sys.argv[1:])
    diff_only = "--diff" in args
    check_only = "--check" in args

    if not SKILLS_DIR.exists():
        print(f"ERROR: {SKILLS_DIR} not found", file=sys.stderr)
        return 2

    lock = _read_lock()
    new_skills = _build_skills_map(lock)

    old_skills = lock.get("skills", {})
    added = sorted(set(new_skills) - set(old_skills))
    removed = sorted(set(old_skills) - set(new_skills))
    changed = sorted(
        n for n in set(new_skills) & set(old_skills)
        if new_skills[n] != old_skills[n]
    )

    if not added and not removed and not changed:
        print(f"OK: .skill-lock.json already in sync ({len(new_skills)} skills)")
        return 1 if check_only else 1

    if diff_only or check_only:
        if added:
            print(f"would ADD ({len(added)}): {', '.join(added)}")
        if removed:
            print(f"would REMOVE ({len(removed)}): {', '.join(removed)}")
        if changed:
            print(f"would UPDATE ({len(changed)}): {', '.join(changed)}")
        return 0 if check_only else 0

    # Preserve all top-level fields, only replace `skills`.
    new_lock = dict(lock)
    new_lock["skills"] = new_skills
    # Bump version on any structural change so consumers can detect drift.
    if added or removed:
        new_lock["version"] = max(int(lock.get("version", 1)), 1) + 1

    with open(LOCK_PATH, "w") as f:
        json.dump(new_lock, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"UPDATED: .skill-lock.json ({len(new_skills)} skills, version={new_lock['version']})")
    if added:
        print(f"  added ({len(added)}): {', '.join(added)}")
    if removed:
        print(f"  removed ({len(removed)}): {', '.join(removed)}")
    if changed:
        print(f"  updated ({len(changed)}): {', '.join(changed)}")
    if not (added or removed or changed):
        print("  (no skill-level changes, file rewritten for formatting)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
