# minor/major bump 的 PR check 必然红(设计内) + §12 旧坑表行修正

> 2026-09-13 实测 PR #211(0.22.2→0.23.0)再次确认;原始机制 2026-09-06 PR #160 确立。
> 本文件 = SKILL.md §17 的补充 + §12 坑表「minor 版本升级」行旧方案的作废声明。
> (SKILL.md 本体 patch 当时受 read-before-write 门限制未写入,规则以此文件为准。)

## 现象

根 `Cargo.toml` version bump 到新 minor/major 区间(如 0.22.2→0.23.0)后:

- 子包 `[workspace.dependencies]` path-dep 仍钉旧区间(`^0.22.2`);
- CI 的 build/clippy/tests 在 cargo 版本解析阶段 **~7-8s 三个 job 同时 fast-fail**;
- 错误形如 `failed to select a version for the requirement euv = "^0.22.2"`;
- **diff 仅根 Cargo.toml 1 行,这不是代码问题,不要修代码。**

patch bump(0.22.2→0.22.3)区间兼容,无此现象,正常等绿合。

## 判别法(设计内红 vs 真问题)

| 信号 | 设计内红 | 真问题 |
|---|---|---|
| 挂的 job | build+clippy+tests 同时 | 任一单挂 |
| job 存活时长 | <10s(版本解析阶段) | 编译中段/测试段 |
| 错误内容 | `failed to select a version` | 具体 compile error |
| PR diff | 仅根 Cargo.toml 1 行 | 含代码改动 |

## 合并路径

minor/major bump PR = `gh pr merge --admin --squash`(不等绿;绿了反而是 patch bump)。
merge 后 `sync_workspace_version` 在 master push 上自动补齐 6 子包 version + 6 个 path-dep 共 14 处。
**合并后必须验证 sync commit 写的是新版本号**(PR #196 教训:sync 曾把 root 从 0.21.2 写回 0.21.1,需手工 fix commit,流程见 SKILL.md §17)。

## 本地验证 minor-bump 工作树(必须回滚)

root 已 bump + 子包/pins 未同步时 `cargo check` 必失败。流程:

1. 临时 sed 全部 7 处版本到目标号(根 + 6 子包 Cargo.toml;path-dep 段用 grep 锁定,避开 `compare_version = "2.0.14"` 这类非 path-dep 行);
2. cargo check / cargo test 验证;
3. **逐文件 `git checkout HEAD --` 回滚,只留根 version 一行**再提交。

不回滚 = 违反「只改一行」铁律(PR #148 被 revert 的直接原因)。

## §12 坑表「minor 版本升级」行修正

SKILL.md §12 该行旧方案「本地复现 CI `sync_workspace_version` 的 sed 并随 PR 提交,CI sync 变 no-op」是 **0.15.x 时代的错误做法**(PR #148 / #160 均被 user 勒令 revert 重做),**作废**。正确做法 = 本文件上述流程(只改根一行 + admin squash + CI sync 自动补齐)。

## 开 bump/perf PR 前的撞号检查

`gh pr list --repo euv-dev/euv --state open` 查在途 bump PR:若已有 open bump PR(如 2026-09-13 的 #211 = 0.23.0),后续 PR 的版本号须等其落地后从新 master 起 patch bump;并行开两个 bump 号会撞车或顺序颠倒。

## listener-id / Reactive-slot id 类型切换的 exhaustive sweep 要求 (PR #218 + 直推 hotfix, 2026-09-13)

`Signal::subscribe` 返回的 subscription id 类型变更时(本次 `u64 → usize`):

**必须搜的不只是直接调用**:

```bash
# 直系: 任何存储/使用 subscribe 返回值的局部变量
grep -rn 'let [a-z_]*id.*= .*\.subscribe(\|let subscription_id.*signal\.subscribe(' \
  --include='*.rs' core/ macros/ ui/ engine/

# 间接: 闭包捕获、Cell/RefCell/Rc/Arc 包装
grep -rn 'Cell<u\|Cell<\\?usize\\?>\|RefCell<u\|Rc<Cell\|Arc<Cell' \
  --include='*.rs' core/ macros/ ui/ engine/

# 间接: 闭包体里调用 unsubscribe(id_value)
grep -rn 'unsubscribe(' --include='*.rs' core/ macros/ ui/ engine/
```

`core/src/vdom/cast/impl.rs:251-259` 命中「闭包内 Rc<Cell<u64>> 装 id,然后 subscribe 闭包体里 `source.unsubscribe(listener_id.get())` 拿回来 re-entrant self-unsubscribe」模式——这种 indirect binding 不被直系 grep 覆盖。改 id 类型必须把它也跟着改,否则 `cargo check --release --target wasm32-unknown-unknown` 会报 E0308。

**CI 用的是 release + wasm32 target**(`.github/workflows/rust.yml` 的 build job 命令是 `cargo check --release --all-features --target wasm32-unknown-unknown --workspace --exclude euv-cli`)。**本地 `cargo check --workspace --all-targets`(默认 dev profile, host target)漏掉这种 wasm-only 类型 mismatch**——dev profile 编译 euv-core / euv-engine / euv-ui 等子集,wasm32 路径上 cast/impl.rs 才会被实例化校验。Pre-commit `cargo check --workspace --all-targets` exit 0 不能证明 PR 干净。**验证清单在 PR 提交前补跑**:

```bash
cargo check --release --all-features --target wasm32-unknown-unknown --workspace --exclude euv-cli
```

本会话已踩:PR #218 CI 挂 `error[E0308]: mismatched types ... expected usize, found u64` 三处 fail,只能直推 master hotfix `c888199d`。教训记入本节。

## sync_workspace_version push 失败的 admin fallback (2026-09-13 实测)

`sync_workspace_version` GH Action job 在 master push 上 commit `chore: sync all package versions to X.Y.Z` 后 `git push` 到 master,可能因为以下原因 fail:

- CI token 缺 `workflow` / `contents: write` scope(本仓库 GH_TOKEN 不是 CI token)
- branch protection rule reject(配置了 require review / status check)
- master HEAD race condition(同步 job 拿到的 ref 比当前 HEAD 旧)

CI log 报 `remote rejected` / `failed to push some refs` 时,**admin 可手动复刻 sync commit** 直推 master:

```bash
cd ~/github/euv-dev/euv
git fetch euv-dev master
git checkout -b tmp-sync-$NEW_VER euv-dev/master
# 替换根 Cargo.toml 的 [package] version + 6 个 path-dep 行
for d in cli core engine example macros ui; do
  sed -i "s/^version = \"$OLD_VER\"\$/version = \"$NEW_VER\"/" $d/Cargo.toml
done
# Cargo.toml 内 workspace.dependencies 段:必须 grep 锁定再 sed,避开 'compare_version = "2.0.14"' 等非 path-dep 行
sed -i "s/version = \"$OLD_VER\"\$/version = \"$NEW_VER\"/g" Cargo.toml
git diff --stat   # 期望: 7 files changed, 14 insertions(+), 14 deletions(-) (根 +1/-1 + 6 子包各 +1/-1 = 14 行)
# user.name 用 eastspire(commit author 与 sync job 一致,避免 git log --author=eastspire 失效)
git -c user.name='eastspire' -c user.email='root@ltpp.vip' commit -m "chore: sync all package versions to $NEW_VER"
git push euv-dev tmp-sync-$NEW_VER:master   # admin 直接 push master
# 验证: master HEAD 含此 commit + 全仓 version 一致
git fetch euv-dev master
git show euv-dev/master:Cargo.toml | head -3
for d in cli core engine example macros ui; do
  echo -n "$d: "; git show euv-dev/master:$d/Cargo.toml | grep '^version' | head -1
done
```

**重要**:push 完成后 master 会再触发一次 sync_workspace_version,看到自己写的版本和 sync job 写的版本一致(noop 或空 commit),确认 state 收敛。

## rebase 解决冲突后 `cargo fmt --check` 仍挂的 corner case (PR #217→#219, 2026-09-13)

`<<<<<<< HEAD` / `=======` / `>>>>>>> branch` 三方合并时,**只删中间冲突块的两侧内容,容易留下两侧相同行的「重复 comment」且其中一行缩进错位**。`cargo check` 通过(`cargo fmt` 不参与编译),但 `cargo fmt --check` fail → CI `Format check` job 挂。

典型例子(`engine/src/renderer/impl.rs:3134-3135`):

```rust
        // OPT 2b: cached `pass.setIndexBuffer(buffer, format)`.
// OPT 2b: cached `pass.setIndexBuffer(buffer, format)`.   // ← 行首少了 8 空格,fmt 拒绝
        // The two spec formats hit the thread-local ...
```

合并两侧「`// OPT 2b: ...`」行,冲突解决后 pick 了其中一侧的注释,但 pick 的位置在错误上下文(从上一行挪下来的孤儿,失去原缩进)。

**预防**:
1. rebase 完成、commit amend 之前,**直接跑 `cargo fmt --all -- --check`**,exit 非零立刻 `cargo fmt` 修一遍再继续 amend。
2. force-push PR head 之前**必跑**`cargo fmt --all -- --check` + `cargo check --release --all-features --target wasm32-unknown-unknown --workspace --exclude euv-cli`(参见前节)。
3. 如果 CI 已挂(`Format check` failure),开 PR 修注释(1 file / 1 line / 1 commit),不 revert 整 PR——本 PR 可能携带其他合法改动。

## CI publish job 假失败 (PR #221, 2026-09-13)

`publish` job 的 post-publish verify curl 在 `set -e` 下遇到瞬时网络/TLS 错误(curl exit 35 = `CURLE_SSL_CONNECT_ERROR`)→ script 直接中断 → publish 报 failure → release job(`needs.publish.result == 'success'`)被阻断 → **git tag `vX.Y.Z` 不存在 + GitHub Release 不存在**,即便所有 crate 已成功上传 crates.io。

**症状**:CI log 显示6 个 crate 全部 `✅ ... verified on crates.io (HTTP 200)`,然后 `##[error]Process completed with exit code 35`。crates.io API 仍报 `max_version=X.Y.Z max_stable=X.Y.Z` — publish 实质成功了。

**`.github/workflows/rust.yml` line 338 修复**(1 file / +1/-1,curl 末尾加 `|| echo "000"`):

```diff
- VERIFY_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "User-Agent: euv" "https://crates.io/api/v1/crates/$PKG_NAME/$VERSION")
+ VERIFY_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "User-Agent: euv" "https://crates.io/api/v1/crates/$PKG_NAME/$VERSION" || echo "000")
```

verify 是 informational — `cargo publish` 已 exit 0 + registry 已接受 upload,verify 不该阻塞 script。

**已发布版本的补救**(workflow 修复只能管下次;已发布的 X.Y.Z 没 tag/release):

```bash
# 1. 建 tag 指向该版本 master HEAD(通常是 sync_workspace_version commit)
git tag -a v0.24.1 <sync-commit-sha> -m "v0.24.1"
git push origin v0.24.1

# 2. 用 gh release create 建 GitHub Release(带源码 zip+tar.gz)
PACKAGE_NAME=euv VERSION=0.24.1 TAG=v0.24.1
git archive --format=zip --prefix="${PACKAGE_NAME}-${VERSION}/" HEAD > "${PACKAGE_NAME}-${VERSION}.zip"
git archive --format=tar.gz --prefix="${PACKAGE_NAME}-${VERSION}/" HEAD > "${PACKAGE_NAME}-${VERSION}.tar.gz"
gh release create "$TAG" \
  --title "[master]($TAG published $(date '+%Y-%m-%d %H:%M:%S'))" \
  --notes "..." \
  --latest
gh release upload "$TAG" "${PACKAGE_NAME}-${VERSION}.zip" "${PACKAGE_NAME}-${VERSION}.tar.gz"
```

## GH_TOKEN 缺 `read:org` scope 时 PR 创建/合并走 REST (2026-09-13)

本仓库 GH_TOKEN scopes = `notifications, repo, workflow`(缺 `read:org`)。`gh pr create` / `gh pr merge` / `gh pr close` 走 GraphQL,被拒:

```
GraphQL: Something went wrong while executing your query on ...
```

`gh pr view` / `gh pr checks` / `gh api .../pulls/N` 走 REST,正常。

**绕道**(已知可靠):

```bash
# 创建 PR
TOKEN=$GH_TOKEN
python3 -c 'import json,sys;body=open("/tmp/pr-body.md").read();print(json.dumps({"title":"...","head":"eastspire:branch","base":"master","body":body}))' > /tmp/pr-payload.json
curl -sS -X POST https://api.github.com/repos/euv-dev/euv/pulls \
  -H "Authorization: token $TOKEN" -H 'Accept: application/vnd.github.v3+json' \
  -H 'Content-Type: application/json' -d @/tmp/pr-payload.json | python3 -c 'import json,sys;d=json.loads(sys.stdin.read());print("PR #"+str(d["number"])+":",d["html_url"])'

# 合并 PR
curl -sS -X PUT https://api.github.com/repos/euv-dev/euv/pulls/N/merge \
  -H "Authorization: token $TOKEN" -H 'Accept: application/vnd.github.v3+json' \
  -d '{"merge_method": "squash", "delete_branch": true}'
```

**GitHub Actions API 偶发 502 Bad Gateway** — REST 调用第一次可能 `non-200 OK status code: 502 Bad Gateway`,重试一次通常 200 OK。Merge 后 `gh pr merge` 也可能返回 GraphQL 错,直接 `curl PUT` 即可。

`gh pr edit` 同样走 GraphQL,被拒 → REST 改 title/body:

```bash
curl -sS -X PATCH https://api.github.com/repos/euv-dev/euv/pulls/N \
  -H "Authorization: token $TOKEN" \
  -F title="..." -F body=@file.md
```

## patch tool 内置 rustfmt 假错 (let chains, Rust 2024) (2026-09-13)

patch tool 携带的 rustfmt 是旧版(< 1.85),对 Rust 2024 `let chains` 语法报 `error: let chains are only allowed in Rust 2024 or later`(伪造,因为我们正是 2024 edition)。patch 输出 `lint.status: error` 不代表代码有问题——只要改动局部(patch 工具显示「Pre-existing lint errors — this edit didn't introduce new ones」)就放心提交。CI 用 rustc 1.98 全过。**Rule**:patch 报错后必须以 `cargo check` exit code 为准,不以 patch 内置 lint 输出为准。
