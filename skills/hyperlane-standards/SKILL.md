---
name: hyperlane-standards
description: '**hyperlane 框架工作区规范 — 涉及 hyperlane monorepo 跨 crate 操作时加载**。Layer-2 skill,与 `hyperlane`(入口)+ `hyperlane/references/api-*.md`(API 速查)互补。本 skill 只讲跨 crate 的事:`[workspace.package]` 单一版本号 + sync_workspace_version CI job + monorepo 7 crate 互依赖图 + crate-cli 工具分工 + 12 interlocking ecosystem crates + 22 common pitfalls(详见 references/pitfalls.md)+ version bump 铁律 + monorepo publish 顺序。**版本号查根 `Cargo.toml` `[workspace.package] version`**(skill 不维护版本信息)。**当且仅当任务不涉及 hyperlane monorepo 跨 crate 操作**(纯写 Server / 纯写 hook / 纯写 client)才不需要加载本 skill,直接用 `hyperlane` 入口 + `hyperlane/references/api-*.md`。**当且仅当任务完全不使用 hyperlane**才不需要加载。'
license: MIT
---
# hyperlane-standards — Monorepo 跨 crate 规范

> **本 skill 只讲 hyperlane monorepo 跨 crate 操作**(workspace / 版本 / 工具 / CI / publish)。具体的 `Server` / `Context` / `Hook` / `Route` / `Config` API 在 `hyperlane/references/api-core.md`,77 个 proc_macro 在 `hyperlane/references/api-macros.md`,HTTP 类型(`Request` / `Response` / `Method` / `Status` / `Stream` / `Cookie` / `WebSocketFrame` 等)在 `hyperlane/references/api-type.md`,客户端在 `hyperlane/references/api-request.md`,22 个常见坑 consolidated 在 `hyperlane/references/pitfalls.md`。

---

## Index

| I want to... | Jump to |
| --- | --- |
| See which other skills must load with this one | [Mutual-Lock Skills](#0-mutual-lock-skills) |
| Check crate name / version / edition / license | [Project Metadata](#1-project-metadata) |
| Add `hyperlane` to `Cargo.toml` | [Installation](#2-installation) |
| See the 5-line minimum call to start a server | [5-Line Minimum Call](#3-5-line-minimum-call) |
| Avoid the 22 most common gotchas | [22 Common Pitfalls](#4-22-common-pitfalls) |
| Pick an ecosystem crate to extend hyperlane | [12 Interlocking Ecosystem Crates](#5-12-interlocking-ecosystem-crates) |
| Work with the monorepo / path-deps / publish order | [Monorepo Layout & Internal Deps](#6-monorepo-layout--internal-deps) |
| Bump the version of all crates at once | [Version Bump Rule](#7-version-bump-rule) |
| See related/companion skills | [互锁 skill](#8-互锁-skill) |

---

## 0. Mutual-Lock Skills

- **`hyperlane`**(入口) — 互锁指针,任何 hyperlane 任务先命中入口再跳到这里
- **`rust-standards`** — Rust 通用规范,对 hyperlane 同样适用,优先级最高
- 生态 crate 各有独立 skill(http-type / http-constant / lombo-macros 暂无独立 skill,内容内联在本文件)

## 1. Project Metadata

- 仓库: `hyperlane-dev/hyperlane` (single repo, monorepo)
- **Monorepo**(2026-09 起) — **7 个 crate**:
  - `hyperlane` (根) — 纯 re-export shim,`use hyperlane::*` 暴露 core + macros(type 通过 core 间接)
  - `hyperlane-core` — 框架本体: `Server` builder + `Context` + `Hook`/`Route`/`Config` + `http_type::*` 重导出
  - `hyperlane-macros` — proc-macro 集合(`#[route]` 等),独立 proc-macro crate
  - `http-type` — HTTP 类型库: Request/Response/Method/Status/Stream/Context/RouteParams/HttpStatus + concurrent 包装(ArcMutex/BoxRwLock/xxhash 等)
  - `http-compress` — Brotli / Deflate / Gzip 压缩解压(`brotli` + `flate2` 库封装)
  - `http-constant` — HTTP 常量(header 名 / version / MIME / protocol)
  - `http-request` — HTTP / HTTPS 客户端(支持自动 redirect / 解码 / `Proxy` enum)
  - `hyperlane-cli` — 命令行工具(`watch` / `new` / `template` / `help` / `version`;**不再提供** `fmt / bump / publish / sync`,那些走 `crate-cli`)
- 当前版本: 全部 crate 同步发布,单 version 号(查根 `Cargo.toml` `[workspace.package]`;skill 不维护具体值)
- Rust edition: `2024`
- License: `MIT`
- workspace 布局:
  ```
  hyperlane/
  ├── Cargo.toml          # [workspace] + 根 hyperlane re-export 包
  ├── core/               # hyperlane-core
  ├── macros/             # hyperlane-macros (proc-macro)
  ├── type/               # http-type
  ├── compress/           # http-compress
  ├── constant/           # http-constant
  ├── request/            # http-request
  └── cli/                # hyperlane-cli (bin target)
  ```
- 顶层重导出(根 `hyperlane`): `hyperlane_core::*` + `hyperlane_macros::*`
- 关键宏支持: 派生自 `lombok-macros` (`Data`, `New`, `Getter`, `GetterMut`, `Setter`, `CustomDebug`, `DisplayDebug`, `Eq`, `PartialEq`, `Hash`, `Clone`, `Default`)
- profile: `[profile.dev]` + `[profile.release]` 都用 `opt-level = 3`, `lto = true`, `incremental = false`, `panic = "unwind"`, `debug = false`, `codegen-units = 1`, `strip = "debuginfo"`(workspace 根定义一次,子包若重复定义会被 cargo 警告忽略,这是预期行为 — 跟 euv 一致)

### 1.1 版本升级规则(用户说「升级版本」时,hyperlane 全家桶通用)

Monorepo 7 个 crate 共享一个 version 号(查根 `Cargo.toml` `[workspace.package]`;skill 不维护具体值)。bump 时 **只改根 `Cargo.toml` 第 3 行 `[package] version`**,子 crate 的 `[package] version` + `[workspace.dependencies]` path-dep 内的 `version` 一律不动 — 由 CI `.github/workflows/rust.yml` 的 `sync_workspace_version` job 在 master push 上自动 propagate(实际行为:PR 上 sync skipped,master push 上 sync + `chore: sync all package versions to X.Y.Z` 自动 commit)。

**禁止全仓 sed `version = "X.Y.Z"`**(会误伤第三方依赖如 `http-compress = "..."`)。**禁止**手改 7 个子 crate 的 `Cargo.toml` 中的 `version` 字段。

**PR 前 diff stat 自检**:`git diff --stat` 期望只有 1 file + 1 line(根 `Cargo.toml`)。多于 1 file = 停下来,先 `git checkout HEAD -- <额外文件>`。

CI sync 行为: master merge → `sync_workspace_version` job 跑 → 在 master 上追加 `chore: sync all package versions to X.Y.Z` commit → 7 个 `Cargo.toml` + 根 `[workspace.dependencies]` 内 path-dep `version` 全部同步。等这个自动 commit 出现后再认为 release 完成。

**发布前必须手动在本地跑 `crate sync`**(`crate-cli` 提供),因为 PR 上 CI 不跑 sync:
- hyperlane 的 `[workspace.dependencies]` 字段中 path-dep 的 `version` 行,例如 `http-type = { path = "type", version = "X.Y.Z" }`,在 PR merge 时可能 stale,CI publish job 会因 resolver 找不到而失败。
- 解决方案:开 PR 前在本地 `crate sync`(从 `crate-cli` 装的),然后 `git diff --stat` 看到 `Cargo.toml` 外的额外 diff 是预期的,**不要**手改或回退。

(详细跨多 PR 的 release bump 实战见 `references/release-bump-flow.md` — 含 PR #171 + #220 + minor/major patch 的踩坑史)

## 2. Installation

```shell
cargo add hyperlane           # 根 shim + hyperlane-core + hyperlane-macros(transitively)
cargo add hyperlane-macros    # 如果需要直接 #[route] / #[hyperlane] 等 proc-macros
```

`Cargo.toml` 关键依赖(`hyperlane/Cargo.toml`):

```toml
[dependencies]
hyperlane-core = { workspace = true }
hyperlane-macros = { workspace = true }
```

`hyperlane-core/Cargo.toml` 关键依赖(实际框架本体):

```toml
[dependencies]
hyperlane-type = { path = "../type", version = "X.Y.Z" }   # crate 名 http-type,路径仍叫 type/;version 跟 [workspace.package] 同步
http-compress = { path = "../compress", version = "X.Y.Z" }
http-constant = { path = "../constant", version = "X.Y.Z" }
http-request = { path = "../request", version = "X.Y.Z" }

regex = "1.13.1"
inventory = "0.3.24"
lombok-macros = "2.1.0"
serde = { version = "1.0.229", features = ["derive"] }
```

## 3. 5-Line Minimum Call

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[tokio::main]
async fn main() {
    let mut server: Server = Server::default();
    server.route::<Index>("/").await;       // 路由注册是 async,不能链式
    let control: ServerControlHook = server.run().await.unwrap_or_default();
    control.wait().await;
}
```

## 4. 22 Common Pitfalls

> 完整内容已迁移到 `hyperlane/references/pitfalls.md`(consolidated index + 22 核心坑 + 8 monorepo/工具链坑)。本节保留精简版作为快速参考,详细解释 + 修法见 references/pitfalls.md。

1. **路由注册是 async**:`server.route::<T>(path).await` — 不能 `.route().route()` 链式。
2. **response setter 是 sync**:`ctx.get_mut_response().set_xxx()` — 不需要 `.await`。
3. **`ServerControlHook` 有 `Default`**:`server.run().await.unwrap_or_default()` — 不要 `expect`。
4. **不要自己 import `Stream`**:框架的 `Stream` 类型通过 `use hyperlane::*;` 进来,不要跟 `tokio::net::TcpStream` 混。
5. **`inventory::collect!` 框架调用**:**不要**在自己代码里再 `collect!` 一遍,会重复注册。
6. **`#[route]` 来自 `hyperlane-macros`,不是 `hyperlane`**:需要 `use hyperlane_macros::*;`。
7. **`Server` 必须是 `let mut`**:所有注册方法都改 `&mut self`。
8. **`Status::Continue` vs `Status::Next`**:继续走下一个 hook vs 跳到下一阶段(细节查 enum 定义)。
9. **`hook` 函数签名是 `async fn handle(self, ...)`**:它拿 `self` 而非 `&self` — 因为 handler 是一次性的(per-request instance)。
10. **`new` 钩子也拿 `&mut Stream, &mut Context`**:可以在 `new` 里做请求级初始化。
11. **`RouteParams` 是 `HashMap<String, String>`**:注意字符串拥有权。
12. **dynamic segment 必须用 `{name}` 包裹**:写 `/users/:id` 是错的,要 `/users/{id}`。
13. **regex segment 语法是 `{name:pattern}`**:`/users/{id:\\d+}` — **注意双反斜杠**(Rust string literal 转义)。
14. **response body 用 `set_body` 接收 `Into<Vec<u8>>`**:传 `&str` 也行,内部 `.into()`。
15. **`build()` 返回 `Vec<u8>`**:这个返回值通常 `let _ = ...;` 丢掉,因为 setter 已经把 body 写到 `Response` 里。
16. **`server_config()` / `request_config()` 是 sync**:不要加 `.await`。
17. **`config_from_json` 是 sync**:接收 `impl AsRef<str>`,传 `&str` 或 `String` 都行。
18. **Tokio runtime 必须自己起**:`#[tokio::main] async fn main() { ... }` — 框架不自动起。
19. **每个 hook 的 `new()` 每次请求都执行**:**不要**在 `new` 里放 expensive IO,放 `handle` 里。
20. **panics 在 `handle` 里会被 `TaskPanic` hook 捕获**:不要在 `handle` 里 `std::panic::catch_unwind` — 让框架做。
21. **404 / 405 默认走 `RequestError` hook**:如果你没注册 `RequestError` hook,框架会用内置 default(返回空 404 body)。
22. **profile `panic = "unwind"`**:`TaskPanic` hook 才能拿到 panic;`panic = "abort"` 直接 abort 不触发。

## 5. 12 Interlocking Ecosystem Crates

hyperlane monorepo 自带的 7 个 crate + 1 个外部核心依赖 `crate-cli`(跨 monorepo 通用)+ lombok-macros 第三方 + 3 个独立 plugin。

| crate | 用途 | 关系 |
|---|---|---|
| `http-type` | Request/Response/HttpVersion/Status/Stream/Context/RouteParams/HttpStatus 类型 + 并发包装(ArcMutex/BoxRwLock/xxhash) | `hyperlane::http_type::*` 重导出(由 `hyperlane-core` 间接暴露) |
| `http-constant` | HTTP 常量(header 名 / version / MIME / protocol) | 通过 `http-type` 间接使用 |
| `http-compress` | Brotli / Deflate / Gzip 压缩解压(`brotli` + `flate2`) | 通过 `http-type` 间接 |
| `http-request` | HTTP / HTTPS 客户端(支持自动 redirect / 解码 / `Proxy` enum / fluent `RequestBuilder`) | 独立路径,通过 `http-type` 间接 |
| `hyperlane-core` | Server / Context / Hook trait / Route / Config + root `hyperlane` 的 re-export 源 | monorepo 根 re-export 目标 + 客户端类型消费者 |
| `lombok-macros` (`2.1.0` 第三方,固定不变) | 派生宏源(`Data/New/Getter/Setter/...` + 替换 `#[async_trait]`) | `hyperlane` + `hyperlane-core` 依赖,derive 在 hyperlane 结构上 |
| `hyperlane-macros` | 过程宏(`#[route]` / `#[hyperlane]` / `#[task_panic]` 等) | **独立 crate**,需单独 `cargo add`,依赖 `hyperlane-core` 才能展开 |
| `hyperlane-cli` | `watch / new / template / help / version` 项目脚手架 CLI | hyperlane monorepo 自带,**不**做 `fmt / bump / publish / sync` |
| `crate-cli`(外部) | `fmt / bump / publish / sync` 跨 monorepo 通用工具 | 独立 crate,在 `ctares` monorepo 下,旧名 `crates-cli`,已发布到 crates.io,`hyperlane` / `euv` / `ctares` CI 都用 |
| `hyperlane-plugin-websocket` | WebSocket 支持 | 独立 plugin,`inventory::submit!` |
| `hyperlane-plugin-server-monitor` | 服务监控(指标/健康检查) | 独立 plugin,`inventory::submit!` |
| `hyperlane-broadcast` | 进程内 broadcast bus | 独立 plugin,`broadcast::Bus<T>` |

> ⚠️ **monorepo 内部 7 个 crate(`hyperlane` 根 re-export + `hyperlane-core` + `hyperlane-macros` + `http-type` + `http-compress` + `http-constant` + `http-request` + `hyperlane-cli`)版本号统一**,跟根 `Cargo.toml` `[workspace.package] version` 同步 — skill 不维护具体值,master `git show master:Cargo.toml | grep '^version'` 即得。`lombok-macros` 是第三方独立版本,不在同步范围。

## 6. Monorepo Layout & Internal Deps

### 6.1 内部依赖图(path-dep,workspace 模式)

```
hyperlane-type (= http-type)        (叶子, 无内部依赖)
   ↑ path-dep
http-constant ────────────────────────┐
http-compress ────────────────────────┤  (都 path-dep 到 http-type)
http-request ────────────────────────┤
   ↑ path-dep
hyperlane-core ──────────────────────┐
   ↑ path-dep                       │
hyperlane-macros ───────────────────┤  (依赖 hyperlane-core + http-type)
   ↑ path-dep                       │
hyperlane-cli ──────────────────────┤  (依赖 hyperlane-core + http-type)
   ↑ path-dep                       │
hyperlane (根) ──────────────────────┘
```

**关键**(2026-09-25 实地):
- `core` 同时依赖 **4 个**内部 path-dep:`hyperlane-type` + `http-constant` + `http-compress` + `http-request`。
- `macros` 依赖 `hyperlane-core`(`dev-dependencies`,因为 macro 生成代码引用 `::hyperlane_core::*`)。
- `cli` 不依赖 `macros`(`hyperlane-cli` 只做 `watch / new / template`,不需要 proc-macro)。
- 根 `hyperlane` 不直接依赖 `hyperlane-type`(由 `hyperlane-core` 间接 `pub use` 暴露)。

**验证命令**:`cargo metadata --format-version=1 --no-deps` 看每个 `package.dependencies[]`,内部依赖的 `source` 字段必须是 `null`(path-dep,不打 crates.io)。任何 `source` 不为 null = 循环依赖 / 错配。

**与 euv 的差异**: euv 子包间内部依赖为 0(core/macros/ui/engine/cli 完全平行)。hyperlane 的 `core` 仓**实际使用** `hyperlane-type` 的 `Request/Response/Status/Stream/Context/RouteParams` 类型 + `http-constant` 的常量 + `http-compress` 的压缩 + `http-request` 的客户端类型,所以 core→它们都是代码约束(非设计选择)。若要 euv-style 0 内部依赖,需要把 core 内部使用的 type 拆碎重定义,会破坏现有 API。

### 6.2 Cargo.toml 依赖写法

子包内部依赖用 `path = "..."` + 显式 `version`:
```toml
# core/Cargo.toml
hyperlane-type = { path = "../type", version = "X.Y.Z" }   # crate 名 http-type,目录仍叫 type/
http-compress  = { path = "../compress", version = "X.Y.Z" }
http-constant  = { path = "../constant", version = "X.Y.Z" }
http-request   = { path = "../request", version = "X.Y.Z" }

# macros/Cargo.toml
hyperlane-core = { path = "../core", version = "X.Y.Z" }

# 根 Cargo.toml 引用子包用 workspace = true:
hyperlane-core = { workspace = true }
```

根 `Cargo.toml` 的 `[workspace.dependencies]` 必须包含**全部** path-dep(sync_workspace_version job 依赖它来 sed):
```toml
[workspace.dependencies]
http-type       = { path = "type", version = "X.Y.Z" }       # crate 名是 http-type
hyperlane-core  = { path = "core", version = "X.Y.Z" }
hyperlane-macros = { path = "macros", version = "X.Y.Z" }
hyperlane-cli   = { path = "cli", version = "X.Y.Z" }
http-compress   = { path = "compress", version = "X.Y.Z" }
http-constant   = { path = "constant", version = "X.Y.Z" }
http-request    = { path = "request", version = "X.Y.Z" }
```

> ⚠️ **所有 `version = "X.Y.Z"` 占位符都跟根 `[workspace.package] version` 同步** — bump 时 `crate sync` 一次性 sed 全 7 个 `Cargo.toml` 的 path-dep `version`。

### 6.3 根 hyperlane 包(纯 re-export shim)

```rust
// src/lib.rs(2 行,带 //! 头注释)
pub use {hyperlane_core::*, hyperlane_macros::*};
```

`hyperlane_type::*` 由 `hyperlane_core` 内部 `pub use {hyperlane_type::*, inventory};` 间接暴露给用户,**根 lib.rs 不需要单独 re-export**(否则触发 unused_imports warning + 不必要)。

根 `[dependencies]`:
```toml
[dependencies]
hyperlane-core = { workspace = true }
hyperlane-macros = { workspace = true }
# 不要加 hyperlane-type / http-compress / http-constant / http-request — root 不直接用,加了就 dead dep
```

### 6.4 `crate-cli` publish 顺序(拓扑序,与 euv 一致)

hyperlane CI `.github/workflows/rust.yml` 的 `publish` job 按**拓扑序**发布(被依赖的先发)。注意:发布顺序**不再**有独立 shell loop,而是 `crate-cli` 的 `crate publish` 子命令按 members 拓扑序自动排(2026-09-13 PR #233 之后的标准模式):

```
http-type → http-constant → http-compress → http-request
         → hyperlane-core → hyperlane-macros → hyperlane-cli → hyperlane
```

每个 `cargo publish -p X --allow-dirty --no-verify` 是纯本地 package 操作,workspace 模式下 path-dep 自动解析为本地路径。**不需要**先把 path-dep 改成 crates.io 版本。

**顺序由依赖图决定**(2026-09-14 PR #34 验证):
- `hyperlane-macros` 在 `Cargo.toml` 里 `dev-dependencies` 引 `hyperlane-core` + 生成代码引用 `::hyperlane_core::*`,所以 **`core` 必须先于 `macros` 发布**。
- `hyperlane-core` 引用 `hyperlane-type` (`Request/Response/...`)+ `http-constant` + `http-compress` + `http-request` 的类型,所以这些**必须先于 `core` 发布**。

如果 publish job 写成 `core → macros`,macros 发布时 core 还没上 crates.io,resolver 失败。CI 静默吞错误(retry+continue),最终 `max_stable_version` 不匹配 tag。

**检测 publish 顺序是否对**:`cargo metadata --format-version=1 --no-deps | jq -r '.packages[].dependencies[] | select(.source == null) | .name'` 看 internal dep 关系,反推拓扑序。或者直接看 `Cargo.toml` 的 `[dev-dependencies]` 里 `path = "..."` 引的目标。

### 6.4.1 PR #34 实际 publish 顺序 pitfall(2026-09-14 verified)

`hyperlane-macros/Cargo.toml` 写了:
```toml
[dev-dependencies]
serde = { ... }
```

但宏生成代码里 `quote!` 出来的 token 含 `::hyperlane_core::Status /::RouteParams`,doctest 100 处有 `use hyperlane_core::*;`。**编译期宏展开需要 core crate 存在**。所以核心仓 `hyperlane-core` 必须先 publish,macros 才能 publish。

不强制 `path-only dev-dep`(Rust macros 子 crate 通常不反向 dev-dep 根 crate,因为根是 re-export shim);只要 publish 顺序对,`hyperlane-core` 上 crates.io 后,`hyperlane-macros` 的 resolver 找到 `hyperlane-core = "X.Y.Z"` 即可。

### 6.5 README 陷阱(cargo publish 拒绝跨仓 README)

每个子包 `Cargo.toml` 的 `readme` **必须指向子包目录内的相对路径**。**禁止** `readme = "../../README.md"`(指向 monorepo 根 README) — `cargo publish` 会拒绝:
```
error: readme `../../README.md` does not appear to exist
       (relative to `/path/to/monorepo/<subcrate>`).
```

**修复**:每个子包目录各放一份 `README.md`(从仓根 `cp` 一份即可),`readme = "README.md"`。这跟 euv monorepo 同模式(每个 euv-* 子仓都有独立 README.md)。

### 6.6 顶层 `use` 命名坑(proc-macro crate)

`hyperlane-macros` 是 proc-macro crate,其源码生成的 TokenStream 用 `::hyperlane::Status/HookType/inventory` 等路径。如果保留单仓时代的 `::hyperlane::*` 路径,展开到用户代码时会找不到 crate。

**monorepo 改法**:把所有 `macros/src/**/*.rs` 内的 `::hyperlane::` 替换为 `::hyperlane_core::`(`sed -i 's|::hyperlane::|::hyperlane_core::|g'`)。同时 `macros/src/lib.rs` 的 100 个 doctest 里 `use hyperlane::*;` → `use hyperlane_core::*;`。

**为什么不反过来**让根 `hyperlane` 反向依赖 macros?会成环(`hyperlane-macros` 不能依赖 `hyperlane`)。正确方向: macros 用 `::hyperlane_core::*` 直接引用,不绕根包。

### 6.7 monorepo 引入后从单仓迁移的 checklist

(从单仓 hyperlane → monorepo 的实战顺序,见 `references/monorepo-migration-checklist.md`)

- [ ] `git mv src core/src && git mv tests core/tests`
- [ ] `cp -r upstream-cli/* cli/` + 同理 macros/type
- [ ] 删除每个子仓的 `.git` 子目录(避免嵌套 repo)
- [ ] 每个子仓的 `lib.rs` 顶部 `//! <name>` 头注释必须删除(rust-standards §2.5)
- [ ] 每个子仓的 `Cargo.toml` 改:
  - `name` → 改前缀 (`hyperlane-type` / `hyperlane-macros` / `hyperlane-cli`)或改成新名 (`http-type` / `http-compress` / `http-constant` / `http-request`)
  - `readme = "../../README.md"` → `readme = "README.md"`(并 `cp README.md` 到子包目录)
  - `repository` → 统一指向 `https://github.com/hyperlane-dev/hyperlane.git`
  - 内部依赖用 `path = "..."` + `version`
- [ ] 根 `Cargo.toml` 写 `[workspace]` + 根 hyperlane 包(纯 re-export)
- [ ] `macros/src/**` 内所有 `::hyperlane::` 替换为 `::hyperlane_core::`
- [ ] `macros/src/lib.rs` 内 100 个 doctest 的 `use hyperlane::*` 替换为 `use hyperlane_core::*`
- [ ] `tests/mod.rs` 内 `use hyperlane::*` 替换为 `use hyperlane_core::*`(在子包内)
- [ ] 跑 `cargo check --workspace` + `cargo test --workspace` + `audit_rust_standards.py`
- [ ] 跑 `cargo metadata` 验证无循环

### 6.8 `Request` 模块拆分模式(`type/src/request/` + `request/src/request/`, 2026-09-26)

**`http-type` 仓**(`type/src/request/`):`Request` impl.rs 在 fluent setter + public accessor 之间混入了 11 个 `pub(crate)` static parser 方法(`get_http_first_line` / `check_http_*` / `get_http_querys` / `get_http_headers` / `get_http_body`),导致 impl.rs 1096 行难以维护,且语义上 parser 不属于 Request 数据类型。

**`http-request` 仓**(`request/src/request/`):parser 也是独立子模块,但**位置不同** — 在 `request/request/parser/`,**不**在顶层 `request/parser/`。

```
type/src/request/                # http-type
├── mod.rs           # pub mod request;
├── enum.rs
├── impl.rs
├── struct.rs
└── type.rs

request/src/request/             # http-request
├── mod.rs           # pub mod r#request; pub mod r#parser;
├── request_builder/
├── proxy/
├── config/
├── impl.rs
├── enum.rs
├── struct.rs
└── parser/                     # 独立 parser 子模块
    ├── mod.rs       # pub mod r#parser;
    └── fn.rs        # parser 方法
```

**关键点**(两个仓通用):
- consumer 调用路径: `request::parser::fn_name(...)`(注意:不能写 `Request::parser::fn_name(...)`,Rust 会把 `parser` 解析成 associated type 而不是模块路径,触发 E0223 ambiguous associated type)。
- `http-request` 的 response 依赖 parser 路径用 `crate::request::parser::wire::split_*` 绝对路径(`parser` 子文件叫 `fn.rs` 还是 `wire.rs` 视具体 crate 而定)。
- `pub(crate) use r#fn::*;` 而**不是** `pub use r#fn::*`(后者配合 `pub(crate)` fn 是 no-op,触发 unused_imports warning)。

### 6.9 `http-request` 客户端(`request/`)2026-09-26 重构

客户端 `http-request` crate 之前 API 设计风格与 server-side `hyperlane-core` 完全不一致 — 双字段 `Box<dyn RequestTrait>` / `Box<dyn ResponseTrait>` / `Arc<RwLock<>>` 嵌套 / 6 个 `*_proxy_auth` setter / `HashMap<K, Vec<V>>` 多值 headers / `response_binary` + `response_text` 双类型。

**重构后**(对齐 rust-standards + hyperlane-standards §8.1):

- 单值 `HashMapXxHash3_64<String,String>` headers(无 Vec 多值)。
- `Proxy` enum: `Proxy::http()` / `Proxy::https()` / `Proxy::socks5(host, port)`,无 `*_proxy_auth` setter 变体。
- fluent `RequestBuilder` 返回 `HttpRequest` 直接具体类型,**不**返回 trait 对象。
- `.send()` 返回 `Result<HttpResponse, RequestError>`。
- parser 独立子模块 `request/parser/{mod.rs, wire.rs}`(`wire` 而非 `fn` 因为是关键字)。
- `HttpResponse` 单值 struct 字段全 `pub`。
- `HttpResponse::from_bytes` 解析 raw response。
- `ResponseBody = Vec<u8>` 支持 `String::from_utf8_lossy` 双模式。

保留 crate 名 `http-request` 和 `HttpRequest`/`HttpResponse` 命名(已发布到 crates.io,避免破坏下游)。

response 依赖 parser 路径用 `crate::request::parser::wire::split_*` 绝对路径(**不能**用 `use super::parser::*` 跨 crate 模块)。

## 7. Version Bump Rule

跟 `euv-standards §17` 同模式。简版:

```bash
cd /root/github/hyperlane-dev/hyperlane
# OLD_VER / NEW_VER 从根 Cargo.toml [workspace.package] version 提取;每个 bump 自填
NEW_VER="X.Y.Z"      # ← bump 目标(每次手填)
OLD_VER="W.V.U"      # ← 当前 master 版本(从根 Cargo.toml 抄)
# 只改根 Cargo.toml
sed -i "s/^version = \"$OLD_VER\"$/version = \"$NEW_VER\"/" Cargo.toml
git diff --stat   # 期望只有 Cargo.toml +1/-1
git add Cargo.toml
git commit -m "chore: bump version to $NEW_VER"
```

**不**做:
- ❌ `sed -i 's/version = "W.V.U"/version = "X.Y.Z"/' */Cargo.toml`
- ❌ 编辑 `core/Cargo.toml` / `macros/Cargo.toml` / `type/Cargo.toml` / `compress/Cargo.toml` / `constant/Cargo.toml` / `request/Cargo.toml` / `cli/Cargo.toml`
- ❌ 编辑 `[workspace.dependencies]` 内 path-dep 的 `version`

CI sync 在 master push 上自动补齐上述字段(`chore: sync all package versions to X.Y.Z` 自动 commit)。


## 8. 互锁 skill

- **`hyperlane`**(入口)— 跳转 + 5-行最小调用 + 按需加载 `references/api-*.md`
- **`hyperlane/references/api-core.md`** — hyperlane-core pub API(Server / Context / Hook / Route / Config)
- **`hyperlane/references/api-macros.md`** — hyperlane-macros 77 个 proc_macro 签名
- **`hyperlane/references/api-type.md`** — http-type pub API(Request / Response / Method / Status / Stream / Cookie / WebSocketFrame 等)
- **`hyperlane/references/api-request.md`** — http-request 客户端 pub API(RequestBuilder / Proxy / redirect / 解码)
- **`hyperlane/references/api-compress.md`** — http-compress pub API(Brotli / Deflate / Gzip)
- **`hyperlane/references/api-constant.md`** — http-constant 14 个常量模块
- **`hyperlane/references/api-cli.md`** — hyperlane-cli pub API(5 个子命令)
- **`hyperlane/references/pitfalls.md`** — 22 核心坑 + 8 monorepo/工具链坑
- **`crates-cli-usage`** — 跨 monorepo 通用 `crate-cli` 工具使用(替代废弃的 `hyperlane fmt`)
- **`rust-standards`** — Rust 通用规范(同时必加载)
- **`rust-pr-validation-checklist`** — Rust PR 提交前必跑的硬性验证清单