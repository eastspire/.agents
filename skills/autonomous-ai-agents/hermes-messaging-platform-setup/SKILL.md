---
name: hermes-messaging-platform-setup
description: "Set up Hermes Agent messaging platforms and gateway deps."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, gateway, messaging, feishu, telegram, discord, slack, platforms]
    related: [hermes-agent]
---

# Hermes Messaging Platform Setup

Operational drill-down for the Hermes Agent gateway + platform layer. For high-level Hermes orientation (`hermes chat`, `hermes config`, surface selection), load the bundled `hermes-agent` skill — it is the hub. This skill is what you reach for when the question is "install platform X's Python deps, walk through setup, keep gateway alive across reboots."

## When to Use

Load this skill when ANY of the following apply:

- Setting up a messaging platform (Feishu, Telegram, Discord, Slack, WhatsApp, WeChat, DingTalk, QQ Bot, …) on a Hermes Agent install.
- `hermes gateway setup` is failing or hanging — especially around QR-code auth, OAuth, or platform connection.
- A platform-specific Python dep (lark-oapi, slack-sdk, python-telegram-bot, …) needs to be installed and the obvious `pip install` paths are silently failing.
- `ModuleNotFoundError` on import in the gateway logs even though `pip list` shows the package.
- The user wants the gateway to survive reboots but `hermes gateway install` reports `Failed to connect to bus: No medium found`.
- Troubleshooting platform adapter code under `/usr/local/lib/hermes-agent/plugins/platforms/`.

Do NOT load this skill for general Hermes usage questions (CLI, models, profiles, skins, pets) — those belong to the bundled `hermes-agent` skill.

## The single most important fact first

Hermes does **NOT** use the system Python. It ships its own virtualenv:

```
/usr/local/lib/hermes-agent/venv/
```

`/usr/local/lib/hermes-agent/hermes gateway …` invokes `/usr/local/lib/hermes-agent/venv/bin/python` directly. Every platform-specific dependency (lark-oapi, aiohttp, websockets, qrcode, slack-sdk, …) must be installed into **that venv**, not into `/usr`. Installing into the system site-packages appears to succeed but the gateway never sees it.

Discovery:

```bash
ls /usr/local/lib/hermes-agent/venv/bin/ | grep -E '^(python|pip)'
ls /usr/local/lib/hermes-agent/venv/lib/python*/site-packages/ | head
```

---

## Workflow — installing per-platform deps

```bash
# Hermes's bundled uv. pip is usually absent from PATH.
/root/.hermes/bin/uv pip install \
    --python /usr/local/lib/hermes-agent/venv/bin/python \
    <package-a> <package-b> …
```

After install, verify in the **venv**, not system:

```bash
/usr/local/lib/hermes-agent/venv/bin/python -c "import <pkg>; print(<pkg>.__version__)"
ls /usr/local/lib/hermes-agent/venv/lib/python*/site-packages/ | grep <pkg>
```

Most adapters lazy-import the SDK on first connect (look for the `try: import … except ImportError: …` block near the top of `adapter.py`). **You do not need to restart the gateway** after installing a new dep — just trigger the platform to connect.

---

## Workflow — `hermes gateway setup` flow

```bash
hermes gateway setup
```

Then in the TUI:

1. **Pick platform** — menu lists every supported adapter. Feishu/Lark is option 12 in current builds, but don't hardcode numbers; count from your own menu.
2. The platform's setup sub-flow usually offers two paths:
   - **Recommended**: scan a one-time QR code → Hermes uses the SDK to auto-create a self-built app in your org and writes `app_id` / `app_secret` to `~/.hermes/.env`. Requires the SDK installed in the venv.
   - **Manual**: paste an existing `App ID` + `App Secret` from a pre-created platform app. Does NOT require the SDK at setup time.
3. After setup, the platform's status flips from `(not configured)` to `(configured)`.

Verify:

```bash
hermes config get platforms.<platform>
grep <PLATFORM>_ ~/.hermes/.env
hermes gateway status    # look for the adapter listed as connected
```

Feishu-specific notes (verified end-to-end through the menu) live in `references/feishu-setup.md`.

---

## Workflow — auto-start, when systemd works

```bash
hermes gateway install   # writes a systemd --user unit
systemctl --user enable --now hermes-gateway
```

Use when `systemctl --user status` works and `loginctl show-user $(whoami) | grep Linger` shows `Linger=yes`.

## Workflow — auto-start, when systemd is unavailable

Many environments (containers, some VPS images, WSL without systemd, Docker hosts without `systemd=true`) report:

```
Failed to connect to bus: No medium found
```

`hermes gateway install` writes a `--user` unit; without a reachable user D-Bus it cannot start. See `references/auto-start-without-systemd.md` for the `@reboot` cron fallback pattern + a starter script.

---

## Pitfalls

- **Background processes lose `~/.hermes/bin` from PATH.** When you start a long-running install with `terminal(background=true)`, the child shell may not source `~/.bashrc` and won't find `uv`. **Always use absolute paths in background commands**: `/root/.hermes/bin/uv`, `/usr/local/lib/hermes-agent/venv/bin/python`. If you see `bash: uv: command not found` from a backgrounded job, this is the cause.
- **Hermes venv ≠ system Python.** `uv pip install --system` (or any `--system` install) puts the package under `/usr/lib/python3.11/site-packages/`, where the gateway never sees it. Always pass `--python /usr/local/lib/hermes-agent/venv/bin/python`.
- **Large SDK packages can hang on download.** PyPI's CDN occasionally stalls on 7+ MiB wheels (lark-oapi is the canonical case). `--no-cache` helps in some cases; the download can still take 10+ minutes for one wheel. Install smaller deps first (`qrcode`) to validate the pipeline before kicking off the heavy one.
- **No `pip` in PATH on a fresh Hermes install.** Hermes ships `uv` / `uvx` under `~/.hermes/bin/`. Don't reach for `pip` — it's not there.
- **The `hermes-agent` skill is bundled and read-only.** When it answers generically ("Telegram, Discord, WhatsApp, Weixin, and more"), it does NOT enumerate every platform — always cross-check `/usr/local/lib/hermes-agent/plugins/platforms/` to confirm a platform is present before promising it works.
- **Setup TUI menu indices shift between versions.** Always read the menu rather than feeding a hardcoded number via piped stdin. If piping, the order matters: first newline is for the "Start gateway now?" prompt, then the platform index.
- **The gateway is a long-lived process.** Never kill PID-style instances without checking they aren't yours. `hermes gateway restart` / `hermes gateway run --replace` exist exactly so two instances don't fight over the same lockfile.

---

## References

- `references/feishu-setup.md` — verified walk-through of the Feishu/Lark platform setup, plugin layout, env-var contract.
- `references/hermes-venv-and-deps.md` — venv location, the `uv pip install --python <venv>` pattern, verification commands.
- `references/auto-start-without-systemd.md` — `@reboot` cron fallback for hosts without a working user systemd.
