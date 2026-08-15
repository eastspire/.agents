---
name: docs-rs-api-fetcher
description: 实地查询 docs.rs 和 crates.io 的 Python 脚本(已在 rust-crate-use skill 的 scripts/ 下)。当需要确认某个 crate 的真实 API、模块路径、版本号、feature flag 时,必须用这个脚本查,**禁止基于训练数据记忆推断**。
---

# docs.rs / crates.io 实地查询脚本

## 脚本位置
`~/.agents/skills/rust-crate-use/scripts/fetch_docs_rs.py`(同时存在 `~/.hermes/skills/rust-crate-use/scripts/`,两边已同步)

## 核心功能
- **crates.io API**:`https://crates.io/api/v1/crates/<name>` 查最新版本、下载量、更新时间
- **docs.rs API**:`https://docs.rs/<name>/<version>/<path>.json` 查模块树 / API 签名
- **占位页检测**:docs.rs 对不存在的版本**返回 200 + 占位页**(嵌入 JSON 把 version 字段归零为 `"0.0.0"`),不是 404。脚本通过**对比嵌入 JSON 的 `name/version` 与 URL 传入的 `crate/version`** 来检测占位页

## 用法

### 基础:查 crate 整体
```bash
python3 fetch_docs_rs.py <crate-name>
# 例:python3 fetch_docs_rs.py serde
```

### 指定版本
```bash
python3 fetch_docs_rs.py <crate-name> --version <version>
# 例:python3 fetch_docs_rs.py serde --version 1.0.0
```

### 只查 crates.io(不查 docs.rs)
```bash
python3 fetch_docs_rs.py <crate-name> --crate-info-only
# 适合:只需要版本号/下载量,不需要 API 细节
```

### 自定义输出文件
```bash
python3 fetch_docs_rs.py <crate-name> --output /tmp/result.json
# 默认输出到当前目录的 docs_rs_<crate>.json
```

## 输出 JSON 结构

### 成功 + 真版本
```json
{
  "crate_info": {"name": "serde", "max_version": "1.0.219", "downloads": ..., "updated_at": "..."},
  "docs_rs": {
    "name": "serde",       // URL 传入的名字
    "version": "1.0.0",    // URL 传入的版本
    "modules": [...]       // 解析的模块树
  },
  "warnings": [],          // 软警告(继续,exit 0)
  "error": null            // 硬错误(null 表示无错误)
}
```

### 失败场景
| 场景 | 行为 | exit |
|------|------|------|
| 真实 crate,真实版本 | 返回元信息 + modules | 0 |
| 真实 crate,假版本 | 识别占位页 → 写入 `warnings` | 0 |
| 老版本无构建 | docs.rs 真 404 → 写入 `warnings` | 0 |
| 不存在 crate | 硬错误,`error` 字段非空 | 2 |
| 仅元信息 (`--crate-info-only`) | 跳过 docs.rs | 0 |

## 关键设计决策
- **软警告 vs 硬错误**:`warnings` 字段 = 软警告(继续运行,exit 0);`error` 字段 = 硬错误(中断,exit 2)
- **四级网络错误捕获**:`urllib.error.HTTPError` / `URLError` / `OSError` / `Exception` 全覆盖,脚本不崩
- **占位页陷阱**:docs.rs 对不存在的版本**返回 200 + 占位页**(URL 路径里的 `version` 在返回的 HTML 里被改成 `"0.0.0"`),不能靠 HTTP 状态码判断,要靠对比嵌入 JSON 的 `name/version` 字段
- **离线判断**:用 `urllib.request.urlopen(timeout=10)` 而不是 requests(无第三方依赖)

## 配合 SKILL 使用
1. `skill_view('rust-crate-use')` 加载 skill
2. 跑这个脚本实地查
3. 解析输出的 JSON 拿真实 API
4. **不**根据脚本输出以外的任何信息(训练数据、记忆、其他 skill)推断 API

## 易踩的坑
1. **crates.io API 用 GET 直接拿 JSON,不需要鉴权**;但加 `User-Agent` header 是好习惯
2. **docs.rs 对不存在路径会返回 HTML 而非 JSON**,JSON 解析前要先 `Content-Type` 头判断
3. **版本字符串规范化**:`1.0.0` 和 `1.0` 在 URL 里等价,但在 JSON 里是不同字符串
4. **超时**:`urlopen` 一定要 `timeout=10`,否则 hang 死会拖慢 agent
