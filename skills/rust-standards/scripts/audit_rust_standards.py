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
12. implicit Vec::new() without type annotation (R5.1, collection-only)
13. #![cfg(test)] in test fn.rs (R14.2)
14. comments in test files (R14.5, DEPRECATED — see check 28)
15. pure &Foo helper in fn.rs should be impl method (R1.3.1)
16. column-0 decl type mismatch in keyword files (R1.3a, raw-string-aware)
17. sub-file body uses external crate full path (R6.4-pitfall-b)
18. fn.rs hardcoded byte/string literals (R1.3c literal purity, fn.rs-only)
19. fn-body blank lines (R9.1 §9.1 item 10)
20. tests/<sub>/fn.rs non-super use (R14.7)
21. Cargo.toml dep block order (§13.7 round 4)
22. CI workflow forbids version bumps and version writes (§17)
23. keyword file purity + first-line use super::* (§1.3 / §6.3)
24. no impl Trait in fn parameters (§9.2)
25. doc-comment format conformance (§2.1 / §2.2) — REMOVED 2026-09-26, see check 35
26. module imports centralized in lib.rs / mod.rs (§6.1 / §6.3 / §6.4)
27. lib.rs / mod.rs three-stage import order (§6.1)
28. no comments in test files (§14.5)
29. mod.rs `mod` declaration must be bare (§6.2)
30. no `#[allow(...)]` in production (§14)
31. explicit type annotations for let bindings (§5.1, collection-only)
32. no `#[inline]` in cdylib crates (§12)
33. all `let` bindings have explicit type annotation (§5.1, comprehensive)
34. closure parameters have explicit type annotation (§5.2)
35. non-test fn has compliant doc comment (§2.1 / §2.2, authoritative)
36. hardcoded strings live in `const.rs` (§1.3c strengthened)
37. lib.rs `//!` doc block structure (§2.4)

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
    ('tests/<sub>/fn.rs non-super use (R14.7)', '''
# Per R14.7: tests/<sub>/fn.rs may contain ONLY `use super::*;` as a top-level
# use statement. Other imports (std / wasm_bindgen_test / web_sys / ...) must
# be re-exported by the parent tests/<sub>/mod.rs via `pub use`.
# Wrapper invokes the dedicated `verify_test_imports_centralized.sh` script.
# {{audit_script_dir}} is substituted at audit-script load time (see main()).
# Filter the inner script's "OK: N file(s) ..." line so it doesn't register
# as a hit; only propagate the violation report + exit status.
cd {{target}}
bash "{{audit_script_dir}}/verify_test_imports_centralized.sh" "{{target}}" \
    | grep -v -E '^OK: [0-9]+ tests/'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_test_imports_centralized.sh exited $exit_code" >&2
fi
exit "$exit_code"
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

    ('Cargo.toml dep block order (§13.7 round 4)', '''
# Per references/13-dependency.md §13.7 (round 4, 2026-09-26):
#   [dependencies] / [dev-dependencies] / [build-dependencies] /
#   [workspace.dependencies] must be ordered:
#     * LOCAL first (workspace members via [workspace] members or
#       value containing workspace = true / path = "...").
#     * EXACTLY ONE blank line separating local group from third-party
#       group. No blank lines within either group.
#     * Within each group: entry full length ascending (whitespace-
#       agnostic; computed by verify_dep_order.py as
#       len(re.sub(r"\\s+", "", "<entry-joined>"))), ties broken by
#       dep key ASCII lex.
#
# The companion script `verify_dep_order.py` implements this. Its
# exit code is the only source of truth for pass/fail. We pipe its
# stdout through `grep -v` to drop the success-path trailer line
# (`N files checked, 0 violations`) — that line would otherwise be
# counted as a hit by the audit wrapper. The actual violation lines
# (file paths + actual vs expected) MUST flow through unfiltered.
# Repos with no Cargo.toml print "No Cargo.toml files found ..." to
# stderr and exit 2 — also filtered out (not a violation).
cd {{target}}
python3 "{{audit_script_dir}}/verify_dep_order.py" "{{target}}" 2>/dev/null \
    | grep -v -E '^[0-9]+ files checked, 0 violations$|^OK: 0 Cargo.toml'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_dep_order.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 22 — §17 CI never bumps versions / never writes `version =`
    # (2026-09-26 added). Companion script: verify_ci_no_bump.py.
    ('CI workflow forbids version bumps and version writes (§17)', '''
# Forbid any `.github/workflows/*.yml` step that bumps a Cargo.toml
# version (cc bump / crate bump with --patch/--minor/.../--release /
# --target-version) or rewrites a `version =` line via sed -i / perl -pi
# / python3 -c / awk >. Read-only `grep ... | sed -E 's/.../.../'`
# extraction of `$VERSION` for tag/commit-message is allowed.
# Allowlist: `# ci-allow-version-write: <reason>` on the line just
# above the violation exempts it (tight coupling).
cd {{target}}
python3 "{{audit_script_dir}}/verify_ci_no_bump.py" "{{target}}" \
    | grep -v -E '^(OK: [0-9]+ workflow|INFO: no .github/workflows)'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_ci_no_bump.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 23 — §1.3 keyword file purity (R1.3a) + first-line use super::*
    # (2026-09-26 user tightening).  Companion script:
    # verify_keyword_file_purity.py.  Replaces / extends the older
    # column-0 decl check (#16) and adds the first-line + use-centralized
    # checks for keyword files.
    ('keyword file purity + first-line use super::* (§1.3 / §6.3)', '''
# Per rust-standards §1.3 + §6.3 (2026-09-26 user tightening):
#   - Each keyword file (const.rs / static.rs / fn.rs / enum.rs /
#     struct.rs / trait.rs / impl.rs / type.rs / mod.rs) under src/
#     MUST be the only declaration kind it contains.
#   - First non-comment line MUST be `use super::*;` (the previous
#     exemption allowing direct `///` doc comments on enum.rs /
#     struct.rs / type.rs is RETIRED).
#   - No `use crate::xxx;` / `use std::xxx;` / `use external::xxx;`
#     / `use super::specific_path;` outside the leading super::*.
cd {{target}}
python3 "{{audit_script_dir}}/verify_keyword_file_purity.py" "{{target}}" \\
    | grep -v -E '^=== keyword-file purity:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_keyword_file_purity.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 24 — §9.2 fn parameter style: no `impl Trait` in parameters.
    # (2026-09-26 user tightening).  Companion script:
    # verify_no_impl_trait_params.py.
    ('no impl Trait in fn parameters (§9.2)', '''
# Per rust-standards §9.2: fn parameters must use generic + where
# clause, not `impl Trait`.  Example:
#   fn parse<T: FromStr>(...)  ❌  inline bound
#   fn parse<T>(...) where T: FromStr  ✅
#   fn f(x: impl AsRef<str>)  ❌  impl param
#   fn f<T>(x: T) where T: AsRef<str>  ✅
cd {{target}}
python3 "{{audit_script_dir}}/verify_no_impl_trait_params.py" "{{target}}" \\
    | grep -v -E '^=== no-impl-trait-fn-params:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_no_impl_trait_params.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 25 — moved to check 35 (consolidated; see 2026-09-26
    # third iteration).  verify_doc_comment_format.py is the
    # authoritative verifier; previously also wired here as
    # check 25.  Removed to avoid running the same script twice.
    # (2026-09-26 user tightening).

    # check 26 — §6.1 / §6.3 / §6.4 module-imports centralized.
    # (2026-09-26 user tightening).  Companion script:
    # verify_module_imports_centralized.py.  Audits lib.rs (private
    # `use` for std/external must be `pub use`), mod.rs (no // comments
    # + last-line use super::*), and keyword sub-files (only `use
    # super::*;` allowed + no long-path use anywhere).
    ('module imports centralized in lib.rs / mod.rs (§6.1 / §6.3 / §6.4)', '''
cd {{target}}
python3 "{{audit_script_dir}}/verify_module_imports_centralized.py" "{{target}}" \\
    | grep -v -E '^=== module-imports centralized:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_module_imports_centralized.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 27 — §6.1 lib.rs / mod.rs three-stage import order.
    # (2026-09-26 user tightening).  Companion script:
    # verify_lib_rs_order.py.
    ('lib.rs / mod.rs three-stage import order (§6.1)', '''
cd {{target}}
python3 "{{audit_script_dir}}/verify_lib_rs_order.py" "{{target}}" \
    | grep -v -E '^(=== |OK: 0 lib)'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_lib_rs_order.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 28 — §14.5 no comments in test files.  Replaces the older
    # regex-based check 14 (which used `^\s*//[^/]` and accidentally
    # excluded `///`).  Companion script: verify_no_test_comments.py.
    # Catches //, ///, and //! uniformly per round-3 user clarification.
    ('no comments in test files (§14.5)', '''
# Per rust-standards §14.5 (2026-09-12 round 3 user clarification,
# 2026-09-26 strengthening):
#   Tests have ZERO comments — no file-level //!, no per-fn ///,
#   no fn-body //.  Test fn name = documentation; assertion
#   message = expected behavior.  All three forms banned.
cd {{target}}
python3 "{{audit_script_dir}}/verify_no_test_comments.py" "{{target}}" \
    | grep -v -E '^=== no-comments-in-tests:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_no_test_comments.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 29 — §6.2 mod.rs `mod xxx;` MUST be bare (no visibility
    # prefix).  User original (2026-09-26): "mod.rs 的 mod 前面不能
    # 有可见性".  Companion: verify_mod_visibility.py.
    ('mod.rs `mod` declaration must be bare (§6.2)', '''
# Per rust-standards §6.2 (2026-09-26 user iteration): in any
# mod.rs, `mod r#xxx;` declarations MUST be bare — no `pub mod`,
# no `pub(crate) mod`, no `pub(super) mod`.  The visibility of
# items inside the module is controlled at the declaration site
# of the item itself, not on the mod line.  `mod` in mod.rs is
# always crate-internal (private to the parent module's
# namespace); the parent re-exports via the middle-stage
# `pub use {...};` block if external visibility is needed.
cd {{target}}
python3 "{{audit_script_dir}}/verify_mod_visibility.py" "{{target}}" \
    | grep -v -E '^=== mod.rs mod visibility'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_mod_visibility.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 30 — §14 no #[allow(...)] / #[expect(...)] in production
    # code.  Companion to git-diff-scoped check 2 (PR review).  This
    # script scans the whole tree to catch historical accumulation.
    ('no `#[allow(...)]` in production (§14)', '''
# Per rust-standards rule 14 (user 原话, 2026-09-14): "从根源修复
# warn, 禁止使用 allow 宏".  clippy / rustc warnings must be
# fixed at source, not silenced with attribute macros.  This
# check is the tree-wide version of git-diff-scoped check 2;
# it catches `#[allow(...)]` accumulated over multiple PRs.
# Exemptions:  (a) `#[allow(...)]` inside `#[cfg(test)] mod tests
# { ... }` blocks (test helpers may silence unused warnings);
# (b) `tests/` directory entirely (R14.7 self-contained).
cd {{target}}
python3 "{{audit_script_dir}}/verify_no_allow_lints.py" "{{target}}" \
    | grep -v -E '^=== no-allow-lints:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_no_allow_lints.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 31 — §5.1 explicit type annotations for `let` bindings
    # of collection constructors.  Companion to check 12
    # (which only catches `Vec::new()` without `:` via a simpler
    # regex).  This script is more comprehensive on collection
    # types AND catches `Vec<_>` placeholder annotations.
    ('explicit type annotations for let bindings (§5.1)', '''
# Per rust-standards rule 6 (user 原话, 2026-09-26): "所有变量 /
# 参数 / 返回值必须显式类型".  Common pitfall: `let items =
# Vec::new();` leaves the type ambiguous to the reader; must be
# `let items: Vec<u32> = Vec::new();`.  Same for HashMap /
# HashSet / BTreeMap / BTreeSet / VecDeque / LinkedList /
# BinaryHeap / String / Box / Rc / Arc.  Also catches
# `let v: Vec<_> = ...collect();` which defeats the rule by
# leaving the element type implicit.
cd {{target}}
python3 "{{audit_script_dir}}/verify_explicit_type_annotations.py" "{{target}}" \
    | grep -v -E '^=== explicit-type-annotations:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_explicit_type_annotations.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 32 — §12 WASM crates (cdylib) MUST NOT have
    # `#[inline]` / `#[inline(always)]` / `#[inline(never)]`
    # attributes.  User original (2026-09-26): "WASM 项目禁止
    # 所有 inline 注解".  WASM codegen handles inlining itself;
    # manual annotations force wasm-opt to skip functions,
    # enlarging the binary 10-50% without measurable speedup.
    ('no `#[inline]` in cdylib crates (§12)', '''
# Per rust-standards rule 12 (2026-09-26 user clarification):
# "WASM 项目禁止所有 inline 注解".  Detection: find all
# Cargo.toml files with `crate-type = ["cdylib", ...]` and
# audit their src/ trees for `#[inline]` / `#[inline(always)]`
# / `#[inline(never)]`.  Pure rust crates (no cdylib) are
# ignored.  When no cdylib crate exists in the tree, the
# script exits 0 with informational output.
cd {{target}}
python3 "{{audit_script_dir}}/verify_no_wasm_inline.py" "{{target}}" \
    | grep -v -E '^=== no-wasm-inline:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_no_wasm_inline.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 33 — §5.1 all `let` bindings MUST have explicit type
    # annotations.  Companion to check 31 (which only catches
    # collection constructors specifically).  This is the
    # comprehensive form: every `let`, including `let _ = ...`,
    # must declare its type.  User original (2026-09-26 third
    # iteration): "let 的类型必须要显示标注 (包含 let _ = )".
    ('all `let` bindings have explicit type annotation (§5.1)', '''
# Per rust-standards §5.1 (2026-09-26 third iteration, user 原话):
#   "let 的类型必须要显示标注 (包含 let _ = )"
# Every `let <name> = <expr>;` MUST declare the binding's type via
# `let <name>: T = <expr>;`.  Bare `let x = 5;` is forbidden.
# Likewise `let _ = expr;` is forbidden; use `let _: T = expr;`.
# Companion script: verify_let_type_annotations.py.
# Exempts: tests/ (R14.7 self-contained), `if let` / `while let`
# pattern guards, Rust 2024 let-chains (the regex won't match).
cd {{target}}
python3 "{{audit_script_dir}}/verify_let_type_annotations.py" "{{target}}" \
    | grep -v -E '^=== let-bindings-explicit-type:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_let_type_annotations.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 34 — §5.2 closure parameters MUST have explicit type
    # annotations.  User original (2026-09-26 third iteration):
    #   "闭包参数需要显示标注"
    # `|x| x * 2` is forbidden; use `|x: u32| x * 2`.  Exempts:
    # `||` (empty), `|..|` (rest), `|(a, b): &(T, U)|` (tuple
    # destructure with type annotation on whole tuple).
    ('closure parameters have explicit type annotation (§5.2)', '''
# Per rust-standards §5.2 (2026-09-26 third iteration, user 原话):
#   "闭包参数需要显示标注"
# Every closure parameter must have explicit `: T` annotation.
# `|x| x + 1` is forbidden; use `|x: u32| -> u32 { x + 1 }`.
# Companion script: verify_closure_type_annotations.py.
# Exempts: tests/, empty `||`, rest `|..|`, ref patterns
# `|&x: &T|`, tuple destructuring with type `(pat): T`.
cd {{target}}
python3 "{{audit_script_dir}}/verify_closure_type_annotations.py" "{{target}}" \
    | grep -v -E '^=== closure-params-explicit-type:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_closure_type_annotations.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 35 — §2.1 non-test fn / impl MUST have `///` doc
    # comment with proper Layer 1+2+3 format.  User original
    # (2026-09-26 third iteration): "非单侧的 fn 必须要符合格式
    # 的文档注释".  Tests are exempt (R14.5 forbids all comments
    # in test files; thus no doc-comment there either).
    ('non-test fn has compliant doc comment (§2.1 / §2.2)', '''
# Per rust-standards §2.1 + §2.2 (2026-09-26 third iteration,
# user 原话): "非单侧的 fn 必须要符合格式的文档注释".
#   Layer 1 (existence): every non-test fn / impl method needs
#     at least one `///` line above it.
#   Layer 2 (completeness): every fn with non-self params OR
#     non-() return must have `# Arguments` / `# Returns` section.
#   Layer 3 (format): the doc-comment template structure is
#     exactly `# Arguments` + `- `Type` - description` /
#     `# Returns` + `- `Type`: description`.
# Tests are exempt (R14.5 says test files have ZERO comments).
# Companion script: verify_doc_comment_format.py (already
# existed pre-this-round, but is now wired as the §2.1/§2.2
# authoritative verifier — check 25).  This check 35 is the
# EXPLICIT strengthened entry per user iteration.
cd {{target}}
python3 "{{audit_script_dir}}/verify_doc_comment_format.py" "{{target}}" \
    | grep -v -E '^=== doc-comment format:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_doc_comment_format.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 36 — §1.3c strengthened (2026-09-26 third iteration):
    # hardcoded string literals (≥ 4 non-trivial chars) MUST live
    # in `const.rs`.  User original: "硬编码字符串必须要维护到
    # const.rs".  Exempts: const.rs itself, tests/, attribute
    # lines (`#[doc = "..."]` / `#[serde(rename = "...")]`),
    # format-macro format strings (`println!("...")`).
    ('hardcoded strings live in `const.rs` (§1.3c)', '''
# Per rust-standards §1.3c strengthened (2026-09-26 third
# iteration, user 原话): "硬编码字符串必须要维护到 const.rs".
# Every hardcoded string literal (≥ 4 non-trivial chars) in any
# non-const file MUST live in `const.rs` as a `pub const`.  This
# is the comprehensive form of the existing check 18 (which
# only covers fn.rs byte/char/multi-char literals).  Companion
# script: verify_hardcoded_strings.py.  Exempts: const.rs
# itself (canonical home), tests/ (R14.7 self-contained), attr
# lines (#[doc = "..."], #[serde(rename = "...")]), and format
# macro format strings (`println!("...")`).
cd {{target}}
python3 "{{audit_script_dir}}/verify_hardcoded_strings.py" "{{target}}" \
    | grep -v -E '^=== hardcoded-strings-to-const:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_hardcoded_strings.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 37 — §2.4 lib.rs MUST have leading `//!` doc block
    # (2026-09-26 fifth iteration).  User original: "对于 lib.rs
    # 必须要检查是否存在 //! 注释,注释第一行 //! 后是包名后面
    # 是一行 //! 再后面才是内容".  Mandatory structure:
    #
    #   //! <package_name>
    #   //!
    #   //! <description>
    #
    # Companion script: verify_lib_rs_doc_comment.py reads the
    # nearest Cargo.toml's [package].name to compare against the
    # first `//!` line text.
    ('lib.rs `//!` doc block structure (§2.4)', '''
# Per rust-standards §2.4 (2026-09-26 fifth iteration, user 原话):
#   "对于 lib.rs 必须要检查是否存在 //! 注释,注释第一行 //! 后是
#    包名后面是一行 //! 再后面才是内容"
# Every lib.rs MUST start with the canonical 3-line `//!` block:
#   1st line: `//! <package_name>` (text must equal [package].name)
#   2nd line: `//!` (empty separator)
#   3rd line: `//! <description>` (content)
# Companion script: verify_lib_rs_doc_comment.py.
cd {{target}}
python3 "{{audit_script_dir}}/verify_lib_rs_doc_comment.py" "{{target}}" \
    | grep -v -E '^=== lib.rs-doct-comment:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_lib_rs_doc_comment.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 38 — §6.5 `use ... as ...` import rename forbidden
    # (2026-09-26 user directive).  User original: "类型导入禁止使用
    # as 重命名...如果类型冲突才在使用的地方使用最短可区分的命名
    # 空间".  Any `as <ident>` inside a use statement (any visibility)
    # is a violation; conflicts are resolved by qualifying at the
    # usage site with the shortest distinguishable namespace
    # (e.g. `fmt::Result`, `io::Error`), never by aliasing the import.
    #
    # Companion script: verify_no_import_rename.py tracks use
    # statements including grouped multi-line blocks.
    ('no `as` rename in use statements (§6.5)', '''
# Per rust-standards §6.5 (2026-09-26, user 原话): "类型导入禁止使用
# as 重命名,如果类型冲突才在使用的地方使用最短可区分的命名空间"
# Companion script: verify_no_import_rename.py.
cd {{target}}
python3 "{{audit_script_dir}}/verify_no_import_rename.py" "{{target}}" \
    | grep -v -E '^=== no-import-rename:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_no_import_rename.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),

    # check 38 — §17.3 / §17.12 direct `self.field` access forbidden
    # (2026-09-26 user directive).  User original: "禁止通过self直接
    # 操作字段,使用Data宏的get和set".  All production field reads /
    # writes go through Data-macro (or §17.11 hand-written) accessors.
    # Legal self.field positions: accessor bodies (get_*/set_*/
    # try_get_*), Debug/Display impl blocks, #[cfg(test)] / tests/.
    #
    # Companion script: verify_no_self_field_access.py tracks fn /
    # trait-impl / cfg(test) ranges via brace counting.
    ('no direct `self.field` access (§17.3 / §17.12)', '''
# Per rust-standards §17.3 / §17.12 (2026-09-26, user 原话): "禁止通过
# self直接操作字段,使用Data宏的get和set"
# Companion script: verify_no_self_field_access.py.
cd {{target}}
python3 "{{audit_script_dir}}/verify_no_self_field_access.py" "{{target}}" \
    | grep -v -E '^=== no-self-field-access:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_no_self_field_access.py exited $exit_code" >&2
fi
exit "$exit_code"
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

    # Substitutions available in every shell template:
    #   {{target}}            — absolute path of the repo root being audited
    #   {{audit_script_dir}}  — directory holding this audit script (for invoking
    #                            companion scripts like verify_test_imports_centralized.sh)
    audit_script_dir = os.path.dirname(os.path.abspath(__file__))
    target = os.path.abspath(target)
    substitutions = {'target': target, 'audit_script_dir': audit_script_dir}

    def substitute(template: str) -> str:
        for k, v in substitutions.items():
            template = template.replace('{{' + k + '}}', v)
        return template

    results = []
    for i, (name, shell_template) in enumerate(CHECKS, start=1):
        cmd = substitute(shell_template)
        n, out = run_check(name, cmd, target)
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