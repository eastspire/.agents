#!/usr/bin/env python3
"""
Comprehensive rust-standards audit script for PR review.

Run from a Rust repo working directory with the diff already applied:
  python3 scripts/audit_rust_standards.py [target_dir]

Default target = current working directory.

Categories checked (each is a single pass; output is grouped by category
so false positives are easy to filter out — see references/audit-pitfalls.md
for the master-pattern exceptions the script cannot statically detect):

 1. non-keyword production files (R1.3)
 2. #[allow] in production (R11.x — explicitly forbidden by user)
 3. production unwrap/expect/panic (R11.4)
 4. #[test] in production (R14.5)
 5. // comments in mod.rs (R2.5)
 6. mod.rs missing trailing use super::* (R6.2)
 7. sub-file first line not use super::* (R6.3)
 8. #[cfg(test)] in production (R14.5)
 9. long-path use crate::xxx in sub-files (R6.3)
10. inline generic bounds (R9.2)
11. r# on non-keyword file (R1.4)
12. implicit Vec::new() without type annotation (R5.1)
13. #![cfg(test)] in test fn.rs (R14.2)

Each check prints either "PASS: N. <category>" or "FAIL: N. <category>: <count>
hits" followed by up to 5 sample lines.

Known false positives — see references/audit-pitfalls.md for the complete
list. The script tries to filter the obvious ones (e.g. tests/ is exempt
for several checks) but cannot statically detect every master-pattern
exception (e.g. master accepts `mod r#signal;` inside `core/src/tests/mod.rs`
per R14.1a; master accepts direct `///` doc comments on `enum.rs` without
`use super::*;` when the enum doesn't reference parent-module symbols).
"""
import subprocess
import sys
import os

DEFAULT_TARGET = '.'

CHECKS = [
    ('non-keyword prod files', '''cd {{target}}
git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -vE "/tests/|/lib\\.rs$|/raw_html\\.rs$|/main\\.rs$|/bin/[^/]+\\.rs$|(^|/)build\\.rs$" | while read f; do
  [ -f "$f" ] || continue
  bn=$(basename "$f")
  case "$bn" in
    const.rs|static.rs|fn.rs|enum.rs|struct.rs|trait.rs|impl.rs|type.rs|mod.rs) ;;
    *) echo "NON-KEYWORD: $f" ;;
  esac
done
'''),
    ('#[allow] in production', '''cd {{target}}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "^\\+.*#\\[allow" | head -20
'''),
        ('production unwrap/expect/panic', '''cd {{target}}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | while read line; do
  if [[ "$line" == "+++ b/"* ]]; then
    current_file=$(echo "$line" | sed "s|+++ b/||")
  fi
  if echo "$line" | grep -qE "^\+.*(panic!\(|\.expect\(|\.unwrap\(\))"; then
    if [[ ! "$current_file" == *"/tests/"* ]]; then
      # Per audit-pitfalls #41: `try_X().unwrap()` in `get_X` wrappers
      # is an upstream idiom (panic-on-missing contract is part of the
      # wrapper's documented API). Exempt this specific call pattern.
      if echo "$line" | grep -qE "(try_|[Ss]elf::try_)[a-z0-9_]+\(.*\)\.unwrap\(\)|(try_|[Ss]elf::try_)[a-z0-9_]+\(.*\)\.await\.unwrap\(\)|Regex::new\(.*\)\.expect\("; then
        continue
      fi
      # Per audit-pitfalls #42 (forthcoming): proc-macro crates
      # conventionally panic/expect in macro internals to surface user
      # errors via compiler diagnostics. Exempt macros/ subtrees.
      if [[ "$current_file" == *"macros/"* ]]; then
        continue
      fi
      echo "$current_file: $line"
    fi
  fi
done | head -20
'''),
    ('#[test] in production', '''cd {{target}}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | grep -B5 "^\\+.*#\\[test\\]" | grep "^\\+\\+\\+ b/" | grep -v "/tests/" | head -5
'''),
    ('// comments in mod.rs', '''cd {{target}}
for f in $(git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "/mod\\.rs$"); do
  [ -f "$f" ] || continue
  if grep -E "^\\s*//[^/!]" "$f" > /dev/null 2>&1; then
    echo "$f"
  fi
done
'''),
    ('mod.rs missing trailing use super::*', '''cd {{target}}
    for f in $(git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "/mod\\.rs$" | grep -v "core/tests/mod.rs\\|cli/tests/mod.rs\\|engine/tests/mod.rs\\|ui/tests/mod.rs\\|type/tests/mod.rs"); do
      [ -f "$f" ] || continue
      last=$(grep -E "^[^[:space:]]" "$f" | tail -1)
      case "$last" in
        "use super::*;"|"pub use super::*;") ;;
        *)
          # Per audit-pitfalls #40: a mod.rs's `use super::*;` is legitimately
          # unused (and may be omitted) when none of its sub-files use the
          # `use super::*;` chain to reach parent symbols. This is the
          # leaf-mod exemption matching #21's leaf-sub-file exemption.
          dir=$(dirname "$f")
          has_parent_use=0
          for sf in "$dir"/*.rs; do
            [ -f "$sf" ] || continue
            sbn=$(basename "$sf")
            [ "$sbn" = "mod.rs" ] && continue
            if grep -qE "^use super::\\*;" "$sf" 2>/dev/null; then
              has_parent_use=1
              break
            fi
          done
          if [ "$has_parent_use" -eq 0 ]; then
            continue
          fi
          echo "$f: last=$last"
          ;;
      esac
    done
    '''),
    ('sub-file first line not use super::*', '''cd {{target}}
git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -vE "/(mod|lib|raw_html|main)\\.rs$|/tests/|(^|/)build\\.rs$|/bin/[^/]+\\.rs$" | while read f; do
  [ -f "$f" ] || continue
  # Per audit-pitfalls #5 / #5a, files dedicated to a single keyword
  # (`const.rs` / `static.rs` / `fn.rs` / `enum.rs` / `struct.rs`
  # / `trait.rs` / `impl.rs` / `type.rs`) are allowed to open with
  # a `///` doc comment when they do not need any parent-module
  # symbol. The audit script now matches by the file's *basename*
  # so that every keyword-only sub-file is exempt from the
  # `use super::*;` requirement, matching what master accepts.
  bn=$(basename "$f")
  case "$bn" in
    const.rs|static.rs|fn.rs|enum.rs|struct.rs|trait.rs|impl.rs|type.rs) continue ;;
  esac
  first=$(grep -nE "^[^[:space:]/]" "$f" 2>/dev/null | head -1 | cut -d: -f1)
  if [ -z "$first" ]; then continue; fi
  line=$(sed -n "${{first}}p" "$f")
  if [ "$line" != "use super::*;" ]; then
    echo "$f:$first: $line"
  fi
done
'''),
    ('#[cfg(test)] in production', '''cd {{target}}
git diff -U0 origin/master HEAD -- "*.rs" 2>/dev/null | grep -F "#[cfg(test)]" | grep -v "^[+][+][+] b/" | grep "^[+]" | grep -v "^\\+[/!]" | grep -v "^\\+\\s*\\*\\s*#\\[cfg" | head -20
'''),
    ('long-path use crate::xxx in sub-files', '''cd {{target}}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "^\\+.*\\buse crate::" | grep -v "/tests/" | head -20
'''),
    ('inline generic bounds', '''cd {{target}}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "^\\+.*fn [a-z_]+<[A-Z][a-zA-Z]+:" | grep -v "/tests/" | head -10
'''),
    ('r# on non-keyword file', '''cd {{target}}
git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "/(mod)\\.rs$" | while read f; do
  [ -f "$f" ] || continue
  if [[ "$f" == *"/tests/"* ]]; then continue; fi
  grep -oE "mod r#[a-z_]+;" "$f" 2>/dev/null | while read line; do
    name=$(echo "$line" | sed -E "s/mod r#([a-z_]+);/\\1/")
    # Per audit-pitfalls #1 the `r#` prefix is required for every
    # Rust keyword, including the four keywords that were added
    # after the original nine (RFC 2018 added `async` / `await` /
    # `try`; RFC 3324-era work brought `dyn`). Master accepts
    # `mod r#async;` for example-page modules whose path collides
    # with these reserved words.
    case "$name" in
      const|static|fn|enum|struct|trait|impl|type|mod|async|await|try|dyn) ;;
      *) echo "$f: r#$name" ;;
    esac
  done
done
'''),
    ('implicit Vec::new() without type', '''cd {{target}}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "^\\+.*let [a-z_]+ = Vec::new\\(\\);" | grep -v "/tests/" | head -10
'''),
    ('#![cfg(test)] in test fn.rs', '''cd {{target}}
for f in $(git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "/tests/.*/fn\\.rs$"); do
  [ -f "$f" ] || continue
  if grep -q "^#!\\[cfg(test)\\]" "$f"; then
    echo "$f"
  fi
done
'''),
    ('comments in test files (R14.5)', '''cd {{target}}
# Per rust-standards §14.5 (2026-09-12 user clarification):
# tests/ files MUST have zero comments. The test fn name is the
# documentation; assertion messages express the expected behavior.
# This applies to:
#   - file-level //! headers
#   - per-fn /// doc comments
#   - fn-body inline // comments
# Blank lines between #[test] fns are fine; only //-prefixed lines fail.
for f in $(git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "/tests/.*\\.rs$"); do
  [ -f "$f" ] || continue
  hits=$(grep -nE "^\s*//[^/]" "$f" 2>/dev/null)
  if [ -n "$hits" ]; then
    echo "FAIL: $f has comments:"
    echo "$hits" | head -3
  fi
done
'''),
    ('pure &Foo helper in fn.rs should be impl method (R1.3.1)', '''cd {{target}}
# For every fn.rs file touched by the PR, find pub fn / pub(crate) fn declarations
# whose first parameter is `&Foo` / `&mut Foo` where Foo is a type declared in the
# same directory's struct.rs / enum.rs. Those should be impl methods, not free fns
# (per references/01-directory-structure.md §1.3.1 rule 1).
for fn_file in $(git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -E '/fn\.rs$'); do
  [ -f "$fn_file" ] || continue
  dir=$(dirname "$fn_file")
  # Collect the type names declared in the same directory's struct.rs / enum.rs
  types_in_dir=$( (cat "$dir/struct.rs" "$dir/enum.rs" 2>/dev/null) \
                  | grep -oE '^\s*pub(?:\([^)]*\))?\s+(?:struct|enum)\s+[A-Z]\w*' \
                  | grep -oE '[A-Z]\w*$' | sort -u )
  [ -z "$types_in_dir" ] && continue
  # For each declared fn in fn.rs, find ones whose first param is &Type or &mut Type
  # for one of those types. Print "<file>:<line>: <fn> takes &(mut )<Type>".
  awk -v types="$types_in_dir" -v file="$fn_file" '
    BEGIN {{ n = split(types, arr, "\n"); for (i = 1; i <= n; i++) known[arr[i]] = 1 }}
    /^\s*pub(?:\([^)]*\))?\s+(async\s+|const\s+|unsafe\s+)*fn\s+[a-zA-Z_]\w*\s*[<(]/ {{
      line = $0
      # Extract fn name
      m = match(line, /fn ([a-zA-Z_][a-zA-Z0-9_]*)/, arr); if (!m) next
      fn_name = arr[1]
      # Skip #[component] entries (component macros require free fn shape)
      if (line ~ /#\[component\]/ || line ~ /component\]/) next
      # Find first parameter — look for &Type or &mut Type after the opening paren
      rest = substr(line, index(line, "("))
      # Strip generics up to first ( ... ) including <T, U>
      depth = 0; in_parens = 0
      start = index(rest, "(")
      i2 = start + 1; depth = 1
      while (i2 <= length(rest) && depth > 0) {{
        c = substr(rest, i2, 1)
        if (c == "(") depth++
        else if (c == ")") depth--
        i2++
      }}
      params = substr(rest, start + 1, i2 - start - 2)
      # First parameter token (before comma)
      p1 = params
      sub(/,.*/, "", p1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", p1)
      # Strip leading & or &mut
      cur = p1
      sub(/^&mut[[:space:]]+/, "", cur)
      sub(/^&[[:space:]]+/, "", cur)
      # cur is the type token (may include generics — strip <...>)
      sub(/<.*$/, "", cur)
      gsub(/[[:space:]]/, "", cur)
      if (cur in known) {{
        printf("%s:%d: %s takes &%s — should be `impl %s {{{{ fn %s(&self) ... }}}}` in impl.rs per §1.3.1\n",
               file, NR, fn_name, cur, cur, fn_name)
      }}
    }}
  ' "$fn_file"
done
'''),
    ('column-0 decl type mismatch in keyword files (R1.3a, raw-string-aware)', '''cd {{target}}
# For each keyword file modified by the PR, check that no column-0 decl of the
# WRONG type lives in it (R1.3a keyword file purity).
# Excludes WGSL shader code inside raw string literals (audit-pitfalls §18).
for f in $(git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -vE '/tests/' | grep -vE '/target/'); do
  [ -f "$f" ] || continue
  bn=$(basename "$f")
  case "$bn" in
    const.rs)   forbidden='^(pub |pub\(crate\) )?(fn |struct |enum |trait |impl |type )' ;;
    static.rs)  forbidden='^(pub |pub\(crate\) )?(fn |struct |enum |trait |impl |type )' ;;
    fn.rs)      forbidden='^(pub |pub\(crate\) )?(struct |enum |trait |impl |type )' ;;
    enum.rs)    forbidden='^(pub |pub\(crate\) )?(struct |fn |impl |trait |type )' ;;
    struct.rs)  forbidden='^(pub |pub\(crate\) )?(enum |fn |impl |trait |type )' ;;
    trait.rs)   forbidden='^(pub |pub\(crate\) )?(struct |enum |fn |impl |type )' ;;
    impl.rs)    forbidden='^(pub |pub\(crate\) )?(struct |enum |fn |trait |type )' ;;
    type.rs)    forbidden='^(pub |pub\(crate\) )?(struct |enum |fn |impl |trait )' ;;
    *) continue ;;
  esac
  python3 -c '
import sys, re
f, forbidden = sys.argv[1], sys.argv[2]
text = open(f).read()
lines = text.split("\n")
in_raw = False
delim = ""
for i, line in enumerate(lines, 1):
    if in_raw:
        close_marker = chr(34) + delim
        if close_marker in line:
            pos = line.find(close_marker)
            after = line[pos + len(close_marker):]
            in_raw = False
            delim = ""
            if re.match(forbidden, after):
                print("%s:%d: %s (forbidden in keyword file, after raw-string close)" % (f, i, after[:80]))
        continue
    m = re.search(r"r(#+)\"", line)
    if m:
        delim = m.group(1)
        rest = line[m.end():]
        close_marker = chr(34) + delim
        cpos = rest.find(close_marker)
        if cpos == -1:
            in_raw = True
        else:
            after = rest[cpos + len(close_marker):]
            if re.match(forbidden, after):
                print("%s:%d: %s (forbidden in keyword file, after raw-string close on same line)" % (f, i, after[:80]))
        pre = line[:m.start()]
        if re.match(forbidden, pre):
            print("%s:%d: %s (forbidden in keyword file, before raw-string)" % (f, i, pre[:80]))
        continue
    if re.match(forbidden, line):
        print("%s:%d: %s (forbidden in keyword file)" % (f, i, line[:80]))
' "$f" "$forbidden"
done
'''),

    ('sub-file body uses external crate full path (R6.4-pitfall-b)', '''cd {{target}}
# Rule 17: detect `external_crate::Symbol` calls in sub-file fn bodies.
# audit rule 9 only catches `use crate::xxx;` imports; this catches
# bare `minify_js::Session` / `tokio::fs::read` / `serde_json::from_str`
# etc. that should have been routed through `lib.rs` re-export +
# `use super::*;`. (R6.4-pitfall-b)
# Script is intentionally simple: extract every third-party dep from
# the changed file's nearest Cargo.toml [dependencies] / [dev-dependencies]
# / [build-dependencies] blocks + the root [workspace.dependencies],
# then grep each non-doc non-use line for `dep::Sym`.
python3 - <<'PY'
import re, os, subprocess, sys
root = os.getcwd()
# Find every third-party dep reachable from any changed src/ sub-file.
diff_proc = subprocess.run(["git", "diff", "--name-only", "origin/master", "HEAD", "--", "*.rs"],
                            capture_output=True, text=True, cwd=root)
files = [f for f in diff_proc.stdout.strip().split("\n") if f
         and "/src/" in f
         and not f.endswith("/mod.rs")
         and not f.endswith("/lib.rs")
         and "/tests/" not in f]
if not files:
    sys.exit(0)
added_lines = {{{{}}}}
for f in files:
    diff = subprocess.run(["git", "diff", "-U0", "origin/master", "HEAD", "--", f],
                          capture_output=True, text=True, cwd=root)
    s = set()
    for ln in diff.stdout.split("\n"):
        if ln.startswith("+") and not ln.startswith("+++"):
            s.add(ln[1:])
    added_lines[f] = s
def parse_cargo_toml(path):
    deps = set()
    in_deps = False
    if not os.path.exists(path):
        return deps
    with open(path) as fh:
        for ln in fh:
            s = ln.strip()
            if s.startswith("["):
                in_deps = s in ("[dependencies]", "[build-dependencies]", "[dev-dependencies]", "[workspace.dependencies]")
                continue
            if in_deps:
                m = re.match(r"^([a-zA-Z0-9_-]+)\s*=", ln)
                if m:
                    deps.add(m.group(1))
    return deps
ext_crates = set()
for f in files:
    cur = os.path.dirname(os.path.join(root, f))
    while cur and cur != "/":
        ct = os.path.join(cur, "Cargo.toml")
        if os.path.exists(ct):
            ext_crates |= parse_cargo_toml(ct)
            break
        cur = os.path.dirname(cur)
# root workspace.deps too
ext_crates |= parse_cargo_toml(os.path.join(root, "Cargo.toml"))
IGNORE = {{{{"std", "core", "alloc", "log",
          "euv", "euv-ui", "euv-cli", "euv-core",
          "euv-engine", "euv-macros", "euv-example", "hyperlane"}}}}
ext_crates -= IGNORE
if not ext_crates:
    sys.exit(0)
hits = 0
# Rule 17 enforces R6.3 / R6.4 literal:
# (a) no `use external_crate::...;` at the top of sub-files (R6.3 spirit)
# (b) no full-path `<ext>::Symbol` calls *when the same symbol is already
#     reachable via `use super::*;` through lib.rs re-export* (R6.4 spirit)
#
# To keep the check tractable and avoid false-positives on common path calls
# (e.g. `tokio::fs::read`), we only flag two patterns:
#   1. Top-of-file `use ext::xxx;` declarations
#   2. Full-path *type annotations* `let x: ext::Type = ...` (these should
#      use the re-exported type name from lib.rs)
# Macro calls like `log::warn!` and qualified path calls like `tokio::fs::read`
# are accepted (they're effectively `use` re-imports via the call site and
# require no lib.rs re-export, since macro/function call resolution works
# directly from the qualified path).
for f in files:
    path = os.path.join(root, f)
    if not os.path.exists(path):
        continue
    added = added_lines.get(f, set())
    for line in added:
        stripped = line.lstrip()
        # Pattern 1: `use external_crate::xxx;` at top of sub-file (R6.3)
        m = re.match(r"^use\s+([a-zA-Z0-9_-]+)::", stripped)
        if m and m.group(1) in ext_crates:
            print("%s: %s" % (f, line.rstrip()[:120]))
            hits += 1
            continue
        # Pattern 2: type annotation `let x: ext::Type = ...` (R6.4 spirit)
        m = re.search(r":\s*([a-zA-Z0-9_-]+)::", stripped)
        if m and m.group(1) in ext_crates:
            # Skip if it's a function call arg or struct field
            # (heuristic: skip lines where the :: is followed by lowercase)
            tail = stripped[m.end():]
            if not re.match(r"[A-Z]", tail):
                continue
            # Skip attribute macros (#[ext::...])
            if stripped.startswith("#"):
                continue
            print("%s: %s" % (f, line.rstrip()[:120]))
            hits += 1
sys.exit(0)
PY
'''),

('fn.rs hardcoded byte/string literals (R1.3c literal purity)', '''cd {{target}}
# Rule 18 (2026-09-14): detect byte / char / multi-char string literals
# in fn.rs / impl.rs / mod.rs that should have been extracted to const.rs.
# Catches `b"<!--"`, `b'<', etc. that appear in fn bodies / expressions.
# Excludes: doc comments, #[cfg(test)] blocks, let bindings, raw strings.
python3 - <<'PY'
import re, subprocess, sys
root = subprocess.run(
["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
diff = subprocess.run(
["git", "diff", "--name-only", "origin/master", "HEAD", "--", "*.rs"],
capture_output=True, text=True, cwd=root)
files = [f for f in diff.stdout.strip().split("\n") if f
     and not f.endswith("/mod.rs")
     and not f.endswith("/const.rs")
     and not f.endswith("/static.rs")
     and not f.endswith("/lib.rs")
     and not f.endswith("/main.rs")
     and "/tests/" not in f
     and "/target/" not in f
     and (f.endswith("/fn.rs") or f.endswith("/impl.rs"))]
hits = 0
for f in files:
try:
    text = open(f).read()
except FileNotFoundError:
    continue
lines = text.split("\n")
in_raw = False
in_test = False
in_doc = False
raw_delim = ""
in_block_doc = False
for i, line in enumerate(lines, 1):
    stripped = line.lstrip()
    # Track doc comments: /// or //!
    if stripped.startswith("///") or stripped.startswith("//!"):
        continue
    # Track /** ... */ block doc comments
    if not in_block_doc and stripped.startswith("/**"):
        in_block_doc = True
        if "*/" in line[line.index("/**") + 3:]:
            in_block_doc = False
        continue
    if in_block_doc:
        if "*/" in line:
            in_block_doc = False
        continue
    # Track raw strings
    if in_raw:
        if raw_delim in line:
            in_raw = False
            raw_delim = ""
        continue
    m = re.search(r'r(#+)"', line)
    if m:
        raw_delim = '"' + m.group(1)
        if raw_delim not in line[m.end():]:
            in_raw = True
        continue
    # Track #[cfg(test)] mod tests {{{{ ... }}}} blocks (simple brace tracking)
    if "#[cfg(test)]" in line or "#[cfg(all(test" in line or "#[test]" in line:
        in_test = True
    if in_test:
        # crude brace balance: tests blocks tend to nest but rarely deeply
        if stripped.startswith("}}") and line.count("}}") > line.count("{{"):
            in_test = False
        continue
    # Detect byte literals `b"..."` / `b'...'`
    # In fn.rs these should have been extracted to const.rs
    # Skip literal in let bindings (one-shot local)
    is_let = bool(re.match(r"^\s*(let|const|static)\s+", line))
    if is_let:
        continue
    # Match byte string / char literals as RHS in expressions
    # Heuristic: detect byte literals NOT in const/let/static declarations
    # and that have non-trivial length (>=2 chars for strings, any for bytes)
    byte_str = re.findall(r'b"([^"\n]{{{{2,}}}})"', line)
    byte_chars = re.findall(r"b'([^'\n])'", line)
    if byte_str or byte_chars:
        # Skip lines that are testing equality of import-named consts
        # (e.g. `if b == HTML_LT`) - those use const, not literal
        # We only flag if literal appears, so the const case is naturally excluded
        # Skip lines where literal appears only inside `as_bytes()` cast
        if "as_bytes()" in line and re.search(r'\.as_bytes\(\)\s*\.last\(\)', line):
            continue
        # Skip `b'\\n'` / `b'\\t'` / `b' '` / `b'\\0'` escape sequences
        # (these are pure escape, not semantic tokens)
        keep = False
        for c in byte_chars:
            if c in (" ", "\t", "\n", "\r", chr(0)):
                continue
            keep = True
        if byte_str or keep:
            print("%s:%d: %s" % (f, i, line.strip()[:120]))
            hits += 1
sys.exit(0)
PY
'''),
    ('fn-body blank lines (R9.1 §9.1 item 10)', '''
# Per audit-pitfalls #33: blank lines inside fn bodies violate §9.1 item 10.
# Detection: track brace depth, classify context (fn body vs trait/impl/test),
# count blank lines inside fn-body scope that lie within PR diff hunks.
# Only flags blank lines INSIDE the diff range, so upstream historical
# violations are not blamed on the PR.
# Base branch: prefer the merge-base between HEAD and upstream/master when
# present (Track 2 fork + PR setup). Falls back to `origin/master`.
python3 - <<'PY'
import re, subprocess, sys
root = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
upstream_remote = subprocess.run(
    ["git", "config", "--get", "remote.upstream.url"],
    capture_output=True, text=True, cwd=root)
if upstream_remote.returncode == 0 and upstream_remote.stdout.strip():
    upstream_sha_proc = subprocess.run(
        ["git", "rev-parse", "upstream/master"],
        capture_output=True, text=True, cwd=root)
    if upstream_sha_proc.returncode == 0 and upstream_sha_proc.stdout.strip():
        mb = subprocess.run(
            ["git", "merge-base", "HEAD", upstream_sha_proc.stdout.strip()],
            capture_output=True, text=True, cwd=root)
        base = mb.stdout.strip() if mb.returncode == 0 else "origin/master"
    else:
        base = "origin/master"
else:
    base = "origin/master"
diff_name = subprocess.run(
    ["git", "diff", "--name-only", base, "HEAD", "--", "*.rs"],
    capture_output=True, text=True, cwd=root)
files = [f for f in diff_name.stdout.strip().split("\\n") if f
         and "/target/" not in f
         and not f.endswith("/lib.rs")
         and not f.endswith("/build.rs")]
hits = 0
for f in files:
    # Get the diff hunks for this file. Only blank lines whose new-file
    # line number falls inside a hunk range get reported.
    diff_proc = subprocess.run(
        ["git", "diff", base, "HEAD", "-U0", "--", f],
        capture_output=True, text=True, cwd=root)
    hunk_ranges = []  # list of (start, end) inclusive new-file line numbers
    for line in diff_proc.stdout.splitlines():
        m = re.match(r'^@@\\s+-\\d+(?:,\\d+)?\\s+\\+(\\d+)(?:,(\\d+))?\\s+@@', line)
        if m:
            new_start = int(m.group(1))
            new_len = int(m.group(2)) if m.group(2) else 1
            hunk_ranges.append((new_start, new_start + new_len - 1))
    if not hunk_ranges:
        continue
    try:
        text = open(f).read()
    except FileNotFoundError:
        continue
    lines = text.split("\\n")
    stack = []  # each entry: "fn" | "test" | "other"
    in_raw = False
    raw_delim = ""
    in_block_doc = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if in_block_doc:
            if "*/" in stripped:
                in_block_doc = False
            continue
        if stripped.startswith("/**"):
            in_block_doc = True
            if "*/" in stripped[3:]:
                in_block_doc = False
            continue
        if in_raw:
            close = '"' + raw_delim
            if close in line:
                in_raw = False
            continue
        m = re.search(r'r(#+)["\\\']', line)
        if m:
            in_raw = True
            raw_delim = m.group(1)
            continue
        opens = line.count("{")
        closes = line.count("}")
        if opens > 0:
            pre = line[: line.find("{")].rstrip()
            for _ in range(opens):
                if re.search(r'\\bfn\\b|\\basync\\s+fn\\b|\\bconst\\s+fn\\b|\\bunsafe\\s+fn\\b', pre):
                    stack.append("fn")
                elif re.search(r'#\\[cfg\\s*\\(test\\)\\]|#\\[test\\]|mod\\s+tests', "\\n".join(lines[max(0,i-3):i])):
                    stack.append("test")
                else:
                    stack.append("other")
        # Only flag blank lines inside the diff hunks
        if (stripped == ""
            and stack
            and stack[-1] == "fn"
            and any(s <= i <= e for s, e in hunk_ranges)):
            print(f"{f}:{i}: blank line in fn body (in diff hunk)")
            hits += 1
        while closes > 0 and stack:
            stack.pop()
            closes -= 1
sys.exit(0 if hits == 0 else 1)
PY
'''),
]


def run_check(name, shell_template, target):
    cmd = shell_template.replace('{target}', target)
    r = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True, cwd=target)
    out = [l for l in r.stdout.strip().split('\n') if l]
    return name, out


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET
    if not os.path.isdir(target):
        print(f'error: {target} is not a directory', file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(os.path.join(target, '.git')) and not os.path.isdir(os.path.join(target, '..', '.git')):
        print(f'warning: {target} does not appear to be a git repo (git diff may be empty)')

    results = []
    for i, (name, shell_template) in enumerate(CHECKS, start=1):
        n, out = run_check(name, shell_template, target)
        if out:
            results.append((n, 'FAIL', out))
            print(f'FAIL: {i}. {n}: {len(out)} hits')
            for o in out[:5]:
                print(f'  {o}')
        else:
            results.append((n, 'PASS', []))
            print(f'PASS: {i}. {n}')

    passed = sum(1 for r in results if r[1] == 'PASS')
    print(f'\n=== SUMMARY: {passed}/{len(results)} PASS ===')
    print('See references/audit-pitfalls.md for the false-positive list')
    sys.exit(0 if passed == len(results) else 1)


if __name__ == '__main__':
    main()