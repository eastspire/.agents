# Monorepo Migration Checklist

End-to-end playbook for collapsing N upstream single-crate repos into one
monorepo (hyperlane pattern, modeled after euv). Use when:

- User asks to merge `repo-a`, `repo-b`, `repo-c` into one monorepo root.
- A crate family has accumulated (e.g. `core / type / macros / cli`) and you
  want a single source of truth + single CI pipeline + single version number.

Hyperlane was the first non-euv application of this pattern (2026-09). The
playbook here is general; replace crate names with your target as needed.

## 1. Pre-flight

| Step | Command / Output |
 | --- | --- |
 | List upstream crates | `gh repo list <org>` -- target `core / type / macros / cli` style family |
 | Confirm Track 2 fork protocol | Fork to eastspire via `gh repo fork <org>/<repo> --remote=false` (don't clone -- we want fast fork + clean clone) |
 | Clone each upstream + the target root | `git clone https://github.com/<org>/<repo>.git <local>` |

Do not start monorepo work until you have local clones of (a) the target
monorepo root (will become `eastspire/<repo>` fork) and (b) each upstream
crate you intend to merge.

## 2. Decide the crate shape

For hyperlane the final shape was 5 crates:

| Crate | Source | Role |
| --- | --- | --- |
| `<root-name>` | new | pure re-export shim (lib) |
| `<name>-core` | upstream main crate | framework body |
| `<name>-macros` | upstream proc-macro crate | attribute macros |
| `<name>-type` | upstream HTTP-types crate | type library |
| `<name>-cli` | upstream CLI tool | bin target |

Rules of thumb:

- Root crate is **always** a re-export shim with no source of its own.
- Proc-macro crates stay independent (they cannot reverse-depend on the root
  or it forms a cycle -- see §13.6 of hyperlane-standards).
- Type-only libraries that other crates depend on should be **leaves** with
  no internal deps.
- Bin targets (CLI tools) get their own crate.

## 3. Branch + migration

```bash
cd /root/github/<org>/<root-repo>
git checkout -b feat/monorepo
mkdir -p core macros type cli
```

Move root's existing source into `core/`:

```bash
git mv src core/src
git mv tests core/tests
```

If `git mv` created `core/tests/tests/` (because you `mkdir -p core/tests`
first), flatten with:

```bash
git mv core/tests/tests core/tests_tmp
mkdir -p core/tests
git mv core/tests_tmp/* core/tests/
rmdir core/tests_tmp
```

Copy each upstream crate as-is (excluding `.git`, build artifacts, debug dirs):

```bash
for src in /path/to/upstream-cli /path/to/upstream-macros /path/to/upstream-type; do
  rsync -a --exclude='.git' --exclude='target' --exclude='debug' "$src/" "<dest>/"
done
```

## 4. Strip top-level comments from every `lib.rs`

Rust-standards §2.5: `lib.rs` / `mod.rs` / `Cargo.toml` carry no comments.

```bash
# For each <crate>/src/lib.rs:
sed -i '1,/<empty-line-after-last-doc-comment>/d' <crate>/src/lib.rs
sed -i '1s/^\xEF\xBB\xBF//' <crate>/src/lib.rs    # strip BOM if present
```

Verify with `head -3 <crate>/src/lib.rs` -- first line should be `mod xxx;`
or `pub use ...;`, not `//!`.

**Pitfall**: If you delete too many lines you also strip `mod xxx;`
declarations. Count the doc lines first (`grep -c '^//!'`), then `1,N d`
where N is `doc_lines + 1` (the trailing blank line). For hyperlane-type it
was `1,11d`, for hyperlane-macros `1,7d`, for hyperlane-cli `1,4d`.

## 5. Rewrite each sub-crate `Cargo.toml`

For each sub-crate:

- Rename `name = "..."` to the new monorepo-prefixed name (e.g.
  `http-type` → `hyperlane-type`).
- Drop `repository = "https://github.com/<upstream-org>/<repo>.git"` -- set
  to the **monorepo URL** so all crates point to one place.
- Rewrite internal deps:
  - `http-type = "20.1.9"` (crates.io dep, stays as-is) → unchanged.
  - `hyperlane = "21.3.6"` (upstream crate that became a workspace member)
    → `hyperlane-core = { path = "../core", version = "<shared-ver>" }`.
- `readme = "README.md"` (per-crate, **never** `../../README.md` -- cargo
  publish rejects this).
- Add `[dev-dependencies]` for `tokio` / `serde` / `url` if `tests/mod.rs`
  imports them but the runtime `[dependencies]` doesn't pull them in.
- Profile blocks (`[profile.dev]` / `[profile.release]`) can stay -- cargo
  will warn "profiles for the non root package will be ignored" but accept
  the build (matches euv pattern).

## 6. Create the root `Cargo.toml`

```toml
[workspace]
resolver = "2"
members = ["core", "macros", "type", "cli"]

[workspace.package]
version = "21.3.6"
edition = "2024"
authors = ["root@ltpp.vip"]
license = "MIT"
repository = "https://github.com/<org>/<root>.git"

[workspace.dependencies]
<name>-core = { path = "core", version = "21.3.6" }
<name>-macros = { path = "macros", version = "21.3.6" }
<name>-type = { path = "type", version = "21.3.6" }
<name>-cli = { path = "cli", version = "21.3.6" }

[package]
name = "<name>"
version.workspace = true
readme = "README.md"
edition.workspace = true
authors.workspace = true
license.workspace = true
repository.workspace = true
# description, keywords, categories, exclude -- copy from old root Cargo.toml

[dependencies]
<name>-core = { workspace = true }
<name>-macros = { workspace = true }
# Do NOT add <name>-type here -- root lib.rs does not need it directly.

[profile.dev]
# copy from old root -- single source of profile truth
[profile.release]
```

Root `src/lib.rs`:

```rust
pub use <name>_core::*;
pub use <name>_macros::*;
```

No `//!` header, no `pub use <name>_type::*` (already re-exported via core).

## 7. Rewrite internal crate references inside the source

Three sweeps with `sed`:

1. In macros (and any other proc-macro / re-export crate):
   ```bash
   find macros/src -name '*.rs' -exec sed -i 's|::hyperlane::|::hyperlane_core::|g' {} +
   ```
2. In macros doctest:
   ```bash
   sed -i 's|use <name>::\*;|use <name>_core::*;|g' macros/src/lib.rs
   ```
3. In sub-crate tests:
   ```bash
   sed -i 's|use <name>::\*;|use <name>_core::*;|g' core/tests/mod.rs
   ```
   (Only if the original tests used `use <name>::*` because they lived in a
   single-crate world.)

Each doctest that referenced `::hyperlane::Foo` will need its `use` line
rewritten too -- if you miss these, `cargo test --doc` will surface
"could not find hyperlane in the list of imported crates" 100 times in
macros.

## 8. Copy README into each sub-crate

```bash
for sub in core macros type cli; do
  cp README.md "$sub/README.md"
done
```

Required because cargo publish refuses cross-repo `readme` paths
(see §13.5 of hyperlane-standards).

## 9. First cargo check

```bash
cargo check --workspace
```

Expected warnings (non-fatal, euv-pattern):

- `unused import: hyperlane_type::*` in root lib.rs -- fix by removing the
  re-export (type is already exposed via core).
- `profiles for the non root package will be ignored` × N -- expected;
  root Cargo.toml is the single source of profile truth.

If you see "no matching package named `hyperlane-foo`" instead, your
`macros/src/common/fn.rs` still references `::hyperlane::Foo` -- re-run
sweep #1.

## 10. CI workflow (rust.yml)

Adapt euv's `rust.yml` (the full file is in `euv-standards` references) to
your crate list:

- `setup` + `sync_workspace_version` (master push only) +
  `check`/`tests`/`clippy`/`build` are unchanged.
- `publish` job: change `PUBLISH_ORDER=(...)` to your topological order.
  Rule: leaves first, root last. For hyperlane:
  `("hyperlane-type" "hyperlane-macros" "hyperlane-core" "hyperlane-cli" "hyperlane")`.
- `release` job: change package name output strings.

The `sync_workspace_version` job reads `toml get Cargo.toml workspace.members`
and `toml get <member>/Cargo.toml package.name` to discover crates
dynamically -- no edit needed when adding crates later, the job adapts.

## 11. Verification checklist

```bash
cargo check --workspace
cargo test --workspace --no-fail-fast   # 0 failed required
cargo clippy --workspace --all-targets
cargo fmt --all && cargo fmt --all     # idempotent
python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py .
cargo metadata --format-version=1 --no-deps   # check no cycles
```

## 12. PR etiquette

- Single commit, single PR.
- PR body lists workspace layout + the dependency graph + how CI was
  verified.
- Do not merge yourself if upstream is Track 2 (`hyperlane-dev`, `euv-dev`,
  third-party). Maintainer merges.
- After maintainer merge, monitor for the auto `chore: sync all package
  versions to X.Y.Z` commit from `sync_workspace_version` -- if missing or
  stale, write it manually.

## 13. Common false positives in `audit_rust_standards.py`

- `cli/src/main.rs` triggers FAIL1 (non-keyword prod file) and FAIL7 (sub-file
  first line not `use super::*`). Both are audit-script gaps -- `main.rs`
  is the bin target entry point and must exist. Either accept the FAIL or
  patch `audit_rust_standards.py` to whitelist `main.rs`.
- `unwrap` / `expect` in upstream proc-macro / CLI source -- audit FAIL3
  flags these, but they're pre-existing upstream code. Out of scope for a
  monorepo migration PR; address in a follow-up.

If the migration PR is intentionally scoped (just structural, no semantic
changes), accepting these FAIL items is correct. State so explicitly in the
PR body.