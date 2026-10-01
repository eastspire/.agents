#!/usr/bin/env python3
"""Generate music with the MiniMax platform HTTP API (Python 3 stdlib only).

The `mmx` CLI (mmx-cli 1.0.27) has NO music resource -- `mmx music generate`
and `mmx music cover` do not exist. Music is a platform HTTP API instead:

    POST https://api.minimax.io/v1/music_generation     (global)
    POST https://api.minimax.cn/v1/music_generation     (cn)

Docs: https://platform.minimax.io/docs/api-reference/music-generation

This script builds the documented request body, decodes the response and writes
the audio to disk. It never prints the API key.

Usage
-----
  # vocal, lyrics written by the model from the prompt
  minimax_music.py --prompt "A melancholic indie folk song, fingerpicked guitar" \\
      --auto-lyrics --out ~/Music/minimax-gen/song.mp3

  # vocal, lyrics you supply
  minimax_music.py --prompt "..." --lyrics-file lyrics.txt --out song.mp3

  # instrumental (no vocals; lyrics not required)
  minimax_music.py --prompt "Warm lo-fi piano, 80 BPM" --instrumental --out bgm.mp3

  # cover from a public audio URL
  minimax_music.py --cover "Jazz, smooth, late night lounge, saxophone" \\
      --audio-url https://example.com/original.mp3 --out cover.mp3

API key resolution order: --api-key, $MINIMAX_API_KEY, ~/.mmx/config.json.
Get a key at https://platform.minimax.io/user-center/basic-information/interface-key
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import NoReturn

# Region -> base URL. Same mapping the mmx CLI uses internally.
REGION_BASE_URL = {
    "global": "https://api.minimax.io",
    "cn": "https://api.minimax.cn",
}

# Documented model ids (music-generation API reference, "model" enum).
# NOTE: as of 2026-08-20 MiniMax discontinued the -free tier
# (Music-3.0-free, Music-2.6-free, music-cover-free). Paid / M Plan only.
TEXT_MODELS = ["music-3.0", "music-2.6"]
COVER_MODELS = ["music-cover"]

# Documented base_resp status codes.
STATUS_MESSAGES = {
    0: "success",
    1002: "rate limit triggered, retry later",
    1004: "authentication failed, check API key",
    1008: "insufficient balance",
    1026: "content flagged for sensitive material",
    2013: "invalid parameters, check input",
    2049: "invalid API key",
    2153: "the music API is not available to this account (closed to new users since 2026-08-20)",
}

# HTTP statuses the music endpoint returns for account-level refusals.
HTTP_HINTS = {
    410: "Gone -- the music API is closed to new users (base_resp 2153).",
}


def fail(message: str, code: int = 1) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def resolve_api_key(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("MINIMAX_API_KEY", "").strip()
    if env:
        return env
    config = Path.home() / ".mmx" / "config.json"
    if config.is_file():
        try:
            key = json.loads(config.read_text(encoding="utf-8")).get("api_key", "")
        except (OSError, ValueError):
            key = ""
        if key:
            return key.strip()
    fail(
        "No MiniMax API key. Set MINIMAX_API_KEY, or run `mmx auth login --api-key <key>`, "
        "or pass --api-key. Keys: https://platform.minimax.io/user-center/basic-information/interface-key"
    )


def resolve_region(explicit: str | None) -> str:
    region = explicit or os.environ.get("MINIMAX_REGION", "").strip()
    if not region:
        config = Path.home() / ".mmx" / "config.json"
        if config.is_file():
            try:
                region = json.loads(config.read_text(encoding="utf-8")).get("region", "")
            except (OSError, ValueError):
                region = ""
    region = (region or "global").strip().lower()
    if region not in REGION_BASE_URL:
        fail(f'Invalid region "{region}". Valid values: global, cn')
    return region


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="minimax_music.py",
        description="Generate music via the MiniMax platform music_generation HTTP API.",
    )
    p.add_argument("--prompt", help="Style/mood/scene description. Required for text-to-music; "
                                   "for covers it describes the target style (10-300 chars).")
    p.add_argument("--lyrics", help="Lyrics with [Section] tags, inline. Required for non-instrumental text-to-music.")
    p.add_argument("--lyrics-file", help="Read lyrics from a file instead of --lyrics.")
    p.add_argument("--auto-lyrics", action="store_true",
                   help="lyrics_optimizer: true -- the model writes lyrics from --prompt when lyrics is empty.")
    p.add_argument("--instrumental", action="store_true",
                   help="is_instrumental: true -- no vocals, lyrics not required.")
    p.add_argument("--cover", metavar="STYLE",
                   help="Cover mode: the target cover style. Use with --audio-url/--audio-base64 "
                        "or --cover-feature-id.")
    p.add_argument("--audio-url", help="Cover mode: URL of the reference audio (6s-6min, <=50MB).")
    p.add_argument("--audio-base64", help="Cover Mode: base64 of the reference audio.")
    p.add_argument("--cover-feature-id", help="Cover Mode: feature id from music_cover_preprocess "
                                              "(then --lyrics is required, 10-1000 chars).")
    p.add_argument("--out", required=True, help="Where to write the audio file.")
    p.add_argument("--model", help="Override the model id. Default: music-3.0 (or music-cover in cover mode).")
    p.add_argument("--format", default="mp3", choices=["mp3", "wav", "pcm"], help="audio_setting.format (default: mp3)")
    p.add_argument("--sample-rate", type=int, default=44100, choices=[16000, 24000, 32000, 44100],
                   help="audio_setting.sample_rate (default: 44100)")
    p.add_argument("--bitrate", type=int, default=256000, choices=[32000, 64000, 128000, 256000],
                   help="audio_setting.bitrate (default: 256000)")
    p.add_argument("--region", choices=["global", "cn"], help="API region. Default: $MINIMAX_REGION or ~/.mmx/config.json, else global.")
    p.add_argument("--base-url", help="Override the API base URL entirely.")
    p.add_argument("--api-key", help="API key. Default: $MINIMAX_API_KEY or ~/.mmx/config.json.")
    p.add_argument("--timeout", type=int, default=900, help="HTTP timeout in seconds (default: 900).")
    p.add_argument("--quiet", action="store_true", help="Suppress non-essential output.")
    return p


def main() -> int:
    args = build_parser().parse_args()
    cover_mode = bool(args.cover)

    # --- lyrics ---
    lyrics = args.lyrics
    if args.lyrics_file:
        try:
            lyrics = Path(args.lyrics_file).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            fail(f"Cannot read --lyrics-file: {exc}")
    if lyrics is not None and not args.lyrics and not args.lyrics_file:
        pass  # inline --lyrics
    if args.auto_lyrics and args.instrumental:
        fail("--auto-lyrics and --instrumental are mutually exclusive (lyrics_optimizer and is_instrumental).")

    payload: dict = {
        "stream": False,
        "output_format": "hex",  # hex returns the audio inline; url expires after 24h.
        "audio_setting": {
            "sample_rate": args.sample_rate,
            "bitrate": args.bitrate,
            "format": args.format,
        },
    }

    if cover_mode:
        payload["model"] = args.model or "music-cover"
        if args.model and args.model not in COVER_MODELS:
            fail(f'--model "{args.model}" is not a cover model. Use one of: {", ".join(COVER_MODELS)}')
        payload["prompt"] = args.cover
        refs = [bool(args.audio_url), bool(args.audio_base64), bool(args.cover_feature_id)]
        if sum(refs) != 1:
            fail("Cover mode needs exactly one of --audio-url, --audio-base64, --cover-feature-id.")
        if args.audio_url:
            payload["audio_url"] = args.audio_url
        if args.audio_base64:
            payload["audio_base64"] = args.audio_base64
        if args.cover_feature_id:
            payload["cover_feature_id"] = args.cover_feature_id
            if not lyrics:
                fail("--cover-feature-id requires --lyrics or --lyrics-file (10-1000 characters).")
    else:
        payload["model"] = args.model or "music-3.0"
        if args.model and args.model not in TEXT_MODELS:
            fail(f'--model "{args.model}" is not a text-to-music model. Use one of: {", ".join(TEXT_MODELS)}')
        if not args.prompt:
            fail("--prompt is required for text-to-music generation.")
        if len(args.prompt) > 2000:
            fail(f"--prompt is {len(args.prompt)} characters; the API caps it at 2000.")
        payload["prompt"] = args.prompt
        if args.instrumental:
            payload["is_instrumental"] = True
        else:
            if not lyrics and not args.auto_lyrics:
                fail("Vocal generation needs lyrics: pass --lyrics/--lyrics-file, or --auto-lyrics "
                     "to let the model write them.")
            if args.auto_lyrics:
                payload["lyrics_optimizer"] = True
            if lyrics:
                if len(lyrics) > 3500:
                    fail(f"lyrics is {len(lyrics)} characters; the API caps it at 3500.")
                payload["lyrics"] = lyrics

    if not args.quiet:
        print(f"POST {args.base_url or REGION_BASE_URL[resolve_region(args.region)]}/v1/music_generation")
        print(f"model={payload['model']} "
              f"{'instrumental' if payload.get('is_instrumental') else 'vocal'}"
              f"{' + auto-lyrics' if payload.get('lyrics_optimizer') else ''}")
        print("Generating... (synchronous, typically 30-120s)")

    api_key = resolve_api_key(args.api_key)
    base = args.base_url or REGION_BASE_URL[resolve_region(args.region)]
    request = urllib.request.Request(
        f"{base.rstrip('/')}/v1/music_generation",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )

    body: dict
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        hint = HTTP_HINTS.get(exc.code)
        if hint:
            print(f"ERROR: HTTP {exc.code}: {hint}", file=sys.stderr)
        try:
            parsed = json.loads(detail)
            base = parsed.get("base_resp") or {}
            if base.get("status_msg"):
                print(f"  API said: {base['status_msg']}", file=sys.stderr)
        except ValueError:
            if detail:
                print(f"  {detail[:400]}", file=sys.stderr)
        if exc.code == 410:
            print("  -> Tell the user the music API is unavailable for this key. Options: "
                  "MiniMax Audio (https://www.minimax.io/audio) or the open-source MiniMax Music 3 "
                  "model (https://huggingface.co/MiniMaxAI/MiniMax-Music3).", file=sys.stderr)
        fail(f"HTTP {exc.code} from the music API", code=2)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        fail(f"Network/timeout error: {exc}", code=3)
    if not isinstance(body, dict):
        fail(f"Expected a JSON object from the music API, got {type(body).__name__}.", code=6)

    base_resp = body.get("base_resp") or {}
    code = base_resp.get("status_code")
    if code not in (None, 0):
        meaning = STATUS_MESSAGES.get(code, "unknown error")
        fail(f"MiniMax error {code}: {base_resp.get('status_msg', '')} ({meaning})".strip(), code=4)

    data = body.get("data") or {}
    status = data.get("status")
    if status != 2:
        # The non-streaming API has no task id and no polling endpoint, so
        # status 1 (in progress) is a failure, not something to wait on.
        fail(f"Music generation did not complete (data.status={status!r}). The synchronous API "
             "returns no task id to poll; retry the request.", code=5)

    audio = data.get("audio")
    if not isinstance(audio, str) or not audio:
        fail(f"No audio in response. Keys returned: {sorted(body)}", code=6)

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        # output_format=hex -> data.audio is a HEX string (not base64).
        out.write_bytes(bytes.fromhex(audio))
    except ValueError:
        fail("data.audio was not valid hex. Retry with output_format=hex.", code=7)

    if not args.quiet:
        extra = body.get("extra_info") or {}
        duration_ms = extra.get("music_duration")
        seconds = f"{duration_ms / 1000:.1f}s" if isinstance(duration_ms, (int, float)) else "unknown"
        print(f"Saved: {out}")
        print(f"Duration: {seconds} | size: {out.stat().st_size} bytes")
    print(str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
