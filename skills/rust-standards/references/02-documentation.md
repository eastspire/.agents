# 2. 注释规范

## 2.1 必须添加文档注释的对象

所有以下项目必须附带完整的 **英文文档注释(doc comment)**:

- 所有类型(结构体、枚举、trait、type 别名)
- 所有常量、静态变量
- 所有函数 / 方法
- 所有 `impl` 块(每个 `impl` 都必须有独立文档注释,**不能仅靠 `//` 行注释**)

## 2.2 doc comment 格式模板

```rust
/// Brief description of the item.
///
/// Extended explanation if needed.
///
/// # Arguments
///
/// - `The type of the first parameter` - Description of argument 1.
/// - `The type of the second parameter` - Description of argument 2.
/// - `GenericName: GenericConstraint` - Description of argument 3.
///
/// # Returns
///
/// - `Type of return value`: Explanation of return value.
///
/// # Panics
///
/// Explanation of when this function might panic.
```

**完整示例**:

```rust
/// Brief description of the item.
///
/// Extended explanation if needed.
///
/// # Arguments
///
/// - `A: AsRef<str>` - Description of argument 1.
/// - `B: String` - Description of argument 2.
///
/// # Returns
///
/// - `String`: Explanation of return value.
///
/// # Panics
///
/// Explanation of when this function might panic.
fn test<A>(_: A, _: String) -> String
where
    A: AsRef<str>,
{
    String::new()
}
```

## 2.3 字段级注释

- 结构体/枚举每个字段必须单独注释其用途。
- 元组结构体的每个字段同样要注释。

## 2.4 lib.rs 唯一注释

`lib.rs` 唯一注释在文件开头,格式如下:

```rust
//! Crates name
//!
//! Description
```

## 2.5 mod.rs 硬性规则:不加任何注释

**`mod.rs` 不加任何注释**(既不写文件头 `//!`,也不写 `mod r#xxx;` 之间的 `// xxx 模块`),保持纯结构组织。**这一条是硬性规则,不可例外。**

## 2.6 impl 块内允许单行注释

`impl` 块内允许使用 `// ...` 形式的**单行注释**解释特定代码行的意图(如解释某段宏调用、某条 `#[derive]` 行为)。
