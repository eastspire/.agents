#!/usr/bin/env python3
"""Run a command with a hard timeout. macOS ships without GNU `timeout`; this
fills the gap. Returns the child process's exit code, or 124 on timeout.

Usage:
    timeout.py SECONDS CMD [ARG ...]

Exit codes:
    0-127   : exit code of CMD (or signal number + 128)
    124     : CMD was killed by timeout
    125     : bad arguments
"""
import subprocess, sys

if len(sys.argv) < 3:
    sys.exit(125)

try:
    secs = int(sys.argv[1])
except ValueError:
    sys.stderr.write(f"timeout.py: not an integer: {sys.argv[1]!r}\n")
    sys.exit(125)

p = subprocess.Popen(sys.argv[2:])
try:
    rc = p.wait(timeout=secs)
    sys.exit(rc)
except subprocess.TimeoutExpired:
    p.kill()
    p.wait()
    sys.exit(124)