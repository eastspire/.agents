# 5. 规范强制要求

## 5.1 显式类型标注(强类型语言铁律)

在强类型语言中(尤其是 Rust),**所有变量、参数、返回值和闭包的参数等必须显式标注类型**。具体必须标注位置:

- `let` 绑定(包括 `let mut`)
- 函数签名(参数 + 返回值)
- `impl` 块内的方法签名
- `async fn` 的参数和返回
- 闭包参数
- 元组解构:`let (left, right): (Left, Right) = ...`
- 模式匹配臂内绑定

**禁止依赖自动类型推导**(如 `let items = Vec::new();` ❌ → 必须写为 `let items: Vec<T> = Vec::new();` ✅)。

## 5.2 命名规范

| 类别 | 命名法 | 示例 |
|------|--------|------|
| 变量名 | 蛇形 `snake_case` | `calculate_total_price` |
| 常量名 | 全大写下划线分隔 `UPPER_SNAKE_CASE` | `MAX_BUFFER_SIZE` |
| 函数名 | 蛇形 `snake_case` | `parse_user_input` |
| 结构体名 | 大驼峰 `CamelCase` | `UserProfile` |
| 枚举名 | 大驼峰 `CamelCase` | `ConnectionState` |
| trait 名 | 大驼峰 `CamelCase` | `Renderable` |
| 模块名 | 蛇形 `snake_case` | `user_auth` |
| 宏名 | 蛇形 `snake_case` | `my_macro!` |

**语义化命名禁止缩写** — 严禁使用字母、语义不明确的字符进行命名,必须使用语义化的英文单词。

## 5.3 闭包参数类型

任何 `API` 参数如果是闭包,闭包的参数部分需要显式注明参数的类型:

```rust
|width: W| {}
|(width, text): (W, T)| {}
|width: &W, text: &T| { ... }
```

## 5.4 format! 宏写法

`format!` 这类宏写法统一:

- **变量**使用 `{变量}` 形式(不要嵌在 `""` 之外),例如 `format!("{field}")`
- **函数或方法返回值**不需要写在 `"{}"` 里,写在 `""` 后面的参数位置,例如 `format!("{}", get_field())`

## 5.5 一次性变量不定义

如果变量只使用一次不要定义,直接将具体逻辑在使用的地方写。

## 5.6 函数式编程

尽量使用函数式编程。

## 5.7 命名空间 / 工厂结构体

当一组相关自由函数需要"挂"在某个类型下作 associated function、又不想污染类型本身时,使用 **零大小命名空间结构体**(`pub struct Hook;` + `impl Hook { pub fn factory() -> ... }`),由 `#[derive(Clone, Copy, Debug, Default)]` 等衍生。

调用方式:`Hook::factory()`。
