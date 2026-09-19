# WebGPU Renderer PR 提交验证清单

> 2026-09-08 euv-engine PR #177 (https://github.com/euv-dev/euv/pull/177) 实测踩坑后沉淀。**改 `engine/src/renderer/{const,enum,impl,struct}.rs` 的任何 PR,提交前必跑下面这套检查**。

## 1. 0 warnings / 0 errors — full rebuild, not incremental

```bash
cd /root/github/euv-dev/euv
cargo clean -p euv-engine                  # 强制 rebuild 该 crate 全部 deps
cargo build -p euv-engine --target wasm32-unknown-unknown --release 2>&1 | tee /tmp/build.log
test "$(grep -c '^warning:' /tmp/build.log)" = "0" || { echo "WARN PRESENT"; exit 1; }
test "$(grep -c '^error' /tmp/build.log)"   = "0" || { echo "ERR PRESENT";  exit 1; }
```

**坑**: 不带 `cargo clean` 时,cargo incremental cache 会**重用上次的 deps 编译**。新加的 const 因为只有 docstring 没引用 → 看不到 `never used` 警告。**full rebuild 才是真相**。

**对下游 crate 同步编译**:
```bash
cargo build -p euv-example --target wasm32-unknown-unknown --release 2>&1 | tee /tmp/example-build.log
```

下游 0 errors 才能保证新 API 没破坏现有调用。

## 2. const / API 增删的「用到 vs 未用」自检

新加 const 后,**先 grep 确认下游真的能消费**,否则被 Rust 编译器标 `never used`:

```bash
# 1. 我新加的 const 列表(看 const.rs 末尾)
git diff upstream/master..HEAD -- engine/src/renderer/const.rs | grep "^+pub(crate) const"

# 2. 每个名字 grep impl.rs / enum.rs 是否被引用
for c in WEBGPU_NEW_CONST_1 WEBGPU_NEW_CONST_2 ...; do
  grep -r "\b$c\b" engine/src/renderer/{impl,enum,struct}.rs || echo "UNUSED: $c"
done

# 3. UNUSED → 删,不要 `#[allow(dead_code)]` 留尾
```

**反例**: PR #177 加 21 个 `WEBGPU_BUFFER_USAGE_*` / `WEBGPU_INDEX_FORMAT_*` / `WEBGPU_PROPERTY_*`,19 个没在 impl.rs 真用到 → 编译全标 `never used`。**只加真正用到的 const**,**文档化 future use** 也不留 — 这是 user 偏好("没有使用的代码导致的警告需要删除")。

## 3. 用 named const 替代裸数字

写 usage / size / format bitmask 时**永远用 named const 加法**,不要写裸 `23.0` 这种 magic number:

```rust
// ❌ 错的 — 谁知道 23 是哪几个 flag 相加?
&JsValue::from_f64(23.0)

// ✅ 对的 — 加法自解释,reviewer 一眼知道是哪些 flag
&JsValue::from_f64(
    WEBGPU_TEXTURE_USAGE_STORAGE_BINDING
        + WEBGPU_TEXTURE_USAGE_TEXTURE_BINDING
        + WEBGPU_TEXTURE_USAGE_COPY_SRC
        + WEBGPU_TEXTURE_USAGE_COPY_DST,
)
```

## 4. 现有 const 值正确性 sanity check

`engine/src/renderer/const.rs` 已存在的几个 const 是 **WRONG**(按 WebGPU spec):

| 当前值 | 名字 | spec 正确值 | 备注 |
|---|---|---|---|
| `8.0` | `WEBGPU_TEXTURE_USAGE_VERTEX` | 32 | 撞 `COPY_DST = 8.0`, 同名 numeric alias |
| `4.0` | `WEBGPU_TEXTURE_USAGE_INDEX` | 16 | 与 `COPY_SRC` 撞值 |
| `8.0` | `WEBGPU_TEXTURE_USAGE_TEXTURE_BINDING` | 8 | 与 `STORAGE_BINDING` 撞值(spec 区分,但实现上同数字) |

**Spec 参考**: https://www.w3.org/TR/webgpu/#buffer-usage
- BufferUsage: MAP_READ=1, MAP_WRITE=2, COPY_SRC=4, COPY_DST=8,
  INDEX=16, VERTEX=32, UNIFORM=64, STORAGE=128, INDIRECT=256, QUERY_RESOLVE=512
- TextureUsage: COPY_SRC=1, COPY_DST=2, SAMPLED=4, STORAGE=8, RENDER_ATTACHMENT=16,
  TEXTURE_BINDING=8

**新加 const 避免与现有错误值撞**(e.g. 不要新加 `WEBGPU_TEXTURE_USAGE_X = 8.0`,会与现存 `COPY_DST = 8.0` 编译冲突 `E0428 defined multiple times`)。

## 5. patch 工具的 fmt-fragility 陷阱

`cargo fmt --all` 后,文件里 const 块的空白可能被 rustfmt 重新调整。后续 `patch 工具` 的 `old_string` 匹配可能因为空白不同而 fail,错误信息:

> Could not find a match for old_string in the file
> Did you mean one of these sections: ...
> _warning: ... was modified since you last read it on disk

**修复**: 用 `execute_code` + Python 正则删除整个 const block(doc-comment + const 定义):

```python
import re
path = "/root/github/euv-dev/euv/engine/src/renderer/const.rs"
with open(path) as f: content = f.read()

unused_names = ["WEBGPU_FOO", "WEBGPU_BAR", ...]
lines = content.split("\n")
new_lines = []
skip_until = -1
for i, line in enumerate(lines):
    if i < skip_until: continue
    matched = any(re.match(rf"^\s*pub\(crate\) const {n}\b", line) for n in unused_names)
    if matched:
        # 删 const + 它前面的 /// 块 + 后面一个空行
        j = i - 1
        while j >= 0 and (lines[j].strip().startswith("///") or lines[j].strip() == ""):
            j -= 1
        skip_until = i + 2
    else:
        new_lines.append(line)
with open(path, "w") as f: f.write("\n".join(new_lines))
```

## 6. BindGroupEntry 等 enum 扩展的 conflict 检查

往已有 `enum` 加新 variant(如 `BindGroupEntry::StorageTexture`)前:

1. `grep -nE "impl EnumName \{|fn binding\(" engine/src/renderer/{impl,enum}.rs` — 找**已有同名方法**的 impl block
2. 不要在 enum.rs 内 `impl BindGroupEntry { pub fn binding() {...} }` 加新方法,**会和 impl.rs 里的同名 `pub(crate) fn binding()` 冲突**
3. 正确做法:改 impl.rs 里**已有**的 `pub(crate) fn binding()` 为 `pub fn binding()` + 加新 variant arm

## 7. 验证清单 (commit 前跑一遍)

```bash
# A. format
cargo fmt --all

# B. clean rebuild, 0 warnings
cargo clean -p euv-engine
cargo build -p euv-engine --target wasm32-unknown-unknown --release 2>&1 | tee /tmp/build.log
grep -c '^warning:' /tmp/build.log  # must be 0
grep -c '^error'    /tmp/build.log  # must be 0

# C. clippy 0 new warnings
cargo clippy -p euv-engine --target wasm32-unknown-unknown --all-targets --no-deps 2>&1 | tee /tmp/clippy.log
# 检查没有 NEW warning(diff upstream/master)

# D. 下游仍能 build
cargo build -p euv-example --target wasm32-unknown-unknown --release 2>&1 | tee /tmp/example-build.log
grep -c '^warning:' /tmp/example-build.log  # must be 0
grep -c '^error'    /tmp/example-build.log  # must be 0

# E. native tests
cargo test -p euv-engine --lib  # must be 0 failed

# F. const 全用到 vs 未用 列表
for c in $(git diff upstream/master..HEAD -- engine/src/renderer/const.rs | grep -oE 'WEBGPU_[A-Z_0-9]+' | sort -u); do
  grep -rln "\b$c\b" engine/src/renderer/{impl,enum,struct}.rs >/dev/null || echo "UNUSED: $c"
done
```

## 8. 实战案例:PR #177 (`feat/engine): expose advanced WebGPU APIs for complex game rendering`)

- Branch: `feat/engine-complex-rendering` (从干净 `upstream/master` checkout -b)
- 第一次 commit `5f3ac1c`: +931/-10,但有 21 个 `never used` warning → **被 user 抓回**
- Amend commit `f47b7ec`: +892/-10,0 warnings
- diff stat:
  - `engine/src/renderer/const.rs` +87 (净)
  - `engine/src/renderer/enum.rs` +162
  - `engine/src/renderer/impl.rs` +653/-3
- PR URL: https://github.com/euv-dev/euv/pull/177