# Crate 调研报告

## 元信息

- **Crate 名(crates.io)**: `<name>`
- **Rust 导入名**: `<name_with_underscores>`
- **docs.rs URL**: https://docs.rs/<name>/<version>/
- **目标版本(从 Cargo.lock)**: `<x.y.z>`
- **目标版本(从 Cargo.toml)**: `<x.y.z 或版本范围>`
- **项目 edition**: `<2021 / 2024>`
- **核验时间**: `<YYYY-MM-DD>`

## API / Feature 核对

- **使用的模块路径**: `crate::module::Item`
- **核心类型 / trait / 函数**:
  - `TypeA`: <一句话说明>
  - `fn do_thing(x: T) -> Result<U, E>`: <说明>
- **必需的 feature flags**: `feature1`, `feature2`
- **默认 feature 状态**: 启用 / 关闭

## Cargo.toml 变更

```diff
 [dependencies]
+<name> = { version = "<x.y>", features = ["feature1", "feature2"] }
```

## 验证

- `cargo check`: 通过 / 失败(<错误信息>)
- `cargo test`: 通过 / 失败 / 不适用
- `cargo clippy`: 通过 / 失败

## 未能核实的内容

- <列出任何未核验的 API / 版本差异 / 风险点>

## 风险与替代

- 是否有更轻量的替代: <是 / 否, 说明>
- 是否引入新依赖: <是 / 否, 理由>
