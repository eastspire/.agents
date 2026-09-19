# Cross-repo workflow trigger: euv → euv-app 不可 0-secret

> 2026-09-13 实测 PR #228 (`8fca2b45`) + revert PR #230 (`8cbd5c1a`)。
> 本文件 = 平台限制说明 + 未来再做类似 trigger 的清单。

## 现象 / 决策点

euv (`euv-dev/euv`) 想在 master push + build 成功后,触发 euv-app (`eastspire/euv-app`) 的 `Build APK` workflow,以保证 APK 总是用最新 euv wasm 重打包。

预期方案 = 0-secret 纯云端 — 实际不可行,见下。

## 平台硬限制(2026-09 GitHub Actions 实测)

| 方案 | 跨 org 是否可用 | 备注 |
|---|---|---|
| `on: workflow_run: workflows: [Rust] types: [completed]` 在 euv-app 端监听 euv workflow run | **否** | `workflow_run` 是 org 内事件,**不跨 org** |
| 默认 `GITHUB_TOKEN` + `gh api POST /repos/{owner}/{repo}/dispatches` | **否** | default token scope 仅 `contents: read, packages: read`,无跨仓 `actions: write` |
| 默认 `GITHUB_TOKEN` + `gh api POST /repos/{owner}/{repo}/actions/workflows/{wf}/dispatches` | **否** | 同上 |
| PAT (`public_repo` scope) + dispatches API | **是** | 唯一云端方案, 但需要 user 在 euv 仓 Settings > Secrets 加 secret |
| GitHub App installed on both repos + euv 仓存 app private key | **是** | 不需要 PAT,但首次要 setup App(更适合长期 multi-repo 场景) |

**结论** = 跨 org trigger 必须有 token。

## 实测 PR #228 失败原因

PR #228 加了 `trigger-euv-app` job:
- `needs: build`
- `if: github.event_name == 'push' && github.ref_name == 'master' && needs.build.result == 'success'`
- `curl -X POST .../actions/workflows/build-apk.yml/dispatches` with `secrets.EUV_APP_DISPATCH_TOKEN`

PR 上 CI 跑通(trigger job 在无 secret 时静默 skip 不影响 merge),但**实际 euv master push 时这个 job 会一直 skip**。 user 拒绝提供 PAT,所以 PR #230 revert 撤销 #228。

## 未来再做类似 trigger 的清单

### 1. 决策前先回答

- 两个 repo **是否同 org**?同 org 可用 `workflow_run` + default `GITHUB_TOKEN`(0-secret)。异 org 必须 PAT / GitHub App。
- user 愿意提供 PAT / setup App 吗?不愿意 → **不要开 PR**;直接记到 skill 让 user 知道不可行。
- 不愿意 → 不做,或改方案:让 euv-app 监听 **webhook** / **schedule**(cron),自己轮询 euv release 决定何时 build。

### 2. 愿意做 → 实施模板

```yaml
trigger-downstream:
  needs: build
  if: github.event_name == 'push' && github.ref_name == 'master' && needs.build.result == 'success'
  runs-on: ubuntu-latest
  steps:
    - name: Trigger downstream via workflow_dispatch
      env:
        DOWNSTREAM_TOKEN: ${{ secrets.DOWNSTREAM_DISPATCH_TOKEN }}
      run: |
        if [ -z "$DOWNSTREAM_TOKEN" ]; then
          echo "⚠️ DOWNSTREAM_DISPATCH_TOKEN not configured; skipping"
          echo "Set secret on https://github.com/${{ github.repository }}/settings/secrets/actions"
          exit 0   # 静默 skip,不 fail pipeline
        fi
        http_code=$(curl -sS -o /tmp/dispatch-resp.txt -w '%{http_code}' \
          -X POST \
          -H "Authorization: token ${DOWNSTREAM_TOKEN}" \
          -H "Accept: application/vnd.github+json" \
          -H "Content-Type: application/json" \
          "https://api.github.com/repos/<owner>/<repo>/actions/workflows/<wf>.yml/dispatches" \
          -d "$(jq -nc --arg ref master '{ref: $ref}')")
        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
          echo "✅ downstream workflow_dispatch submitted"
        else
          echo "❌ dispatch failed (HTTP $http_code)"
          cat /tmp/dispatch-resp.txt
          exit 1
        fi
```

**关键**:
- `if` 内含 `needs.build.result == 'success'` + master push 才跑
- `if [ -z "$TOKEN" ]; then exit 0; fi` 让无 secret 时 PR 仍能 merge(避免卡 review)
- 用 `workflow_dispatch` 而非 `repository_dispatch`(后者要求下游声明 event type,改动面更大)
- `inputs` 字段必须在下游 workflow file 显式 declare 才能传 — 默认只传 `ref`,简单够用
- 把 `DOWNSTREAM_TOKEN` 加到 euv 仓 Settings > Secrets > Actions:**scope 必须足够跨仓 trigger**,classic PAT 用 `public_repo`,fine-grained 用 `Actions: Write` on downstream repo

### 3. Revert 模式

如果 PR 上了但 user 撤销,标准 revert:

```bash
cd ~/github/<owner>/<repo>
git checkout -b revert/<pr-branch-name> 8fca2b45  # 紧跟要 revert 的 commit SHA
git revert --no-edit 8fca2b45
git push -u origin revert/<pr-branch-name>
# 用 Python json.dumps 写 PR body(shell heredoc 转义会被 backtick 坑)
python3 -c 'import json; body=open("/tmp/pr-body.md").read(); payload=json.dumps({"title":"Revert \"<original-title>\"","head":"eastspire:revert/<pr-branch-name>","base":"master","body":body}); open("/tmp/p.json","w").write(payload)'
TOKEN=$GH_TOKEN curl -sS -X POST https://api.github.com/repos/<owner>/<repo>/pulls \
  -H "Authorization: token $TOKEN" -H 'Accept: application/vnd.github.v3+json' \
  -H 'Content-Type: application/json' -d @/tmp/p.json
# Wait CI, merge squash, delete branch
```

**坑**: shell heredoc 三重引号里含 backtick(`)会被 bash 当命令执行,导致 body 被截断。**始终**用 `python3 -c 'import json;...'` 把 body 写文件再 curl。

## References

- PR #228 (`8fca2b45`) + PR #230 (`8cbd5c1a`) — 完整 trigger + revert commit 链。
- Related: `minor-bump-ci-red-by-design.md`(同档 CI 参考,讲 euv 自家 pipeline 的设计内红)。
- Related: `euv-standards` §17(版本升级规则)。
