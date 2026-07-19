# Batch Image Generation — Verified Workflow

**Use when**: generating N>1 images with `mcp__MiniMax__text_to_image` (or `mmx image generate`) for an ordered list (gallery, illustration set, prompt-to-photo pipelines). Validated end-to-end 2026-07-19 with N=100 concurrent calls.

## TL;DR pattern

```
1. Author all prompts as a Python dict {number: (name, prompt)} → save to .py
2. Fire MCP calls in batches of 5 concurrent (parallel tool calls in one turn)
3. Collect URLs from each batch's response
4. ONE Python script does batched urllib downloads (NOT bash + curl) → local .jpeg
5. Verify: count files, scan sizes, optionally vision_analyze sample
6. Trigger a single verify step before declaring done
```

## Step-by-step with the actual pitfalls

### 1. Prompt authoring (Python dict, not 100 separate files)

When N is large (10+), put all prompts in a single Python module. Reasons:
- Easy to iterate the wording across all
- The download script can `import` it to look up filenames
- One place to apply consistent style ("photographed on Sony A7R IV, golden hour, 8K quality")

```python
# all_prompts.py
PROMPTS = {
    3: ("九寨沟·五花海秋色", "A vertical photograph of Wuhua Hai..."),
    4: ("桂林·漓江山水", "..."),
    ...
}
```

### 2. Concurrent MCP calls — 5 per turn is the sweet spot

The MCP server has per-call overhead (TLS, request setup). With 5 calls/turn, 100 calls finish in ~20 turns of ~30s each. Higher concurrency (10+) risks timeouts; lower (1/turn) wastes wall-clock.

```python
# 5 tool calls in one assistant message → 5 in-flight at once
mcp__MiniMax__text_to_image(prompt="...", aspect_ratio="9:16", output_directory="...", n=1)
mcp__MiniMax__text_to_image(prompt="...", aspect_ratio="9:16", output_directory="...", n=1)
# ... up to 5
```

**Timeout handling**: the MCP client times out at 300s per call. If one call hangs (rare, but happens), it returns `{"error": "MCP call failed: TimeoutError: ... TimeoutError after 300.0s"}` while the others succeed. Re-fire just that one call in the next turn — DO NOT retry the whole batch.

### 3. URL extraction from MCP response

Response shape:
```json
{"result": "Success. Image URLs: ['https://hailuo-image-algeng-data.oss-cn-wulanchabu.aliyuncs.com/...?Expires=...&Signature=...']"}
```

`output_directory` is honored by MCP — and as of the 2026-07-19 Iceland/Korea/Japan/USA runs, the MCP tool **does** auto-save to that directory using a filename derived from the prompt (typically the subject / location phrase). Observed behavior: when prompted with "Blue Lagoon geothermal spa Iceland", the saved file was `001_蓝湖温泉_雷克雅未克.jpeg` style (numbered prefix + Chinese descriptive name). However, this behavior depends on the MCP tool's filename-extraction and is **not guaranteed across prompt styles** — for tight control over the exact `{NNN}_{chinese_name}.jpeg` filename, run the Python urllib download step below to overwrite/rename the file.

### 4. Download — use Python urllib, NOT bash curl

**Critical pitfalls with bash curl**:
- OSS signature URL contains `OSSAccessKeyId=LTAI5tB2SwrRwAtD23etQUbC` — the `L` (capital L) is easily mistranscribed as `I` (capital I) when typing URLs into a shell command. URL then 403s.
- Shell escaping of `&` in query strings requires careful quoting in bash. `&` is the background operator — must escape as `\&` or single-quote the URL.
- Downloaded file is sometimes 0 bytes or HTML error page — verify each download with `os.path.getsize` and re-fetch failures.

**Recommended Python pattern** (no shell, no escaping):
```python
import urllib.request
from pathlib import Path
import importlib.util

# Load the same prompts file to map # → filename
spec = importlib.util.spec_from_file_location("all_prompts", "all_prompts.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

URLS = [(3, "https://hailuo-image-algeng-data.oss-cn-wulanchabu.aliyuncs.com/...?Signature=..."), ...]

out = Path("./out")
ok = fail = 0
for n, url in URLS:
    name = mod.PROMPTS[n][0]
    path = out / f"{n:03d}_{name}.jpeg"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        path.write_bytes(data)
        ok += 1
    except Exception as e:
        print(f"FAIL {n}: {e}")
        fail += 1
print(f"ok={ok}, fail={fail}")
```

**Alternative** (CLI users, single-shot): `mmx image generate --prompt "..." --out-dir ./out --quiet --out-prefix "003_"` handles download natively. Use this for ad-hoc requests; use the Python urllib pattern for batches of 10+ where you need fine-grained retry control and consistent filenames.

### 5. Verification — never skip

Three checks, all fast:
```python
files = sorted(out.glob("*.jpeg"))
nums = [int(re.match(r"^(\d{3})_", f.name).group(1)) for f in files]
assert len(files) == 100, "missing files"
assert set(nums) == set(range(1, 101)), f"missing/duplicate: {set(range(1,101))-set(nums)}"
sizes = [f.stat().st_size for f in files]
assert all(s > 50_000 for s in sizes), f"too-small files: {[(f.name, f.stat().st_size) for f, s in zip(files, sizes) if s < 50000]}"
print(f"all 100 present, sizes {min(sizes)//1024}KB - {max(sizes)//1024}KB, total {sum(sizes)//1024//1024}MB")
```

### 6. Visual spot-check (optional but recommended)

Pick 2-3 random files and use `vision_analyze` with the **local path** (NOT the OSS URL — `vision_analyze` rejects OSS URLs as "unsafe or private URL"):
```
vision_analyze(image_url="C:/Users/.../out/007_青海湖_油菜花海.jpeg", question="...")
```

## User preference notes (for batch-image tasks)

Validated 2026-07-19:
- **Aspect ratio defaults to 1:1**. User can and will switch to 9:16 (vertical) or 16:9 mid-task. Always confirm `aspect_ratio` BEFORE generating, especially if the use case is mobile wallpaper, portrait gallery, story/reel format, or print photo.
- **"1 张/张 send to me" is initial rhythm preference**. After 2-3 samples approved, user typically says "全部跑完" or "继续生成直到任务完成" — switch to batch mode at that signal, don't ask.
- **Best Guess forward when ambiguous**: when user says "继续" without specifying aspect/prompt style, repeat the LAST verified style. Don't re-ask.
- **Honest about limits**: this tool generates AI art, not real photos. If user asks for "real photo / 8K / 全画幅 / DSLR capture" output, state the limitation ONCE upfront ("image-01 max 1024x1024, AI composition not optical capture"), offer to proceed with the limitation, then proceed. Do NOT pretend to deliver something the tool can't produce.

## Persistent download script + append helper (user-preferred pattern)

Validated pattern from the user's prompt — **explicit preference, learned from past failure**: do NOT generate one download script per batch. Maintain ONE persistent download script that grows across batches, plus a tiny append helper that regex-extends its `DATA = [...]` list.

```
dl_full.py           # ONE script. DATA = [ ... ] grows across batches.
append_dl.py         # pure helper: extends dl_full.py DATA list.
prompts.py           # {n: (name, prompt)} dict, also contains the (n,name,url) → filename mapping.
```

`append_dl.py` skeleton (uses regex on `DATA = \[\n(.*?)\n\]` so it survives whitespace drift):

```python
import sys, re
from pathlib import Path
DL = Path(r"C:\Users\14915\AppData\Local\Temp\dl_full.py")
entries = [tuple(arg.split("|", 2)) for arg in sys.argv[1:]]  # "n|name|url"
src = DL.read_text(encoding="utf-8")
pattern = re.compile(r"DATA = \[\s*\n(.*?)\n\]", re.DOTALL)
existing = pattern.search(src).group(1).rstrip()
new_lines = "".join(f"    ({n}, {name!r}, {url!r}),\n" for n, name, url in entries)
new_src = pattern.sub(f"DATA = [\n{existing}\n{new_lines}]", src, count=1)
DL.write_text(new_src, encoding="utf-8")
```

Workflow per batch:
1. Fire 5 parallel MCP calls → 5 URLs.
2. `python append_dl.py "N|name|url" ...` (5 args).
3. `python dl_full.py 2>&1 | tail -10` — re-runs over ALL prior entries too, but `write_bytes` is idempotent (same content → same bytes) and only OSS URL re-fetch is the actual network cost. To avoid re-downloading the world, **only append new entries; let the script's natural overwrite-with-same-bytes handle previous ones cheaply.**

Why this beats per-batch scripts:
- If a batch run is interrupted (MCP timeout, network drop, agent iteration cap), no prior progress is lost.
- Verification at end is one `dl_full.py` run that re-downloads nothing on already-complete files.
- One source of truth for the whole pipeline state — easier to resume / inspect / dedupe.

**Marker-pitfall to avoid**: don't put a sentinel comment like `# Entries appended here` inside the DATA list and try to do simple text-replace — the marker gets consumed on first append and subsequent runs fail. Use the regex on `DATA = \[\n(.*?)\n]` form above; it's marker-free and idempotent.

**Even faster append pattern (validated USA N=100, 2026-07-19)** — skip the `append_dl.py` helper entirely and use the `patch` tool's `mode='replace'` to insert the 5 new tuples directly into `DATA = [ ... ]`. The DATA list is naturally unique per line (each `(n, name, url)` is one record), so an `old_string` containing the LAST existing entry + `]` and a `new_string` ending with `]\n]` (no trailing comma on final entry) works every batch. One tool call replaces "write helper script + python helper.py + run dl_full.py" → still 2 calls (`patch` + `terminal run`). The helper script is still useful when you can't trust the patch boundary, but for clean machine-generated URL lists the patch path is strictly faster and avoids the regex dependency. Saved in patch args: only the previous tail entry + new lines; the diff is small enough that the tool's fuzzy match handles indentation drift reliably.

**Terminal-timeout pitfall on big download runs** (validated Korea N=85 run 2026-07-19): the `terminal` tool's default invocation has a 60s command-timeout; the download script's `urlopen(timeout=60)` is per request. On a 70+ entry DATA list, a slow OSS round-trip near the tail can exceed 60s and the terminal process is killed mid-write — leaving already-written files intact but the script interrupted. The persistent script's DATA is preserved (writes go to disk immediately per iteration), so the recovery is just **re-run the script**. Defensive fixes for future runs:
- Invoke with `python C:/path/dl_full.py` from a script that passes `--timeout 180` (or use `background=true` + `notify_on_complete=true` for very large runs) so a slow tail doesn't kill the terminal.
- Consider raising the script's per-request `timeout=60` to `timeout=120` in `dl_full_template.py` for batches > 50.
- Always check `len(disk_files) == len(DATA)` after re-run before declaring done — the script's `fail=` counter only reports exceptions, not "killed by terminal".

**`ls "*.jpeg" | wc -l` quirk on this Windows host** (validated same run): `ls "C:/Users/.../*.jpeg" 2>/dev/null | wc -l` returned 0 even when 15 files existed. Plain `ls "C:/path/" | wc -l` works correctly. Don't trust the glob-pipe form for file-count verification; prefer the Python verification snippet in §5 or `search_files(target='files', pattern='*.jpeg', path=<dir>)` for a count.

## Iteration-cap reality (agent can halt mid-task)

The agent may halt mid-batch due to a per-session iteration cap (observed 2026-07-19 Iceland run: stopped at 45/100 with 0 failures, 0 timeouts — clean stop, not error-driven; **also observed USA run same day: halted at 75/100 with 0 failures, 0 timeouts** — the cap is hit AFTER ~20 batches × ~5 turns of patches/downloads, not at any predictable count). When picking up an interrupted run:

```python
import re
from pathlib import Path
nums = sorted({int(re.match(r"^(\d{3})", f.name).group(1))
               for f in Path(outdir).glob("*.jpeg")})
gaps = sorted(set(range(1, 101)) - set(nums))
# gaps[0] is the next entry to generate
```

1. List present numbers; identify next gap; resume at `gaps[0]`.
2. The persistent download script is already populated with valid URLs for prior entries — leave them as-is; they re-write identical bytes on re-run.
3. If you lost the prompt file, regenerate URLs by re-firing MCP for the gap range (cheap). NEVER re-fire calls for already-present entries (faster, cheaper, no risk of style drift).

If a user says "continue from where you stopped", the recovery verb is **re-run the download script after re-firing only the gap entries**; don't re-run the whole generation.

**Resume procedure when the halt is in the parent agent (not a child subagent)** (validated USA 2026-07-19): the subagent that hit the iteration cap cannot continue itself. The parent agent should:
1. Read the persistent `dl_full.py` to see how many entries are already appended (each `(n, name, url)` tuple is one line).
2. Compute gaps = sorted(set(range(1, N+1)) - {n for n,_,_ in DATA}).
3. Spawn a new subagent (or continue manually) that starts by reading `prompts.py`, fires 5-way parallel MCP calls for `gaps[0]:gaps[0]+5`, patches the next 5 entries in via the `patch` tool, runs the downloader, and repeats until `len(gaps) == 0`.
4. The new subagent should NOT re-run the already-completed batches (already on disk); only append+download for gaps. The existing downloader is idempotent — re-running it after appending more entries writes only the new ones.

## Cost note

Each `mcp__MiniMax__text_to_image` call is one API invocation = one billable image generation. A batch of 100 = 100 cost units. The MCP server surfaces a `COST WARNING` in the tool description — surface this to user before kicking off large batches, not after.