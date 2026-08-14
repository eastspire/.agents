# scripts/

Utility scripts for maintaining this repository.

## `sync-references.sh` — sync skill `references/` from upstream docs-pages

Several skills (currently `euv/`, `hyperlane/`) vendor a curated subset of pages from the private [docs-pages](https://github.com/docs-pages/docs) repo. The pages live flat under `skills/<skill>/references/` so a tool can `read_file` them without going through the network.

When upstream docs-pages changes, run the sync script to refresh the vendored copies. The script:

1. Shallow-clones docs-pages (or reuses a clone via `--source-dir`).
2. For each line in `sync-references.mapping`, copies the source `.md` into the destination, strips VuePress-only frontmatter (`head`, `icon`, `order`, `dataset`, `index`, `keywords`), and prepends a normalized header with `synced_from` / `sync_method` / `sync_date` so it's clear where the content came from.
3. For lines tagged `# manual override:`, leaves the existing dest file alone (and warns if no dest exists yet).

### Usage

```shell
# Full sync — clones docs-pages into a temp dir, then exits
bash scripts/sync-references.sh

# Reuse an existing clone (faster, no network)
bash scripts/sync-references.sh --source-dir /path/to/docs-pages

# Preview what would change
bash scripts/sync-references.sh --dry-run

# Override the manual-override skips (NOT recommended — you'll lose local edits)
bash scripts/sync-references.sh --force
```

### Adding a new file

Append a line to `sync-references.mapping`:

```
skills/euv/references/foo.md<TAB>src/euv/usage-introduction/foo.md
```

(tab-separated; the third column is an optional note). Then re-run the script.

### Pinning a custom version of a file

If you need to hand-edit a vendored page (e.g. add a section that's not yet in upstream), append `# manual override:` to its mapping line. The script will then skip it on every run. The dest file will keep a `synced_from` header from the last successful sync so you can tell how stale it is.

### Verifying

```shell
# Show which files changed since HEAD, plus any drift/orphans
bash scripts/verify-references.sh

# Same, but also exit non-zero on drift
bash scripts/verify-references.sh --strict

# Compare against a different ref (e.g. main, or a tag)
bash scripts/verify-references.sh --against main
```

`verify-references.sh` will additionally check for **mapping drift** (source paths in the mapping that don't exist upstream anymore) if you point it at a clone via `DOCS_PAGES_DIR`:

```shell
DOCS_PAGES_DIR=/path/to/docs-pages bash scripts/verify-references.sh
```

## Why a custom script instead of git submodules / symlinks?

docs-pages is a **private** VuePress monorepo with hundreds of pages, nested subdirs, and VuePress-specific frontmatter. Submodules drag in the whole tree; symlinks break on Windows + confuse the `read_file` tool. A flat curated list under each skill:

- keeps the skill repo small and reviewable
- lets each skill pick exactly the pages it needs
- survives docs-pages' upstream restructuring (just update the mapping)
- makes the relationship explicit (the `synced_from` line in every synced file)
