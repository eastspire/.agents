---
name: mmx-cli
description: Use mmx to generate text, images, video, and speech via the MiniMax AI platform, plus web search, file storage, and coding-agent setup. Use when the user wants to create media content, chat with MiniMax models, perform web search, or manage MiniMax API resources from the terminal.
---

# MiniMax CLI — Agent Skill Guide

Use `mmx` to generate text, images, video, and speech, and perform web search via the MiniMax AI platform.

## Prerequisites

```bash
# Install
npm install -g mmx-cli

# Auth (persisted to ~/.mmx/credentials.json)
mmx auth login --api-key sk-xxxxx

# Or pass per-call
mmx text chat --api-key sk-xxxxx --message "Hello"
```

Region defaults to `global`; set it explicitly with `--region global` or `--region cn`.

## Resources

`agent`, `auth`, `config`, `file`, `image`, `quota`, `search`, `speech`, `text`, `update`, `video`, `vision`.
There is also a `help` command that prints MiniMax API documentation links.

```bash
mmx --help              # resource list + global flags
mmx <resource> --help   # commands for one resource
mmx <resource> <cmd> --help   # full flag list with defaults
```

---

## Global Flags

Available on every command. Use these in non-interactive (agent/CI) contexts:

| Flag | Purpose |
|---|---|
| `--non-interactive` | Disable interactive prompts; fail fast on missing args |
| `--quiet` | Suppress non-essential output; stdout is clean data |
| `--output <text\|json>` | Output format (default: `text`) |
| `--api-key <key>` | API key (overrides all other auth) |
| `--region <global\|cn>` | API region (default: `global`) |
| `--base-url <url>` | API base URL (overrides region) |
| `--timeout <seconds>` | Request timeout (default: 300) |
| `--verbose` | Print HTTP request/response details |
| `--no-color` | Disable ANSI colors and spinners |
| `--dry-run` | Show what would happen without executing |

`--async` and `--yes` are **not** global: `--async` belongs to `video generate`, and `--yes` to `auth logout`.

---

## Commands

### text chat

Chat completion. Default model: `MiniMax-M3`.

```bash
mmx text chat --message <text> [flags]
```

| Flag | Type | Description |
|---|---|---|
| `--message <text>` | string, repeatable | Message text. Prefix with `role:` to set role (e.g. `"system:You are helpful"`, `"assistant:Hi!"`) |
| `--messages-file <path>` | string | JSON file with messages array. Use `-` for stdin |
| `--system <text>` | string | System prompt |
| `--model <model>` | string | Model ID (default: `MiniMax-M3`) |
| `--max-tokens <n>` | number | Max tokens (default: 4096) |
| `--temperature <n>` | number | Sampling temperature (0.0, 1.0] |
| `--top-p <n>` | number | Nucleus sampling threshold |
| `--stream` | boolean | Stream response tokens (default: on in TTY) |
| `--tool <json-or-path>` | string, repeatable | Tool definition as JSON or file path |

```bash
# Single message
mmx text chat --message "user:What is MiniMax?" --output json --quiet

# Multi-turn
mmx text chat \
  --system "You are a coding assistant." \
  --message "user:Write fizzbuzz in Python" \
  --output json

# From file
cat conversation.json | mmx text chat --messages-file - --output json
```

**stdout**: response text (text mode) or full response object (json mode).

### text repl

Interactive multi-turn chat session. Same model default (`MiniMax-M3`); not suitable for non-interactive use.

```bash
mmx text repl [--model <model>] [--system <text>] [--max-tokens <n>] [--temperature <n>] [--top-p <n>]
```

---

### image generate

Generate images. Models: `image-01` and `image-01-live`.

```bash
mmx image generate --prompt <text> [flags]
```

| Flag | Type | Description |
|---|---|---|
| `--prompt <text>` | string, **required** | Image description |
| `--aspect-ratio <ratio>` | string | e.g. `16:9`, `1:1`. Ignored if both `--width` and `--height` are set |
| `--width <px>` | number | Custom width, 512–2048, multiple of 8. `image-01` only. Overrides `--aspect-ratio` |
| `--height <px>` | number | Custom height, 512–2048, multiple of 8. `image-01` only. Overrides `--aspect-ratio` |
| `--n <count>` | number | Number of images to generate (default: 1) |
| `--seed <n>` | number | Reproducible output (same seed + prompt = identical image) |
| `--prompt-optimizer` | boolean | Optimize the prompt before generation |
| `--aigc-watermark` | boolean | Embed AI-generated content watermark |
| `--subject-ref <params>` | string | Subject reference for character consistency: `type=character,image=path-or-url` |
| `--out <path>` | string | Save to an exact file path (single image only) |
| `--response-format <url\|base64>` | string | Response format (default: `url`). Use `base64` to bypass an unreachable CDN |
| `--out-dir <dir>` | string | Download images to directory |
| `--out-prefix <prefix>` | string | Filename prefix (default: `image`) |

```bash
mmx image generate --prompt "A cat in a spacesuit" --output json --quiet
# stdout: image URLs (one per line in quiet mode)

mmx image generate --prompt "Logo" --n 3 --out-dir ./gen/ --quiet
# stdout: saved file paths (one per line)

mmx image generate --prompt "A castle" --seed 42 --width 1920 --height 1080
```

---

### video generate

Generate video. This is an async task — by default it polls until completion.

Model families (chosen by flags, not only by `--model`):

| Mode | Model | Trigger |
|---|---|---|
| V2 | `MiniMax-H3` | `--model MiniMax-H3`; text/image/video/audio content, up to 2K |
| T2V | `MiniMax-Hailuo-2.3` | Legacy text-to-video |
| I2V | `MiniMax-Hailuo-2.3` (default) / `MiniMax-Hailuo-2.3-Fast` | Fast mode requires `--image` |
| SEF | `MiniMax-Hailuo-02` | Requires `--image` and `--last-frame` |
| S2V | `S2V-01` | Requires `--subject-image` |

```bash
mmx video generate --prompt <text> [flags]
```

| Flag | Type | Description |
|---|---|---|
| `--prompt <text>` | string, **required** | Video description |
| `--model <model>` | string | `MiniMax-H3` for V2, or legacy `MiniMax-Hailuo-2.3` / `MiniMax-Hailuo-2.3-Fast`. Auto-switches to `Hailuo-02` with `--last-frame`, or `S2V-01` with `--subject-image` |
| `--image <path-or-url>` | string | Input image for image-to-video |
| `--first-frame <path-or-url>` | string | Backward-compatible alias for `--image`; do not pass both |
| `--last-frame <path-or-url>` | string | Ending image. Legacy SEF also requires `--image`; H3 supports a last frame alone |
| `--subject-image <path-or-url>` | string | Character-consistency reference; switches to `S2V-01` |
| `--reference-image <path-or-url>` | string | H3 reference image (repeatable) |
| `--reference-video <path-or-url>` | string | H3 reference video (repeatable; local MP4/MOV, URL, data URI, or `mm_file://` ID) |
| `--reference-audio <path-or-url>` | string | H3 reference audio (repeatable; requires a reference image or video) |
| `--duration <seconds>` | number | H3 supports integers 4–15 (default: 5) |
| `--ratio <ratio>` | string | H3 aspect ratio: `adaptive`, `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, `9:16` |
| `--callback-url <url>` | string | Webhook URL for completion |
| `--download <path>` | string | Save video to file on completion |
| `--async` | boolean | Return task ID immediately (agent/CI mode) |
| `--no-wait` | boolean | Same as `--async` |
| `--poll-interval <seconds>` | number | Polling interval when waiting (default: 5) |

```bash
# Non-blocking: get task ID
mmx video generate --prompt "A robot." --async --quiet
# stdout: {"taskId":"..."}

# Blocking: wait and get file path
mmx video generate --prompt "Ocean waves." --download ocean.mp4 --quiet
# stdout: ocean.mp4

# H3 text-to-video
mmx video generate --model MiniMax-H3 --prompt "Ocean waves at sunset"

# First + last frame interpolation (Hailuo-02)
mmx video generate --prompt "Walk forward" --image start.jpg --last-frame end.jpg
```

### video task get

Query status of a video generation task.

```bash
mmx video task get --task-id <id> [--model MiniMax-H3] [--output json]
```

Pass `--model MiniMax-H3` for Video Generation V2 tasks; otherwise the legacy V1 query is used.

### video download

Download a completed video by **file ID** (not task ID).

```bash
mmx video download --file-id <id> --out <path>
```

---

### speech synthesize

Text-to-speech. Default model: `speech-2.8-hd`; also `speech-2.6` and `speech-02`. Max 10k chars per call.
`speech generate` is an alias for `speech synthesize`.

```bash
mmx speech synthesize --text <text> [--out <path>] [flags]
```

| Flag | Type | Description |
|---|---|---|
| `--text <text>` | string | Text to synthesize |
| `--text-file <path>` | string | Read text from file. Use `-` for stdin |
| `--model <model>` | string | `speech-2.8-hd` (default), `speech-2.6`, `speech-02` |
| `--voice <id>` | string | Voice ID (default: `English_expressive_narrator`) |
| `--speed <n>` | number | Speech speed multiplier |
| `--volume <n>` | number | Volume level |
| `--pitch <n>` | number | Pitch adjustment |
| `--emotion <emotion>` | string | `happy`, `sad`, `angry`, `fearful`, `disgusted`, `surprised`, `calm`, `fluent`, `whisper` |
| `--text-normalization` | boolean | Enable Chinese/English text normalization |
| `--latex-read` | boolean | Read LaTeX formulas (`$$...$$`, Chinese only) |
| `--format <fmt>` | string | `mp3`, `pcm`, `flac`, `wav`, `pcmu_raw`, `pcmu_wav`, `opus` (default: `mp3`) |
| `--sample-rate <hz>` | number | Sample rate (default: 32000) |
| `--bitrate <bps>` | number | Bitrate (default: 128000) |
| `--channels <n>` | number | Audio channels (default: 1) |
| `--language <code>` | string | Language boost |
| `--subtitles` | boolean | Include subtitle timing data |
| `--pronunciation <from/to>` | string, repeatable | Custom pronunciation |
| `--out <path>` | string | Save audio to file |
| `--stream` | boolean | Stream raw audio to stdout |

```bash
mmx speech synthesize --text "Hello world" --out hello.mp3 --quiet
# stdout: hello.mp3

echo "Breaking news." | mmx speech synthesize --text-file - --out news.mp3
```

### speech transcribe

Transcribe audio to text. Default model: `asr-1.0`. `speech recognize` is an alias.

```bash
mmx speech transcribe --file <path> [flags]
```

| Flag | Type | Description |
|---|---|---|
| `--file <path>` | string, **required** | Audio file: mp3, wav, m4a, flac, aac, opus, ogg, aiff |
| `--model <model>` | string | Model ID (default: `asr-1.0`) |
| `--response-format <fmt>` | string | `json`, `verbose_json`, `srt`, `vtt` (default: `json`) |
| `--language <code>` | string | BCP-47 hint (`zh`, `en`, `ja`, …); omit for auto-detect |
| `--timestamp-level <level>` | string | `sentence` or `word` (only with `verbose_json`/`srt`/`vtt`) |
| `--stream` | boolean | Stream incremental text (json only; pair with `--output text` when piping) |
| `--out <path>` | string | Write the result to a file instead of stdout |

```bash
mmx speech transcribe --file meeting.mp3
mmx speech transcribe --file talk.mp3 --response-format srt --out talk.srt
```

### speech voices

List available system voices.

```bash
mmx speech voices [--language <lang>]
```

---

### Batch image generation (N>1 ordered images)

See `references/batch-image-generation.md` for the verified workflow: prompt authoring in a Python dict, concurrent MCP calls in batches of 5, Python urllib batch download (NOT bash curl — OSS signature URLs have shell-escape pitfalls), the persistent `dl_full.py` + `append_dl.py` script pair (see `scripts/dl_full_template.py` and `scripts/append_dl.py`), the agent-iteration-cap recovery procedure, and the 3-step verification (file count + size threshold + visual spot-check via `vision_analyze` on local path). Validated N=100 on 2026-07-19.

### vision describe

Image understanding via VLM. Provide either `--image` or `--file-id`, not both.

```bash
mmx vision describe (--image <path-or-url> | --file-id <id>) [flags]
```

| Flag | Type | Description |
|---|---|---|
| `--image <path-or-url>` | string | Local path or URL (base64-encoded automatically) |
| `--file-id <id>` | string | Pre-uploaded file ID (skips base64 conversion) |
| `--prompt <text>` | string | Question about the image (default: `"Describe the image."`) |

```bash
mmx vision describe --image photo.jpg --prompt "What breed?" --output json
```

**stdout**: description text (text mode) or full response (json mode).

---

### search query

Web search via MiniMax. `search web` is an alias for `search query`.

Both hit `/v1/coding_plan/search`, which returns **at most 10 results** and has **no pagination** — refining `--q` is the only way to see different results.

```bash
mmx search query --q <query>
```

| Flag | Type | Description |
|---|---|---|
| `--q <query>` | string, **required** | Search query string |

```bash
mmx search query --q "MiniMax AI" --output json --quiet
```

---

### file upload

Upload a file to MiniMax storage, then reference it by ID (e.g. with `vision describe --file-id`).

```bash
mmx file upload --file <path> [--purpose <purpose>]
```

| Flag | Type | Description |
|---|---|---|
| `--file <path>` | string, **required** | Local path to the file |
| `--purpose <string>` | string | File purpose (default: `retrieval`) |

```bash
mmx file upload --file doc.pdf --output json --quiet
mmx file upload --file image.png --purpose vision
```

### file list

List uploaded files in MiniMax storage. Takes no flags of its own.

```bash
mmx file list [--output json]
```

### file delete

Delete an uploaded file.

```bash
mmx file delete --file-id <id>
```

---

### agent setup

Configure external coding agents to use a MiniMax API key, optionally installing missing ones.
In non-interactive mode **both** `--region` and an API key are required (or an existing Codex MiniMax provider key).

```bash
mmx agent setup [--agent <name> ... | --all] [--api-key <key>] [--region <region>]
```

| Flag | Type | Description |
|---|---|---|
| `--agent <name>` | string, repeatable | `claude-code`, `codex`, `grok`/`grok-build`, `opencode`, `hermes`, `pi` |
| `--all` | boolean | Configure every supported agent |
| `--api-key <key>` | string | API key. Reuses an existing Codex MiniMax provider key when omitted. Token Plan (`sk-cp-…`) and pay-as-you-go (`sk-api-…`) keys use separate quotas and are not interchangeable |
| `--region <region>` | string | `global` or `cn` (required in non-interactive mode) |
| `--model <model>` | string | Default model: `MiniMax-M3.1-Flash-Preview` (default), `MiniMax-M3`, `MiniMax-M2.7`, `MiniMax-M2.7-highspeed` |
| `--m31-context-window <size>` | string | Context window for `MiniMax-M3.1-Flash-Preview` in Claude Code, Codex, OpenCode: `512k` (recommended) or `1m` |

```bash
mmx agent setup --agent claude-code --agent codex --api-key sk-xxxxx --region global
mmx agent setup --all --api-key sk-xxxxx --region cn --output json
# Preview without writing anything:
mmx agent setup --agent opencode --api-key sk-xxxxx --region cn --dry-run
```

---

### update

Update the `mmx` CLI itself to the latest version. A leaf command with no subcommands.

```bash
mmx update
```

---

### quota show

Display Token Plan usage and remaining quotas.

```bash
mmx quota show [--output json]
```

---

### Not in this CLI

**Music generation.** There is no `music` resource in `mmx` — music is generated through a
platform HTTP API driven by a bundled script, not through the CLI. See
[`../minimax-music-gen/SKILL.md`](../minimax-music-gen/SKILL.md) (and `../minimax-music-playlist/SKILL.md`).

Caution: `mmx music --help` and `mmx music generate --help` do **not** error — they print the top-level help and exit 0, which makes a missing command look like a valid one. Check the resource list in `mmx --help` instead.

---

## Tool Schema Export

Export all commands as Anthropic/OpenAI-compatible JSON tool schemas:

```bash
# All tool-worthy commands (excludes auth/config/update)
mmx config export-schema

# Single command
mmx config export-schema --command "video generate"
```

Use this to dynamically register mmx commands as tools in your agent framework.

---

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | General error |
| 2 | Usage error (bad flags, missing args) |
| 3 | Authentication error |
| 4 | Quota exceeded |
| 5 | Timeout |
| 6 | Network error |
| 10 | Content filter triggered |

---

## Piping Patterns

```bash
# stdout is always clean data — safe to pipe
mmx text chat --message "Hi" --output json | jq '.content'

# stderr has progress/spinners — discard if needed
mmx video generate --prompt "Waves" 2>/dev/null

# Chain: generate image → describe it
URL=$(mmx image generate --prompt "A sunset" --quiet)
mmx vision describe --image "$URL" --quiet

# Chain: upload → describe by file ID
FID=$(mmx file upload --file photo.jpg --output json --quiet | jq -r '.fileId')
mmx vision describe --file-id "$FID" --prompt "What breed?"

# Async video workflow (download takes a --file-id, not a --task-id)
TASK=$(mmx video generate --prompt "A robot" --async --quiet | jq -r '.taskId')
mmx video task get --task-id "$TASK" --output json
FILE=$(mmx video task get --task-id "$TASK" --output json --quiet | jq -r '.fileId')
mmx video download --file-id "$FILE" --out robot.mp4
```

---

## Configuration Precedence

CLI flags → environment variables → `~/.mmx/config.json` → defaults.

```bash
# Persistent config
mmx config set --key region --value cn
mmx config set --key default_text_model --value MiniMax-M3
mmx config show

# Environment
export MINIMAX_API_KEY=sk-xxxxx
export MINIMAX_REGION=cn
```

Valid `config set --key` values: `region`, `base_url`, `output`, `timeout`, `api_key`, `proxy`, `default_text_model`, `default_speech_model`, `default_video_model`.
Recognized env vars: `MINIMAX_API_KEY`, `MINIMAX_REGION`, `MINIMAX_BASE_URL`, `MINIMAX_OUTPUT`, `MINIMAX_TIMEOUT`, `MINIMAX_VERBOSE`, `MINIMAX_CN_API_KEY`.
