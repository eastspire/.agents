#!/usr/bin/env python3
"""Parameterized SPA server for local euv-example testing.

Serves a directory over HTTP on :8080 with SPA fallback (non-/pkg/*
non-file paths serve index.html). The directory MUST be passed as
argv[1]; there is intentionally NO hardcoded fallback default, because
euv has multiple www roots (main checkout, worktrees, PR-branches) and
defaulting to any one silently serves stale artifacts.

Why this exists: a previous session hardcoded
`WWW_DIR = "/root/github/eastspire/euv/example/www"` in /tmp/spa_server.py
and copy-pasted that script into a worktree at
/root/github/eastspire/euv-worktrees/foo/example/www. The server kept
serving the OLD main-checkout www while the agent edited files in
the worktree www. The agent thought its changes weren't taking effect
and wasted ~30 min debugging before realizing the cwd of the running
python process didn't match the served directory.

Usage:
    python3 scripts/spa_server.py <path-to-www-dir>

Example:
    python3 scripts/spa_server.py /root/github/eastspire/euv-worktrees/foo/example/www

Verifying which directory the server is serving (important sanity
check after start, before any test):

    curl -sf -I http://localhost:8080/ | head -3
    curl -sf -o /dev/null -w '%{http_code} size=%{size_download}\\n' \\
        http://localhost:8080/pkg/euv_example_bg.wasm

Compare the size against `ls -la <your-www>/pkg/euv_example_bg.wasm` —
if they differ, the server is serving a different directory than you
think.

See euv-release/references/release-pitfalls.md "P11 — SPA server
hardcoded www_dir traps worktree edits" for the full incident.
"""

import http.server
import os
import socketserver
import sys

if len(sys.argv) < 2:
    print("Usage: python3 spa_server.py <path-to-www-dir>", file=sys.stderr)
    print("  No hardcoded default — pass the directory explicitly to avoid",
          file=sys.stderr)
    print("  serving stale artifacts from a different checkout.", file=sys.stderr)
    sys.exit(1)

WWW_DIR = os.path.abspath(sys.argv[1])
if not os.path.isdir(WWW_DIR):
    print(f"error: {WWW_DIR} is not a directory", file=sys.stderr)
    sys.exit(1)
if not os.path.isfile(os.path.join(WWW_DIR, "index.html")):
    print(f"warning: {WWW_DIR}/index.html not found — are you sure this is",
          file=sys.stderr)
    print(f"  a www dir? (expected at minimum index.html + pkg/*.wasm)",
          file=sys.stderr)

PORT = 8080


class SpaHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WWW_DIR, **kwargs)

    def do_GET(self):
        # SPA fallback: serve index.html for non-file paths (except /pkg/*)
        path = self.translate_path(self.path)
        if not os.path.isfile(path) and not self.path.startswith("/pkg/"):
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, *args, **kwargs):
        pass  # quiet


with socketserver.TCPServer(("", PORT), SpaHandler) as httpd:
    print(f"SPA server on :{PORT} serving {WWW_DIR}", flush=True)
    httpd.serve_forever()