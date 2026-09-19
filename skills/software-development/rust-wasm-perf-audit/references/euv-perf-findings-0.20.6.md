# euv 性能审计发现清单 (v0.20.6)

> 实测自 `~/github/euv-dev/euv` @ commit `83c4d39`（v0.20.6, 2026-09-10），对照基线 v0.18.58 (`1f09cd5`)。
> 行号随版本漂移，重查时按函数名 grep。按 频率×单次成本 排序。
> 状态已同步至 2026-09-10 upstream/master (5918d90，含 PR #178/#179)；PR #180 OPEN。
> 方法：4 个并行 worker 分区审计（A=core renderer+noderef / B=reactive+vdom+app / C=macros+ui / D=engine），汇总者对全部一档结论与关键回归做了独立复核（逐处 sed 读码 + cargo check 复现）。
> 成本模型不变：**主要成本单位 = JS 边界穿越 + 堆分配**。

## ⚠️ 已知错误论据（必须在审计中否定）

1. **`dyn_ref::<HtmlInputElement>()` 不是 JS 边界穿越**。wasm-bindgen 在 WASM 端的纯 Rust trait downcast（vtable + type tag 比对），0 次 FFI，单次 ~1-3ns。任何基于"消除 N 次 dyn_ref = 消除 N 次 JS 桥接"的收益估算都是错的。
2. **短字符串字面量 match 重排优化真实收益 < 5%**。LLVM -O3 下编成 jump table / immediate match。`set_attribute_or_property` 的 6 次字符串比较消除属于此类——本轮复核后**建议关闭该项**（见二档末）。
3. **[新增] `event.composed_path()` 不是事件委托的解**。`js_sys::Array` 的 `.get(i)` 每个元素仍是一次 JS 穿越，总穿越数与逐层 `get_attribute` 相当。真正的修法是把祖先链 walk 挪进 JS 端 glue，完成后带 euv_id 回调 WASM（每事件 1-2 次穿越）。
4. **[新增] "DocumentFragment 批量 append 总是更快"是错的**。对 **detached**（尚未入文档）的子树，append 不触发任何 layout，fragment 化反而把 N 次 append_child 变成 N+2 次 JS 穿越（create_fragment + N×append + graft）还多付 1 个 `Vec<Node>`。批量收益只存在于 connected 父节点（见回归 R3）。

## 0.18.58 → 0.20.6 已闭环

### 本轮新落地的优化（v0.18.58..HEAD 共 56 commits，perf 相关 4 个）

1. **OPT-10 零分配静态 style**（a90db6c / PR #144 / 随 v0.18.59）：`AttributeValue::StaticText(&'static str)` 新增（vdom/attribute/enum.rs:18），macros 全字面量 style emit StaticText（macros/src/html/impl.rs:698-700），renderer patch/mount 两臂接线（render/impl.rs:311-313 / 755-757）。**带两个回归尾巴，见 R1/R2。**
2. **OPT-11 零拷贝静态 class**（a90db6c / PR #144）：`AttributeValue::CssRef(&'static Css)`（enum.rs:37）+ `class!` 全静态类生成 `OnceLock<Css>` + `fn() -> &'static Css`（macros/src/class/fn.rs:1146-1155），`From<&'static Css>` 深 clone 消除（reactive/cast/impl.rs:150-165）。fc89f7a 顺手补了 merge_class 的 CssRef 匹配臂（attribute/impl.rs:119-122/:143-146，否则多 class 合并时 CssRef 被 `_ => None` 吞掉）。**引出回归 R1。**
3. **OPT-13 DocumentFragment 批量 append**（fc89f7a / PR #146 / 随 v0.18.60）：新增 `append_nodes`（render/fn.rs:58-91），≥2 子节点时 funnel 进 fragment，父节点只见 1 次 append_child。覆盖三条路径：元素 mount 子节点（render/impl.rs:739-746）、portal 目标（:717-725）、positional patch 尾部新增（:602-607）。**不覆盖**：patch 属性写、删除路径、keyed move。误覆盖 detached mount 见回归 R3。（注：fc89f7a 的 commit message 误贴了 PR #144 的 OPT-10/11 文案，message 与 diff 不符，读历史时注意。）
4. **engine raytracing scene-based 重构**（8c72cc9 / PR #159）：新增 `RayTraceScene`（raytracing/struct.rs:64）构建时一次性预计算 `shadow_points`；`trace_bounces`（raytracing/fn.rs:158）改迭代式 + specular throughput，只在 winning hit 上取 `&Material`（借用不 clone）；消除 d06e376 初版的每 bounce `collect_occluder_points` Vec 分配 + 递归 + per-candidate Material clone。官方实测 /raytrace Canvas2D ~0.33→39.6 FPS（主要来自 example 侧 put_image_data 改造）。
5. **engine 新增 WebGL2 backend**（8c72cc9 / PR #159）：`WebGlRenderer` 全程 web_sys typed 绑定（0 处 Reflect），`get_uniform_location`（renderer/impl.rs:5768）显式缓存——**这正是 WebGPU 侧该做而没做的模式**，可直接对照抄。
6. **physics 3D torque 积分修复**（d06e376 / PR #150）：`apply_torque` 累积的 torque 真正积分进 angular velocity（physics/impl.rs:726-728），新增 `update_inertia`（:576）+ 回归测试；correctness 修复，附带静态体 inverse_inertia=0 不再空转积分。

### 复核确认仍有效（0.18.58 前落地，0.20.6 未回退，非新发现）

- 0.18.36 #1 `unwrap_component_owned` 零分配预扫描（`subtree_has_component`）完好（render/impl.rs:997-1032）。
- OPT-2 静态 attr key/tag 走 `Cow::Borrowed`（html/impl.rs:1012-1018/:1269-1273，cargo expand 实证）；attr key 单次提取（7e12ef7）。
- 静态 N 子节点已用 `vec![...]` 精确容量（html/fn.rs:1205/:1258、html/impl.rs:781/:900/:908/:1119/:1274）——0.18.58 档一#3 的"无 with_capacity"在**纯静态**路径已闭环；for/inline-if 动态路径仍开放（见三档）。
- OPT-5/6/7/9（eef1b62）本轮复核未回退。
- 高频事件祖先链深度上限 `MAX_ANCESTOR_DEPTH_FOR_HIGH_FREQ=4`（2ea95c8，registry/const.rs:104）在 0.18.58 基线内已在，非本轮闭环。

## 报告发布后已落地（2026-09-10）

报告发布当天 upstream 连续合入两个 perf PR，以下条目已闭环（✅=全部落地，◐=部分落地）：

**PR #178 `perf: fix OPT-10/11 regressions, scheduler current_time, and 6 low-risk wins`（commit 5918d90）**
- ✅ R1 — PartialEq 补 StaticText/CssRef 及 Text/Css 交叉臂（attribute/impl.rs:279-302）
- ✅ R2 — macros 三个包装点改为直接透传 + 新增 macros/tests/html_static_style.rs 编译期回归测试
- ✅ R3 — `append_nodes` 加 `parent.is_connected()` detached gate（render/fn.rs:67）
- ✅ 档一#3 — scheduler `current_time` 改为 Reflect 取 Function 后 `call0(&performance)`（scheduler/impl.rs:51-55）
- ✅ 档一#4 — lighting `lights` getter 去掉 `type(clone)`（lighting/struct.rs:64）
- ✅ 二档#12 — positional 删除循环 `last_child` 复用（render/impl.rs:633）
- ✅ 二档#14 — Event 属性 `Rc::ptr_eq` 比对跳过重复 attach（render/impl.rs:296-315）
- ✅ 二档#18 — 6 处 `join(&CHAR_SPACE.to_string())` 改为 `join(" ")`，CHAR_SPACE 常量随删（后续 PR #180 恢复为 `&str` 常量，OPEN）
- ✅ 二档#32 — `SsaaCanvas::present` 不再每帧 apply_quality（renderer/impl.rs:1270）

**PR #179 `perf: Signal::with, Float32Array view, physics reuse, scene borrow, i18n read borrow`（commit 69ecc2d，随 v0.21.0）**
- ✅ 二档#17（API 半）— 新增 `Signal::with(FnOnce(&T))` 只读 API（signal/impl.rs:99）；`set()` 内 dependents `Vec<usize>` clone 未动
- ◐ 二档#22 — i18n `t`/`locale_count`/`active_message_count` 改用 `with` 借读（i18n/impl.rs:117-141）；消息表移出 Signal 的完整重构仍挂账
- ✅ 二档#31 — `update_uniform_buffer`/`write_buffer` 改 `Float32Array::view`/`Uint8Array::view` 零拷贝（renderer/impl.rs:3126/:3767）
- ✅ 二档#33 — physics 2D/3D pairs 改用 world 持久 `pair_buffer` 复用（physics/impl.rs:402/:773）；3D bboxes 落地为 `Vec::with_capacity` 预分配（持久 bbox_buffer 方案因借用规则放弃）；grid.clear 保 buffer 未做
- ◐ 档一#2 — 新增 thread_local `cached_method_name()` 缓存静态方法名的 `JsValue::from_str`（renderer/impl.rs:13），接线 begin_render_pass_full 9 处 + submit；其余 ~230 处 Reflect 调用点未动，Function 级缓存未做
- ◐ 二档#34 — 托档一#2 部分之福，begin_render_pass_full 的 9 处 from_str 被缓存；descriptor Object/Array 每帧重建仍在
- ✅ 三档#38 — `SceneManager::update` 改借用 current_scene_name + clone SceneRc（scene/impl.rs:110）

**PR #180 `refactor(core): restore CHAR_SPACE as a &str const for join separators`（1042d8b）— OPEN，待 review**
- 二档#18 后续：把 #178 的 `join(" ")` 字面量恢复为命名常量 `join(CHAR_SPACE)`，常量以 `pub(crate) const CHAR_SPACE: &str = " "` 形式加回（const.rs:31，attribute/impl.rs:129/:152/:186/:200/:683/:727），语义不变。

## 本轮新发现的回归（最高优先级——都是 0.18.58 后的优化 PR 引入，先修这些）

### R1. [已落地 PR #178] `AttributeValue::PartialEq` 缺 StaticText/CssRef 分支——OPT-10/11 把 skip_equal 整树跳过全局打废（Worker B/C 独立发现，汇总者已读码确认）

> ✅ 已落地：PR #178 (5918d90)，PartialEq 已补 `(StaticText,StaticText)`、`(CssRef,CssRef)` 及 Text/Css 交叉臂（现 attribute/impl.rs:279-302）。

`core/src/vdom/attribute/impl.rs:276-294`（全仓库唯一 impl）的 eq 只有 Text/Signal/Event/Css/Dynamic 五个 arm，`(StaticText,StaticText)`、`(CssRef,CssRef)`、`(Text,StaticText)` 全落 `_ => false`。

- 后果链：`visual_eq`（render/impl.rs:1110→:1131 `old_attr == new_attr`）对**任何含 class! 类或字面量 style 的 dynamic 子树**恒 false → `setup_dynamic_node` 的 skip_equal 早退（:941-948）被废 → 每次相关 signal set 全子树 patch（每元素 2 个 HashMap 分配 + 属性逐个比）；且 `patch_attributes`（:302-305）的 `!=` 恒 true → 每个 class! 元素每次 patch 白付 1 次 `set_attribute_or_property` JS 桥接（:327-331）。
- 频率：每 dynamic 节点每次重渲染 × 子树内每个 class! 元素（euv 应用几乎全部元素）。
- 量化：0.18.58 前未变子树可整树跳过（0 JS 穿越）；现在 44 元素页面一次 signal 翻转 = 全树 patch walk + 每 class 元素 ≥1 次多余 set_attribute。**OPT-11 省下的深 clone 大概率倒贴**（JS 穿越 ≫ 堆分配）。
- 修法：PartialEq 补 `(StaticText(a),StaticText(b)) => a==b`、`(CssRef(a),CssRef(b)) => a.get_name()==b.get_name()`、`(Text(a),StaticText(b)) => a==b` 交叉臂，各 1 行。注：`class:` 经 merge_class 归并为 Text 的场景不受此洞影响，但 cargo expand 实证 `class: c_demo()` 直挂时走的是 CssRef。

### R2. [已落地 PR #178] 全字面量 `style: { color: "red" }` 编译失败（E0308）——OPT-10 引入，0.18.59 起五个版本没人发现（Worker C 发现，汇总者 cargo check 复现）

> ✅ 已落地：PR #178 (5918d90)，三个包装点改为直接透传，并新增 macros/tests/html_static_style.rs 编译期回归测试。

OPT-10 把 `HtmlAttrValue::Style` 全字面量分支的 emit 从 String 改成 `AttributeValue::StaticText(...)`（macros/src/html/impl.rs:698-700），但**三个包装点仍 emit `AttributeValue::Text(#value)`（需要 String）**：macros/src/html/fn.rs:2063（原生元素主路径）、:1861（merge_style 路径）、:1822（merge_class 路径）；组件 props 路径 fn.rs:2147 的 `(#value).to_string()` 同样炸。

- 汇总者复现：最小用例 `html! { div { style: { color: "red"; } "x" } }` → `error[E0308]: mismatched types, expected String, found AttributeValue`。
- 为何漏了五个版本：全仓库 example//ui/ 0 处使用该语法、`macros/tests/` 无 html! 测试目录。
- 修法：三个包装点对 all-literal 直接透传 `#value`（它已是 AttributeValue）；prop_field_token 对 all-literal 直接 emit 字符串字面量；**并补一个 html! 字面量 style 的宏展开测试**，否则下次还会无声回归。

### R3. [已落地 PR #178] OPT-13 误覆盖 detached mount 路径，纯属加负（Worker A 发现，汇总者已读码确认）

> ✅ 已落地：PR #178 (5918d90)，`append_nodes` 入口加 `parent.is_connected()` gate（render/fn.rs:67），detached 直接循环 append。

render/impl.rs:739-746：`create_dom_with_doc` 里新元素**尚未入文档**，detached 子树的 append 不触发任何 layout；fragment 化把 N 次 append_child 变成 N+2 次 JS 穿越（create_fragment + N×append + graft）还多付 1 个 `Vec<Node>`。

- 频率：每 mount 一个 ≥2 子节点的元素（= 每个元素，初始全树 mount 全走这里）。
- 量化：1000 元素 mount（平均 3 子）≈ +600 次白付的 JS 穿越。OPT-13 的真收益只在 connected 父节点：positional 尾部 append（:602-607）与 portal（:717-725）。
- 修法：`append_nodes` 里 gate `parent.is_connected()`，detached 时直接循环 append（或拆两个入口）。

## 一档：架构级大头

### 1. [仍开放] patch 路径仍无 DomOp 收集 + 批量 commit（0.18.58 档一#1，连续两轮开放）

render/impl.rs:249 `patch_attributes` 每属性立即 `set_attribute_or_property`（:328/:331/:335/:341/:349）/`remove_attribute_or_property`（:270）；keyed diff 每个 move 立即 `insert_before`（:542/:551）/`append_child`；positional 删除立即 `remove_child`（:640）；text patch 立即 `set_text_content`（:162/:599）。OPT-13 只 batch 了 append 一个维度。

- 频率：每次 render 的每个变更属性/子节点。
- 量化：一次 patch 触及 E 个元素、每元素 A 个变更属性 + C 个子节点变更 = E×(A+C) 次独立 JS 穿越，无合并上限。
- 修法：patch 阶段收集 `Vec<DomOp>`（纯 WASM 内存操作，0 桥接），commit 阶段按 element 分组一次性 flush；属性写可合并为 JS 端一次 `for` 循环的 glue 调用。改动量大（新增 commit.rs、patch 函数签名改返回 Vec<DomOp>），需 CDP 指纹回归（templates/cdp-mount-bench.py）。

### 2. [仍开放·PR #179 部分缓解] engine WebGPU 全 API 走 `Reflect::get(obj, &JsValue::from_str(m))`，水位 203 → 245

> ◐ 部分落地：PR #179 (69ecc2d) 新增 thread_local `cached_method_name()` 缓存静态方法名的 `JsValue::from_str`（renderer/impl.rs:13），接线 `begin_render_pass_full` 9 处 + `submit`；其余 ~230 处 Reflect 调用点未动，方法名→`js_sys::Function` 缓存未做（#179 commit message 明确留给后续 PR）。

`engine/src/renderer/impl.rs` Reflect 从 203 涨到 **245**（+42 全部来自 PR #177 新增高级 API；5918d90 复核真实代码行 243：impl.rs 243（含 #179 新增 helper 内部）+ input 4 + scheduler 2，enum/struct/const 的 8 处仅为 doc 注释）。**无 thread_local Function 缓存、无 `#[wasm_bindgen(extern)]` 绑定**（grep 均 0）。热路径（5918d90 行号）：set_pipeline:2909 / draw:2975 / draw_indexed:2997 / end_render_pass:3043 / finish_command_encoder:3059 / set_vertex_buffer:2932 / set_index_buffer:2957 / set_bind_group:4206 / create_command_encoder:2380 / get_current_texture_view:2401 / begin_render_pass_full:2486 / submit:2654 / update_uniform_buffer:3117 / write_buffer:3759 / dispatch:3233。

- 量化：example lighting demo 实际路径（update_uniform_buffer + render_frame_with_bind_group）单 fullscreen triangle ≈ **50 次 JS 穿越/帧**，其中 ~40 次是 Reflect/from_str 纯开销；500 实体 ×（set_pipeline+set_vertex_buffer+set_index_buffer+set_bind_group+draw_indexed）≈ **7500 次穿越/帧**。
- 修法：方法名→`js_sys::Function` 的 thread_local 缓存（Function 不绑 this，`call1(pass,…)` 显式传 this，首次拿到即可缓存）；彻底方案换 web-sys GpuXxx typed 绑定。**同仓库 WebGL2 backend（本轮已闭环#5）就是现成范式。**

### 3. [已落地 PR #178] scheduler `current_time()` 永远返回 0.0——固定步长更新实际死亡

> ✅ 已落地：PR #178 (5918d90)，Reflect 取 `now` Function 后 `call0(&performance)`（scheduler/impl.rs:51-55）。

engine/src/scheduler/impl.rs:41-54：`Reflect::get(performance, "now")` 拿到的是 **Function 对象**，`.as_f64()` 对函数恒为 None → return 0.0——**`now()` 从未被调用**。

- 后果：`tick()`（:67）首帧后 frame_time 恒 0 → `on_update` 只在第 1 帧跑过一次、`on_render` 的 interpolation 恒 0。`Engine::run`/`EngineHandle::start` 的固定步长更新实际死亡（demo 全部自写 RAF 循环所以没暴露）。
- 频率：每帧 2×Reflect::get + 2×from_str，且整个 update 阶段空转。
- 修法：`window().performance().now()`（web-sys Performance feature，typed 绑定），或 Reflect 取 now 后 `call0(&performance)`。一行级修复。

### 4. [已落地 PR #178] `LightingUniforms::shade` 每次调用 clone 整个 lights Vec——CPU raytrace 每像素每 bounce 一次堆分配

> ✅ 已落地：PR #178 (5918d90)，getter 去掉 `type(clone)`（lighting/struct.rs:64），返回 `&Vec<Light>`。

engine/src/lighting/struct.rs:63 `lights` 标了 `#[get(pub(crate), type(clone))]`（lombok-macros `type(clone)` = 返回 T 克隆），lighting/impl.rs:205 `for light in self.get_lights().iter()` → 每次 shade 一次 Vec 堆分配 + memcpy。

- 频率：CPU raytrace 路径每像素每 bounce 一次（trace_bounces → shade，raytracing/fn.rs:179）。
- 量化：320×240 内部分辨率 ≈ 76.8K 主光线 × ~2 次命中 ≈ **15 万次 Vec clone/帧**。**直接违反 `RayTraceScene` 文档「no heap allocation per ray or per bounce」的承诺**（raytracing/struct.rs:60-62）。
- 修法：getter 去掉 `type(clone)` 改返回 `&[Light]`，一行改动。

### 5. [仍开放] `Signal::create` 每次 `Box::new(SignalInner)` + mount 路径 bridge 放大

core/src/reactive/signal/impl.rs:43 每次 `Box::new(inner)`，无 arena/slab/对象池。mount 路径放大器：每个 signal 属性 renderer 额外 `Signal::create` 一个 bridge（render/impl.rs:762）、`as_reactive_text` 每响应式文本一个（vdom/cast/impl.rs:207）、`bool_to_attr` 每 bool 属性一个（attribute/impl.rs:241）。

- 量化：100 个 signal 属性 = ~200 次 SignalInner Box alloc + 各带 listeners Vec/闭包 Box。wasm allocator 单线程 Box::new ≈ 30-80ns + page fault 风险。
- 修法：typed slab（槽位+索引），Drop 归还。SignalInner 结构不变，只换分配策略。

### 6. [仍开放] bridge signal 链路重

render/impl.rs:775-805（属性 signal）、810-829（InnerHtmlSignal）、831-866（Text signal）：每 `{sig}` mount = `Signal::create` Box + `track_signal_addr` 2 次 JS（:787/:831）+ `attr_name.to_string()` + `element.clone()` + 2 个 Box 闭包 + `BridgeRefsCell::track`（:805/:866，HashMap+HashSet 分配）。每 signal set = `is_connected` 1 JS + `get()` String clone + `set_attribute_or_property` 1 JS。

- 修法：(a) subscribe 闭包直连 DOM 节点干掉 bridge 中转（signal Copy，addr 可直接作 key）；(b) 或 html! 宏对 `attr: {sig}` 直接生成 register_attr_listener 路径。配合二档的 Rust 侧 `HashMap<euv_id, Vec<usize>>` 替代 DOM attribute 存储。

## 二档：局部 10-30%

### core renderer（Worker A）

7. **[仍开放] `track_signal_addr` N+1 写放大**：dom/impl.rs:172-181，每 signal 属性 get_attribute（1 JS）+ String 拼接 + set_attribute（1 JS）。K 个 signal 属性的元素 = 2K 次 JS。修法：create_dom_with_doc 属性循环用 SmallVec 收集 addr，循环结束一次 set_attribute（2K→1 JS）。
8. **[仍开放] `dispatch_delegated_event` 祖先链逐层 2 次 JS**：registry/impl.rs:143-187，每层 get_attribute（:167）+ parent_element（:184）；深度 10 的 click ≈ 20 次穿越/事件。修法见「已知错误论据」#3——JS 端 glue walk，不是 composed_path。
9. **[仍开放] `data-euv-signal-addrs` usize 列表序列化进 DOM attribute**：dom/impl.rs:172-181 写 + render/impl.rs:1190-1195 cleanup 解析。修法：Rust 侧 `HashMap<euv_id, Vec<usize>>`，cleanup_subtree 已读 euv-id 顺带查表，删掉该 attribute 全部读/写/解析 JS 穿越。
10. **[仍开放] `patch_attributes` 每次建两个 HashMap**：render/impl.rs:255-262，每次 patch 每元素 2 次堆分配 + ~2A 次 SipHash；属性典型 1-5 个，线性 find 更便宜。1000 元素树一次全量 patch = 2000 次 HashMap 分配。修法：n<8 线性扫描或复用 thread_local 缓冲。
11. **[仍开放] keyed diff 无 LIS**：render/impl.rs:458-538，每次 keyed patch HashMap+HashSet 各 1 分配；反转 N 个 keyed 子节点 = N 次 insert_before 而非 N-LIS(N)。修法：标准 LIS（参考 ivi/udomdiff）。
12. **[已落地 PR #178] positional 删除循环 `last_child()` 每轮调两次**：render/impl.rs:610 与 :615，每删一个子节点 3 次 JS（2×last_child + remove_child）。修法：存下第一次结果复用（3→2 JS/删除）。
    > ✅ 已落地：PR #178 (5918d90)，第一次结果存 `last_child` 复用（现 render/impl.rs:633-641）。
13. **[仍开放] `cleanup_subtree` 每元素 ≈ 4+N 次 JS**：render/impl.rs:1204/:1209/:1214 三次 get_attribute + :1220 child_nodes + 每子节点 :1223 get（5918d90 复核行号，fn 入口 :1203）。修法：一次 `query_selector_all("[data-euv-id],[data-euv-dynamic-id],[data-euv-signal-addrs]")` 拿全标记后代（1 JS），Rust 侧逐个清；配合 #9 再减。
14. **[已落地 PR #178] `patch_attributes` 对 Event 属性无条件重 attach**（汇总者已读码确认）：render/impl.rs:296-298，每次 patch 每个事件属性都调 `attach_event_listener`（:1219 get_attribute 1 JS + 2 次 HashMap 查询 + handler Rc clone），不比较 handler 是否变化。频率：每 render × 每事件属性。修法：`Rc::ptr_eq` 比对旧 callback，相同则跳过。
    > ✅ 已落地：PR #178 (5918d90)，新旧 handler `Rc::as_ptr` 比对相同则跳过 attach（现 render/impl.rs:296-315）。
15. **[新] `window_event_listener` 每事件 1 次 Vec 分配 + 每 handler 2 次 HashMap 查找**（汇总者已读码确认）：registry/impl.rs:505-526，先 collect 全部 handler id（:509），再逐个二次 `get`（:514）。频率：每 window 事件（resize/scroll 高频）。修法：索引循环内边查边调（回调期间 unregister 则跳过），省 Vec 分配与一半查找。
16. **[新] `setup_dynamic_node` 每 dynamic mount 3 次 Box**：render/impl.rs:938/:944/:945（Box\<Renderer\> + Box\<usize\>(last_arm) + Box\<dyn FnMut\>，fn 入口 :916，5918d90 复核行号），外加 register_dynamic 再 Box SignalUpdateSlot（registry/impl.rs:291）。频率：每 `{sig}`/`{if}`/`{match}` 挂载。修法：renderer+arm 合并进单个 Box 的 struct。

### core reactive + vdom（Worker B）

17. **[部分落地 PR #179] `Signal::get()` 永远 clone，无只读 API**：signal/impl.rs:70/:76，无 `with(FnOnce(&T))`；`set()` :301 调 `get_dependents()`（:284-286）每次有效 set clone 一个 `Vec<usize>`。修法：加 `with`；set 内锁内迭代或 swap 出 dependents。
    > ◐ 已落地一半：PR #179 (69ecc2d) 新增 `Signal::with(FnOnce(&T))`（现 signal/impl.rs:99），首个用户为 i18n；`set()` 内 dependents Vec clone **仍开放**。
18. **[已落地 PR #178；后续 PR #180 OPEN] `join(&CHAR_SPACE.to_string())` 6 处原样未改**：attribute/impl.rs:129/:152/:186/:200/:671/:715（merge_class/merge_style/style_string/style_string_owned）。已 grep 全 core/ 无其他同类残留。频率：每带 class:/style: 元素每 render（signal 分支每次 signal 更新再跑）。修法：**把常量类型从 `char` 改成 `&'static str`**——`const.rs:31` 的 `pub(crate) const CHAR_SPACE: char = ' '` 改为 `pub(crate) const CHAR_SPACE: &str = " "`，6 处调用点改 `join(CHAR_SPACE)`。`join` 分隔符本来就要 `&str`，`.to_string()` 是白付的堆分配；`CHAR_SPACE` 全 core 仅这 6 处使用，改类型无连锁影响（2026-09-10 用户确认此写法优于 `join(" ")` 字面量，保留命名常量）。
    > ✅ 已落地：PR #178 (5918d90) 先以 `join(" ")` 字面量消除堆分配并删除旧常量；**PR #180 (1042d8b, OPEN)** 按用户偏好恢复命名常量——`pub(crate) const CHAR_SPACE: &str = " "`（const.rs:31）+ 6 处 `join(CHAR_SPACE)`（attribute/impl.rs:129/:152/:186/:200/:683/:727）。
19. **[仍开放] `try_reclaim_inactive(usize::MAX)` 全表扫描**：signal/impl.rs:609（5918d90 复核行号），仍 `map.iter().filter().collect()` 全扫 BridgeRefsCell + 每次调用 1 个 candidates Vec 分配（doc 已改写但语义未变）；hook/impl.rs:57 `switch_arm` 每次 match arm 切换（=每次路由切换，macros/src/html/impl.rs:474 emit）触发一次。修法：候选小队列 drain 而非全扫。
20. **[新] merge_class/merge_style 每 render 中间分配链**：attribute/impl.rs:96-154/:170-202，非 signal 路径每 class `css.get_name().to_string()` + 每 Text clone + `collect::<Vec<String>>` + join；signal 路径再 `values.to_vec()`（:101/:175 整数组 clone）+ `Box::new(compute)` + bridge `Signal::create`。N 个 class 值 ≈ N+2 次堆分配/render（signal 路径 +3）。修法：`String::with_capacity` 直接拼，跳过中间 Vec；静态段借 &str。
21. **[新] `VirtualNode::get_child_node` 深克隆整棵 children 子树**：vdom/node/impl.rs:332-341（fn 入口 :332，5918d90 复核行号；`children.clone()`），ui/ 共 12 处组件 view（button/card/alert/info/logo/modal/router 等）每次组件 render 调一次。子树 M 节点 = M 次 Vec/String 递归 clone/组件 render。修法：返回 `&[VirtualNode]` 或 Rc 切片。

### macros + ui（Worker C）

22. **[部分落地 PR #179] i18n `t()` 每次调用深克隆整张翻译表**：ui/src/hook/i18n/impl.rs:120 `self.get_messages().get()`——Signal::get 永远 clone（#17 的放大器），此处 T = `HashMap<String, HashMap<String, String>>`，外加 :118-119 两个 locale String clone。100 处 t() 的页面每 render 深克隆整表 100 次。修法：消息表移出 Signal 放 OnceLock/Rc（表不响应式，locale 才是），或先落 `Signal::with`。
    > ◐ 已落地一半：PR #179 (69ecc2d) `t`/`locale_count`/`active_message_count` 改用 `Signal::with` 借读（现 i18n/impl.rs:117-141），整表 clone 消除；消息表移出 Signal 的完整重构（OnceLock/Rc）**仍开放**。
23. **[新] vconsole 每 render 3 次全量过滤+克隆日志**：ui/src/component/vconsole/view/fn.rs:219/:227/:232 各调一次 `Console::filter_entries`，每次 `logs.get()` 克隆整个 Vec\<ConsoleEntry\>（hook/impl.rs:125）+ 逐条 entry.clone()（:136）+ reverse；200 条上限下每 render ≈ 600 条 entry clone。`append_entry`（hook/impl.rs:153-159）每条日志 get()+set 全 vec clone。修法：filter 结果做 computed 缓存；append 走 in-place 变异专用 API。
24. **[新] virtual_list 每滚动帧的分配与 JS 穿越**：ui/src/component/virtual_list/view/fn.rs:97 每可见项 `format!("height: {item_height}px; ...")`（item_height 跨项跨帧不变，可 hoist——50 项视口每帧 50 alloc→1）；:96 `key: index.to_string()` 每项每帧；:109/:111 两个 format! 每帧。事件侧 hook/impl.rs:33-37 每次 scroll 事件 get_element_by_id+scroll_top+client_height = 3 次 JS 穿越，可缓存 Element。修法：height 串 hoist、容器 Element 用 NodeRef 缓存。
25. **[新] touch hook 每事件每触点 ~10 次 `Reflect::get(event, JsValue::from_str(...))`**：ui/src/component/touch/hook/impl.rs:41-71/:130-160/:200+（identifier/clientX/clientY/screenX/screenY/pageX/pageY + touches 列表），每次 from_str 还分配 JS 字符串。touchmove 60-120Hz。修法：web_sys `Touch`/`TouchList` typed getters（仍是 JS 调用但免字符串查找与分配）。
26. **[新] camera QR 扫描每 tick 泄漏 2 个 Closure**：ui/src/component/camera/hook/impl.rs:259-289 每个 scan interval 新建 on_detected/on_scan_error 并 `.forget()`（:288-289），扫描期间内存单调增长；每 tick 还有 `Reflect::get(detector,"detect")`（:247）+ query_selector。修法：一次性持久 Closure 或改 wasm_bindgen_futures async 循环。
27. **[新] attr 级响应式 if/match 每 render 成本**：`class: if {cond} {..}` → `AttributeValue::reactive(...)`（emit 于 macros/src/html/impl.rs:611/:626）= `Signal::create`（Box SignalInner）+ register_attr_listener 全局注册（attribute/impl.rs:72-79），每元素每 render 一次；且 attr_if_to_tokens/attr_match_to_tokens 对 Reactive 模式每分支 emit `(#body).to_string()`（html/fn.rs:1509/:1568），字面量分支也分配；fn.rs:1481 注释自称 emit `IntoReactiveString::into_reactive_string`，实际是 `.to_string()`——**注释与代码不符**（又一个 OPT 标记式 doc 漂移实例）。修法：字面量臂 emit `&'static str` 经 Cow；或宏对全字面量臂的 attr-if 生成两态 Signal 复用。
28. **[新] 参数化 class!/vars! 每次调用重建 Css**：macros/src/class/impl.rs:390-396 参数化分支无 OnceLock，每 render 每调用 = Css::new（name/style 各 1 String）+ inject_style HashSet 检查；vars! 参数化路径 var/impl.rs:118-124 还有 `[...].concat()` + 每参数 `format!("{:?}")`。修法：按 (name, 参数序列化) 全局缓存。
29. **[新] 字面量文本节点每 render 1 String alloc**：宏 emit `TextNode::new("hello".into(), None)`（html/impl.rs:426-429），`TextNode.content: String`（vdom/node/struct.rs:20-32）。markdown 文档页数百个文本节点 = 数百 alloc/render。修法：content 改 `Cow<'static, str>`，宏对字面量 emit Borrowed。
30. **[新] markdown/navbar/sidebar/nav 每 render format!**：markdown/view/fn.rs:77 `format!("language-{lang}")`、:146 `format!("docs-container {kind}")`（lang/kind 来自 &'static AST，可构建期预拼）；navbar/view/fn.rs:49/:120、sidebar/view/fn.rs:78/:96、nav/view/fn.rs:38-43 每项 `format!("#{link}")`；sidebar 每项还有 route_signal.get() String clone（:59）与每组 collapsed.get() Vec clone（:87）。频率：路由/主题切换级，单项量级小。

### engine（Worker D）

31. **[已落地 PR #179] uniform/buffer 上传每次新建 JS typed array**：update_uniform_buffer（renderer/impl.rs:3082）`Float32Array::from(data)`、write_buffer（:3716）`Uint8Array::from(data)`——每帧每 buffer 1 次 JS 数组分配 + memcpy。修法：`Float32Array::view`/`Uint8Array::view`（借 wasm linear memory，零拷贝）或缓存持久 typed array。
    > ✅ 已落地：PR #179 (69ecc2d)，两处均改 `unsafe { ...::view(data) }` 零拷贝（现 renderer/impl.rs:3126/:3767）。
32. **[已落地 PR #178] `SsaaCanvas::present()` 每帧重放不变的 quality 状态**：renderer/impl.rs:1234-1247，每帧 apply_quality = set_image_smoothing_enabled + 2×Reflect::set + 4×from_str ≈ 7 次 JS 穿越/帧，而状态从不变化。修法：仅 init/quality 变更时应用。
    > ✅ 已落地：PR #178 (5918d90)，quality 预设在构造时 `enable_smoothing` 一次应用（现 renderer/impl.rs:1270 present 不再调 apply_quality）。
33. **[已落地 PR #179] physics 每 step 堆分配（2D+3D）**：physics/impl.rs:398（2D）与 :756（3D）`pairs: Vec::new()`/步；3D 另有 :760-765 `bboxes` collect Vec(N 体）/步；grid.clear()（spatial/impl.rs:88-90/:225-227）是 HashMap::clear，每步 drop 所有 cell 的 Vec buffer，下一步 insert 逐 cell 重新分配。注：query_buffer/query_seen 已复用（好）。修法：pairs/bboxes 提为 world 持久字段；grid 清表改 `values_mut().for_each(Vec::clear)` 保 buffer。
    > ✅ 已落地：PR #179 (69ecc2d)，2D/3D pairs 改用 world 持久 `pair_buffer`（现 physics/impl.rs:402/:773，每步首行 clear 复用）；3D bboxes 落地为 `Vec::with_capacity(body_count)` 预分配（持久 bbox_buffer 方案因 split-borrow 限制放弃，见 commit message）；**grid.clear 保 buffer 未做，仍开放**。
34. **[部分落地 PR #179] `begin_render_pass_full` 每帧重建 pass descriptor**：renderer/impl.rs:2451，~8-15 次 Reflect::set + ~10 次 from_str + 2-3 个 Object + 1 个 Array，仅 clear color 逐帧变。修法：descriptor 结构化缓存，或 extern 绑定 + 静态 property 名常量。
    > ◐ 部分落地：PR #179 (69ecc2d) 的 `cached_method_name()` 接住了该函数 9 处 from_str（现 renderer/impl.rs:2486 起）；descriptor Object/Array 每帧重建 **仍开放**。
35. **[新] `set_bind_group_with_dynamic_offsets` 每调用 1 JS Array alloc + N 次 set**：renderer/impl.rs:5015/:5053（fn 入口 :5002/:5043，5918d90 复核行号）。动态偏移做 per-entity uniform 时 = 每实体每帧 1 次。修法：Uint32Array::view 一次性传或缓存 Array。

### 建议关闭的旧项（降级，不再跟踪）

- **`set_attribute_or_property` 字符串级联**（dom/impl.rs:95-161）：确认仍在，但每条路径恰好 1 次 JS 调用收尾，dyn_ref 是纯 Rust，短串比较被 LLVM 编成 jump table，真实可省 <5% CPU（已知错误论据 #1/#2）。
- **`inject_style` 每次 patch 哈希查找**（vdom/attribute/impl.rs:541 HashSet\<String\>::contains，被 render/impl.rs:320/:328/:788/:796 调用）：纯 Rust 侧、仅 should_set 时触发，~30-80ns/次，相对 JS 穿越可忽略。

## 三档：架构级（晚做比早做贵）

36. **[仍开放] 静态子树零共享，零进展**：`VirtualNode::Element.children` 仍是 `Vec<VirtualNode>`（vdom/node/enum.rs:63），全 core 无 `Rc<[VirtualNode]>`/模板克隆；DynamicNode 每次 render 全新建树（node/impl.rs:188-191），visual_eq（render/impl.rs:1110）与 VirtualNode PartialEq（node/impl.rs:112-158）仍全树递归逐节点比，`(Dynamic,Dynamic)` 恒 false（:154）。html! 展开产物（cargo expand 实证）每次 render 全量重建所有 VirtualNode，无静态提升。中间态：`children: Rc<[VirtualNode]>` 让宏生成共享常量；终极：SolidJS 式模板克隆。**注意：R1 修复前该项的实际痛感被 PartialEq 回归放大——先修 R1 再评估。（2026-09-10 更新：R1 已随 PR #178 落地，可重新评估。）**
37. **[仍开放] for 循环与 inline-if 混合 children 仍 emit `Vec::new()` + push/extend**：macros/src/html/fn.rs:1228/:1315、html/impl.rs:518-523（纯静态 N 子节点已 `vec![]` 精确容量，见已闭环）。修法：for 循环用 `size_hint().0` 做 with_capacity；SmallVec/ThinVec 未引入（每元素每 render 仍 1 次 Vec 堆分配）。
38. **[已落地 PR #179] `SceneManager::update` 每帧 clone `Option<String>`**：engine/src/scene/impl.rs:105 `get_mut_current_scene_name().clone()`；同文件 render()（:131）已用正确的 Rc clone 模式，update 没有。修法：先 clone Rc 再查表，零堆分配。
    > ✅ 已落地：PR #179 (69ecc2d)，update 改借用 `try_get_current_scene_name()` + clone SceneRc（现 scene/impl.rs:110）。
39. **[新] input 事件提取走 Reflect 而非 typed getter**：engine/src/input/impl.rs:15（键盘 code，1 Reflect+from_str+String alloc/事件）、:31（mouse button）、:60/:65（mousemove 每事件 2 Reflect+2 from_str，~120/s）。修法：`event.unchecked_ref::<KeyboardEvent>().code()` / `MouseEvent::client_x()`。
40. **[新] DrawList batching 被逐粒子颜色击穿**：particle render（particle/impl.rs:188-203）每粒子 lerp 出不同 Color → replay_context 的 batch_key 每粒子变 → 每粒子 set_fill_style_str + `Color::to_css` String 分配（math/impl.rs:1021）+ begin_path/arc/fill。N 粒子 ≈ N String alloc + 3N JS 调用/帧。修法：粒子颜色量化 bucket 或 replay 前按颜色排序；replay 内换用已有的 `write_css_rgba`（:1035，buffer 复用版）。
41. **[仍开放] per-property signal（每 attribute 一个独立 signal）**：需重写整个 attribute 系统，继续挂账。

## 推荐动手顺序（按 风险×收益）

> 2026-09-10 同步：PR-1/PR-2/PR-3 已全部落地（PR #178）；PR-6 的 Signal::with 与 PR-4 的 #31 已落地（PR #179）；#2/#17/#22/#34 部分落地。剩余待做见下方重排。

1. **PR-1 ✅ 已落地（PR #178, 5918d90）**：R1 PartialEq 补 StaticText/CssRef/交叉臂 + R2 三个包装点透传 + html! 字面量 style 宏展开回归测试。
2. **PR-2 ✅ 已落地（PR #178）**：scheduler `current_time()` Reflect 取 Function 后 call0——on_update 复活 + 每帧省 4 次 JS 穿越。
3. **PR-3 ✅ 已落地（PR #178）**：R3 detached gate + #14 Event `Rc::ptr_eq` + #12 last_child 复用 + #18 join 6 处 + #4 lighting getter + #32 SsaaCanvas 幂等。#18 的命名常量恢复由 PR #180（OPEN）收尾。
4. **PR-4 ◐ 部分落地（PR #179）**：#31 typed array view ✅；#2 落 thread_local `cached_method_name` helper + 10 处样板（begin_render_pass_full/submit）；#34 的 from_str 部分被接住。**剩余：#2 全量 Function 缓存 + #34 descriptor 结构化缓存。**
5. **PR-6 ◐ 部分落地（PR #179）**：#17 `Signal::with` ✅，#22 借 with 落地 borrow 版。**剩余：#5 Signal typed slab、#17 的 set() dependents clone、#22 完整版（消息表移出 Signal）。**
6. **PR-7 仍开放**：#1 patch 路径 DomOp 收集 + 批量 commit，未动。

### 剩余待做重排（2026-09-10）

1. **PR-A（engine Reflect 收尾，中风险高收益）**：#2 全量方法名→`js_sys::Function` thread_local 缓存（~230 处剩余调用点，同仓库 WebGL2 backend 是现成范式，#179 的 cached_method_name 是第一步）+ #34 pass descriptor 结构化缓存 + #35 dynamic offsets 改 Uint32Array::view。500 实体场景 7500→~500 次穿越/帧量级。
2. **PR-B（最大收益最大风险，压轴大头）**：#1 patch 路径 DomOp 收集 + 批量 commit。需要 commit.rs 新模块 + patch 函数签名改返回 + CDP 指纹 7 次 reload 回归（templates/cdp-mount-bench.py）。
3. **PR-C（core 数据结构上 Rust 侧）**：#9 `data-euv-signal-addrs` 改 Rust 侧 HashMap + #7 track_signal_addr 收集后一次写 + #13 cleanup_subtree query_selector_all 一次取。三件事同一主题，一个 PR。
4. **PR-D（中风险）**：#5 Signal typed slab + #6 bridge signal 重写 + #17 剩余（set() dependents clone）+ #22 完整版（消息表移出 Signal 放 OnceLock/Rc）。
5. **PR-E（低风险二档/三档打包）**：#10 patch_attributes 双 HashMap + #11 keyed LIS + #15 window_event_listener + #16 setup_dynamic_node Box 合并 + #19 try_reclaim_inactive 全扫 + #20 merge_class/merge_style 中间分配 + #21 get_child_node 深克隆 + #23-#30（ui/macros 局部项）+ #33 尾巴（physics grid.clear 保 buffer）+ #39 input typed getter + #40 particle batching。
6. **三档 #36/#37/#41**：R1 已随 #178 修复，#36 的静态子树共享痛感需重新实测后再定优先级；`Rc<[VirtualNode]>` 中间态可在宏侧先行。

## 非性能观察

- **SIGNAL_UPDATE_REGISTRY 键空间混用仍无结构性防护**：register_dynamic（registry/impl.rs:290，键=NEXT_EUV_DYNAMIC_ID 自增 id）与 register_attr_listener（:310，键=signal 堆地址）同一张 `HashMap<usize, _>`。实际碰撞仍理论级（堆地址远大于自增 id），建议键改 enum/高位 tag。
- **euv-cli 仍无 wasm-opt 步骤**；release wasm 还有 -Oz 体积空间。
- **[新] NodeRef 卸载后不清 None（正确性）**：`AttributeValue::Ref` mount 时 `node_ref.set`（render/impl.rs:817-820），但 `cleanup_subtree`（:1179-1205）无任何 NodeRef 处理，卸载后 `get()` 仍返回旧元素，与 noderef/struct.rs 文档承诺（"after unmount it is reset to None"）不符。
- **[新] 两处死代码进 wasm 产物**：vdom/fn.rs `diff_children`/`diff_keyed`/`diff_positional`（仅 core/tests/keyed 引用，且 diff_keyed:79 `old.iter().any(...)` 是 O(N²) 查重）+ reactive/cache LruCache（仅 tests 引用，且文档声称 put/get/remove O(1)，实际 `VecDeque::retain` 是 O(n)，cache/impl.rs:68/:119/:147）。合计 ~350 行。修法：`#[cfg(test)]` 或接入真调用方。
- **[新] fc89f7a commit message 误贴 PR #144 文案**（message 描述 OPT-10/11，diff 实为 OPT-13），读 git 历史对账时注意。
- engine 复核确认无问题的区域：lighting/raytracing 核心数学（除 #4 外）纯栈上计算；particle update retain+push 复用持久 Vec；Canvas2D immediate/replay 全 typed 调用；resize 的 configure+MSAA 重建仅 resize 触发，depth texture 有缓存早退（:3756）。

## 跨引用

- 上一轮清单：`references/euv-perf-findings-0.18.58.md`（含 OPT-10/11 落地记录）
- 更早快照：`references/euv-perf-findings-0.18.36.md`
- CDP mount bench 验证模板：`templates/cdp-mount-bench.py`
- euv 框架 API/坑表：`euv-standards` skill
