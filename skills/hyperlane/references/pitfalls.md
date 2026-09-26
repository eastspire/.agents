# hyperlane 框架踩坑表(consolidated index)

> **本文件是索引** — 每个坑的详细 repro / 修复 / 不该做的事放在各自 reference 文档中。

## 22 个核心坑(hyperlane-standards §10 原版)

> 维护:这些是 hyperlane 框架反复踩过的坑,任何 hyperlane PR 提交前**逐条对照**。

| # | 坑 | 详细 |
|---|---|---|
| 1 | 路由注册是 **async**:`server.route::<T>(path).await` — 不能链式 `.route().route()` | `references/hyperlane-macros-route.md` |
| 2 | response setter 是 **sync**:`ctx.get_mut_response().set_xxx()` — 不要 `.await` | `references/response.md` |
| 3 | `ServerControlHook` 有 `Default`,用 `unwrap_or_default()` 不要 `expect()` | `references/run.md` |
| 4 | 不要自己 `use Stream`;框架 `Stream` 类型与 `tokio::net::TcpStream` 是两个不同类型 | `references/stream.md` |
| 5 | **`inventory::collect!` 框架调用**:不要在自己代码里再 `collect!` 一遍(重复注册 panic) | `references/hyperlane-macros-hyperlane-init.md` |
| 6 | `#[route]` / `#[hyperlane]` / `#[task_panic]` 来自 `hyperlane-macros`,不是 `hyperlane`;`use hyperlane_macros::*;` | `references/hyperlane-macros-attributes.md` |
| 7 | `Server` 必须 `let mut`(所有注册方法都 `&mut self`)| `references/run.md` |
| 8 | `Status::Continue` vs `Status::Next` 区别:继续走下一个 hook vs 跳到下一阶段 | `api-core.md` §ServerHook |
| 9 | `hook` 函数签名是 `async fn handle(self, ...)`:拿 `self` 而非 `&self`(per-request instance) | `api-core.md` §hook trait |
| 10 | `new()` 钩子也拿 `&mut Stream, &mut Context`:可在 `new` 里做请求级初始化(轻量) | `api-core.md` §hook |
| 11 | `RouteParams` 是 `HashMap<String, String>`:字符串拥有权 — 修改前 `clone()` | `references/hyperlane-macros-route-params.md` |
| 12 | dynamic segment 必须 `{name}` 包裹,**不能** `/users/:id` | `references/hyperlane-macros-route-params.md` |
| 13 | regex segment `{name:pattern}` 写法;**注意 Rust string literal 双反斜杠** `/users/{id:\\d+}` | `references/hyperlane-macros-route-params.md` |
| 14 | response body `set_body` 接收 `Into<Vec<u8>>` — `&str` 也行,内部 `.into()` | `references/response.md` |
| 15 | `build()` 返回 `Vec<u8>`(这个值通常 `let _ = ...;` 丢掉,setter 已经写 body) | `references/send.md` |
| 16 | `server_config()` / `request_config()` 是 **sync**:不要 `.await` | `references/run.md` |
| 17 | `config_from_json` 是 sync,接收 `impl AsRef<str>` | `references/run.md` |
| 18 | Tokio runtime 自己起:`#[tokio::main] async fn main() { ... }` — 框架不自动起 | `references/run.md` |
| 19 | 每个 hook 的 `new()` **每次请求都执行**:**不要**在 `new` 里放 expensive IO,放 `handle` 里 | `references/hyperlane-macros-method-filter.md` |
| 20 | panics 在 `handle` 里会被 `TaskPanic` hook 捕获;**不要**在 `handle` 里 `catch_unwind` | `references/hyperlane-macros-send-flush.md` |
| 21 | 404 / 405 默认走 `RequestError` hook;未注册时框架内置 default(返回空 404 body) | `references/hyperlane-macros-request.md` |
| 22 | `panic = "unwind"`:`TaskPanic` hook 才能拿到 panic;`panic = "abort"` 直接 abort 不触发 | `references/hyperlane-macros-attributes.md` |

## monorepo / 工具链相关

| # | 坑 | 详细 |
|---|---|---|
| 23 | `hyperlane-cli` 只有 `watch / new / template / help / version`;**不要**找 `hyperlane fmt` | `references/api-cli.md` |
| 24 | `bump / sync / fmt / publish` 在外部 `crate-cli`(`~/.cargo/bin/crate`),不是 `hyperlane-cli` | `references/release-bump-flow.md` |
| 25 | bump commit 只改根 `Cargo.toml`,**不要**对 6 个 sub-crate 做任何 sed | `references/release-bump-flow.md` |
| 26 | CI `sync_workspace_version` 在 master push 上自动补齐 sub-crate `Cargo.toml` | `references/release-bump-flow.md` |
| 27 | publish 顺序: `http-type → http-constant → http-compress → http-request → hyperlane-core → hyperlane-macros → hyperlane-cli → hyperlane`(拓扑序)| `references/release-bump-flow.md` |
| 28 | monorepo 切换:旧版 21.3.x 单仓无 path-dep;新版 21.7.x monorepo 必须 path-dep | `references/monorepo-migration-checklist.md` |
| 29 | `readme = "../../README.md"` 拒绝陷阱:子 crate 写错路径会让 crates.io publish 失败 | `references/release-bump-flow.md` |
| 30 | `http-request` 客户端不能用 `use super::parser::*` 跨 crate 模块;**用绝对路径** `crate::request::parser::wire::split_*` | `api-request.md` |

## 工具冲突 quick map

| 工具 | 提供 | 不提供 |
|---|---|---|
| `hyperlane-cli` | `watch / new / template / help / version` | `bump / sync / fmt / publish` |
| `crate-cli`(`~/.cargo/bin/crate`)| `bump / sync / fmt / publish` | server 启动 / template 生成 |
| `cargo fmt` | impl 代码 | (没有 hyperlane-specific 宏重排) |

## 关键词速查

- **hook 不触发** → 坑 #5(`inventory::collect!` 重复)、坑 #6(use 路径错)
- **panic 不被捕获** → 坑 #20(catch_unwind 重复)、坑 #22(`panic = "abort"`)
- **404 default** → 坑 #21(`RequestError` hook 未注册)
- **build / publish fail** → 坑 #24(用错工具)、坑 #25(bump sed 错文件)、坑 #27(发布顺序)
- **路由不匹配** → 坑 #11(RouteParams 拥有权)、坑 #12(/users/:id 错)、坑 #13(正则双反斜杠)