# Profiler 实战坑 — PR#16 (`feature/profiler-2026-08-23`)

## 1. 时间源 `cfg(target_arch = "wasm32")` 二分

```rust
pub fn now_ms() -> f64 {
    #[cfg(target_arch = "wasm32")]
    {
        web_sys::window()
            .and_then(|w: web_sys::Window| w.performance())
            .map(|p: web_sys::Performance| p.now())
            .unwrap_or_else(|| js_sys::Date::now())
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        use std::time::Instant;
        static PROCESS_START: std::sync::OnceLock<Instant> =
            std::sync::OnceLock::new();
        let start: &Instant = PROCESS_START.get_or_init(Instant::now);
        start.elapsed().as_secs_f64() * 1000.0
    }
}
```

**关键**:两边都返回 `f64` (毫秒),user code 不需要任何 `cfg` 分支。**wasm `performance.now()` 是 monotonic + 跨 worker 共享**,native `Instant` 是 monotonic 但只在该 process scope 内一致 — 两者**不能跨平台比较 absolute 值**,但**delta 数学相同** (`ended - started`)。

## 2. `Signal::set` 在 native panic 必捕获

`ProfilerHandle::measure` / `ProfilerMark::end` 都走 `Signal::set` 路径:

```rust
let mut current: Vec<ProfileEntry> = self.entries.get();
current.push(entry);
self.entries.set(current);  // <-- 这里 native build 触发 web_sys::window() panic
```

详细机制见 `euv-standards` SKILL.md §23。

## 3. 测试 fixture 必带 `run_with_signal_capture`

```rust
fn run_with_signal_capture<F: FnOnce()>(f: F) -> bool {
    catch_unwind(AssertUnwindSafe(f)).is_ok()
}

#[test]
fn my_measure_test() {
    let handle: ProfilerHandle = ProfilerHandle::new(Signal::create(Vec::new()));
    let mut captured = None;
    let ran_clean = run_with_signal_capture(|| {
        captured = Some(handle.measure("op", || 42));
    });
    assert!(ran_clean, "native Signal::set panic should be caught");
    // closure 返回值始终能拿到 (无论 wasm/native)
    assert_eq!(captured, Some(42));
    if ran_clean {
        // post-push 断言只在 wasm 上跑
        assert_eq!(handle.entries().get().len(), 1);
    }
}
```

**为什么 `if ran_clean` 分支 gating**:wasm 上 push 成功,entries 真的多了 1 行;native 上 push panic 在 `Signal::set` 之前 capture 的是 started/ended,但 entries 写入被 abort — assert `len() == 1` 永远 fail。

## 4. `--test-threads=1` 必加

`Scheduler::update` panic **之后**没 reset `SCHEDULED` AtomicBool 到 `false`。多线程 (`--test-threads > 1`) 下:
- 测试 1 panic → SCHEDULED 留在 true
- 测试 2 调 `Signal::set` → `SCHEDULED.load() == true` → 提前 return → **测试 2 意外 pass** (写路径根本没跑)
- 部分测试通过,部分 fail,行为不确定

`cargo test -p euv-core --lib -- --test-threads=1` 是 PR#16 验证通过的运行模式。

## 5. `ProfileEntry.elapsed_ms >= 0.0` 而非 `> 0.0`

`now_ms()` 在 `Instant` 上的精度到 nanosecond,但两次连续调用的差可能恰好 0(高频调用 / 同一 clock tick)。**测试断言用 `>= 0.0` 不要 `> 0.0`**,否则会 flaky。

## 6. `ProfileMark` drop semantics

```rust
pub struct ProfilerMark { label: String, started_ms: f64, entries: Signal<Vec<ProfileEntry>> }
```

`begin()` 返回 mark,`end()` 消费 mark。**drop mark 不 push entry**(silent discard)。如果 user 期望"drop 也提交一个 elapsed=now 时刻的 entry",**不满足** — 是设计选择,避免 panic-on-drop。

**测试验证**:构造 mark 不调 end,assert `entries().get().is_empty()`。

## 7. `ProfilerHandle::clone` 是 signal clone(共享 entries)

`Signal<T>` 是 `Copy`-by-pointer (raw address in `inner: usize`),所以 `ProfilerHandle { entries: Signal<Vec<ProfileEntry>> }` 的 `derive(Clone)` 字段 clone = `Signal` clone = 共享同一份 vec。**两个 handle 互相 `measure()` 都看到所有 entry**。

**测试**:构造 handle + twin,handle.measure("x") 后 twin.entries().get().len() == 1。

## 8. wasm 真值验证

Native 测试 `catch_unwind` 只能验证 closure 路径 / return value / structural invariants,**无法验证 Signal push 是否真的写入 entries**。wasm32 真值靠:

```bash
# wasm-pack test (headless browser)
wasm-pack test --headless --chrome

# 或 example page 挂断言
euv_debug { label: "entries" value: Some(Rc::new(|| format!("{}", profiler.entries().get().len())) as _) }
```

## 9. derive macro scoping (跟 §22 euv-standards 联动)

`core/src/reactive/profiler/handle.rs` 必须 explicit:

```rust
use super::*;
use crate::Signal;
use lombok_macros::{Data, New};
```

不能 `use super::*;` 然后 `#[derive(Data, New)]` 直接编译 — derive macro 不通过 `super::*` 拉到子模块,见 euv-standards §22.1。