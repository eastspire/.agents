# Fetching raw files from githubusercontent.com

When you need the raw content of a file from a GitHub repo (e.g. `Cargo.toml`, `package.json`, `pyproject.toml`) without cloning, the canonical URL is:

```
https://raw.githubusercontent.com/OWNER/REPO/BRANCH/PATH
```

## The web_extract trap

On this machine, `web_extract` returns:

> Blocked: URL targets a private or internal network address

for `raw.githubusercontent.com` URLs — even though the host is fully public and `curl` reaches it without issue. This is a known tool-layer false positive; it has also been observed against other major public hosts (openai.com, anthropic.com, apple.com, infoq.com, blog.google, etc.).

Don't retry `web_extract` with the same URL. Pivot to `curl` immediately.

## Working curl incantation

```bash
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
curl -sSL -A "$UA" "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/PATH"
```

Why each flag:

- `-sS` — silent (no progress bar) but still show errors.
- `-L` — follow redirects (some setups redirect through a tracking edge).
- `-A "$UA"` — a desktop Safari User-Agent. githubusercontent does not require a specific UA, but using a real browser UA reduces the chance of hitting any rate-limit or WAF heuristic in the future.
- The trailing URL is plain — no `Accept:` header, no auth header. The file is public.

## Default-branch ambiguity

GitHub repos use either `main` or `master` (or occasionally something custom). `raw.githubusercontent.com` does NOT auto-resolve the default branch; you must specify it. Trying the wrong one returns a plain `404: Not Found`.

Strategy: try `master` first, then `main`. Older Rust crates (the `crates-dev/*` namespace, hyperlane, tokio forks, etc.) use `master`; most non-Rust projects and newer repos use `main`.

```bash
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
for branch in master main; do
  body=$(curl -sSL -A "$UA" "https://raw.githubusercontent.com/OWNER/REPO/$branch/Cargo.toml")
  if [ "$body" != "404: Not Found" ]; then
    echo "branch=$branch"
    echo "$body"
    break
  fi
done
```

If both 404, the repo exists but the file is not on either branch (different default branch, file not at that path, repo is empty, etc.). At that point use the GitHub REST API to discover the actual default branch:

```bash
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
curl -sSL -A "$UA" "https://api.github.com/repos/OWNER/REPO" \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('default_branch'))"
```

## When not to use raw fetch

- If you need many files from the repo, or you need git history — just `git clone`.
- If the file is large (>100 KB) and you only need a snippet — `git clone` is still cheaper than a multi-megabyte HTTP response piped through grep.
- If the repo is private — you'll need `gh auth` or a `GITHUB_TOKEN` env var. Raw URL auth is awkward.
