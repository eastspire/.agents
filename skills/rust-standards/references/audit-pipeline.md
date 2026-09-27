# Audit pipeline workflow — verifier → fixtures → wrapper → rollout

> **Use when**: adding a new rust-standards audit check, or rolling out a
> strengthened rule (e.g. when user upgrades Layer N to Layer N+1 in an
> existing verifier).

This document codifies the workflow that emerged across check 23–38
(2026-09-26 sixth-round rollout, 2026-09-27 Layer 4 doc-comment + self.field
enforcement).  The SKILL.md mentions these steps inline under
"始终生效的工程原则", but this file is the **single reusable checklist** for
any new check or strengthening.

## When you need a new verifier

A new `scripts/verify_<rule>.py` is needed when:
- A new rule is added to rust-standards (§X.Y) and needs automated enforcement
- An existing rule is strengthened to a stricter form (e.g. doc-comment Layer 4
  signature-type match on top of Layer 1–3 existence + completeness + format)

A new verifier is **not** needed when:
- The existing verifier can be extended (Layer 4 added to the existing
  `verify_doc_comment_format.py`, not a separate script)
- The rule is a one-shot sweep PR concern — apply the existing verifier,
  don't add infrastructure

## Step-by-step rollout

The five steps below must all complete before the new check is enabled in
`audit_rust_standards.py`.  Doing them in a different order produces the
failures called out in §45–§67 of `audit-pitfalls.md`.

### 1. Write `scripts/verify_<rule>.py`

Single source of truth: exit 0 = compliant, exit 1 = violations, exit 2 = usage
error.  Output format: one violation per line on stdout, summary line
`=== <rule-name>: N violation(s) in M file(s) ===` at the end (audit wrapper
filters this via `grep -v`).

Two-script design when a fixer is also needed:
- `scripts/verify_<rule>.py` — pure read-only checker
- `scripts/fix_<rule>.py` — auto-fixer that **re-imports** the verifier's parse
  logic (do not maintain two parsers — they will diverge, see audit-pitfalls
  §45)

Pitfall: never share code between verifier and fixer except by `import` —
copy-pasting the parse function is the most common source of "the fixer
succeeded but the verifier still reports violations" bugs.

### 2. Bidirectional fixture self-test (BEFORE audit wiring)

Each new verifier must pass two fixtures:
- `<fixture>-compliant/` — exit 0, zero violations
- `<fixture>-violating/` — exit 1, exactly N violations (deterministic count)

When the rule has **≥ 3 distinct exempt categories** (e.g. self.field has 6:
hand-written accessor body, setter body, Debug impl, Display impl, cfg(test),
tests/), add a **third fixture**:
- `<fixture>-edge-cases/` — exit 1 with a small deterministic count that
  exercises every exempt path AND every non-exempt violation pattern

Why three fixtures, not two: a compliant/violating pair catches "happy path
works" + "obvious violations caught".  A rule with many exempt categories
additionally needs to prove **each exempt path is correctly excluded AND each
violation pattern is correctly caught** — both in the same fixture, with a
deterministic violation count.  The fixture header documents both the rule
semantics and the expected count.

#### Edge-case fixture template

```rust
//! <rule-name>-edge-cases
//!
//! Verifies that verify_<rule>.py enforces the §X rule precisely,
//! with these EXACT semantics:
//!
//!   - <exempt category 1>: ALLOWED
//!   - <exempt category 2>: ALLOWED
//!   - ...
//!   - <violation pattern 1>: FLAGGED
//!   - <violation pattern 2>: FLAGGED
//!
//! Expected: exactly N violations (the N flagged patterns).
```

Layout: each exempt pattern gets a single-method test, each violation
pattern gets a single-method test, all in one file.  The expected count
appears as a comment in the file header AND in the verifier's stdout summary.

Verified working examples in
`~/.hermes/cache/scratch/verifier-fixtures/`:
- `self-edge-cases/` (6 exempt + 2 violation = 2 violations expected)
- `doc-layer4-violating/` (5 violation patterns across identity/equal/
  take_three/no_prose/wrong_separator = 6 expected due to identity having 2)

### 3. Wire into `audit_rust_standards.py`

Wrapper template (this exact form — the audit-pitfalls §45 documents why):

```python
('check NN — §X.Y <rule name> (<date>, user 原话: "<verbatim quote>")', '''
# Per rust-standards §X.Y ...
# Companion script: verify_<rule>.py.
cd {{target}}
python3 "{{audit_script_dir}}/verify_<rule>.py" "{{target}}" \\
    | grep -v -E '^=== <summary-line-prefix>:'
exit_code=${PIPESTATUS[0]}
if [ "$exit_code" -ne 0 ]; then
    echo "FAIL: verify_<rule>.py exited $exit_code" >&2
fi
exit "$exit_code"
'''),
```

Pitfalls (audit-pitfalls §45–§67):
- `audit_script_dir` must be substituted via Python `os.path.dirname(__file__)`
  + template variable, **not** `$(dirname "$0")` inside the shell — `bash -c`
  sets `$0=bash`, the script path is wrong
- The `grep -v -E '^=== ...'` filter is mandatory — the verifier's success
  summary line would otherwise register as a hit
- `>&2` for the FAIL trailer — stdout violations are line-counted by
  `run_check`, stderr is not; a FAIL trailer on stdout inflates the hit
  count by 1

### 4. End-to-end pipeline verification

After wiring, run the full audit on each fixture and confirm:
- `*-compliant/` → check NN **PASS** (0 hits)
- `*-violating/` → check NN **FAIL** with exact expected count
- `*-edge-cases/` (if exists) → check NN **FAIL** with exact expected count

Pitfall (audit-pitfalls §45): the wrapper and the verifier script must be in
the **same commit**.  Adding a wrapper reference to a script that lives in an
unmerged branch produces a "file not found" fallback that audit treats as 0
violations — a green check that means nothing.

### 5. Document in `audit-pitfalls.md` §XX

Append a new section at the bottom of `audit-pitfalls.md` documenting:
- Which check this is, which § of rust-standards it enforces
- Which fixtures were created and their expected counts
- Known limitations of the verifier (e.g. tuple fields not covered, regex
  false positives on edge cases)
- Real-world impact measured on euv / hyperlane / ctares (raw violation
  count from the first dry-run)

Format consistent with §45–§67.

### 6. (When violations are large) Separate sweep PR

When the verifier produces ≥ 50 violations on euv or hyperlane, **do not
enable audit enforcement in the same commit** as the verifier.  Two-PR
sequence:

1. **PR A** — verifier + fixtures + wrapper + audit-pitfalls §XX (audit
   enforcement is now live, but downstream repo baseline hasn't been
   touched)
2. **PR B (or PRs)** — sweep: run verifier in dry-run mode, fix each
   violation file-by-file, re-run audit to confirm 0 violations

The audit enablement PR may be reviewed alone — the sweep is a separate
audit-friendly change that doesn't need verifier infrastructure review.

Real-world examples:
- check 35 Layer 4 (doc-comment signature-type match): **801 violations in
  euv** — sweep PR separate from verifier commit
- check 38 (self.field access): **203 violations in euv** — same pattern

## Common failure modes

Captured from §45–§67 — read before adding any new check:

- **Wrapper exit code via stdout** (audit-pitfalls §45): don't `echo "FAIL"`
  to stdout; use `>&2`
- **Filter missing on success summary** (audit-pitfalls §45): the
  `=== <rule>: 0 violation(s) ...` line registers as a hit
- **Verifier and wrapper in different PRs** (audit-pitfalls §45): file not
  found at audit run time
- **Two parsers between verifier and fixer** (audit-pitfalls §45): fixer
  succeeds but verifier still flags — re-import the parse function
- **dry-run writes to disk silently** (audit-pitfalls §45): `_rewrite_file`
  with no `write: bool` flag defaults to writing; first `python3 fix_*.py`
  in dry-run mode changes files, second `--write` round overwrites the
  silent changes
- **Unresolved git merge-conflict markers** (§16,audit-pitfalls §45):
  `<<<<<<<` / `=======` / `>>>>>>>` left in committed files after a bad
  stash pop — pre-commit grep `grep -nE '^(<{7}|={7}|>{7})' skills/`
  catches this
- **Edge-case fixture has ambiguous expected count** (this session's
  `identity` example): a single fn can fire multiple Layer 4 sub-checks
  independently (wrong-type-literal + missing-coverage); document this in
  the fixture header

## Filesystem layout

```
skills/rust-standards/scripts/
  verify_<rule>.py           # pure checker
  fix_<rule>.py              # auto-fixer (when applicable)
  audit_rust_standards.py    # 38 wrappers, each invokes one verifier

~/.hermes/cache/scratch/
  rust-std-fixtures/<rule>-{compliant,violating}/
  verifier-fixtures/<rule>-{compliant,violating,edge-cases}/
```

Two parallel fixture roots exist:
- `rust-std-fixtures/` — older checks (e.g. doc-comment), 9-keyword-file-purity
- `verifier-fixtures/` — newer checks (e.g. rename, self-field, layer4)

**Use `verifier-fixtures/` for all new checks** — it is the de-facto
canonical location since 2026-09-26.

## When a check is strengthened (Layer N → Layer N+1)

When user strengthens an existing rule (e.g. doc-comment Layer 1+2+3 → adds
Layer 4 signature-type match):

1. **Do NOT write a new verifier** — extend the existing one (Layer 4 added
   to `verify_doc_comment_format.py` in this session, not a new script)
2. **Existing fixtures may need to be updated** — the compliant fixture used
   param-name `a` instead of type `u32`; when Layer 4 starts flagging this,
   the fixture must be re-written to use the new stronger format
3. **Add a new edge-case fixture** — Layer 4's edge cases (signature type
   match, prose-before-section, missing coverage) are exactly the kind of
   nuanced per-case behavior that needs the third fixture
4. **Update audit-pitfalls.md** — append a new §XX entry documenting the
   strengthened layer + impact (euv 801 violations for Layer 4 doc-comment
   is the textbook example)
5. **Recommend sweep PR** — same two-PR sequence as a brand-new check

Real-world worked example for Layer 4 doc-comment: see commit history of
`verify_doc_comment_format.py`, `references/02-documentation.md` §2.2, and
`audit-pitfalls.md` §66.
