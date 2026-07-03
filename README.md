# CBIR Web 系统

这是按 `CBIR_IMPLEMENTATION_SPEC.md` 搭建的基于内容的图像检索系统。

当前验收范围：

- M0：项目脚手架、配置、健康检查。
- M1：以 CIFAR-10 为主数据集，完成 HSV 颜色直方图建库、上传图片检索 Top-12、最简 Vue3 页面。
- M2：传统特征、图库、直方图展示、批量评估。
- M3：ResNet50 深度特征、FAISS 深度索引、深度检索与融合检索。
- M4：mAP、P@K、PR 曲线评估接口与前端图表。
- M5：CIFAR-10 数据集热切换、图库增删、索引重建、错误提示与空状态。
- M6：复现说明、API 清单、算法说明、报告素材清单。
- Pipeline：前端实验流水线，支持上传/下载数据集、预处理、训练 CNN、重建索引、后台任务日志。

## 后端

CIFAR-10 从 Toronto 官方页面获取：[https://www.cs.toronto.edu/~kriz/cifar.html](https://www.cs.toronto.edu/~kriz/cifar.html)。本项目以 CIFAR-10 为主数据集，使用 Python 版本 `cifar-10-python.tar.gz`，官方 md5 为 `c58f30108f718f92721af3b95e74349a`。

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-cuda.txt
curl.exe -L -o ..\data\raw\cifar-10-python.tar.gz https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz
Get-FileHash ..\data\raw\cifar-10-python.tar.gz -Algorithm MD5
tar -xzf ..\data\raw\cifar-10-python.tar.gz -C ..\data\raw
python -m scripts.prepare_cifar --src ..\data\raw\cifar-10-batches-py --split all
python -m scripts.build_index --dataset cifar10 --features all
uvicorn app.main:app --reload --port 8000
```

没有 CUDA 时，代码会自动回退 CPU。也可以先安装 CPU 版 PyTorch：

```powershell
pip install torch torchvision
```

CUDA 验收：

```powershell
python -m scripts.verify_cuda
curl http://localhost:8000/api/health
```

当前项目已将 CIFAR-10 train+test 全量 60000 张作为主数据集。如果只想快速验收子集，可改用 `--split train --per-class 500`。

后端质量验收：

```powershell
python -m pytest
python -m ruff check app scripts tests
python -m black --check app scripts tests
```

## 前端

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
pnpm install
pnpm run dev
```

访问 `http://localhost:5173/search`，默认数据集为 `cifar10`。

如果后端因端口权限问题改跑 `8010`，前端这样启动：

```powershell
$env:VITE_API_TARGET="http://127.0.0.1:8010"
npm run dev
```

## API 清单

- `GET /api/health`：健康检查，返回当前 CPU/CUDA 状态。
- `GET /api/datasets`：数据集列表。
- `GET /api/datasets/{dataset}/images`：分页图库。
- `GET /api/datasets/{dataset}/categories`：类别列表。
- `POST /api/search`：上传图片或按 `image_id` 检索 Top-K。
- `GET /api/histogram`：HSV/灰度直方图。
- `POST /api/images`：上传图片入库并同步索引。
- `DELETE /api/images/{image_id}`：删除图片并同步索引。
- `POST /api/index/build`：重建指定特征索引。
- `GET /api/evaluate`：返回 mAP、P@K、PR 曲线。

FastAPI 自动文档：启动后端后访问 `http://127.0.0.1:8000/docs`。

## 算法说明

- 颜色特征：HSV 三维联合直方图做 L1 归一化；颜色矩统计 H/S/V 三通道均值、标准差、三阶中心矩。
- 纹理特征：GLCM 先量化灰度级，再计算对比度、相关性、能量、熵，并统计均值和标准差；LBP 采用 uniform 模式并归一化直方图。
- 形状特征：Hu 矩使用灰度化、中值滤波、Sobel、迭代阈值后计算 7 个不变矩；EOH 使用 Sobel 梯度方向按幅值加权统计。
- 深度特征：ResNet50 去掉全连接层，取 avgpool 2048 维输出，使用 ImageNet 标准化和 L2 归一化。
- 综合检索：颜色、纹理、形状、深度分别计算相似度，min-max 归一化到 `[0,1]` 后按滑块权重融合。
- 评估：图库内每张图作为查询图，排除自身，同类为相关样本，计算 mAP、P@K 和平均 PR 曲线。

## 报告素材清单

- `/search`：上传或选择 CIFAR-10 图片，截图 Top-12 检索结果与直方图。
- `/gallery`：截图类别筛选、上传、删除、重建索引。
- `/evaluate`：分别评估 `color_hist`、`glcm`、`hu`、`deep`，截图 mAP/P@12 柱状图和 PR 曲线。
- `/pipeline`：截图数据集导入、预处理、训练、索引构建和任务日志。
- `/docs`：截图接口文档首页和 `/api/evaluate` 接口。

## 常见问题

- 端口 `8000` 被占用或无权限：后端改用 `--port 8010`。
- 后端使用 `8010` 时前端连不上：先设置 `$env:VITE_API_TARGET="http://127.0.0.1:8010"`，再启动前端。
- CUDA 不可用：确认 `python -m scripts.verify_cuda`；不可用时系统会自动回退 CPU，但深度建库会变慢。
- `pnpm` 不存在：本项目也支持 `npm install` 和 `npm run dev`。
- 首次深度特征建库慢：首次会下载 ResNet50 权重；下载完成后会走本地缓存。

## 实验流水线页面

访问 `http://localhost:5173/pipeline`，可以通过前端启动以下后台任务：

- 上传或下载 CIFAR 数据压缩包。
- 预处理 CIFAR-10 / CIFAR-100，写入图片目录、SQLite 和 `registry.json`。
- 训练 CIFAR CNN，实时查看 epoch、loss、train_acc、val_acc。
- 重建 deep 或传统特征索引。
- 启动一次 deep + cosine 评估。

说明：浏览器只负责交互和进度展示，真正的数据处理、PyTorch 训练、CUDA 推理和 FAISS 建库仍由 FastAPI 后端启动 Python 后台任务执行。

## 一键启动脚本

项目根目录提供 `start_cbir.ps1`，会先关闭占用后端/前端端口的旧进程，再后台启动后端和前端，并输出接口健康检查结果。

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system
.\start_cbir.ps1
```

默认端口：

- 后端：`http://127.0.0.1:8010`
- 前端：`http://localhost:5173`
- 实验流水线：`http://localhost:5173/pipeline`

如果想跳过评估接口健康检查：

```powershell
.\start_cbir.ps1 -SkipEvaluateHealth
```

日志目录：

```text
C:\Users\wgq20\Documents\CBIR\cbir-system\.runtime\logs
```
