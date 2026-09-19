# wasm-pack --out-name 与 index.html 期望文件名错位陷阱

## 现象

改了 `core/src/**` 或 `ui/src/**` 源码后:

- `cargo check -p <crate> --target wasm32-unknown-unknown` ✅ 干净
- `cargo test -p <crate> --test mod` ✅ 全 pass
- `wasm-pack build --target web --release --out-dir www/pkg` ✅ success
- headless Chromium 加载页面 → **行为完全没生效**

## 根因(本会话 euv example 滑块回归教训,2026-09-05)

`example/Cargo.toml`:

```toml
[package]
name = "euv-example"
version = "0.18.59"
...
```

`www/index.html`(手写早期模板,固定 import 路径):

```html
<script type="module">
  import init, { main } from './pkg/euv.js';
  await init();
  main();
</script>
```

`wasm-pack build --target web --release --out-dir www/pkg`(无 `--out-name`)
默认 `--out-name = <crate-name>`(`-` 转 `_`):

```
www/pkg/
├── euv.js                  ← 旧文件,首次 build 时间戳 11:40
├── euv.js.map              ← 旧
├── euv_bg.wasm             ← 旧(用户实际加载的)
├── euv_example.js          ← 新的(每次 build 更新)
├── euv_example.js.map
├── euv_example_bg.wasm
└── ...
```

每次 rebuild **生成新 `euv_example.{js,_bg.wasm}` 同时保留旧 `euv.{js,_bg.wasm}`**
(`euv.js` 时间戳停留)。`index.html` 加载 `./pkg/euv.js` → 旧 `euv.js` →
间接 load 旧 `euv_bg.wasm` → 用户看不到任何源码改动生效。

## 诊断步骤(必跑,按顺序)

### 1. 列文件 mtime

```bash
ls -la www/pkg/
```

**所有"被 index.html 引用"的入口文件 mtime 必须 ≤ 30 秒**。看到 `euv.js`
mtime 是 `Sep  5 11:40` 但 `euv_example.js` 是 `Sep  5 13:14` → 入口
引用错位。

### 2. 提取 import 路径

```bash
grep -n "import" www/index.html
```

输出:
```
import init, { main } from './pkg/euv.js';
```

期望 wasm-pack 产出: `euv.js` + `euv_bg.wasm`(`--out-name euv`)。

### 3. 字符串验证 wasm 内容

```bash
strings www/pkg/euv_bg.wasm | grep -E "0\.18\.[0-9]+"
```

如果输出 `0.18.59` 而 Cargo.toml 已经是 `0.18.60` → **这个 wasm 不是当前
源码 build 的**(用的是 cache / 旧文件 override)。

### 4. headless 浏览器行为验证(终极)

```python
# CDP 抓 input className
r = send("Runtime.evaluate", {"expression": """
document.querySelector('input#color-mixer-red')?.className
""", "returnByValue": True})
```

如果期望 `c_binding_slider c_slider_value-XXX` 但实际只有 `c_slider_value-XXX`
→ 加载的 wasm 是旧版,即使 Cargo.toml / build / CI 全 pass。

## 修复方案

### A. 强制 `--out-name` 对齐(推荐)

```bash
wasm-pack build --target web --release --out-dir www/pkg --out-name euv
```

产出固定 `euv.js` + `euv_bg.wasm`,每次 build 覆盖。**改动只在 build 命令
脚本里,不动源码、不动 index.html、不动 Cargo.toml**。

### B. 改 index.html 跟 wasm-pack 默认走

```html
<!-- before -->
import init, { main } from './pkg/euv.js';
<!-- after -->
import init, { main } from './pkg/euv_example.js';
```

需要同步确认 `www/pkg/euv_example.d.ts` 等其他引用。

## 预防 checklist(部署 / 发布前)

- [ ] **CI build 步骤写明 `--out-name`**(不要依赖 wasm-pack 默认)
- [ ] `euv build` 等框架 CLI 的 `--out-name` 默认值 vs 项目 `index.html`
      期望 — 不一致时显式 override
- [ ] 任何 wasm rebuild 后 `ls -la www/pkg/` 看 mtime
- [ ] mtime 停留超过 build 时间 = 用了 cache / 错文件
- [ ] headless browser 行为验证是终极证据,不能只信 wasm 字符串

## 同类陷阱(cargo 工具链)

- **trunk** for Rust web frontend: `trunk build` 默认用 `<crate-name>.html`
  文件名,如果 `index.html` 是手写的 fixed path 可能也踩到。
- **wasm-bindgen**(非 wasm-pack): 直接输出 `<crate>_bg.wasm` + `<crate>.js`,
  无 `--out-name`,依赖 crate 名字。

## 本会话 incident 时间线

- 13:00 — 改 `core/src/vdom/attribute/impl.rs`,加 `Self::CssRef` 分支
- 13:01 — `cargo test -p euv-core --test mod` 172/172 pass
- 13:03 — `cargo check -p euv-core --target wasm32` clean
- 13:05 — `wasm-pack build --release --out-dir www/pkg` → 产出
  `euv_example_bg.wasm`,但 `euv_bg.wasm` 留 11:40 旧版
- 13:07 — `strings euv_example_bg.wasm | grep MERGE_CLASS` → 没找到
  (console.log string 在 wasm 里但 trace 没触发)→ **误判为 wasm-opt
  dead-code-elim 整段**
- 13:09 — 多次 rebuild + force-reload + disable cache + network.setCacheDisabled
  → UI 行为仍然不生效
- 13:11 — `strings euv_example_bg.wasm | grep 0.18` → `0.18.60` ← 新版 wasm 是
  0.18.60,但浏览器加载的是 `euv_bg.wasm`(0.18.59 旧版)→ **root cause**
- 13:12 — `wasm-pack build --out-dir www/pkg --out-name euv` → `euv_bg.wasm`
  mtime 更新到 13:12
- 13:13 — headless reload → 滑块 `class="c_binding_slider c_slider_value-XXX"`,
  flex `1 1 0%`,height `24px` ✅ **fix verified**

**30 分钟浪费在 trace "fix 没生效"**,根因是文件名错位导致**浏览器加载
的是旧 wasm**。**`ls -la www/pkg/` 看 mtime** 是第一步诊断,如果当时先做,
2 分钟定位。

## 教训提炼

**build success ≠ 行为生效**。WASM 项目部署链有 4 个隐藏变量:

1. build 命令的输出文件名(`--out-name` 默认 vs 项目期望)
2. `index.html` 的 import 路径
3. dev server 的 cache(`python3 -m http.server` 默认有 etag/304)
4. browser 的 cache(`chrome --remote-debugging-port` 默认有 disk cache,
   CDP `Network.setCacheDisabled` 才能 bypass)

任何一个对不上,用户看到的都是"修复没生效"。`ls -la` + `grep import` 是 30 秒
诊断全部 4 个变量是否对齐的最快方式。
