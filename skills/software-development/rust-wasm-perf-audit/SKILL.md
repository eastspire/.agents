---
name: rust-wasm-perf-audit
description: 'Use when auditing Rust-WASM app/framework performance.'
---

# Rust WASM 性能审计

> 成本模型：WASM 里纯 Rust 很快，**主要成本单位是 JS 边界穿越**（每次 web_sys 调用、Reflect、get/set_attribute、append_child）和**堆分配**（Vec/String/Box，wasm allocator 不便宜）。审计 = 数这两类。

## 审计顺序

1. **找热路径入口**：信号 `set()` → 调度 → 重渲染这条链每步走什么；引擎的 per-frame tick 走什么。
2. **数 JS 边界穿越**：hot loop 里每个 `get_attribute` / `set_attribute` / `Reflect::get` / `JsValue::from_str` / DOM 遍历都是一次穿越。
3. **数每次 render 的分配**：特别警惕注释自称 "zero-copy / returned by move" 但代码里无条件 `into_iter().map().collect()` 的——逐 arm 核实，Text/Empty 的 move 快路径不代表 Element/Fragment 不重建 Vec。
4. **读宏的产物，不读宏的输入**：`html!`/`class!` 生成的代码才是运行时真相（如静态 style 每次 render `.to_string()` 分配）。
5. **检查常数项反转**：n≤8 的属性列表建两个 HashMap 比线性扫描慢；"O(N) 慢" 的优化注释可能对错了量级。
6. **验证再上报**：每个发现给 file:line + 触发频率（每 render / 每信号 set / 每帧 / 每事件），按 频率×单次成本 排序。

## 落地优化点时的硬性流程

> 这是把 audit 发现变成 patch 的"交付循环",缺一步都会留下烂摊子。

1. **改 `OPT N:` 标记的代码前后,`grep -rn "OPT N\b" --include='*.rs'` 同文件同编号所有 doc 引用,一并同步修订**。仓库常用一套连续编号(`OPT 1`-`OPT 9`),同主题优化点会散落在多个函数 doc、`render()` 入口 doc、`mod.rs` 三段里,改一处不动别处会出现"代码加预扫描、注释仍写无预扫描"的矛盾(2026-09-02 euv `unwrap_component_owned` 实例:`subtree_has_component` 加完后 `render()` doc line 60-65 还说"single fused pass without pre-walk",立即误导下一个审计者)。grep 后逐处对账语义 + 修改。
2. **cargo check 目标 wasm 跑一遍再上报,且 exit code 不可被管道吞**。`rust-wasm-perf-audit` 多数改动落在 `core/` 里,只看 `cargo check -p <crate> --target wasm32-unknown-unknown` 不够,要把所有 wasm 入口 crate (euv 下是 `euv / euv-core / euv-engine / euv-ui / euv-example`) 一起编,因为 `html!` 宏调用方散在 `ui/` 和 `example/`,改 macro 输出类型不立刻报错,改宏输出 *格式* 时漏。

   **mandatory unpiped pattern** (2026-09-11 lesson, see `references/exit-code-masked-by-pipe.md`): the subagent/operator MUST invoke cargo with no pipe to tail/head/grep. Bash `$?` after `cmd | tail` is tail's exit (always 0), NOT cargo's. Pattern:
   ```bash
   cargo check -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example --target wasm32-unknown-unknown > /tmp/c.log 2>&1
   echo "cargo check exit: $?"   # MUST be 0; if 101, output is in /tmp/c.log
   ```
   Or `cargo check ... 2>&1 | tee /tmp/c.log >/dev/null; echo "exit: $?"`. **Never** report "exit 0" from `cmd | tail -N && echo "exit: $?"` — the exit code is the tail's, not the command's. This bug caused 14 sequential PRs to be merged into a broken master before detection (E0425 stale const references survived because every subagent's `cargo check ... | tail -5` reported "exit 0").
3. **`euv fmt` 后看 git status,不要被无关 file 惊到**:它会 macro-aware 展开后顺手修正注释缩进(2026-09 实例:改 `core/` 一处却格式化了 `ui/style/class/fn.rs` 注释 20 行)。这是 euv fmt 默认 macro-aware 行为,不是错。看 git diff stat 确认"非预期 file 是否仅缩进/注释"。**如果非预期 file 是上游脏状态而非本 PR 改动,用 `git checkout HEAD -- <file>` 撤回,保住 PR diff 范围干净**(2026-09-05 PR #144 实例:`euv fmt` 把 upstream master 的 `ui/src/style/class/fn.rs` 一起 format 了,该文件不在 PR 范围,撤回保住 `+146/-5` 的 6 files 干净 diff)。
   - **重要(2026-09-11)**: `euv fmt` 对含 `/* ... */` 块注释的 `class!` / `html!` / `vars!` macro 主体**不幂等**——`cli/src/fmt/fn.rs:818` 的 `add_indentation` 把块注释内部的 `\n + 缩进空白` 当作宏主体缩进重写,每次跑 +1 空格。这是 euv-cli's 真 bug,**修复 PR 在飞**(`fix/euv-fmt-non-idempotent-block-comments`)。修好之前,所有 PR 的 pre-commit 必须包括 `euv fmt && git checkout HEAD -- ui/src/style/class/fn.rs && cargo fmt --all`。完整诊断见 `references/euv-fmt-non-idempotent-block-comments.md`。
4. **OPT-style enum 改动要补 `From<impl>` 的 doc 注释说明引用语义**:zero-copy variant(如 `CssRef(&'static T)`)依赖外部 lifetime 保证(2026-09-05 实例:`class!` 生成的 `OnceLock<Css>` 才让 `&'static` 安全)。在 enum 变体 doc + impl 块顶部都写清楚"来源是 X, 不是任意 `&'static T` 都行"。
4. **续上一轮 audit session 第一件事是 cargo check + grep OPT N:`:上一轮可能落了 patch 没编译,或 patch 落了一半。盲目继续下一步会在错的 baseline 上叠错。先验证现状再决定是「推进下一项」还是「补全上一轮」。
5. **PR 范围检查:开 PR 前先 `git diff <newbase> --stat`,确认 diff 只含本 PR 计划改的文件**(2026-09-11 PR #194 实例教训:一个 fix-euv-fmt-bug 的 PR 误把 PR #180(CHAR_SPACE const restore, 已 merge)的 core/ 改动塞进了自己的 diff——subagent 在 stale base 上 fork 而没察觉,提交后才发现 `git diff origin/master --stat` 多了 2 个不该有的 core/ 文件。**rule: 任何 PR 创建前都要跑 `git diff <newbase> --stat`;若 diff 范围 ≠ 预期 scope,先 rebase (drop 不相关 commit 或 cherry-pick 到 fresh branch from current master) 再 push。**完整诊断见 `references/pr-194-scope-leak-from-stale-base.md`。)

## 跨 session 闭环:发现 → 列项 → 落地

> `references/euv-perf-findings-0.18.36.md` 是某个版本的快照,**下次 audit session 第一件事是 grep 该 reference 里的 #1、#2... 看是否还有未落地的项**,优先把"建议修法明确、改动局部"的一档项转成 PR(例如 0.18.36 清单 #1 `unwrap_component_owned` 零分配预扫描,本 session 已落:恢复 `subtree_has_component(&node)` 预扫描 + 拆分 `unwrap_component_owned` / `unwrap_component_owned_slow` 双函数,doc 同步刷新)。

## 热模式清单（命中即记录）

| 模式 | 症状 | 修法方向 |
|---|---|---|
| VDOM 分配流失 | 无组件子树也整树 `collect()` 重建 Vec | 零分配预扫描（`&VirtualNode` walk）+ 无变化直接 move 返回 |
| 小 n 建 HashMap | patch 属性时 1-5 个 attr 建 2 个 HashMap | n 小走线性 find |
| 桥接中间层 | source→bridge signal→DOM，每层 Box+registry+闭包+2 次 JS 写 | 闭包直连 DOM 节点；`data-*` 地址列表改 Rust 侧 HashMap |
| DOM attribute 当存储 | `data-x-addrs` 序列化/parse usize 列表 | Rust 侧 `HashMap<elem_id, Vec<addr>>` |
| 每帧 Reflect | `Reflect::get(obj, &JsValue::from_str(m))` 在 draw/set_pipeline 里 | `Function` 不显式绑 this → 首次拿到后 thread_local 缓存；彻底方案 `#[wasm_bindgen(extern)]` 绑定 |
| 事件委托逐层走 | 每事件 get_attribute × DOM 深度 | `event.composed_path()` 一次取整条链，纯 Rust 查表 |
| clone 链 | `get()` 每次 clone；`set()` clone dependents Vec | `with(FnOnce(&T))` 只读 API；dependents move 给调度器 |
| 全量扫描当回收 | 每次路由切换 `try_reclaim(usize::MAX)` 扫全表 | 候选小队列，drain 而非 scan |
| format!/join 微分配 | `join(&" ".to_string())`、循环 format! 追加 | 分隔符来自常量时**改常量类型为 `&str` 并保留命名常量**（如 `const CHAR_SPACE: &str = " "` 后 `join(CHAR_SPACE)`——2026-09-10 用户明确纠正：不要用字面量替换常量，euv PR #180 实例）；非常量才 `join(" ")`；循环追加 `push_str`/`write!` |
| 静态子树无共享 | DynamicNode 内静态子树每次重建+全树 eq | `Rc<[VirtualNode]>` 共享 / 编译期模板克隆（架构级） |
| 运行时字符串分派 | `set_attribute_or_property` 6 次字符串比较 + dyn_ref instanceof | 宏编译期知道 key，生成分派好的专用调用 |

## 验证方法学:CDP mount benchmark + byte fingerprint

> euv/WASM 框架改动验收**:除了 `cargo test` 全过,必须**在浏览器里实测**渲染输出是否完全相同(2026-09-05 PR #144 实例:166 native test 全过不等于渲染行为没破;CDP 7 次 reload 指纹一致才算 DOM 等价)。**`cargo test` 只能验证函数行为;`euv-example` 在浏览器里的渲染快照才是用户可见的"正确性"。**

最小验证脚本(`/tmp/bench-mount.py` 起手,需要 `headless chromium + remote-debugging-port=9222`):

```python
# 见 templates/cdp-mount-bench.py
import asyncio, json, websockets
async def measure():
    async with websockets.connect(ws_url) as ws:
        await call('Page.enable'); await call('Runtime.enable')
        for run in range(7):
            await call('Page.reload', {'ignoreCache': True})
            await asyncio.sleep(3)  # 等 wasm init + main 跑完
            r = await call('Runtime.evaluate', {'expression': '''
                (() => {
                    const all = document.querySelectorAll('#app *');
                    let digest = 0;
                    for (let i = 0; i < all.length; i++) digest = (digest + all[i].tagName.length + (all[i].textContent || '').length) | 0;
                    return {
                        allNodes: all.length, divs: document.querySelectorAll('div').length,
                        dataEuvIds: document.querySelectorAll('[data-euv-id]').length,
                        dataEuvDyn: document.querySelectorAll('[data-euv-dynamic-id]').length,
                        dataEuvSig: document.querySelectorAll('[data-euv-signal-addrs]').length,
                        bodyText: document.body.innerText.slice(0, 250),
                    };
                })()
            ''', 'returnByValue': True})
            print(run, r['result']['value'])
```

**关键指标**(2026-09-05 PR #144 验收用):
- `[data-euv-id]` 元素数量 → euv 给每个事件挂载元素打标,**只要数量稳定 = renderer 没有破**
- `digest` (tagName.length + textContent.length 累计) → **字节指纹**,reload 7 次完全一致才算 DOM 100% 等价
- `[data-euv-dynamic-id]` = DynamicNode 数量
- `[data-euv-signal-addrs]` = bridge signal 数量
- `nav.duration` warm reload median → 反映 mount commit 阶段效率

**坑**:
- `Page.reload` 后必须等 `Page.loadEventFired` **+ 额外 2-3 秒**让 wasm init + main() 跑完,否则 DOM nodes=0(2026-09-05 初次测时 60s timeout 内页面还没 mount 完)
- `wasm-pack build --target web` 第一次冷启动 wasm 模块 fetch 主导,nav.duration 300+ ms;**比较时只比 warm reload median**,不要比 cold
- 装 python `websockets` 库:`pip install websockets`(跟 `euv-examples` 测试 server 同款)
- 脚本存 `/tmp/` 不要污染 `example/www/`,后者是 `wasm-pack build` 的产物目录,会被 build 脚本清掉

## 产出格式

分级清单（确定大头 / 局部 / 架构级），每条：file:line + 触发频率 + 量化（"1000 元素树 = 每次更新 1000 次 Vec 分配"）+ 修法。结尾给动手顺序建议。


---

## euv 引擎性能审计 2026-09-30 结论:两项已优化,一项已落地(OPT 40)

> 下次审计先读这一节,不要重复提 B1/B2。

### B1 WebGL descriptor cache —— **已存在,不需要做**

`use_program` 早有脏检查(`engine/src/renderer/webgl/impl.rs:2090`):
`if !Object::is(self.get_bound_program(), candidate)` 才发 `useProgram`。
实测 WebGL 每帧 **4 次 GL 调用**(clearColor / clear / useProgram / drawArrays),已近下限。

**更重要的是 WebGL2 没有 render-pass descriptor 这个对象** —— 状态直接设在 context 上,
不存在 WebGPU 那个 `RenderPassDescriptor` 可以缓存。给不存在的东西做缓存是照搬概念。

### B2 静态子树共享(`Rc<[VirtualNode]>`) —— **实测无可回收的浪费**

实测(counter 页一次 signal 更新 / timer 页 6 秒):
- `createElement` **0** 次、`setAttribute` **0** 次、`append/remove` **0** 次
- 一次更新只有 **1 次** Reflect 穿越;MutationObserver 6 秒 **0** 条记录
- `render()` 走 `patch_root` 增量,不是全量替换

细粒度 patch 已在工作,静态子树并没有被重建。**改这个是纯架构复杂度换零收益。**

### B3 事件委托祖先链 —— **已落地为 OPT 40**

改动前实测:event 页一次点击 **71 次 `getAttribute`**,0 次 `composedPath`。
原因是 `registry/fn.rs` 的 Rust 循环每层祖先一次 `get_attribute` + 一次 `parent_node`
= 每层 2 次 JS 穿越;该按钮祖先链深 **15** 层。

**做法(用户指定)**:不用 `#[wasm_bindgen(inline_js)]`(那会多出
`pkg/snippets/.../inlineN.js` 文件,数量随 feature 增长),改为
**`Mount::setup` 里 `js_sys::eval` 一次性把 `__euvEventIdChain` 注入 globalThis**,
之后按名调用。注入幂等,重复 mount 不重复 eval。

实现要点:
- `thread_local! RefCell<Option<Option<Function>>>` 缓存 handle:外层 `Option` = "查过了",
  内层 `None` = "查过且不存在",这样 host 若剥掉该全局,代价是每页一次探测而非每事件一次。
  **用 `RefCell` 而不是 `UnsafeCell`**:`Option<Option<Function>>` 不能 move 出裸指针,
  `UnsafeCell` 版本编译不过(也没有 unsafe 的必要)。
- `Function::call2(this, a1, a2)` **第一个参数是 this**,要传 `globalThis`,不是事件。
- 保留纯 Rust 祖先循环作为 fallback:全局缺失 / 返回非数组 / 出现非数字项时退回,
  **绝不让事件静默失效**。
- 三个字符串字面量按 §1.3c 进 `const.rs`(`GLOBAL_THIS_NAME` / `EVENT_TARGET_PROP`
  / 复用已有的 `DATA_EUV_ID`)。

**验收**(浏览器实测,event 页 412 节点):
- `globalThis.__euvEventIdChain` 是 function ✓
- `example/www/pkg/snippets` **不存在** ✓
- 包体 2,316,848 → 2,319,203 bytes(**+2.3KB**,即注入的那段 JS)
- 包装 global 计数:一次点击触发 **6 次** fast-path walk(回退路径会是 0)✓
- 正确性:counter 点击 0→1、form 输入 `aabbcc` 全部正常 ✓

**测量陷阱(这次踩了两次)**:祖先遍历的 `getAttribute` 次数**不是**好指标 —— 快路径把
这些读取搬进了 JS,`getAttribute` 计数不降反升(58~88),因为它连同 click 触发的
re-render 写入一起计。**唯一可靠的判据是"注入的 global 被调用了几次"**:
回退路径必然是 0。计数包装必须装在 wasm 缓存 handle **之前**,
否则 Rust 缓存的是旧 Function,包装无效(会误读成 0 = 快路径没生效)。
用 `Page.addScriptToEvaluateOnNewDocument` + 轮询等 global 出现再包装。

## 关联

- euv 专项发现（0.18.36 实测，含 file:line 清单）：`references/euv-perf-findings-0.18.36.md`
- euv 0.18.58 发现 + PR #144 闭环（OPT-10/11 已落地）:`references/euv-perf-findings-0.18.58.md`
- euv 0.20.6 发现(4-worker 并行审计;含 OPT-10/11 引入的 PartialEq/E0308 回归、OPT-13 detached 误覆盖、scheduler current_time 恒 0 等功能性 bug):`references/euv-perf-findings-0.20.6.md`
- euv 0.22.2 example+cli+build config 发现(example 热路径 E1-E13、CLI wasm-opt 死配置、dev/release profile 问题;含 -Oz 实测仅 2.4% 残余空间):`references/euv-perf-findings-0.22.2-example-cli.md`
- **euv fmt 块注释不幂等 bug (2026-09-11)**: `references/euv-fmt-non-idempotent-block-comments.md`
- **PR 范围从 stale base 泄漏 (2026-09-11 PR #194 教训)**: `references/pr-194-scope-leak-from-stale-base.md`
- **exit code 被 bash 管道吞掉 (2026-09-11 最严重 session 教训)**: `references/exit-code-masked-by-pipe.md`
- **跨 PR 合并后 master 集成检查 + sync_workspace_version 失败 (2026-09-11 14-PR batch 教训)**: `references/post-merge-cross-pr-integration-check.md`
- **12-PR 批次流程教训 (2026-09-11)**: `references/lessons-from-12-pr-batch-2026-09-11.md`
- CDP mount bench 模板(浏览器渲染等价性验证):`templates/cdp-mount-bench.py`
- euv 框架 API/坑表:`euv-standards` skill
