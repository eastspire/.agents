---
name: github-pat-scope-check
description: 调用 GitHub API 前快速核查当前 GH_TOKEN 拥有哪些 scope，避免 403 Permission Denied
category: devops
---

# GitHub PAT Scope 核查

## 适用场景
调用 `gh api` 或 `curl -H "Authorization: token $GH_TOKEN" https://api.github.com/...` 前，对「删除仓库」「建仓」「改可见性」等高权限操作，先确认 token 是否有对应 scope。

## 核查命令

```bash
# 1. 查看 token 自身的 metadata（HEAD 请求会返回所有 scope）
curl -sI -H "Authorization: token $GH_TOKEN" https://api.github.com/user \
  | grep -i '^x-oauth-scopes'
# 输出示例: X-OAuth-Scopes: repo, read:org

# 2. 验证 token 能否调用目标端点
curl -s -H "Authorization: token $GH_TOKEN" \
  https://api.github.com/repos/eastspire/<repo-name> | jq -r .full_name

# 3. 实际操作前 dry-run（无害 GET）
curl -sI -H "Authorization: token $GH_TOKEN" \
  -X DELETE https://api.github.com/repos/eastspire/<repo-name>
# 返回 403 + "Must have admin rights to Repository" = 缺 delete_repo scope
# 返回 401 = token 无效
# 返回 204 = 权限足够
```

## 常见 scope 对照
| 操作 | 所需 scope |
|---|---|
| 读 / clone 仓库 | `repo`（或 `public_repo` 公共仓库） |
| 改 README / 提交 | `repo` |
| 改仓库可见性 (private↔public) | `repo` |
| 删 issue / PR / comment | `repo` |
| **删除整个仓库** | `repo` + **`delete_repo`** ⭐ |
| 创建个人仓库 | `repo` |
| 创建组织仓库 | `repo` + `admin:org` |

## 已知缺 delete_repo 的处理
1. 提示用户手动到 https://github.com/{owner}/{repo}/settings 滚到 Danger Zone 删除
2. 或指导用户重新生成 classic PAT: https://github.com/settings/tokens → 勾选 `repo` + `delete_repo`
3. 替换 `~/.bashrc` / `~/.profile` 中的 `GH_TOKEN` 后 `source ~/.bashrc` 再重试

## Pitfall
- GitHub Apps 用的 `gh auth login` 走的 installation token 默认没有 `delete_repo`
- Fine-grained PAT (beta) 不支持 `delete_repo` scope，必须用 classic PAT
- 同一 token 在 `curl` 和 `gh` CLI 中显示的 scope 可能不同步（看 `gh auth status` 也要核对）
