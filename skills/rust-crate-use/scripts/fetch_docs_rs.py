#!/usr/bin/env python3
"""
fetch_docs_rs.py — Query docs.rs for a crate, return API summary.

Usage:
    python3 fetch_docs_rs.py <crate-name> [--version <x.y.z>] [--crate-info-only]

Output: JSON with:
    name              — input crate name (as provided)
    package_name      — official crates.io package name
    import_name       — Rust import name (usually package_name with - → _)
    crate_url         — canonical docs.rs URL for the target version
    versions          — top N stable versions (latest first)
    features          — list of available feature flags
    default_features  — bool, whether default features are enabled by default
    description       — one-paragraph description from docs.rs / Cargo.toml
    license           — SPDX license string
    repository        — source repo URL
    target_modules    — top-level modules (if --full) or just `["crate root"]`
    error             — present if query failed (network / 404 / etc.)

The script is read-only and caches nothing; it always queries docs.rs / crates.io
live so results are accurate. Designed to be called by the agent mid-task.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any

USER_AGENT = "rust-crate-use-skill/1.0 (Hermes Agent)"
DEFAULT_TIMEOUT = 20
USER_REQUEST = urllib.request.Request(
    "https://crates.io/api/v1/crates/{name}", headers={"User-Agent": USER_AGENT}
)


def http_get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def http_get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def package_to_import_name(name: str) -> str:
    """crates.io names: most are kebab-case → snake_case in Rust. Some end with
    @version suffix which must be stripped first."""
    base = name.split("@")[0]
    return base.replace("-", "_")


def fetch_from_crates_io(crate: str) -> dict[str, Any]:
    """Get package metadata from crates.io (description, repo, versions, features)."""
    url = f"https://crates.io/api/v1/crates/{urllib.parse.quote(crate)}"
    data = http_get_json(url)
    if "crate" not in data:
        raise ValueError(f"crates.io returned no 'crate' key for {crate!r}")
    k = data["crate"]
    # versions field is a list of version IDs, not version strings. Need second query.
    # For inspection purposes, use max_stable_version (the recommended stable).
    newest = (
        k.get("max_stable_version")
        or k.get("newest_version")
        or k.get("max_version")
        or k.get("default_version")
        or ""
    )
    # Top recent versions: parse the versions list and sort by created_at desc, then
    # fetch the first N. But that means N more HTTP calls. For now, return the IDs so
    # the user can see how many there are; the "newest_stable" is the actionable one.
    version_ids = k.get("versions") or []
    return {
        "package_name": k.get("name", crate),
        "newest_stable": newest,
        "total_versions": len(version_ids),
        "description": (k.get("description") or "").strip(),
        "repository": k.get("repository") or "",
        "homepage": k.get("homepage") or "",
        "documentation": k.get("documentation") or "",
        "downloads": k.get("downloads", 0),
        "recent_downloads": k.get("recent_downloads", 0),
    }


def fetch_features_from_repo(crate: str) -> list[str]:
    """Best-effort: try to extract feature list from docs.rs crate root page."""
    # docs.rs page exposes features in a small JSON blob at the top:
    #   <script id="rustdoc-vars" type="application/json">{"features":["a","b"], ...}</script>
    try:
        html = http_get_text(f"https://docs.rs/{urllib.parse.quote(crate)}/latest/{urllib.parse.quote(crate)}/")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    m = re.search(r'"features"\s*:\s*\[([^\]]*)\]', html)
    if not m:
        return []
    feats = re.findall(r'"([^"]+)"', m.group(1))
    return [f for f in feats if f]


def fetch_documentation_summary(crate: str, version: str) -> dict[str, Any]:
    """Read docs.rs version page, return summary of what user will see there."""
    base = f"https://docs.rs/{urllib.parse.quote(crate)}/{urllib.parse.quote(version)}"
    info: dict[str, Any] = {"crate_url": base + "/", "target_modules": ["crate root"]}
    try:
        html = http_get_text(base + "/" + urllib.parse.quote(crate) + "/index.html")
    except urllib.error.HTTPError as e:
        info["error"] = f"docs.rs returned {e.code} for {version}"
        return info
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        info["error"] = f"docs.rs network error for {version}: {e}"
        return info
    except Exception as e:  # last-resort safety net
        info["error"] = f"docs.rs unexpected error for {version}: {type(e).__name__}: {e}"
        return info
    # docs.rs returns 200 even for non-existent versions (with an empty placeholder
    # page). The placeholder normalizes the embedded JSON's "version" field to
    # "0.0.0", while real builds preserve the actual version. Compare the two
    # to detect the placeholder case.
    m = re.search(r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"version"\s*:\s*"([^"]+)"\s*\}', html)
    if not m:
        info["error"] = (
            f"docs.rs returned a non-rustdoc page for {crate} {version} "
            f"(could not find embedded crate/version JSON). The version may not "
            f"have been built yet or does not exist. Try --version with a known "
            f"release or omit --version to use newest stable."
        )
        return info
    embedded_name, embedded_version = m.group(1), m.group(2)
    if embedded_name != crate or embedded_version != version:
        info["error"] = (
            f"docs.rs has no real build for {crate} {version} "
            f"(page reports '{embedded_name} {embedded_version}', a placeholder). "
            f"The version may not have been built yet or does not exist. "
            f"Try --version with a known release or omit --version to use newest stable."
        )
        return info
    # Extract top-level module names from the navigation list
    class ModuleLister(HTMLParser):
        def __init__(self):
            super().__init__()
            self.modules: list[str] = []
            self.in_nav = False
            self.in_link = False
            self.current_href = ""
        def handle_starttag(self, tag, attrs):
            ad = dict(attrs)
            if tag == "nav" and ad.get("class", "").startswith("sidebar"):
                self.in_nav = True
            if self.in_nav and tag == "a" and "mod" in ad.get("href", ""):
                self.current_href = ad["href"]
                self.in_link = True
        def handle_endtag(self, tag):
            if tag == "a":
                self.in_link = False
                self.current_href = ""
        def handle_data(self, data):
            if self.in_link and data.strip() and data.strip() != crate:
                name = data.strip().rstrip("()")
                if name and not name.startswith("&") and len(name) < 64:
                    self.modules.append(name)
    lister = ModuleLister()
    try:
        lister.feed(html[:200_000])  # cap to first 200KB
    except Exception:
        pass
    seen = set()
    deduped: list[str] = []
    for m in lister.modules:
        if m not in seen:
            seen.add(m)
            deduped.append(m)
        if len(deduped) >= 20:
            break
    if deduped:
        info["target_modules"] = deduped
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description="Query docs.rs + crates.io for a Rust crate.")
    ap.add_argument("crate", help="Crate name on crates.io (e.g. 'lombok-macros', 'tokio')")
    ap.add_argument("--version", help="Specific version to inspect (e.g. '1.0.0'). Default: newest stable.")
    ap.add_argument("--crate-info-only", action="store_true",
                    help="Only fetch crates.io metadata; skip docs.rs HTML parsing.")
    args = ap.parse_args()

    result: dict[str, Any] = {
        "name": args.crate,
        "package_name": args.crate,
        "import_name": package_to_import_name(args.crate),
        "error": None,
    }

    # Step 1: crates.io metadata
    try:
        meta = fetch_from_crates_io(args.crate)
        result.update(meta)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result["error"] = f"crate {args.crate!r} not found on crates.io (404)"
        else:
            result["error"] = f"crates.io HTTP {e.code}: {e.reason}"
    except Exception as e:
        result["error"] = f"crates.io query failed: {e}"

    # Step 2: pick version (explicit > newest stable)
    target_version = args.version or result.get("newest_stable") or ""
    result["target_version"] = target_version

    if not args.crate_info_only and target_version:
        # Step 3: features
        try:
            result["features"] = fetch_features_from_repo(args.crate)
        except Exception as e:
            result["features"] = []
            result.setdefault("warnings", []).append(f"feature fetch failed: {e}")
        # Step 4: docs.rs page summary (a 404 is a warning, not a hard error:
        # crates.io metadata itself is still useful)
        try:
            doc = fetch_documentation_summary(args.crate, target_version)
            result.update(doc)
            if doc.get("error"):
                result.setdefault("warnings", []).append(doc["error"])
        except Exception as e:
            result["docs_error"] = f"docs.rs query failed: {e}"

    print(json.dumps(result, indent=2, ensure_ascii=False))
    # Exit code 0 = full success, 2 = hard error (e.g. 404 on crates.io),
    # 0 also when only warnings present (we already populated the JSON).
    return 0 if not result.get("error") else 2


if __name__ == "__main__":
    sys.exit(main())
