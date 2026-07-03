# CBIR Backend

当前完成到 M6：FastAPI 后端、SQLite 图像元数据、CIFAR-10 数据准备、6 种传统特征、ResNet50 深度特征、FAISS 深度索引、融合检索、评估模块、图库管理、索引重建接口和复现文档。

## 环境

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

如需 CUDA 加速深度特征，在 Windows + NVIDIA 显卡上单独安装：

```powershell
pip install -r requirements-cuda.txt
```

没有 CUDA 时会自动回退 CPU，也可以安装 CPU 版：

```powershell
pip install torch torchvision
```

CUDA 验收：

```powershell
python -m scripts.verify_cuda
curl http://localhost:8000/api/health
```

## 运行

```powershell
uvicorn app.main:app --reload --port 8000
```

健康检查：

```powershell
curl http://localhost:8000/api/health
```

评估接口：

```powershell
curl "http://localhost:8000/api/evaluate?dataset=cifar10&feature=deep&metric=cosine&k=12&sample=100"
```

## CIFAR-10 最小闭环

先从 Toronto 官方页面下载并解压 CIFAR-10 Python 版本：[https://www.cs.toronto.edu/~kriz/cifar.html](https://www.cs.toronto.edu/~kriz/cifar.html)。目录中应包含 `batches.meta`、`data_batch_1` 到 `data_batch_5`、`test_batch`。官方 md5 为 `c58f30108f718f92721af3b95e74349a`。

```powershell
curl.exe -L -o ..\data\raw\cifar-10-python.tar.gz https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz
Get-FileHash ..\data\raw\cifar-10-python.tar.gz -Algorithm MD5
tar -xzf ..\data\raw\cifar-10-python.tar.gz -C ..\data\raw
python -m scripts.prepare_cifar --src <cifar-10-batches-py目录> --split all
python -m scripts.build_index --dataset cifar10 --features all
uvicorn app.main:app --reload --port 8000
```

如果要用小样本快速验收：

```powershell
python -m scripts.prepare_cifar --src <cifar-10-batches-py目录> --per-class 500 --split train
python -m scripts.build_index --dataset cifar10 --features all
```

然后启动前端，在 `/search` 上传一张库内 CIFAR 图片，正常情况下 Top-1 应返回它自身。

## M3 深度特征与融合

`--features all` 会生成 6 种传统特征和 `deep.npy`、`deep.faiss`。如果只想重建深度索引：

```powershell
python -m scripts.build_index --dataset cifar10 --features deep
```

前端检索页可选择“深度”或“综合”，综合检索使用颜色、纹理、形状、深度 4 个权重滑块。

## 自训练 CIFAR-10 CNN

系统默认优先读取 `..\data\models\cifar_resnet18.pt`。如果该文件不存在，深度特征会自动回退到 ImageNet 预训练 ResNet50。训练自己的 CIFAR-10 CNN 后，需要重建 `deep` 索引，前端“深度特征”才会使用新模型。

推荐先用 CUDA 训练：

```powershell
python -m scripts.train_cifar_cnn --src ..\data\raw\cifar-10-batches-py --epochs 80 --batch-size 128 --amp
python -m scripts.build_index --dataset cifar10 --features deep
```

想快速冒烟测试训练流程，可先跑 1 个 epoch：

```powershell
python -m scripts.train_cifar_cnn --src ..\data\raw\cifar-10-batches-py --epochs 1 --batch-size 128 --amp
```

训练脚本使用 CIFAR-10 官方 50000 张训练集训练分类器，用 10000 张测试集保存最佳准确率模型。模型的倒数第二层 512 维向量会作为 CBIR 深度检索特征，并通过 FAISS `IndexFlatIP` 检索。

## M4-M6 评估与交付

```powershell
python -m pytest
python -m ruff check app scripts tests
python -m black --check app scripts tests
```

常用 API：

- `GET /api/evaluate`：mAP、P@K、PR 曲线。
- `POST /api/index/build`：按数据集和特征列表重建索引。
- `POST /api/images` / `DELETE /api/images/{id}`：图库增删并同步索引。

报告可用数据建议：在前端 `/evaluate` 中用 `sample=100` 快速比较 `color_hist`、`glcm`、`hu`、`deep`；需要更稳定表格时把 sample 增大到 500 或全量。
