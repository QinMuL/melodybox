# MelodyBox · 音律盒子

> 面向 NAS 和内网环境的音乐文件智能整理工具 —— 自动规范化文件名、去重音乐库、按"艺术家-专辑"结构归档。

仿 QQ 音乐主题设计，Docker 一键部署，支持群晖、威联通、unRAID 等 NAS 设备。

## 功能特性

- **元数据整理**：基于 mutagen 读取音频元数据，自动规范化文件名
- **目录归档**：按 `艺术家/专辑/音轨号-歌曲名` 结构自动归类
- **智能去重**：文件哈希精确匹配 + 元数据模糊匹配，推荐保留最高音质
- **QQ 音乐主题**：绿色渐变主题、深色/浅色双模式、现代化 Web 界面
- **实时进度**：WebSocket 推送整理任务进度与日志
- **多格式支持**：MP3、FLAC、APE、WAV、M4A、OGG、OPUS
- **在线补全**：MusicBrainz 在线查询补全缺失元数据

## 快速开始

### Docker Compose 部署（推荐）

```bash
git clone https://github.com/<your-username>/melodybox.git
cd melodybox
```

编辑 `docker-compose.yml`，将 `/path/to/your/music` 改为你的实际音乐目录路径：

```yaml
volumes:
  - /your/music/path:/music:rw
```

启动服务：

```bash
docker compose up -d
```

访问 `http://<NAS_IP>:28080` 即可使用。

### Docker Run 部署

```bash
docker run -d \
  --name melodybox \
  --restart unless-stopped \
  -p 28080:28080 \
  -v /your/music/path:/music:rw \
  -v melodybox-data:/app/data:rw \
  -e TZ=Asia/Shanghai \
  ghcr.io/<your-username>/melodybox:latest
```

## 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 28080 | Nginx | 对外暴露的 Web 服务（前端 + API 代理） |
| 28081 | FastAPI | 容器内部，不对外暴露 |

## 本地开发

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

## 项目结构

```
melodybox/
├── frontend/          # React + Vite + TailwindCSS 前端
├── backend/           # Python FastAPI 后端
├── docker/            # Nginx 配置与启动脚本
├── Dockerfile         # 多阶段构建
├── docker-compose.yml # 一键部署
└── .github/workflows/ # GitHub Actions 自动构建镜像
```

## 技术栈

- **前端**：React 18 + Vite + TailwindCSS + Zustand
- **后端**：Python + FastAPI + SQLAlchemy + SQLite
- **音频处理**：mutagen（元数据）、ChromaPrint/AcoustID（音频指纹）
- **部署**：Docker 多阶段构建 + Nginx 反向代理

## License

MIT
