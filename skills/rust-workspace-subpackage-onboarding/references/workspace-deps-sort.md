# Sort rule for `[workspace.dependencies]`

The user's exact ordering rule, observed across their hyperlane workspace and adjacent projects.

## Rule

Inside `[workspace.dependencies]` entries are placed in **two groups**:

1. **Intra-workspace `path = "..."` entries first**, sorted within the group by:
2. **External (crates.io) entries second**, sorted within the group by:

**Per-group sort key**: ascending by the **full line length**, where "full line" is `len("name = value")` including the ` = ` separator and the entire RHS. Ties broken by **lexical order on the name**.

## Why line length, not key length

The user said "整体长度" (overall / whole length) when correcting an earlier key-only sort. Counting only the key (`len("http-compress") == 13`) lumps together lines that visually look different lengths (`http-compress = { path = "compress", version = "3.0.28" }` vs `http-request = { path = "request", version = "8.91.128" }`). Counting the whole line captures the visual weight and produces a cleaner layout.

## Worked example

`[workspace.dependencies]` after sorting:

```
hyperlane-cli = { path = "cli", version.workspace = true }        # len 58
hyperlane-core = { path = "core", version.workspace = true }      # len 60
hyperlane-type = { path = "type", version.workspace = true }      # len 60
http-compress = { path = "compress", version.workspace = true }    # len 63
http-constant = { path = "constant", version.workspace = true }    # len 63
http-request = { path = "request", version.workspace = true }     # len 61
hyperlane-macros = { path = "macros", version.workspace = true }  # len 64
```

Note the line for `http-request` (61 chars) is shorter than the others and correctly placed between the 60-char and 63-char lines, even though its key (`http-request`, 12) is shorter than `hyperlane-macros` (16). Key-only sort would have placed it elsewhere.

## Edge case: multi-line table entries

`features = [...]` or `default-features = false` causes some entries to span multiple lines. **Do not sort by line length in this case** — it sorts by the first line only and produces nonsense. Either:

- Inline the table onto one line so all lines are comparable (`notify = { version = "8.2.0", default-features = false, features = ["macos_fsevent"] }` on one line).
- Or accept that the multi-line entries will not sort cleanly and just put them after the single-line entries, sorted among themselves by first-line length.

This project (hyperlane) uses the first form: all `features = [...]` and `default-features` are inline.

## Audit script

Run this against the root `Cargo.toml` after editing:

```python
import tomllib
from pathlib import Path

text = Path("Cargo.toml").read_text()
t = tomllib.loads(text)
deps = t["workspace"]["dependencies"]

# 1. Local-first
def is_local(n):
    return isinstance(deps[n], dict) and "path" in deps[n]

local  = [n for n in deps if is_local(n)]
extern = [n for n in deps if not is_local(n)]
assert all(is_local(n) for n in local) and all(not is_local(n) for n in extern), "groups not contiguous"

# 2. Within each group, full-line length ascending then lexical
def line_len(n):
    # Reconstruct the actual line by reading the file and finding it
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(f"{n} =") or s.startswith(f"{n}="):
            return len(line)
    raise KeyError(n)

for grp in (local, extern):
    sorted_v = sorted(grp, key=lambda x: (line_len(x), x))
    assert grp == sorted_v, f"group not sorted: got {grp}, want {sorted_v}"

print("OK")
```

For a quick eyeball check, just look at the file and confirm:

- Every `path = ...` entry sits before every non-`path` entry.
- Within each group, line widths don't decrease as you go down.

## When to re-apply this sort

After **any** change to `[workspace.dependencies]`:

- Adding or removing entries (always).
- Changing a `version = "x.y.z"` value (the line length changes — sort position may shift).
- Inlining a multi-line table or splitting one (rare).

The user reviews diffs by eye and notices when sort order drifts.
