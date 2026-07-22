---
name: euv-app
description: 'Tauri 2.x Android packaging for the euv framework. Bundles the euv web frontend as a standalone Android APK (productName `Euv`, identifier `com.euv`). Uses tauri-plugin-log + tauri-plugin-opener + reqwest, exposes a Rust bridge (`src-tauri/src/bridge/`) for the web view, and ships a `bundled-cache` + `sdk` for offline use. Triggers: euv-app, euv APK, Euv Tauri Android, src-tauri, com.euv, tauri-plugin-opener, tauri-plugin-log, euv_app apk.'
license: MIT
---

# euv-app

- GitHub: <https://github.com/euv-dev/euv-app>
- crates.io: _not published_ (no `euv_app` crate on crates.io — the Rust crate lives at `src-tauri/Cargo.toml` as `euv-app` v0.1.0 and is consumed only by the Tauri build)
- docs.rs: _not published_ (the Tauri lib uses `name = "euv_lib"` but is `cdylib + rlib`, not published)

> Tauri 2.x shell that wraps the **euv** web framework as an installable Android APK. Not a Rust library distributed via crates.io — it's a packaging + native-bridge project.

## Overview

`D:\code\euv-app` is a **Tauri Android project**, not a standalone Rust crate. Layout:

```
euv-app/
├── package.json              # name=euv, scripts use build.sh + tauri
├── app.config.json           # runtime config consumed by apply-config.js
├── build.sh                  # android release / android debug entry
├── src-tauri/
│   ├── Cargo.toml            # name=euv-app v0.1.0, lib name=euv_lib (cdylib+rlib)
│   ├── tauri.conf.json       # productName=Euv, identifier=com.euv, frontendDist=../dist
│   ├── capabilities/         # Tauri 2.x permission capabilities
│   ├── icons/                # 32x32, 128x128, 128x128@2x, icon.ico
│   ├── gen/                  # Tauri-generated Android scaffolding (JNI bindings)
│   └── src/
│       ├── main.rs           # Tauri entrypoint
│       ├── lib.rs            # euv_lib root — exports `run()` invoked from main
│       ├── bridge/           # Web ↔ Rust IPC bridge (const / enum / fn / impl / mod)
│       ├── cache/            # bundled-cache layer (const / enum / fn / impl / static / struct / type)
│       └── log/              # tauri-plugin-log wrapper + macros
├── scripts/
│   ├── apply-config.js       # patches app.config.json into the frontend dist
│   ├── prefetch-cache.js     # warm-up `bundled-cache` for offline use
│   ├── gen-icons.py          # regenerate app icons
│   └── setup-sdk.sh          # install Android SDK / NDK
├── sdk/                      # Android SDK + NDK + platform-tools (uncommitted setup)
├── keystore.jks              # signing key for release builds
├── bundled-cache/            # pre-fetched asset cache (offline-mode material)
├── dist/                     # built frontend (populated by `npm run config` + `tauri build`)
├── node_modules/             # @tauri-apps/api ^2.11.0, @tauri-apps/cli ^2.11.2
└── euv.apk                   # built artifact
```

## 项目元信息

- crate 名 (in `src-tauri/Cargo.toml`): `euv-app` (lib name `euv_lib`)
- Rust edition: `2024`
- License: (inherits parent — none declared explicitly; check upstream)
- 类型: Tauri 2.x Android app (`cdylib + rlib`, no published crate)
- 关键字: (Tauri app, not a library)
- Tauri 配置: `productName=Euv`, `identifier=com.euv`, `frontendDist=../dist`, `windows.0 = {title: "Euv", width: 1280, height: 800, resizable: true}`
- Build targets: `bundle.targets = "all"`, `bundle.android.debugApplicationIdSuffix = ".debug"`
- Native bridge deps: `tauri 2.11.5`, `tauri-build 2.6.3`, `tauri-plugin-log 2.8.0`, `tauri-plugin-opener 2`, `reqwest 0.12.28 (rustls-tls-webpki-roots + gzip)`
- Cache deps: `lombok-macros 2.0.31`, `serde 1`, `tokio 1.52.3 (time+fs)`

## Build

```sh
cd D:\code\euv-app

# install JS deps once
npm install

# warm bundled-cache (optional but recommended for offline)
node scripts/prefetch-cache.js

# apply runtime config to dist/
node scripts/apply-config.js

# release Android APK
npm run build:android
# → ./euv.apk

# debug Android APK
npm run build:android:debug

# generate icons
npm run icons

# open Tauri devtools
npm run tauri dev
```

`build.sh android release` is the underlying entry — invokes `tauri build --target android --release` plus the JNI/gen scaffolding.

## Native bridge (`src-tauri/src/bridge/`)

Tauri exposes JS-callable Rust functions via the bridge module. Files are split by Rust keyword: `const.rs` / `enum.rs` / `fn.rs` / `impl.rs` / `mod.rs`. The bridge is invoked from the euv frontend via `@tauri-apps/api`'s `invoke()`.

```rust
// src-tauri/src/bridge/mod.rs
#[tauri::command]
pub fn open_external_url(url: String, opener: tauri::AppHandle) -> Result<(), String> {
    tauri_plugin_opener::open_url(url, None::<&str>).map_err(|e| e.to_string())
}
```

Frontend usage:

```js
import { invoke } from '@tauri-apps/api/core';
await invoke('open_external_url', { url: 'https://euv.dev' });
```

## Cache (`src-tauri/src/cache/`)

Pre-fetched asset cache loaded from `bundled-cache/` at startup. Files split by Rust keyword: `const.rs` / `enum.rs` / `fn.rs` / `impl.rs` / `static.rs` / `struct.rs` / `type.rs`. Paired with `scripts/prefetch-cache.js` which downloads assets ahead of time so the APK can run offline.

## Log (`src-tauri/src/log/`)

Thin wrapper over `tauri-plugin-log` with custom macros (`log/macros.rs`). Call sites use:

```rust
use euv_lib::log::macros::*;
info!("bridge open_external_url: {}", url);
```

Log output goes to both Android logcat (via tauri-plugin-log) and `dist/logs/` on the device.

## Related skills

- `euv` — frontend framework this app packages
- `euv-standards` — frontend coding standards (`App::mount`, `App::use_signal`, html!/class! macros)
- `euv-ui-standards` — UI design system (304 class! + design tokens)
- `euv-html-macro-traps` — html! / class! macro pitfalls
- `tauri` ecosystem (third-party skill, see `<Tauri>` plugin catalog)
- `agent-file-standards` — Tauri `dist/` + `bundled-cache/` + `node_modules/` are exempt from temp-file rules; only repo-tracked sources are subject
