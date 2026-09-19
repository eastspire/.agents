# Hyperlane-aligned single-crate `rust.yml` (euv-docs verified)

The user pattern is "脚本对齐 hyperlane 的脚本即可" — copy `hyperlane-dev/hyperlane`'s
`.github/workflows/rust.yml` 1:1 and adapt for the target crate. Verified working on
`euv-dev/euv-docs` (PR #40, run `35415160651`, 2026-09-19).

## When to use

- Single-crate Rust project where the user explicitly wants the **hyperlane rust.yml structure**
- Want `cargo install --git ...` users to get a working binary
- Want GitHub Releases to auto-create on every version bump
- Project is publish-ready (no `publish = false` in `Cargo.toml`)

## When NOT to use

- Workspace project — drop `Cargo.lock` (cargo install doesn't need lockfile), use the full
  euv template with `sync_workspace_version` job. See `single-crate-rust-yml.md` for the
  verbose alternative.
- Library-only crate with no `[[bin]]` — drop the `build` job's `cargo build --release`.

## The file (verbatim from hyperlane rust.yml, adapted for a non-workspace single crate)

`.github/workflows/rust.yml`:

```yaml
name: Rust
on:
  push:
    branches: [master]
env:
  CARGO_TERM_COLOR: always
jobs:
  setup:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.read.outputs.version }}
      tag: ${{ steps.read.outputs.tag }}
      package_name: ${{ steps.read.outputs.package_name }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Install rust-toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
          components: rustfmt, clippy
      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            target
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
      - name: Install toml-cli
        run: cargo install toml-cli
      - name: Cache toml-cli
        uses: actions/cache@v3
        with:
          path: ~/.cargo/bin/toml
          key: toml-cli-${{ runner.os }}
      - name: Read cargo metadata
        id: read
        run: |
          VERSION=$(toml get Cargo.toml package.version --raw)
          PACKAGE_NAME=$(toml get Cargo.toml package.name --raw)
          echo "📦 Detected package: $PACKAGE_NAME v$VERSION"
          if [ -z "$VERSION" ] || [ -z "$PACKAGE_NAME" ]; then
            echo "❌ Failed to read package info from Cargo.toml"
          fi
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "tag=v$VERSION" >> $GITHUB_OUTPUT
          echo "package_name=$PACKAGE_NAME" >> $GITHUB_OUTPUT

  check:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup rust
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
          components: rustfmt
      - name: Format check
        run: cargo fmt -- --check

  tests:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Prepare environment
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
      - name: Run tests
        run: cargo test --all-features -- --nocapture

  clippy:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Load clippy
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
          components: clippy
      - name: Run clippy
        run: cargo clippy --all-features

  build:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup build
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
      - name: Build release
        run: cargo check --release --all-features

  publish:
    needs: [setup, check, tests, clippy, build]
    if: needs.setup.outputs.tag != ''
    runs-on: ubuntu-latest
    outputs:
      published: ${{ steps.publish.outputs.published }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Restore toml-cli
        uses: actions/cache@v3
        with:
          path: ~/.cargo/bin/toml
          key: toml-cli-${{ runner.os }}
      - name: Publish to crates.io
        id: publish
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}
        run: |
          set -e
          echo "published=false" >> $GITHUB_OUTPUT
          echo "${{ secrets.CARGO_REGISTRY_TOKEN }}" | cargo login
          PACKAGE_NAME=$(toml get Cargo.toml package.name --raw)
          VERSION=${{ needs.setup.outputs.version }}
          if cargo publish --allow-dirty; then
            echo "published=true" >> $GITHUB_OUTPUT
            echo "🎉🎉🎉 PUBLISH SUCCESSFUL 🎉🎉🎉"
            echo "✅ Successfully published $PACKAGE_NAME v$VERSION to crates.io"
            echo "📦 Crates.io: [https://crates.io/crates/$PACKAGE_NAME/$VERSION](https://crates.io/crates/$PACKAGE_NAME/$VERSION)"
            echo "📚 Docs.rs: [https://docs.rs/$PACKAGE_NAME/$VERSION](https://docs.rs/$PACKAGE_NAME/$VERSION)"
          else
            echo "❌ Publish failed"
          fi

  release:
    needs: [setup, check, tests, clippy, build]
    permissions:
      contents: write
      packages: write
    if: needs.setup.outputs.tag != ''
    runs-on: ubuntu-latest
    outputs:
      released: ${{ steps.release.outputs.released }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Get package name
        id: package_info
        run: |
          echo "package_name=${{ needs.setup.outputs.package_name }}" >> $GITHUB_OUTPUT
      - name: Check tag status
        id: check_tag
        run: |
          if git tag -l | grep -q "^${{ needs.setup.outputs.tag }}$"; then
            echo "tag_exists=true" >> $GITHUB_OUTPUT
            echo "🏷️ Tag ${{ needs.setup.outputs.tag }} exists locally"
          else
            echo "tag_exists=false" >> $GITHUB_OUTPUT
            echo "🏷️ Tag ${{ needs.setup.outputs.tag }} does not exist locally"
          fi
          if git ls-remote --tags origin | grep -q "refs/tags/${{ needs.setup.outputs.tag }}$"; then
            echo "remote_tag_exists=true" >> $GITHUB_OUTPUT
            echo "🌐 Tag ${{ needs.setup.outputs.tag }} exists on remote"
          else
            echo "remote_tag_exists=false" >> $GITHUB_OUTPUT
            echo "🌐 Tag ${{ needs.setup.outputs.tag }} does not exist on remote"
          fi
      - name: Check release status
        id: check_release
        run: |
          if gh release view "${{ needs.setup.outputs.tag }}" > /dev/null 2>&1; then
            echo "release_exists=true" >> $GITHUB_OUTPUT
            echo "📦 Release ${{ needs.setup.outputs.tag }} already exists"
          else
            echo "release_exists=false" >> $GITHUB_OUTPUT
            echo "📦 Release ${{ needs.setup.outputs.tag }} does not exist"
          fi
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - name: Create or update release
        id: release
        run: |
          set -e
          echo "released=false" >> $GITHUB_OUTPUT
          PACKAGE_NAME="${{ steps.package_info.outputs.package_name }}"
          VERSION="${{ needs.setup.outputs.version }}"
          TAG="${{ needs.setup.outputs.tag }}"
          echo "📦 Building source archives..."
          git archive --format=zip --prefix="${PACKAGE_NAME}-${VERSION}/" HEAD > "${PACKAGE_NAME}-${VERSION}.zip"
          git archive --format=tar.gz --prefix="${PACKAGE_NAME}-${VERSION}/" HEAD > "${PACKAGE_NAME}-${VERSION}.tar.gz"
          if [ "${{ steps.check_release.outputs.release_exists }}" = "true" ]; then
            echo "🔄 Updating existing release: $TAG"
            gh release view "$TAG" --json assets --jq '.assets[].name' | while read asset; do
              if [ -n "$asset" ]; then
                echo "🗑️ Deleting asset: $asset"
                gh release delete-asset "$TAG" "$asset" --yes || true
              fi
            done
            if gh release edit "$TAG" \
              --title "$TAG (Updated $(date '+%Y-%m-%d %H:%M:%S'))" \
              --notes "Release $TAG - Updated at $(date '+%Y-%m-%d %S UTC')
          ## Changes
          - Version: $VERSION
          - Package: $PACKAGE_NAME
          ## Links
          📦 [Crate on crates.io](https://crates.io/crates/$PACKAGE_NAME/$VERSION)
          📚 [Documentation on docs.rs](https://docs.rs/$PACKAGE_NAME/$VERSION)
          📋 [Commit History](https://github.com/${{ github.repository }}/commits/$TAG)" && \
               gh release upload "$TAG" "${PACKAGE_NAME}-${VERSION}.zip" "${PACKAGE_NAME}-${VERSION}.tar.gz" --clobber; then
              echo "released=true" >> $GITHUB_OUTPUT
              echo "✅ Updated release $TAG"
              echo "🔖 Tag: $TAG"
              echo "🚀 Release: [GitHub Release](${{ github.server_url }}/${{ github.repository }}/releases/tag/$TAG)"
            else
              echo "❌ Failed to update release"
            fi
          else
            if [ "${{ steps.check_tag.outputs.remote_tag_exists }}" = "false" ]; then
              echo "🏷️ Creating and pushing tag: $TAG"
              git tag "$TAG"
              git push origin "$TAG"
            fi
            echo "🆕 Creating new release: $TAG"
            if gh release create "$TAG" \
              --title "$TAG (Created $(date '+%Y-%m-%d %H:%M:%S'))" \
              --notes "Release $TAG - Created at $(date '+%Y-%m:%S UTC')
          ## Changes
          - Version: $VERSION
          - Package: $PACKAGE_NAME
          ## Links
          📦 [Crate on crates.io](https://crates.io/crates/$PACKAGE_NAME/$VERSION)
          📚 [Documentation on docs.rs](https://docs.rs/$PACKAGE_NAME/$VERSION)
          📋 [Commit History](https://github.com/${{ github.repository }}/commits/$TAG)" \
              --latest && \
               gh release upload "$TAG" "${PACKAGE_NAME}-${VERSION}.zip" "${PACKAGE_NAME}-${VERSION}.tar.gz"; then
              echo "released=true" >> $GITHUB_OUTPUT
              echo "✅ Created release $TAG"
              echo "🔖 Tag: $TAG"
              echo "🚀 Release: [GitHub Release](${{ github.server_url }}/${{ github.repository }}/releases/tag/$TAG)"
            else
              echo "❌ Failed to create release"
            fi
          fi
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Differences from hyperlane rust.yml

| hyperlane | this template | why |
| --- | --- | --- |
| `--target wasm32-unknown-unknown` on `dtolnay/rust-toolchain` | (drop unless crate ships wasm) | most single-crate targets don't need wasm |
| One Cargo.toml, no workspace | identical | both are non-workspace |
| `cargo check --release --all-features` for build | identical | lighter than `cargo build --release` (no actual binary needed for `cargo install` — cargo install builds it locally on the user side) |
| `cargo publish --allow-dirty` | identical | works because the workflow job is its own checkout, no `git status` dirty from user perspective |

## Required Cargo.toml changes

- Drop `publish = false` if present. Without this, `cargo publish` exits non-zero and the
  publish job reports `published=false` but the workflow itself still passes — silent
  failure mode that bites on first version bump.
- Confirm the `publish = false` removal is in its own PR (one-line diff). Combining it
  with other changes (`rust.yml` add, comment cleanup) makes the "did the publish job
  actually run?" answer non-obvious.

## Required secrets

- `CARGO_REGISTRY_TOKEN` — crates.io publish token from <https://crates.io/me/>
- `GITHUB_TOKEN` — auto-provided

If `CARGO_REGISTRY_TOKEN` is unset, `cargo publish` reports:

```
please paste the token found on https://crates.io/me below
```

…and exits non-zero. The `if: cargo publish --allow-dirty` block catches this and writes
`published=false` to `$GITHUB_OUTPUT` — the job still passes green, so always verify
`max_stable_version` on crates.io after a release commit (see the "cargo publish 鸡生蛋鸡
生蛋" section in SKILL.md §"cargo publish").

## Trigger semantics

Pipeline fires on every commit to `master`. The `publish` and `release` jobs are gated on
`needs.setup.outputs.tag != ''`, which is always true (toml-cli always reads a non-empty
`version` from any well-formed Cargo.toml). Net effect: **every master commit attempts to
publish + create a GitHub Release**. For a project that's already published its current
version, the publish job will fail at `cargo publish` (already-exists), the release job
will detect the existing release and re-upload the archives (idempotent). So a non-version
bump commit produces a no-op publish + a release asset refresh — harmless but visible in
the run log.

To make the pipeline truly version-bump-only, add a version-bump check:

```yaml
publish:
  if: needs.setup.outputs.tag != '' && contains(needs.setup.outputs.commit_message, 'chore(release)') || needs.setup.outputs.version != needs.setup.outputs.previous_version
```

…but this requires capturing `previous_version` somewhere (e.g. last successful release's
`tag` via `gh release view`). The hyperlane template intentionally does NOT do this —
treats every master commit as a release candidate. Match the upstream simplicity unless
the user explicitly asks for stricter gating.

## Verified

- PR #40 on `euv-dev/euv-docs`, commit `8ec9e77386`, run `35415160651` completed success
- Pipeline jobs: setup / check / tests / clippy / build / publish / release — all green
- `cargo publish --allow-dirty` exited 0 because `publish = false` was removed in the same
  PR (Cargo.toml `-1/+0` line)
- `gh release create v0.1.6` exited 0 because no prior release existed for that tag
- Subsequent PR #41 (`chore(cargo): strip explanatory comments from Cargo.toml`) fired the
  pipeline again — `cargo publish` correctly reported "version already published" and
  short-circuited; `gh release view v0.1.6` triggered the "update existing release" branch
  and re-uploaded `.zip` + `.tar.gz` archives (idempotent, harmless)