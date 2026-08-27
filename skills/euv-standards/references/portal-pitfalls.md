# Portal / pseudo-element 实战坑表 (euv-dev/euv#18)

PR#18 实现 `portal { target: "..." } children` 时撞到的具体坑。给后续做 `svg { namespace }` / `math { ... }` / 其他 Tag enum variant 的 session 用。

## 1. `document.body()` 类型陷阱: `Option<HtmlElement>` ≠ `Option<Element>`

```rust
// ❌ E0308: expected Option<Element>, found Option<HtmlElement>
let target: Element = document
    .query_selector(selector)
    .ok()
    .flatten()
    .or_else(|| document.body())
    .unwrap_or_else(|| marker.clone());

// ✅ .map(HtmlElement::into) 显式转换
let target: Element = document
    .query_selector(selector)
    .ok()
    .flatten()
    .or_else(|| document.body().map(HtmlElement::into))
    .unwrap_or_else(|| marker.clone());
```

**根因**:web_sys 的 `document.body()` 返回 `Option<HtmlElement>` (因为 body 永远是 HTMLElement)。`Element` 是 `HtmlElement` 的父类型,要从 `Option<HtmlElement>` 转 `Option<Element>` 必须 `.map(HtmlElement::into)` —— web_sys 已 derive `From<HtmlElement> for Element`,所以 `into` 自动可调用。

## 2. Macro emit `String::from(#expr)` 而非 `.to_string()`

```rust
// ❌ Signal<String> 触发: doesn't implement Display
let target_expr = quote! { (#expr).to_string() };

// ✅ Signal<String> 接受,user 写 target: signal.get()
let target_expr = quote! { ::std::string::String::from(#expr) };
```

**为什么不能用 `.to_string()`**:euv 的 `Signal<T>` 是核心 reactive type,但**没有实现 `Display` trait**(API 表面只有 `.get()`,不是 `.to_string()`)。Macro 强制 `.to_string()` 会让 `target: signal` 这种 reactive 用法直接编译失败。

**`String::from(#expr)` 接受**:
- `&str` / `&String` (普通静态)
- `String` (返回值,signal `.get()` 返回 String 就是这个)
- 任何 `Into<String>` impl

**User 写法对应**:
| 用户想 | 写法 | macro 展开后 |
|---|---|---|
| 静态 selector | `target: "#modal"` | `String::from("#modal")` → `String` |
| 动态 selector | `target: signal.get()` | `String::from(signal.get())` → 拷贝 String |
| 计算 selector | `target: format!("#host-{}", i)` | `String::from(format!(...))` → owned |

**不能直接 `target: signal`**(因为 `Signal<String>: !Into<String>`),必须 `.get()`。

## 3. Macro emit `compile_error!` 要 wrap in `quote!`

```rust
// ❌ syn 直接拒绝 "compile_error" 字面 token
.unwrap_or_else(|| compile_error!("..."));

// ✅ wrap in quote! 走 proc_macro2 路径
.unwrap_or_else(|| quote! { compile_error!("portal element requires a `target:` attribute") });
```

`compile_error!` 是 proc_macro,要在 macro 内部生成它,token 必须走 quote 输出,由外层 macro 编译器展开。

## 4. Marker 必须用 Element 别用 Comment

```rust
// ❌ Comment 节点会让 patch_children_positional 走 replace_child 分支
let marker = document.create_comment("euv-portal");

// ✅ 真实 Element 让 patch loop 当普通子节点
let marker = document.create_element("div").unwrap();
marker.set_attribute("data-euv-portal", selector);
marker.set_attribute("style", "display:none");
```

**根因**:`patch_children_positional` (render/impl.rs:474) 走 `dom_child.dyn_ref::<Element>()`,Element → patch_node 路径;非 Element → `replace_child` 路径。用 Comment 会让 portal 的 marker 在 re-render 时被无脑替换,丢失 portal 的 children 挂载点。

`data-euv-portal="<selector>"` 让 dev-tools inspector 一眼看出 portal marker(避免误以为是用户写的 div)。

## 5. `render_full_replace` 不在 patch loop 里 — portal 切换 target 需要 match arm 翻转

**Portal 增量 patch 故意 short-circuit**:

```rust
// patch_node element-element arm
if matches!(old_tag, Tag::Portal(_)) {
    return;  // portal 不参与 incremental patch
}
```

**为什么**:portal 的 children 在另一个 DOM 子树(target element),patch marker 的 children 会让它们被 mount 到 marker 里 → 错位置 + 双挂载。

**用户改 `target` 时怎么办**:
- ❌ 不能依赖 incremental patch
- ✅ match arm 切换触发 `render_full_replace`:
  ```rust
  match mode.get().as_str() {
      "stack" => html! { portal { target: "#stack" ... } },
      "page"  => html! { portal { target: "#page"  ... } },
      _       => html! { portal { target: "body"   ... } },
  }
  ```
- ✅ 主动调 `App::render_full_replace(vnode)`(已有 API,PR#3 之前就能用)

**文档化为 "known limitation + escape hatch"** —— 不要试图在 patch loop 里 hack target 切换,会污染 patch 算法的简洁性。

## 6. 顶层 `let _v = html! { ... }` 必须 type annotation

```rust
// ❌ E0282: type annotations needed for VirtualNode<_>
let _v = euv::html! {
    portal { target: "body" }
};

// ✅ 必须显式标注
let _v: VirtualNode = euv::html! {
    portal { target: "body" }
};
```

**根因**:euv html! macro 用 `VirtualNode::create_dynamic(move |_: &mut HookContext| { ... })` 包装,inner 闭包 type 不透明,compiler 推不出 outer VirtualNode<T>。Portal 触发更频繁(顶层 portal 没有 children,缺少 hint),其他 element 在 div/section 内也有同样问题但 `let v: VirtualNode = html! { div {} }` 是 euv 用户的惯例写法。

**throwaway crate 测试要主动加 `: VirtualNode`**(PR#18 撞了 4 次)。

## 7. `Tag` enum 加 variant 后 exhaustiveness 检查范围

加 `Tag::Portal(String)` 后,**所有 match `Tag` 的 arm 必须覆盖 Portal**。具体位置:

```bash
grep -rn "match.*Tag::\|match tag\b\|Tag::Element(\|Tag::Component(" /root/euv-wt/feature/<name>/core/src
```

**实地发现**(PR#18):
- `core/src/vdom/node/impl.rs:174` 的 `try_get_tag_name` — **需要**加 Portal arm(返回 None)
- `core/src/renderer/render/impl.rs:828, 887` 的 `unwrap_component` / `unwrap_component_owned` — **不需要**显式加 Portal arm,因为 generic arm `Element { tag, attributes, children, ... }` 会捕所有 Element(包括 Portal),compiler 不抱怨。
- `core/src/renderer/render/impl.rs:566` 的 `create_dom_with_doc` match `Tag` — **需要**加 Portal arm(自己 mount marker + 挂 children 到 target)

**经验**:写完加完 variant 后,跑 `cargo check` —— compiler 会列出所有缺 arm 的位置。比手动 grep 稳。

## 8. 测试模板 (9 tests + 端到端 crate)

**Native 测试**(9 个,覆盖 Clone/Eq/Hash/Debug/try_get_tag_name/不同 payload/空 payload):

```rust
fn portal_tag_is_clone()           // Clone derive
fn portal_tag_partial_eq_...()     // Eq derive,不同 selector 不等
fn portal_tag_is_hashable()        // Hash derive (keyed patch 需要)
fn portal_tag_debug_...()          // Debug derive (devtools inspect)
fn virtual_node_try_get_tag_name_returns_none_for_portal()  // 关键:API 不泄漏
fn virtual_node_try_get_tag_name_still_works_for_element()  // 回归:不变 Element 行为
fn virtual_node_try_get_tag_name_still_works_for_component() // 回归:不变 Component 行为
fn portal_tag_partial_eq_same_selector_equals()  // 优化:同 selector 不触发 remount
fn portal_tag_supports_empty_selector()           // unwrap_component pass-through 用
```

**端到端 throwaway crate**(5 种用法):
```rust
// 1. 静态 string target
// 2. signal accessor (target: signal.get())
// 3. 无 children
// 4. 嵌套在 section 内 + 普通 siblings
// 5. (可选)同一信号多次使用
```

每条都 `let _: VirtualNode = html! {...}`(必须 type annotation,见 §6)。

## 9. `unwrap_component` 在 `Tag::Portal` 下不强制改

实测:**generic arm `Element { tag, ... }` 会自动覆盖 Portal**,compiler 不抱怨。如果你的 `unwrap_component` 已经写成:

```rust
match node {
    Element { tag: Tag::Component(_), children, .. } => { /* 递归 */ }
    Element { tag, attributes, children, key, props } => { /* 通用 pass-through */ }
    Fragment(...) => { /* 递归 */ }
    Text(...) | Empty | Dynamic(...) => node.clone(),
}
```

那么 Portal 走第二个 arm,无需改动。**前提**:第二个 arm 没显式列 `Tag::Element(_)` 或 `Tag::Component(_)`(只写 generic `tag`),这样它真的捕所有 Element。

如果你的 unwrap 写成 `Element { tag: Tag::Element(_), ... } => ...` 这种 narrow pattern,会撞 exhaustiveness —— 重构成 generic `tag` 即可。

## 10. 完整 PR checklist (已用 PR#18 走通)

- [x] `cargo check --workspace` exit 0
- [x] `cargo check --target wasm32-unknown-unknown -p euv-core` exit 0
- [x] `cargo test -p euv-core --lib` ≥ 12 passed
- [x] 端到端 throwaway crate `html! { portal { ... } }` 5 种用法全部 `cargo check` 通过
- [x] `euv fmt --check` exit 0
- [x] `cargo fmt --all --check` exit 0
- [x] 4 处 Tag match 位置全覆盖(exhaustiveness 通过)
- [x] worktree: `feature/portal-2026-08-23`
- [x] PR body 4 段模板:Summary / Changes(table + LOC) / Testing(native + wasm + workspace + 端到端)/ Design notes(决策 + 拒绝的方案)
