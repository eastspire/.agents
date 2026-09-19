# euv 性能审计发现清单

> 实测自 `~/github/euv-dev/euv` @ commit `2f2e4fb`（v0.18.36，2026-09-02）。
> 行号随版本漂移，重查时按函数名 grep。按 频率×单次成本 排序。

## 一档：确定的大头

### 1. `unwrap_component_owned` 对无组件子树也整树重分配 ✅ 已落地（2026-09-02 session）
`core/src/renderer/render/impl.rs:949`（fn `unwrap_component_owned`，post-patch）→ `subtree_has_component(&node)` 预扫描 + `unwrap_component_owned_slow` 双函数拆分。
- patch 前注释自称 "Component-free trees are returned by move" —— 只对 `Text/Empty` 成立。`Element`/`Fragment` 分支无条件 `children.into_iter().map().collect()`，每元素每次渲染新建 Vec。
- 触发频率：每个 DynamicNode 每次信号更新 1-2 遍（render + visual_eq 前）。
- **落地方案**：恢复零分配 `subtree_has_component(&VirtualNode)` 预扫描，无组件直接 `return node;`；有组件再走 `unwrap_component_owned_slow`。预扫描 `iter().any(...)` 短路，第一处 `Tag::Component` 即返，不重建任何 `Vec`。`VirtualNode::Dynamic` 当叶子处理（其闭包每次重新产出新树，自己会再次走 `unwrap_component_owned`，不需要在此下钻）。
- **同时刷新的 doc**：`render()` 入口 doc line 60-65 旧版说"single fused pass without pre-walk"已改为「零分配预扫描 + 无组件 move 返回 + 有组件才走 slow」，`unwrap_component_owned` 函数 doc 也同步翻新。**下一步 audit 必须 grep 同 OPT 编号所有 doc 引用一并修**（这是 SKILL.md §「落地优化点时的硬性流程」#1 的由来）。
- cargo check 验证：`cargo check -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example --target wasm32-unknown-unknown` 0 错 0 警，17.85s。
- 下一步待补：未发 PR（fork + `gh pr create` 流程待触发，按 `gh-pr-creation-workflow`）。

### 2. engine WebGPU 每帧热路径全走 `Reflect::get` + `JsValue::from_str`
`engine/src/renderer/impl.rs:2874-2925`（`set_pipeline`/`draw`/`end_render_pass`/`finish_command_encoder`）；全文件 203 处 Reflect。
- 500 实体/帧 × ~4 调用 = 2000 次 from_str+Reflect/帧。
- 关键事实：`Function` 不显式绑 this（`call1(pass, ...)` 显式传 this）→ 首次拿到后 thread_local 缓存即可，热循环只剩裸 call。彻底方案：WebGPU 方法写 `#[wasm_bindgen(extern)]` 绑定。

### 3. 事件委托祖先链逐层 `get_attribute` JS 调用
`core/src/renderer/registry/impl.rs:143`（`dispatch_delegated_event`）
- 每事件从 target 到根每层 `get_attribute("data-euv-id")` + `parse::<usize>()`。20 层 = 20 次 JS 往返/事件；click 类无深度上限（`usize::MAX`，只有高频事件有 cap）。
- 修法：`event.composed_path()` 一次拿整条链（1 次 JS 调用），纯 Rust 查 HashMap。

### 4. 桥接 Signal 链路重
`render/impl.rs:718-741`（AttributeValue::Signal）、`render/impl.rs:779-795`（文本）、`core/src/vdom/cast/impl.rs:205`（`as_reactive_text`）
- 每个 `{sig}` 文本/属性 mount 时：bridge Signal（Box+全局 registry）+ 2 Box 闭包 + BridgeRefsCell 登记 + `track_signal_addr` 的 get_attribute+set_attribute **2 次 JS 写**。
- 每次 `set()`：clone + to_string 分配 + `is_connected()` JS 调用 + 再 clone。
- 修法：(a) `data-euv-signal-addrs` 改 Rust 侧 `HashMap<euv_id, Vec<usize>>`；(b) 文本闭包直连 `Text` 节点干掉 bridge。

### 5. `patch_attributes` 每次 patch 建两个 HashMap
`render/impl.rs:249-256`
- 属性典型 1-5 个，两次 HashMap 分配+哈希 > 线性扫描。OPT 5 注释的 "O(N) find 慢" 对错了量级。
- 修法：n 小线性 find。

### 6. 每次 match 路由切换全量扫 BridgeRefsCell
`core/src/reactive/hook/impl.rs:57`（`switch_arm`）→ `core/src/reactive/signal/impl.rs:577`（`try_reclaim_inactive(usize::MAX)`，注释自认 "walks the full map regardless of the cap"）
- 修法：`clear_listeners` 时把候选 push 进小队列，switch_arm 只 drain。

## 二档：局部

- `Signal::get()` 永远 clone（`signal/impl.rs:70`）；`set()` 里 `get_dependents()` clone Vec（:252）。加 `with(FnOnce(&T))` API。
- `join(&CHAR_SPACE.to_string())`：`core/src/vdom/attribute/impl.rs` 6 处（:116/:134/:168/:182/:653/:697），每次堆分配一个 `" "`。改 `join(" ")`。
- `set_attribute_or_property` 字符串级联 + dyn_ref instanceof（`core/src/renderer/dom/impl.rs:95`）。html! 宏编译期知道 `value:`/`checked:` key，应生成分派好的专用调用。
- codegen 静态 style 每次渲染 `#css_string.to_string()`（`macros/src/html/impl.rs:695`）。加 `AttributeValue::StaticText(&'static str)` 变体。
- `inject_style` 每次 patch 哈希查找（`render/impl.rs:311`）→ `HashSet<&'static str>`。
- `cleanup_subtree` 每元素 3 次 get_attribute（`render/impl.rs:1083`）→ 配合 #4a Rust 侧登记可纯 Rust 剪枝。
- keyed diff 无 LIS（`render/impl.rs:441`），乱序列表 DOM 移动非最优；positional 删除循环 `last_child()` 每轮调两次（:584-591）。

## 三档：架构级

- 静态子树零共享：DynamicNode 内 `if { sig } { 大静态子树 }` 每次重建整树 + visual_eq 全树比。终极 = SolidJS 式模板克隆；中间态 = `children: Rc<[VirtualNode]>` 让宏生成共享常量。

## 非性能观察

- `SIGNAL_UPDATE_REGISTRY` 混用 dynamic id（自增）和 attr signal 堆地址两个键空间，理论可碰撞。
- euv-cli 无 wasm-opt 步骤；release wasm 还有 `-Oz` 体积空间。
