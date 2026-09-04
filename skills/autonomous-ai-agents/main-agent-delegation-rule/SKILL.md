---
name: main-agent-delegation-rule
description: "Use when any task enters the main agent. Delegate everything via delegate_task (2026-09-04 hard rule). Single tool calls, dialogue, skill/memory ops, and orchestration prose are exempt."
license: MIT
metadata:
  version: 1.0.0
  supersedes: 2026-09-03 narrower rule (PR cycle only)
---

# Main Agent Delegation Rule

**User hard directive (2026-09-04 Feishu):** "以后所有任务都需要派发给子 agent 去执行,确保主 agent 上下文干净。"

This **supersedes** the older 2026-09-03 narrower rule (which only required delegation for PR cycles and other heavy multi-tool work). The current rule is **comprehensive**: every task the main agent receives MUST be evaluated for delegation, with only a small exemption list.

## 0. The Rule (one sentence)

**Default = `delegate_task`.** The main agent does **planning, dispatch, verification, reporting, memory/skill updates, and dialogue reply** — it does **NOT** execute multi-step tool work itself.

## 1. Trigger Condition

**Any** task entering the main agent must first ask: _"Should this be delegated?"_ If the answer is "yes" (which is the default — see §2), wrap it in a `delegate_task` call before doing anything else.

There is no complexity threshold that exempts delegation. The decision is driven by **tool-call count + output token volume**, not by the apparent complexity of the task.

## 2. Must Delegate (exhaustive checklist)

Delegate when the task is **any** of:

- **Multi-step work** — anything that needs more than ~2-3 sequential tool calls.
- **High-volume output tasks** — `cargo build` / `clippy` / lint logs, `gh` CLI output, intermediate patches, browser screenshots, raw web pages, search result lists.
- **File changes** — `patch`, `write_file`, multi-file edits, refactors, version bumps.
- **PR cycle** — `gh pr create`, wait for CI, read CI logs, fix failures, merge, clean up branch.
- **Debug loops** — read error → hypothesize → patch → rebuild → verify (any iteration > 1 round).
- **Batch operations** — bulk web searches, multi-page scraping, headless-browser validation, mass `rm` / `install` / `build` / `test` / `cargo` runs.
- **Long-running commands** — anything with timeout > ~30 s (installs, builds, full test suites, mirror syncs).
- **Sub-tasks the user explicitly framed as "do X and report back"** — anything where the user is expecting a self-contained deliverable, not a running narrative.
- **Anything you would naturally batch into a research / coding / ops "session"** — that's a subagent.

## 3. Exempt — Main Agent May Run Directly

The main agent may run only when the task is **strictly** one of:

- **A single tool call** — read one file, run one quick check, confirm one state. _Two or more_ sequential tool calls on the same task → delegate.
- **Pure dialogue** — text reply with no tool use (rare; usually the response summarizing a subagent's report).
- **Memory / skill management** — `skill_manage`, `memory` tool, session bookkeeping. These are the main agent's own meta-tools.
- **Orchestration prose** — drafting the `goal` / `context` / `output_schema` for an upcoming `delegate_task` call. The prose that _plans_ delegation is fine; the work that _executes_ it is not.

When in doubt → delegate. The cost of an unnecessary delegation is small (one extra round-trip). The cost of _not_ delegating is the main-agent context filling with tool output it could have summarized.

## 4. Decision Method (mechanical)

Count what you'd produce if you ran it yourself:

| Signal                                  | Threshold      | Action   |
| --------------------------------------- | -------------- | -------- |
| Sequential tool calls on this task      | > 2-3          | delegate |
| Cumulative output tokens you would emit | > ~500 (rough) | delegate |
| Wall-clock time of the work             | > ~30 s        | delegate |
| Number of files touched                 | > 1            | delegate |
| Loop iterations expected                | any            | delegate |
| Branches / PRs involved                 | any            | delegate |

If **any** signal trips → delegate. **Do not** evaluate "is this task simple?" — a "simple" task with 8 tool calls and 4000 log lines is still delegate territory.

## 5. Anti-pattern / Lesson Learned (2026-09-03)

**The bug that prompted this rule:** Main agent was asked to refactor fullscreen-canvas resize logic across the euv game module. The work touched:

- `game_2d/3d` hook `fn.rs`
- `style/class fn.rs`
- `acquire_game_2d/3d_ssaa_canvas` → runtime dimensions
- `resolve_wall_collision` / `map_client_to_canvas` / `clear_rect` / `click` → runtime-aware
- Synthesize resize events and dispatch

The main agent ran **30+ tool calls itself** — file reads, patches, builds, validation, edits. The user had to intervene: _"应该等待子 agent 完成"_. The correct flow was: write one `delegate_task` with the full scope, wait for the subagent's summary, reply to user.

**Lesson:** even when the task feels coherent and the user didn't say "use a subagent", the tool-call / output-volume signals (§4) are what matters. Main agent context is **the** scarce resource — protect it by default.

## 6. What the Main Agent Keeps

Even after delegating everything, the main agent is **not idle**. It still does:

1. **Planning** — decompose the user's ask into 1+ delegate-able tasks.
2. **Dispatch** — write `goal` / `context` / `output_schema`, choose role, fire `delegate_task`.
3. **Verification** — check the subagent's summary, run quick sanity reads if needed.
4. **Reporting** — condense subagent output into a user-facing reply.
5. **Memory + skill updates** — record new procedures, patch stale skills.
6. **Dialogue** — pure text replies that don't need tools.

The main agent is the **router + summarizer**, not the worker.

## 7. Related Skills

- **`multi-agent-team-setup`** — profile / SOUL.md / AGENTS.md setup for multi-agent teams. This rule says _when_ to delegate; that skill says _how_ to set up the team.
- **`hermes-agent` (autonomous-ai-agents/)** — `delegate_task` tool API, background systems, Kanban / Cron / Curator. Reference for the actual delegation primitive.
- **`autonomous-ai-agents/{claude-code, codex, opencode, computer-use}`** — leaf-worker skills; the kinds of subagents you typically dispatch to.

## 8. One-Line Cheat Sheet

> **Main agent = plan, dispatch, verify, report. Everything else = delegate.**
