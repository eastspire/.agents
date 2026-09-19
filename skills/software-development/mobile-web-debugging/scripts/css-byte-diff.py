#!/usr/bin/env python3
"""Byte-level CSS rule comparison between a reference and a target site.

Use case: headless verification of safe-area / mobile CSS fixes when
``env(safe-area-inset-*)`` always returns 0 in headless Chrome. Two sites
loading the same CSS class definitions from a shared upstream (e.g. euv-docs
vs. euv example) MUST emit byte-identical CSS rules for those classes. This
script captures ``cssRules[i].cssText`` for each requested class on each site
and emits a JSON diff that is human-readable.

Why this works: CSS for euv / euv-ui is generated at build time and embedded
in the wasm binary; ``document.styleSheets`` exposes the rules verbatim.
Two sites that produce the same ``cssText`` for a class will render the same
way on any device — including devices where ``env()`` returns non-zero.

Usage::

    python3 css-byte-diff.py \\
        --reference https://example.com/ \\
        --target http://127.0.0.1:18702/ \\
        --target-route '#/zh/' \\
        --classes c_mobile_header c_mobile_nav_drawer c_app_main c_mobile_main \\
        --viewport 390x844 --is-mobile \\
        --out /tmp/css_diff.json

Exit codes:
    0  all requested classes emitted identical ``cssText`` on both sites
    1  at least one class differs (diff written to ``--out``)
    2  script error (bad args, navigation failure, etc.)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

DEFAULT_CHROME = "/root/LTPP-MINIMAX/chrome-linux/chrome"
CHARS_BEFORE_AFTER = 30


def collect_css(page, url: str, classes: list[str]) -> dict[str, list[str]]:
    """Navigate to ``url`` and return ``{class_name: [cssText, ...]}`` for every
    class that has at least one rule. Only rules whose ``selectorText``
    equals exactly ``.{class_name}`` are captured — rules with modifier
    classes (``c_mobile_header.fixed``) or pseudo-classes are skipped
    intentionally, since they describe behavioural variants rather than the
    baseline definition.
    """
    page.goto(url, wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(1500)  # let wasm inject CSS
    js = """
    (classes) => {
        const out = {};
        for (const c of classes) out[c] = [];
        for (const sheet of document.styleSheets) {
            let rules;
            try { rules = sheet.cssRules || []; } catch (_) { continue; }
            for (const rule of rules) {
                const sel = rule.selectorText || '';
                for (const c of classes) {
                    if (sel === '.' + c) out[c].push(rule.cssText);
                }
            }
        }
        return out;
    }
    """
    return page.evaluate(js, classes)


def diff_pair(ref: list[str], tgt: list[str]) -> dict[str, Any]:
    """Compare two lists of cssText. ``ref`` and ``tgt`` may have different
    lengths; we still try to find the first divergence position by aligning
    the first entries (typical case: each class has exactly one rule).
    """
    if ref == tgt:
        return {"identical": True}
    # First-entry alignment; surfaces the typical "missing property" case.
    r0, t0 = ref[0] if ref else "", tgt[0] if tgt else ""
    first_diff = None
    for i, (rc, tc) in enumerate(zip(r0, t0)):
        if rc != tc:
            start = max(0, i - CHARS_BEFORE_AFTER)
            first_diff = {
                "char_offset": i,
                "ref_context": r0[start : i + CHARS_BEFORE_AFTER],
                "tgt_context": t0[start : i + CHARS_BEFORE_AFTER],
            }
            break
    if first_diff is None and len(r0) != len(t0):
        first_diff = {
            "char_offset": min(len(r0), len(t0)),
            "ref_context": r0[-CHARS_BEFORE_AFTER:],
            "tgt_context": t0[-CHARS_BEFORE_AFTER:],
            "note": "same prefix, different length",
        }
    return {
        "identical": False,
        "ref_rule_count": len(ref),
        "tgt_rule_count": len(tgt),
        "first_diff": first_diff,
    }


def parse_viewport(s: str) -> tuple[int, int]:
    w, _, h = s.partition("x")
    return int(w), int(h)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", required=True, help="URL of the known-correct reference site")
    ap.add_argument("--target", required=True, help="URL of the site under verification")
    ap.add_argument("--target-route", default="", help="Hash route appended to --target (e.g. '#/zh/')")
    ap.add_argument("--classes", nargs="+", required=True, help="CSS class names to compare (e.g. c_mobile_header)")
    ap.add_argument("--viewport", default="390x844", help="WIDTHxHEIGHT (default 390x844 — iPhone 14)")
    ap.add_argument("--is-mobile", action="store_true", help="Enable mobile emulation (touch + mobile UA)")
    ap.add_argument("--chrome", default=DEFAULT_CHROME, help=f"Chrome executable path (default {DEFAULT_CHROME})")
    ap.add_argument("--out", default="", help="Write JSON report here (default: stdout)")
    ap.add_argument("--quiet", action="store_true", help="Suppress human-readable summary on stderr")
    args = ap.parse_args()

    target_url = args.target + args.target_route
    out: dict[str, Any] = {
        "reference": args.reference,
        "target": target_url,
        "viewport": args.viewport,
        "is_mobile": args.is_mobile,
        "results": {},
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=args.chrome,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
                headless=True,
            )
            w, h = parse_viewport(args.viewport)
            ctx = browser.new_context(
                viewport={"width": w, "height": h},
                is_mobile=args.is_mobile,
                has_touch=args.is_mobile,
            )
            page = ctx.new_page()

            ref_css = collect_css(page, args.reference, args.classes)
            tgt_css = collect_css(page, target_url, args.classes)

            all_identical = True
            for c in args.classes:
                pair = diff_pair(ref_css.get(c, []), tgt_css.get(c, []))
                out["results"][c] = {
                    "reference_css": ref_css.get(c, []),
                    "target_css": tgt_css.get(c, []),
                    **pair,
                }
                if not pair["identical"]:
                    all_identical = False

            browser.close()
    except Exception as e:
        print(f"css-byte-diff: ERROR {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    out["all_identical"] = all_identical

    text = json.dumps(out, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    if not args.quiet:
        if all_identical:
            print(f"css-byte-diff: OK — all {len(args.classes)} classes identical", file=sys.stderr)
        else:
            differing = [c for c, r in out["results"].items() if not r["identical"]]
            print(
                f"css-byte-diff: MISMATCH on {len(differing)}/{len(args.classes)} classes: "
                + ", ".join(differing),
                file=sys.stderr,
            )
            for c in differing:
                d = out["results"][c]["first_diff"]
                if d:
                    print(f"  {c} @ char {d['char_offset']}:", file=sys.stderr)
                    print(f"    ref: …{d['ref_context']}…", file=sys.stderr)
                    print(f"    tgt: …{d['tgt_context']}…", file=sys.stderr)

    print(text)
    return 0 if all_identical else 1


if __name__ == "__main__":
    sys.exit(main())
