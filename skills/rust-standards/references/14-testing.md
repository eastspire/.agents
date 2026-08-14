# 14. 测试策略一致性

## 14.1 测试目录结构

- **单元测试放在项目根目录的 `tests/` 里**,子目录按职责命名(如 `tests/server/`, `tests/route/`),里面文件命名遵守 1.3 节的命名规则(关键字文件 + raw identifier)。
- **`tests/mod.rs` 直接列子模块**(`mod config; mod context; ...`,子模块名不带 `r#`),开头 `use crate_name::*;` 引入被测 crate 的全部公共 API。
- **`tests/<sub>/mod.rs` 极简三段式**(与 src 同样遵守 `mod r#xxx;` + `use super::*;`),但**测试模块内部符号全部私有**,不需要 `pub use`、不需要 `pub(crate) use`(tests/ 是独立 crate)。
- **`tests/<sub>/fn.rs`** 写法:`use super::*;` 开头,然后直接 `#[test] fn test_case() { let value: T = ...; ... assert_eq!(...); }`,每个 `#[test]` 函数独立、互不依赖。
- **测试不需要镜像 src**:tests/ 里只放真正需要测试行为的文件(通常是 `fn.rs`),不必为 src/ 里每个关键字文件都建立对应测试文件。

## 14.2 覆盖率

- 测试覆盖率尽可能高,覆盖边界条件和错误路径。

## 14.3 派生宏生成样板

`#[derive]` 样板字段统一通过项目内的派生宏(参见 references/16-lombok-derives.md)生成 getter/setter / Debug / Display,不要手写 `impl Server { pub fn get_field(&self) -> &Field { &self.field } }`。
