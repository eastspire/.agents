# Cargo.toml 模板

## 普通 lib crate

```toml
[package]
name = "my-crate"
version = "0.1.0"
edition = "2024"
exclude = ["target", "sh", ".github", "Cargo.lock"]

[lib]

[dependencies]
serde = { version = "1.0", features = ["derive"] }
thiserror = "1.0"

[dev-dependencies]
tokio = { version = "1", features = ["full"] }

[profile.dev]
incremental = false
opt-level = 3
lto = true
panic = "unwind"
debug = false
codegen-units = 1
strip = "debuginfo"

[profile.release]
incremental = false
opt-level = 3
lto = true
panic = "unwind"
debug = false
codegen-units = 1
strip = "debuginfo"
```

## proc-macro crate

```toml
[package]
name = "my-macros"
version = "0.1.0"
edition = "2024"
exclude = ["target", "sh", ".github"]

[lib]
proc-macro = true

[dependencies]
syn = { version = "2", features = ["full"] }
quote = "1"
proc-macro2 = "1"

[profile.dev]
incremental = false
opt-level = 3
lto = true
panic = "unwind"
debug = false
codegen-units = 1
strip = "debuginfo"

[profile.release]
incremental = false
opt-level = 3
lto = true
panic = "unwind"
debug = false
codegen-units = 1
strip = "debuginfo"
```

## bin crate(必须上传 Cargo.lock)

```toml
[package]
name = "my-bin"
version = "0.1.0"
edition = "2024"
exclude = ["target", "sh", ".github"]

[[bin]]
name = "my-bin"
path = "src/main.rs"

[dependencies]

[profile.dev]
incremental = false
opt-level = 3
lto = true
panic = "unwind"
debug = false
codegen-units = 1
strip = "debuginfo"

[profile.release]
incremental = false
opt-level = 3
lto = true
panic = "unwind"
debug = false
codegen-units = 1
strip = "debuginfo"
```
