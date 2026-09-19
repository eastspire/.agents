# WebGPU descriptor 缓存 → resolveTarget 过期 →「GPU 活跃但画面全黑」(2026-09-11, euv PR #184)

> 来源:用户报「webgpu 没有展示画面,gpu 状态是活跃状态」,定位到 euv master `d46d26b`
> (PR #184 `perf(engine): Function-level cache + descriptor caching for WebGPU`)。
> 本文件是完整诊断链;SKILL.md 正文只保留两条泛化规则。

## 症状

- WebGPU demo(example game_3d WebGPU tab)**画面全黑**,从第 2 帧起什么都不画
- init 完全正常:adapter/device 拿到、pipeline 创建成功、demo 把 `active` signal 置 true
  → 页面显示「GPU 状态:活跃」
- **零 JS 异常**,FPS 计数照跑,rAF 循环存活
- console 里只有异步 GPU validation warning(不抛异常,不中断执行)

## 根因链(5 环)

1. PR #184 给 `begin_render_pass_full` 加了 `RenderPassDescriptorCache`
   (`engine/src/renderer/struct.rs` + `impl.rs`):跨帧复用同一个
   `GpuRenderPassDescriptor` Object,失效条件**只有** load_op / store_op /
   depth-stencil 形态变化。
2. 热路径每帧只重写 `attachment.view` 和 `clearValue.r/g/b/a`;
   **`attachment.resolveTarget` 只在 build 时写一次,之后永不刷新**。
3. 引擎默认 `CONFIG_DEFAULT_ANTIALIAS = true`(`engine/src/config/const.rs:14`)
   → MSAA 路径下 `attachment.view` = 多重采样纹理 view(分配一次,终身稳定),
   而 **`resolveTarget` = 每帧 `context.getCurrentTexture()` 返回的新 view**
   (`begin_render_pass_full` 里 `Some(view) => (view, Some(swap_chain_view.clone()))`)。
4. WebGPU 规范:`getCurrentTexture()` 的纹理在当帧 present 后**自动失效**。
   缓存把第 1 帧的 swap-chain view 永久留在 resolveTarget → 第 2 帧起
   `beginRenderPass` 每次 validation error → pass/command buffer 无效 →
   `submit` 空转 → swap chain 呈现未被绘制的纹理 = 黑。
5. 所有 Rust 侧调用都是 `.unwrap_or(JsValue::UNDEFINED)` 吞错,GPU validation
   又是异步 console 消息 → 无任何异常冒出,init 路径完全不受影响。

## 调用链(定位路径)

```
example/src/page/game_3d/hook/fn.rs
  start_game_3d_webgpu_loop            # rAF 循环;init 成功后 active.set(true)
    └─ renderer.render_frame_with_bind_group(pipeline, bind_group, clear, n)
       (engine/src/renderer/impl.rs:4486)
       └─ begin_render_pass → begin_render_pass_full   # ← 缓存在这里
```

验证思路:`git log --oneline` 找到 perf batch(#182-#193)→ 唯一直接触
WebGPU 渲染路径的是 #184 → 读 diff 发现 resolveTarget 只在 build 路径 →
对照 MSAA 默认开 + swap-chain 纹理每帧失效,闭环。

## 修复

热路径把 `resolveTarget` 和 `view` 一起每帧重写,并把 resolve 形态纳入失效条件:

```rust
// begin_render_pass_full 热路径,紧跟现有 view 更新之后:
if let Some(target) = resolve_view.as_ref() {
    let _: Result<bool, JsValue> = Reflect::set(
        &cache.attachment,
        &cached_method_name(WEBGPU_PROPERTY_RESOLVE_TARGET),
        target,
    );
}
// RenderPassDescriptorCache 加 last_has_resolve: bool,
// Some/None 切换时重建(防 MSAA↔非 MSAA 切换残留 stale resolveTarget)。
```

快速反证:`git revert d46d26b` 后 `wasm-pack build example`,WebGPU tab 恢复画面。

## 次要地雷(同 PR,`cached_method`)

缓存 key = `(obj as *const JsValue as usize, method_name)` —— 取的是
**wasm 线性内存里 `JsValue` handle 的地址**,不是 JS 对象身份。栈上的临时
`JsValue`(texture/encoder/pass)地址会被无关调用复用;而 `"end"` /
`"setPipeline"` / `"setBindGroup"` 是 `GPURenderPassEncoder` 和
`GPUComputePassEncoder` **共名**方法 —— 撞地址即拿到错误类的 Function,
调用抛 TypeError,再被 `unwrap_or(UNDEFINED)` 吞掉 → 同款静默不渲染。
**Function 缓存只对 renderer 持有的稳定 JsValue(device/queue/context)安全;
临时对象应回退 `Reflect::get`。**

## 泛化规则(给后续 perf PR)

1. **跨帧缓存任何 WebGPU descriptor 前,逐字段标注「帧内稳定」还是「每帧新对象」**。
   `getCurrentTexture()` 的一切产物(view、resolveTarget)永远属于后者。
2. **「init 活跃 + 无异常 + 无画面」= 异步 GPU validation 被吞**。排查第一步:
   看 console 的 WebGPU validation warning,或临时 `push_error_scope` /
   `pop_error_scope` 把错捞出来;不要信「没抛异常 = 没破」。
3. perf PR 的验收清单里,`cargo check` + `cargo test` 之外**必须有浏览器视觉
   验证**(canvas 实际像素),字节指纹对 DOM 有效,对 GPU 帧缓冲无效 ——
   #184 过了全部编译/测试/DOM 指纹,画面照样全黑。
