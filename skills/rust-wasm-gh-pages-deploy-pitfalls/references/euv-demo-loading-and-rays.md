# euv demo bug-fix playbook (PR #170, 2026-09-07)

> 这次 PR 修了三个 bug 在两个 demo 页面 (`/lighting`, `/raytrace`) × 三个 backend tab
> (Canvas 2D / WebGL / WebGPU) = 6 tabs。本 reference 记下这次踩到的坑,下次再加类似
> "全 6 tab 对齐" 的功能时**直接抄作业**。

## 三大 bug 概览

| Bug | 症状 | 根因 | 修复位置 |
|---|---|---|---|
| 1. Lighting Canvas 2D 永远 loading | `loaded` signal 永 false,overlay 不消失 | `let Some(loading_window) = window() else { return; };` 早 return 跳过后续整个 RAF init | `example/src/page/lighting/hook/lighting_fn.rs:439-441` → 改成 `if let Some(...) = window() { ... }` 块作用域 |
| 2. View 里 `loaded` 不 re-render | 即使 loop 跑通 + signal 变 true,view 不更新 | `let loaded = state.get_loaded().get(); if { !loaded }` snapshot 冻结 signal 值 | `example/src/page/lighting/view/fn.rs` — `euv fmt` 自动重写为 `if { !state.get_loaded().get() }` |
| 3. 光线不是从光源位置发出 | 6 tabs 都不画 ray,或画在错位置 | 完全没有 ray overlay 渲染逻辑 | 6 个 tab 各加 per-backend ray drawing |

## Bug 1 详解:`let-else` 早 return 杀 RAF loop

**症状** (用户原话):"Phong Lighting 页面 Canvas 2D 一直在 loading"。
**真实表现**:
- 页面打开 → "Initializing..." overlay 显示
- 永远不消失,canvas 始终黑屏
- DevTools console 无 error,WASM module init 看起来成功
- 切到 WebGL tab → OK;切回 Canvas 2D tab → 永远 loading

**根因** (`example/src/page/<page>/hook/<page>_fn.rs::start_<page>_loop`):

```rust
// ❌ 错的 — 早 return 跳过整个 init
let Some(loading_window): Option<Window> = window() else {
    return;  // ← 整个函数退出
};

// 后面**必须**执行的初始化,全被跳过:
let raf_closure: Closure<dyn FnMut()> = Closure::wrap(...);
closure_cell.try_set(raf_closure);     // 让 start_timeout callback 找到 closure
App::use_cleanup(move || { ... });      // tab 切换时取消 RAF
let start_closure: Closure<dyn FnMut()> = Closure::wrap(...);
window.set_timeout_with_callback_and_timeout_and_arguments_0(
    &start_callback,
    LIGHTING_LOOP_START_DELAY_MILLIS,  // 调度第一次 RAF
);
```

任何一个 init 被跳过 → `loop_started` signal 永 false → view 里 `if { !loop_started.get() }` 永远 true → loading canvas 永远在。

**触发条件**:`window()` 在 `use_signal` 第一次 mount 时返回 `None`。少见但一发生就 catastrophic。同 codebase 的 `raytrace/hook/fn.rs:596-605` 已经用正确 pattern,可以对照抄。

**正确写法** (抄 `raytrace/hook/fn.rs:596-605`):

```rust
// ✅ 对的 — 块作用域,后续 init 无条件继续
if let Some(loading_window) = window() {
    let loading_closure: Closure<dyn FnMut()> = Closure::wrap(Box::new(move || {
        draw_game_3d_loading(LIGHTING_LOADING_CANVAS_SELECTOR, LIGHTING_CANVAS_SELECTOR);
    }));
    let loading_callback: Function =
        loading_closure.as_ref().unchecked_ref::<Function>().clone();
    loading_closure.forget();
    let _ = loading_window
        .set_timeout_with_callback_and_timeout_and_arguments_0(&loading_callback, 0);
}
// 后续 init 无条件继续 ↓
let raf_closure: Closure<dyn FnMut()> = Closure::wrap(...);
...
```

**反模式**:
- ❌ `let Some(...) = window() else { return; };` —— 早 return 杀 init
- ❌ `window().expect("must have window")` —— panic 整个 wasm 崩
- ❌ `window().unwrap_or_default()` —— `Window` 不是 `Default`,编译不过

**Code review checklist** (任何 `start_<page>_loop` 函数):
- [ ] 不允许 `?` / `else { return }` 早退
- [ ] overlay 绘制是 nice-to-have,init 注册是 must-have
- [ ] `window()` / `document()` / `performance()` 都用 `if let`

## Bug 2 详解:euv fmt 自动 fix snapshot-vs-subscribe

**症状**:即使修了 Bug 1 让 loop 跑通,view 仍然不 re-render,loading overlay 还在。

**根因** (euv signal 的 reactive 语义):

```rust
// ❌ snapshot pattern — 把 signal 当前值冻结到局部变量
let loaded: bool = state.get_loaded().get();   // 此刻 signal 是 false
if { !loaded } {
    html! { div { class: c_loading_overlay() ... } }
}
// loop 跑到 → state.get_loaded().set(true)
// view 不会重新 render,因为它依赖的是局部 `loaded`,不是 signal 自己
```

**euv fmt 的智能修复**:

```rust
// ✅ subscribe pattern — 每次 view render 都重新读 signal
if { !state.get_loaded().get() } {
    html! { div { class: c_loading_overlay() ... } }
}
```

`euv fmt` 检测到 `let x = signal.get(); if { !x }` 这模式,自动 rewrite 去掉局部变量,view 直接依赖 signal → signal 变化触发 re-render → loading 正确消失。

**euv fmt 抓得到 / cargo fmt 抓不到**:
- cargo fmt 只看 Rust 语法,不知道 `Signal<bool>` 的 reactive 语义
- euv fmt 展开 euv 的 `html!` / `Signal::get()` 宏,知道哪些是 reactive 调用

**为什么这是真坑**:
- subagent 写 snapshot pattern 时**完全合理**(防御性局部变量),code review 也不会拦截
- 只有运行时才能发现问题,但运行时表现就是 "loading 永 false" — 跟 Bug 1 一样
- **救星是 `euv fmt`** — 它会在 build 之前自动 rewrite

**commit 前最后一组命令**(坑 21):
```bash
euv fmt                 # 展开宏 + 格式化 + 自动 rewrite 错 pattern
cargo fmt --all         # 同步 cargo fmt 偏好
cargo fmt --all -- --check   # **显式 check,0 输出才算 pass**
euv fmt                 # 再跑一遍确认 idempotent
cargo fmt --all -- --check   # 再 check
```

**反模式** (所有这些都会被 euv fmt 抓并 fix,但你自己写就避免):
- ❌ `let x = state.get_X().get();` 然后 view 用 `x`
- ❌ `let fps_display = format!("{:.1}", fps.get());` 然后 view 用 `fps_display`
- ✅ `format!("{:.1}", fps.get())` 直接放在 view 函数体里
- ✅ `state.get_X().get()` 直接在 `if {}` / `match {}` / `format!()` 表达式内

**诊断**:`grep -n "let.*= state.get.*get()" example/src/page/*/view/*.rs` → 所有匹配都要重审是否 snapshot 冻结了 signal。

## Bug 3 详解:6 tabs × 3 backends × 1 feature 的统一实现

**问题**:euv example 的 `/lighting` 和 `/raytrace` 页面各有 3 个 sub-tab
(Canvas 2D / WebGL / WebGPU),加同一 feature 必须 6 个 backend 都改。

### 6 tabs 实现矩阵

| Backend | ray overlay 实现 | 关键 API |
|---|---|---|
| Lighting Canvas 2D | Bresenham line + manual alpha blend 进 raw RGBA buffer | `buffer[index + 3] = 255;`,逻辑坐标 (320x240) × scale |
| Lighting WebGL | GLSL fragment shader `distance_to_segment` blend | `uniform vec4 u_params[]` (sun pos + sphere centers) |
| Lighting WebGPU | WGSL fragment shader `distance_to_segment` blend | `var<uniform> params: array<vec4<f32>, N>` |
| Raytrace Canvas 2D | SsaaCanvas display canvas overlay (after `present()`) | `cache.0.get_context("2d")`,world→NDC→CSS px 转换 |
| Raytrace WebGL | GLSL fragment shader `distance_to_segment` blend | 投影 sun + 3 object centers → NDC,上传 uniform |
| Raytrace WebGPU | WGSL 同上 | 同上 |

### Canvas 2D raw RGBA Bresenham (Lighting 用)

```rust
fn draw_ray_line(
    buffer: &mut [u8],
    width: u32, height: u32,
    from: (f64, f64), to: (f64, f64),  // logical scene coords (320x240 space)
    scale: f64,                          // = framebuffer_width / LIGHTING_WIDTH
    color: (f64, f64, f64),
    alpha: f64,
) {
    let ax = from.0 * scale;
    let ay = from.1 * scale;
    let bx = to.0 * scale;
    let by = to.1 * scale;
    let dx = (bx - ax).abs() as i32;
    let dy = -(by as i32);
    let sx: i32 = if ax < bx { 1 } else { -1 };
    let sy: i32 = if ay < by { 1 } else { -1 };
    let mut err = dx + dy;
    let mut x = ax as i32;
    let mut y = ay as i32;
    loop {
        if x >= 0 && y >= 0 && (x as u32) < width && (y as u32) < height {
            let idx = ((y as u32 * width + x as u32) * 4) as usize;
            let r0 = buffer[idx] as f64 / 255.0;
            let g0 = buffer[idx + 1] as f64 / 255.0;
            let b0 = buffer[idx + 2] as f64 / 255.0;
            buffer[idx]     = ((1.0 - alpha) * r0 + alpha * color.0).clamp(0.0, 1.0).mul_add(255.0, 0.0) as u8;
            buffer[idx + 1] = ((1.0 - alpha) * g0 + alpha * color.1).clamp(0.0, 1.0).mul_add(255.0, 0.0) as u8;
            buffer[idx + 2] = ((1.0 - alpha) * b0 + alpha * color.2).clamp(0.0, 1.0).mul_add(255.0, 0.0) as u8;
            // alpha 通道保留
        }
        if x as i32 == bx as i32 && y as i32 == by as i32 { break; }
        let e2 = 2 * err;
        if e2 >= dy { err += dy; x += sx; }
        if e2 <= dx { err += dx; y += sy; }
    }
}
```

调用点:在 `render_lighting_frame` shading 完成后,`for sphere in spheres.iter() { draw_ray_line(buffer, w, h, lamp_pos, (sphere.cx, sphere.cy), scale, LAMP_COLOR, 0.4); }`。**scale 必须 = framebuffer_w / LIGHTING_WIDTH**,考虑 `LIGHTING_RENDER_SCALES` ladder(scale=1 时 320x240,scale=4 时 1280x960)。

### WebGL/GLSL `distance_to_segment` blend (Lighting + Raytrace 用)

```glsl
float distance_to_segment(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a;
    vec2 ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

// In main() — after sphere shading:
// lamp pos + sphere centers hardcoded as vec3 constants (Lighting)
// OR passed as uniform vec4[N] (Raytrace, sun + 3 object centers)
for (int i = 0; i < NUM_RAYS; i++) {
    vec3 lamp = u_params[i*2 + 0].xyz;       // ray origin (lamp / sun)
    vec3 target = u_params[i*2 + 1].xyz;     // ray end (sphere center / object center)
    vec2 lamp_2d = lamp.xy;
    vec2 target_2d = target.xy;
    vec2 logical_px = gl_FragCoord.xy * scene_scale + vec2(scene_offset);
    float dist = distance_to_segment(logical_px, lamp_2d, target_2d);
    if (dist < 1.5) {
        color = mix(color, vec3(ray_color), 0.4);
    }
}
```

GPU uniform buffer 扩展:`RAYTRACE_GPU_UNIFORM_VEC4_COUNT` 从 8 增到 12,容纳
sun + 3 objects 的 (ndc_x, ndc_y, depth, _) 各一个 vec4。

### SsaaCanvas display overlay (Raytrace Canvas 2D 用)

在 `start_raytrace_loop` 的每帧 closure 内,`present_raytrace_framebuffer` 之后:

```rust
// 复用已经 acquire 的 display canvas,不要重新 build SsaaCanvas
if let Some((display_canvas, _ssaa)) = cache.as_ref() {
    let ctx: CanvasRenderingContext2d = display_canvas
        .get_context(RAYTRACE_CONTEXT_TYPE)
        .unwrap()
        .unwrap()
        .unchecked_into();
    let css_w = display_canvas.client_width() as f64;
    let css_h = display_canvas.client_height() as f64;
    let (eye, forward, right, up_true, aspect, focal) = ...; // 复用已算好的 camera basis
    for (sun_pos, target_pos) in [(sun_world, mirror_center), (sun_world, emissive_center), (sun_world, ground_center)] {
        let sun_ndc = project_world_to_ndc(sun_pos, eye, forward, right, up_true, aspect, focal);
        let tgt_ndc = project_world_to_ndc(target_pos, eye, forward, right, up_true, aspect, focal);
        let sun_x = (sun_ndc.0 + 1.0) * 0.5 * css_w;
        let sun_y = (1.0 - sun_ndc.1) * 0.5 * css_h;
        let tgt_x = (tgt_ndc.0 + 1.0) * 0.5 * css_w;
        let tgt_y = (1.0 - tgt_ndc.1) * 0.5 * css_h;
        ctx.begin_path();
        ctx.move_to(sun_x, sun_y);
        ctx.line_to(tgt_x, tgt_y);
        ctx.set_stroke_style(&JsValue::from_str("rgba(255, 235, 200, 0.6)"));
        ctx.set_line_width(1.5);
        ctx.stroke();
    }
}
```

### WebGPU 验证不可达

headless Chrome 跑 WebGPU 需要 `--enable-unsafe-webgpu --enable-features=Vulkan` flags
而且不稳。WebGPU tab 的 WGSL 改动只能通过 build success 间接验证。**CI build 绿就
当 OK**,runtime 行为看 WebGL tab 类推。

## 标题同步的小细节

用户原话:"Ray Trace 页面标题改成 Ray Trace 和 tab 单词一样"。

**期望**:nav sidebar 的标签 = page header = per-tab card title,三处字面一致。

**实际**:三个地方不一致:
- `example/src/component/nav/view/const.rs:34` → `"RayTrace"` (no space, PascalCase)
- `example/src/page/raytrace/view/fn.rs:38` → `"Ray Tracing"` (with space)
- `example/src/page/raytrace/view/fn.rs:42-46` → `"RayTrace Demo (2D/GL/GPU)"` (mixed)

**两种 fix 路径**(选一):
1. **改 nav → "Ray Trace"** (with space),让 page header 和 card 跟着对齐 — 这次 PR 选的路径,euv fmt 自动同步三处
2. **改 page header → "RayTrace"** (PascalCase),让 card title 已经对,只动 header

**euv fmt 会做什么**:跑 `euv fmt` 时,它会把 `title: "Ray Trace"` 这种字面量 normalize 成项目偏好的风格(实测偏好 "Ray Trace" with space),三处自动统一。**先跑 euv fmt 看它怎么处理,再决定要不要手动改**。

## commit 前验证清单(合并坑 13 + 21 + 本 PR 教训)

```bash
# 1. 格式化(euv fmt 抓 snapshot pattern, cargo fmt 抓 column budget)
euv fmt
cargo fmt --all
cargo fmt --all -- --check   # **必须 0 输出**
euv fmt
cargo fmt --all -- --check

# 2. build + clippy + tests
cargo build
cargo clippy --all-targets -- -D warnings
cargo test

# 3. wasm-pack build(verify 编译所有 WGSL/GLSL)
wasm-pack build example --release --target web --out-dir www/pkg

# 4. headless 验证
cd www && python3 -m http.server 8765 &
~/LTPP-MINIMAX/chrome-linux/chrome --headless=new --no-sandbox --disable-gpu \
  --window-size=1280,1100 --hide-scrollbars \
  --virtual-time-budget=30000 \
  --screenshot=/tmp/lighting.png \
  "http://localhost:8765/index.html#/lighting"
# 同上截图 /raytrace + 各 tab 切换

# 5. version bump (euv: 只改根 Cargo.toml 一行)
sed -i '0,/^version = /s//version = "X.Y.Z+1"/' Cargo.toml
euv fmt && cargo fmt --all -- --check   # 再 fmt 一次
git add Cargo.toml
git commit -m "fix(example): <summary>

<3-5 行描述,英文>"

# 6. push (admin 直接推 master)
git push euv-dev master
# 或走 PR:fork → branch → gh pr create → wait CI → merge --squash
```

## 本 PR 实战验证时间线

```
08:35  收到 user 报告 3 个 bug
08:35  delegate 子 agent 诊断 → 拿到精确 root cause + 文件:行号 (3.5 分钟)
08:48  delegate 另一个子 agent 改 + build + headless 验证 (40 分钟)
       - subagent 跑了 euv fmt + cargo fmt,但漏 cargo fmt -- --check
       - 第一次 push → CI Format check failed (格式 drift)
       - subagent 报告 "全部完成,推到 euv-dev/master"
09:11  我 fetch + 看到 CI failure → gh run view --log-failed 拿到 diff
09:12  cargo fmt --all + euv fmt + 显式 check → 干净
09:25  commit ed93660 + 推送 → rebase (remote ahead) → push success
09:34  CI 全绿 (setup / sync_workspace_version / build / clippy / **check** / tests)
09:45  Deploy Pages workflow success
09:50  chromium 直拍 ltpp.vip 实拍 → 三个 bug 全部 visible 修复
       - Lighting: lamp 可见,5 条蓝色光线到 5 个 sphere,no loading
       - Raytrace: 标题 "Ray Trace", sun disk + 3 条白色光线可见, no loading
```

**总耗时 ≈ 75 分钟**,其中 15 分钟花在补救 cargo fmt drift。

**关键 takeaway**:
- delegate subagent 成功率高,但**它不会主动跑 `cargo fmt -- --check`** — 必须显式写在 prompt 里
- chromium 直拍是最稳的验证手段,**browser-use daemon 不可靠**(120s timeout 卡死)
- euv fmt 是 reactive-pattern 的隐形守护,**commit 前必跑**
