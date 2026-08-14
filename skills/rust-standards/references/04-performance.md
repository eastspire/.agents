# 4. 性能优化优先级

## 4.1 优先级

1. 默认选择最优的时间复杂度算法,空间换时间可接受,但避免过度消耗内存。
2. 尽可能减少拷贝、避免冗余计算、利用零成本抽象。
3. 使用 `Box`、`Rc`、`Arc` 等智能指针时明确所有权意图。
4. 根据项目使用场景,允许安全的 `unsafe` 使用来优化性能。

## 4.2 `#[inline]` 决策

- **频繁调用的小函数**(含 getter、工厂方法、`is_pred` 谓词)统一加 `#[inline(always)]`,单字段 getter 也带 `#[inline(always)]`。
- **紧凑小方法**(`fn eq`、`fn hash`、`fn cmp`、`fn default` 等 trait 方法)全部加 `#[inline(always)]`
- **较大方法**(多分支 match、多语句逻辑)保持默认 inline 决策或显式 `#[inline]`

## 4.3 WASM 特殊限制

**对于 `wasm` 项目,禁止显示标注任何 `inline` 宏** — 编译时由 wasm-pack / wasm-bindgen 默认行为决定,不要手动干预。
