# ⚠️ SKILL.md §17 OVERRIDE NOTICE — version bump rule (2026-09-02)

> The rule currently in SKILL.md §17 is **wrong**. The correct rule
> (verified end-to-end via PR #101 squash merge) is in
> `references/version-bump-rule-2026-09-02.md`.
> This file is a **pointer summary** so future sessions that don't
>> drill into references still get the right rule.

## The rule in 4 lines

1. Bump **only** `Cargo.toml` line 3 (`[package] version`).
2. **Do NOT** touch `[workspace.dependencies]` path-dep `version`s.
3. **Do NOT** touch `core/`, `ui/`, `engine/`, `cli/`, `macros/`, `example/` Cargo.toml.
4. CI's `sync_workspace_version` job auto-propagates after squash merge to master. The job's PR-side `skipped` status is **by design**, not a failure.

## What you MUST NOT do (this is what triggered user correction)

```bash
# ❌ WRONG — overwrites [workspace.dependencies] path-dep versions too
sed -i 's/version = "0.18.36"/version = "0.18.37"/g' Cargo.toml

# ❌ WRONG — duplicates CI's job
for c in core ui engine cli macros example; do
  sed -i "s/version = \"0.18.36\"/version = \"0.18.37\"/" "$c/Cargo.toml"
done
```

User feedback verbatim: "升级小版本从记忆读取规则,不是全升级"

## What you DO

```bash
# ✅ ONLY this — bump root line 3
sed -i 's/^version = "0.18.36"$/version = "0.18.37"/' Cargo.toml
```

## Full evidence

See `references/version-bump-rule-2026-09-02.md` for:

- PR #101 squash merge commit (`9411c9a`)
- PR diff (1 file +1/-1, the root Cargo.toml only)
- Post-merge CI run 33590700876 with `sync_workspace_version` success
- Verification of all 7 files ending up at `0.18.37` after CI auto-sync
- Why the previous rule was wrong (PR-side `skipped` ≠ "PR must manually sync")
- Exception: when to still bump all 7 (adding a new workspace member)