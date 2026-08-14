# 包名 vs 导入名

crates.io 的包名和 Rust 代码里的 `use` 路径**不总是相同**。

## 规则

- 多数情况下,crates.io 上的包名是连字符形式(如 `lombok-macros`),Rust 代码里用下划线导入(`use lombok_macros::...`)。
- 反过来,有些 crate 包名是下划线,导入也是下划线。
- 例外:带版本后缀的包名,如 `tokio-util@0.6`,导入用 `tokio_util`。

## 速查脚本

不确定时运行 `scripts/fetch_docs_rs.py <crate>` — 它会同时显示 crates.io 包名和文档页面顶部的 "use" 路径,可直接对比。
