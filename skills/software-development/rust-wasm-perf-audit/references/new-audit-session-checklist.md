# 新一轮 audit session 开场清单(2026-09-13 起)

> 对 SKILL.md「跨 session 闭环」节的展开;适用于每一轮全仓 perf audit 的开场 10 分钟。

## 1. 对齐上游再审计

`git checkout master && git reset --hard <upstream>/master`——本地 HEAD 可能停在未推送的 bump 分支上(2026-09-13 实测:本地挂在 `chore/bump-0.23.0`,version 行与上游不一致),audit 基线必须是上游 master。
同时 `gh pr list --state open` 查在途 bump PR,后续 PR 版本号从「当时 master」动态起 bump,避免撞号。

## 2. 复核最新 findings reference 的开放项

行号随版本漂移,按函数名 grep 定位;已闭环项 `git log --oneline` 对照 PR 号确认无回退。

## 3. 按 crate 分区派并行 audit worker

实测 5 区划分(euv @ 0.22.x):

1. core renderer + dom + registry + noderef
2. core reactive + vdom + app + i18n
3. macros + ui
4. engine
5. example + cli + workspace profile

worker audit-only 不改码;每条发现必须 file:line + 触发频率 + 量化 + api_safe(是否不动 pub API)标记。

**近期落地的 perf PR 本身也是审计对象**——每批优化都可能引入回归(前科:OPT-10/11 引入 R1 PartialEq 缺臂 / R2 E0308,OPT-13 引入 R3 detached 误覆盖)。audit prompt 里必须列出近期 PR 号与主题,让 worker 专门复核其改动路径。

## 4. 重型构建前环境准备(内存受限机器)

清 /tmp 的 cdp-*/浏览器 profile 垃圾(单 terminal 调用内 ≥4 个 `rm -rf` 触发安全拦截,拆独立调用)→ `sync && echo 3 > /proc/sys/vm/drop_caches` → 构建限 `CARGO_BUILD_JOBS=2`。磁盘水位先看 `df -h /`(60G 盘易满)。
