# Hermes venv and Python deps

## Location

Hermes is installed at `/usr/local/lib/hermes-agent/` (or `$HERMES_HOME/../` depending on install mode). Its Python interpreter and packages live in:

```
/usr/local/lib/hermes-agent/venv/
├── bin/
│   ├── python              # the gateway runtime
│   ├── hermes              # CLI shim (launches venv/bin/python)
│   └── hermes-acp
└── lib/python3.11/site-packages/
    ├── aiohttp-3.14.3.dist-info/
    ├── websockets-15.0.1.dist-info/
    └── ...
```

`/usr/local/lib/hermes-agent/hermes` is a Python entry-point that re-execs `venv/bin/python hermes …`. So **any pip/uv work for the gateway must target `venv`**.

## The canonical install command

```bash
/root/.hermes/bin/uv pip install \
    --python /usr/local/lib/hermes-agent/venv/bin/python \
    <pkg> [<pkg> ...]
```

`uv` ships under `~/.hermes/bin/uv` — `pip` is usually not in PATH on a fresh install.

## What NOT to do

| Command | Why it's wrong |
|---|---|
| `pip install <pkg>` | `pip` not in PATH |
| `uv pip install --system <pkg>` | Installs to `/usr/lib/python3.11/site-packages/`; gateway doesn't see it |
| `python3 -m pip install <pkg>` | Targets system Python, same problem |
| `apt install python3-<pkg>` | Same — wrong site-packages |

## Verifying a package is in the venv

```bash
ls /usr/local/lib/hermes-agent/venv/lib/python*/site-packages/ | grep <pkg>
/usr/local/lib/hermes-agent/venv/bin/python -c "import <pkg>; print(<pkg>.__version__)"
```

## Restart policy after install

Most adapters lazy-import the SDK on first connect (see the `try: import … except ImportError: …` block near the top of `plugins/platforms/<platform>/adapter.py`). You do **NOT** need to restart the running gateway process after installing a dep — just trigger the platform to connect (e.g. via `hermes gateway status` or sending a message).

Exception: if you changed the gateway's own code under `/usr/local/lib/hermes-agent/`, you do need a restart (`hermes gateway restart`).

## Background jobs and PATH

When `terminal(background=true)` spawns a child shell, it may not source `~/.bashrc` and thus won't have `~/.hermes/bin` on PATH. Symptoms:

```
bash: uv: command not found
```

Fix: **always use absolute paths in background commands**:

```bash
# bad (background)
terminal(background=true, command="uv pip install …")

# good
terminal(background=true, command="/root/.hermes/bin/uv pip install --python /usr/local/lib/hermes-agent/venv/bin/python …")
```
