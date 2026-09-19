# euv 性能审计发现清单 (v0.22.2 — example + cli + workspace build config)

> 实测自 `~/github/euv-dev/euv` @ commit `398924c7`（v0.22.2, 2026-09-13, upstream master）。
> 范围: `example/src/**`（用户可见 WASM demo 应用）、`cli/src/**`（euv-cli 构建工具）、workspace `Cargo.toml` profiles。
> 审计侧worker: example+cli+build config。core/engine/ui/macros 由并行 worker 覆盖。
> 成本模型不变：**主要成本单位 = JS 边界穿越 + 堆分配**。
> 行号按 v0.22.2 实测；重查时按函数名 grep。
> **注意**: example 是 demo 代码，发现按"示例代码误导用户复制坏习惯 + 演示页自身流畅度"双重意义定级，整体严重度低于 framework 同级项。

## 0.20.6 → 0.22.2 本范围内的状态对账

- **"euv-cli 仍无 wasm-opt 步骤"（0.20.6 非性能观察）→ 部分失效 (verified_closed: partial)**。euv-cli 自身确实仍无 wasm-opt 调用（`grep -rniE 'wasm[-_]?opt|binaryen' cli/src` = 0 命中），`build_wasm` 只 spawn `wasm-pack build`（cli/src/build/fn.rs:713-801）。但 wasm-pack 0.15 在 release 模式**默认跑 wasm-opt**——实证：对 `example/pkg/euv_example_bg.wasm`（1,527,851 B, 2026-09-11 构建）重跑 `wasm-opt -O3` 产物反而 +74 B（1,527,925 B），重跑 `-Oz` 仅省 2.4%（1,491,802 B）。已是优化过的产物，-Oz 残余空间约 36 KB ≈ 2.4%。**真正的问题不是"没跑 wasm-opt"，而是 -Oz 配置不在生效路径上**（见 CLI-1）。
- dev server `.wasm` MIME → `application/wasm` 正确（http-type 20.1.9 `FileExtensionWasm => APPLICATION_WASM`），wasm-pack `init()` 的 `instantiateStreaming` 路径可用 (verified_closed: yes)。
- raytrace/lighting 的 put_image_data 单帧单调用 + 持久 framebuffer 模式（0.20.6 闭环#4 的 example 侧）完好：lighting/hook/lighting_fn.rs:371-382、raytrace/hook/fn.rs:552-557，持久 `Rc<RefCell<Vec<u8>>>` framebuffer + `Clamped(&mut [u8])` 零拷贝 view (verified_closed: yes)。

## 一档：example 热路径（每帧 / 每事件）

### E1. game_3d `render_scene` 每帧分配风暴 + 未提升的 style key

example/src/page/game_3d/hook/fn.rs:227-317（fn 入口 :227）。

- 每帧每 cube（默认 4 个）：:243-255 `cube_batches` Vec + 每 cube 1 个 `world_vertices` Vec（8 顶点）; :262 `face_batches` Vec::new(); :264 每可见面 `vec![4 verts]`; :285-288 每面 `screen_vertices` collect Vec; :297 `collect_visible_edges` 每 cube 1 个 HashSet 分配 + 内部 :340 又重复 `vec![4 verts]` ×6 面 + 结果 Vec。
- 每帧每 cube 2 次 `Reflect::set` + 4 次 `JsValue::from_str`：:279-283（fillStyle）、:298-301（strokeStyle）——**property key 的 from_str 在 cube 循环内**（对比 game_2d :944 已提升出循环，game_3d 没有）。
- 量化：4 cube/帧 ≈ **50+ 次堆分配 + 8 次 Reflect 穿越 + 16 次 JS 字符串分配/帧** @60fps。
- 修法：顶点/面改定长数组（`[Vector3D; 8]` / `[Vector3D; 4]`，Vector3D 是 Copy）；HashSet 改 12 元素线性扫描；两个 style key 提升为循环外 lazy 常量；fill/stroke 用 typed `set_fill_style_str`。
- api_safe: true（example 内部）。severity: **medium**（demo 页本身最重单帧函数）。

### E2. `interpolate_balls` / `interpolate_cubes` 每帧全量 clone（含 String 字段）

example/src/page/game_2d/hook/fn.rs:904-920、game_3d/hook/fn.rs:428-444。

- `Ball.color: String`（game_2d/hook/struct.rs:11-14）与 `Cube3D.face_color/edge_color: String`（game_3d/hook/fn.rs:69-94 由 `&'static str` 调色板 `to_string()` 而来）→ 每帧 N 次 String clone + Vec collect。WebGPU/WebGL 路径（game_2d:2015-2018）clone 完 Ball 后只取 pos+重新 parse hex（`game_2d_hex_to_rgb` :1498 每球每帧字符串解析）——String clone 纯属浪费。
- 频率：每帧 × N 实体（game_2d 可达 100 球）。
- 修法：颜色字段改 `&'static str`（调色板本来就是 `random_ball_color() -> &'static str`，fn.rs:23）；或插值只拷贝位置进 scratch buffer，渲染直接读原数组。
- api_safe: true。severity: **medium**。

### E3. 4 个 GPU render loop 每帧 `getComputedStyle` 轮询主题色

game_2d/hook/fn.rs:2028（WebGPU loop）/ :2535（WebGL loop）、game_3d/hook/fn.rs:1735 区域（WebGPU）/ :2196 区域（WebGL），全部调用 `game_2d_canvas_clear_color`（:1525-1550）/ `game_3d_canvas_clear_color`（:1201+）= 每帧 query_selector + **getComputedStyle** + get_property_value + 字符串 parse。

- getComputedStyle 是 DOM 最贵读取之一（可强制 style recalc）。注释自称"computed style is cached by the engine"——但本函数直接读 DOM，无缓存。
- 频率：每帧 × 当前激活的 GPU demo 页。
- 修法：主题切换事件/Signal 驱动重读；或 init 读一次 + `matchMedia`/主题 hook 订阅。
- api_safe: true。severity: **medium**。

### E4. canvas 画板每 mousemove/touchmove 重取 context + 重放不可变 style + HashMap signal clone

example/src/page/canvas/hook/fn.rs：

- `continue_drawing`（:163-207）每 mousemove：query_selector(:177) + get_context(:185) + `CanvasRenderer::enable_smoothing_on`(:193 → engine apply_quality ≈ 7 次 JS 穿越：set_image_smoothing_enabled + 2×Reflect::set + 4×from_str，见 0.20.6 #32) + `Reflect::set` strokeStyle(:194-198，2×from_str) + `state.get_stroke_color().get()`（String clone）。
- `continue_drawing_multi_touch`（:403-463）每 touchmove 同上，另加 get_bounding_client_rect(:431) + `state.get_touch_last_points().get()`（:441，**整个 HashMap clone**）+ `.set()` 回写（:462）。
- 频率：60-120Hz 事件流。量化：每事件 ≈ 15 次 JS 穿越 + 1 HashMap clone + 2 String clone。
- 修法：context/rect 在 start_drawing 时缓存进 Rc 闭包状态（stroke 内不变）；smoothing 只在 context 首次获取时 apply；`touch_last_points` 用 `Rc<RefCell<HashMap>>`（view 层未订阅该 signal，见 canvas/view — 写穿 signal 纯属当 RefCell 用）；strokeStyle 用 typed setter。
- api_safe: true。severity: **medium**。

### E5. list 页（1000 项 todo）：view 每次 render clone 整个 `Vec<String>`，输入框每 keystroke 触发全量重渲染

example/src/page/list/view/fn.rs:56 `for (index, item) in state.get_items().get().iter().enumerate()`——`Signal<Vec<String>>::get()` 深 clone 1000 个 String；循环内 :58/:60 每 item 2×`to_string()` + :63 `item.clone()`。hook/fn.rs:51-60 `todo_list_on_input_new_item` 每 keystroke `set(input.value())` → 全页重渲染 → 上述 1000 项 VDOM 重建 + 3000+ 次 String 分配/keystroke。add/remove（hook/fn.rs:77/:100）再各付 2 次全 Vec clone。

- 修法：demo 视角——items 分页/窗口化；或 item 文本提取为独立子组件 + key 稳定化让 renderer 跳过；`get()` 改 `with()` 借读（PR #179 已提供 API）。
- api_safe: true。severity: **medium**（per-keystroke 最重 demo 页）。

### E6. raytrace `present_raytrace_framebuffer` 每帧新建 canvas + 2d context

example/src/page/raytrace/hook/fn.rs:526-574：每帧 `create_element("canvas")`(:538) + set_width/height + `get_context("2d")`(:546-551) + `ImageData::new`(:552) + put_image_data + draw_image + SSAA present。

- 量化：每帧 ≈ 8-10 次 JS 穿越 + 2-3 个 JS 对象分配（canvas 元素、context、ImageData），framebuffer 尺寸固定（ladder 档位内）→ 全部可缓存。
- 修法：SSAA cache 旁边加 `source_canvas` cache（档位切换时随 framebuffer 一起重建）。
- api_safe: true。severity: **low-medium**。

## 二档：局部 / 事件级

### E7. 所有 RAF loop 每帧 query_selector + getBoundingClientRect + clientWidth/Height 轮询

- game_2d Canvas2D loop：每帧 `game_2d_canvas_detached`（query_selector, fn.rs:1481 经由 :1206）+ `handle_rescale_dirty_canvas2d` 内 `read_canvas_size`（query_selector + getBoundingClientRect, :430-431）+ clientWidth/Height ×2(:439-444) + render 块再读 clientWidth/Height(:1287-1291) ≈ **7-8 次 JS 穿越/帧**纯轮询。
- game_3d(:702 detached + :756 read_canvas_size)、raytrace(:660 detached + :692-693 read size)、lighting 同构。
- 修法：detached 检查降频（每 30 帧一次）或用 MutationObserver；尺寸轮询合并为一次 read，ResizeObserver 已存在于 raytrace(:1490) 可推广。
- api_safe: true。severity: **low-medium**。

### E8. game_3d/raytrace/canvas 事件提取走 `Reflect::get(event, from_str("clientX"))` 而非 typed getter

game_3d/hook/fn.rs:953-957/:987-991/:1030-1045（拖拽旋转 mousemove/touchmove）、raytrace/hook/fn.rs:941-957/:1048-1063、canvas/hook/fn.rs:282-322（offsetX/clientX/clientY）。每事件 2-6 次 Reflect + from_str（JS 字符串分配）。engine #39（input typed getter）的同 pattern example 版。

- 修法：`event.unchecked_ref::<MouseEvent>().client_x()` / `TouchEvent` typed API（web-sys features 已含 MouseEvent/TouchEvent）。
- api_safe: true。severity: **low-medium**（仅拖拽期间高频）。

### E9. raytrace/lighting `devicePixelRatio` 走 Reflect（8 处）

raytrace/hook/fn.rs:1511/:1602/:1882/:1973、lighting/hook/lighting_fn.rs:902/:984/:1219/:1302。全在 ResizeObserver/init 路径（非每帧）。web-sys `Window::device_pixel_ratio()` typed getter 可用（`Window` feature 已开）——engine `detect_dpr`（renderer/impl.rs:149-161）注释声称"web-sys 无 native getter"是错的，example 照抄了该模式。

- 修法：`window_value.device_pixel_ratio()` 一行。
- api_safe: true。severity: **low**。

### E10. `pack_game_2d_balls_webgpu/webgl` 每帧新 Vec + per-ball hex parse

game_2d/hook/fn.rs:1626-1640（webgpu：每帧分配 4+100×8 floats 的 Vec，靠 resize 撑到全量）/ :1658-1667（webgl：2 个 Vec/帧）。配合 E2 的 clone，每帧 GPU 路径 = N Ball clone + N 次 hex parse + 1-2 个 Vec 分配。修法：持久 scratch buffer + 颜色入 Ball 时预存 rgb 三元组。api_safe: true。severity: **low-medium**。

### E11. virtual_list demo 页每可见项 2×format! + to_string（scroll 驱动 render）

example/src/page/virtual_list/view/fn.rs:22/:26/:30。叠加 ui#24（组件侧 format!/key 每帧）与 `on_visible_range_change` 每次 scroll set signal → 整页重渲染。api_safe: true。severity: **low**（demo 侧镜像项，主账在 ui#24）。

### E12. 一次性 `Closure::forget()` 泄漏（loading overlay / set_loaded_delayed）

raytrace:650-655、lighting、game_2d:1150-1155 等：每次 loop 启动泄漏 1 个 Closure（有界，每页访问次数级）。同族老问题 ui#26（camera 每 tick 泄漏 2 个）已在清单。api_safe: true。severity: **low**。

### E13. form 页每 keystroke `input.value()` + `signal.set` → 全页重渲染

form/hook/fn.rs:106-148。demo 固有写法（euv 响应式表单的标准用法），真正的成本在 framework 侧重渲染路径（0.20.6 一档#1/#36）。仅记录，不单列。severity: informational。

## CLI（euv build / euv run 发布管线现状）

### CLI-1. 无 wasm-opt 步骤；-Oz 配置挂在**不生效的** crate 上

- 现状管线：`run_build_pipeline`（cli/src/build/fn.rs:592-629）= `euv fmt` → `build_wasm`（spawn `wasm-pack build [--release] --target web --out-dir ...`，:713-801）→ `generate_html`。CLI 源码 0 处 wasm-opt/binaryen（grep 实证）。用户可在 `--` 后透传 wasm-pack 参数（`filter_euv_args` :35-61），但 wasm-pack 不接受任意 wasm-opt flags，只认 crate Cargo.toml 的 `[package.metadata.wasm-pack]`。
- **关键**: root Cargo.toml:292-306 的 `[package.metadata.wasm-pack.*] wasm-opt = ["-Oz", ...]` 挂在 root `euv` 包上；euv-cli 在 **被构建 crate 目录**（如 example/）跑 wasm-pack（:737 `current_dir(args.get_crate_path())`），wasm-pack 读的是 `example/Cargo.toml`——**该文件无此 section**（example/Cargo.toml 全文 45 行，无 metadata）。root 的 -Oz 配置对实际构建路径是死配置。
- 实测残余空间：对现有 release 产物重跑 -Oz 仅 -2.4%（1,527,851 → 1,491,802 B），因为 wasm-pack 默认已优化。所以本条是"可控性/正确性"问题，不是大的 size 泄漏。
- 修法：把 `[package.metadata.wasm-pack]` 挪进 `example/Cargo.toml`（api_safe: true，demo crate 配置）；CLI 侧可选加 `--wasm-opt-args` 透传或在 release 后自跑 wasm-opt（api_safe: true，CLI 内部）。
- severity: **low**（实测增益 2.4%）；correctness-of-config 角度 medium-low。

### CLI-2. workspace `[profile.dev]` = release 级 codegen，拖慢 `euv run` HMR 迭代

root Cargo.toml:308-315：`[profile.dev] opt-level = 3, lto = true, codegen-units = 1, incremental = false`。`euv run` 默认 dev 模式（`resolve_build_mode` 默认 Dev，build/fn.rs:179-201）→ **每次文件变更的全量 rebuild 付 release 级 LTO 成本**；`incremental = false` 又关掉增量。watch 链路（:640-697）debounce 500ms+300ms 后串行重建。
- 对 wasm 演示页这是刻意的（dev 也要跑得快/接近真机性能），但应在注释里写明取舍，或提供 `--fast-dev` 档。
- 修法：dev 拆两档（默认 dev-debug 快编 + `--release` 跑性能），或至少在 profile 上注释意图。
- api_safe: true。severity: **low-medium**（dev-loop 体验）。

### CLI-3. `[profile.release]` 非标准 wasm 发布形态

root Cargo.toml:317-324：`opt-level = 3, lto = true, codegen-units = 1, panic = "unwind", strip = "debuginfo"`；另有 :329-330 `[profile.release.package.euv-example] opt-level = "z"`——**只有 example crate 自身编 -Oz，所有 framework 依赖（体积大头）仍 -O3**。

- `panic = "unwind"`：wasm32-unknown-unknown 无 unwinding（实际降级为 abort），但显式 `panic = "abort"` 是 wasm 发布标准写法，避免 host-side 目标/工具链歧义。
- `strip = "debuginfo"` vs `strip = true`：wasm 产物 symtab 残余可再削。
- 标准 wasm release 形态：`opt-level = "z"`（或 "s"）+ `lto = true` + `codegen-units = 1` + `panic = "abort"` + `strip = true`，再叠 wasm-opt -Oz。
- api_safe: true（workspace 构建配置）。severity: **low**（size 维度，实测 wasm-opt 端只剩 2.4% 空间）。

### CLI-4. dev server 小项

- `server_config.set_nodelay(Some(false))`（cli/src/mode/fn.rs:124）：Nagle 开启，局域网/本机小响应多付延迟；dev server 建议 nodelay(true)。severity: low。
- `RequestMiddleware` 对所有响应 `no-cache, no-store`（server/impl.rs:29-36）：dev 正确，无需改。
- release/dev HTML 模板（build/const.rs:126/:199）：`await init(); main();` 串行；无 `<link rel="preload" as="fetch" type="application/wasm">` 提示——1.5MB wasm 可提前并行拉取。severity: low（load perf）。
- 加分项：`.wasm` → `application/wasm` 正确（streaming compilation 可用，verified_closed）。

## 建议动手顺序（本范围内）

1. E3（getComputedStyle 每帧 × 4 loop）——改动最小、收益最直接，每帧省一次潜在 style recalc。
2. E1 + E2 + E10（game_3d/game_2d 帧内分配三件套：定长数组化 + 颜色 `&'static str` + scratch buffer）——一个 PR 内做完，game 页帧成本可降一个量级。
3. E4（canvas 事件路径缓存 context + 去掉 per-event apply_quality + HashMap 挪出 Signal）。
4. E5（list 页 `Signal::with` 借读 + key 稳定化）。
5. CLI-2/CLI-3（profile 整理 + metadata 挪位）——配置级小 PR。
6. E6/E7/E8/E9 打包扫尾。

## 非性能观察

- example 侧 `Reflect::get(window, "devicePixelRatio")` 模式（E9）是从 engine `detect_dpr` 的错误注释复制而来——engine 侧修正后 example 8 处应同步。
- game_2d/game_3d/raytrace/lighting 四个页面各自复制了 `read_canvas_size` / `*_canvas_detached` / `draw_*_loading` / `set_loaded_delayed` 近重复实现（~200 行×4），长期可下沉为 example 共享 helper（也会进入 wasm 产物体积）。
