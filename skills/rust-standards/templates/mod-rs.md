# mod.rs 模板(四种)

> **硬性规则**:`mod.rs` 不加任何注释,三段式无空行分隔。

## 标准版(完整版,含 trait + type)

```rust
mod r#enum;
mod r#impl;
mod r#struct;
mod r#trait;
mod r#type;

pub use {r#enum::*, r#struct::*, r#trait::*, r#type::*};

use super::*;
```

## 简化版(仅 impl + struct)

```rust
mod r#impl;
mod r#struct;

pub use r#struct::*;

use super::*;
```

## 私有版(所有符号仅 crate 内可见)

```rust
mod r#const;
mod r#enum;
mod r#fn;
mod r#impl;
mod r#static;
mod r#struct;
mod r#type;

pub(crate) use {r#const::*, r#enum::*, r#fn::*, r#impl::*, r#static::*, r#struct::*, r#type::*};

use super::*;
```

## 测试子目录版(仅 fn,最简形态)

```rust
mod r#fn;

use super::*;
```
