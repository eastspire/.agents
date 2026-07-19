"""Append entries to a persistent download script's DATA list.

Usage:
    python append_dl.py "N|name|url" "N|name|url" ...

Each argument is one entry, encoded as "N|name|url" (URL is verbatim,
including query string). Mutates DL_SCRIPT's DATA = [...] block by
regex-extending it (no sentinel markers, no fragile text replace).

Configure DL_SCRIPT for the run. The OUT_DIR in the download script
itself is authoritative; this helper only mutates DATA.
"""
import sys
import re
from pathlib import Path

# Default: persistent script used for the active country batch.
# Override with environment variable DL_SCRIPT if running multiple in parallel.
import os
DL_SCRIPT = Path(os.environ.get(
    "DL_SCRIPT",
    r"C:\Users\14915\AppData\Local\Temp\dl_full.py",
))


def main():
    entries = [tuple(arg.split("|", 2)) for arg in sys.argv[1:]]
    src = DL_SCRIPT.read_text(encoding="utf-8")
    pattern = re.compile(r"DATA = \[\s*\n(.*?)\n\]", re.DOTALL)
    m = pattern.search(src)
    if not m:
        raise SystemExit(f"No DATA = [ ... ] block found in {DL_SCRIPT}")
    existing = m.group(1).rstrip()
    new_lines = "".join(f"    ({n}, {name!r}, {url!r}),\n"
                        for n, name, url in entries)
    replacement = f"DATA = [\n{existing}\n{new_lines}]"
    new_src = pattern.sub(replacement, src, count=1)
    DL_SCRIPT.write_text(new_src, encoding="utf-8")
    prior = sum(1 for ln in existing.splitlines() if ln.strip())
    print(f"Appended {len(entries)} entries; DATA now has {prior + len(entries)} items")


if __name__ == "__main__":
    main()
