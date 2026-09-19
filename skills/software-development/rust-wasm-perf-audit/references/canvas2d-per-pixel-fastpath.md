# Canvas2D 逐像素渲染快路径 + 光追热路径（euv example raytrace/lighting 诊断 @0.18.64）

> 来源：2026-09-06 /lighting + /raytrace 三后端性能重构会话。诊断已核实（源码 file:line），修复手法为图形学标准做法。

## 诊断（已核实）

**euv example `/raytrace`**（`example/src/page/raytrace/hook/raytrace_fn.rs`）：

- 320×240 backing buffer，每像素 2×2 SSAA = 307,200 次 `trace_default`/帧。
- `write_pixel`（L165-179）：每像素 `format!("rgb({},{},{})")` 分配 JS 字符串 → `Reflect::set(ctx, "fillStyle", style)` → `ctx.fill_rect(x, y, 1.0, 1.0)`。**每帧 76,800 次 JS 字符串分配 + 76,800 次 Canvas 调用**。页面 header 自报 "~15 FPS"。
- RAF 循环结构本身没问题（`start_raytrace_loop` L305）；瓶颈 100% 在 presentation + CPU trace。

**euv example `/lighting`**（`example/src/page/lighting/hook/lighting_fn.rs`）：

- `apply_pixel_style`（L184-197）同形态逐像素 fillStyle；5 球 Phong 每球 bounding box 内 4 个子采样。

**euv-engine `raytracing`**（`engine/src/raytracing/fn.rs`）：

- `trace`（L22-51）每次命中调 `collect_occluder_points(occluders)`（L194-208）**新建 Vec** —— 每像素每 bounce 一次堆分配。
- `closest_hit`（L79-136）每个 occluder 测试 `occ.get_material().clone()`；`trace` 命中再 `hit.get_material().clone()`。
- 递归反弹（`trace` → `reflect_ray` → `trace`），depth 字段递增。

## 修法方向（标准做法）

1. **Canvas2D 呈现批量化**：Rust 侧 `Vec<u8>` RGBA8 帧缓冲（帧间复用）→ `Uint8ClampedArray::view` → 每帧单次 `ImageData` + `put_image_data`。JS 边界穿越从 O(像素) → O(1)。SSAA 保留在 Rust 累加缓冲。
2. **engine 光追零热路径分配**：Scene 结构一次性预计算 shadow occluder points，`trace` 改迭代式反弹（能量按 specular 连乘），hit 存索引/借用 Material。公开 API（`trace`/`trace_default`/`closest_hit`/`reflect_ray`）保持向后兼容。
3. **自适应内部分辨率**：EMA 帧时间超预算降 render scale 档（1.0→0.75→0.5），有富余回升，CSS upscale 交给浏览器。
4. **GPU 后端**：同场景移植 WebGL GLSL fragment shader / WebGPU WGSL 全屏三角形 pass，uniform 传相机基向量 + 光照；shader 内做 AA。GPU 路径是「跑满客户端帧率」的终解。
5. **perf PR 先测基线**：headless Chromium 实测优化前 FPS（页面 FPS counter + RAF 注入计数双通道），PR body 报 before/after。
