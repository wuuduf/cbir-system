# CBIR Web 系统

本项目是一个基于内容的图像检索系统（Content-Based Image Retrieval, CBIR）。系统以 CIFAR-10 全量 60000 张图片作为主要图库，支持传统图像特征、深度特征、模型训练、检索评估、视频检索和 AI 辅助分析。

GitHub 地址：

```text
https://github.com/wuuduf/cbir-system
```

在线演示地址：

```text
https://cbir.sdaudw321.dpdns.org
```

## 1. 功能概览

- 图像检索：上传图片或选择图库图片，返回 Top-K 相似图片。
- 图库浏览：分页浏览 CIFAR-10 全量图片，支持类别筛选。
- 特征提取：支持 HSV、颜色矩、GLCM、LBP、Hu、EOH、CNN、Triplet、DINOv2、CLIP。
- 相似度度量：支持余弦相似度、欧氏距离、直方图相交、加权距离。
- 检索评估：计算 mAP、P@K、PR 曲线，支持多特征同场对比。
- 模型训练：支持 CIFAR-ResNet18 分类模型和 Triplet 度量学习模型训练。
- 视频检索：抽取视频关键帧，复用图像检索流程实现以图搜视频。
- 任务中心：后台任务支持进度条、日志查看和取消。
- AI 分析：管理员配置 DeepSeek 兼容接口后，可对评估结果生成文字分析。
- 前端部署：支持 Cloudflare Pages。
- 后端部署：支持本地运行和 Docker 部署到 VPS。

## 2. 项目结构

```text
cbir-system/
├─ backend/                       FastAPI 后端
│  ├─ app/                        API、特征、检索、评估、服务层代码
│  ├─ scripts/                    数据准备、索引、训练、评估脚本
│  ├─ tests/                      后端测试
│  ├─ requirements.txt            本地开发依赖
│  ├─ requirements-docker.txt     Docker CPU 部署依赖
│  └─ settings.yaml               后端配置
├─ frontend/                      Vue3 + Vite 前端
│  ├─ public/                     静态资源，如二维码、Pages 路由规则
│  └─ src/                        页面、组件、路由、API 封装
├─ data/                          本地运行数据目录，不提交到 GitHub
├─ docker-compose.backend.yml     Docker 后端编排文件
├─ start_cbir.ps1                 Windows 一键启动脚本
└─ README.md
```

## 3. 数据目录约定

运行系统需要把数据放在项目根目录的 `data/` 下：

```text
data/
├─ raw/                           原始压缩包和解压目录
│  ├─ cifar-10-python.tar.gz
│  └─ cifar-10-batches-py/
├─ datasets/
│  └─ cifar10/
│     ├─ images/                  入库后的 JPG 图片
│     └─ index/                   .npy / .faiss 特征索引
├─ models/                        CNN / Triplet 模型 .pt 文件
├─ videos/                        视频库、关键帧和视频索引
├─ cbir.db                        SQLite 数据库
├─ registry.json                  数据集登记信息
└─ admin_config.json              AI 接口配置，本地保存，不提交
```

GitHub 仓库不包含数据库、模型、索引、视频和 CIFAR-10 图片文件。

## 4. 环境准备

### 4.1 后端 Python 环境

推荐 Python 版本：`3.10`

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

如果只在 VPS 上部署展示版，推荐使用 CPU 依赖：

```powershell
pip install -r requirements-docker.txt
```

如果要在本地 RTX 显卡上训练模型，需要安装 CUDA 版 PyTorch。安装后可检查：

```powershell
python -m scripts.verify_cuda
```

### 4.2 前端 Node 环境

推荐 Node.js 版本：`18+`

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm install
```

## 5. 从零准备 CIFAR-10 数据集

CIFAR-10 官方页面：

```text
https://www.cs.toronto.edu/~kriz/cifar.html
```

Python 版本下载地址：

```text
https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz
```

官方 MD5：

```text
c58f30108f718f92721af3b95e74349a
```

### 5.1 下载数据集

方式一：使用 PowerShell 下载：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system
New-Item -ItemType Directory -Force -Path .\data\raw
curl.exe -L -o .\data\raw\cifar-10-python.tar.gz https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz
Get-FileHash .\data\raw\cifar-10-python.tar.gz -Algorithm MD5
```

方式二：使用项目下载脚本：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.download_file `
  https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz `
  ..\data\raw\cifar-10-python.tar.gz
```

### 5.2 解压数据集

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system
tar -xzf .\data\raw\cifar-10-python.tar.gz -C .\data\raw
```

解压后应出现：

```text
data/raw/cifar-10-batches-py/
```

该目录中应包含：

```text
batches.meta
data_batch_1
data_batch_2
data_batch_3
data_batch_4
data_batch_5
test_batch
```

### 5.3 将 CIFAR-10 全量 60000 张图片入库

这个步骤会把官方 batch 文件转换为 JPG 图片，写入 SQLite 数据库，并更新 `data/registry.json`。

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.prepare_cifar_dataset `
  --dataset cifar10 `
  --src ..\data\raw\cifar-10-batches-py `
  --split all
```

执行后会生成：

```text
data/datasets/cifar10/images/
data/datasets/cifar10/index/
data/cbir.db
data/registry.json
```

如果只想快速测试，可以每类只导入少量图片：

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_cifar_dataset `
  --dataset cifar10 `
  --src ..\data\raw\cifar-10-batches-py `
  --split train `
  --per-class 500
```

## 6. 构建图像特征索引

入库后必须构建索引，检索页和评估页才能正常返回结果。

### 6.1 构建所有主要特征

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.build_index --dataset cifar10 --features all
```

`all` 会构建：

```text
color_hist,color_moments,glcm,lbp,hu,eoh,deep_cnn,deep_triplet,clip,dinov2
```

注意：`clip` 和 `dinov2` 首次运行可能需要下载模型权重，CPU 机器上会比较慢。

### 6.2 只构建传统特征

适合 CPU 或快速验收：

```powershell
.\.venv\Scripts\python.exe -m scripts.build_index `
  --dataset cifar10 `
  --features color_hist,color_moments,glcm,lbp,hu,eoh
```

### 6.3 只构建 CNN / Triplet 深度索引

如果已经训练好模型：

```powershell
.\.venv\Scripts\python.exe -m scripts.build_index `
  --dataset cifar10 `
  --features deep_cnn `
  --cnn-model ..\data\models\cifar_resnet18.pt
```

```powershell
.\.venv\Scripts\python.exe -m scripts.build_index `
  --dataset cifar10 `
  --features deep_triplet `
  --triplet-model ..\data\models\cifar_resnet18_metric.pt
```

也可以同时构建：

```powershell
.\.venv\Scripts\python.exe -m scripts.build_index `
  --dataset cifar10 `
  --features deep_cnn,deep_triplet `
  --cnn-model ..\data\models\cifar_resnet18.pt `
  --triplet-model ..\data\models\cifar_resnet18_metric.pt
```

## 7. 启动系统

### 7.1 手动启动后端

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

后端接口文档：

```text
http://127.0.0.1:8000/docs
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

### 7.2 手动启动前端

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm run dev
```

访问：

```text
http://localhost:5173/search
```

如果后端端口不是 8000，例如使用 8010：

```powershell
$env:VITE_API_TARGET="http://127.0.0.1:8010"
npm run dev
```

### 7.3 一键启动

项目根目录提供 Windows 一键启动脚本：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system
.\start_cbir.ps1
```

脚本会尝试关闭已有前后端进程，重新启动后端和前端，并输出接口健康度。

## 8. 打开前端进行模型训练

完成数据集下载、解压、入库后，就可以通过前端训练模型。

### 8.1 启动前后端

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system
.\start_cbir.ps1
```

或手动启动：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm run dev
```

### 8.2 进入模型训练页

浏览器打开：

```text
http://localhost:5173/models
```

训练页固定使用 CIFAR-10 官方解包目录：

```text
data/raw/cifar-10-batches-py
```

页面中有两条训练路线：

```text
CNN 分类模型
Triplet 度量学习模型
```

### 8.3 前端训练 CNN

在“CNN 分类模型”卡片中设置：

```text
Epoch
Batch Size
学习率
Workers
权重衰减 WD
是否使用 AMP
```

点击：

```text
开始训练 CNN
```

训练过程会在任务中心显示进度和日志。输出模型会保存到：

```text
data/models/
```

### 8.4 前端训练 Triplet

Triplet 可以在已训练 CNN 基础上继续训练，也可以从零训练。

在“Triplet 度量学习模型”卡片中设置：

```text
Epoch
Batch Size
学习率
Eval K
Margin
Triplet 权重
权重衰减 WD
预训练 CNN
是否使用 AMP
```

点击：

```text
开始训练 Triplet
```

训练完成后，模型同样保存到：

```text
data/models/
```

### 8.5 训练后重建深度索引

模型训练完成后，需要在页面下方选择训练出的 `.pt` 模型，然后重建对应索引：

```text
CNN 索引
Triplet 索引
```

索引完成后，检索页和评估页才会使用新模型结果。

## 9. 命令行训练模型

如果不通过前端，也可以直接用脚本训练。

### 9.1 训练 CNN 分类模型

推荐命令：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.train_cifar_cnn `
  --dataset cifar10 `
  --src ..\data\raw\cifar-10-batches-py `
  --epochs 80 `
  --batch-size 128 `
  --lr 0.1 `
  --weight-decay 0.0005 `
  --workers 2 `
  --amp `
  --output ..\data\models\cifar_resnet18.pt
```

参数说明：

```text
--dataset        cifar10 或 cifar100
--src            官方 CIFAR 解包目录
--epochs         训练轮数
--batch-size     批大小
--lr             学习率
--weight-decay   权重衰减
--workers        DataLoader 进程数
--amp            CUDA 下启用混合精度
--output         模型保存路径
```

训练完成后会输出最佳验证准确率和模型路径。

### 9.2 训练 Triplet 度量学习模型

推荐先用 CNN 作为预训练模型：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.train_cifar_triplet `
  --dataset cifar10 `
  --src ..\data\raw\cifar-10-batches-py `
  --epochs 40 `
  --batch-size 128 `
  --lr 0.01 `
  --weight-decay 0.0005 `
  --workers 2 `
  --margin 0.2 `
  --triplet-weight 1.0 `
  --ce-weight 0.5 `
  --eval-k 12 `
  --pretrained ..\data\models\cifar_resnet18.pt `
  --amp `
  --output ..\data\models\cifar_resnet18_metric.pt
```

如果要从零训练 Triplet，可以把 `--pretrained` 设为空字符串：

```powershell
.\.venv\Scripts\python.exe -m scripts.train_cifar_triplet `
  --dataset cifar10 `
  --src ..\data\raw\cifar-10-batches-py `
  --pretrained "" `
  --output ..\data\models\cifar_resnet18_metric.pt
```

Triplet 训练输出中会包含：

```text
best_acc
best_p_at_k
best_score
checkpoint
```

### 9.3 训练后重建索引

训练完成后必须重建索引：

```powershell
.\.venv\Scripts\python.exe -m scripts.build_index `
  --dataset cifar10 `
  --features deep_cnn `
  --cnn-model ..\data\models\cifar_resnet18.pt
```

```powershell
.\.venv\Scripts\python.exe -m scripts.build_index `
  --dataset cifar10 `
  --features deep_triplet `
  --triplet-model ..\data\models\cifar_resnet18_metric.pt
```

## 10. 命令行评估

评估 CNN 深度特征：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.run_evaluate `
  --dataset cifar10 `
  --feature deep_cnn `
  --metric cosine `
  --k 12 `
  --sample 100
```

评估 Triplet 特征：

```powershell
.\.venv\Scripts\python.exe -m scripts.run_evaluate `
  --dataset cifar10 `
  --feature deep_triplet `
  --metric cosine `
  --k 12 `
  --sample 100
```

评估传统特征：

```powershell
.\.venv\Scripts\python.exe -m scripts.run_evaluate `
  --dataset cifar10 `
  --feature color_hist `
  --metric intersection `
  --k 12 `
  --sample 100
```

常用特征名：

```text
color_hist
color_moments
glcm
lbp
hu
eoh
deep_cnn
deep_triplet
clip
dinov2
```

常用相似度：

```text
cosine
euclidean
intersection
weighted
```

## 11. CIFAR-100 可选扩展

如果要使用 CIFAR-100，可以下载官方 Python 版本：

```text
https://www.cs.toronto.edu/~kriz/cifar-100-python.tar.gz
```

解压后目录一般为：

```text
data/raw/cifar-100-python/
```

入库 CIFAR-100：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.prepare_cifar_dataset `
  --dataset cifar100 `
  --src ..\data\raw\cifar-100-python `
  --split all `
  --label-level fine
```

使用粗类别：

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_cifar_dataset `
  --dataset cifar100 `
  --src ..\data\raw\cifar-100-python `
  --split all `
  --label-level coarse
```

训练 CIFAR-100 CNN：

```powershell
.\.venv\Scripts\python.exe -m scripts.train_cifar_cnn `
  --dataset cifar100 `
  --src ..\data\raw\cifar-100-python `
  --label-level fine `
  --epochs 100 `
  --batch-size 128 `
  --lr 0.1 `
  --amp `
  --output ..\data\models\cifar100_resnet18.pt
```

## 12. Corel 或自定义图片集可选入库

如果有本地图像文件夹，可以用 Corel 脚本入库。脚本会递归扫描图片，根据子文件夹或文件名前缀推断类别。

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.prepare_corel --src D:\datasets\Corel1000
```

入库后构建索引：

```powershell
.\.venv\Scripts\python.exe -m scripts.build_index `
  --dataset corel1000 `
  --features color_hist,glcm,lbp,hu,eoh
```

## 13. 前端页面说明

```text
/search      图像检索，上传或选择图片，查看 Top-K 结果
/gallery     图库浏览，分页查看 CIFAR-10 图片
/evaluate    检索评估，查看 mAP、P@K、PR 曲线和多特征对比
/videos      视频检索，导入视频、抽关键帧、以图搜视频
/models      模型训练，前端启动 CNN / Triplet 训练和索引重建
/admin       AI 分析接口配置
```

## 14. 主要脚本速查

所有脚本都在 `backend/scripts/` 下，通常在 `backend` 目录中执行：

```text
download_file.py             下载一个文件到指定路径
prepare_cifar.py             旧版 CIFAR-10 入库脚本
prepare_cifar_dataset.py     CIFAR-10 / CIFAR-100 通用入库脚本
prepare_corel.py             Corel 或自定义图片目录入库
build_index.py               构建传统/深度特征索引
train_cifar_cnn.py           训练 CIFAR ResNet18 分类模型
train_cifar_triplet.py       训练 Triplet 度量学习模型
run_evaluate.py              命令行评估单个特征
verify_cuda.py               检查 CUDA 是否可用
```

## 15. Cloudflare Pages 前端部署

GitHub 仓库根目录中直接包含 `frontend` 文件夹，因此 Cloudflare Pages 填：

```text
Root directory: frontend
Build command: npm run build
Build output directory: dist
```

环境变量：

```text
VITE_API_BASE_URL=https://你的后端域名
```

如果暂时没有 HTTPS 域名，也可以测试：

```text
VITE_API_BASE_URL=http://你的VPS_IP:8000
```

正式展示建议后端也配置 HTTPS，避免浏览器拦截 HTTPS 页面请求 HTTP 接口。

## 16. Docker 后端部署

在项目根目录构建后端镜像：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system
docker build -f backend/Dockerfile -t cbir-backend:latest .
```

本地 Docker 运行：

```powershell
docker run -d `
  --name cbir-backend `
  --restart unless-stopped `
  -p 8000:8000 `
  -e APP__DEVICE=cpu `
  -e "CBIR_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173" `
  -v "${PWD}\data:/app/data" `
  cbir-backend:latest
```

VPS 运行示例：

```bash
mkdir -p /opt/cbir/data

docker run -d \
  --name cbir-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  -e APP__DEVICE=cpu \
  -e CBIR_CORS_ORIGINS=https://你的前端.pages.dev \
  -v /opt/cbir/data:/app/data \
  cbir-backend:latest
```

VPS 上的数据应放在：

```text
/opt/cbir/data
```

## 17. 常见问题

### 17.1 前端能打开，但没有检索结果

通常是数据集没有入库或索引没有构建。检查：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.run_evaluate --dataset cifar10 --feature color_hist --metric intersection --k 12 --sample 10
```

如果提示没有图片，重新执行入库脚本。

如果提示没有索引，重新执行 `scripts.build_index`。

### 17.2 训练页面不能启动任务

检查后端是否运行：

```text
http://127.0.0.1:8000/api/health
```

检查 CIFAR 解包目录是否存在：

```text
data/raw/cifar-10-batches-py
```

### 17.3 CUDA 不可用

运行：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.verify_cuda
```

如果显示 `cuda_available: False`，系统仍可用 CPU 运行，但训练和深度索引会慢很多。

### 17.4 Cloudflare Pages 页面能打开，但接口失败

检查 Pages 环境变量：

```text
VITE_API_BASE_URL
```

检查后端 CORS：

```text
CBIR_CORS_ORIGINS=https://你的前端.pages.dev
```

如果前端是 HTTPS，后端最好也使用 HTTPS。

## 18. 推荐完整流程

从零开始，最常用流程如下：

```powershell
# 1. 后端环境
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# 2. 下载并解压 CIFAR-10
cd C:\Users\wgq20\Documents\CBIR\cbir-system
New-Item -ItemType Directory -Force -Path .\data\raw
curl.exe -L -o .\data\raw\cifar-10-python.tar.gz https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz
tar -xzf .\data\raw\cifar-10-python.tar.gz -C .\data\raw

# 3. 全量入库
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.prepare_cifar_dataset --dataset cifar10 --src ..\data\raw\cifar-10-batches-py --split all

# 4. 先构建传统索引，保证系统能快速检索
.\.venv\Scripts\python.exe -m scripts.build_index --dataset cifar10 --features color_hist,color_moments,glcm,lbp,hu,eoh

# 5. 启动系统
cd C:\Users\wgq20\Documents\CBIR\cbir-system
.\start_cbir.ps1
```

然后打开：

```text
http://localhost:5173/search
http://localhost:5173/models
http://localhost:5173/evaluate
```

如果要进一步提升深度检索效果：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.train_cifar_cnn --dataset cifar10 --src ..\data\raw\cifar-10-batches-py --epochs 80 --batch-size 128 --lr 0.1 --weight-decay 0.0005 --workers 2 --amp --output ..\data\models\cifar_resnet18.pt
.\.venv\Scripts\python.exe -m scripts.train_cifar_triplet --dataset cifar10 --src ..\data\raw\cifar-10-batches-py --epochs 40 --batch-size 128 --lr 0.01 --weight-decay 0.0005 --workers 2 --margin 0.2 --triplet-weight 1.0 --ce-weight 0.5 --eval-k 12 --pretrained ..\data\models\cifar_resnet18.pt --amp --output ..\data\models\cifar_resnet18_metric.pt
.\.venv\Scripts\python.exe -m scripts.build_index --dataset cifar10 --features deep_cnn,deep_triplet --cnn-model ..\data\models\cifar_resnet18.pt --triplet-model ..\data\models\cifar_resnet18_metric.pt
```
