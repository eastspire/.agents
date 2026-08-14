# 12. 公开 API 文档化

- 所有公开函数、类型、常量必须有清晰的文档注释
- 说明用途、参数含义、返回值语义、可能的错误情况
- 对返回非 `()` 的纯函数(getter、builder、构造器)应保持 `#[must_use]` 标记
- `#[inline(always)]` 配 `#[must_use]` 是常见搭配

> 详细 doc comment 格式见 `references/02-documentation.md`。
