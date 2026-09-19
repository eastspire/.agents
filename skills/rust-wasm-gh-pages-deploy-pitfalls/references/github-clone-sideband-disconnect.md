# 本机 git clone/fetch 持续 sideband disconnect — 必须走 GitHub Git Data API

**症状(VM-24-7-opencloudos,2026-09-18 docs-pages/docs 重命名实测)**:
- `git clone https://github.com/<org>/<repo>.git` 在本机持续 `fetch-pack: unexpected disconnect while reading sideband packet`,exit code 124
- 即使 `--depth 50` 浅克隆同样失败
- 换 SSH (`git@github.com:...`) 同样 sideband 断
- `timeout N git clone` 触发 SIGTERM 后,git **自动清理**正在创建的目标目录(空中间态也清) — 表面看 "什么都没发生"

**根因**(多重叠加):
1. **GFW 对 GitHub sideband protocol 的丢包**:sideband 是 git 在 pack 传输时用的多路复用协议,把 pack data + progress + error 合并到一个 stderr 流。GFW 在 TLS 内识别 sideband 模式后倾向 reset 连接。
2. **HTTPS 与 SSH 都不通**:换 `--config http.postBuffer=...` / `http.version=HTTP/1.1` / `protocol.version=2` 都没用。
3. **git SIGTERM cleanup**:timeout 触发后 git 收到 SIGTERM,自动 delete `<target>` 目录(包括部分 cloned objects + 中间空目录)。看起来像 "从来没跑过"。
4. **空本地仓 + remote 不通 = 永远 orphan**:`git init` + `git remote add origin https://...` 成功后,后续 `git fetch` 仍然 sideband 断,本地仓永远没 origin/master ref,push 时 fatal "no upstream configured" / "non-fast-forward"。

**诊断三件套**(快速确认是不是这条坑):
```bash
# 1. 30s 短 fetch,看是否 sideband 断
cd ~/github/<org>/<repo>
timeout 30 git fetch --depth 1 origin master 2>&1 | tee /tmp/fetch.log
grep -E "sideband|fetch-pack" /tmp/fetch.log  # 命中 = 这条坑

# 2. 看本机出口 IP 是否在 GFW 影响范围
curl -s https://api.ipify.org && echo

# 3. 看 git 的 HTTPS proxy(可能配错)
git config --global --get http.proxy
git config --global --get https.proxy
env | grep -i proxy
```

**解法**:用 GitHub Contents / Git Data API 拿内容(完全绕过 git 协议):

```bash
# 1. 拿 tree(整个 master 树,递归)
TOKEN=$(grep -oP 'export GH_TOKEN="\K[^"]+' /root/.bashrc.d/gh_token.sh)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/<owner>/<repo>/git/trees/master?recursive=1" \
  > /tmp/tree.json

# 2. 拿到 blob 后逐个 GET 内容(每文件一次 API 调用)
python3 -c "
import json, urllib.request, os, base64, re
TOKEN = re.search(r'export GH_TOKEN=\"([^\"]+)\"', open('/root/.bashrc.d/gh_token.sh').read()).group(1)
d = json.load(open('/tmp/tree.json'))
for e in d['tree']:
    if e['type'] == 'blob' and e['path'].endswith(('.md', '.toml', '.json', '.rs', '.html', '.css')):
        req = urllib.request.Request(e['url'], headers={'Authorization': f'Bearer {TOKEN}'})
        with urllib.request.urlopen(req) as r:
            blob = json.load(r)
        content = base64.b64decode(blob['content']).decode('utf-8', errors='replace') if blob['encoding'] == 'base64' else blob['content']
        os.makedirs(os.path.dirname(e['path']) or '.', exist_ok=True)
        with open(e['path'], 'w') as f: f.write(content)
        print(f'wrote {e[\"path\"]}')
" 2>&1 | head -50

# 3. binary 大文件 / 图片不能这样拿,要单独走 raw.githubusercontent.com
```

**token 来源**:本机 `gh auth login` 没配,跑 `gh api` 会报 "To get started with GitHub CLI, please run: gh auth login" → **必须**用 `GH_TOKEN` env var,从 `/root/.bashrc.d/gh_token.sh` 里 source 出来。

**完整 pull-via-API 脚本**(扩展 `push-via-git-data-api.py` 为双向):

```python
# scripts/pull-via-git-data-api.py
# GET master HEAD sha → GET commit tree → recursive blob GET → 写文件
# 一次 pull 1000+ 文件的 API quota ~1000 calls(GH_TOKEN auth 5000/h 限额内)
```

**预防**(在受 GFW 影响环境):
1. **clone 前先 `curl -I https://github.com/<org>/<repo>`** 测连通性。如果 timeout,别浪费时间试 `git clone`。
2. **永远 background + 长 timeout**:`terminal(background=true, timeout=600)`,而不是 foreground 60s。foreground timeout SIGTERM 触发 git 自动 cleanup 空目录。
3. **对空本地仓不抱希望**:`git init` + `git remote add origin` 后没 origin/master ref,后续 push 失败 — 必须先 fetch 拿到 ref,而 fetch 又会卡。这条循环无解,只能走 API。
4. **GH_TOKEN 一定 env 配好**:API pull / push 全靠它。

**push 路线自检**(GFW 环境):
```bash
# 不要用 git push — 走 Git Data API
python3 ~/.hermes/skills/rust-wasm-gh-pages-deploy-pitfalls/scripts/push-via-git-data-api.py \
  --src-dir <local_path> --repo <owner>/<repo> --ref master --message "..."
```

**memory 关联**(已替换过时条目):memory 里旧的 "On this host, git clone from GitHub via SSH needs a long timeout" 是 2026-08 的经验,**已过时** — 长 timeout 也救不了,必须走 API。

**适用范围**:任何在本机(VM-24-7-opencloudos 等被 GFW 影响的国内 VM)需要 clone 或 fetch GitHub 仓库的场景。`fetch-pack: unexpected disconnect while reading sideband packet` 是 GFW sideband 干扰的 signature 错误。SSH 同样会卡,不是 SSH key 问题。