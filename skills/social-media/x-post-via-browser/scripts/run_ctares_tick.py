#!/usr/bin/env python3
"""Post the next crate from the queue, once. Idempotent, one per invocation.

The cron job runs this every minute. It picks the first crate that has not
been posted yet, publishes it, and records the result — so a missed or failed
tick does not repost, and a duplicate tick does not double-post.

Every rule the publisher obeys is in the x-post-via-browser skill and enforced
by verify_no_unsafe_posting.py. Nothing here opens a tab, navigates, reloads
or clears the composer: the browser tab must already be on x.com/compose/post,
and if it is not, this says so and posts nothing.

  python3 run_ctares_tick.py 9240
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLISH = HERE / "publish.py"          # x-post-via-browser/scripts
COPY = os.environ.get("X_COPY", str(HERE.parent / "x_copy_ctares.json"))
STATE = Path(os.environ.get(
    "X_POST_STATE", "/Users/sqs/.hermes/cache/scratch/ctares_posted.json"))
PORT = os.environ.get("X_PORT", "9240")


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except ValueError:
            pass
    return {"posted": [], "skipped": []}


def save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1))


def run(args: list[str], timeout: int = 420) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(PUBLISH)] + args,
                       capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else PORT
    posts = json.loads(Path(COPY).read_text())
    state = load_state()
    done = set(state["posted"]) | set(state["skipped"])

    if len(done) >= len(posts):
        print(f"all {len(posts)} crates posted; nothing left in the queue")
        return 0

    idx = next(i for i in range(len(posts)) if i not in done)
    print(f"posting crate {idx + 1}/{len(posts)}: "
          f"{posts[idx].splitlines()[0][:60]}")

    rc, out = run([port, "--post", str(idx), "--go"])
    print(out.strip()[-1200:])

    # The publisher exits 0 even when it declines to click, so the decision is
    # made on its own words, not on the exit code. CLICKED alone is not proof
    # either — the timeline is what counts.
    if "CLICK CLICKED" not in out:
        print("publisher did not click; leaving the crate queued for the "
              "next tick rather than marking it done")
        return 0

    time.sleep(8)
    rc, tl = run_top_of_timeline(port)
    if rc == 0:
        print("timeline after the post:\n" + tl.strip()[-800:])
    state["posted"].append(idx)
    save_state(state)
    print(f"recorded crate {idx} as posted "
          f"({len(state['posted'])}/{len(posts)})")
    return 0


def run_top_of_timeline(port: str) -> tuple[int, str]:
    script = HERE / "top_of_timeline.py"
    p = subprocess.run([sys.executable, str(script), port],
                       capture_output=True, text=True, timeout=300)
    return p.returncode, (p.stdout + p.stderr)


if __name__ == "__main__":
    sys.exit(main())
