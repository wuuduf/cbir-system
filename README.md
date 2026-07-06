# CBIR Web 系统

本项目是一个基于内容的图像检索系统。系统以 CIFAR-10 全量 60000 张图片作为主要图库，支持传统特征、深度特征、模型训练、检索评估、视频检索和 AI 辅助结果分析。

GitHub 地址：

```text
https://github.com/wuuduf/cbir-system
```

## 主要功能

- 图像检索：上传图片或选择图库图片，按 Top-K 返回相似图片。
- 图库浏览：分页查看 CIFAR-10 图片，支持类别筛选。
- 多特征检索：支持 HSV、颜色矩、GLCM、LBP、Hu、EOH、CNN、Triplet、DINOv2、CLIP 等特征。
- 多相似度度量：支持余弦相似度、欧氏距离、直方图相交和加权距离。
- 检索评估：计算 mAP、P@K、PR 曲线，并支持多特征同场对比。
- 模型训练：支持 CIFAR-ResNet18 分类模型训练和 Triplet 度量学习模型训练。
- 视频检索：上传或导入视频，抽取关键帧并复用图像特征完成以图搜视频。
- 任务中心：下载、预处理、训练、索引、评估等耗时任务可查看进度和日志。
- AI 分析：管理员配置 DeepSeek 兼容接口后，可对评估结果生成文字分析。
- 前端部署：支持 Cloudflare Pages 静态部署。
- 后端部署：支持 Docker 在 VPS 上运行。

## 项目结构

```text
cbir-system/
├─ backend/                 FastAPI 后端、特征提取、检索、评估和训练脚本
├─ frontend/                Vue3 + Vite 前端页面
├─ data/                    本地数据目录，提交代码时不包含数据库和数据集
├─ docker-compose.backend.yml
├─ DOCKER_DEPLOYMENT.md
├─ read日志.txt             数据获取、放置和启动说明
├─ 依赖文件.txt             前后端主要依赖说明
└─ README.md
```

## 数据集来源

主要数据集使用 CIFAR-10 Python 版本：

```text
https://www.cs.toronto.edu/~kriz/cifar.html
```

下载文件：

```text
cifar-10-python.tar.gz
```

官方 MD5：

```text
c58f30108f718f92721af3b95e74349a
```

数据文件不提交到 GitHub。部署或本地运行时，应把数据放到：

```text
cbir-system/data/
```

常用目录包括：

```text
data/raw/                   原始压缩包和解压目录
data/datasets/cifar10/      CIFAR-10 图片和特征索引
data/models/                已训练 CNN / Triplet 模型
data/videos/                视频库与关键帧
data/cbir.db                SQLite 数据库
data/registry.json          数据集登记信息
```

## 本地后端启动

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

如果只部署演示版，建议使用 CPU 依赖；如果要在本地 RTX 显卡上训练模型，可以安装 CUDA 版本 PyTorch。

后端接口文档：

```text
http://127.0.0.1:8000/docs
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

## 本地前端启动

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm install
npm run dev
```

访问：

```text
http://localhost:5173/search
```

如果后端不是默认 `8000` 端口，可以设置：

```powershell
$env:VITE_API_TARGET="http://127.0.0.1:8000"
npm run dev
```

## 一键启动

项目根目录提供 Windows 一键启动脚本：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system
.\start_cbir.ps1
```

脚本会尝试关闭已占用的前后端进程，重新启动后端和前端，并输出接口健康度。

## Cloudflare Pages 前端部署

GitHub 仓库根目录中直接包含 `frontend` 文件夹，因此 Cloudflare Pages 应填写：

```text
Root directory: frontend
Build command: npm run build
Build output directory: dist
```

环境变量：

```text
VITE_API_BASE_URL=https://你的后端域名
```

如果暂时没有域名，也可测试：

```text
VITE_API_BASE_URL=http://你的VPS_IP:8000
```

正式展示时建议后端也配置 HTTPS，避免浏览器拦截 HTTPS 页面请求 HTTP 接口。

## Docker 后端部署

后端可在 VPS 上使用 Docker 运行：

```bash
docker build -f backend/Dockerfile -t cbir-backend:latest .
docker run -d \
  --name cbir-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  -e APP__DEVICE=cpu \
  -e CBIR_CORS_ORIGINS=https://你的前端.pages.dev \
  -v /opt/cbir/data:/app/data \
  cbir-backend:latest
```

详细说明见：

```text
DOCKER_DEPLOYMENT.md
```

## 常用页面

```text
/search      图像检索
/gallery     图库浏览
/evaluate    检索评估与多特征对比
/videos      视频检索
/models      模型训练与索引重建
/admin       AI 接口配置
```

## 主要接口

```text
GET  /api/health
GET  /api/datasets
GET  /api/datasets/{dataset}/images
POST /api/search
GET  /api/evaluate
POST /api/index/build
GET  /api/tasks
POST /api/tasks/{task_id}/cancel
POST /api/videos/import-local
POST /api/videos/index/build
POST /api/videos/search
GET  /api/admin/config
PUT  /api/admin/config
POST /api/admin/analyze-evaluation
```

## 注意事项

- GitHub 仓库只提交源代码和必要配置，不包含数据库、模型、视频和 CIFAR-10 图片文件。
- `data/admin_config.json` 可能保存 API Key，已经加入 `.gitignore`，不要提交。
- 1 核 1GB VPS 适合运行展示版后端，不适合在线训练模型。
- 如果需要重新训练 CNN 或 Triplet，建议在本地有 CUDA 的电脑上训练，再把 `.pt` 模型和索引上传到 VPS。
