#!/bin/bash
# MelodyBox 启动脚本：同时运行 nginx 和 uvicorn

set -e

echo "启动 MelodyBox 音律盒子..."

# 启动 FastAPI 后端（后台运行）
cd /app/backend
python -m uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 28081 \
    --log-level info &

BACKEND_PID=$!
echo "FastAPI 后端已启动 (PID: $BACKEND_PID)"

# 等待后端就绪
sleep 2

# 启动 nginx（前台运行，作为主进程）
echo "启动 Nginx..."
nginx -g 'daemon off;'
