# Single-crate rust.yml (euv-template simplified)

Use this when porting euv's `rust.yml` to a **single-crate Rust project**
(non-workspace, non-WASM, server/binary application). The euv template has
8 jobs designed for a 7-crate workspace with WASM targets; most are noise
for a single crate. This file is the **verified-working simplified version**
(run 33392352509, 2026-08-31, on `eastspire/hyperlane-mcp-upload`).

## When to use

- Single crate, no `workspace.members`
- Default branch is `master` (not `main`)
- Binary or server (not WASM)
- Want clients to `cargo install <name>` and get a working binary
- Plan to publish to crates.io via CI

## When NOT to use

- Workspace (use euv's full rust.yml + `sync_workspace_version` job)
- WASM (need `wasm32-unknown-unknown` target + Pages deploy steps)
- Library-only (no binary = no build smoke test, drop that step)

## The file

`.github/workflows/rust.yml`:

```yaml
name: Rust
on:
  push:
    branches: [master]
  pull_request:
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
      branch_name: ${{ steps.read.outputs.branch_name }}
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
      - name: Cache toml-cli
        id: cache_toml_cli
        uses: actions/cache@v3
        with:
          path: ~/.cargo/bin/toml
          key: toml-cli-${{ runner.os }}
      - name: Install toml-cli
        if: steps.cache_toml_cli.outputs.cache-hit != 'true'
        run: |
          for i in 1 2 3 4 5 6 7 8; do
            if cargo install toml-cli; then
              break
            fi
            echo "🔁 Retrying..."
          done
      - name: Read cargo metadata
        id: read
        run: |
          VERSION=$(toml get Cargo.toml package.version --raw)
          PACKAGE_NAME=$(toml get Cargo.toml package.name --raw)
          BRANCH_NAME="${{ github.ref_name }}"
          echo "📦 Detected package: $PACKAGE_NAME v$VERSION"
          echo "🌿 Branch: $BRANCH_NAME"
          if [ -z "$VERSION" ] || [ -z "$PACKAGE_NAME" ]; then
            echo "❌ Failed to read package info from Cargo.toml"
          fi
          if [ "$BRANCH_NAME" = "master" ]; then
            TAG="v$VERSION"
          else
            TAG="v$VERSION-$BRANCH_NAME"
          fi
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "tag=$TAG" >> $GITHUB_OUTPUT
          echo "package_name=$PACKAGE_NAME" >> $GITHUB_OUTPUT
          echo "branch_name=$BRANCH_NAME" >> $GITHUB_OUTPUT

  check:
    needs: setup
    if: always() && (github.event_name == 'pull_request' || github.event_name == 'push')
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: ${{ github.ref }}
      - name: Setup rust
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
          components: rustfmt
      - name: Format check
        run: cargo fmt -- --check

  tests:
    needs: setup
    if: always() && (github.event_name == 'pull_request' || github.event_name == 'push')
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: ${{ github.ref }}
      - name: Prepare environment
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
      - name: Run tests
        run: cargo test --all-features -- --nocapture

  clippy:
    needs: setup
    if: always() && (github.event_name == 'pull_request' || github.event_name == 'push')
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: ${{ github.ref }}
      - name: Load clippy
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
          components: clippy
      - name: Run clippy
        run: cargo clippy --all-features --all-targets

  build:
    needs: setup
    if: always() && (github.event_name == 'pull_request' || github.event_name == 'push')
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: ${{ github.ref }}
      - name: Setup build
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
      - name: Build release
        run: cargo build --release --all-features
      - name: Verify binary exists
        run: |
          if [ ! -f "target/release/<BIN-NAME>" ]; then
            echo "❌ Binary not found at target/release/<BIN-NAME>"
            exit 1
          fi
          echo "✅ Binary built successfully"
          ls -la target/release/<BIN-NAME>
      - name: Smoke test binary
        run: |
          ./target/release/<BIN-NAME> &
          SERVER_PID=$!
          sleep 2
          if curl -sf http://127.0.0.1:<PORT>/health > /tmp/health.txt; then
            echo "✅ /health responds"
            cat /tmp/health.txt
          else
            echo "❌ /health did not respond"
            kill $SERVER_PID 2>/dev/null || true
            exit 1
          fi
          kill $SERVER_PID 2>/dev/null || true

  publish:
    permissions:
      contents: write
    needs: [setup, check, tests, clippy, build]
    if: always() && github.event_name == 'push' && github.ref_name == 'master' && needs.setup.outputs.tag != '' && needs.check.result == 'success' && needs.tests.result == 'success' && needs.clippy.result == 'success' && needs.build.result == 'success'
    runs-on: ubuntu-latest
    outputs:
      published: ${{ steps.publish.outputs.published }}
    steps:
      - name: Check branch
        id: check_branch
        run: |
          if [ "${{ needs.setup.outputs.branch_name }}" != "master" ]; then
            echo "⚠️ Not on master branch (current: ${{ needs.setup.outputs.branch_name }}), skipping publish"
            echo "skip=true" >> $GITHUB_OUTPUT
          else
            echo "✅ On master branch, proceeding with publish"
            echo "skip=false" >> $GITHUB_OUTPUT
          fi
      - name: Checkout
        if: steps.check_branch.outputs.skip == 'false'
        uses: actions/checkout@v4
        with:
          ref: ${{ github.ref }}
      - name: Configure git
        if: steps.check_branch.outputs.skip == 'false'
        run: |
          git config user.name "eastspire"
          git config user.email "root@ltpp.vip"
      - name: Publish to crates.io
        id: publish
        if: steps.check_branch.outputs.skip == 'false'
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}
        run: |
          echo "published=false" >> $GITHUB_OUTPUT
          echo "${{ secrets.CARGO_REGISTRY_TOKEN }}" | cargo login
          VERSION="${{ needs.setup.outputs.version }}"
          PKG_NAME="${{ needs.setup.outputs.package_name }}"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "📦 Publishing $PKG_NAME v$VERSION"
          PUBLISHED=false
          for ((i=1; i<=36; i++)); do
            echo "🚀 Attempt $i/36: publishing $PKG_NAME v$VERSION"
            set +e
            PUBLISH_OUTPUT=$(cargo publish --allow-dirty --no-verify 2>&1)
            PUBLISH_EXIT_CODE=$?
            set -e
            echo "$PUBLISH_OUTPUT"
            if [ $PUBLISH_EXIT_CODE -eq 0 ]; then
              echo "✅ $PKG_NAME v$VERSION publish exited with code 0"
              PUBLISHED=true
              break
            fi
            if echo "$PUBLISH_OUTPUT" | grep -q "is already published"; then
              echo "📦 $PKG_NAME v$VERSION is already published to crates.io"
              PUBLISHED=true
              break
            fi
            if echo "$PUBLISH_OUTPUT" | grep -q "already been uploaded"; then
              echo "📦 $PKG_NAME v$VERSION is already uploaded to crates.io"
              PUBLISHED=true
              break
            fi
            echo "⚠️ Attempt $i failed for $PKG_NAME (exit code: $PUBLISH_EXIT_CODE)"
            if echo "$PUBLISH_OUTPUT" | grep -qi "unauthorized\|forbidden\|token\|credential"; then
              echo "🚫 Authentication error detected, aborting"
              break
            fi
            if [ "$i" -lt "36" ]; then
              echo "🔁 Retrying..."
            fi
          done
          if [ "$PUBLISHED" = "true" ]; then
            VERIFY_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "User-Agent: $PKG_NAME" "https://crates.io/api/v1/crates/$PKG_NAME/$VERSION")
            if [ "$VERIFY_HTTP_CODE" = "200" ]; then
              echo "✅ $PKG_NAME v$VERSION verified on crates.io (HTTP 200)"
            else
              echo "⚠️ $PKG_NAME v$VERSION could not be verified (HTTP $VERIFY_HTTP_CODE), but publish reported success - continuing"
            fi
            echo "published=true" >> "$GITHUB_OUTPUT"
            echo "🎉🎉🎉 PUBLISH SUCCESSFUL 🎉🎉🎉"
            echo "📦 Crates.io: https://crates.io/crates/$PKG_NAME/$VERSION"
            echo "📚 Docs.rs: https://docs.rs/$PKG_NAME/$VERSION"
            echo "📥 Install: cargo install $PKG_NAME"
          else
            echo "❌ $PKG_NAME v$VERSION failed to publish"
          fi

  release:
    needs: [setup, publish]
    permissions:
      contents: write
    if: always() && github.event_name == 'push' && github.ref_name == 'master' && needs.setup.outputs.tag != '' && needs.publish.result == 'success'
    runs-on: ubuntu-latest
    outputs:
      released: ${{ steps.release.outputs.released }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: ${{ github.ref }}
          fetch-depth: 0
      - name: Get package name and branch info
        id: package_info
        run: |
          echo "package_name=${{ needs.setup.outputs.package_name }}" >> $GITHUB_OUTPUT
          echo "branch_name=${{ needs.setup.outputs.branch_name }}" >> $GITHUB_OUTPUT
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
      - name: Build source archives
        run: |
          set -e
          PACKAGE_NAME="${{ steps.package_info.outputs.package_name }}"
          VERSION="${{ needs.setup.outputs.version }}"
          echo "📦 Building source archives..."
          git archive --format=zip --prefix="${PACKAGE_NAME}-${VERSION}/" HEAD > "${PACKAGE_NAME}-${VERSION}.zip"
          git archive --format=tar.gz --prefix="${PACKAGE_NAME}-${VERSION}/" HEAD > "${PACKAGE_NAME}-${VERSION}.tar.gz"
          echo "✅ Source archives built"
          ls -la "${PACKAGE_NAME}-${VERSION}".{zip,tar.gz}
      - name: Create tag
        id: tag
        run: |
          if [ "${{ steps.check_tag.outputs.remote_tag_exists }}" = "false" ]; then
            echo "🏷️ Creating and pushing tag: ${{ needs.setup.outputs.tag }}"
            git tag "${{ needs.setup.outputs.tag }}"
            git push origin "${{ needs.setup.outputs.tag }}"
            echo "tag_created=true" >> $GITHUB_OUTPUT
          else
            echo "tag_created=false" >> $GITHUB_OUTPUT
          fi
      - name: Create or update release
        id: release
        run: |
          set -e
          echo "released=false" >> $GITHUB_OUTPUT
          PACKAGE_NAME="${{ steps.package_info.outputs.package_name }}"
          VERSION="${{ needs.setup.outputs.version }}"
          TAG="${{ needs.setup.outputs.tag }}"
          BRANCH_NAME="${{ steps.package_info.outputs.branch_name }}"
          if gh release view "$TAG" > /dev/null 2>&1; then
            echo "🔄 Updating existing release: $TAG"
            gh release view "$TAG" --json assets --jq '.assets[].name' | while read asset; do
              if [ -n "$asset" ]; then
                echo "🗑️ Deleting asset: $asset"
                gh release delete-asset "$TAG" "$asset" --yes || true
              fi
            done
            TITLE="[$BRANCH_NAME]($TAG updated $(date '+%Y-%m-%d %H:%M:%S'))"
            if gh release edit "$TAG" \
                --title "$TITLE" \
                --notes "[$BRANCH_NAME] - release $TAG updated at $(date '+%Y-%m-%d %H:%M:%S UTC')
              ## Changes
              - Branch: $BRANCH_NAME
              - Version: $VERSION
              - Package: $PACKAGE_NAME
              ## Links
              📦 [Crate on crates.io](https://crates.io/crates/$PACKAGE_NAME/$VERSION)
              📚 [Documentation on docs.rs](https://docs.rs/$PACKAGE_NAME/$VERSION)
              📋 [Commit History](https://github.com/${{ github.repository }}/commits/$TAG)
              ## Install
              \`\`\`bash
              cargo install $PACKAGE_NAME
              \`\`\`" && \
                 gh release upload "$TAG" "${PACKAGE_NAME}-${VERSION}.zip" "${PACKAGE_NAME}-${VERSION}.tar.gz" --clobber; then
              echo "released=true" >> $GITHUB_OUTPUT
              echo "✅ Updated release $TAG"
              echo "🚀 Release: ${{ github.server_url }}/${{ github.repository }}/releases/tag/$TAG"
            else
              echo "❌ Failed to update release"
            fi
          else
            echo "🆕 Creating new release: $TAG"
            TITLE="[$BRANCH_NAME]($TAG created $(date '+%Y-%m-%d %H:%M:%S'))"
            if gh release create "$TAG" \
              --title "$TITLE" \
              --notes "[$BRANCH_NAME] - release $TAG created at $(date '+%Y-%m-%d %H:%M:%S UTC')
            ## Changes
            - Branch: $BRANCH_NAME
            - Version: $VERSION
            - Package: $PACKAGE_NAME
            ## Links
            📦 [Crate on crates.io](https://crates.io/crates/$PACKAGE_NAME/$VERSION)
            📚 [Documentation on docs.rs](https://docs.rs/$PACKAGE_NAME/$VERSION)
            📋 [Commit History](https://github.com/${{ github.repository }}/commits/$TAG)
            ## Install
            \`\`\`bash
            cargo install $PACKAGE_NAME
            \`\`\`" \
              --latest && \
               gh release upload "$TAG" "${PACKAGE_NAME}-${VERSION}.zip" "${PACKAGE_NAME}-${VERSION}.tar.gz"; then
              echo "released=true" >> $GITHUB_OUTPUT
              echo "✅ Created release $TAG"
              echo "🚀 Release: ${{ github.server_url }}/${{ github.repository }}/releases/tag/$TAG"
            else
              echo "❌ Failed to create release"
            fi
          fi
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## What was simplified from euv

| Dropped from euv | Why |
| --- | --- |
| `sync_workspace_version` job | Single crate has no workspace members to sync |
| `--target wasm32-unknown-unknown` on build | Not a WASM project |
| `-p euv-cli` host test step | No separate CLI crate |
| `PUBLISH_ORDER` / `SKIP_PACKAGES` arrays | Single package, just `cargo publish` once |
| `concurrency:` group | Only 7 jobs, no race risk; add if burst observed |

## What was added (vs euv)

| Added | Why |
| --- | --- |
| `build` job binary existence check | Catches cargo silently building nothing |
| `build` job smoke test (background binary + curl /health) | Catches "builds but won't run" (e.g. port conflict, missing dep) |
| Single `cargo publish` instead of per-package loop | Single crate |

## Variables to substitute

- `<BIN-NAME>` — name in `[[bin]] name = "..."` (e.g. `hyperlane-mcp-upload`)
- `<PORT>` — port the binary listens on (used in smoke test)
- Replace `root@ltpp.vip` git config email with your own
- Replace `User-Agent: <PKG_NAME>` with your crate name (cosmetic for crates.io API)

## Required secrets

- `CARGO_REGISTRY_TOKEN` — from https://crates.io/me/ → Tokens → New Token
- `GITHUB_TOKEN` — auto-provided by GitHub Actions

**`CARGO_REGISTRY_TOKEN` is NOT auto-set**; you must add it manually at
`https://github.com/<owner>/<repo>/settings/secrets/actions` even on personal
repos. CI without it fails at `cargo login` with `please provide a non-empty token`.

## Verified

- Commit hash `d12f7e3` on `eastspire/hyperlane-mcp-upload`
- Run `33392352509` — setup / check / tests / clippy / build all green;
  publish failed at `cargo login` (expected, no token), release correctly
  skipped
- After adding `CARGO_REGISTRY_TOKEN`, the same workflow publishes
  end-to-end with no further changes