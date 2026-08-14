# 9. 遵守项目现有规范

## 9.1 严格遵循项目的约定

- 文件夹命名
- 模块划分方式
- 包导入风格(参考 references/06-module-imports.md)
- 代码排序逻辑
- 编码约定
- **禁止函数体内出现空行**

## 9.2 泛型约束写法

泛型参数统一使用 `where` 关键字进行约束:

```rust
// ✅ 正确
fn parse<T>(input: T) -> Result<T, Error>
where
    T: FromStr,
{
    // ...
}

// ❌ 错误
fn parse<T: FromStr>(input: T) -> Result<T, Error> {
    // ...
}
```

**不允许在 `fn` 签名直接写 `<T: Bound>`,必须挪到 `where T: Bound { ... }`**。

## 9.3 impl 块排列顺序(同一文件内多个 impl 时)

1. **trait 的 blanket impl**(如 `impl<F, R> SomeTrait<R> for F where ... {}`)
2. `impl Default for Xxx`
3. `impl Xxx`(本体方法,按调用关系或字母顺序排列)
4. `impl PartialEq` / `impl Eq` / `impl Hash` / `impl PartialOrd` / `impl Ord`

## 9.4 关联函数 / factory 独立 impl 块

- 关联函数(factory / utility)放独立 `impl Hook { ... }` 块,**不混入** 数据类型自身的 `impl` 块
- 工厂方法、构造器、单字段 getter 统一返回显式类型(不依赖类型推导)
- 若返回非 `()`,加 `#[must_use]`
