# euv-docs CLI 在外部 Pages 仓作为构建引擎 (GitHub Actions 模式)

> 2026-09-19 docs-pages 部署从 `euv-dev/euv-docs` 仓 (retired) 切换到 `euv-dev/euv` 仓 `euv-docs` 子包的过程。本文件记录外部 Pages 消费 euv-docs CLI 时的 Cargo install / build.rs 协作陷阱。

## 1. euv-docs CLI 的工作模式

```
cargo install --git <URL> --branch <branch> --bin euv-docs --force
    → 安装 binary `euv-docs` (从上游 build.rs codegen 出 DocsSite 常量)
↓
euv-docs <SRC_DIR> --out <OUT_DIR> --index-html <TEMPLATE>
    → <SRC_DIR> 内 **所有 *.md** 进 wasm SPA route
    → <SRC_DIR>/public/** 自动复制到 <OUT_DIR>/ 根
    → <SRC_DIR>/../README.md frontmatter 提供 site + locales (0.2.0+)
    → <SRC_DIR>/README.md frontmatter 提供 home page actions/features
```

binary 是 build-time tool (产物是 WASM SPA),**用户 build 站时 cargo install 后只需 `euv-docs <SRC_DIR> --out www`**,无须 rust toolchain。

## 2. `cargo install --git URL --bin <name>` 的 package 解析陷阱 (5 次踩坑)

**坑**:`cargo install --git URL --bin euv-docs --force` 当 git repo 包含多个 Cargo.toml (e.g. euv monorepo 有 `cli/Cargo.toml` + `euv-docs/Cargo.toml`) 时,cargo 会报:

```
error: multiple packages with binaries found: euv-cli, euv-docs.
When installing a git repository, cargo will always search the entire
repo for any Cargo.toml. Please specify a package, e.g.
`cargo install --git https://github.com/euv-dev/euv euv-cli`.
```

**5 种错误尝试** (实测,全部失败):

| 命令 | 错误 |
|---|---|
| `cargo install --git URL --bin euv-docs` | "multiple packages with binaries found" |
| `cargo install --git URL -p euv-docs --bin euv-docs` | `unexpected argument '-p' found. tip: to pass '-p' as a value, use '-- -p'` (因为 `-p` 是 cargo build 的 flag;install flag 列表里没有) |
| `cargo install --git URL --branch master euv-docs` | 工作 ✓ (下面正解) |
| `cargo install --git URL euv-docs` | 工作 ✓(无 --branch 也行,cargo 默认走 default branch;但生产必须显式 --branch 锁定) |
| `cargo install --git URL --branch master --bin euv-docs` | 失败 (cargo install 的 `--bin` 期望全局 crate 名字而非单 bin) |

**正解**(`cargo install --git` 的 flag 顺序坑 — 包名是位置参数,不是 `-p`):

```bash
cargo install --target-dir /tmp/euv-docs-target \
    --git https://github.com/euv-dev/euv \
    --branch master \
    euv-docs \                # ← 包名,作为位置参数放在所有 flag 之后
    --bin euv-docs \
    --force
```

注:`--bin euv-docs` 仍需保留 (即使 binary 名 = crate 名) — cargo install 的 `--bin` 含义是"从该 crate 的多个 binary 中选这一个"(euv 仓 euv-docs 子包只有一个 binary,所以不冲突但 cargo 不知道)。

## 3. `euv-docs` build.rs 的相对路径解析 — **安装 vs build 必须共享 src_dir**

**坑**:`build.rs` 在 `<SRC_DIR>/../README.md` 找 site config (`load_config_from_readme`),这是**相对路径**。`EUV_DOCS_SRC_DIR` env var 决定 `<SRC_DIR>`。

**错误时序**(实测 4 次踩坑):

| 时序 | 错误 |
|---|---|
| `cargo install` → `cargo build` (无 fetch step) | build.rs panic: `site-level config (site + locales) missing from <SRC_DIR>/../README.md frontmatter` —— 因为 install 时 `EUV_DOCS_SRC_DIR` 默认 = manifest_dir/docs = `euv-docs/docs/`,但 `<SRC_DIR>/../README.md` 指向 `~/.cargo/git/checkouts/euv-docs-XXXXXX/euv-docs/README.md`,**上游 euv-docs README.md 含 site config ✓** 应该 OK,但**build 时 `EUV_DOCS_SRC_DIR` 设的是 docs-pages 仓的 `<src>/docs/`** (绝对路径) → `../README.md` 指向 docs-pages 仓根 (无 frontmatter) → panic。 |
| fetch 仓 → `cargo install` → `cargo build` (fetch 与 install 间) | install 时 build.rs 同样 panic,因 EUV_DOCS_SRC_DIR 仍指向 docs-pages 仓的 `<src>/docs/`(install step 的 env 还没轮到 fetch 后生效)。 |
| fetch 仓 → `cargo install` 用正确 EUV_DOCS_SRC_DIR → `cargo build` 用 docs-pages 仓 docs | OK ✓ |

**正解**(GitHub Actions 顺序,5 steps):

```yaml
- name: Install euv-cli
  run: cargo install euv-cli

- name: Install wasm-pack
  run: curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh

- name: Fetch euv monorepo  # ← 必须在 install 之前
  uses: actions/checkout@v4
  with:
    repository: euv-dev/euv
    ref: master
    path: __euv_mono
    sparse-checkout: cli   # ← 含 cli/README.md frontmatter (site config) + cli/docs/

- name: Install euv-docs CLI (binary)
  env:
    EUV_DOCS_SRC_DIR: ${{ github.workspace }}/__euv_mono/cli/docs
  run: cargo install --target-dir /tmp/euv-docs-target \
      --git https://github.com/euv-dev/euv --branch master \
      euv-docs --bin euv-docs --force

- name: Build site (euv-docs → www/)
  run: euv-docs ${{ github.workspace }}/docs --out ${{ github.workspace }}/www --index-html template.html
```

**关键 invariant**:`EUV_DOCS_SRC_DIR` 必须是 **绝对路径**,不能用相对路径 (因 GitHub Actions `working-directory` 不可靠)。`${{ github.workspace }}/...` 必填。

**为什么 install 时也需 EUV_DOCS_SRC_DIR**:`cargo install --git URL` 会跑 build script,build.rs 会尝试 `load_config_from_readme(&docs_dir)`,即使最终用户用不同的 SRC_DIR 调用 binary。install 时的 docs_dir 也要含 site config(可以是 binary 自己的 demo docs + README.md)。

## 4. `euv-docs` binary 硬性 config.toml 检查已弃 (0.2.0+)

**坑**:`euv-docs/src/bin/euv-docs/fn.rs` 之前检查 `<SRC_DIR>/config.toml` 必须存在,否则直接 return Err。新工作流 site config 在 `<SRC_DIR>/../README.md` frontmatter(`docs/README.md` 不再含 config.toml),binary 必须支持 "config.toml 缺失但 parent README.md frontmatter 有 site config" 的场景。

**Fix**(`fn.rs`):

```rust
// 旧(0.1.7):
if !src_dir.join(CONFIG_FILE_NAME).is_file() {
    return Err(format!(
        "source directory is missing {}: {}",
        CONFIG_FILE_NAME, src_dir.display()
    ));
}

// 新(0.2.0+):
if !src_dir.join(CONFIG_FILE_NAME).is_file() {
    eprintln!(
        "euv-docs: note: {} not found at {}, falling back to parent README.md frontmatter",
        CONFIG_FILE_NAME, src_dir.display()
    );
    // fall through to build.rs::load_config_from_readme
}
```

`build.rs` 的 `load_config_from_readme` 仍读 `<SRC_DIR>/../README.md` (yaml frontmatter),是真正的 site config source。`config.toml` 是 deprecated 兼容性 fallback。

## 5. euv-docs binary 在 GitHub Pages 仓消费时的数据流

```
docs-pages/docs 仓(本仓)
├── docs/                    ← <SRC_DIR> = build 时 euv-docs CLI 吃这里
│   ├── README.md            ← home page frontmatter (actions, features)
│   ├── catalog.md           ← /catalog.html route
│   ├── appreciate.md        ← /appreciate.html route
│   ├── public/              ← static assets (PNG/SVG/audio/css)
│   │   └── img/*.png        ← 自动复制到 www/img/*.png
│   └── ...
├── README.md                ← 顶部加 frontmatter 含 site + locales
│                                 (build.rs::load_config_from_readme 读这)
├── template.html            ← 含 <base href="./"> 的 index.html 模板
├── build.sh                 ← local wrapper(可选,CI 不依赖)
└── .github/workflows/deploy.yml
```

**文档路由格式**:`link: /catalog.html` 而非 `link: /catalog`。`find_page` 在 binary 里用 `route.ends_with('/') || route.ends_with(".html")` 区分,frontmatter link 必须带 `.html` 才能正确路由。

## 6. 部署后 CDN 验证 — wait + buster + 多个 sanity check

deploy `git push origin gh-pages` 后,GitHub Pages CDN 传播需要 ~30-60s。验证模式:

```bash
# 1. 看 build run 的 conclusion
gh run view <run-id> --repo docs-pages/docs --json conclusion,status

# 2. 等 last-modified 推进 (而不是立即返回)
for i in {1..30}; do
    TS=$(date +%s)
    MT=$(curl -sI "https://docs-pages.github.io/pages/pkg/euv_docs_bg.wasm?cb=$TS" \
         | grep -i last-modified | tr -d '\r')
    echo "t+${i}0s: $MT"
    [ -n "$MT" ] && [[ "$MT" =~ 2026 ]] && break
    sleep 10
done

# 3. cache bust 必加 (CDN 边缘缓存可能命中旧版本)
curl -sI "https://docs-pages.github.io/pages/pkg/euv_docs_bg.wasm?nocache=$TS"
curl -sI "https://docs-pages.github.io/pages/img/logo.png?nocache=$TS"
```

**陷阱**:chrome 浏览器自身的 wasm cache (`--user-data-dir`) 会命中旧版,即使 CDN 已更新;重测必须开新 chrome-data dir:

```bash
nohup ungoogled-chromium \
    --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
    --remote-debugging-port=9222 --remote-allow-origins='*' \
    --user-data-dir=/tmp/chrome-data7 \
    about:blank > /tmp/chrome.log 2>&1 &
```

## 7. force-push euv monorepo master from local (admin escalation)

**场景**:本地 commit chain 含 N 个 commits 想一次合并到 upstream monorepo master (e.g. euv 仓 eastspire 是 admin 但默认走 PR flow;PR review 可能被 hold)。

**流程**:

```bash
cd ~/github/euv-dev/euv
git fetch upstream master
git rebase upstream/master   # 如果 diverged (ahead X / behind Y)
git push --force euv-dev HEAD:refs/heads/master   # 强制 push 用 explicit refspec

# 注意: 用 explicit "HEAD:refs/heads/master" 避免 force-with-lease
# 在 squash-merge 后误判 "Everything up-to-date" (git remote/local SHA 不同)
```

**GitHub branch protection**:force-push 可能触发 "branch requires linear history" / "PR review required" 等规则。如果 upstream 是 admin-owned,需要先 disable branch protection 或用 admin token push 直推。

## 8. euv-docs monorepo migration 完整 audit(2026-09-19 PR #237)

把 `euv-dev/euv-docs` 仓整个 import 到 `euv-dev/euv` 仓 `euv-docs/` 子包 (workspace-excluded):

| Source 文件 | Target 文件 | 注意 |
|---|---|---|
| `euv-docs/Cargo.toml` | `euv-docs/Cargo.toml` | `version = "0.1.7"` 保持(sync workflow 会自动 bump) |
| `euv-docs/build.rs` | `euv-docs/build.rs` | 改 config.toml 读取 → README.md frontmatter 读取 (PR #237 主要改动) |
| `euv-docs/src/bin/euv-docs/` | `euv-docs/src/bin/euv-docs/` | `euv_docs` rename `euv-docs` (rust-standards §1.4 关键字文件名 kebab-case) |
| `euv-docs/src/component/...` | `euv-docs/src/component/...` | 不动 |
| `euv-docs/template.html` | `euv-docs/template.html` | 不动 |
| `docs-pages/docs/docs/` | `euv/cli/docs/` | 全 content tree 复制 (CLI docs lives in cli/) |
| `euv-docs/docs/` (demo) | `euv-docs/docs/` (workspace 仓内部) | 保留 cargo clippy 跑通(默认 EUV_DOCS_SRC_DIR = manifest_dir/docs),只是 frontmatter 必要 |

**workspace exclude 必要性**:`euv-docs` 在 monorepo root `Cargo.toml` 的 `[workspace]` 加 `exclude = ["euv-docs", ...]`,因为:

1. `euv-docs/Cargo.toml` 仍写 `euv = "0.18"` (与 workspace root `euv = "0.24.5"` 不兼容 — `framework-engine-version-pin-rule` 说的就是这个)
2. 强制 sync workspace deps 会 float euv-docs 的 euv dep 到 0.24.x → CSS safe-area mismatch

`exclude` 阻 cargo workspace 把 euv-docs 当成员,publish/sync workflow 单独处理它(在 `sync_workspace_version` job 加 euv-docs/Cargo.toml path,见 `crates-io-release-pipeline-template.md`)。

## 9. 关联 references

- `euv-standards/SKILL.md` §17 + `references/framework-engine-version-pin-rule.md` —— pin 0.18 理由
- `euv-standards/references/crates-io-release-pipeline-template.md` —— release pipeline 7-job 结构 + sync_workspace_version 加 euv-docs
- `rust-standards/references/audit-pitfalls.md` §38 —— `cargo fmt --check` rustfmt 版本 skew (CI vs local)
- `rust-standards/references/audit-pitfalls.md` §39a —— `build.rs` 是 cargo convention,豁免 §1.3a keyword purity