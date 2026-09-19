# lib.rs 模板

## 普通 lib crate

```rust
mod config;
mod context;
mod error;
mod hook;
mod route;
mod server;

pub use {config::*, context::*, error::*, hook::*, route::*, server::*};

pub use {external_dep_1::*, external_dep_2};

use std::{
    cmp::Ordering,
    collections::HashSet,
    future::Future,
    hash::{Hash, Hasher},
    io::{self, Write, stderr, stdout},
    pin::Pin,
    sync::Arc,
};

use current_crate::*;

use {
    external_crate_1::*,
    external_crate_2::{Deserialize, Serialize},
    external_crate_3::{
        net::{Listener, Stream},
        spawn,
        sync::watch::{Receiver, Sender, channel},
        task::JoinHandle,
    },
};
```

**常见违规**(详见 `references/06-module-imports.md` §6.1):

1. private use 写到 pub use 之前
2. `pub use {sub-modules::*}` 放到 `pub use std` / `pub use external` 之后
3. mod 列表中插空行
4. 单条 `use external_crate::Symbol;` 没并入 `use {...}` 块(如 `use log::SetLoggerError;` 单独成行)

## proc-macro lib.rs(子模块名不带 r#)

```rust
mod helper;

use {helper::*};

use proc_macro::TokenStream;

#[proc_macro_attribute]
pub fn my_attr(_args: TokenStream, input: TokenStream) -> TokenStream {
    input
}
```
