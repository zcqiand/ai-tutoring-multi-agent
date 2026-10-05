#!/bin/sh
# Usage: ai-tutoring-multi-agent.sh <DOCKER_USERNAME> <DOCKER_PASSWORD> [VERSION]
#
# 由 .github/workflows/ci.yml 的 deploy job 远程调用：
#   ssh deploy@vps -- cd /home/deploy/ai-tutoring-multi-agent
#                    && sh ai-tutoring-multi-agent.sh $DOCKER_USERNAME $DOCKER_PASSWORD $VERSION
#
# agent 家族部署形态（docs/families/agent.md，家族表槽位 5304/5404）：
#   web 容器（nginx 静态，容器内 :80）→ host 127.0.0.1:5304
#   api 容器（uvicorn，host=container）→ host 127.0.0.1:5404
#   vhost ai-tutoring.xiangru.uk：/ → web 容器，/api/ → api 容器（SSE 关缓冲）
#
# 与 cs-support-agent 脚本的差异：
#   - live 走 Anthropic SDK + MiniMax Anthropic 兼容端点（LLM_BASE_URL=/anthropic），
#     env 键为 ANTHROPIC_API_KEY + AI_TUTOR_MODEL_*（本仓自有契约）
#   - 会话库为内存实现：无 SQLite 卷、无 APP_DB_PATH
#   - 分支为 main（脚本/模板 raw URL 用 refs/heads/main）
#
# 前置: deploy 用户需在 docker 组中；sudoers 放 nginx + systemctl reload + !requiretty。

set -eu

USERNAME="${1:-}"
PASSWORD="${2:-}"
VERSION="${3:-latest}"
IMAGE_API="${USERNAME}/ai-tutoring-multi-agent-api:${VERSION}"
IMAGE_WEB="${USERNAME}/ai-tutoring-multi-agent-web:${VERSION}"
BASE="/home/deploy/ai-tutoring-multi-agent"
API_PORT=5404
WEB_PORT=5304
CONTAINER_API="ai-tutoring-multi-agent-api"
CONTAINER_WEB="ai-tutoring-multi-agent-web"

NGINX_DOMAIN="${NGINX_DOMAIN:-ai-tutoring.xiangru.uk}"
NGINX_CERT_BASENAME="${NGINX_CERT_BASENAME:-xiangru-uk}"

if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: $0 <DOCKER_USERNAME> <DOCKER_PASSWORD> [VERSION]" >&2
  exit 2
fi

# 唯一 secret fail-fast（suite 硬规则 §1：禁兜底）。env-file 已有真 key 时可缺省
# （后续 deploy 不转发 secret 也能跑）；空值/占位不算真 key。
ENV_FILE="$BASE/ai-tutoring-multi-agent.env"
have_real_key() {
  [ -f "$ENV_FILE" ] \
    && grep -q '^ANTHROPIC_API_KEY=sk-' "$ENV_FILE" \
    && ! grep -q '^ANTHROPIC_API_KEY=sk-xxxxxxxx$' "$ENV_FILE"
}
if [ -z "${LLM_API_KEY:-}" ] && ! have_real_key; then
  echo "ERROR: LLM_API_KEY secret required（MiniMax key；GitHub Secrets → ci.yml envs → 本脚本）" >&2
  exit 1
fi

# env-file 自举（首启）：key 集合 = .env.example 全集，APP_PORT 为 prod 值
if [ ! -f "$ENV_FILE" ]; then
  echo "→ bootstrapping $ENV_FILE from SSH env secrets"
  umask 077
  {
    printf 'LLM_MODE=live\n'
    printf 'LLM_BASE_URL=https://api.minimaxi.com/anthropic\n'
    printf 'ANTHROPIC_API_KEY=%s\n' "$LLM_API_KEY"
    printf 'AI_TUTOR_MODEL_PLANNER=MiniMax-M3\n'
    printf 'AI_TUTOR_MODEL_TUTOR=MiniMax-M3\n'
    printf 'AI_TUTOR_MODEL_EVALUATOR=MiniMax-M3\n'
    printf 'AI_TUTOR_BUDGET_USD=0.50\n'
    printf 'APP_PORT=%s\n' "$API_PORT"
  } > "$ENV_FILE"
  chown deploy:deploy "$ENV_FILE" 2>/dev/null || true
  chmod 600 "$ENV_FILE"
fi

# 存量 env-file 补键（append 不覆盖已有行）
if [ -f "$ENV_FILE" ]; then
  append_if_missing() {
    key="$1"; val="$2"
    if ! grep -q "^${key}=" "$ENV_FILE"; then
      echo "→ append ${key} to existing $ENV_FILE"
      umask 077
      printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
    fi
  }
  append_if_missing LLM_MODE 'live'
  append_if_missing LLM_BASE_URL 'https://api.minimaxi.com/anthropic'
  append_if_missing AI_TUTOR_MODEL_PLANNER 'MiniMax-M3'
  append_if_missing AI_TUTOR_MODEL_TUTOR 'MiniMax-M3'
  append_if_missing AI_TUTOR_MODEL_EVALUATOR 'MiniMax-M3'
  append_if_missing AI_TUTOR_BUDGET_USD '0.50'
  append_if_missing APP_PORT "$API_PORT"

  # 密钥类双模：缺/空/占位才覆盖（运维手工换的真 key 保留）
  upsert_if_placeholder() {
    key="$1"; val="$2"
    if ! grep -q "^${key}=..*" "$ENV_FILE" \
       || grep -q "^${key}=$" "$ENV_FILE" \
       || grep -q "^${key}=CHANGE_ME$" "$ENV_FILE" \
       || grep -q "^${key}=sk-xxxxxxxx$" "$ENV_FILE"; then
      echo "→ upsert ${key} to existing $ENV_FILE"
      sed -i "s#^${key}=.*#${key}=${val}#" "$ENV_FILE"
    fi
  }
  if [ -n "${LLM_API_KEY:-}" ]; then
    upsert_if_placeholder ANTHROPIC_API_KEY "$LLM_API_KEY"
  fi
fi

# nginx vhost 重渲染（每次 deploy 都跑；模板总从 main 拉最新）
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
NGINX_VHOST_FILE="${NGINX_SITES_AVAILABLE}/${NGINX_DOMAIN}"
NGINX_VHOST_LINK="${NGINX_SITES_ENABLED}/${NGINX_DOMAIN}"
NGINX_TEMPLATE="${BASE}/nginx-vps.conf.example"

echo "→ fetching nginx-vps.conf.example template (always fresh from main)"
curl -fsSL "https://raw.githubusercontent.com/zcqiand/ai-tutoring-multi-agent/refs/heads/main/deploy/nginx-vps.conf.example" -o "${NGINX_TEMPLATE}"

# 渲染到临时文件 —— sed 顺序：cert 归一化规则必须排在 <domain> 通配之前
# （先替换 <domain> 会把 cert 路径占位符一并吃掉，2026-09-03 事故根因）。
TMP_VHOST="$(mktemp -t vpstpl.XXXXXX)"
sed \
  -e "s|/etc/nginx/ssl/<domain>\.crt|/etc/nginx/ssl/${NGINX_CERT_BASENAME}.cert|g" \
  -e "s|/etc/nginx/ssl/<domain>\.key|/etc/nginx/ssl/${NGINX_CERT_BASENAME}.key|g" \
  -e "s|<domain>|${NGINX_DOMAIN}|g" \
  "${NGINX_TEMPLATE}" > "${TMP_VHOST}"

if [ -e "${NGINX_VHOST_FILE}" ] && diff -q "${TMP_VHOST}" "${NGINX_VHOST_FILE}" >/dev/null 2>&1; then
  echo "→ nginx vhost ${NGINX_VHOST_FILE} unchanged, skip"
  rm -f "${TMP_VHOST}"
else
  echo "→ rendering nginx vhost ${NGINX_VHOST_FILE} (domain=${NGINX_DOMAIN} cert=${NGINX_CERT_BASENAME})"
  if [ -w "${NGINX_SITES_AVAILABLE}" ]; then
    cp "${TMP_VHOST}" "${NGINX_VHOST_FILE}"
  else
    sudo cp "${TMP_VHOST}" "${NGINX_VHOST_FILE}" \
      || { echo "ERROR: sudo cp ${NGINX_VHOST_FILE} failed"; rm -f "${TMP_VHOST}"; exit 1; }
  fi
  if [ -w "${NGINX_SITES_ENABLED}" ]; then
    ln -sf "${NGINX_VHOST_FILE}" "${NGINX_VHOST_LINK}"
  else
    sudo ln -sf "${NGINX_VHOST_FILE}" "${NGINX_VHOST_LINK}" \
      || { echo "ERROR: sudo ln ${NGINX_VHOST_LINK} failed"; rm -f "${TMP_VHOST}"; exit 1; }
  fi
  rm -f "${TMP_VHOST}"
  echo "→ nginx -t"
  sudo nginx -t
  echo "→ systemctl reload nginx"
  sudo systemctl reload nginx
  echo "✓ nginx reloaded"
fi

echo "→ image: $IMAGE_API / $IMAGE_WEB"
echo "→ docker login"
printf '%s' "$PASSWORD" | docker login -u "$USERNAME" --password-stdin

echo "→ docker pull (api + web)"
docker pull "$IMAGE_API"
docker pull "$IMAGE_WEB"

echo "→ docker stop & rm $CONTAINER_API $CONTAINER_WEB"
docker stop "$CONTAINER_API" 2>/dev/null || true
docker rm "$CONTAINER_API" 2>/dev/null || true
docker stop "$CONTAINER_WEB" 2>/dev/null || true
docker rm "$CONTAINER_WEB" 2>/dev/null || true

echo "→ docker run api (host=container=$API_PORT, 内存会话库无数据卷)"
docker run -d \
  --name "$CONTAINER_API" \
  --restart unless-stopped \
  -p "127.0.0.1:${API_PORT}:${API_PORT}" \
  --env-file "$ENV_FILE" \
  "$IMAGE_API"

echo "→ docker run web (容器 :80 → host $WEB_PORT)"
docker run -d \
  --name "$CONTAINER_WEB" \
  --restart unless-stopped \
  -p "127.0.0.1:${WEB_PORT}:80" \
  "$IMAGE_WEB"

echo "→ docker image prune"
docker image prune -f

echo "→ docker ps"
docker ps --filter name="$CONTAINER_API"
docker ps --filter name="$CONTAINER_WEB"

# 健康检查：/api/health 探 200。容器死亡提前终止循环，立刻报失败。
i=0
while [ $i -lt 120 ]; do
  if wget --tries=1 --timeout=3 -q "http://127.0.0.1:${API_PORT}/api/health" -O /dev/null 2>/dev/null; then
    echo "→ /api/health 200 (host 127.0.0.1:${API_PORT}) after ${i}s"
    break
  fi
  if ! docker inspect --format='{{.State.Running}}' "$CONTAINER_API" 2>/dev/null | grep -q true; then
    echo "→ api container not running, logs:"
    docker logs --tail 30 "$CONTAINER_API"
    exit 1
  fi
  i=$((i+1))
  sleep 1
done
if [ $i -ge 120 ]; then
  echo "→ /api/health 仍未 200（120s 上限）, logs:"
  docker logs --tail 30 "$CONTAINER_API"
  exit 1
fi

# web 静态探活
if wget --tries=1 --timeout=3 -q "http://127.0.0.1:${WEB_PORT}/" -O /dev/null 2>/dev/null; then
  echo "→ web / 200 (host 127.0.0.1:${WEB_PORT})"
else
  echo "→ web / 探活失败, logs:"
  docker logs --tail 30 "$CONTAINER_WEB"
  exit 1
fi

echo "→ deploy done at $(date -u)"
