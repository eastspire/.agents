---
name: mobile-web-debugging
description: 'Use when 移动端浏览器/WebView 渲染问题：safe-area 空白、刘海遮挡、不贴边、视口不匹配、用户截图与本地复现结果不一致。Includes viewport-match repro workflow (extract dims from screenshot → cross-check user build → multi-viewport sweep before declaring "no bug").'
---

# Mobile WebView / Mobile Browser Rendering Debugging

诊断移动端浏览器（含飞书/微信等 in-app WebView）的布局问题。这类问题的核心难点：**headless Chrome 和桌面 DevTools 设备仿真里 `env(safe-area-inset-*)` 恒为 0，无法在本地复现真机的 safe-area 场景**。

触发词：移动端空白、navbar 顶部空白、safe-area、viewport-fit、刘海屏、沉浸式、WebView 适配、手机浏览器布局不对。

## 核心事实（先读再动手）

1. **`env(safe-area-inset-*)` 在 headless / 桌面仿真中永远返回 0**。任何依赖 env() 的 bug 在本地无法复现 —— 本地"没问题"不代表真机没问题。
2. **`viewport-fit=cover` 是 iOS 全屏渲染的唯一开关**：有它 → 页面延伸到状态栏/刘海下方，env() 返回 47~59px；没有它 → 系统 letterbox，env() 恒 0。**但部分 Android WebView（尤其国产 X5/UC 内核）可能无视 viewport-fit 强制沉浸式**，删 cover 不一定能治好 Android。
3. **in-app browser（飞书/微信）缓存 HTML 非常激进**，超过 HTTP cache-control。部署修复后让用户复测必须加 cache-buster query：`https://site/?v=N`。
4. **像素取证无法区分两种状态**:"系统 letterbox(页面从状态栏下方开始)"和"cover + env padding(页面在状态栏下,内容被 padding 推下去)"在截图里像素几乎一样 —— 两者内容都出现在 y ≈ 状态栏高度 + padding 处。**不要从截图像素宣布"已修复"** —— 只有运行时数值(env() 实际值)能定论。
5. **headless 下无法验证 env()-driven 修复时,改用"emitted CSS 字节级对比"**(2026-08-30 euv-docs PR #13 总结):把目标站点和已知正确的参考站点(euv example、其他项目等)用 Playwright 加载,遍历 `document.styleSheets` 收集关心的 class 的 `cssRules[i].cssText`,逐 class 比对 —— 因为 CSS 是 wasm/构建产物,emitted 字符串一致 ⇒ runtime 行为一致,即使 env() 在 headless 永远 0 也能验证。可执行脚本见 `scripts/css-byte-diff.py`。**这是当前唯一可靠的"本地验证 safe-area 类修复"路径**。

## 诊断工作流

### 1. 先排除缓存

部署修复后用户仍看到旧布局 → 第一嫌疑是 webview 缓存。给用户带 query 的链接复测:`?v=2`、`?v=3`…

### 2. 拿真机运行时数据(诊断页模式)

不要猜。做一个自包含 HTML 诊断页(模板见 `templates/env-diag.html`),用 hyperlane-upload skill 传到 ltpp.vip 拿公网链接,让用户在有问题的设备/浏览器上打开并截图发回。诊断页显示:

- `env(safe-area-inset-top)` 计算后的实际 px 值(用临时 div + getComputedStyle 探测)
- `innerWidth/innerHeight`、`visualViewport`、`screen` 尺寸、`devicePixelRatio`
- 当前 viewport meta 内容
- UA 字符串(判断是 Feishu/WeChat/Chrome/Safari 哪个壳)

一张截图 = 完整地面真相。

### 3. 根因分类

| env 值 | 结论 |
|---|---|
| 0px 且仍有空白 | 与 safe-area 无关 → 查普通布局(margin/height:100%/sticky) |
| >0 且页面有 viewport-fit=cover | cover 生效中 → 删 cover 或正确处理 padding |
| >0 且页面无 cover | 宿主 WebView 强制沉浸式 → CSS 必须自己处理 env()(padding 给内容、背景延伸策略要想清楚) |

### 4. 字节级 CSS 对比(headless env=0 场景的唯一验证手段)

**触发条件**:有"参考站点"(euv example、reference impl) + 目标站点,需要在 merge 前本地确认两边 emitted CSS 一致。

```bash
python3 scripts/css-byte-diff.py \
  --reference https://example.com/ \
  --target     http://127.0.0.1:18702/ \
  --target-route '#/zh/' \
  --classes c_mobile_header c_mobile_nav_drawer c_app_main c_mobile_main \
  --viewport 390x844 --is-mobile \
  --out /tmp/css_diff.json
```

脚本输出 JSON:每个 class 一对 `{reference: "...", target: "..."}`,identical=true/false,首个差异位置 + 差异前后 30 字符。**identical=true ⇒ runtime 行为等价**(env() 永远 0 的局限被绕开,因为差异在 CSS 字符串层而非渲染层)。`cssText` 可能含 media query 或嵌套 selector;脚本只挑 `selectorText === .{class}` 的规则,跳过 `.class.other` / `.class:hover` / `@media` 嵌套 —— 这是故意的,只想确认"裸 class 定义"是否对齐。

如果对比发现 `c_mobile_header` 的 target 缺 `var(--euv-mobile-safe-top, 0px)` 模式,根因通常是上游 dep 版本漂移(坑见 `rust-wasm-gh-pages-deploy-pitfalls` §euv-ui pin drift)。

### 4. 修复设计原则（本用户偏好，euv PR #53-59 教训）

- 用户截图默认 light mode，navbar bg = 页面 bg 同色。**任何不可见的 padding 都会被感知为"顶部空白"**。
- 不要用 border-top/box-shadow 给 safe-area 造假边界 —— 用户会立刻发现 navbar 没真的在屏幕顶。
- 把 safe-area 条带涂成对比色（如黑）有风险：状态栏时钟文字颜色由宿主 app 控制，可能不可读。
- 确定性最强的方案是让系统 letterbox（删 viewport-fit=cover），但前提是宿主 WebView 尊重它（见核心事实 #2）。

## 无视觉模型时的截图分析（fallback）

`vision_analyze` 不可用（无 provider）时，用 PIL 做数值分析：

```python
from PIL import Image
im = Image.open(path).convert('L')
w, h = im.size
# 1) 行扫描找内容带：每行暗像素计数，band = 连续 >2 的行
# 2) 把区域渲染成 ASCII art 直接"看"布局：
crop = im.crop((0, 0, w, 400)).resize((120, 22))
chars = ' .:-=+*#%@'
for y in range(crop.height):
    print(''.join(chars[min(crop.getpixel((x, y)) * 10 // 256, 9)] for x in range(crop.width)))
```

ASCII art 能看清布局结构（边框线 = 全宽暗行、logo = 实心方块、文字带），但**记住核心事实 #4**：布局"看起来对"不等于修复生效，数值才能定论。

## 常见坑

- ❌ 本地 headless 复测 env() 相关 bug → 恒 0，白测。
- ❌ 改 `example/www/index.html` 这类构建产物 → 先确认它是不是模板生成的（git check-ignore + 找生成它的代码）。
- ❌ 部署后让用户直接刷新复测 → in-app browser 缓存会拿旧 HTML，必须 cache-buster。
- ❌ 从单张截图推断修复生效 → letterbox 和 env-padding 像素不可区分，要诊断页数值。
- ❌ **用桌面 headless viewport 复现用户的移动端 bug 后宣布"未复现"** → 移动端视口（innerWidth/innerHeight）、DPR、user agent、滚动容器高度、字体度量常常是 bug 触发的关键维度。用户的截图就是 ground truth——先量截图里的视口+关键元素的 px 尺寸，再用相同 `--window-size` 的 chrome 跑 headless。如果用户说"iPhone 上 8 个 row 顺序错乱"，用 375×667 重测；用 1280×900 测了 7 个场景全 PASS 不构成"无 bug"判定。**至少覆盖：截图测出的视口、桌面 ≥1024、≥2 个中间宽度**。参考脚本 `scripts/multi-viewport-sweep.py`。
- ❌ **断言"无 bug"前没核对用户测的 build** → euv / wasm-pack / GitHub Pages / Tauri WebView 这条链路上,**`www/pkg/` 可能是旧构建**（路由 `/virtual-list` 没注册就跳 404 → 首页，看起来"列表错乱"；或 `item_height` 被本地改过但用户看到的 44 vs 截图里的 170+ 不一致）。第一动作：`git show master:Cargo.toml | grep '^version'` + `ls -la example/www/pkg/` + 看 `pkg/euv_bg.wasm` 的 mtime。如果用户截图里的元素间距 ≠ 源码常量(如 euv example `VIRTUAL_LIST_DEMO_ITEM_HEIGHT = 44` 而截图 row ~170px)，**用户测的根本不是当前 build**——让他跑 `wasm-pack build --target web --out-dir www/pkg` 强刷而不是改源码。

## iOS Safari `<div>` + 委托 `onclick` 在滚动/fixed 容器内 silently dead（2026-09-14 PR #231/PR #232 经验）

iOS WebKit 把 tap 误判为"开始滚动"→ 直接 suppress synthetic click，所以 `euv` 的 `Registry::delegation("click")` 监听 window 但 iOS 根本不派发 click。`euv_button` 是真 `<button>` 不受影响。修复 = 给 clickable-`<div>` 类加 `touch-action: manipulation` + `user-select: none` (+ `-webkit-` 前缀)。6 个 affected classes（已合并到 `euv-standards` §12 坑表）：`c_tab_item_active` / `c_tab_item_inactive` / `c_modal_overlay` / `c_vconsole_overlay` / `c_euv_drawer_overlay` / `c_mobile_overlay`。

**用户报告"修了但还坏"时，不要假设 user 错了，用 CDP 验证 fix 真的进了 production wasm：**

```bash
# 1) 启动 headless chrome 模拟 iPhone 视口 + iOS UA + touch emulation
chromium --headless=new --no-sandbox --disable-gpu \
  --window-size=390,844 \
  --remote-debugging-port=9222 --remote-allow-origins=* \
  --user-agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1' \
  about:blank &
sleep 3

# 2) 用 Python + websocket-client 直连 CDP（不要用 browser-use skill daemon，会卡）
python3 - <<'PY'
import json, urllib.request, websocket, time
def get_tabs(): return json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
ws = websocket.create_connection(get_tabs()[0]['webSocketDebuggerUrl'], timeout=30)
mid = [0]
def cmd(m, p=None):
    mid[0] += 1; ws.send(json.dumps({'id':mid[0],'method':m,'params':p or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get('id') == mid[0]: return msg
def ev(e): return cmd('Runtime.evaluate', {'expression': e, 'returnByValue': True})['result']['result'].get('value')

# 3) 必须先 enable device metrics + touch emulation，否则 dispatchTouchEvent 被忽略
cmd('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 3, 'mobile': True})
cmd('Emulation.setTouchEmulationEnabled', {'enabled': True, 'maxTouchPoints': 1})

# 4) navigate to page, wait for wasm init
cmd('Page.navigate', {'url': 'https://ltpp.vip/github/pages/euv-dev/euv/#/conditional'})
time.sleep(6)

# 5) 验证 CSS 真的生效（如果 touchAction 不是 manipulation 说明 fix 没 deploy）
print(ev('''
const el = document.querySelector('.c_tab_item_inactive');
const cs = window.getComputedStyle(el);
JSON.stringify({touchAction: cs.touchAction, userSelect: cs.userSelect});
'''))')  # → {"touchAction":"manipulation","userSelect":"none"}  = fix 生效

# 6) 关键: iOS tap 必须用 dispatchTouchEvent，不能用 dispatchMouseEvent（那是 desktop 路径）
# 取 inactive tab 中心坐标
info = json.loads(ev('''
const t = document.querySelector('.c_tab_item_inactive');
const r = t.getBoundingClientRect();
JSON.stringify({x: r.x + r.width/2, y: r.y + r.height/2, text: t.textContent.trim()});
'''))
# touchStart → 50ms → touchEnd（不能 sleep 太短；iOS 内部需要 gesture disambiguation 时间）
cx, cy = int(info['x']), int(info['y'])
cmd('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': cx, 'y': cy, 'id': 1, 'radiusX': 10, 'radiusY': 10, 'force': 0.5}]})
time.sleep(0.08)
cmd('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
time.sleep(0.5)
# active tab 应该变成被点击的那个
active = ev('document.querySelector(".c_tab_item_active")?.textContent.trim()')
print('active after touch:', active, 'expected:', info['text'])
PY
```

**判定**：

- `touchAction != "manipulation"` → fix 没 deploy，deploy 链断了。检查 ltpp mirror sync + 仓库 wasm mtime + `wasm-pack build` 是否漏跑（参考 `rust-wasm-gh-pages-deploy-pitfalls`）。
- `touchAction == "manipulation"` 但 touch event 后 active tab 没切换 → fix 不够（罕见；考虑改用 `touch-action: none` 完全禁 gesture，或 `<div>` 改 `<button>`）。
- `touchAction == "manipulation"` 且 touch event 后 active tab 切换 → fix 在生产实际工作，**用户侧的"还坏"是 CDN/浏览器缓存**（ltpp reference `static-site-deploy-verification` 明确 iOS Safari / Chinese Android 浏览器忽略 `cache-control: no-store`）。让用户清缓存或加 `?v=N` cache-buster 复测，**不要继续改代码**。

**完整复用脚本**（已在本会话验证可用，输出 6 hop 报告：touchAction/userSelect/deploy sha/active-before/active-after/md5）→ `scripts/ios-touch-action-verify.py`。

## 文件

- `templates/env-diag.html` — 自包含诊断页模板，可直接用 hyperlane-upload 传 ltpp.vip 后发给用户。
