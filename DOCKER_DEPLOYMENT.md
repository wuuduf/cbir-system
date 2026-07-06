# CBIR 后端 Docker 部署说明

## 部署结构

推荐使用：

```text
Cloudflare Pages：前端 Vue 静态页面
VPS Docker：FastAPI 后端、SQLite、图片库、视频库、索引和模型
```

后端镜像只包含 FastAPI 程序和 Python 依赖，不直接把 `data/` 打进镜像。`data/` 目录通过 Docker volume 挂载到容器内的 `/app/data`。

这样做的原因：

- `data/` 通常包含 CIFAR-10 图片、视频、索引和模型，体积较大，不适合放进 GitHub 或 Docker 镜像。
- 代码更新时只需要重新构建较小的后端镜像。
- VPS 上的数据目录可以长期保留，容器重建后仍然能复用。

## 本地构建

在项目根目录运行：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system
docker compose -f docker-compose.backend.yml build
```

本地启动：

```powershell
docker compose -f docker-compose.backend.yml up -d
```

检查接口：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/datasets
```

停止：

```powershell
docker compose -f docker-compose.backend.yml down
```

## 上传到 Docker Hub

先登录 Docker Hub：

```powershell
docker login
```

构建并打标签：

```powershell
docker build -f backend/Dockerfile -t 你的用户名/cbir-backend:latest .
```

推送镜像：

```powershell
docker push 你的用户名/cbir-backend:latest
```

## VPS 运行

在 VPS 上准备目录：

```bash
mkdir -p /opt/cbir/data
```

把本地 `data/` 上传到 VPS：

```powershell
scp -r C:\Users\wgq20\Documents\CBIR\cbir-system\data root@你的VPS_IP:/opt/cbir/data
```

在 VPS 上运行后端：

```bash
docker pull 你的用户名/cbir-backend:latest

docker rm -f cbir-backend || true
docker run -d \
  --name cbir-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  -e APP__DEVICE=cpu \
  -e CBIR_CORS_ORIGINS=https://你的前端.pages.dev \
  -v /opt/cbir/data:/app/data \
  你的用户名/cbir-backend:latest
```

检查后端：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/datasets
```

## Cloudflare Pages 前端配置

Cloudflare Pages 的构建配置：

```text
Root directory: frontend
Build command: npm run build
Build output directory: dist
```

环境变量：

```text
VITE_API_BASE_URL=http://你的VPS_IP:8000
```

如果后续配置了域名和 HTTPS，建议改成：

```text
VITE_API_BASE_URL=https://api.你的域名
```

## 注意事项

- 不要把 `data/admin_config.json`、模型文件、视频文件、索引文件提交到 GitHub。
- 1 核 1GB VPS 适合部署展示版后端，不适合在线训练 CNN 或 Triplet 模型。
- 如果前端是 HTTPS，后端也建议使用 HTTPS，否则浏览器可能拦截接口请求。
