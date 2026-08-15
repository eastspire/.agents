---
name: github-org-bulk-clone
description: 批量 clone GitHub 组织下所有仓库（含私有），使用 PAT token 鉴权，支持失败重试、跳过已存在、后台运行避免超时
when_to_use: 需要一次性 clone 某个 GitHub 用户/组织下所有仓库时
---

# GitHub 组织/账号批量 clone

## 前置条件
- PAT token 已存为环境变量：`GH_TOKEN` 或 `GITHUB_TOKEN`（从 `~/.bashrc` / `~/.profile` 读取）
- 工具：`git`、`curl`、`jq`、`xargs`

## 步骤

### 1. 验证 token + 获取用户身份
```bash
curl -s -H "Authorization: token $GH_TOKEN" https://api.github.com/user | jq -r '.login'
```

### 2. 列出用户所属所有组织
```bash
curl -s -H "Authorization: token $GH_TOKEN" https://api.github.com/user/orgs | jq -r '.[].login'
```

### 3. 对每个组织列出所有仓库（含私有）
```bash
curl -s -H "Authorization: token $GH_TOKEN" "https://api.github.com/orgs/<ORG>/repos?per_page=100&type=all" \
  | jq -r '.[] | "\(.name)|\(.private)"'
```
注意：`type=all` 才能包含私有仓库；`type=private` 仅返回私有；不传 `type` 默认公开+私有但行为可能变化。

### 4. 批量 clone 脚本模板
```bash
#!/bin/bash
set +e  # 不要因单个失败退出
ORG=$1
BASE="/workspace/orgs/$ORG"
mkdir -p "$BASE"
cd "$BASE"

# 用 jq 拼成 "name|clone_url" 列表
URLS=$(curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/orgs/$ORG/repos?per_page=100&type=all&page=1" \
  | jq -r '.[] | "\(.name) \(.clone_url)"')

while read -r name url; do
  if [ -d "$name" ]; then
    echo "SKIP: $name"
    continue
  fi
  for i in 1 2 3; do
    git clone --depth 1 "$url" && break
    echo "RETRY $i for $name"
    sleep 2
  done
done <<< "$URLS"
```

## 关键坑 & 解决方案

### HTTP/2 帧错误（`RPC failed; HTTP2 stream ... was not closed cleanly`）
**原因**：并行 clone 太多触发 GitHub 限流 / 网络栈 bug。
**解决**：
1. **改用串行**（不要 `xargs -P` 并行）
2. 设置 Git 缓冲与 HTTP/1.1：
   ```bash
   git config --global http.version HTTP/1.1
   git config --global http.postBuffer 524288000
   git config --global core.parallelism 1
   ```
3. 每个 clone 之间 `sleep 2`

### 大批量 clone 超时（5 分钟任务超时）
**解决**：用 `nohup ... &` 后台运行 + 重定向日志：
```bash
nohup bash /workspace/clone.sh > /workspace/clone.log 2>&1 &
echo $! > /workspace/clone.pid
# 查进度：
tail -f /workspace/clone.log
kill -0 $(cat /workspace/clone.pid) 2>/dev/null && echo "运行中" || echo "已结束"
```

### API 分页
GitHub 单页最多 100 条，超过需 `&page=2`、`page=3` 循环拉取直到返回空数组。

### 权限
- 私有仓库需要 token 有 `repo` scope
- 组织仓库需要用户是该组织成员且 token 有相应权限

## 验证清单
- [ ] `curl -I https://api.github.com/user -H "Authorization: token $GH_TOKEN"` 返回 200
- [ ] 列出仓库数与 GitHub 网页端一致
- [ ] clone.log 无 `fatal` 错误
- [ ] 目录数 = 预期仓库数（含 .git 的目录）
