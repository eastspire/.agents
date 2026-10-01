---
name: minimax-music-gen
description: >
  Use when user wants to generate music, songs, or audio tracks. Triggers on any request
  involving music creation, song writing, lyrics generation, audio production, or covers.
  Also triggers when user provides lyrics and wants them turned into a song, or describes
  a mood/scene and wants background music. Supports multilingual triggers — match equivalent
  phrases in any language. Do NOT use for music playback of existing files, music theory
  questions, or music recommendation without generation.
license: MIT
metadata:
  version: "1.2"
  category: creative
---

# MiniMax Music Generation Skill

Generate songs (vocal or instrumental) using the MiniMax platform Music Generation API.
Supports two creation modes: **Basic** (one-sentence-in, song-out) and **Advanced Control**
(edit lyrics, refine prompt, plan before generating).

## How music is actually generated (read this first)

**There is no `mmx music` command.** The `mmx` CLI (mmx-cli 1.0.27) has these resources only:
`auth`, `text`, `speech`, `image`, `video`, `search`, `vision`, `quota`, `config`, `agent`,
`file`, `update`. `mmx music generate` and `mmx music cover` do not exist — the CLI fails with
`Unknown command: mmx music generate`.

Music is a **platform HTTP API**, not a CLI subcommand:

| | |
|---|---|
| Endpoint | `POST /v1/music_generation` |
| Global | `https://api.minimax.io/v1/music_generation` |
| China | `https://api.minimax.cn/v1/music_generation` |
| Auth | `Authorization: Bearer <your MiniMax API key>` |
| Docs | https://platform.minimax.io/docs/api-reference/music-generation |

This skill drives that API with a bundled script:
**`scripts/minimax_music.py`** (Python 3 stdlib only, no pip install).

### API availability (important — verify before promising a song)

From the official docs (https://platform.minimax.io/docs/api-reference/music-generation,
page last modified 2026-08-18):

- **Starting 2026-08-20**, the **paid** Music Generation and Lyrics Generation APIs are
  **no longer available to new users**. Existing paying users can keep using them.
- The **free** music models (`Music-3.0-free`, `Music-2.6-free`, `music-cover-free`)
  **will be discontinued** — the docs state this without naming a separate date, so do not
  attribute the 2026-08-20 date to them.

In practice a fresh API key gets:

```
HTTP 410
{"base_resp":{"status_code":2153,"status_msg":"This Music API is no longer available to new users..."}}
```

**So: run a cheap preflight before you tell the user you can make them a song.** If the call
returns `410` / `status_code 2153`, the API is unavailable for that key. Do not retry, do not
loop, and do not silently fall back. Tell the user plainly and offer the official alternatives:

- **MiniMax Audio** (consumer product): https://www.minimax.io/audio
- **Open-source MiniMax Music 3** (weights you can self-host):
  https://huggingface.co/MiniMaxAI/MiniMax-Music3
  (self-hosting guide: https://platform.minimax.io/docs/guides/local-deploy-music-3)

A key from a MiniMax **M Plan** or existing paying account still works against
`music-3.0` / `music-2.6` / `music-cover`. Everything else in this skill assumes that case.

## Models

Current model ids, from the Music Generation API `model` enum:

| Model | Use | Access |
|---|---|---|
| `music-3.0` | Text-to-music (recommended) | M Plan / paying users, RPM 120 |
| `music-2.6` | Previous-gen text-to-music | M Plan / paying users, RPM 120 |
| `music-cover` | Cover from reference audio | M Plan / paying users, RPM 120 |
| `music-3.0-free` / `music-2.6-free` / `music-cover-free` | Free tier | **Being discontinued** (date not stated in the docs) |

The script defaults to `music-3.0` for text-to-music and `music-cover` for cover mode, and
rejects any other id with a clear error.

## Prerequisites

- **Python 3** (required) — runs `scripts/minimax_music.py`. Stdlib only, no pip install.

  ```bash
  python3 --version
  ```

- **A MiniMax API key with music access** (M Plan or an existing paying account). Get one at
  [MiniMax Platform](https://platform.minimax.io/user-center/basic-information/interface-key).

  The script resolves the key in this order: `--api-key` → `$MINIMAX_API_KEY` →
  `~/.mmx/config.json`. If you use `mmx` for other resources, its login already wrote the key
  there:

  ```bash
  mmx auth login --api-key <your-minimax-api-key>
  ```

  `mmx config show` (or read `~/.mmx/config.json`) confirms the key and the region.
  `mmx quota show` confirms account quota.

- **Region** — `global` (`https://api.minimax.io`) or `cn` (`https://api.minimax.cn`), the same
  two values the `mmx` CLI uses. The script reads `$MINIMAX_REGION` then
  `~/.mmx/config.json`, defaulting to `global`. Override with `--region`.

- **Audio player** (recommended): `mpv`, `ffplay`, or `afplay` (macOS built-in) for local
  playback. `mpv` is preferred for its interactive controls.

### Preflight

Confirm the key reaches the music API before promising anything. This makes no charge:

```bash
python3 <SKILL_DIR>/scripts/minimax_music.py \
  --prompt "probe" --instrumental --out /tmp/music-preflight.mp3 --quiet
```

- Exit `0` → music is available, proceed with the workflow.
- Exit `2` with `HTTP 410` / `status_code 2153` → not available for this key. Report the
  alternatives above and stop.

## Storage

All generated music is saved to `~/Music/minimax-gen/`. Create the directory if it doesn't
exist. Files are named with a timestamp and a short slug derived from the prompt:
`YYYYMMDD_HHMMSS_<slug>.mp3`

---

## Language & Interaction

Detect the user's language from their first message and respond in that language for the
entire session. This applies to all interaction text, questions, confirmations, and feedback
prompts.

**User-facing text localization rule**:
- ALL text shown to the user — including preview labels, field names, confirmations, status
  messages, playback info, feedback prompts, **and the prompt/description preview** — MUST
  be fully translated into the user's language.
- The **API prompt** sent to the model should always be written in English for best
  generation quality. However, when previewing the prompt to the user, show a localized
  description in the user's language instead of the raw English prompt. The English prompt
  is an internal implementation detail — the user does not need to see it.
- The templates below are written in English as reference. At runtime, translate every label
  and message into the user's detected language.

**Lyrics language rule**:
- Default lyrics language = the user's language. A Chinese-speaking user gets Chinese lyrics;
  an English-speaking user gets English lyrics.
- Only generate lyrics in a different language if the user **explicitly** requests it.
- When a different lyrics language is needed, embed it naturally into the vocal or genre
  description in the prompt. For example, instead of appending "with Korean lyrics", use
  "featuring a Korean female vocalist" or specify a genre that implies the language (e.g.,
  "K-pop", "J-rock", "Mandopop", "Latin pop").

---

## Workflow

### Step 0: Detect Intent

Parse the user's message to determine:

1. **Song category**: vocal (with lyrics), instrumental (no vocals), or cover
2. **Creation mode preference**: did they provide detailed requirements (Advanced) or a
   casual one-liner (Basic)?

If ambiguous, ask using this decision tree:

```
Q1: What type of music?
  - Vocal (with lyrics)
  - Instrumental (no vocals)
  - Cover

Q2: Creation mode?
  - Basic — one-line description, auto-generate
  - Advanced — edit lyrics, refine prompt, plan
```

If the user gives a clear one-liner like "make me a sad piano piece", skip the questions —
infer instrumental + basic mode and proceed.

---

### Step 1: Basic Mode

**Goal**: User provides a short description, the skill auto-generates everything, then calls
the API.

1. **Expand the description into a prompt**: Take the user's one-liner and expand it into a
   rich music prompt. Refer to the **Prompt Writing Guide** appendix at the end of this
   document for style vocabulary, genre/instrument references, and prompt structure.
   **The API prompt should always be written in English** for best generation quality,
   regardless of the user's language.

   Follow this pattern:
   ```
   A [mood] [BPM optional] [genre] song, featuring [vocal description],
   about [narrative/theme], [atmosphere], [key instruments and production].
   ```

   Keep the prompt under the API's 2000-character limit (the script enforces it).

2. **Show the user a preview** before generating. Translate all labels AND the prompt
   description into the user's language. The English prompt is only used internally when
   calling the API — the user should never see it. Example template (English reference —
   localize everything at runtime):

   ```
   About to generate:
   Type: Vocal / Instrumental
   Description: indie folk, melancholy, acoustic guitar, gentle female voice
   Lyrics: Auto-generated by the model

   Confirm? (press enter to confirm, or tell me what to change)
   ```

3. **Call the API** (see Step 3).

---

### Step 2: Advanced Control Mode

**Goal**: User has full control over every parameter before generation.

1. **Lyrics phase**:
   - If user provided lyrics: display them formatted with section markers, ask for edits.
     The final lyrics are passed to the API via `--lyrics` / `--lyrics-file`.
   - If user has a theme but no lyrics: use `--auto-lyrics` (`lyrics_optimizer`) to have the
     model write them, or call the separate Lyrics Generation endpoint first
     (see "Optional: standalone lyrics generation" below).
   - Support iterative editing: "change the second chorus" -> only rewrite that section.
   - User can also write lyrics themselves and pass them via `--lyrics`.

2. **Prompt phase**:
   - Generate a recommended prompt based on the lyrics' mood and content.
   - Present it as editable tags the user can add/remove/modify.
   - Refer to the **Prompt Writing Guide** appendix for the full vocabulary.

   Note: the music API has no separate `--genre` / `--mood` / `--vocals` / `--bpm` fields.
   There is one `prompt` string — pack the structured details into the prompt text itself,
   using the guide's vocabulary to keep it natural.

3. **Advanced planning** (optional, offer but don't force):
   - Song structure: verse-chorus-verse-chorus-bridge-chorus or custom, expressed with
     `[Section]` tags inside the lyrics
   - BPM suggestion (encode in prompt as tempo descriptor)
   - Reference style: "something like X style" -> map to prompt tags
   - Vocal character description

4. **Final confirmation**: Show complete parameter summary, then generate.

---

### Step 3: Call the API

`<SKILL_DIR>` = the directory containing this SKILL.md file. All paths below are relative to
it.

**Vocal, model writes the lyrics from the prompt** (`lyrics_optimizer: true`):
```bash
python3 <SKILL_DIR>/scripts/minimax_music.py \
  --prompt "<english prompt>" \
  --auto-lyrics \
  --out ~/Music/minimax-gen/<filename>.mp3
```

**Vocal with user-provided lyrics** (lyrics required unless `--auto-lyrics`):
```bash
python3 <SKILL_DIR>/scripts/minimax_music.py \
  --prompt "<english prompt>" \
  --lyrics "<lyrics with [Section] markers>" \
  --out ~/Music/minimax-gen/<filename>.mp3
```

**Instrumental (no vocals)** — `is_instrumental: true`, lyrics not required, prompt required:
```bash
python3 <SKILL_DIR>/scripts/minimax_music.py \
  --prompt "<english prompt>" \
  --instrumental \
  --out ~/Music/minimax-gen/<filename>.mp3
```

**Audio settings** (`audio_setting`, all optional):
```bash
  --format mp3|wav|pcm        # default mp3
  --sample-rate 16000|24000|32000|44100   # default 44100
  --bitrate 32000|64000|128000|256000     # default 256000
```

**Agent discipline**: add `--quiet` when you need to capture stdout, and redirect stderr
separately. The script's last stdout line is always the output path, so this is safe to parse:

```bash
out=$(python3 <SKILL_DIR>/scripts/minimax_music.py \
  --prompt "<english prompt>" --auto-lyrics \
  --out ~/Music/minimax-gen/<filename>.mp3 --quiet)
```

For `mmx` commands (e.g. `mmx image generate` for an album cover), the equivalent discipline is
the CLI's global flags `--quiet --non-interactive`.

**Generation is synchronous** — the call holds open until the song is finished, typically
30-120 seconds. There is no task id and no polling endpoint, so don't poll. Show a progress
indicator while waiting. The script uses a 900-second timeout by default; raise it with
`--timeout` for long tracks.

**Output**: with `output_format: hex` (what the script uses) the API returns the audio inline
as a **hex** string in `data.audio`, which the script decodes and writes to `--out`. Using
`output_format: url` returns a download link that **expires after 24 hours** — don't use it for
anything you need to keep.

---

### Step 4: Playback

After generation, detect an available audio player and play the file.

**Detect player:**
```bash
command -v mpv || command -v ffplay || command -v afplay
```

**Play based on detected player (in priority order):**

| Player | Command | Controls |
|--------|---------|----------|
| `mpv` (preferred) | `mpv --no-video ~/Music/minimax-gen/<filename>.mp3` | space = pause/resume, q = quit, left/right = seek |
| `ffplay` | `ffplay -nodisp -autoexit ~/Music/minimax-gen/<filename>.mp3` | q = quit |
| `afplay` (macOS) | `afplay ~/Music/minimax-gen/<filename>.mp3` | Ctrl+C = stop |
| None found | Do not attempt playback | Show file path only |

After starting playback, tell the user (localize all text):

```
Now playing: <filename>.mp3
Saved to: ~/Music/minimax-gen/<filename>.mp3
```

Do NOT show playback controls (e.g. keyboard shortcuts) — they don't work in this
environment since the player runs in the background.

If no player is found (localize all text):

```
No audio player detected.
File saved to: ~/Music/minimax-gen/<filename>.mp3
Tip: Install mpv for the best playback experience (brew install mpv).
```

---

### Step 5: Feedback & Iteration

After playback, ask for feedback:

```
How was this song?
  1. Love it, keep it!
  2. Not quite, adjust and regenerate
  3. Fine-tune lyrics/style then regenerate
  4. Don't want it, start over
```

Based on feedback:
- **Satisfied**: Done. Mention the file path again.
- **Adjust & regenerate**: Ask what to change (prompt? lyrics? style?), apply edits,
  re-run generation. Keep the old file with a `_v1` suffix for comparison.
- **Fine-tune**: Enter Advanced Control Mode with the current parameters pre-filled.
- **Delete & restart**: Remove the file, go back to Step 0.

---

## Optional: standalone lyrics generation

`POST /v1/lyrics_generation` (global `https://api.minimax.io`, cn `https://api.minimax.cn`)
writes lyrics without generating audio. Useful in Advanced mode when the user wants to review
and edit lyrics before spending on a song.

Request body: `{"mode": "write_full_song" | "edit", "prompt": "<theme, <=2000 chars>"}`, plus
optional `lyrics` (existing text, only for `edit`, <=3500 chars) and `title` (preserved in the
output). The response carries `song_title`, `style_tags`, and `lyrics`.

Notes:
- `lyrics_optimizer: true` on the music endpoint does the same thing in one call — prefer it
  unless the user wants to edit lyrics first.
- This endpoint (Lyrics Generation) is closed to new users under the same 2026-08-20
  restriction as music generation: a new key gets `410` / `status_code 2153`.

## Cover Mode

Generate a cover version of a song based on reference audio. Model: `music-cover` (the
`music-cover-free` tier is discontinued).

**Reference audio requirements**: 6s to 6min, max 50MB, common formats (mp3, wav, flac).
Provide the reference as `audio_url` or `audio_base64` — exactly one, never both.

**Cover from a URL:**
```bash
python3 <SKILL_DIR>/scripts/minimax_music.py \
  --cover "<cover style description, 10-300 chars>" \
  --audio-url "https://example.com/source.mp3" \
  --out ~/Music/minimax-gen/<filename>.mp3
```

**Cover from a local file** — base64-encode it first (`base64 -i source.mp3`), then:
```bash
python3 <SKILL_DIR>/scripts/minimax_music.py \
  --cover "<cover style description>" \
  --audio-base64 "$(base64 -i ~/source.mp3)" \
  --out ~/Music/minimax-gen/<filename>.mp3
```

**With custom lyrics** (10-1000 characters). If you omit them, the API extracts the original
lyrics from the reference audio via ASR:
```bash
python3 <SKILL_DIR>/scripts/minimax_music.py \
  --cover "<style>" --audio-url "<source_url>" \
  --lyrics-file ~/lyrics.txt \
  --out ~/Music/minimax-gen/<filename>.mp3
```

**Two-step cover** (edit the extracted lyrics before generating). First call the free
preprocess endpoint `POST /v1/music_cover_preprocess` with
`{"model": "music-cover", "audio_url": "..."}`; it returns `cover_feature_id` (valid 24 hours),
`formatted_lyrics`, `structure_result`, and `audio_duration`. Edit the lyrics, then:
```bash
python3 <SKILL_DIR>/scripts/minimax_music.py \
  --cover "<style>" --cover-feature-id "<id>" \
  --lyrics "<edited lyrics, 10-1000 chars>" \
  --out ~/Music/minimax-gen/<filename>.mp3
```
`cover_feature_id` is mutually exclusive with `audio_url` / `audio_base64`, and it requires
`--lyrics`.

**Not available**: the music API has no `seed`, `channel`, or per-request bitrate/samplerate
overrides beyond `audio_setting`. There is no cover "from a local path" parameter — local audio
must be base64-encoded first. Each `cover_feature_id` is valid for 24 hours, and identical
audio content returns the same id.

### After generation
Proceed with normal playback and feedback flow (Step 4 & 5).

---

## Error Handling

Script exit codes (from `scripts/minimax_music.py`):

| Exit | Meaning | Action |
|------|---------|--------|
| 1 | Bad arguments / missing key / failed validation | Fix the invocation; the message names the constraint |
| 2 | HTTP error from the music API | Read stderr. `410`/`2153` = closed to new users, see above |
| 3 | Network or timeout error | Retry once, then report failure |
| 4 | `base_resp.status_code` non-zero | Read the mapped meaning below |
| 5 | `data.status != 2` | Generation did not complete; no task id exists, so retry |
| 6 | No `data.audio` in the response | Retry; verify the model id |
| 7 | `data.audio` was not valid hex | Retry with the default hex output format |

Documented API status codes (`base_resp.status_code`):

| Code | Meaning | Action |
|------|---------|--------|
| 0 | success | — |
| 1002 | Rate limit triggered | Wait and retry; free tier was RPM 3, paid RPM 120 |
| 1004 | Authentication failed | Check the API key |
| 1008 | Insufficient balance | Report quota, suggest topping up |
| 1026 | Content flagged for sensitive material | Reword the prompt/lyrics |
| 2013 | Invalid parameters | Check lengths and required fields |
| 2049 | Invalid API key | Re-authenticate |
| 2153 | Music API not available to this account | Closed to new users since 2026-08-20 — offer the alternatives |

Other conditions:

| Error | Action |
|-------|--------|
| No audio player found | Save file and tell user the path, suggest installing mpv |
| Lyrics rejected for missing section tags | Add the documented tags, warn user |
| Python 3 missing | Report it — the script is stdlib-only, no install step needed |

---

## Important Notes

- **Never reproduce copyrighted lyrics.** When doing covers, always write original lyrics
  inspired by the song's theme. Explain this to the user.
- **Prompt language**: The API prompt works best with English tags. Chinese tags are also
  acceptable. Mixing is OK.
- **Section markers in lyrics**: The API documents these structure tags — `[Intro]`,
  `[Verse]`, `[Pre Chorus]`, `[Chorus]`, `[Interlude]`, `[Bridge]`, `[Outro]`,
  `[Post Chorus]`, `[Transition]`, `[Break]`, `[Hook]`, `[Build Up]`, `[Inst]`, `[Solo]`.
  Always include them when providing lyrics.
- **Lyrics limits**: 1-3500 characters for text-to-music; 10-1000 for covers.
- **Prompt limits**: up to 2000 characters; 10-300 for a cover style description.
- **No seed parameter**: the music API has no `seed` field, so results are not reproducible
  from a seed. Save prompts and lyrics alongside saved files if the user may want to re-run.
- **File management**: If `~/Music/minimax-gen/` has more than 50 files, suggest cleanup
  when starting a new session.
- **Lyrics language via style**: When the user wants lyrics in a specific language, express
  it through the vocal description or genre (e.g., "Japanese female vocalist", "Mandopop
  ballad") rather than appending a language directive to the prompt.

---

## Removed / no longer available

These were documented by earlier versions of this skill and **do not exist**. Do not use them:

| Removed | Reality |
|---------|---------|
| `mmx music generate` | No `music` resource in the mmx CLI. Use `scripts/minimax_music.py`. |
| `mmx music cover` | Same — no `mmx music` subcommand exists. |
| `--lyrics-optimizer` / `--instrumental` / `--genre` / `--mood` / `--vocals` / `--instruments` / `--bpm` / `--key` / `--tempo` / `--structure` / `--references` / `--avoid` / `--use-case` | These were never real `mmx` flags. The API has a single `prompt` string plus `lyrics`, `is_instrumental`, `lyrics_optimizer`, and `audio_setting`. |
| `--audio-file <path>` for covers | No such field. Use `--audio-url` or `--audio-base64`. |
| `--seed` / `--channel` | Not in the music API schema. |
| `music-2.6-free`, `music-cover-free`, `Music-3.0-free` | Free tier is being discontinued; the paid APIs closed to new users on 2026-08-20. |
| mmx exit codes 3/4/5/10 for music | Those are `mmx` CLI exit codes; music never goes through `mmx`. |
| API key from `https://platform.minimaxi.com/` | Keys come from platform.minimax.io (global) or platform.minimaxi.com (China). |

---

## Appendix: Prompt Writing Guide

See [references/prompt_guide.md](references/prompt_guide.md) for the complete prompt writing
guide, including genre/vocal/instrument references, BPM tables, and the API field limits.
