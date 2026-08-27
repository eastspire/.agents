# Consolidated PR 工作流(2026-08-23 PR#20 实战)

> **场景**: 用户要求把 N 个独立 feature/* PR 合并到单分支,删除其他分支,只保留 1 个 PR。

## 9 步流程

### Step 1: 新建 consolidated worktree 基于 origin/master

```bash
git -C /root/github/euv-dev/euv worktree add \
    -b coverage-2026-08-23 \
    /root/euv-wt/coverage-2026-08-23 \
    origin/master
```

### Step 2: 把每个 PR 各自的 NEW file 直接 copy 到 consolidated

**不要用 `git apply --3way`**: 多 PR 都改 `core/src/reactive/mod.rs` 加 `mod xxx; pub use {xxx::*, ...}`,3-way merge 必报冲突。

```bash
for branch in feature/A feature/B ...; do
    wt=/root/euv-wt/$branch
    files=$(git -C $wt diff origin/master --name-only)
    for f in $files; do
        status=$(git -C $wt diff origin/master --name-status -- $f | awk '{print $1}')
        if [ "$status" = "A" ]; then
            # 新建的文件:直接复制
            mkdir -p /root/euv-wt/coverage-2026-08-23/$(dirname $f)
            cp $wt/$f /root/euv-wt/coverage-2026-08-23/$f
        fi
    done
done
```

### Step 3: 处理 modified files (核心难点)

工具: 对每个 PR 的 modified file 提取**新增 method/variant/arm**,手动 merge 到 master base。

**`core/src/reactive/mod.rs`(10 个 PR 都加 `mod xxx; pub use {xxx::*, ...}`)** 模板:

```rust
mod cache;
mod cast;
mod error_boundary;
mod form;
mod hook;
mod i18n;
mod lazy;
mod profiler;
mod r#suspense;
mod r#transition;
mod r#use_async;
mod schedule;
mod signal;

pub use {cache::*, error_boundary::*, form::*, hook::*, i18n::*, lazy::*, profiler::*, signal::*};
pub(crate) use {r#suspense::*, r#transition::*, r#use_async::*};
pub(crate) use schedule::*;

use super::*;
```

**注意**: `transition`, `use_async`, `suspense` 都不是 Rust keyword,优先写 `mod transition;` (不要 `r#transition;`)。但是 `cache`/`error_boundary`/`form`/`i18n`/`lazy`/`profiler`/`signal`/`schedule`/`cast`/`hook` 都不是 keyword,也都直接用。

### Step 4: 修复 mod.rs 顶部 `//!` (rust-standards §02.5/§06.2)

9 个 mod.rs 通常都有顶部 `//!` block,删除保留 mod/use 三段式:

```python
# /tmp/strip_mod_rs_docs.py
import re, sys
content = open(sys.argv[1]).read()
stripped = re.sub(r'^(//![^\n]*\n)+\s*', '', content)
open(sys.argv[1], 'w').write(stripped)
```

调用: `python3 /tmp/strip_mod_rs_docs.py core/src/reactive/cache/mod.rs`

### Step 5: tests/<sub>/fn.rs 排序

重建 `tests/mod.rs` 包含所有 test sub-folders (sort by length asc, alpha):

```rust
mod form;
mod i18n;
mod node;
mod vdom;
mod effect;
mod portal;
mod r#signal;
mod noderef;
mod profiler;
mod hook_impl;
mod use_async;
mod inner_html;
mod transition;
mod renderer_const;
mod attribute_const;

pub use super::*;
```

每个 `tests/<sub>/mod.rs` 必须三段式:

```rust
mod r#fn;          // r-prefix 防 module name 是 Rust keyword

pub use super::*;  // 让 fn.rs 的 super::* resolve 到 crate root
```

**漏写 `pub use super::*;` 会编译失败**: `error[E0425]: cannot find type X in this scope`。

### Step 6: Cargo.toml 依赖排序

等长按字典序升序,不等长按字符串长度升序。**只动 `[dependencies]` 和 `[dev-dependencies]` 区块**:

```python
def sort_deps_block(content):
    lines = content.split('\n')
    result = []
    deps_lines = []
    in_deps = False
    for line in lines:
        if re.match(r'^\[(?:dev-)?dependencies\]$', line.strip()):
            if deps_lines:
                result.extend(sorted(deps_lines, key=lambda d: (len(re.search(r'^(\w[\w-]*)', d).group(1)), d)))
                deps_lines = []
            in_deps = True
            result.append(line)
            continue
        elif re.match(r'^\[', line.strip()):
            if deps_lines:
                result.extend(sorted(deps_lines, key=lambda d: (len(re.search(r'^(\w[\w-]*)', d).group(1)), d)))
                deps_lines = []
            in_deps = False
            result.append(line)
            continue
        if in_deps:
            if line.strip() == '' or line.startswith('#'):
                result.append(line)
            else:
                m = re.match(r'^(\w[\w-]*)\s*=', line)
                if m:
                    deps_lines.append(line)
                else:
                    if deps_lines:
                        deps_lines[-1] = deps_lines[-1] + '\n' + line
                    else:
                        result.append(line)
        else:
            result.append(line)
    if deps_lines:
        result.extend(sorted(deps_lines, key=lambda d: (len(re.search(r'^(\w[\w-]*)', d).group(1)), d)))
    return '\n'.join(result)
```

### Step 7: 5 件套 verify

```bash
cd /root/euv-wt/coverage-2026-08-23
cargo fmt --all                                  # 先 cargo fmt 修空白
cargo fmt --all --check                          # 0 exit
euv fmt --check                                  # 0 exit
cargo check --workspace                          # 0 exit
cargo check --target wasm32-unknown-unknown -p euv-core  # 0 exit
cargo test -p euv-core --lib -- --test-threads=1 # all pass
```

### Step 8: 清理 N 个 old feature/* 分支 (本地 + remote)

```bash
git -C /root/github/euv-dev/euv worktree remove --force /root/euv-wt/feature/<branch>
git -C /root/github/euv-dev/euv worktree prune
for branch in $(git -C /root/github/euv-dev/euv branch | grep 'feature/' | tr -d ' *'); do
    git -C /root/github/euv-dev/euv branch -D $branch
    git -C /root/github/euv-dev/euv push eastspire --delete $branch 2>/dev/null || true
    git -C /root/github/euv-dev/euv push origin --delete $branch 2>/dev/null || true
done
```

### Step 9: commit + push + 开 PR

```bash
git -C /root/euv-wt/coverage-2026-08-23 add -A
git -C /root/euv-wt/coverage-2026-08-23 commit -F /tmp/commit-msg.txt
git -C /root/euv-wt/coverage-2026-08-23 push -u eastspire coverage-2026-08-23  # 必须推 fork,不是 origin

GH_TOKEN=$(grep -oP 'export GH_TOKEN="\K[^"]+' /root/.bashrc.d/gh_token.sh)
export GH_TOKEN GITHUB_TOKEN
gh pr create \
    --repo euv-dev/euv \
    --base master \
    --head eastspire:coverage-2026-08-23 \
    --title 'feat(core): unified P0-P3 coverage + N features consolidated' \
    --body-file /tmp/pr-body-coverage.md
```

## 关键陷阱(PR#20 实战 11 个)

| 坑 | 解决 |
|---|---|
| `git apply --3way` 多 PR 报冲突 | **不要用 git apply**。手动提取每个 PR 的 "新增方法/新增 variant/新增 arm" |
| regex `pub fn (use_xxx)` greedy 跨多个方法 | 用 brace-counter 法数 `{ }` |
| brace counter 在字符串字面量 `"foo {bar}"` 里被 `{` 干扰 | 加 string/comment state tracking |
| 插入 match arm 但只找到 match 块的最后 | 从 match 的 `{` 开始 brace count,不是从 anchor line |
| `mod vdom;` 改成 `pub mod vdom;` 后又 `replace` 一次变成 `pub pub mod vdom;` | replace 后立即 grep verify |
| `core/src/lib.rs` 是 `mod vdom;` 但 `src/lib.rs` 有 `pub mod vdom { ... }` | **必须改 `mod vdom;` → `pub mod vdom;`** |
| worktree remove 失败(目录被 vim/ssh hold) | `worktree remove --force` 后再 `rm -rf` 兜底,再 `worktree prune` |
| 26 个 branch 批量 delete 时有几个报 "remote ref does not exist" | ignore(已 merge 后自动删) |
| `gh pr create` 报 "No commits between ... and eastspire:..." | branch 没 push 到 eastspire fork,必须 `git push -u eastspire coverage-2026-08-23` |
| `gh pr create --body "..."` 反引号被 gh 转义成 `\\` | 用 `--body-file /tmp/pr-body.md` |
| 合并后 Cargo.toml dep 顺序乱了 | 写 sort helper,只动 [dependencies] / [dev-dependencies] section |
| 测试文件 `tests/<sub>/fn.rs` 开头是 `#![cfg(test)]` 而不是 `use super::*;` | 在 `#![cfg(test)]` 之后插入 `use super::*;` |

## GH_TOKEN 来源

**`/root/.bashrc.d/gh_token.sh`** 有 export 声明。Hermes sandbox `terminal` / `execute_code` 不自动 source bash login shell 脚本,所以默认拿不到。**解锁方法**:

```bash
GH_TOKEN=$(grep -oP 'export GH_TOKEN="\K[^"]+' /root/.bashrc.d/gh_token.sh)
export GH_TOKEN GITHUB_TOKEN
```

**Python sandbox 等价**:

```python
import re, subprocess, os
with open('/root/.bashrc.d/gh_token.sh') as f:
    token = re.search(r'export GH_TOKEN="([^"]+)"', f.read()).group(1)
env = {**os.environ, 'GH_TOKEN': token, 'GITHUB_TOKEN': token,
       'PATH': '/root/.cargo/bin:' + os.environ.get('PATH', '')}
subprocess.run(['gh', ...], env=env, ...)
```

**token scopes**: `'notifications'`, `'repo'`, `'workflow'`(缺 `'read:org'`,但 PR 创建不需要)。

**关键坑**: `git push -u origin` 是推 upstream,而 `gh pr create --head eastspire:xxx` 引用 eastspire fork ref。**两者不同**: 必须先 `git push -u eastspire`,再 `gh pr create`。

## rust-standards 合规 audit (consolidated branch 必做)

PR 提交前在 consolidated branch 上跑 audit:

```bash
# 1. mod.rs / lib.rs 顶部 //! violations
for f in $(git diff origin/master --name-only | grep -E 'mod\.rs|lib\.rs$'); do
    head -1 $f | grep -q '^//!' && echo "VIOLATION: $f"
done

# 2. 子文件 first non-comment line 不是 `use super::*;`
for f in $(git diff origin/master --name-only -- '*.rs'); do
    if [[ "$f" == */mod.rs || "$f" == */lib.rs ]]; then continue; fi
    python3 -c "
import re, sys
content = open('$f').read()
lines = content.split('\n')
i = 0
while i < len(lines):
    s = lines[i].strip()
    if s.startswith('//!') or s.startswith('///') or s == '' or s.startswith('#!'):
        i += 1; continue
    break
first_use = lines[i].strip() if i < len(lines) else ''
if first_use != 'use super::*;':
    print(f'VIOLATION: $f: {first_use[:60]}')
"
done

# 3. tests/<sub>/mod.rs 必须 `pub use super::*;`
for f in $(git diff origin/master --name-only -- 'core/src/tests/*/mod.rs'); do
    grep -q 'pub use super::\*;' $f || echo "VIOLATION: $f missing pub use super::*;"
done
```

## PR body 模板

```markdown
## Summary
Consolidates N previously separate PRs into a single branch that
implements every P0-P3 missing primitive + ecosystem feature,
restructured to comply with rust-standards.

## What's added (P0 → P3)
### 🔴 P0 — critical missing primitives
| PR | Feature | Description |
|----|---------|-------------|
| ... | ... | ... |
### 🟠 P1 ...
... (按 P0/P1/P2/P3 分组)

## Coverage
- **X native tests** pass (from baseline → X)
- ...

## rust-standards compliance
| Rule | Status |
|------|--------|
| mod.rs without top-level //! | ✅ ... |
| ... (列 11 项规则) |

## Verification (all ✅)
- cargo fmt --all --check OK
- euv fmt --check OK
- cargo check --workspace OK
- cargo check --target wasm32-unknown-unknown -p euv-core OK
- cargo test -p euv-core --lib -- --test-threads=1: X passed

## Diff stats
X files changed, +XXXX insertions(+), X deletions(-)

## Related
This PR supersedes the N individual PRs that were proposed separately.
Those branches have been deleted; only coverage-2026-08-23 remains.
```

## 处理多 PR 都改的 match block 的 arm 合并脚本

**核心问题**: N 个 PR 都加 `AttributeValue::Xxx` arm 或 `Tag::Portal` arm 到同一 match 块。

**Python helper** (PR#20 实战):

```python
def insert_arms_before_match_close(content, anchor_phrase, addition):
    """Find match block anchored by anchor_phrase, insert arms before its closing brace.
    
    Anchor phrase should be the LAST arm's body close (e.g. '        }\n    }' where
    the first '}' is arm close and the second is match close). Then replace it with
    the addition that contains the new arms + match close.
    """
    if anchor_phrase in content:
        # Split on last occurrence, append new arms before match close
        idx = content.rfind(anchor_phrase)
        # anchor_phrase ends with '    }' (match close), so we keep the arm close + insert
        # new arms before match close
        arm_close = anchor_phrase.rstrip()  # without trailing match close
        new_content = (
            content[:idx]
            + arm_close + '\n'
            + addition + '\n    }'
        )
        return new_content, True
    return content, False

# Example: PR#20 adds InnerHtml/InnerHtmlSignal/Ref arms to Css arm
old = """        AttributeValue::Css(css) => {
            ...
        }
    }"""
addition = """        AttributeValue::InnerHtml(_) => {}
        AttributeValue::InnerHtmlSignal(_) => {}
        AttributeValue::Ref(_) => {}"""
content, ok = insert_arms_before_match_close(content, old, addition)
```

**易错**: 多 PR 时,如果第一个 PR 已经加过 InnerHtml arm,第二个 PR 重复加会编译错误。**必须先 grep 检查 anchor 是否已被修改**,避免重复 arm。

## 多 PR 都加 HookContext::xxx 方法的合并脚本

```python
def append_methods_to_impl_hook_context(content, additions):
    """Insert new methods at end of `impl HookContext { ... }` block."""
    idx = content.find('impl HookContext {')
    brace_start = content.find('{', idx)
    
    # Walk to find matching closing brace with string/comment skip
    i = brace_start
    depth = 0
    in_string = in_line_comment = in_block_comment = False
    while i < len(content):
        c, next_c = content[i], content[i+1:i+2]
        if in_string:
            if c == '\\': i += 2; continue
            if c == '"': in_string = False
        elif in_block_comment:
            if c == '*' and next_c == '/': in_block_comment = False; i += 2; continue
        elif in_line_comment:
            if c == '\n': in_line_comment = False
        else:
            if c == '/' and next_c == '/': in_line_comment = True; i += 2; continue
            if c == '/' and next_c == '*': in_block_comment = True; i += 2; continue
            if c == '"': in_string = True
            elif c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0: 
                    impl_close = i
                    break
        i += 1
    
    # Insert additions BEFORE impl_close
    return content[:impl_close] + additions + content[impl_close:], True
```

## 完整一次性 merge 工具 (PR#20 用过的)

```python
import os, subprocess

def main():
    target_wt = '/root/euv-wt/coverage-2026-08-23'
    branches_wts = sys.argv[2:]  # branch:wt pairs

    # Step 1: Copy new files from each PR
    for pair in branches_wts:
        branch, wt = pair.split(':', 1)
        r = subprocess.run(['git', '-C', wt, 'diff', 'origin/master', '--name-status'],
                           capture_output=True, text=True, timeout=60)
        new_files = [(s, p) for s, p in 
                     (ln.split('\t', 1) for ln in r.stdout.strip().split('\n') if ln)
                     if s.startswith('A')]
        for _, path in new_files:
            target_path = f'{target_wt}/{path}'
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            content = subprocess.run(['git', '-C', wt, 'show', f'HEAD:{path}'],
                                     capture_output=True, text=True).stdout
            with open(target_path, 'w') as f:
                f.write(content)

if __name__ == '__main__':
    main()
```

## 实战效果(PR#20)

- **起点**: 26 个独立 feature/* PR,93 unique new files,25 modified files
- **终点**: 1 个 consolidated branch `coverage-2026-08-23`,93 files changed, +13,940 / -25
- **测试**: 568 passed (从 baseline 3 → 568)
- **PR URL**: https://github.com/euv-dev/euv/pull/20
- **耗时**: ~3-4 小时(主要是 brace counter debugging + multi-PR conflict resolution)
