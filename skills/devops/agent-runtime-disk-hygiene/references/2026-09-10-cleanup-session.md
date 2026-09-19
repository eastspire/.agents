# 2026-09-10 cleanup session — fresh evidence & suggested SKILL.md patches

Session transcript: user said "清理磁盘", agent ran the disk-hygiene triage, freed
~743 MB (real disk), and reported. This file captures the **new lessons** not yet
in SKILL.md (2026-08-22 baseline, v1.0.0) and a **suggested patch draft** the user
can adopt on next curator pass.

## New lesson 1 — `du -sh` unit mixing makes arithmetic wrong (high-impact pitfall)

The `du -sh` output mixes K/M/G in a single stream. Summing it with awk by
stripping the last char makes numbers blow up when K is treated as M, etc.

Concrete examples from this session (all on the same VM):

```
$ du -sh /tmp/*.png | awk '{sum+=substr($1,1,length($1)-1)+0} END {printf "%.0fM\n", sum}'
29024M         # ← WRONG: 472 pngs actually 27M total, awk read "K" as "M"

$ du -cb /tmp/*.png | tail -1
28701801 total # ← correct: 27.4 MB
```

Same trap bit the chromium count:

```
$ du -sh /tmp/org.chromium.Chromium.* | awk '{sum += ...} END {printf "%.0fM\n", sum}'
3557M          # ← WRONG: actual 154 MB
$ du -cb /tmp/org.chromium.Chromium.* | tail -1
154319977      # correct: 147 MB
```

**Rule**: never accumulate `du -h` output with shell arithmetic. Use one of:

```bash
# byte-level (most reliable)
du -cb /tmp/<pattern> | tail -1

# block-level (also reliable, fixed at 1024-byte blocks)
du -s /tmp/<pattern>      # total in KB

# human-readable single total
du -shc /tmp/<pattern> | tail -1   # last line is "<size> total" with consistent unit
```

The `du -shc` form is the most user-friendly for reports because it always picks
the unit that makes the single total line legible.

## New lesson 2 — the "top 10 offenders" signature on this VM shifted

SKILL.md v1.0.0 was authored against an Aug 2026 baseline where `/tmp/cp-*`
dominated. This session (Sep 2026) showed a **different dominant pattern**:

| Source | Size | Notes |
|---|---|---|
| `/tmp/cargo-installpK2A6n` (cargo install run) | 331 MB | one-shot, not target/ — finished install left the build tree behind |
| `/tmp/euv-expand-test/target` | 220 MB | a temp test project created during the "test expand macro" debugging session |
| `/tmp/org.chromium.Chromium.*` | 154 MB total | 250 dirs, two big fetcher dirs dominated (114M + 27M), rest ~16K each |
| `/tmp/playwright-download-*` | 48 MB | two alive, five empty |

So the agent's mental model "cp-* is the leak" needs to be **conditional**: check
the actual top offenders first, the dominant pattern may be cargo/expand/playwright
artifacts on a different week.

## New lesson 3 — small-dir mass adds up but cleanup ROI is bad

246 leftover chromium fetcher dirs at ~16 KB each = ~4 MB total. Cleaning them
requires 246 separate `rm` calls (each its own approval gate under the mass-delete
block). Cleanup ROI ≈ zero — not worth the approval churn. Stop after the 2-3
big ones unless disk pressure is acute.

## Real disk-allocation map (this VM, 2026-09-10)

To set expectations — `/tmp` cleanup rarely moves the needle on a small root disk:

```
/                60G, 54G used, 90% full, 6.6G available
├─ /var/lib/docker          13G  ← USER ACTIVE SERVICES, do not touch
├─ /root                     32G
│  ├─ /root/github           15G
│  │  ├─ hyperlane-dev/...   7G (target 6.9G)
│  │  ├─ euv-dev/euv-app     2.7G (sdk 2.5G Android NDK/JDK)
│  │  ├─ euv-dev/euv         1.4G (target)
│  │  └─ eastspire/*         ~2.5G (water-surface target 1G, euv target 919M, ...)
│  ├─ /root/LTPP-MINIMAX     659M (chrome-linux 658M, KEEP)
│  └─ /root/.cache           ~1G (sccache etc., regenerable)
├─ /usr                      11G (system — don't touch)
├─ /var                       6.2G (system — don't touch)
├─ /www                       3.2G (web root — check with user)
└─ /tmp                     888M (cleanup target)
```

This means: a "清理磁盘" request that only touches `/tmp` reclaims at most
~1-2 GB even when nuking everything reasonable. To get real space back (5-10+ GB),
the agent needs to propose `cargo clean` on Rust projects and `docker system prune`
(only with explicit user approval per USER PROFILE). Always **report the actual
reclaim number**, not a vague "cleaned up".

## Suggested SKILL.md patches (for next curator pass)

These are written as drop-in replacements for SKILL.md sections. The user can
adopt via `hermes curator adopt agent-runtime-disk-hygiene` then apply, OR
include them in the next PR.

### Patch A — "The recurring leak signature" table

Add these rows to the existing table:

| `cargo install` leftovers | `/tmp/cargo-install<random>/release/{deps,build}/` | build tree left after `cargo install` finishes; safe to `rm -rf` once install confirmed succeeded | 100 MB – 1 GB |
| Temp Rust test scratch | `/tmp/euv-*-test/target`, `/tmp/foo/target`, etc. | ad-hoc scratch repos used to reproduce issues; target/ is the only reclaimable part | 100 MB – 1 GB |
| `browser-use` Chrome fetcher dirs | `/tmp/org.chromium.Chromium.chrome_url_fetcher_<rand>` | one per Chromium network fetch session; ~250 dirs typical, dominated by 1-2 big ones | 16 KB – 120 MB |

### Patch B — new "du unit-mixing pitfall" section

Insert under §"Triage flow":

```bash
# ALWAYS use byte-level total when accumulating across files of mixed sizes.
# `du -h` mixes K/M/G in the stream — shell arithmetic on it gives garbage.
du -cb /tmp/<pattern> 2>/dev/null | tail -1   # bytes
# or for a single human-readable total:
du -shc /tmp/<pattern> 2>/dev/null | tail -1   # last line "<size> total"
# AVOID:
du -sh /tmp/<pattern> | awk '{sum+=substr($1,1,length($1)-1)} END ...'  # broken
```

### Patch C — small-dir cleanup ROI note

Under §"Cleanup recipe" add:

> **Skip leftover dirs < 1 MB individually.** When `du -sh /tmp/org.chromium.*`
> shows 246 entries at ~16 KB each, total reclaim is ~4 MB. The per-dir
> `rm -rf` approval gate cost dominates the savings. Clean only the top
> offenders (top 1-2 by size) unless disk pressure is acute.

### Patch D — "Real disk-allocation map" addition

Under §"What NEVER to delete" or as a new §"Setting expectations" add:

> On the 2026-09-10 60G VM, `/tmp` total is ~888 MB even when maximally
> leaked. Cleaning `/tmp` reclaims at most 1-2 GB. To get 5-10+ GB back
> on a single pass, propose `cargo clean` on user Rust projects (reversible,
> safe) and `docker system prune` (needs explicit user approval — see
> USER PROFILE Docker isolation rule). Always report the **actual** bytes
> reclaimed, not a vague "cleaned up".

## Cron-friendly script additions

If extending `/root/scripts/cleanup-tmp-cp.sh`, the allowlist prefix list
should grow to:

```bash
ALLOWLIST_PREFIXES=(
    "/tmp/cp-"
    "/tmp/c-"
    "/tmp/cargo-"
    "/tmp/cargo-install"     # NEW: one-shot cargo install leftovers
    "/tmp/org.chromium.Chromium.chrome_url_fetcher_"  # NEW: but ONLY the fetcher dirs
    "/tmp/playwright-download-"   # NEW: empty ones mostly; KEEP if .still-actively-downloading
)
```

**Caution** for `/tmp/org.chromium.Chromium.*`: do NOT match the bare prefix
`/tmp/org.chromium.Chromium.` because that includes live singleton/lock
symlinks (`/tmp/org.chromium.Chromium.<rand>` with no `chrome_url_fetcher_`
suffix are active session handles). Match only the `chrome_url_fetcher_`
suffix to be safe. Equivalent guard for any future chromium pattern.