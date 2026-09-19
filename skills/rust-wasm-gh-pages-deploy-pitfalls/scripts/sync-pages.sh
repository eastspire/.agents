#!/usr/bin/env bash
# 仿照 euv 仓库 .github/workflows/pages.yml 的 Sync Pages 步骤:
#   curl -sf -X POST https://ltpp.vip/api/github/pages/sync/<owner>/<repo> \
#        -H "Connection: close"
#
# 部署完成(GitHub Pages action 跑完 + 返回 success)后,这一步告诉 ltpp.vip 镜像站
# "新版本已经就绪,把它推到 CDN 上"。如果不调,镜像站会继续返回旧内容(直到它自己
# 的轮询周期刷新)。
#
# 用法:
#   ./sync-pages.sh [owner/repo]      # 默认 euv-dev/euv
#   MAX_RETRIES=60 RETRY_DELAY=30 ./sync-pages.sh euv-dev/euv-docs
#
# env:
#   MAX_RETRIES  最大尝试次数,默认 60
#   RETRY_DELAY  每次重试间隔(秒),默认 60
#
# 返回: API 返回 200 + {"code":200,"message":"Success",...} 即视为同步请求成功,
#       实际 CDN 刷新仍需 ~1 分钟(见 static-site-deploy-verification skill)。

set -euo pipefail

TARGET="${1:-euv-dev/euv}"
MAX_RETRIES="${MAX_RETRIES:-60}"
RETRY_DELAY="${RETRY_DELAY:-60}"

URL="https://ltpp.vip/api/github/pages/sync/${TARGET}"

echo "[sync-pages] target:    ${TARGET}"
echo "[sync-pages] endpoint:  ${URL}"
echo "[sync-pages] max_retries=${MAX_RETRIES} retry_delay=${RETRY_DELAY}s"

for i in $(seq 1 "${MAX_RETRIES}"); do
  if curl -sf -X POST "${URL}" -H "Connection: close"; then
    echo ""
    echo "[sync-pages] Sync succeeded on attempt $i"
    exit 0
  fi
  echo "[sync-pages] Attempt $i of ${MAX_RETRIES} failed"
  if [ "$i" -lt "${MAX_RETRIES}" ]; then
    echo "[sync-pages] Retrying in ${RETRY_DELAY}s..."
    sleep "${RETRY_DELAY}"
  fi
done
echo "[sync-pages] All ${MAX_RETRIES} attempts failed"
exit 1