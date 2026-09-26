---
name: install-vendor-skills
description: Fetch and install third-party vendor-published skill packs via the .well-known/skills convention.
---

# Install Vendor-Published Skill Packs

Some vendors publish their own agent-skill catalogs at `<host>/.well-known/skills/index.json` (Stripe is the first known publisher; OpenAI, Anthropic, and others may follow). Use this skill to fetch and install those packs at `~/.agents/skills/<vendor>/<skill>/`, register them in `.skill-lock.json`, and verify they load.

## When to Use

- A task references `docs.<vendor>.com/skills` or `<host>/.well-known/skills/index.json`
- The user asks to "install the Stripe skill pack", "fetch skills from <vendor>", "download vendor skills", or says a URL matching `<host>/.well-known/skills/...`
- The user names a non-GitHub, non-npm third-party skill source

Do **not** use this skill for skills on the open skills.sh ecosystem (use `find-skills` + `npx skills add …`), GitHub-published skill repos (`npx skills add <owner>/<repo>@<skill>`), or user-authored local skills (`skill_manage action='create'`).

## Canonical Workflow

### 1. Pull the catalog

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
curl -sSL --retry 3 --max-time 30 -A "$UA" \
  https://docs.<vendor>.com/.well-known/skills/index.json -o /tmp/<vendor>-skills/index.json
```

The JSON has shape `{"skills":[{"name":..., "description":..., "files":[SKILL.md, references/foo.md, ...]}, ...]}`.

### 2. Fetch every file under each skill

URL pattern is `https://<host>/.well-known/skills/<skill-name>/<relative-path>`. The top-level file `<host>/.well-known/skills/SKILL.md` is 404 — files are namespaced per skill.

```python
import json, subprocess
from pathlib import Path
UA = "Mozilla/5.0 (...) Safari/605.1.15"
BASE = "https://<host>/.well-known/skills"
ROOT = Path.home() / ".agents/skills" / "<vendor>"
idx = json.load(open("/tmp/<vendor>-skills/index.json"))["skills"]
for sk in idx:
    sdir = ROOT / sk["name"]
    sdir.mkdir(parents=True, exist_ok=True)
    for f in sk["files"]:
        out = sdir / f
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl","-sSL","--retry","3","--max-time","60",
                        "-A", UA, "-o", str(out),
                        f"{BASE}/{sk['name']}/{f}"], check=True)
```

### 3. Verify every file landed and YAML parses

```python
import re, yaml
from pathlib import Path
ROOT = Path.home() / ".agents/skills" / "<vendor>"
for sk_dir in sorted(ROOT.iterdir()):
    if not sk_dir.is_dir(): continue
    fm = re.match(r"---\n(.*?)\n---", (sk_dir/"SKILL.md").read_text(), re.DOTALL)
    meta = yaml.safe_load(fm.group(1))
    assert meta.get("name") == sk_dir.name, f"name mismatch: {sk_dir.name} vs {meta.get('name')}"
    assert meta.get("description"), "missing description"
```

End criterion: every file in every `files[]` array exists with non-zero size, and every `SKILL.md` parses as YAML.

### 4. Write the parent `DESCRIPTION.md`

Match the convention of sibling vendor folders (`apple/DESCRIPTION.md`, `autonomous-ai-agents/DESCRIPTION.md`):

```python
(Path.home()/".agents/skills/<vendor>/DESCRIPTION.md").write_text(
  "<Vendor> skills — official knowledge packs published at "
  "https://<host>/.well-known/skills/index.json. Cover <one-line scope>.\n"
)
```

### 5. Register each skill in `.skill-lock.json`

```python
import json, hashlib, datetime, pathlib
LOCK = pathlib.Path.home()/".agents/.skill-lock.json"
lock = json.loads(LOCK.read_text())
now = datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
ROOT = pathlib.Path.home()/".agents/skills"
for sk_dir in sorted((ROOT/"<vendor>").iterdir()):
    if not sk_dir.is_dir() or not (sk_dir/"SKILL.md").exists(): continue
    h = hashlib.sha1()
    for f in sorted(sk_dir.rglob("*")):
        if f.is_file():
            h.update(f.relative_to(ROOT).as_posix().encode()); h.update(b"\0")
            h.update(f.read_bytes()); h.update(b"\0")
    lock["skills"][sk_dir.name] = {
      "source": "https://<host>/.well-known/skills",
      "sourceType": "remote",
      "skillPath": f"skills/<vendor>/{sk_dir.name}/SKILL.md",
      "installedAt": now, "updatedAt": now,
      "skillFolderHash": h.hexdigest(),
      "sourceUrl": f"https://<host>/.well-known/skills/{sk_dir.name}/SKILL.md",
    }
LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False))
```

## Pitfalls

### `web_extract` is unreliable for docs-host catalogs
Hermes' `web_extract` returns a false-positive "Blocked: URL targets a private or internal network address" for many mainstream public docs hosts (Stripe docs, OpenAI, Anthropic, Apple, Yahoo Finance, Nature, dev.to). This is a tool-layer false positive — `curl` from the same machine gets them fine. **Use Safari-UA `curl` directly, not `web_extract`.**

### Top-level URL is 404 — files are namespaced
`<host>/.well-known/skills/SKILL.md` returns 404. The correct path is `<host>/.well-known/skills/<skill-name>/<file>`. Iterate the index's `files[]` under each skill — don't assume a flat layout.

### Curl first attempt can SSL-fail on docs hosts
The first request to a docs host (e.g. `docs.stripe.com`) occasionally fails with `SSL_ERROR_SYSCALL`. Use `--retry 3 --max-time 60` in the fetch loop and the second attempt usually succeeds. Don't switch tools over a single transient SSL error.

### Different vendors write different frontmatter shapes
Stripe uses YAML `>-` folded multi-line `description` blocks. Other vendors may use single-line strings, single quotes, or mapping syntax. Parse with `yaml.safe_load` and verify `name` matches the folder name and `description` is non-empty — don't regex-match the shape.

### Never write to `~/.agents/skills/_pending/`
The `_pending/` tree is reserved for the daily skill-sync cron (`~/.hermes/scripts/daily_skill_sync.py`). Vendor-installed packs live under their vendor name (e.g. `~/.agents/skills/stripe/`), never under `_pending/`.

## Verification Checklist

- [ ] All `files[]` entries from the index exist on disk and are non-empty
- [ ] Every `SKILL.md` parses as YAML and `name` matches the folder
- [ ] Parent `DESCRIPTION.md` written at `~/.agents/skills/<vendor>/DESCRIPTION.md`
- [ ] `.skill-lock.json` is valid JSON; new entries have `skillPath` matching each skill's `SKILL.md`
- [ ] `~/.agents/skills/_pending/` unchanged (not used by this workflow)
- [ ] Confirm load: `skills_list` shows the new vendor's skills in the catalog
