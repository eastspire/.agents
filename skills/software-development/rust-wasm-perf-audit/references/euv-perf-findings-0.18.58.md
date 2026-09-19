# euv 性能审计发现清单 (v0.18.58)

> 实测自 `~/github/euv-dev/euv` @ commit `1f09cd5`（v0.18.58, 2026-09-04）。
> 行号随版本漂移，重查时按函数名 grep。按 频率×单次成本 排序。

## 关于本轮新增发现（v0.18.36 → v0.18.58 增量）

### ⚠️ 已知错误论据（必须在审计中否定）

**`dyn_ref::<HtmlInputElement>()` 不是 JS 边界穿越**。wasm-bindgen 在 WASM 端的 pure-Rust trait downcast（vtable + type tag 比对），0 次 FFI，单次 ~1-3ns。任何基于"消除 N 次 dyn_ref = 消除 N 次 JS 桥接"的优化收益估算都是错的——真实节省只是 N × 几纳秒。

**`set_attribute_or_property` 字符串重排优化（6 次比较 → 0 次）的真实收益**：LLVM -O3 release 模式下，短字符串字面量比较会被编成 jump table 或 immediate match，**实际 CPU 节省可能 < 5%**。报告里声称的"40-60% JS 桥接调用减少"严重高估——LLVM 已经在做这些优化。

## 一档：架构级（大头，新发现）

### 1. VDOM patch 完全没用 batch commit（架构级，3-10× 提升空间）
`core/src/renderer/render/impl.rs::patch_root` / `patch_attributes` / `patch_children_*` 每改一个 attribute / text / 子节点就**立刻** `set_attribute(...)` / `appendChild(...)` / `removeChild(...)`。每次都是 1 次桥接。patch 粒度 = 1 节点 = N 次桥接（N = 节点属性数 + 子节点数）。

- 真实优化空间：在 patch 阶段只**收集变更**到 `Vec<DomOp>`（纯 WASM 端内存操作，0 桥接），在 commit 阶段**一次性** apply，按 element 引用分组批量执行。
- Vue/Solid/React concurrent renderer 都做过这个。
- **改动量大**：需要新增 `commit.rs`、patch 函数签名改为返回 `Vec<DomOp>`、flush 边界设计。euv-example 整套 UI 行为不会受影响（接口签名不破坏），但需要谨慎回归测试。

### 2. `Signal::create` 每次 `Box::new(SignalInner)`（架构级，2-5× 内存吞吐）
`core/src/reactive/signal/impl.rs::create` 每次调用都 `Box::new(SignalInner { ... })`。100 个 Signal 属性 = 100 个独立 heap alloc + 100 个独立 free。wasm allocator 单线程下 `Box::new` 一次 ≈ 30-80ns + page fault 风险。

- 真实优化空间：bump arena / typed slab，signal inner 在 slab 里取槽位，Drop 时归还。Box alloc 变 stack push + index 分配。
- **改动量中**：SignalInner 结构不变，分配策略重构。需要把全局 `Vec<SignalInner>` 改为 `typed_arena::Arena` 或自实现。

### 3. `html!` macro codegen 质量（架构级，1.3-1.5× macro 展开后代码）
`macros/src/html/impl.rs` 生成的 Rust 代码常见坑：
- 用 `Vec::new()` 然后 `vec.push()` N 次，**没有** `Vec::with_capacity(N)` — 触发 N-1 次 realloc
- 对 `Option<T>` 频繁 `unwrap()` / `clone()`，**没有** `map_or_else`
- `match` 链没按概率排序，**没有** 编译器友好的 jump table
- 子节点用 `Vec<VirtualNode>` 而不是 `SmallVec<[_; 4]>` 或 `thin_vec::ThinVec`
- 静态 style 每次渲染 `#css_string.to_string()`（约 `macros/src/html/impl.rs:695`）→ 加 `AttributeValue::StaticText(&'static str)` 变体
- `From<&'static Css>` 深 deep-clone Css(name/style/pseudo_rules/media_rules) → 加 `AttributeValue::CssRef(&'static Css)` 变体,借用 class! 的 OnceLock 共享存储

- 真实优化空间：改宏模板的代码生成。最容易改、风险最低 —— 源代码不变，只是宏输出的 Rust 代码质量提升。

**2026-09-05 PR #144 (OPT-10 + OPT-11) 已落地 v0.18.58+**:
- `core/src/vdom/attribute/enum.rs` 加 `StaticText(&'static str)` 和 `CssRef(&'static Css)` 两个 variant
- `core/src/reactive/cast/impl.rs` `From<&'static Css>` 改 emit CssRef
- `core/src/renderer/render/impl.rs` 三处 match arm 加新 variant 分支
- `macros/src/html/impl.rs` 全静态 style 路径改 emit `StaticText(#css_string)`
- 4 个单元测试 + 170 native test 全过
- **7 次 reload DOM 字节指纹 (digest=16398) 完全一致**,`[data-euv-id]=44 / divs=77 / dyn=5 / sig=11` 与 baseline 1:1
- PR diff `+146/-5` 6 files (撤回 euv fmt 自动 format 的上游脏 `ui/style/class/fn.rs`)
- 验证方法学见 `templates/cdp-mount-bench.py`

**验证**(可执行性):
- 加 enum variant + match arm 后必须改 `#[derive(CustomDebug, Clone)]` 之外的所有 exhaustive match site;**`grep -rn "AttributeValue::" --include="*.rs" core/ ui/ example/ | grep -v "core/src/vdom/attribute"`** 找全 match sites
- renderer 三个 `match attr.get_value()` 都在 `core/src/renderer/render/impl.rs`(patch_attributes 295-335 + create_dom_with_doc mount 路径 720-790),加一个 `AttributeValue::CssRef(css) => { css.inject_style(); element.set_attribute_or_property(...) }` 就行
- 验证加 StaticText 的语义:hash check `format!("{:?}", cloned)` 含 "StaticText" 字面量 — CustomDebug derive 输出 variant 名

## 二档：局部（10-30% 局部提升）

- `track_signal_addr` 写路径 N+1 放大（`core/src/renderer/dom/impl.rs:172-178`）：每个 Signal 属性挂载都做 `get_attribute + String 拼接 + set_attribute`，5 个 Signal 属性 = 15 次 JS 桥接/元素。**这才是 cleanup 路径真正热点**，报告漏了。
- `event.composed_path()` 一次拿整条链（`core/src/renderer/registry/impl.rs:143` `dispatch_delegated_event`）替代祖先链 `get_attribute` × DOM 深度。20 层 = 20 次 JS 往返/事件 → 1 次。
- `Reflect::get(obj, &JsValue::from_str(m))` 在 engine draw/set_pipeline 里 203 处 → `Function` 不显式绑 this，首次拿到后 thread_local 缓存。
- `data-euv-signal-addrs` 序列化/parse usize 列表 → Rust 侧 `HashMap<euv_id, Vec<usize>>`。
- `try_reclaim_inactive(usize::MAX)`（`core/src/reactive/signal/impl.rs:577`，注释自认"walks the full map regardless of the cap"）→ 候选小队列，drain 而非 scan。
- `Signal::get()` 永远 clone（`signal/impl.rs:70`）；`set()` 里 `get_dependents()` clone Vec（:252）。加 `with(FnOnce(&T))` 只读 API。
- `join(&CHAR_SPACE.to_string())`：`core/src/vdom/attribute/impl.rs` 6 处（:116/:134/:168/:182/:653/:697），每次堆分配一个 `" "`。改 `join(" ")`。
- `patch_attributes` 每次建两个 HashMap（`render/impl.rs:249-256`）：属性典型 1-5 个，HashMap 分配+哈希 > 线性扫描。n 小走线性 find。
- keyed diff 无 LIS（`render/impl.rs:441`）；positional 删除循环 `last_child()` 每轮调两次（:584-591）。

## 三档：架构级（晚做比早做贵）

- 静态子树零共享：`DynamicNode` 内 `if { sig } { 大静态子树 }` 每次重建整树 + `visual_eq` 全树比。终极 = SolidJS 式模板克隆；中间态 = `children: Rc<[VirtualNode]>` 让宏生成共享常量。
- per-property signal（每个 attribute 一个独立 signal）：dispatch 时只标 dirty 的那一个。需重写整个 attribute 系统。

## 推荐动手顺序（基于本轮验证）

1. **先跑 `wasm-pack test --headless --release` 实际 mount 1000 节点基准**，看现在真实数字，别看理论。
2. **macro codegen 优化**：低风险高收益，PR 1。
3. **arena slab Signal**：中风险中收益，PR 2。
4. **batch commit**：高风险高收益，PR 3（最大）。
5. 砍掉报告里的"#1 Element cache" + "#4 Box::leak" —— 收益存疑。

## 非性能观察

- `SIGNAL_UPDATE_REGISTRY` 混用 dynamic id（自增）和 attr signal 堆地址两个键空间，理论可碰撞。
- euv-cli 无 wasm-opt 步骤；release wasm 还有 `-Oz` 体积空间。

## 跨引用

- 0.18.36 快照：`references/euv-perf-findings-0.18.36.md`
- euv 框架 API/坑表：`euv-standards` skill
- Rust 开发规范：`rust-standards` skill