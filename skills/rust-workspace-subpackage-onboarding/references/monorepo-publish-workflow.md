# Monorepo publish: ordering and CI workflow

Once a Cargo workspace has multiple members that share a single version, the GitHub Actions publish workflow needs to push them in **dependency order** so each crate's `cargo publish` resolves against already-published siblings (or against the workspace's path deps — both are fine, but order matters when one crate's `path = "..."` reference points at a not-yet-built sibling).

## Deriving the publish order

`cargo metadata --format-version 1` exposes the full workspace resolve graph. Filter to `workspace_members`, walk the `dependencies` arrays of each, and emit a topological sort. Concretely (Python, stdlib only):

```python
import json, subprocess
from collections import deque, defaultdict

r = subprocess.run(["cargo", "metadata", "--format-version", "1"],
                   capture_output=True, text=True, check=True)
d = json.loads(r.stdout)
pkgs = {p["name"]: p for p in d["packages"]}

# Only intra-workspace edges
edges = {name: {dep["name"] for dep in pkg["dependencies"] if dep["name"] in pkgs}
         for name, pkg in pkgs.items()}

indeg = {n: len(deps) for n, deps in edges.items()}
rev = defaultdict(list)
for n, deps in edges.items():
    for dep in deps:
        rev[dep].append(n)

# Topological: leaves first
queue = deque(sorted(n for n, v in indeg.items() if v == 0))
order = []
while queue:
    n = queue.popleft()
    order.append(n)
    for child in sorted(rev[n]):
        indeg[child] -= 1
        if indeg[child] == 0:
            queue.append(child)

assert len(order) == len(edges), "cycle in workspace deps"
print(order)
```

Sample output for the hyperlane workspace:

```
1. http-compress
2. http-constant
3. http-request
4. hyperlane-type
5. hyperlane-core
6. hyperlane-macros
7. hyperlane
8. hyperlane-cli
```

Note `http-request` lands early (it has no internal deps), but it must still be published before any consumer that might import it — though in this workspace, only `http-type` (a crates.io crate, not a workspace member) consumes it.

## Workflow shape

`publish: needs: [check, tests, clippy, build]` — all CI jobs gate on the four gates above. The `setup` job only reads `version` from the root `Cargo.toml` (no `toml-cli` needed):

```bash
VERSION=$(grep -E '^version = ' Cargo.toml | head -1 | sed -E 's/^version = "([^"]+)".*/\1/')
```

Then publish:

```bash
PUBLISH_ORDER=(
  "http-compress"
  "http-constant"
  # ... full topological order ...
)

declare -A PUBLISH_RESULT
for PKG_NAME in "${PUBLISH_ORDER[@]}"; do
  # 36 attempts max per package, with `sleep $((i * 5))` backoff between attempts
  # to avoid hammering crates.io when a publish slot isn't ready.
  # Detect "already published" / "already been uploaded" as success.
  # Detect "unauthorized/forbidden/token/credential" as fatal (no retry).
done

if [ "$ALL_OK" = "true" ]; then
  echo "published=true" >> "$GITHUB_OUTPUT"
else
  exit 1
fi
```

`release:` then depends on `publish:` succeeding, creates a single GitHub Release tagged `v$VERSION` (since the workspace shares a version), with notes listing all 8 crates in a table:

```bash
NOTES_FILE="$(mktemp)"
{
  printf '## Release %s\n\n' "$TAG"
  printf '| Package | crates.io | docs.rs |\n'
  printf '| --- | --- | --- |\n'
  for pkg in "${PACKAGES[@]}"; do
    printf '| `%s` | [crates.io](https://crates.io/crates/%s/%s) | [docs.rs](https://docs.rs/%s/%s) |\n' \
      "$pkg" "$pkg" "$VERSION" "$pkg" "$VERSION"
  done
} > "$NOTES_FILE"
gh release create "$TAG" --notes-file "$NOTES_FILE" --latest
```

Build the source archive using the **repo name** (not the package name):

```bash
REPO_NAME="${{ github.event.repository.name }}"
git archive --format=tar.gz --prefix="${REPO_NAME}-${VERSION}/" HEAD > "${REPO_NAME}-${VERSION}.tar.gz"
```

## Pitfalls

### Do NOT use heredoc strings for release notes

GitHub Actions' YAML pre-validator misparses a `|` block scalar at the start of a line inside a `NOTES="..."` shell assignment, even though the assignment is inside a `run: |` block. Symptom:

```
error: could not find expected ':' at line 328, column 1
```

Fix: don't construct the notes string with a multi-line shell literal that contains `|`. Build the file via `printf` line-by-line into a tempfile, then pass it to `gh release create --notes-file`. See the snippet above.

### Don't put `version = "X.Y.Z"` next to `path = "..."` once versions are unified

If subpackages adopt `version.workspace = true` and the workspace root has `[workspace.package].version = "21.3.6"`, then `[workspace.dependencies]` entries must drop the inline `version` field too. Otherwise `cargo publish` aborts with:

```
failed to select a version for the requirement `http-compress = "^3.0.28"`
candidate versions found which didn't match: 21.3.6
```

Use just `{ path = "compress" }` — cargo reads the version from the subpackage's own manifest.

### Don't write a separate `sync_workspace_version` job

Older workflow files (including the one this project had at onboarding time) include a job that `sed`s subpackage versions to the workspace root's. Once everything uses `version.workspace = true`, that job:

- Matches no lines (the subpackages have no `version = "..."` literal to sed).
- Either does nothing (if guarded by `git diff --cached --quiet`) or produces a confusing empty commit.
- Adds latency and noise.

Delete it. `version` is now purely a `[workspace.package]` concern.

### `cargo publish --allow-dirty --no-verify`

The workflow runs against a checkout that may have uncommitted changes (e.g. recent commit from another job). `--allow-dirty` accepts that. `--no-verify` skips the per-package build verification because the workspace's `cargo check --workspace --release --all-features` from the `build:` job already validated compilation. Without `--no-verify`, `cargo publish` will rebuild every dependent crate from scratch, doubling CI time.

## Don't

- Don't try to publish in parallel via `cargo publish --workspace` from inside CI. It works locally but in CI you want explicit per-crate retry logic and a clear failure summary.
- Don't bump the workspace version from the workflow. The user wants a single source of truth: editing the root `Cargo.toml` and committing is the intended path. Bumping from CI hides the change from `git log`.
- Don't create one GitHub Release per crate. They share a version; one Release with a table is correct.
