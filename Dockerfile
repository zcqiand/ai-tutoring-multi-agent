# ai-tutoring-multi-agent — API 容器（agent 家族 api 段 5404，host=container）
#
# 家族 deploy 链同款（kids/hr/cs 先例）：
#   VPS nginx 终结 TLS → /api/ proxy_pass http://127.0.0.1:5404 → 容器 uvicorn。
#   CI deploy job build & push（latest + tag 双份）→ VPS deploy/ai-tutoring-multi-agent.sh
#   拉镜像起容器。
#
# 端口是家族契约（docs/families/agent.md，家族表下一空槽 5304/5404），
# 钉死在 CMD 里不走 env 兜底。会话库为内存实现（demo 性质），无 SQLite 卷。
# 无 HEALTHCHECK（debian slim 无 wget）：探活由 deploy 脚本 host 侧 /api/health 完成。
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

EXPOSE 5404
CMD ["uvicorn", "--factory", "ai_tutoring.main:create_app", "--host", "0.0.0.0", "--port", "5404"]
