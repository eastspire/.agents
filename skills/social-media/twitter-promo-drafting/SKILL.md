---
name: twitter-promo-drafting
description: 'Draft X promo tweets for software projects.'
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [twitter, x, social-media, marketing, promo, draft]
---

# Twitter/X Promo Drafting for Software Projects

## When to Use

User asks for "推特宣传 / Twitter promo / tweet for / 推广文 / tweet to promote X" where the target is a **software project** (library, framework, tool, service). Do NOT use for LinkedIn / Reddit / HN / blog posts (different format) or for actually posting tweets (use `social-media/xurl` instead).

## Workflow

1. **Load the project's skill** (`skill_view(name=<project-skill>)`) to get accurate value props, technical claims, and the real GitHub URL.
   - If no project skill exists, fall back to: search `/root/.cargo/registry/src/` for the crate README, or `gh repo view <owner>/<repo>` to verify the URL.
2. **Check if xurl can post**: `which xurl && xurl auth status`.
   - Yes → after user picks a draft, offer to actually post via `xurl post "..."`.
   - No → draft copy-paste content; user will post themselves.
3. **Draft Version A** (recommended): single 256-280 char tweet, English, code-block wrapped for direct copy.
4. **Offer 2-3 alternative angles** (see taxonomy below).
5. **On user pick** (e.g. "A"): deliver the final version in the same code-block format. **No extra explanation** — just the draft.

## Style guidelines

- **English** by default (Rust/global tech audience). Switch to Chinese only if user explicitly requests.
- **256-280 chars** for single tweet. Leave 0-24 chars of headroom.
- **Structure**: emoji header line → ✓ bullets (3-5) → GitHub link → optional one-line tagline.
- **Code-block wrap** the final draft (` ``` ` fences) so the user can copy-paste directly without reformatting.
- **No fluff**: don't add "here's what I drafted:" or "you can adjust..." — just deliver.
- **GitHub URL**: full `github.com/<owner>/<repo>`, never shortened or guessed.

## Angle taxonomy

| Angle | Lead with | Best for |
|---|---|---|
| **Technical features** | "🦀 [name] — [category] · [license]" + ✓ bullets | Default. First impressions, scanning. |
| **vs alternatives** | Position against actix-web / axum / React / etc. | Differentiation, switching cost. |
| **Ecosystem completeness** | "one monorepo · N crates · all Rust" | Adoption signals, lock-in. |

Default to angle #1 in initial response; offer #2 and #3 as alt-versions alongside. User typically picks #1 — keep the lead consistent across angles.

## Pitfalls

1. **Don't load `social-media/xurl` just to draft tweets** — that skill is for using the CLI, not for content. Load it only when actually posting.
2. **Don't pad with explanation** — user asked for the draft, not a tutorial on how to use it.
3. **Don't fabricate stats** — no "10x faster", no "trusted by X companies" without a source. Hallucinated claims destroy credibility.
4. **Don't ask "want me to post it?"** after delivering the draft — just stop. User will say so explicitly.
5. **Verify the GitHub URL** — don't guess `<owner>/<repo>` from the crate name alone. If unsure, `gh repo view` it.
6. **Don't switch languages silently** — Chinese user prompt + English draft is fine (Rust audience), but if the user wrote in Chinese AND asks for a Chinese audience, switch accordingly.

## Project → skill lookup (verified)

| Project | Skill to load | One-line pitch |
|---|---|---|
| euv | `euv` | declarative Rust UI → WASM, 6-crate monorepo |
| hyperlane | `hyperlane` | Tokio async HTTP server, attribute-macro routes |
| lombok-macros | (none — read `/root/.cargo/registry/src/.../lombok-macros-*/README.md` or the docs-pages `lombok-macros` page) | Lombok port to Rust: `#[derive(Data, New, Getter, Setter)]` |

For projects without a skill entry above: search cargo registry source or run `gh repo view` to gather ground truth before drafting.

## When NOT to use this skill

- User asks for LinkedIn / Reddit / HN / blog post → different format, different skill needed.
- User asks to ACTUALLY POST (not draft) → load `social-media/xurl` directly.
- User asks to summarize an existing tweet → that's `xurl search` + summarization, not drafting.
