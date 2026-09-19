# bin target with sub-files (`src/bin/<name>/main.rs` + keyword files)

> **Use when**: CLI / binary exceeds ~150 lines, OR you want to honour
> §1.3 keyword-purity for a binary target. Verified against
> `eastspire/euv-docs` PR #31 (feat/cli-binary, 2026-09-18).

## Cargo.toml

```toml
[[bin]]
name = "my-cli"
path = "src/bin/my_cli/main.rs"
required-features = []
```

`required-features = []` is empty by default — leave it empty unless the
bin actually depends on `#[cfg(feature = "...")]` items. An empty list
is fine.

## File layout

```
src/bin/my_cli/
├── main.rs        — bin entry (mod declarations + pub use glob + fn main)
├── const.rs       — semantic constants
├── struct.rs      — one pub struct per file (the parsed CLI args)
└── fn.rs          — free functions: parse_args / run / print_usage
```

5 keyword files at most (const / struct / fn / impl / enum / trait /
type / static). Drop the ones you don't need.

## main.rs (bin entry)

```rust
mod r#const;
mod r#fn;
mod r#struct;

pub use {r#const::*, r#fn::*, r#struct::*};

use std::{
    env,
    iter::Skip,
    path::PathBuf,
    process::{Command, ExitCode, exit},
};

fn main() -> ExitCode {
    // ... uses parse_args(), run(), print_usage() — all glob-imported.
}
```

**Three-segment structure** (mirror mod.rs 三段式, even though main.rs
is not literally a mod.rs — same spirit):

1. `mod r#xxx;` declarations (raw identifier, keyword file convention)
2. `pub use {r#xxx::*, ...};` glob re-export — **without this line the
   sub-files can't see each other**
3. private `use std::{...};` block (single-line block form per §6.1)

**Critical**: `pub use {r#const::*, r#fn::*, r#struct::*};` is what makes
the sub-files work. Without it, `use super::*;` inside `fn.rs` only
inherits the *use statements* from main.rs, not the *mod declarations*.
You'll get `error[E0425]: cannot find type 'Args' in this scope`
inside fn.rs even though `mod r#struct;` is declared in main.rs.

## sub-file pattern (struct.rs, fn.rs, const.rs)

```rust
// const.rs — has no parent-symbol dependency, NO `use super::*;` (would
// trigger `unused_imports` warning per §6.4)

/// One parsed CLI invocation.
pub struct Args {
    pub src_dir: PathBuf,
    pub out_dir: PathBuf,
    pub name: &'static str,
    pub release: bool,
}
```

```rust
// fn.rs — first line MUST be `use super::*;` per §6.3
use super::*;
use std::path::Path;   // any extra std items sub-file needs (NOT in main.rs)

pub fn parse_args() -> Result<Args, String> { /* ... */ }
pub fn run(args: &Args) -> Result<(), String> { /* ... */ }
pub fn print_usage() { /* ... */ }
```

```rust
// const.rs — semantic constants in alphabetical-by-(name_len, name_lex) order
pub const DEFAULT_NAME: &str = "my_cli";
pub const PKG_DIR_NAME: &str = "pkg";
pub const CONFIG_FILE_NAME: &str = "config.toml";
```

## Things that DO NOT work (learned the hard way)

1. **`env!("LITERAL")` cannot accept a const expression**:
   ```rust
   // ❌ Compiler error: "expected string literal"
   let manifest_dir = PathBuf::from(env!(CARGO_MANIFEST_DIR_MACRO));

   // ✅ Always pass a literal string
   let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
   ```
   Other macros with the same restriction: `concat!()`, `include!()`,
   `include_str!()`, `include_bytes!()`, `module_path!()`,
   `stringify!()`. Their arguments must be string literals, NOT
   `pub const FOO: &str = "..."` re-exported from const.rs.

2. **Sub-file `use super::*;` only inherits use items, NOT mod
   declarations** (see main.rs section above). Symptom:
   `error[E0425]: cannot find type 'Args' in this scope` inside fn.rs.
   Fix: add `pub use {r#const::*, r#fn::*, r#struct::*};` to main.rs.

3. **`<sub-file>` declared in main.rs gets `unused_imports` warning
   on `use super::*;` IF the sub-file doesn't reference any super
   symbol**. Workaround: omit `use super::*;` from that sub-file (it's
   optional for `const.rs` per §6.3 exception). Symptom: warning on
   const.rs line 1.

4. **`pub use` glob visibility must ≤ glob-internal items**: if a
   sub-file contains `pub(crate) const`, the `pub use` in main.rs must
   be `pub(crate) use` — not plain `pub use`. Per §6.1 pitfall-a.

## §1.3c carve-out for built-in macros

`env!()` / `concat!()` / `include!()` / etc. take string LITERALS, not
const references. So when extracting magic strings to const.rs, you
**cannot** replace `env!("CARGO_MANIFEST_DIR")` with
`env!(CARGO_MANIFEST_DIR_MACRO)`. Same for `include!("foo.txt")` vs
`include!(FOO_PATH)`. Keep these specific macro arguments as literals;
extract everything else to const.rs.

## Verification

```bash
cargo build --bin my-cli           # rc=0
cargo clippy --bin my-cli          # 0 warnings on bin
cargo fmt --all -- --check         # idempotent
euv fmt && euv fmt                 # 0 files changed
python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py <repo-root>  # 19/19 PASS
```

The `audit_rust_standards.py` check 1 / check 7 white-lists
`src/bin/<name>/<seg>.rs` and `src/bin/<name>.rs` via audit-pitfalls
§39a — they are NOT reported as keyword-purity violations.