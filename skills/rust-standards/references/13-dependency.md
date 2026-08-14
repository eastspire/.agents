# 13. 依赖管理

## 13.1 复用优先

- 优先复用项目中已引入的第三方库
- 避免引入新依赖,除非必要且经过权衡
- 若引入新依赖,需说明理由并符合安全审查标准
- **不引入新第三方依赖**优先于 `Cargo.toml` 整洁度;需要时先评估是否能用现有依赖 + 内部宏实现

## 13.2 Cargo.toml 强制约定

| 配置项 | 强制值 |
|--------|--------|
| `edition` | `"2024"` |
| `package.exclude` | 包含 `"target"`, `"sh"`, `".github"` |
| lib 项目的 `package.exclude` | **额外** 包含 `"Cargo.lock"` |
| proc-macro crate 的 `[lib]` | `proc-macro = true;` |

## 13.3 Profile 配置(dev 与 release 必须完全相同)

```toml
[profile.dev]
incremental = false
opt-level = 3
lto = true
panic = "unwind"
debug = false
codegen-units = 1
strip = "debuginfo"

[profile.release]
incremental = false
opt-level = 3
lto = true
panic = "unwind"
debug = false
codegen-units = 1
strip = "debuginfo"
```

> 完整 Cargo.toml 模板见 `templates/cargo-toml.md`
