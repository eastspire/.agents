# crates.io + GitHub Release 流水线模板(mono-org 标准)

> 2026-09-19 给 euv-docs 仓补齐 release pipeline 时确立的模板。**复用模式**:hyperlane-dev/hyperlane 的 `.github/workflows/rust.yml` 是 mono-org (`euv-dev` / `hyperlane-dev` / `crates-dev`) 的标准发布流水线,euv / euv-docs / 任何 wasm crate 仓都按此 7-job 结构拷贝。

## 1. 模板定位

`.github/workflows/rust.yml` = mono-org 标准 Rust 发布流水线,职责:

- **CI gate**:check (fmt) / tests / clippy / build 必须全过
- **publish**:成功通过 CI 后自动 `cargo publish` 到 crates.io
- **release**:在 master 跑完 publish 后自动建 `git tag` + GitHub Release + 源码 zip/tar 归档

触发:每次 `push: branches: [master]` 触发,**幂等**(已经 publish 过的版本不重复 publish,已经存在的 release 不重复 create)。

## 2. 7-job 结构(完整模板)

```yaml
name: Rust
on:
  push:
    branches: [master]
env:
  CARGO_TERM_COLOR: always

jobs:
  setup:                            # 读 Cargo.toml metadata → 后续 job 共享
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.read.outputs.version }}
      tag: ${{ steps.read.outputs.tag }}
      package_name: ${{ steps.read.outputs.package_name }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
          components: rustfmt, clippy
          # ↓ wasm crate 必须加 (euv / euv-docs / euv-ui / euv-app)
          targets: wasm32-unknown-unknown
      - uses: actions/cache@v3
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            target
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
      - run: cargo install toml-cli
      - uses: actions/cache@v3
        with:
          path: ~/.cargo/bin/toml
          key: toml-cli-${{ runner.os }}
      - id: read
        run: |
          VERSION=$(toml get Cargo.toml package.version --raw)
          PACKAGE_NAME=$(toml get Cargo.toml package.name --raw)
          echo "📦 Detected package: $PACKAGE_NAME v$VERSION"
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "tag=v$VERSION" >> $GITHUB_OUTPUT
          echo "package_name=$PACKAGE_NAME" >> $GITHUB_OUTPUT

  check:                            # cargo fmt --check
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
          components: rustfmt
      - run: cargo fmt -- --check

  tests:                            # cargo test --all-features
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
          targets: wasm32-unknown-unknown       # wasm crate 加这行
      - run: cargo test --all-features -- --nocapture

  clippy:                           # cargo clippy --all-features
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
          components: clippy
      - run: cargo clippy --all-features

  build:                            # cargo check --release (wasm target 加这行)
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: stable
          targets: wasm32-unknown-unknown       # wasm crate 加这行
      - run: cargo check --release --all-features

  publish:                          # cargo publish --allow-dirty
    needs: [setup, check, tests, clippy, build]
    if: needs.setup.outputs.tag != ''
    runs-on: ubuntu-latest
    outputs:
      published: ${{ steps.publish.outputs.published }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache@v3
        with:
          path: ~/.cargo/bin/toml
          key: toml-cli-${{ runner.os }}
      - id: publish
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
            echo "📦 Crates.io: [https://crates.io/crates/$PACKAGE_NAME/$VERSION](...)"
            echo "📚 Docs.rs: [https://docs.rs/$PACKAGE_NAME/$VERSION](...)"
          else
            echo "❌ Publish failed"
          fi

  release:                          # git tag + gh release create + 源码 zip/tar
    needs: [setup, check, tests, clippy, build]
    permissions:
      contents: write
      packages: write
    if: needs.setup.outputs.tag != ''
    runs-on: ubuntu-latest
    outputs:
      released: ${{ steps.release.outputs.released }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: package_info
        run: echo "package_name=${{ needs.setup.outputs.package_name }}" >> $GITHUB_OUTPUT
      - id: check_tag
        run: |
          if git tag -l | grep -q "^${{ needs.setup.outputs.tag }}$"; then
            echo "tag_exists=true" >> $GITHUB_OUTPUT
          else
            echo "tag_exists=false" >> $GITHUB_OUTPUT
          fi
          if git ls-remote --tags origin | grep -q "refs/tags/${{ needs.setup.outputs.tag }}$"; then
            echo "remote_tag_exists=true" >> $GITHUB_OUTPUT
          else
            echo "remote_tag_exists=false" >> $GITHUB_OUTPUT
          fi
      - id: check_release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if gh release view "${{ needs.setup.outputs.tag }}" > /dev/null 2>&1; then
            echo "release_exists=true" >> $GITHUB_OUTPUT
          else
            echo "release_exists=false" >> $GITHUB_OUTPUT
          fi
      - id: release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
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
            gh release edit "$TAG" \
              --title "$TAG (Updated $(date '+%Y-%m-%d %H:%M:%S'))" \
              --notes "Release $TAG ..."
            gh release upload "$TAG" "${PACKAGE_NAME}-${VERSION}.zip" "${PACKAGE_NAME}-${VERSION}.tar.gz" --clobber
          else
            if [ "${{ steps.check_tag.outputs.remote_tag_exists }}" = "false" ]; then
              git tag "$TAG"
              git push origin "$TAG"
            fi
            gh release create "$TAG" \
              --title "$TAG (Created $(date '+%Y-%m-%d %H:%M:%S'))" \
              --notes "Release $TAG ..." \
              --latest
            gh release upload "$TAG" "${PACKAGE_NAME}-${VERSION}.zip" "${PACKAGE_NAME}-${VERSION}.tar.gz"
          fi
          echo "released=true" >> $GITHUB_OUTPUT
```

## 3. 关键参数说明

### 3.1 `if: needs.setup.outputs.tag != ''`

只有当 Cargo.toml 有 version 时才 publish / release。**幂等性**:已经发布过的版本,cargo publish 会失败(版本冲突),但 release job 会识别 tag 已存在 → 走 update 分支,不重复 create。

### 3.2 `cargo publish --allow-dirty`

publish job 在独立的 `actions/checkout@v4` step(没传 `clean` 字段)→ 默认 checkout 含 working tree,有可能未提交改动 → `--allow-dirty` 让 publish 继续。**安全前提**:publish job 是 sequential 在 setup/check/tests/clippy/build 之后跑(都是干净 master HEAD),实际触碰到 dirty working tree 的概率极低;但 `allow-dirty` 是 hyperlane / euv 共用的兜底。

### 3.3 wasm crate 必须加 `targets: wasm32-unknown-unknown`

`cargo check --release --all-features` 默认走 host target。wasm crate 在 host target 下编译会**报错**(e.g. `wasm-bindgen` 引用 `wasm32` 内置类型)。**所有 setup/tests/build 步骤的 `dtolnay/rust-toolchain` 都必须加 `targets: wasm32-unknown-unknown`**。

### 3.4 `permissions: contents: write, packages: write` 仅 release job

GH_TOKEN 默认是 read-only。`release` job 额外加 `contents: write`(push tag) + `packages: write`(理论上 crates.io 发布需要,实际上 CARGO_REGISTRY_TOKEN 是独立 secret)。其他 6 个 job 用默认 read-only 即可。

## 4. 必填 secret

| Secret | 用途 | 来源 |
|---|---|---|
| `CARGO_REGISTRY_TOKEN` | crates.io publish token | https://crates.io/settings/tokens 创建 |
| `GITHUB_TOKEN` | gh CLI + git push tag | Actions 默认 |

**owner 一次性配置**:`Settings → Secrets and variables → Actions → New repository secret`,粘 crates.io token。mono-org 所有 crate 仓共用同一个 token。

## 5. 复用到 euv-docs / 其他 wasm crate 的 PR diff

euv-docs 上游 master (2026-09-18 `6c62600`) 已有 `daily-deploy.yml` + `deploy.yml` + `pages.yml`,但**缺 release pipeline**。本会话开的 PR #40 (https://github.com/euv-dev/euv-docs/pull/40) 添加 `.github/workflows/rust.yml`,改动:

```diff
+ .github/workflows/rust.yml  (新增 255 行 — 上文完整 7-job 模板)
- Cargo.toml: publish = false   (删除 1 行 — 必须让 cargo publish 真的能跑)
```

PR body 必填内容:

```markdown
## Summary

Align `euv-docs` release pipeline with `hyperlane-dev/hyperlane`'s
`.github/workflows/rust.yml`.

## Pipeline (mirrors hyperlane)
- setup, check, tests, clippy, build, publish, release

## Differences from hyperlane
- `wasm32-unknown-unknown` target added to setup steps (euv-docs builds cdylib)
- single Cargo.toml — no workspace member iteration

## Cargo.toml change
Drop `publish = false` so the publish job can run.

## Required secrets (one-time setup)
- `CARGO_REGISTRY_TOKEN` — crates.io publish token
```

## 6. 验证步骤

合并 PR 后:

```bash
# 1. 触发 master push 跑全流水线
#    (PR merge → squash commit on master → workflow 自动跑)
gh run watch <run-id> --repo euv-dev/euv-docs

# 2. 验证 crates.io 上有新版本
cargo search euv-docs --limit 3
# → euv-docs = "0.1.6"    # 旧版本
# → euv-docs = "0.1.7"    # 新版本(如果 bump 了)

# 3. 验证 GitHub Release + tag 存在
gh release list --repo euv-dev/euv-docs --limit 3
# → v0.1.7   Published ... Latest

# 4. 验证 docs.rs 文档生成
curl -sI https://docs.rs/euv-docs/0.1.7/euv_docs/
# → HTTP 200 (首次构建可能 5-10 分钟)
```

## 7. 复用模式决策树

新仓需要 release pipeline?问以下问题:

| 场景 | 用 rust.yml | 不需要 |
|---|---|---|
| 单 crate workspace,cdylib/rlib/bin 都发布 | ✓ | |
| monorepo 多 crate,每 crate 独立发布 | ✓ 但需改 `setup` job 遍历 `[workspace] members` | |
| 内部 CLI 工具,只本仓库用 | | ✓ 用本地 `cargo install --path` |
| 前端 npm 包 / Python 库 | | ✓ 用对应生态(node.yml / python-publish.yml) |
| GitHub Pages + wasm 构建 + 部署 + 发布 | ✓ rust.yml + pages.yml 共存 | |

euv / euv-docs / euv-app / hyperlane / hyperlane-time / hyperlane-log / hyperlane-macros / hyperlane-broadcast / hyperlane-utils / hyperlane-plugin-websocket / hyperlane-ai / hyperlane-cli / hyperlane-mcp-upload 全部适合本模板(全部 cdylib + workspace 结构)。

## 8. 已知坑

1. **CI `publish` job curl verify exit 35 → script 中断 → 阻断 release job**:`set -e` 下 post-publish verify 的 curl 报错导致整个 publish job failure → release job 因 `needs.publish.result == 'success'` 被跳过 → tag + GitHub Release 缺失,即便 crates.io 上传成功。修法 = verify curl 末尾加 `|| echo "000"` (参考 `references/minor-bump-ci-red-by-design.md` §"CI publish job 假失败")
2. **`sync_workspace_version` job 失败 / 与 cargo 缓存 race condition**:monorepo 用独立的 sync job,rust.yml 之外的 workflow;若 sync fail 可手动直推 master
3. **`gh pr merge` 走 GraphQL 失败**(GH_TOKEN 缺 `read:org` scope):用 `curl PUT .../pulls/N/merge` REST 替代
4. **Cargo workspace 多个 crate 各自发布**:本模板只 publish 根 Cargo.toml 的 crate;monorepo 需扩展 setup job 让其循环 `[workspace] members` 每个 crate 一份(本仓不展开)

## 9. 关联 references

- `references/minor-bump-ci-red-by-design.md`(§"CI publish job 假失败" 直接相关)
- `euv-standards/SKILL.md` §17(euv 自身的 sync_workspace_version + bump 铁律)
- `euv-standards/SKILL.md` §12 坑表行"下游工具仓 engine 版本 pin"(rust.yml deploy 引用 euv-docs 时必须 pin 绝对 SHA)
- `github-pr-workflow` skill(PR 流程相关的 REST 绕道)