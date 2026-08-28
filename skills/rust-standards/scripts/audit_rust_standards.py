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
    ('non-keyword prod files', '''
cd {target}
git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -vE "/tests/|/lib\\.rs$|/raw_html\\.rs$" | while read f; do
  [ -f "$f" ] || continue
  bn=$(basename "$f")
  case "$bn" in
    const.rs|static.rs|fn.rs|enum.rs|struct.rs|trait.rs|impl.rs|type.rs|mod.rs) ;;
    *) echo "NON-KEYWORD: $f" ;;
  esac
done
'''),
    ('#[allow] in production', '''
cd {target}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "^\\+.*#\\[allow" | head -20
'''),
    ('production unwrap/expect/panic', '''
cd {target}
current_file=""
git diff origin/master HEAD -- "*.rs" 2>/dev/null | while read line; do
  if [[ "$line" == "+++ b/"* ]]; then
    current_file=$(echo "$line" | sed "s|+++ b/||")
  fi
  if echo "$line" | grep -qE "^\\+.*(panic!\\(|\\.expect\\(|\\.unwrap\\(\\))"; then
    if [[ ! "$current_file" == *"/tests/"* ]]; then
      echo "$current_file: $line"
    fi
  fi
done | head -20
'''),
    ('#[test] in production', '''
cd {target}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | grep -B5 "^\\+.*#\\[test\\]" | grep "^\\+\\+\\+ b/" | grep -v "/tests/" | head -5
'''),
    ('// comments in mod.rs', '''
cd {target}
for f in $(git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "/mod\\.rs$"); do
  [ -f "$f" ] || continue
  if grep -E "^\\s*//[^/!]" "$f" > /dev/null 2>&1; then
    echo "$f"
  fi
done
'''),
    ('mod.rs missing trailing use super::*', '''
cd {target}
for f in $(git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "/mod\\.rs$" | grep -v "core/tests/mod.rs\\|cli/tests/mod.rs"); do
  [ -f "$f" ] || continue
  last=$(grep -E "^[^[:space:]]" "$f" | tail -1)
  case "$last" in
    "use super::*;"|"pub use super::*;") ;;
    *) echo "$f: last=$last" ;;
  esac
done
'''),
    ('sub-file first line not use super::*', '''
cd {target}
git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -vE "/(mod|lib|raw_html)\\.rs$|/tests/" | while read f; do
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
    ('#[cfg(test)] in production', '''
cd {target}
git diff -U0 origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "^\\+.*#\\[(test|cfg\\(test\\)\\)" | head -20
'''),
    ('long-path use crate::xxx in sub-files', '''
cd {target}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "^\\+.*\\buse crate::" | grep -v "/tests/" | head -20
'''),
    ('inline generic bounds', '''
cd {target}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "^\\+.*fn [a-z_]+<[A-Z][a-zA-Z]+:" | grep -v "/tests/" | head -10
'''),
    ('r# on non-keyword file', '''
cd {target}
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
    ('implicit Vec::new() without type', '''
cd {target}
git diff origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "^\\+.*let [a-z_]+ = Vec::new\\(\\);" | grep -v "/tests/" | head -10
'''),
    ('#![cfg(test)] in test fn.rs', '''
cd {target}
for f in $(git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "/tests/.*/fn\\.rs$"); do
  [ -f "$f" ] || continue
  if grep -q "^#!\\[cfg(test)\\]" "$f"; then
    echo "$f"
  fi
done
'''),
    ('pure &Foo helper in fn.rs should be impl method (R1.3.1)', r'''
cd {target}
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
    BEGIN { n = split(types, arr, "\n"); for (i = 1; i <= n; i++) known[arr[i]] = 1 }
    /^\s*pub(?:\([^)]*\))?\s+(async\s+|const\s+|unsafe\s+)*fn\s+[a-zA-Z_]\w*\s*[<(]/ {
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
      while (i2 <= length(rest) && depth > 0) {
        c = substr(rest, i2, 1)
        if (c == "(") depth++
        else if (c == ")") depth--
        i2++
      }
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
      if (cur in known) {
        printf("%s:%d: %s takes &%s — should be `impl %s { fn %s(&self) ... }` in impl.rs per §1.3.1\n",
               file, NR, fn_name, cur, cur, fn_name)
      }
    }
  ' "$fn_file"
done
'''),
]


def run_check(name, shell_template, target):
    cmd = shell_template.format(target=target)
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