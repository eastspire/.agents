# Feishu / Lark platform setup (verified end-to-end)

Feishu (China) and Lark (International) are the same platform; the domain is set by `FEISHU_DOMAIN`.

## Plugin layout

```
/usr/local/lib/hermes-agent/plugins/platforms/feishu/
├── plugin.yaml                    # metadata + env-var contract
├── adapter.py                     # 5895-line gateway adapter
├── feishu_comment.py              # drive comment events
├── feishu_comment_rules.py
├── feishu_meeting_invite.py
└── __init__.py
```

The plugin is shipped pre-installed but is not enabled by default in `config.yaml`:

```yaml
platforms:
  qqbot:
    enabled: false
  feishu:
    enabled: false
```

`hermes gateway setup` flips `enabled: true` after successful configuration.

## Env-var contract (from plugin.yaml)

Required:
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

Optional:
- `FEISHU_DOMAIN` — `feishu` (default, China) or `lark` (International)
- `FEISHU_ALLOWED_USERS` — comma-separated user IDs allowed to talk to the bot
- `FEISHU_ALLOW_ALL_USERS` — `true`/`false`; only safe for dev
- `FEISHU_HOME_CHANNEL` / `FEISHU_HOME_CHANNEL_NAME` — default chat for cron / notifications

Written by setup to `~/.hermes/.env` (NOT `config.yaml`).

## Setup flow (verified)

```bash
hermes gateway setup
```

In the TUI:

1. Menu → `🪽 Feishu / Lark` (option 12 in current builds, count from your menu).
2. Sub-menu:
   - **Option 1 (default)**: *Scan QR code to create a new bot automatically*
   - Option 2: *Enter existing App ID and App Secret manually*
3. **Option 1 path** requires `lark-oapi` in the venv. After install, Hermes prints a QR code in the terminal and a URL of the form:
   ```
   https://open.feishu.cn/page/launcher?user_code=XXXX-XXXX&from=hermes&tp=hermes
   ```
   Open Feishu on your phone, scan the QR, confirm in the app — Hermes polls and writes the resulting `app_id`/`app_secret` back to `~/.hermes/.env`.

`qrcode` is needed for the in-terminal QR rendering. Without it, only the URL is printed and you have to copy it manually.

## Deps needed in the venv

| Package | Used by | Install |
|---|---|---|
| `aiohttp` | webhook transport | usually preinstalled |
| `websockets` | WebSocket long-connection transport | usually preinstalled |
| `lark-oapi` | OAuth + auto-create-app in option 1; SDK for API calls | install via `uv pip install --python /usr/local/lib/hermes-agent/venv/bin/python lark-oapi` |
| `pycryptodome` | transitive dep of `lark-oapi` | pulled in automatically |
| `qrcode` | render QR in terminal during setup | `uv pip install --python /usr/local/lib/hermes-agent/venv/bin/python qrcode` |

## Transport modes

Adapter supports both WebSocket long-connection and webhook. WebSocket is the default — Hermes opens an outbound connection to Feishu's gateway, no inbound port needed. Webhook is for users behind firewalls that block long-lived outbound.

## Verification after setup

```bash
hermes config get platforms.feishu
grep FEISHU_ ~/.hermes/.env
hermes gateway status
tail -f ~/.hermes/logs/gateway.log | grep -i feishu
```

`hermes gateway status` will show the Feishu adapter as connected once setup completes and the gateway polls its config.

## Identity tiers (for session keying)

The adapter recognises three Feishu user-ID tiers (see `adapter.py:18-46`):
- `open_id` (ou_xxx) — app-scoped, always present in event payloads
- `user_id` (u_xxx) — tenant-scoped, requires `contact:user.employee_id:readonly` scope
- `union_id` (on_xxx) — developer-scoped, most stable cross-app

Session keys prefer `union_id` so sessions stay stable across apps.
