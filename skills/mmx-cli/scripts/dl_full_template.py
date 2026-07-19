"""Persistent download script for batch AI image generation.

Append entries via append_dl.py or via the patch tool (preferred for
batched MCP workflows — see mmx-cli skill / batch-image-generation).

Run this script to (re-)write all images to OUT_DIR using the requested
{NNN}_{name}.jpeg filename.

Re-runs are idempotent: identical URLs overwrite identical files.

Override OUT_DIR via the OUT_DIR environment variable, e.g.:
    OUT_DIR="C:\\Users\\14915\\Downloads\\china_nature_100_2k\\jpg2\\usa" python dl_full.py
"""
import urllib.request
import os
from pathlib import Path

# Default: USA batch under the china_nature_100_2k project. Override per-run.
OUT_DIR = os.environ.get(
    "OUT_DIR",
    r"C:\Users\14915\Downloads\china_nature_100_2k\jpg2\usa",
)
os.makedirs(OUT_DIR, exist_ok=True)

DATA = [
    # Append entries here via append_dl.py — never edit this list by hand
    # for batches larger than ~5. See mmx-cli skill / batch-image-generation.
]

ok = fail = 0
errors = []
for n, name, url in DATA:
    p = Path(OUT_DIR) / f"{n:03d}_{name}.jpeg"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        p.write_bytes(data)
        ok += 1
        print(f"OK {n:3} {name}: {len(data)} bytes")
    except Exception as e:
        fail += 1
        errors.append((n, name, e))
        print(f"FAIL {n:3} {name}: {e}")

print(f"--- ok={ok} fail={fail} ---")
