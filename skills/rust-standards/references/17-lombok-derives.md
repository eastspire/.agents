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

> **⚠️ Lombok 行为坑 — `#[get(pub, copy)]` 实际仍然返回 `&T`(2026-09-18 eastspire/euv-docs PR #31 实测 lombok-macros 2.0 / 2.1)**:本表说 `#[get(pub, copy)]` 对 Copy 类型返回 `T`(字段值副本),但实际 lombok 2.0 / 2.1 不论 `copy` 与否,生成的 `get_field(&self)` 都返回 `&T`。详 §17.8。

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

lombok-macros 会为每个字段同时生成两组 getter。**`Option<T>` / `Result<T, E>` 字段的 `get_*` 是 `clone().unwrap()`**——直接 panic,不是返回 `Option<&T>`:

- `get_field(&self) -> T` (对 `Option<T>` / `Result<T, E>` 字段) — `self.field.clone().unwrap()`
  - **None / Err 时直接 panic**,不能安全访问 `Option` 字段
  - 类型签名看起来是 `T`,不是 `Option<T>`——调用方看不出来会 panic
- `try_get_field(&self) -> &Option<T>` / `&Result<T, E>` — 返回裸引用的 Option / Result,调用方做 pattern match
  - **唯一安全的访问路径**
- `get_field(&self) -> &T` (对非 `Option` / `Result` 字段) — 普通引用

**示例对比**(lombok 2.0 `cargo expand` 实测):
```rust
#[derive(Data, New)]
pub struct Args {
    #[get(pub)] #[set(pub)] required: PathBuf,
    #[get(pub)] #[set(pub)] maybe:    Option<PathBuf>,
}
// 展开后:
//   pub fn get_required(&self) -> &PathBuf            { &self.required }
//   pub fn get_maybe(&self)    -> PathBuf             { self.maybe.clone().unwrap() }
//   pub fn try_get_maybe(&self) -> &Option<PathBuf>   { &self.maybe }
```

**踩坑实证**(2026-09-18 euv-docs `Args::index_html` 字段,`cargo expand` 输出):
```text
pub fn get_index_html(&self) -> PathBuf {
    self.index_html.clone().unwrap()
}
pub fn try_get_index_html(&self) -> &Option<PathBuf> {
    &self.index_html
}
```

实际写 `match args.get_index_html() { ... }` 想拿到 `Some(...)` / `None` —— 编译就过不了 (编译器推断 `match` 期望 `Option<_>`,实际拿到 `PathBuf`, `Some` 分支永远 unreachable);改成 `match args.try_get_index_html() { Some(p) => ..., None => ... }` 才正确。

**判定准则**(写新 code 前):
1. **字段类型是 `Option<T>` / `Result<T, E>`** → 用 `try_get_*`(`&Option<T>` / `&Result<T, E>`),做显式 match
2. **字段类型是普通 `T`(Copy 或非 Copy)** → 用 `get_*`(`&T`)。注意对 `Copy` 类型字段用 `*x.get_*()` 解引用取出值
3. **想设字段值** → 用 `set_*` (始终是 `&mut self`),与字段类型无关

**常见反模式**:
- `let x: Option<&T> = args.get_optional_field()`  — 编译失败 (`get_*` 返回 `T`,不是 `Option<&T>`)
- `args.get_optional_field()` 在 `None` 分支会直接 panic,不带任何类型信号
- 期望 `get_*` 返回 `Option<&T>` 是 Rust 标准库约定(例如 `HashMap::get`),**Lombok 不遵循这个约定**

其他类型字段**不生成** `try_get_xxx`,**不要**手动写 `try_get` 方法;如需安全访问,统一用 `match` / `if let` 配合 `try_get_field` 写显式逻辑。

## 17.5 版本与冲突

- 项目优先复用**已经在依赖图中**的 `lombok-macros` 版本,避免引入多版本
- 优先使用 `Debug`,如果某些字段无法 `Debug`, 再换成 `CustomDebug` 来替代标准 `#[derive(Debug)]`,没有实现 `Debug` 的字段需要标注 `#[debug(skip)]`
- **不要**重复 `#[derive(Debug)]`(否则产生冲突 impl)

## 17.6 Lombok 生成 setter 的两个真实陷阱(2026-09-12 euv PR #209 实测)

把 `self.x = value` 改成 `self.set_x(value)` 看似一行替换,**实际有两个坑会触发编译错误**。修复它们之后 setter 路径才真能用。

### 陷阱 A — setter 接收的是 Lombok 推导出的字段类型,不是调用方期望的转换类型

```rust
// SsaaCanvas.width: u32   (#[get(type(copy))])
// Lombok 生成:
//   pub(crate) fn set_width(&mut self, value: u32) { self.width = value }
//
// ❌ 错误: 把 u32 转成 f64 想"贴合字段类型外的 API"
self.set_width(physical_width as f64);
// → E0308: expected `u32`, found `f64`

// ✅ 正确: 保持传入类型与字段声明一致,u32 直传
self.set_width(physical_width);   // physical_width: u32
```

**根因**: Lombok 的 `set_field` 签名由字段类型 `T` 直接推导出 `fn set_field(&mut self, value: T)`,**不接受隐式转换**(虽然 Rust 允许 `as` cast,但 setter 签名是字段类型本身,cast 出的不同类型就是"expected T, found Other")。如果调用方需要不同类型,**在调用方**转换,而非 setter 内部。

**例外 — `#[set(pub, type(AsRef<str>))]` / `#[set(pub, type(Into<String>))]` 这类字段注解**: Lombok 会用注解里的 `type(...)` 改 setter 接收类型。**只有字段声明上有这种注解时**,setter 才"接受另一种类型"。代码里没看到对应 `type(...)` 注解,就按字段原类型传。

### 陷阱 B — `&mut self` setter 不能在同一表达式嵌套 `self.method()`

```rust
// ❌ 错误: 编译 E0499 cannot borrow *self as mutable more than once
self.set_render_pass_descriptor_cache(Some(self.build_render_pass_descriptor(
    &color_view, ..., depth,
)));
// Lombok 生成:
//   pub fn set_render_pass_descriptor_cache(&mut self, value: Option<RenderPassDescriptorCache>)
//
// 问题: outer &mut self (setter) vs inner &self (build_render_pass_descriptor) 撞借用检查器
```

**✅ 正确 — 先 bind 到 local 再传 setter**:

```rust
let descriptor = self.build_render_pass_descriptor(
    &color_view, resolve_view.as_ref(), color.clear_value,
    effective_load_op, effective_store_op, depth,
);
self.set_render_pass_descriptor_cache(Some(descriptor));
```

**根因**: Lombok 的 `set_field` 是 `&mut self` 取借用,**任何在同一表达式里又对 `self` 取借用或可变借用的内嵌调用都会撞 borrow checker**(rust 2018+ NLL 也没解开)。如果 `build_*` 是 `&self` 方法,先临时变量绑定结果再传 setter 是唯一干净解。

**判断准则**: 改写前先 grep Lombok 在该字段生成的 setter 签名
```bash
# Lombok 在 struct 字段旁插入 derive 后,生成的 set_xxx 方法会出现在同一编译单元
grep -nE 'fn set_<field>' target/wasm32-unknown-unknown/debug/deps/*.rmeta 2>/dev/null || \
  cargo doc --no-deps --target wasm32-unknown-unknown -p <crate>  # 找 generated docs
```
**实际更可靠的方式**:直接看 `impl Self { fn set_<field>(...) }` 的 `cargo check` 输出。Rust 编译器对 setter 签名有错时会把它打到 note 行,跟一遍就清楚。

### 跳过 Lombok setter 的合法理由

`Self::field` 是 `pub(crate)` 但 Lombok 未 derive(典型场景: generic 字段上 Lombok derive 推不出 `T: Default` 类 bound,如 euv 的 `Tween<T: Interpolable + Copy>`):
```rust
/// Lombok's `Data` derive is intentionally **not** applied here for the same
/// reason as [`EngineCell`]: the derive does not propagate generic bounds, ...
/// The accessor pairs below follow the same naming contract as the Lombok-
/// generated ones (`get_*` / `set_*`).
pub struct Tween<T: Interpolable + Copy> { ... }
```

这种 struct 文档会**显式说明**为何不 derive Lombok,需保留手写 accessor。在仓库里 grep `Lombok-shaped counterpart` 或 `not deriving \`Data\`` 找这种例外,不要强改 setter。

## 17.8 Lombok `get_*` 实际返回 `&T` —— 调用方必须解引用(2026-09-18 实测)

**§17.2 表格描述与 lombok-macros 2.0 / 2.1 实际行为不符**。表格说:

> `#[get(pub, copy)]` - Generates a public getter that returns a copy of the field value (`self.field`) for Copy types

实际 `cargo expand --lib` 展开 Lombok 生成的代码(lombok-macros 2.0.36 + 2.1 都一样):

| 字段类型 | `#[get(pub)]` 实际签名 | `#[get(pub, copy)]` 实际签名 |
|---|---|---|
| `bool` | `pub fn get_x(&self) -> &bool` | `pub fn get_x(&self) -> &bool` |
| `&'static str` | `pub fn get_x(&self) -> &&'static str` | `pub fn get_x(&self) -> &&'static str` |
| `PathBuf` | `pub fn get_x(&self) -> &PathBuf` | `pub fn get_x(&self) -> &PathBuf` |

`copy` 修饰符**被忽略** —— 所有 Lombok `get_*` 一律返回 `&T`(或 `&&T` for references)。

**调用方陷阱**:

```rust
// ❌ 错误: 拿 `&bool` 当 `bool` 用
if args.get_release() {
    // E0308: expected `bool`, found `&bool`
}

// ❌ 错误: 拿 `&&'static str` 当 `&str` 用(例如 Command::arg)
.command.arg(args.get_name())  // arg 期望 &OsStr
// E0308: expected `&OsStr`, found `&&str`

// ✅ 正确: 显式解引用
if *args.get_release() { ... }
.command.arg(*args.get_name())
```

**经验**:写完 `#[derive(Data, New)]` 的 struct,先 `cargo expand --lib` 看 Lombok 实际生成的 `get_*` 签名(尤其 `bool` / `&T` 字段),不要按 §17.2 表格的描述脑补签名。

**验证代码**(复制粘贴,确认 Lombok 行为版本相关):
```rust
use lombok_macros::{Data, New};

#[derive(Data, New)]
pub struct Probe {
    #[get(pub)]              b: bool,
    #[get(pub, copy)]        c: bool,
    #[get(pub)]              r: &'static str,
    #[get(pub, copy)]        s: &'static str,
}

// cargo expand --lib 后:
//   pub fn get_b(&self) -> &bool          ← 都是 &T
//   pub fn get_c(&self) -> &bool          ← copy 不生效
//   pub fn get_r(&self) -> &&'static str  ← 双 ref
//   pub fn get_s(&self) -> &&'static str  ← copy 不生效
```

## 17.9 `CustomDebug` 与 `Debug` 互斥(2026-09-18 实测)

**反例**(踩坑,eastspire/euv-docs PR #31 第一版):

```rust
use lombok_macros::{Data, New, CustomDebug};

#[derive(Clone, Debug, PartialEq, Eq)]       // 标准 Debug
#[derive(Data, New, CustomDebug)]             // Lombok CustomDebug 也 impl Debug
pub struct Args { ... }
```

**编译错误**:
```
error[E0119]: conflicting implementations of trait `Debug` for type `Args`
 --> src/lib.rs:3:21
  |
3 | #[derive(Clone, Debug, PartialEq, Eq)]
  |                 ----- first implementation here
4 | #[derive(Data, New, CustomDebug)]
  |                     ^^^^^^^^^^^ conflicting implementation for `Args`
```

**正确写法**(只用一个 Debug 派生):

```rust
use lombok_macros::{Data, New, CustomDebug};

#[derive(Clone, PartialEq, Eq)]               // 不写 Debug
#[derive(Data, New, CustomDebug)]             // Lombok 负责 Debug impl
pub struct Args { ... }
```

§17.2 表头说"`CustomDebug` 替代标准 `#[derive(Debug)]` 的更细粒度版本" —— 这句话隐含了**互斥**,但容易被忽略。两行 derive 都不带 `Debug` 才不会冲突。

**反向陷阱**:如果只想用 `Data + New` 不要 Debug,同样**不要** `#[derive(Debug)]` —— `Data` / `New` 不会自动加 Debug,但如果标准 derive 加了 `Debug`,而后续又把 `CustomDebug` 加进 Lombok derive,就会撞 impl。

## 17.10 `cargo fmt` 合并相邻 `#[derive]` 行(2026-09-18 实测)

**§17.2 "标准组合" 示例**用了两行 `#[derive(...)]`:

```rust
#[derive(Clone, Debug, Default, PartialEq, Eq)]
#[derive(Data, New, CustomDebug)]
```

**`cargo fmt --all` 会自动合并**为一行:

```rust
#[derive(Clone, Debug, Default, PartialEq, Eq, Data, New, CustomDebug)]
```

合并后**语义正确**(lombok-macros 都是 proc-macro derive,放进同一个 `#[derive(...)]` 完全合法),但偏离示例格式。两种写法都通过 audit / clippy / fmt 幂等检查,只是表面不一致。

**对策**:写完后跑 `cargo fmt --all && cargo fmt --all -- --check` —— 如果 `cargo fmt` 改动了 `#[derive]` 行,**接受** 合并后的版本,不要写 `.rustfmt.toml` 配置强行保留两行(formatting config 跨 crate 不通用,会污染下游项目)。

## 17.11 Lombok `#[derive(Getter, Setter)]` 静默失效时的手写 accessor 三件套(2026-09-26 hyperlane request crate 实测)

§17.3 假定 Lombok 的 `#[derive(Data)]` / `#[derive(Getter, Setter)]` 会自动生成 `get_*` / `set_*` 方法。**实测 hyperlane `request/src/response/struct.rs` 中 `#[derive(Getter, Setter)]` 标注在 `HttpResponse` 上,但 `cargo check` 后 impl 块中没有任何 `get_status_code` / `set_status_code` 之类的方法被生成** —— Lombok 的 getter/setter 生成对某些字段类型(尤其嵌套 `HashMap` / `Vec<u8>` / 自定义 struct)的支持不完整,会**静默失败**(编译通过,但零产出)。

**症状判定**:
```bash
# 在目标 struct 上标了 #[derive(Data)] / #[derive(Getter, Setter)] 之后,
# 运行下面命令,期望看到 set_<field> / get_<field> 至少一处:
grep -nE '^    pub fn (set|get)_' <crate>/src/<module>/<struct>/struct.rs
# 如果 0 行命中,但 struct 顶部确实有 Lombok derive —— Lombok 静默失效
```

**强制规则(2026-09-26 user 钦定,user 原话:"request里所有字段避免直接self访问,使用self的get和set")**:即使 Lombok derive 标注到位,所有跨 impl block 的字段读写**必须**经过 `get_<field>` / `set_<field>` 方法,**禁止** `self.field` 直接读写。Lombok 静默失效时**必须手写** accessor 三件套:

```rust
// 1. clone getter (返回 owned T,用于 fn 调用传值场景)
pub fn get_field(&self) -> FieldType { self.field.clone() }

// 2. ref getter (返回 &T,用于只读借场景)
pub fn get_field_ref(&self) -> &FieldType { &self.field }

// 3. mut getter (返回 &mut T,用于就地改写,典型场景 self.field.X -= 1)
pub fn get_field_mut(&mut self) -> &mut FieldType { &mut self.field }

// 4. setter (返回 &mut Self 给 fluent chain 用,沿用现有命名风格)
pub fn set_field(&mut self, value: FieldType) -> &mut Self {
    self.field = value;
    self
}
```

**命名契约**(跨 crate 一致):
- `get_<field>` → owned clone(签名 `-> FieldType`,不接引用,**不**是 `&FieldType`)
- `get_<field>_ref` → `&FieldType`(Lombok 也用 `_ref` 后缀,需手工命名对齐)
- `get_<field>_mut` → `&mut FieldType`(Lombok 同样后缀)
- `set_<field>(&mut self, value: FieldType) -> &mut Self`

**实施步骤**(从 `self.field` 直读改写为 accessor):
1. **判定**:在 impl.rs 用 `grep -nE 'self\.(field_a|field_b)'` 列出所有直接字段访问。
2. **构造 accessor 三件套**:在 struct.rs 的 `impl` 块顶部集中加入 `get_*` / `get_*_ref` / `get_*_mut` / `set_*` 方法。**不要逐字段散落**到 impl.rs 各处 —— 集中后 reader 一眼能找到访问面。
3. **替换读**:`self.field` → `self.get_field_ref()`(或 `self.get_field()` 当 fn 接收 owned 时);`self.field.X` → `self.get_field_ref().X`;`self.field.bytes` → `self.get_body_ref().as_slice()` 等方法替代。
4. **替换写**:`self.field = value` → `self.set_field(value)`(沿用 fluent `&mut Self` 链);`self.field.X -= 1` → `self.get_field_mut().X -= 1`。
5. **builder 中的链式调用**:如果 builder 通过 `&mut HttpRequest` 字段直写(`self.request.config.X = Y`),改写为 `self.request.get_config_mut().X = Y`(**不**是 `set_config(config); config.set_X(Y)` —— 后者拆成两行多一次 clone)。
6. **验证**:`cargo check --workspace --all-targets` exit 0,`cargo clippy --workspace --all-targets` 0 warning,`grep -nE 'self\.(method|url|headers|body|config|tmp)' <file>` 仅命中 setter 内部的 `self.field = value` 表达式。

**Pitfall(setter 内部允许直写,impl.rs 其他位置不允许)**:`pub fn set_field(&mut self, value: T) -> &mut Self { self.field = value; self }` 内部的 `self.field = value` 是**允许**的直写 —— 这是 setter 的实现,没法用 setter 调用 setter 自身。如果改成 `self.set_field(value); self`,则无限递归。这是唯一允许 `self.field` 直写的位置。

**Pitfall(`get_*` 返回 owned 而非 `&T`,误用触发 borrow 错)**:手写 `get_field()` **永远**返回 owned `T`(clone 一次);不要写成 `&FieldType`。如果调用方需要 `&FieldType`,**用 `get_field_ref()`**。这样命名对齐 Lombok 用户的预期(Lombok 的 `get_*` 返回 owned,`get_*_ref` 返回 ref)。**反例**:`fn header_bytes(&self) -> Vec<u8> { let mut header = self.headers.clone(); ... }` 改成 `let mut header = self.get_headers();` 是正确 owned clone;若改成 `let mut header = self.get_headers_ref();` 则是借用 + clone,触发"cannot borrow as mutable"。

**Pitfall(Lombok 静默失效但标了 derive,不要"补 derive 期望它工作")**:常见的失败模式是发现问题后,在 derive 链上再叠加 `#[derive(Data, New, Getter, Setter)]` 期望 Lombok 这次生成 —— **不会**。Lombok 对某些类型组合(`HashMap<_,_>` 字段 + `Getter` 同时在)的处理就是空展开。验证:`cargo expand --lib <module>` 看实际生成的 impl 块 —— 如果 0 行 `pub fn get_*,` 命中,确认 Lombok 失效,**手写 accessor 是唯一修复路径**,不要在 derive 上叠参数期望 Lombok 工作。

## 17.12 业务代码读 vs Lombok 自动生成读 —— 在哪里允许 `self.field` 直读

`self.field` 直读**仅在以下 3 个场景合法**,**所有其他场景必须用 accessor**:

1. **Lombok 生成的 impl 块内部**(包括 `new` 构造、`Debug` / `Display` 实现、`Getter` 实际生成的 `&self.field` body)。
2. **手写 setter 的实现 body** —— `self.field = value;` setter 没法调 setter 自身。
3. **`#[cfg(test)] mod tests` 块内部** —— test helper 是生产代码看不到的;**不**走生产 accessor,以避免 setter 副作用。

**严禁** `self.field` 直读的位置:
- 生产 impl 块内的业务方法(impl `<Struct> { fn business_method(&self) { let x = self.field; ... } }`)
- 跨 impl block 的字段访问(`impl A { fn foo(&self, b: &B) { use b.field; } }` 也不行,b 也要有 getter)
- builder / 工厂方法内部的字段组装(`fn build(&mut self) { self.field = read_field(); }` 必须改成 `self.set_field(read_field())`)

**反向引证**(2026-09-26 hyperlane request/):session 中 35 处 `self.headers` / `self.body` / `self.config` / `self.tmp` / `self.url` 直读全部重写为 accessor,build 与 clippy 干净,12/12 test pass。这是项目级强制规则,新加字段**默认**先写 accessor 三件套,不要先写完 `self.field` 直读再"以后"重构。

## 17.13 `self.field` 禁令的可执行校验(2026-09-26 第七轮,user 原话:"禁止通过self直接操作字段,使用Data宏的get和set")

§17.3 / §17.12 的规则现在有可执行脚本:`scripts/verify_no_self_field_access.py`,被 `audit_rust_standards.py` **check 38** 调用。

### 豁免区(脚本与规则一致,仅 3 类)

1. 手写 accessor fn(`get_*` / `set_*` / `try_get_*` / `new`)体内
2. `impl Debug for ...` / `impl Display for ...` 块内(§17.3)
3. `#[cfg(test)]` 块 + `tests/` 目录

**不在豁免区 = 违规**:`default()` / `drop()` / `AsyncRead` 等其它 trait impl / builder / 业务方法,全部必须走 accessor。`Pin::new(&mut self.inner)` 这种 wrapper 委托也要改成 `Pin::new(self.get_inner_mut())`。

### 方法调用不算字段访问

`self.get_x()` / `self.flush()` 等带括号的调用永不命中;`self.x` / `self.x = v` / `self.x.m()`(字段上再调方法)都命中。`self.0` tuple 字段与 `self::<path>` 不覆盖(已知限制)。

### 无 accessor 的 struct 怎么办

先补访问面再改使用处:

- 普通 struct → `#[derive(Data)]`(lombok 生成全套)
- Lombok 静默失效 / 字段含生命周期引用(如 `&'a mut TcpStream`)→ 按 §17.11 手写三件套,命名对齐 Lombok(`get_x` / `get_x_ref` / `get_x_mut` / `set_x`)

### 三仓收敛基线(2026-09-26 第七轮启动时)

hyperlane 94 / euv 203 / ctares 91 处违规(request crate 虽经 §17.12 清扫,但 AsyncRead/AsyncWrite wrapper 委托与 builder 残留 50 处当时未覆盖 —— 本轮规则文本已含 trait impl)。
