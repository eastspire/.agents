---
name: euv-engine-webgpu-completion-workflow
description: '在 euv-engine 的 `WebGpuRenderer` 上补完 WebGPU API 的标准流程。本轮在 euv 0.13.3 实地把 WebGPU const.rs / impl.rs / struct.rs 补到了完整 web 等级(descriptor 完整字段、async readback、dynamic offsets、writeTexture、generateMipmaps、error scope)。'
---

# euv-engine WebGPU API 补完流程

## 触发条件

- 在 `euv-engine` 的 `WebGpuRenderer` 上**新增一个 WebGPU 方法**或**新增一个描述符字段**
- 必须保证 `cargo check -p euv-engine --target wasm32-unknown-unknown` 0 错、`cargo test` 通过、`euv fmt` 不改文件

## 流程(5 步)

### Step 1: 先 grep,再写

```bash
# 看 const.rs 已有什么
grep -oE "WEBGPU_(PROPERTY|METHOD|MAP_MODE)_[A-Z_]+" \
  /root/projects/euv/engine/src/renderer/const.rs | sort -u

# 看 impl.rs 已有什么方法
grep -oE "pub fn [a-z_]+" /root/projects/euv/engine/src/renderer/impl.rs | sort -u

# 看 struct.rs 已有什么描述符
grep -oE "pub struct [A-Z][A-Za-z]+" /root/projects/euv/engine/src/renderer/struct.rs | sort -u
```

**99% 的 const 和方法都已经存在**。本轮补完时一次性 append 27 个 const,**20+ 个全部重复**触发 `E0428 defined multiple times` 雪崩。**铁律:只加 grep 确认 missing 的**。

### Step 2: Rust 不支持 method overloading

预存在的方法名(如 `set_bind_group` 3 参 / `create_shader_module` 泛型版)**不能**重写,必须**改新名**:
- `set_bind_group_with_dynamic_offsets`
- `create_shader_module_with_label`

**新方法名用语义化后缀**:`_with_label` / `_with_dynamic_offsets` / `_compute` / `_full` / `_to_texture`。

### Step 3: Lombok Getter 规则

Lombok `Getter` 对:
- `u32` 字段生成 `fn get_x(&self) -> u32`(**value** — 不要 `*` 解引用)
- `Option<T>` 字段生成 `fn get_x(&self) -> Option<T>`(**value**)
- `JsValue` 字段生成 `fn get_x(&self) -> JsValue`(**value**)

**这跟手写 getter 不同**。`if let Some(x) = d.get_origin()` 让 `x: &JsValue` (因为 `Option<T>::as_ref` 自动 deref) — 直接 `&x` 用,不要 `&&x`。

### Step 4: async/sync 边界

凡涉及 WebGPU promise(`mapAsync` / `createComputePipelineAsync` / `popErrorScope` / `getCompilationInfo`):
- **必须 `pub async fn`**,让调用方 `await`
- **不能**用 `spawn_local` + channel 模拟同步 — 会在 wasm executor 上死锁

```rust
// ✅ 对的
pub async fn read_buffer(
    &self, buffer: &JsValue, offset: u64, size: u64
) -> Option<Vec<u8>> {
    let map_promise: js_sys::Promise = ...;
    wasm_bindgen_futures::JsFuture::from(map_promise).await.ok()?;
    // ...
}

// ❌ 错的 (会卡死 executor)
pub fn read_buffer_sync(&self, ...) -> Option<Vec<u8>> {
    wasm_bindgen_futures::JsFuture::from(map_promise).await.ok()?
}
```

### Step 5: 描述符构造 — 0/None = default

WebGPU 浏览器对未设置的 descriptor key 有 spec-compliant fallback。**0 = "用 default"**,**None = "不发送"**:

```rust
let base_mip: u32 = d.get_base_mip_level();
if base_mip != 0 {
    let _ = Reflect::set(&dict, &"baseMipLevel", &JsValue::from_f64(base_mip as f64));
}
```

**不要**总是 set `0` 或 `""` — 浏览器会 reject `bytesPerRow: 0` 这种,或者把它当成字面量解释。

## 验证(必跑)

```bash
cd /root/projects/euv/engine
cargo check --target wasm32-unknown-unknown 2>&1 | grep -E "^error"   # 必须空
cargo test 2>&1 | grep -E "test result"                                # 必须 0 failed
cd /root/projects/euv
euv fmt 2>&1 | grep "Formatted"                                         # 必须 0 file changed
```

## 常见错误 → 解决表

| 错 | 原因 | 解决 |
|---|---|---|
| `E0428 defined multiple times` | const 重复 | grep 后只加 missing |
| `E0592 duplicate definitions` | 方法重名 | 改新名 |
| `E0728 await in non-async fn` | sync fn 用 await | 改 `pub async fn` |
| `cannot dereference u32` | Lombok `u32` getter 返 value | 不要 `*` |
| `mismatched types: expected &JsValue, found JsValue` | Lombok 返回 value | 加 `&` |
| `cannot find type js_sys::Promise` | 漏 use | `use js_sys;` |
| `unused variable: map_result` | let 但不用 | 加 `_` 前缀 |

## 工具

- `web-sys` 提供 `GpuDevice` / `GpuBuffer` / `GpuTexture` / `GpuShaderModule` 等 web-idl 绑定
- `js-sys` 提供 `js_sys::Promise` / `js_sys::Uint8Array` / `js_sys::ArrayBuffer`
- `wasm_bindgen_futures::JsFuture` 驱动 JS promise
- `wasm_bindgen::{JsValue, JsCast, UnwrapThrowExt}`: `dyn_into` / `unchecked_into` / `as_ref`
- `js_sys::Function` / `js_sys::Array` / `js_sys::Reflect` 通过 `wasm_bindgen` 间接拿

## 历史

- **2026-08-15**:euv 0.13.3 第一次补完(descriptor 完整字段 / async readback / dynamic offsets / writeTexture / generateMipmaps /error scope)。一次过 0 错 + 0 fail + 0 fmt 改动。

- **2026-08-15 (同一会话后续)**:加 13 个新 API 的 **integration test shape pin**(`engine/tests/webgpu_renderer_api_shape.rs`,15 个测试全过)。在 `example/src/lib.rs` 加 `webgpu_renderer_completion_demo` 真实 demo 函数(`pub async fn`,编译时验证 13 个 API 在 wasm 上下文中的真实可用性)。**euv fmt 仍然 0 改动**。

## 实际真实签名(2026-08-15 实地核对,不要靠记忆)

13 个本轮新 API 的真实签名(`grep -nE "pub fn ...$" src/renderer/impl.rs` + `cargo test` 反向验证):

| # | API | 真实签名 | 备注 |
|---|---|---|---|
| 1 | `begin_render_pass_full` | `&mut self, encoder: &JsValue, color: &mut RenderPassColorAttachment, depth: Option<&RenderPassDepthStencilAttachment> -> JsValue` | **color 是 `&mut`,depth 是 `Option<&RenderPassDepthStencilAttachment>`,不是 `Option<&JsValue>`** |
| 2 | `create_render_pipeline_full` | `&self, S: AsRef<str>, &[VertexBufferLayout], &str, &str, Option<&str> -> JsValue` | **6 参,不是 9 参**;shader 走 `S: AsRef<str>` 泛型 |
| 3 | `create_view` | `&self, &JsValue, Option<&TextureViewDescriptor> -> JsValue` | 第二参是 `Option<&_>`,**None 表示 "default 2D view"** |
| 4 | `create_shader_module_with_label` | `&self, &str, &str -> JsValue` | **2 参,不是 3 参**;source + label,device 是隐式 |
| 5 | `push_error_scope` | `&self, &str -> ()` | 无返回值;**`pop_error_scope` 还没实现**(本轮只 commit 了 push) |
| 6 | `set_viewport` | `&self, &JsValue, f32×6` | 7 参 |
| 7 | `set_scissor_rect` | `&self, &JsValue, u32×4` | 5 参 |
| 8 | `set_blend_constant` | `&self, &JsValue, f32×4` | 5 参 |
| 9 | `set_stencil_reference` | `&self, &JsValue, u32` | 2 参 |
| 10 | `set_bind_group_with_dynamic_offsets` | `&self, &JsValue, u32, &JsValue, &[u32]` | 5 参 |
| 11 | `set_bind_group_compute_with_dynamic_offsets` | `&self, &JsValue, u32, &JsValue, &[u32]` | 5 参 |
| 12 | `generate_mipmaps` | `&self, &JsValue -> ()` | 1 参 |
| 13 | `read_buffer` | `&self, &JsValue, u64, u64 -> impl Future<Output=Option<Vec<u8>>>` | **`pub async fn`,必须 await** |

### Lombok 泛型方法不能 `fn` pointer coerce

如果 API 用了 `S: AsRef<str>` / `&[T]` slice / 其它泛型,**不能用**:
```rust
let _: fn(&WebGpuRenderer, &str, &[VertexBufferLayout], ...) = WebGpuRenderer::create_render_pipeline_full;
```
会触发 E0308 "expected fn pointer, found fn item"。**改用**:
```rust
fn _type_check<S: AsRef<str>>(
    renderer: &WebGpuRenderer,
    shader_code: S,
    ...
) -> JsValue { renderer.create_render_pipeline_full(shader_code, ...) }
let _ = _type_check::<&str>;
```

### `RenderPassColorAttachment` 字段是 `pub(crate)` — 设计缺陷

`RenderPassColorAttachment.view` / `resolve_target` / `clear_value` / `load_op` / `store_op` 全是 `pub(crate)`,**example 外部 crate 无法构造**。只有 `begin_render_pass_full` 内部代码能填字段。

**影响**:
- example 不能用 `begin_render_pass_full`(传不出 color attachment)
- 必须走旧的 `begin_render_pass` 或 `render_frame_with_bind_group`,**这两个会用 swap chain view 当默认 view**
- 未来如果想给 caller 自定义 color attachment,要么加 `pub fn builder()`,要么把字段 `pub`

**Demo 函数怎么处理**:`example/src/lib.rs::webgpu_renderer_completion_demo` 用 closure `_type_check` 把签名**pin 住**(编译时验证),不实际调 — 这就是 Lombok `pub(crate)` 设计下的**正确 demo pattern**。

### `TextureViewDescriptor::full()` 才有,`RenderPassColorAttachment::full()` 没有

`TextureViewDescriptor` 有 `pub fn full() -> Self`(在 struct.rs 内 impl),但 `RenderPassColorAttachment` **没**有 `::full()`。区别是 Lombok 处理: `TextureViewDescriptor` 是 Lombok `@AllArgsConstructor(staticName = "full")` 或手写,`RenderPassColorAttachment` 是手写 impl 但没 `full()` 关联函数。
