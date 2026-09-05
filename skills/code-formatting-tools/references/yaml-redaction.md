# YAML redaction in shared artifacts

When you publish a YAML config (essay blog post, README, screenshot, etc.) and need to redact secret-looking fields without breaking the file's parseability, the marker you choose matters.

## The trap

`[REDACTED]` (unquoted) is **not** a YAML string — YAML 1.2 parses it as a **flow sequence** (a one-element list). The verifier sees:

```yaml
password_hash: [REDACTED]      # ← parses as ["REDACTED"] (a list)
```

This silently changes the type. If downstream code expected `String`, it now sees `Vec<String>` and breaks.

```yaml
password: [REDACTED]           # same trap
api_key: [REDACTED]            # same trap
session_key: [REDACTED]        # same trap
```

## The fix

Quote the marker so YAML keeps it as a string:

```yaml
password_hash: "[REDACTED]"    # ← parses as "[REDACTED]" (str)
password: "[REDACTED]"         # str
api_key: "[REDACTED]"          # str
```

The double quotes are part of the YAML syntax, **not** part of the rendered string. A reader running `grep '"\[REDACTED\]"' config.yaml` still finds it; a reader visually scanning the file still sees the redaction marker.

## Empty vs missing values

YAML distinguishes empty (`''`) from missing. To preserve the original shape (so the reader can tell which fields were configured-but-now-redacted vs never-configured), keep empty strings as `''`:

```yaml
# OK — empty preserved
api_key: ''

# OK — redacted value
password_hash: "[REDACTED]"

# NOT OK — both become indistinguishable after redaction if you use [REDACTED]
# for empty too:
api_key: "[REDACTED]"          # ← misleading; looks redacted but wasn't
```

Use `[REDACTED]` only for fields that had a non-empty value before. Use `''` for fields that were already empty (don't second-guess the original shape).

## Env-var names are not secrets

`access_token_env: BWS_ACCESS_TOKEN` and similar "env var **name**" fields are **not** sensitive — they name a variable, they don't contain its value. Keep these as-is, don't redact.

```yaml
secrets:
  bitwarden:
    enabled: false
    access_token_env: BWS_ACCESS_TOKEN    # ← keep, it's the variable NAME
    project_id: ''                        # ← empty, preserve
    server_url: ''                        # ← empty, preserve
```

A naive `awk` / `sed` redact-everything-looking-like-a-key pass would mangle these — verify by re-reading the config source rather than blanket-redacting.

## Re-formatting risk

When the YAML block lives inside a markdown code fence, downstream tooling may auto-format it. Two common cases:

1. **Prettier / dprint on markdown**: usually leaves code fences alone, but `prettier --write "**/*.md"` on a file with YAML in a code block can shift indentation if the file is otherwise Prettier-clean. After running `prettier --write`, re-grep for the `[REDACTED]` marker and the surrounding key shape.
2. **Custom markdown plugins that parse code blocks**: some renderers (Hugo goldmark extensions, Docusaurus MDX components) will try to parse the fenced block as YAML if the language tag matches. Adding a language tag like ` ```yaml ` is normally safe; problems arise with ` ```toml ` confused-for-`yaml ` or vice versa.

If you format the markdown, re-verify by extracting the block and running `yaml.safe_load()` on it:

```python
import re, yaml
md = open("post.md").read()
block = re.search(r"```yaml\n(.*?)\n```", md, re.DOTALL).group(1)
parsed = yaml.safe_load(block)
assert parsed["key"]["password_hash"] == "[REDACTED]", "type drift — recheck"
```

## When this matters

- Writing an essay / blog post about your own config (Hermes, app settings, CI secrets)
- Screenshotting a `.env` file or `~/.config/<app>/config.yaml` for a tutorial
- Sharing a CI workflow file in docs (GitHub Actions masks secrets in logs but not in committed YAML)
- Committing a sanitized example to `examples/` in an open-source project

## When NOT to redact

- **Local-only files** — keep full values; just don't commit them
- **Private repos** that won't be made public — leave them as-is, secrets at rest in private repos are fine
- **Hashes of passwords** — the hash itself isn't usable to log in. Only redact if you're worried about offline brute force (rare for properly-hashed passwords)

## TL;DR

```yaml
# Wrong
password_hash: [REDACTED]

# Right
password_hash: "[REDACTED]"
```

Quote your redaction marker. Verify with `yaml.safe_load`. Preserve empty fields as `''`. Don't blanket-redact env var names.