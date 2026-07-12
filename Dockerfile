# ===== 阶段1：前端构建 =====
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ===== 阶段2：后端依赖 =====
FROM python:3.11-slim AS backend-deps
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ===== 阶段3：生产镜像 =====
FROM python:3.11-slim

# 安装系统依赖：nginx、libsndfile（音频解码）
# chromaprint 为可选（音频指纹），不存在则去重回退到哈希+元数据匹配
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    libsndfile1 \
    && (apt-get install -y --no-install-recommends chromaprint-tools || true) \
    && rm -rf /var/lib/apt/lists/*

# 复制后端依赖与源码
WORKDIR /app/backend
COPY --from=backend-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY backend/ ./

# 复制前端构建产物到 nginx 静态目录
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# nginx 配置：静态资源 + 反向代理 API 到后端
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
# 移除默认 nginx 配置避免冲突
RUN rm -f /etc/nginx/sites-enabled/default

# 启动脚本：同时运行 nginx 和 uvicorn
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

# 数据与配置目录（回收站也放这里，构建时预创建）
# 注意：docker-compose 挂载 ./data:/app/data 后，挂载点会覆盖镜像内容，
# 所以 start.sh 还会在启动时再 mkdir 一次保证目录存在
RUN mkdir -p /app/data /app/data/recycle /app/data/logs /app/data/covers

EXPOSE 28080

CMD ["/start.sh"]
