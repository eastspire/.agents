# 11. 错误处理机制

## 11.1 强制规则

- 所有可能失败的操作必须正确处理错误。
- 使用 `Result<T, E>` 显式传播错误。

## 11.2 错误类型选择

- 自定义错误类型优先使用 `thiserror` 或标准 `std::error::Error`
- derive 友好地使用第三方 derive 宏替代手写 `impl Debug` / `impl Display`

## 11.3 禁止 panic 调用

- 不使用 `.unwrap()`、`.expect()` 等可能导致 panic 的方法
- 不在生产路径中调用 `panic!`
- 唯一允许 panic 的位置:`assert_*` 系列宏和测试代码

**例外**:单元测试与集成测试场景允许直接 `.unwrap()` / `.expect()` 以保持测试断言简洁。
