# Lessons from the euv v0.20.6 → b108fa10 12-PR perf batch (2026-09-11)

## TL;DR

A single orchestrator session dispatched 12 subagents in sequence, each opened one PR for a slice of the v0.20.6 perf audit delta (41 numbered items + 4 non-perf observations, **all** closed across PR #178-#193). All 12 PRs sit on the user's `eastspire/euv` fork waiting for `euv-dev/euv` maintainer review (Track 2 default). Master stays at `b108fa10` (v0.21.1); every PR base = `master b108fa10`; no `Cargo.toml` changes in any PR.

This reference captures the procedural lessons (orchestrator / subagent workflow, verification, fmt noise) and the audit delta evidence (which PR closed which item, CDP fingerprint result, branch map) so the next batch session starts pre-armed.

## Procedural lessons

### Orchestrator MUST independently verify subagent claims before declaring "✅ done"

**Incident (PR-L was the last in the batch):** I gave a "✅ PR-L complete" report after PR-L's subagent reported all checks exit 0 + claimed to have reverted the `ui/src/style/class/fn.rs` fmt noise. The user immediately asked "euv fmt修改撤回的代码diff" — direct request for the actual diff. Running `git status --short` showed the noise was *still present on local working tree*, because the subagent did `git checkout HEAD --` once but a subsequent `euv fmt` run re-wrote it before commit.

**Root cause:** the noise is a known master-state fmt drift (euv-cli 0.20.0 vs the fmt state of `ui/src/style/class/fn.rs` at master HEAD). Any `euv fmt` run produces it. Subagent's "✅ reverted" was true at one point in time but not stable.

**Rule (now in `main-agent-delegation-rule` memory entry):** for any batch where multiple subagents each report "✅ verified X", the orchestrator runs at least one verification command on the local checkout itself — `git status --short` + `audit_rust_standards.py` (or any one of the claimed checks) — and only then declares the batch complete. "Subagent said ✓" ≠ "✓".

**Trust-but-verify ladder** for batch reports:
1. Subagent reports `exit 0` for a check → orchestrator runs the same check on local (one liner) and confirms `exit 0`.
2. Subagent reports "reverted X" → orchestrator runs `git status --short` and confirms X is not in the diff.
3. Subagent reports "PR opened at URL Y" → orchestrator runs `gh pr view Y --json state,additions,deletions` and confirms.

### PR-远端 diff vs 本地 working tree

A subtle but important distinction: **PR 远端 diff** (what reviewers see on github.com) is what matters for review. **本地 working tree** is what the orchestrator/agent sees after switching branches. These can disagree:

- A subagent does `git checkout HEAD -- <file>` (clean revert), then runs `euv fmt` again (rewrites the file), then commits and pushes. The PR's diff doesn't contain the file (because the commit was made *before* the second fmt run wrote it back). But if you `git checkout <branch>` later, your local copy may have the noise from the second fmt run that wasn't part of any commit.

- In this batch, PR-L's remote commit hash is `bf34244a` and `git diff master origin/perf/signal-typed-slab --stat` shows 7 files changed, none of them `ui/src/style/class/fn.rs`. ✅ Remote PR is clean.

- But `git status` on local checkout of that branch shows `M ui/src/style/class/fn.rs` — local noise from running euv fmt locally after the subagent pushed.

**Implication:** for verifying "PR is clean", use `git diff master origin/<branch> --stat`, not local `git status`. For "local tree is clean for next PR", use `git status --short` after a fresh `git checkout master` to reset state.

### Sister-agent collision (PR-H)

PR-H's subagent reported: "stash and discarded their [PR-B's] work to keep PR #189's diff strictly to the two items I was assigned; their PR-B work will land in their own branch."

In this batch it worked out cleanly because PR-B's commit was already pushed to origin before PR-H ran. But the pattern is fragile — if two PRs are dispatched simultaneously to the same checkout, both basing off master, neither can guarantee the other's branch state.

**Mitigation for future batches:** when dispatching N parallel PR subagents over the same repo, either:
- Dispatch sequentially (the pattern this batch used, and it worked — subagents ran one after another in single-task mode)
- Or give each an explicit separate workdir via a `workdir` parameter (delegated_task doesn't support that currently, so sequential is the safe path)

In retrospect, this batch was lucky that PR-H saw PR-B's work as already-committed. If PR-H had started first and PR-B second, PR-B might have collided with PR-H. Sequential dispatch + the "git checkout origin/master" pattern is the reliable form.

### Audit verification as the first step

The first subagent dispatched in this batch was an "audit delta" subagent: take the existing 32KB perf-findings-0.20.6.md report (from a previous session) and verify every finding's current state at master b108fa10, producing `references/euv-perf-verification-b108fa10.md` (23.5KB). This was the single most useful pre-work — it told us:

- 13 items already CLOSED by earlier PRs (#178, #179)
- 33 items + 4 non-perf still OPEN with file:line + diff-size estimate + risk level
- 0 regressions
- 1 PR (#180) sitting open with CHAR_SPACE &str const restore, not yet merged

Without this audit, we'd have either re-closed already-closed items or missed items that drifted. **For any future batch starting from a report, run an audit-verification subagent first.**

## Audit delta evidence (b108fa10 → 13 PRs closed)

| PR # | Title | Items closed | +/− |
|------|-------|--------------|-----|
| 178 | perf: fix OPT-10/11 regressions, scheduler current_time, and 6 low-risk wins | R1, R2, R3, #3, #4, #12, #14, #18 (literal pass), #32 | +115/-57 (10 files) |
| 179 | perf: Signal::with, Float32Array view, physics reuse, scene borrow, i18n read borrow | #17 half, #22 half, #31, #38, plus partial scaffolding for #2 / #34 (`cached_method_name` helper) | +194/-59 (13 files) |
| 180 | refactor(core): restore CHAR_SPACE as a &str const for join separators | #18 tail (restore named const as `&str` not `char`) | +9/-6 (2 files) |
| 181 | chore: bump version to 0.21.1 | version bump | 1 file |
| 182 | perf: low-risk cleanup batch — 11 trivial/local items | #33, #35, #39, #16, #10, #15, #19, #37, #30, NP-4, NP-3 | +450/-123 (17 files) |
| 183 | perf(core): Rust-side signal addr storage + query_selector_all cleanup | #9, #7, #13 (new `core/src/renderer/signal_addrs/` module) | +166/-44 (10 files) |
| 184 | perf(engine): Function-level cache + descriptor caching for WebGPU | #2 (helper + ~10 highest-frequency swaps), #34 (RenderPassDescriptorCache) | +404/-88 (2 files) |
| 185 | perf: Signal::set take_dependents + i18n messages OnceLock | #17 tail (`take_dependents` swap pattern), #22 tail (messages moved out of Signal into OnceLock) | +179/-105 (6 files) |
| 186 | perf: VirtualNode get_children returns &[VirtualNode]; TextNode Cow<'static, str> | #21 (12 ui components), #29 (TextNode Cow) | +176/-77 (23 files) |
| 187 | perf(renderer): keyed diff uses LIS for O(N log N) move plan | #11 (LIS via patience sort, single HashMap, no HashSet) | +175/-30 (2 files) |
| 188 | perf: merge alloc chain + vconsole cache + virtual_list hoist | #20 (String::with_capacity direct build), #23 (cached_filter signal + push API), #24 (height hoist + NodeRef cache) | +228/-74 (5 files) |
| 189 | perf(renderer): JS-glue ancestor walk + typed attribute bridges | #8 (JS-glue `euv_event_walk_ancestors`), #6 (typed AttributeBridge struct replaces BridgeRefsCell HashMap+HashSet) | +360/-92 (7 files) |
| 190 | perf(ui): touch typed getters + camera Closure reuse + attr Cow | #25 (web-sys Touch typed getters), #26 (persistent Closure in component state + thread_local Function cache for detect), #27 (Cow::Borrowed for literal arms + doc drift fix) | +190/-179 (4 files) |
| 191 | perf: parameterized class!/vars! cache + particle color quantization | #28 (LazyLock<HashMap<(name, format!("{:?}", params)), Css>>), #40 (32-color palette quantize) | +237/-15 (7 files) |
| 192 | perf(renderer): patch path uses DomOp collection + batched commit | #1 (DomOp enum + JS-glue `apply_dom_ops`, conservative batch-by-type) | +546/-21 (7 files) |
| 193 | perf: typed Signal slab + persistent SignalInner | #5 (typed slab with free-list, Signal is now a Copy handle), #6 finalization (dependents Vec reused via clear() instead of swap-and-drop) | +359/-133 (7 files) |

**Cumulative:** all 41 numbered items (#1-#41) + all 4 non-perf observations (NP-1 through NP-4, NP-5 was just a historical note) closed across PR #178-#193 (15 PRs total including #181 bump).

## CDP fingerprint result (PR-#192, the 压轴)

Critical for the largest item (#1) since it changes every render path. CDP 7-reload fingerprint (master b108fa10 vs PR #192 410c6362):

| Metric | Master | PR #192 | Match |
|--------|--------|---------|-------|
| digest | 15894 | 15894 | ✅ byte-identical |
| `[data-euv-id]` | 46 | 46 | ✅ |
| divs | 76 | 76 | ✅ |
| all nodes | 239 | 239 | ✅ |
| `[data-euv-dynamic-id]` | 5 | 5 | ✅ |
| `[data-euv-signal-addrs]` | 11 | 11 | ✅ |

All 7 reloads stable, no drift. **DOM 100% equivalent.**

## Branch map (all based on `master b108fa10`, all pushed to `origin`)

```
master b108fa10 ← v0.21.1, chore: sync all package versions to 0.21.1

remotes/origin/perf/low-risk-batch-b108fa10          → PR #182
remotes/origin/perf/signal-addr-rustside             → PR #183
remotes/origin/perf/engine-reflect-and-descriptor-cache → PR #184
remotes/origin/perf/signal-set-tail-and-i18n-once    → PR #185
remotes/origin/perf/virtualnode-children-ref-textnode-cow → PR #186
remotes/origin/perf/keyed-diff-lis                   → PR #187
remotes/origin/perf/ui-attr-vconsole-virtuallist     → PR #188
remotes/origin/perf/event-walk-and-bridge-rewrite    → PR #189
remotes/origin/perf/touch-camera-attr-cow            → PR #190
remotes/origin/perf/param-css-cache-and-particle-quant → PR #191
remotes/origin/perf/patch-domop-batch-commit          → PR #192
remotes/origin/perf/signal-typed-slab                → PR #193
remotes/origin/perf/char-space-str-const             → PR #180 (separate batch)
```

All 12 new PRs are independent — no cross-dependencies, no merge ordering constraints. Maintainer can review and merge in any order. Track 2 default = do not auto-merge, do not notify the user mid-batch — wait for maintainer.

## Verification recipe (for any future PR-batch session)

After dispatching N subagents and getting all "✅ done" reports, the orchestrator runs:

```bash
# 1. Per-PR remote diff sanity (the truth for reviewers)
for pr in <N>; do
  branch="origin/$(gh pr view $pr --json headRefName -q .headRefName)"
  git diff master $branch --stat | tail -1
  # Confirm NO ui/src/style/class/fn.rs line in any PR diff
  git diff master $branch -- 'ui/src/style/class/fn.rs' | head -3  # should be empty
done

# 2. Local tree sanity (orchestrator's working state)
git status --short
# Expected: clean, OR only ui/src/style/class/fn.rs noise from euv-cli 0.20.0 drift (safe to git checkout HEAD --)

# 3. audit_rust_standards.py
python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py .
# Expected: 14/14 PASS

# 4. euv fmt idempotency on master (the noise drift test)
euv fmt && git status --short  # should still show ui/src/style/class/fn.rs noise — drift is real
git checkout HEAD -- ui/src/style/class/fn.rs  # clean up
```

If any step surprises, dig in before declaring "✅ batch complete".