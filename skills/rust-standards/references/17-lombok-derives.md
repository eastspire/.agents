# 17. 派生宏与 lombok-macros

所有 **枚举(`enum`)** 和 **结构体(`struct`,含 tuple struct 与 unit struct)** 必须遵守以下派生与访问约定,**优先使用 [`lombok-macros`](https://crates.io/crates/lombok-macros) 提供的派生宏**生成样板代码,禁止手写 getter / setter / new / Debug / Display。

## 17.1 标准 `#[derive(...)]` 列表

所有枚举和结构体尽可能加上:

```rust
#[derive(Clone, Copy, Debug, Default, Eq, Hash, Ord, PartialEq, PartialOrd)]
```

- 字段语义或 trait bound 不允许时,按需删减;但 `Debug` 与 `Clone` **强烈建议**保留(除非泛型参数不支持)
- **如果 derive 链中某个宏报错且无法解决,应当定位并保留**那个导致报错的宏(连同它前面的宏一起),**只删除**导致错误的那个及其后续宏,**不要全删 `#[derive]` 整行**。例如 `#[derive(Clone, Copy, Debug, Default, Eq, Hash, Ord, PartialEq, PartialOrd)]` 里 `Eq` 报类型不满足,**保留** `Clone, Copy, Debug, Default`,**只删** `Eq` 起及其后续的 `Hash, Ord, PartialEq, PartialOrd` 视依赖关系而定
- `Copy` 要求所有字段 `Copy`;任一字段非 `Copy` 时**必须**移除 `Copy`
- `Eq` 要求 `PartialEq`;`Ord` 要求 `Eq` + `PartialOrd`;`Hash` 不强制要求 `Eq`,但同一键里通常 `Eq + Hash` 同时出现

## 17.2 lombok-macros 派生宏(只适用结构体,枚举不支持)

| 宏 | 生成内容 | 用途 |
|----|----------|------|
| `Getter` | `pub fn get_field(&self) -> &T`(引用 / Deref 自动展开 `Option<&T>` / `Result<&T, &E>`) | 不可变访问 |
| `GetterMut` | `pub fn get_mut_field(&mut self) -> &mut T` | 可变访问 |
| `Setter` | `pub fn set_field(&mut self, value: ...)`(支持 `#[set(pub, type(AsRef<str>))]` / `#[set(pub, Into)]` 等参数转换) | 字段写入 |
| `Data` | `Getter + GetterMut + Setter` 三合一 | **默认推荐**:字段访问样板一次性生成 |
| `New` | `pub fn new(field1: T1, field2: T2, ...) -> Self`(`#[new(skip)]` 字段用 `Default::default()` 初始化;支持 `#[new(pub(crate))]` / `#[new(pub(super))]` / `#[new(private)]`) | 构造器 |
| `CustomDebug` | 自定义 `Debug`,字段标注 `#[debug(skip)]` 可跳过(用于敏感字段) | 替代标准 `#[derive(Debug)]` 的更细粒度版本 |
| `DisplayDebug` | `Display` 用 `{:?}` 格式 | 调试输出兼 `Display` |
| `DisplayDebugFormat` | `Display` 用 `{:#?}` 格式 | 多行调试输出 |

**标准组合**:

```rust
use lombok_macros::{Data, New, CustomDebug};

#[derive(Clone, Debug, Default, PartialEq, Eq)]
#[derive(Data, New, CustomDebug)]
pub struct User {
    #[debug(skip)]
    password: String,
    name: String,
    email: String,
}

let user: User = User::new("alice".to_string(), "alice@ltpp.vip".to_string());
assert_eq!(user.get_name(), "alice");
assert_eq!(user.get_email(), "alice@ltpp.vip");
let mut user: User = user;
user.set_name("bob".to_string());
```

## 17.3 字段访问规则(禁止直接访问字段)

- **必须**通过宏生成的 `get_field` / `set_field` / `new(...)` 操作字段,**禁止** `instance.field` 直接读写
- **例外**:宏生成的 `new(...)` 内部、`Debug` / `Display` 实现内部、`#[derive(...)]` 自动实现里允许直接访问字段,**业务代码不允许**

## 17.4 Option / Result 字段的 try_getter

lombok-macros 会**额外**生成 `try_get_field` 系列方法(仅字段类型为 `Option<T>` 或 `Result<T, E>` 时生成):

- `Option<T>` → `pub fn try_get_field(&self) -> Option<&T>`
- `Result<T, E>` → `pub fn try_get_field(&self) -> Result<&T, &E>`

其他类型字段**不生成** `try_get_xxx`,**不要**手动写 `try_get` 方法;如需安全访问,统一用 `match` / `if let` 配合 `get_field` 写显式逻辑。

## 17.5 版本与冲突

- 项目优先复用**已经在依赖图中**的 `lombok-macros` 版本,避免引入多版本
- 优先使用 `Debug`,如果某些字段无法 `Debug`, 再换成 `CustomDebug` 来替代标准 `#[derive(Debug)]`,没有实现 `Debug` 的字段需要标注 `#[debug(skip)]`
- **不要**重复 `#[derive(Debug)]`(否则产生冲突 impl)
