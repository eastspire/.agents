# euv-docs CLI positional path resolution — investigation transcript

> **Why this file exists**: Captures the multi-hour debugging session for
> "deployments show euv-docs starter template instead of user's docs/"
> so future agents don't repeat the same investigation when they hit
> the same symptom.

## Symptom (the actual user complaint)

> 部署之后,内容是默认模板,不是我真实文档

- workflow 全绿、Pages 部署成功、index.html 字节正常、wasm binary 体积正常(>400KB)
- 但浏览器打开 `https://<user>.github.io/<repo>/` 显示 **euv-docs 框架默认首页**:
  - `<title>docs-euv</title>`
  - `description = "docs-pages (VuePress) migrated to euv-docs engine, compiled to WebAssembly."`
  - 不包含用户的 essay/posts/private 内容

## Investigation steps that DID NOT solve it (false leads)

These were tried and ruled out. Do NOT repeat them.

1. **"是 EUV_DOCS_SRC_DIR 没设对"** — 设成 `${{ github.workspace }}/docs`,build log 显示 `EUV_DOCS_SRC_DIR: /home/runner/work/docs/docs/docs`,看起来对。**实际**:env var 在 euv-docs CLI 内部被 positional 覆盖(见下)。
2. **"是 EUV_DOCS_OUT_DIR 没设对"** — 设成 `${{ github.workspace }}/www`,产物路径变了,但 wasm 内容仍是 starter。**实际**:OUT_DIR 控制产物路径,不控制 wasm 内容。
3. **"是 cargo install 没重 build"** — 加 `--target-dir /tmp/euv-docs-target` 强制新 target dir,install 阶段的 `docs_gen.rs` 重生成,内容含 essay/posts。**但 wasm-pack 内部 cargo build 仍用 euv-docs crate 自己的 wasm32 target**(不是 install target),继续命中 cache。
4. **"是 build.rs panic 没暴露"** — 实际 build.rs 没 panic,因为它**成功读到 euv-docs crate 自带 starter docs/**(而不是用户的 docs/)。完全没有 error。
5. **"是 wasm-pack 不传 EUV_DOCS_SRC_DIR"** — 实测 wasm-pack 子进程 `/proc/<pid>/environ` 没有 EUV_DOCS_SRC_DIR(被 euv-cli 链路丢了)。**但即便传过去也没用**,因为 euv-docs crate 自带 starter docs 是**绝对存在的**(不是 fallback)— cargo build 拿到 env 后解析到 `<euv-docs-crate-manifest-dir>/docs` = 真的 starter docs/。

## The actual root cause (euv-docs CLI design issue)

`euv-docs` crate 的 `src/bin/euv_docs/fn.rs:67-127`:

```rust
let src_dir: PathBuf = positional
    .into_iter()
    .next()
    .ok_or_else(|| "missing required <SRC_DIR> argument".to_string())?;  // line 67-70
...
let src_dir: &Path = args.get_src_dir().as_path();  // line 83
...
command.env(EUV_DOCS_SRC_DIR_ENV, src_dir);  // line 127: src_dir 原样传给 euv build
```

**euv-docs CLI 不会 resolve positional 成绝对路径**,直接 forward 给 euv build。

但 `build.rs` 收到 `EUV_DOCS_SRC_DIR=docs`(相对),`PathBuf::from("docs")` 后 join 的是 **cargo 的 cwd = euv-docs crate manifest_dir**(cargo 在那个目录跑 `cargo build`),不是用户的 cwd。

`euv-docs` crate git checkout 在 `/root/.cargo/git/checkouts/euv-docs-*/6c62600/`,**自带 starter docs/ 子目录**(被 git ignore 但源码里就是有,包含 config.toml + 5 个 guide 页面 + README)。build.rs 编译的是这个 starter,**永远不是用户的 docs/**。

## Local diagnostic that confirmed it

```bash
# 1. 拉已部署 wasm binary
TOKEN=$(grep -oP 'export GH_TOKEN="\K[^"]+' /root/.bashrc.d/gh_token.sh)
gh api repos/docs-pages/pages/contents/pkg/euv_docs_bg.wasm?ref=gh-pages \
  -H "Accept: application/vnd.github.v3.raw" -o /tmp/deployed.wasm

# 2. grep 用户独有的字符串(essay/posts 标题)
python3 -c "
with open('/tmp/deployed.wasm','rb') as f: d=f.read()
for needle, label in [(b'essay','essay'), (b'06-09','06-09'), (b'\xe9\x9f\xa9\xe5\x9b\xbd','韩国'), (b'docs-euv','docs-euv')]:
    print(label, ':', d.count(needle))
"

# BEFORE fix (EUV_DOCS_SRC_DIR 设为相对 'docs'):
#   essay : 0
#   06-09 : 0
#   韩国  : 0
#   docs-euv : 2  ← 只 starter 有,用户 docs 没有

# AFTER fix (positional + EUV_DOCS_SRC_DIR 都用绝对路径):
#   essay : 75  ← 用户 docs essay 出现 75 次
#   06-09 : 25
#   韩国  : 4
#   docs-euv : 2  ← 用户 config.toml 写的 title="docs-euv"
```

## The fix (verified working)

```yaml
# .github/workflows/deploy.yml — Build step
- name: Build site (euv-docs → www/)
  # 关键: positional 也是绝对路径(不是 "docs")
  # 跟 EUV_DOCS_SRC_DIR env var 都用绝对路径,因为 euv-docs CLI
  # 用 positional 覆盖 env,所以 positional 必须绝对
  run: euv-docs ${{ github.workspace }}/docs --out ${{ github.workspace }}/www --index-html template.html
```

不要写:

```yaml
# ❌ relative positional + 显式 env var(看起来对,实际仍指向 starter)
env:
  EUV_DOCS_SRC_DIR: ${{ github.workspace }}/docs
run: euv-docs docs --out www --index-html template.html
```

## Why this is hard to spot

`docs/config.toml` 里的 title/description 如果正好是 `euv-docs` 自带的默认值("docs-euv" / "A VuePress-style documentation site powered by euv + euv-ui"),用户改 docs/ 后这些字段值不变 = 部署后看起来"对"的概率高,**但 wasm 里仍没用户 essay/posts/私有文章内容**。

**唯一硬指标**:grep 用户独有的内容字符串(essay 标题、posts 标题、`<user-specific-string>`)。0 hits = 还是 starter。

## What a fix to euv-docs upstream should look like (for reference)

```rust
// euv-docs/src/bin/euv_docs/fn.rs:67-70 — 应改成 resolve 成绝对路径
let src_dir: PathBuf = positional
    .into_iter()
    .next()
    .ok_or_else(|| "missing required <SRC_DIR> argument".to_string())?
    .canonicalize()  // ← 加上这一行,resolve 成绝对路径
    .unwrap_or_else(|_| /* error */);
```

但这是 upstream change,要等 fork `eastspire/euv-docs` 后合并。

## Cleanup checklist after fix lands

1. **改 `docs/config.toml` 标题/描述**:用户当前用的是 starter title/description(因为 build 出 starter 后改也来不及),改成本站的真实信息。
2. **commit + push**:触发新一轮 CI build。
3. **再 grep 一次 deployed wasm**:确认用户独有内容出现。
4. **触发 ltpp.vip 镜像同步**(坑 9):`scripts/sync-pages.sh docs-pages/pages`。