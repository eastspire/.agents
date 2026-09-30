---
name: euv-engine-renderer-api
description: 'Use when editing euv-engine renderer or WebGL/WebGPU APIs.'
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags:
      - euv
      - euv-engine
      - renderer
      - webgl
      - webgpu
    related_skills:
      - euv
      - euv-standards
      - euv-engine-webgpu-completion-workflow
      - rust-standards
---

# euv-engine 渲染后端:API 表面与 WebGL/WebGPU 能力边界

## When to Use

- 改 `engine/src/renderer/` 的公开 API(加方法 / 改描述符 / 迁签名)。
- 评估或补完 WebGL / WebGPU 后端能力。
- 清理 `engine/src/` 里泄漏给外部的自由函数。

数字与签名以实地 grep 为准,本 skill 只记结构与判定方法。

## 1. 公开 API 走结构体/枚举方法,禁止暴露自由函数

`engine/src/lib.rs` 把每个模块 `pub use ...::*` 摊平成 crate 根命名空间 —— 任何 `mod.rs`
里 `pub use r#fn::*;` 都会把 `fn.rs` 的自由函数整包暴露成外部可调用 API。

**验收单一判据**(一条命令,不依赖读文件):

```bash
grep -rnE '^pub fn |^pub const fn ' engine/src --include='*.rs'   # 必须 0 命中
```

`pub(crate) fn` **不算**暴露 —— 引擎内部 helper(解析 / 编码 / 缓存)留在 `fn.rs` 是对的。
泄漏的判据是 `pub fn` + `pub use` 组合。关掉外泄面就是把 `mod.rs` 的
`pub use {.., r#fn::*, ..}` 改成 `pub(crate) use r#fn::{..}`。

**给自由函数选新家**:优先选真正拥有这份数据的类型,而不是零尺寸命名空间 struct。
`compute_lambert(light: &Light, ..)` → `Light::lambert(&self, ..)`,顺便把 `light: &Light`
参数删掉用 `self`。命名空间 struct(`Engine` / `Input` / `Numeric`)只在真的没有数据主人时用,
是最后手段。

## 2. 重构前先合并重复类型

同名概念的多份定义是重构的隐藏成本。引擎实际有 **3 个 3D 射线类型**:`math::Ray2D`(死)、
`math::Ray3D`(死)、`raytracing::Ray`(活),其中两个方法重名(`Ray3D::point_at` 与 `Ray::at`
完全重复)。

判活方法(先做,再动手):

```bash
for t in Ray2D Ray3D Ray; do echo "$t: $(grep -row "$t" engine example docs --include='*.rs' | wc -l)"; done
```

**引用数 ≈ 自身定义数 = 死代码**。合并方向:保留活的那个 + 把死类型的独有方法移植过去,
重名的丢弃 —— **不要造第二个近义方法**。

## 3. 位置元组换具名 struct

`(Vector3D, f64)` 这种位置元组一旦被 4 个以上签名传递就成了可读性债,且无法加字段。
实例:`occluders: &[(Vector3D, f64)]` 串起 `LightingUniforms::shade` /
`Light::soft_shadow` / `Occluder::occluder_points` / `RayTraceScene::shadow_points`。
改法:引入 `ShadowSphere { center, radius }`,放在**遮挡几何**域(`raytracing/struct.rs`)——
两个模块都因 lib.rs 摊平命名空间而可见。

同类还有渲染调用里 5 个连续位置参数(`index_count/instance_count/first_index/base_vertex/
first_instance`)→ `DrawIndexedArgs`。

## 4. 字符串 / 位掩码 API 必须换枚举

WebGPU 后端当前用 `load_op: Option<&'static str>`(合法值只有 "clear"/"load")、
`create_buffer(size, usage: u32)` 裸位掩码、`push_error_scope(filter: &str)` 裸字符串、
sampler 的 6 个 `&'static str` + 一个 `compare: bool`。**拼错是运行时静默失败,不是编译错误。**

替换为枚举(`LoadOp` / `StoreOp` / `BufferUsage` / `TextureUsage` / `FilterMode` /
`MipmapFilter` / `AddressMode` / `CompareFunction` / `BlendFactor` / `BlendOperation` /
`PrimitiveTopology` / `IndexFormat` / `ShaderStage` / `FrontFace` / `CullMode`)+
描述符 struct(`ColorAttachment` / `DepthStencilAttachment` / `SamplerDescriptor` /
`RenderPipelineDescriptor` / `TextureDescriptor` / `BufferDescriptor` / `UniformSlice`)。

细节:
- 复用引擎已有的 `Color`(在 `math/struct.rs`),**不要**再造颜色类型,也不要留裸 4 元组。
- `Option<CompareFunction>` 比 `compare: bool` 表达力强得多(前者能表达 less / greater)。
- 位掩码型枚举(`BufferUsage` / `TextureUsage`)在 doc 里写明「调用点按位或」,位值另放 `const`。

## 5. web-sys feature 门:哪些句柄有强类型绑定

web-sys 的 WebGL2 **方法**在 `WebGl2RenderingContext` feature 打开后全部可用(604 个),
但**资源句柄**各自需要独立 feature。根 `Cargo.toml` 已开:`WebGl2RenderingContext` /
`WebGlBuffer` / `WebGlProgram` / `WebGlShader` / `WebGlUniformLocation`。

**未开**(要写 VAO / 纹理 / FBO 必须先加到根 `Cargo.toml`):
`WebGlVertexArrayObject` / `WebGlTexture` / `WebGlFramebuffer` / `WebGlRenderbuffer`

缺 feature 时句柄是 `JsValue`,只能 `Reflect::set` 走反射 —— 能跑但丢掉全部类型检查,正是
§4 要消灭的东西。加 feature 前先确认根 `Cargo.toml` 是唯一 feature 入口(engine/ 与 core/
都写 `web-sys = { workspace = true }`)。

## 6. WebGL 后端当前缺口(相对 WebGPU)

`WebGlRenderer` 只有 **9 个方法**(`is_available` / `init` / `create_program` /
`get_uniform_location` / `set_uniform_2f` / `set_uniform_4fv` / `render_frame` / `resize`
+ 私有 `compile_shader`),对照 WebGPU 的 62 个 public 方法。缺:VAO、buffer 上传与子区间更新、
纹理创建/上传/参数/mipmap、depth renderbuffer、framebuffer 离屏目标、indexed draw、顶点属性
指针与 divisor、blend / cull / depth / scissor / color-mask 状态、4x4 矩阵 uniform、sampler
对象。补完时按 §5 先开 4 个 feature。

## 7. 改名时连带修文档引用

迁函数名时,doc 注释里以反引号提到的旧名字(`Mirrors engine \`ray_sphere_intersect\``、
`` `apply_falloff(view_dist, falloff)` ``)和 intra-doc 链接(`` [`soft_shadow_factor`] ``)
会一起变悬空。**悬空 intra-doc 链接是 build warning**,而这些注释是使用者看到的第一手文档。
改名后全仓 grep 旧名字一次,含 `example/` 的注释与手写 CPU fallback 副本。

## 8. 大规模重构的并行拆分

重构这类「改签名 + 加类型」的工作天然想拆成两个 agent(一个迁调用点、一个声明新类型),
**但这样不安全**:声明方 agent 工作期间,迁方改到一半的 impl.rs 必须仍然能编译。
按**不相交文件集合**拆才安全(`enum.rs`/`struct.rs`/`const.rs` 归一个,`impl.rs`/`fn.rs`
归另一个),详见 `delegate-task-contract-pitfalls` §2。

## 验证

```bash
cd <repo>
cargo check -p euv-engine --target wasm32-unknown-unknown
cargo check -p euv-example --target wasm32-unknown-unknown
cargo clippy -p euv-engine --all-targets --target wasm32-unknown-unknown   # 0 warning
~/.cargo/bin/crate fmt --check                                              # exit 0
grep -rnE '^pub fn |^pub const fn ' engine/src --include='*.rs'             # 0 命中
```
