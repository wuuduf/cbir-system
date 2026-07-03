# CBIR 项目开发日志

> 补录日期：2026-07-01  
> 说明：本文档用于记录 CBIR Web 系统从脚手架到训练模型、评估验收的主要开发过程。前期日志根据当前工程状态、验收结果和对话记录补录，后续每次阶段性修改都应继续追加，方便整理实训报告、答辩材料和复现实验过程。

## 日志规范

- 每次记录包含：日期、阶段、目标、主要改动、关键文件、验收方式、结果、遗留问题。
- 涉及模型、数据集、评估指标时，记录具体数值，例如数据量、类别数、mAP、P@K、准确率。
- 涉及命令行操作时，记录可复现命令。
- 涉及前端交互时，记录页面路径，例如 `/search`、`/gallery`、`/evaluate`。
- 如果有未执行或暂缓执行的操作，也要写明原因，例如“删除会触发 60000 张索引重建，暂不执行”。

---

## 2026-06-30 以前：M0 项目脚手架

### 目标

根据 `CBIR_IMPLEMENTATION_SPEC.md` 搭建项目基础结构，为后续图像检索、数据集管理、模型训练和前端展示提供统一工程框架。

### 完成内容

- 建立 `cbir-system` 项目目录。
- 分离前后端结构：
  - `backend/`：FastAPI、SQLite、特征提取、索引构建、检索、评估。
  - `frontend/`：Vue 3、Element Plus、Vite。
  - `data/`：数据集、索引、模型文件、原始压缩包。
- 增加后端配置文件 `backend/settings.yaml`。
- 增加后端健康检查接口 `GET /api/health`。
- 建立 SQLite 数据库模型，用于保存图像元数据。
- 建立基础 README 和验收命令。

### 关键文件

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/device.py`
- `backend/app/db/models.py`
- `backend/settings.yaml`
- `frontend/src/`
- `README.md`

### 验收结果

- 后端服务可启动。
- 健康检查接口可返回 `status: ok`。
- 前端页面可通过 Vite 打开。

---

## 2026-06-30 以前：M1 最小闭环

### 目标

完成从“准备数据集 -> 建立索引 -> 上传图片检索 -> 前端展示结果”的最小可用闭环。

### 完成内容

- 以 CIFAR-10 作为主数据集。
- 从 Toronto 官方 CIFAR 页面获取 CIFAR-10 Python 版本。
- 编写 CIFAR-10 数据准备脚本：
  - 读取 `data_batch_1` 到 `data_batch_5`。
  - 读取 `test_batch`。
  - 将 CIFAR 原始二进制数据转换为 JPEG 图片文件。
  - 写入 SQLite 图像元数据。
  - 生成 `data/registry.json` 数据集注册信息。
- 实现 HSV 颜色直方图特征。
- 实现上传图片检索接口 `POST /api/search`。
- 实现前端搜索页 `/search`，可以上传图片并显示 Top-K 检索结果。

### 关键文件

- `backend/scripts/prepare_cifar.py`
- `backend/scripts/build_index.py`
- `backend/app/features/color.py`
- `backend/app/services/search_service.py`
- `backend/app/routers/search.py`
- `frontend/src/views/SearchView.vue`
- `frontend/src/components/QueryPanel.vue`
- `frontend/src/components/ResultGrid.vue`

### 验收结果

- 能够准备 CIFAR-10 数据。
- 能够建立最小 HSV 索引。
- 前端上传图片后能返回 Top-12 相似图片。
- M0、M1 已由用户验收。

---

## 2026-06-30 以前：CIFAR-10 全量 60000 张接入

### 目标

将 CIFAR-10 的训练集和测试集全部作为系统主数据集，而不是只使用小样本。

### 完成内容

- 修改 `prepare_cifar.py`，支持 `--split all`。
- 默认导入 CIFAR-10 全量 60000 张：
  - 训练集 50000 张。
  - 测试集 10000 张。
  - 10 个类别，每类 6000 张。
- 调整脚本逻辑：
  - 不传 `--per-class` 时默认不截断。
  - 支持小样本模式用于快速验收。
  - 重新导入 CIFAR 时清理旧索引，避免数据和索引不一致。
- 更新 README 中的数据准备命令。

### 数据状态

- `data/registry.json` 中 `cifar10.count = 60000`。
- `data/datasets/cifar10/images/` 下包含 60000 张图片。
- SQLite 数据库中 `cifar10` 图像记录为 60000 条。

### 验收命令

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.prepare_cifar --src ..\data\raw\cifar-10-batches-py --split all
```

### 验收结果

- 前端数据集选择显示 `CIFAR-10 (60000)`。
- 图库页 `/gallery` 显示当前数据集共 60000 张。
- 类别筛选 `frog` 后显示 6000 张。

---

## 2026-06-30 以前：M2 传统特征与图库功能

### 目标

实现多种传统 CBIR 特征，丰富检索方式，并增加图库管理与直方图展示。

### 完成内容

实现 6 种传统特征：

- HSV 颜色直方图：颜色分布。
- 颜色矩：H/S/V 通道均值、标准差、三阶中心矩。
- GLCM：灰度共生矩阵纹理特征。
- LBP：局部二值模式纹理直方图。
- Hu 不变矩：形状统计特征。
- EOH：边缘方向直方图。

实现多种相似度：

- 余弦相似度。
- 欧氏距离。
- 直方图相交。
- 加权距离。

前端功能：

- 搜索页 `/search` 支持选择特征和相似度。
- 结果卡片显示图片、类别、分数。
- 点击结果可显示 HSV/灰度直方图。
- 图库页 `/gallery` 支持分页浏览。
- 图库页支持类别筛选。
- 图库页支持上传、删除和重建索引接口。

### 关键文件

- `backend/app/features/color.py`
- `backend/app/features/texture.py`
- `backend/app/features/shape.py`
- `backend/app/similarity.py`
- `backend/app/retrieval.py`
- `backend/app/routers/images.py`
- `frontend/src/views/GalleryView.vue`
- `frontend/src/components/HistogramChart.vue`

### 验收结果

- 传统特征索引全部可构建。
- 搜索页可切换不同特征和度量。
- 图库页分页正常。
- 图库页类别筛选正常。

---

## 2026-06-30 以前：M3 深度特征、FAISS 和融合检索

### 目标

引入深度学习特征，提高语义检索能力，并实现传统特征和深度特征的融合检索。

### 完成内容

- 使用 `torchvision.models.resnet50` 加载 ImageNet 预训练 ResNet50。
- 去掉 ResNet50 最后的分类层，取 `avgpool` 输出作为 2048 维深度特征。
- 对深度向量做 L2 归一化。
- 使用 FAISS `IndexFlatIP` 建立深度索引。
- 深度特征使用内积检索；由于已 L2 归一化，内积等价于余弦相似度。
- 实现融合检索：
  - 颜色。
  - 纹理。
  - 形状。
  - 深度。
- 前端搜索页增加“深度”和“综合”选项。
- 综合检索增加权重滑块。

### 关键文件

- `backend/app/features/deep.py`
- `backend/app/retrieval.py`
- `backend/scripts/build_index.py`
- `frontend/src/components/QueryPanel.vue`

### CUDA 支持

- 安装 CUDA 版本 PyTorch：
  - `torch 2.3.1+cu121`
  - `torchvision 0.18.1+cu121`
- 健康检查显示：
  - `selected: cuda`
  - `cuda_device_name: NVIDIA GeForce RTX 4060 Laptop GPU`

### 验收命令

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.verify_cuda
.\.venv\Scripts\python.exe -m scripts.build_index --dataset cifar10 --features deep
```

### 验收结果

- `deep.npy`、`deep_ids.npy`、`deep.faiss` 生成成功。
- 使用 `frog_0001.jpg` 检索时，Top-1 返回原图。

---

## 2026-06-30 以前：M4-M6 评估模块、交付材料和复现说明

### 目标

增加可量化评价指标，使系统不仅能“看结果”，还能比较不同算法效果。

### 完成内容

- 后端实现评估服务。
- 支持评估：
  - mAP。
  - P@K。
  - PR 曲线。
  - 查询样本数。
  - 评估耗时。
- 前端新增评估页 `/evaluate`。
- 支持选择特征、相似度、K 值和样本数。
- 前端展示指标卡、柱状图、PR 曲线和自动结论。
- 增加报告素材文件 `REPORT_MATERIALS.md`。
- 更新 README 中复现命令和 API 清单。

### 关键文件

- `backend/app/evaluate.py`
- `backend/app/services/eval_service.py`
- `backend/app/routers/evaluate.py`
- `frontend/src/views/EvaluateView.vue`
- `frontend/src/components/MetricChart.vue`
- `REPORT_MATERIALS.md`

### ResNet50 深度特征阶段评估结果

在 CIFAR-10 全量索引上，使用 sample=100：

- `deep + cosine`
- `mAP ≈ 0.4178`
- `P@12 ≈ 0.7466`

说明：ImageNet 预训练 ResNet50 具有一定泛化语义能力，但没有针对 CIFAR-10 进行训练，因此在 CIFAR-10 类内检索上效果有限。

---

## 2026-06-30：网页真人路径测试

### 目标

模拟用户真实操作，验证前端页面和后端检索结果是否正确。

### 测试范围

- 图库页 `/gallery`。
- 搜索页 `/search`。
- 评估页 `/evaluate`。
- 后端健康检查。
- 后端 CUDA 状态。
- 搜索正确性。

### 测试结果

图库页：

- 显示 `CIFAR-10 (60000)`。
- 首屏加载 24 张图片。
- 图片路径、文件名、类别标签均正常。
- 类别筛选 `frog` 后总数变为 6000。
- frog 第二页首图为 `frog_0025.jpg`。

搜索页：

- 上传区正常显示。
- 8 个特征选项正常显示：
  - HSV 直方图。
  - 颜色矩。
  - GLCM。
  - LBP。
  - Hu。
  - EOH。
  - 深度。
  - 综合。
- 综合检索权重滑块正常显示。
- 选择综合后相似度自动切到余弦。

评估页：

- 默认深度评估能生成两个图表。
- sample=100 时显示：
  - `mAP = 0.4178`
  - `P@12 = 0.7466`
  - 耗时约 58 秒。

搜索正确性：

使用 CIFAR-10 中的 `frog_0001.jpg` 作为上传查询图，8 种代表性检索方式 Top-1 均命中原图。

| 特征 | 度量 | Top-1 | 是否正确 |
|---|---|---|---|
| HSV 直方图 | intersection | frog_0001.jpg | 是 |
| 颜色矩 | cosine | frog_0001.jpg | 是 |
| GLCM | cosine | frog_0001.jpg | 是 |
| LBP | intersection | frog_0001.jpg | 是 |
| Hu | cosine | frog_0001.jpg | 是 |
| EOH | intersection | frog_0001.jpg | 是 |
| 深度 | cosine | frog_0001.jpg | 是 |
| 综合 | cosine | frog_0001.jpg | 是 |

补充测试：

- 8 个特征 × 4 个度量，共 32 个组合全部 Top-1 命中原图。
- `/api/search` 真实 HTTP 上传接口测试通过。
- `/api/histogram` 返回 36 个 HSV bin。
- `/api/health` 显示 CUDA 正常。

### 未执行项

没有真实点击图库页的“上传图片 / 删除 / 重建索引”，原因是这些操作会修改 60000 张数据集并触发全量索引重建，测试副作用较大。

---

## 2026-06-30：耗时操作遮罩窗口

### 目标

解决评估、检索、索引重建时用户可能重复点击按钮或切换控件的问题。

### 完成内容

- 新增通用遮罩组件 `BlockingOverlay.vue`。
- 搜索页检索时显示“正在检索”窗口。
- 评估页计算 mAP、P@K、PR 曲线时显示“正在评估”窗口。
- 图库上传、删除、重建索引时显示“正在同步图库”窗口。
- 遮罩期间禁用相关控件，防止重复触发。
- 任务完成后遮罩自动关闭，控件恢复。

### 关键文件

- `frontend/src/components/BlockingOverlay.vue`
- `frontend/src/views/SearchView.vue`
- `frontend/src/views/EvaluateView.vue`
- `frontend/src/views/GalleryView.vue`

### 验收结果

- `npm.cmd run build` 通过。
- 浏览器实际进入 `/evaluate` 后，评估开始时遮罩出现。
- 遮罩期间评估按钮、输入框、特征选择控件被禁用。
- 评估完成后遮罩隐藏，按钮恢复可用。

### 备注

浏览器中发现 Element Plus 会保留隐藏状态的弹窗 DOM 节点，但 `display: none`，不会阻挡操作。

---

## 2026-06-30：自训练 CIFAR-10 CNN 能力接入

### 目标

让系统不再只依赖 ImageNet 预训练 ResNet50，而是支持用 CIFAR-10 的 50000 张训练图训练自己的 CNN，并将训练后的模型用于深度检索。

### 完成内容

- 新增 CIFAR-10 专用 ResNet-18 风格 CNN。
- 新增训练脚本。
- 修改 deep 特征提取器：
  - 如果存在自训练模型 `cifar_resnet18.pt`，自动加载它。
  - 如果模型不存在，则回退到原来的 ImageNet ResNet50。
- 修改配置文件：
  - `features.deep.model: auto`
  - `features.deep.checkpoint: ../data/models/cifar_resnet18.pt`
- 更新 README 中训练命令。

### 模型设计

- 模型：CIFAR ResNet-18 风格 CNN。
- 输入：32×32 RGB 图像。
- 输出分类：10 类。
- 检索特征：倒数第二层 512 维向量。
- 特征归一化：L2 归一化。
- 训练损失：交叉熵 + label smoothing。
- 优化器：SGD + momentum + nesterov。
- 学习率调度：CosineAnnealingLR。
- 数据增强：
  - RandomCrop。
  - RandomHorizontalFlip。
  - Normalize。
  - RandomErasing。
- 支持 AMP 混合精度。

### 关键文件

- `backend/app/features/cifar_cnn.py`
- `backend/scripts/train_cifar_cnn.py`
- `backend/app/features/deep.py`
- `backend/settings.yaml`
- `backend/README.md`

### 验收结果

- `ruff` 通过。
- `black --check` 通过。
- `pytest` 6 个测试全部通过。
- 训练脚本 `--help` 可正常显示。
- deep 提取器在未训练模型时可正常回退。

---

## 2026-06-30：完成自训练 CNN 训练并重建 deep 索引

### 目标

使用 CIFAR-10 训练集训练自定义 CNN，并将训练好的模型用于全量 60000 张 CIFAR-10 的 deep 检索索引。

### 训练命令

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.train_cifar_cnn `
  --src ..\data\raw\cifar-10-batches-py `
  --epochs 80 `
  --batch-size 128 `
  --amp
```

### 训练结果

最后若干 epoch：

```text
epoch 73: train_acc=0.9962, val_acc=0.9477
epoch 74: train_acc=0.9964, val_acc=0.9473
epoch 75: train_acc=0.9964, val_acc=0.9484
epoch 76: train_acc=0.9966, val_acc=0.9499
epoch 77: train_acc=0.9969, val_acc=0.9496
epoch 78: train_acc=0.9972, val_acc=0.9495
epoch 79: train_acc=0.9972, val_acc=0.9493
epoch 80: train_acc=0.9968, val_acc=0.9491
```

最佳结果：

- `best_acc = 0.9499`
- checkpoint：`data/models/cifar_resnet18.pt`

### 模型接入验证

验证模型文件存在：

- `data/models/cifar_resnet18.pt`
- 文件大小约 44.8 MB。

验证 deep 提取器加载自训练模型：

- 特征维度从 ResNet50 的 2048 维变为自训练 CNN 的 512 维。
- 输出向量 L2 范数约为 1.0。

### 重建 deep 索引命令

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.build_index --dataset cifar10 --features deep
```

### 重建结果

- `deep.npy`：60000 × 512。
- `deep_ids.npy`：60000 个 image_id。
- `deep.faiss`：基于 512 维 L2 归一化向量的 FAISS 内积索引。
- 设备：RTX 4060 CUDA。
- 重建耗时约 1 分钟。

### 检索验收

查询图：`frog_0001.jpg`

结果：

- Top-1：`frog_0001.jpg`
- Top-1 分数：约 `0.9999999`
- Top-12 同类数量：`12 / 12`

### 评估验收

使用 `/evaluate` 同等 sample=100，`deep + cosine`：

- `mAP = 0.9961`
- `P@12 = 0.9967`
- `query_count = 100`
- 评估耗时约 8.7 秒。

与 ResNet50 预训练特征阶段对比：

| 深度特征来源 | mAP | P@12 |
|---|---:|---:|
| ImageNet ResNet50 | 0.4178 | 0.7466 |
| 自训练 CIFAR CNN | 0.9961 | 0.9967 |

结论：自训练 CIFAR-10 CNN 显著提升 CIFAR-10 类内检索效果。

---

## 2026-07-01：CIFAR-100 与前端一站式实验平台需求确认

### 用户需求

用户希望不仅支持 CIFAR-10，还希望支持 CIFAR-100，并希望把目前依赖命令行的流程升级为前端一站式操作。

用户目标可以概括为：

```text
前端选择或上传数据集
  ↓
后端 Python 自动下载/导入数据
  ↓
自动预处理并写入数据库
  ↓
前端启动模型训练
  ↓
实时显示训练进度、loss、accuracy
  ↓
训练完成后自动重建索引
  ↓
前端完成检索和评估
```

### CIFAR-100 可行性

CIFAR-100 可以接入。它与 CIFAR-10 类似：

- 共 60000 张 32×32 彩色图像。
- 100 个 fine classes。
- 每类 600 张。
- 每类 500 张训练图、100 张测试图。
- 100 个 fine classes 归属于 20 个 superclasses。
- 每张图有 fine label 和 coarse label。

### 架构理解

训练不能真正放在浏览器执行。正确方式是：

```text
Vue 前端负责交互
FastAPI 后端负责接收任务
Python/PyTorch/CUDA 执行数据处理和训练
SQLite/FAISS/文件系统保存结果
前端轮询或 WebSocket 显示进度
```

### 后续建议阶段

建议新增一个“实验流水线”页面，例如 `/pipeline` 或 `/experiments`：

- 数据集管理：
  - CIFAR-10。
  - CIFAR-100。
  - 上传本地压缩包。
  - 官方 URL 下载。
- 数据预处理：
  - 解压。
  - 转图片。
  - 写数据库。
  - 显示类别数、图片数。
- 模型训练：
  - 选择模型。
  - 设置 epoch、batch size、学习率、AMP。
  - 启动训练。
  - 显示日志和曲线。
- 索引构建：
  - 构建 deep。
  - 构建 all。
  - 显示进度。
- 自动评估：
  - mAP。
  - P@K。
  - PR 曲线。
  - 新旧模型对比。

### 待实现

- 后端任务系统。
- 前端任务中心。
- CIFAR-100 prepare 脚本。
- 数据集上传/下载接口。
- 训练任务 API。
- 训练日志持久化。
- 索引构建进度 API。
- 前端训练曲线展示。

---

## 当前系统状态小结

### 数据集

- CIFAR-10 已作为主数据集。
- 使用 train + test 全量 60000 张。
- 10 类，每类 6000 张。
- CIFAR-100 尚未实现，但可按同样方式扩展。

### 检索能力

已支持：

- HSV 直方图。
- 颜色矩。
- GLCM。
- LBP。
- Hu。
- EOH。
- 自训练 CNN deep 特征。
- 多特征融合。

### 前端页面

已支持：

- `/search`：上传图片检索、切换特征、切换度量、查看结果和直方图。
- `/gallery`：浏览图库、类别筛选、上传、删除、重建索引。
- `/evaluate`：mAP、P@K、PR 曲线和实验结论。

### 质量检查

已通过：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app scripts tests
.\.venv\Scripts\python.exe -m black --check app scripts tests
```

前端构建已通过：

```powershell
npm.cmd run build
```

### 主要遗留问题

- 前端暂未实现一站式数据集上传、预处理、训练、建索引流程。
- CIFAR-100 暂未接入。
- 训练任务暂时仍通过命令行启动。
- 索引构建和训练进度暂未通过 WebSocket 或任务接口实时展示。
- Element Plus `el-radio label as value` 有废弃警告，暂不影响功能。

---

## 2026-07-01：前端一站式实验流水线初版实现

### 目标

把原来依赖命令行执行的流程迁移到前端交互中，使用户可以通过网页完成：

```text
上传/下载数据集
  ↓
预处理并写入数据库
  ↓
训练 CNN 模型
  ↓
重建 deep/all 索引
  ↓
查看训练日志和评估结果
```

### 实现原则

- 浏览器只负责交互和展示。
- FastAPI 后端负责启动固定后台任务。
- 数据处理、训练、CUDA 推理和 FAISS 建库仍由 Python/PyTorch 执行。
- 当前版本采用“进程内任务表 + 后台线程 + Python 子进程”的本地实训实现，适合单机开发和答辩展示。
- 后续如果需要多用户或长期任务队列，可替换为 Celery、RQ 或数据库持久化任务表。

### 后端完成内容

新增后台任务系统：

- 每个任务有唯一 `task_id`。
- 任务状态包括：
  - `queued`
  - `running`
  - `succeeded`
  - `failed`
- 后台任务实时收集 stdout 日志。
- 训练任务可解析 JSON epoch 日志，提取：
  - epoch
  - train_loss
  - train_acc
  - val_loss
  - val_acc
  - best_acc
- 前端可轮询任务列表和单个任务详情。

新增 Pipeline API：

- `GET /api/pipeline/tasks`
- `GET /api/pipeline/tasks/{task_id}`
- `POST /api/pipeline/upload`
- `POST /api/pipeline/download`
- `POST /api/pipeline/prepare`
- `POST /api/pipeline/train`
- `POST /api/pipeline/index`
- `POST /api/pipeline/evaluate`

新增 CIFAR 通用预处理脚本：

- 支持 `cifar10`。
- 支持 `cifar100`。
- 支持 `split=train/test/all`。
- 支持 `per_class` 小样本参数。
- CIFAR-100 支持：
  - `fine` 100 类标签。
  - `coarse` 20 类超类标签。

扩展 CNN 训练脚本：

- 支持 `--dataset cifar10`。
- 支持 `--dataset cifar100`。
- 支持 CIFAR-100 fine/coarse 标签。
- 根据数据集使用不同 mean/std。
- 默认保存到系统 deep 提取器读取的 checkpoint 路径，训练后可直接重建索引。

改进 deep 特征提取器：

- 自动检测 checkpoint 更新时间。
- 如果前端训练产生了新模型，后端后续提取 deep 特征时可以自动重新加载新模型。
- 减少必须手动重启后端的情况。

### 前端完成内容

新增页面 `/pipeline`，导航名称为“实验流水线”。

页面包含四个主要操作区：

1. 数据集导入
   - 选择 CIFAR-10 / CIFAR-100。
   - 自动填充官方下载 URL。
   - 支持上传本地压缩包。
   - 上传后可自动解压并回填解压目录。

2. 数据预处理
   - 选择 `train/test/all`。
   - 设置每类数量。
   - CIFAR-100 可选择 fine 100 类或 coarse 20 类。
   - 点击后启动后台预处理任务。

3. 训练 CNN 模型
   - 设置 epoch。
   - 设置 batch size。
   - 设置学习率。
   - 设置 workers。
   - 勾选 AMP 混合精度。
   - 启动后在任务中心查看训练日志和 val_acc。

4. 索引与评估
   - 选择要重建的特征索引。
   - 支持 deep 或 all 传统特征。
   - 支持启动一次 `deep + cosine` 评估。

任务中心：

- 显示任务名称、类型、状态。
- 显示训练进度或评估指标。
- 点击任务行可查看任务日志。
- 每 2 秒自动刷新。

### 关键文件

后端：

- `backend/app/services/task_service.py`
- `backend/app/routers/pipeline.py`
- `backend/scripts/download_file.py`
- `backend/scripts/prepare_cifar_dataset.py`
- `backend/scripts/run_evaluate.py`
- `backend/scripts/train_cifar_cnn.py`
- `backend/app/features/deep.py`
- `backend/app/main.py`
- `backend/app/schemas.py`

前端：

- `frontend/src/views/PipelineView.vue`
- `frontend/src/api/cbir.js`
- `frontend/src/api/client.js`
- `frontend/src/router/index.js`
- `frontend/src/App.vue`

文档：

- `README.md`
- `PROJECT_LOG.md`

### 验收结果

后端：

```powershell
.\.venv\Scripts\python.exe -m ruff check app scripts tests
.\.venv\Scripts\python.exe -m black --check app scripts tests
.\.venv\Scripts\python.exe -m pytest
```

结果：

- ruff 通过。
- black check 通过。
- pytest 6 个测试全部通过。

前端：

```powershell
npm.cmd run build
```

结果：

- Vite production build 通过。
- 仍有已知 chunk size 警告和 VueUse PURE 注释警告，不影响运行。

API 注册检查：

- OpenAPI 中已包含 `/api/pipeline/tasks`。
- OpenAPI 中已包含 `/api/pipeline/upload`、`prepare`、`train`、`index`、`evaluate` 等接口。

### 当前限制

- 任务状态保存在后端进程内存中，重启后任务记录会丢失。
- 暂未实现任务取消。
- 暂未实现 WebSocket 推送，前端使用轮询刷新。
- 上传大文件时仍依赖浏览器和后端请求稳定性。
- 当前 deep checkpoint 是全局配置，若连续训练 CIFAR-10 和 CIFAR-100，需要重建对应数据集 deep 索引，避免模型和索引不一致。

### 后续可增强

- 增加任务取消按钮。
- 将任务记录持久化到 SQLite。
- 使用 WebSocket/SSE 实时推送日志。
- 支持 CIFAR-100 下载后自动解压并自动定位 `cifar-100-python` 目录。
- 在任务完成后自动刷新数据集列表。
- 在训练完成后自动触发 deep 索引重建。
- 在索引完成后自动触发评估并生成对比表。

---

## 2026-07-01：一键启动前后端脚本

### 目标

提供一个 PowerShell 脚本，让用户不用分别打开两个终端手动启动后端和前端。脚本需要：

- 先关闭已占用端口的旧前端/后端进程。
- 后台启动 FastAPI 后端。
- 后台启动 Vite 前端。
- 自动设置前端代理到后端 `8010`。
- 输出后端接口健康度。
- 输出前端访问地址。
- 保存运行日志和 PID 信息。

### 完成内容

新增脚本：

- `start_cbir.ps1`

脚本默认端口：

- 后端：`8010`
- 前端：`5173`

脚本启动流程：

```text
关闭 8010 / 5173 / 8000 端口上的旧进程
  ↓
关闭当前项目目录下的 uvicorn / vite 相关旧进程
  ↓
启动 backend/.venv/Scripts/python.exe -m uvicorn app.main:app
  ↓
启动 npm.cmd run dev
  ↓
等待 /api/health 和 /pipeline 就绪
  ↓
输出接口健康检查表
```

健康检查覆盖：

- `GET /api/health`
- `GET /openapi.json`
- `GET /api/datasets`
- `GET /api/datasets/cifar10/images`
- `GET /api/datasets/cifar10/categories`
- `GET /api/histogram`
- `GET /api/pipeline/tasks`
- `GET /api/evaluate`，可用 `-SkipEvaluateHealth` 跳过。

日志输出：

- `.runtime/logs/backend.out.log`
- `.runtime/logs/backend.err.log`
- `.runtime/logs/frontend.out.log`
- `.runtime/logs/frontend.err.log`

PID 文件：

- `.runtime/cbir-dev-pids.json`

### 使用命令

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system
.\start_cbir.ps1
```

跳过评估接口健康检查：

```powershell
.\start_cbir.ps1 -SkipEvaluateHealth
```

自定义端口：

```powershell
.\start_cbir.ps1 -BackendPort 8010 -FrontendPort 5173
```

### 验收结果

- PowerShell 脚本语法解析通过。
- README 已补充使用说明。
- 本次未直接执行完整脚本，避免打断用户当前浏览器中的运行服务。

### 2026-07-01 修复记录

用户在 Windows PowerShell 中直接执行 `.\start_cbir.ps1` 时遇到解析错误。原因是脚本中包含中文输出字符串和较复杂的前端内联启动命令，在用户当前 PowerShell 环境下被误解析。

修复内容：

- 将脚本运行输出改为 ASCII 文本，避免旧 PowerShell 编码误读。
- 将前端启动从 `powershell -Command "$env:..."` 改为 `cmd.exe /c "set VITE_API_TARGET=...&& npm.cmd run dev ..."`。
- 将带 `&` 的健康检查 URL 先保存到变量，再传入函数，避免命令解析歧义。
- 收紧旧进程关闭范围，只关闭指定前后端端口和当前项目目录下的相关进程。

复测结果：

- `start_cbir.ps1` 默认读取解析通过。
- `.\start_cbir.ps1 -SkipEvaluateHealth` 实际运行成功。
- `GET http://127.0.0.1:8010/api/health` 返回 `status=ok`，CUDA 为 RTX 4060。
- `GET http://localhost:5173/pipeline` 返回 HTTP 200。
- `.runtime/cbir-dev-pids.json` 正常记录后端和前端 PID。

---

## 2026-07-01：任务进度、取消按钮、评估页行为和明暗模式

### 目标

根据前端使用反馈继续优化交互：

- 任务中心增加进度条。
- 任务中心增加取消按钮。
- 评估页打开时不要自动评估，避免每次进入页面都触发耗时计算。
- 页面右上角增加白天/夜间模式切换按钮。

### 完成内容

任务系统：

- 后端任务管理器保存子进程句柄。
- 新增任务取消能力，运行中的任务会调用 subprocess terminate。
- 新增 API：
  - `POST /api/pipeline/tasks/{task_id}/cancel`
- 任务状态增加：
  - `cancelling`
  - `cancelled`
- 训练任务在 progress 中保存 `total_epochs`。
- 前端任务中心根据 `epoch / total_epochs` 计算进度百分比。
- 非训练任务运行中显示基础进度提示，完成/失败/取消后显示 100% 结束状态。
- 前端任务中心新增“取消”按钮，只有 `queued/running` 状态可点击。

评估页：

- 移除 `onMounted(runEvaluate)`。
- 用户进入 `/evaluate` 后不再自动计算。
- 只有点击“评估”按钮后才启动 mAP、P@K、PR 曲线计算。

明暗模式：

- 顶部右侧新增圆形图标按钮。
- 使用 Element Plus `Sunny/Moon` 图标。
- 引入 Element Plus 暗色变量。
- 使用 `html.dark` 切换主题。
- 主题选择保存到 `localStorage`。
- 基础背景、面板、边框、文字、表格和日志区域改为 CSS 变量。

### 关键文件

- `backend/app/services/task_service.py`
- `backend/app/routers/pipeline.py`
- `frontend/src/api/cbir.js`
- `frontend/src/views/PipelineView.vue`
- `frontend/src/views/EvaluateView.vue`
- `frontend/src/App.vue`
- `frontend/src/main.js`
- `frontend/src/styles.css`

### 验收结果

后端：

```powershell
.\.venv\Scripts\python.exe -m ruff check app scripts tests
.\.venv\Scripts\python.exe -m pytest
```

结果：

- ruff 通过。
- pytest 6 个测试全部通过。
- OpenAPI 确认 `/api/pipeline/tasks/{task_id}/cancel` 已注册。

前端：

```powershell
npm.cmd run build
```

结果：

- Vite production build 通过。
- 仍有已知 chunk size 和 VueUse PURE 注释警告，不影响运行。

### 备注

- 取消任务依赖子进程响应 terminate。大多数下载、训练、建索引任务可以停止；如果某些底层库正在执行不可中断操作，可能需要等待当前操作片段结束后才退出。
- 明暗模式当前覆盖了全局基础样式和主要 Element Plus 变量，局部组件若有硬编码颜色，后续可继续细化。

## 2026-07-01：任务中心重启残留与取消失败修复

### 背景

用户重启前端和后端后，发现上一次任务中心中的 CIFAR-100 下载任务仍显示为运行中；点击“取消”后连续弹出 `Not Found`。这会造成两个问题：

- 页面上看起来有旧任务一直存在，用户无法确认当前系统真实状态。
- 后端重启后内存任务表已丢失，前端仍尝试取消旧任务 ID，接口返回 404，交互体验不清晰。

### 问题分析

任务中心当前是后端进程内存态任务表：

- 后端重启后，旧任务 ID 不一定还存在。
- 旧的下载、训练、建索引等 Python 子进程可能没有被一键启动脚本完整关闭。
- 前端取消任务时没有专门处理 404，导致全局请求拦截器直接弹出 `Not Found`。
- 任务列表刷新时，如果原选中任务已不存在，前端仍保留旧选中项，容易形成“幽灵任务”的视觉残留。

### 完成内容

后端任务管理：

- `TaskManager` 新增 `clear(mode)`：
  - `finished`：清理已完成、失败、已取消任务。
  - `all`：终止正在运行的子进程，并清空任务中心。
- 清空任务后，如果后台子进程仍有日志回写，任务管理器会安全忽略，不再因为任务 ID 缺失产生异常。
- 取消排队任务时，如果还没有创建子进程，会直接标记为 `cancelled`。
- 后台线程启动前会检查任务是否已经被取消或清空，避免取消后又重新进入 running。

后端接口：

- 新增 API：
  - `DELETE /api/pipeline/tasks?mode=finished`
  - `DELETE /api/pipeline/tasks?mode=all`
  - `POST /api/pipeline/tasks/clear?mode=finished`
  - `POST /api/pipeline/tasks/clear?mode=all`
- 调整 `app.main` 的路由注册方式：当前 FastAPI 版本会以 `_IncludedRouter` 懒加载方式保存 `include_router`，新增路由在运行 OpenAPI 中未展开；改为显式展开各 APIRouter 的 routes，保证新增接口实际可访问。

前端任务中心：

- 增加“清空已结束”按钮，用于移除完成、失败、取消的任务记录。
- 增加“清空全部”按钮，用于取消运行中任务并清空任务中心。
- “清空全部”前增加确认弹窗，避免误点。
- 取消任务时若后端返回 404，不再弹全局 `Not Found`，改为提示“任务已经不在后端任务中心，已从页面移除”。
- 任务列表刷新后，如果当前选中任务不存在，会自动切换到最新任务或清空选中状态。

一键启动脚本：

- `start_cbir.ps1` 重启时除关闭 uvicorn/vite 外，也会尝试关闭以下后端任务子进程：
  - `scripts.download_file`
  - `scripts.prepare_cifar_dataset`
  - `scripts.train_cifar_cnn`
  - `scripts.build_index`
  - `scripts.run_evaluate`

### 关键文件

- `backend/app/services/task_service.py`
- `backend/app/routers/pipeline.py`
- `backend/app/main.py`
- `frontend/src/api/client.js`
- `frontend/src/api/cbir.js`
- `frontend/src/views/PipelineView.vue`
- `start_cbir.ps1`

### 验收建议

1. 运行 `.\start_cbir.ps1 -SkipEvaluateHealth` 重启系统。
2. 打开 `http://localhost:5173/pipeline`。
3. 点击任务中心“刷新”，确认任务列表为当前后端真实状态。
4. 若仍有历史任务，点击“清空全部”。
5. 再点击“刷新”，确认任务中心为空或只剩当前真实任务。

## 2026-07-01：前端视觉美化与轻量动画

### 背景

用户反馈当前系统前端“不太好看”，希望在不影响已有检索、图库、评估和实验流水线功能的前提下，提升整体视觉效果，并加入适量动画。

### 完成内容

整体视觉：

- 重做全局背景，从纯灰背景改为带轻微层次的工作台背景。
- 顶部导航栏改为半透明吸附式工具栏，增加阴影和模糊质感。
- 品牌区新增彩色方形标识，增强系统识别度。
- 页面最大宽度从 1180 调整到 1220，使图库、流水线和结果区更舒展。
- 统一面板样式：边框、阴影、圆角、hover 状态和明暗模式变量。

动画与交互反馈：

- 路由切换增加淡入和轻微位移动画。
- 页面内容和卡片增加入场动画。
- 面板 hover 时增加边框高亮和阴影变化。
- 按钮 hover 时增加轻微上浮和阴影反馈。
- 进度条宽度变化增加平滑过渡。
- 上传区域增加 hover 上浮和图标动效。
- 查询图片预览增加淡入缩放动画。
- 检索结果卡片和图库卡片增加图片放大、阴影和边框反馈。
- 阻塞弹窗增加流动进度线，提升“正在运行”的感知。

明暗模式：

- 重新整理浅色和暗色主题 CSS 变量。
- 表格、弹窗、下拉菜单、输入框、单选按钮、复选按钮补充暗色样式。
- 修复评估结论文字在暗色模式下使用硬编码灰色的问题。

### 关键文件

- `frontend/src/App.vue`
- `frontend/src/styles.css`
- `frontend/src/components/QueryPanel.vue`
- `frontend/src/components/ResultGrid.vue`
- `frontend/src/components/BlockingOverlay.vue`
- `frontend/src/views/GalleryView.vue`
- `frontend/src/views/EvaluateView.vue`

### 验收结果

前端构建：

```powershell
npm.cmd run build
```

结果：

- Vite production build 通过。
- 仍有 VueUse PURE 注释和 chunk size 提示，属于已有依赖/包体积提示，不影响运行。

浏览器检查：

- 使用本机 Chrome 对 `/search` 和 `/pipeline` 进行截图检查。
- 浅色模式布局正常，导航、面板、上传区、结果区无明显重叠。
- 暗色模式布局正常，文字和面板对比度可读。

### 备注

- 本次仅调整视觉和交互动效，没有改变检索、训练、评估、上传、索引构建等业务逻辑。
- 动效遵守 `prefers-reduced-motion`，系统开启减少动态效果时会自动缩短动画。

## 2026-07-03：M1 CLIP 文本搜图

### 背景

用户确定后续升级路线：

- M1：加入 CLIP 文本搜图。
- M2：加入 DINOv2 图像特征。
- M3：加入 Triplet Loss 度量学习训练。
- M4：加入重排序和相关反馈。

本次先完成 M1，使系统在原有“以图搜图”的基础上，扩展为“文本搜图”和“CLIP 图像语义检索”。

### 完成内容

后端 CLIP 特征：

- 新增 `app/features/clip.py`。
- 基于 `open_clip_torch` 实现 `CLIPFeature`。
- 支持图像编码：
  - 输入 OpenCV BGR 图像。
  - 转为 RGB PIL 图像。
  - 使用 OpenCLIP transform 预处理。
  - 输出 L2 归一化 embedding。
- 支持文本编码：
  - 输入自然语言文本。
  - 使用 OpenCLIP tokenizer。
  - 输出 L2 归一化 text embedding。
- 默认配置：
  - model：`ViT-B-32`
  - pretrained：`laion2b_s34b_b79k`
  - dim：`512`
  - batch_size：`64`

特征注册与配置：

- `app/features/base.py` 注册 `clip` 特征。
- `app/core/config.py` 增加 `features.clip` 配置。
- `backend/settings.yaml` 增加 CLIP 模型配置。
- `backend/requirements.txt` 增加 `open_clip_torch>=2.26`。

索引构建：

- `scripts/build_index.py` 支持 `clip`。
- `--features clip` 可单独构建 CLIP 索引。
- `--features all` 已包含 `clip`。
- CLIP 图像向量保存为：
  - `clip.npy`
  - `clip_ids.npy`
  - `clip.faiss`
- `clip.faiss` 使用 FAISS `IndexFlatIP`，适配 L2 归一化向量的余弦检索。

检索接口：

- `app/retrieval.py` 支持 `clip` 走 FAISS 余弦检索。
- `app/services/search_service.py` 新增 `search_text()`。
- `app/routers/search.py` 新增：
  - `POST /api/search/text`
- 文本检索返回结构复用 `SearchResponse`，前端结果展示无需额外适配。

前端搜索页：

- `frontend/src/api/cbir.js` 新增 `searchByText()`。
- `frontend/src/components/QueryPanel.vue` 新增“CLIP 文本搜图”输入框。
- 支持输入英文或中文描述，例如：
  - `a red airplane`
  - `一辆红色汽车`
- 回车或点击“搜图”按钮触发文本检索。
- 深度与综合特征区新增：
  - `CLIP 图像`
- `frontend/src/views/SearchView.vue` 支持文本检索结果展示，并在摘要区显示“CLIP 文本搜图”和当前文本查询。

其他页面联动：

- `frontend/src/views/PipelineView.vue` 的索引构建选项增加 `CLIP`。
- `frontend/src/views/GalleryView.vue` 的“重建索引”包含 `clip`。
- `frontend/src/views/EvaluateView.vue` 增加 `CLIP` 评估选项。
- 评估页选择 `deep` 或 `clip` 时自动切换到余弦相似度。
- `app/services/eval_service.py` 支持评估 `clip`。

### 当前依赖状态

尝试安装：

```powershell
.\.venv\Scripts\python.exe -m pip install open_clip_torch>=2.26
.\.venv\Scripts\python.exe -m pip install open_clip_torch>=2.26 --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

结果：

- 第一次失败：PyPI SSL 握手异常。
- 第二次失败：本机代理连接异常。
- 代码已做懒加载处理：未安装 `open_clip_torch` 时，传统检索、CNN 深度检索、图库、评估等已有功能不受影响；只有构建 CLIP 索引或文本搜图时会提示安装依赖。

### 验收结果

后端：

```powershell
.\.venv\Scripts\python.exe -m ruff check app scripts tests
.\.venv\Scripts\python.exe -m pytest
```

结果：

- ruff 通过。
- pytest 7 个测试全部通过。
- FastAPI app 路由确认包含：
  - `/api/search POST`
  - `/api/search/text POST`
- 特征注册确认包含 `clip`。
- `parse_features("clip")` 和 `parse_features("all")` 确认可用。

前端：

```powershell
npm.cmd run build
```

结果：

- Vite production build 通过。
- 仍有已有 VueUse PURE 注释和 chunk size 提示，不影响运行。

### 后续验收建议

依赖安装成功后，执行：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.build_index --dataset cifar10 --features clip
```

然后打开搜索页，在“CLIP 文本搜图”输入：

```text
a red car
an airplane
a dog
```

观察返回结果是否语义相关。

## 2026-07-01：CIFAR 低分辨率图片显示优化

### 背景

用户反馈图库中的 CIFAR-10 图片显示很糊。原因是 CIFAR-10/CIFAR-100 原始图片只有 `32x32` 像素，前端卡片将其放大到数百像素时，浏览器默认使用平滑插值，视觉上会像被模糊处理。

### 完成内容

后端：

- 检索结果 `Hit` schema 增加 `width` 和 `height` 字段。
- 检索命中结果返回图片原始宽高，便于前端判断低分辨率图片。

前端：

- 图库页面根据图片宽高判断是否为低分辨率图片。
- 检索结果卡片根据命中结果宽高判断是否为低分辨率图片。
- 第一版曾对 `<=64x64` 的小图启用 `image-rendering: pixelated/crisp-edges`，避免浏览器平滑放大导致模糊。
- 用户反馈像素放大后有马赛克感，因此改为在固定预览区域内按原始小尺寸居中显示。
- 保留上传高清图片的默认大图显示，不影响用户后续上传普通大图。

### 关键文件

- `backend/app/schemas.py`
- `backend/app/retrieval.py`
- `frontend/src/views/GalleryView.vue`
- `frontend/src/components/ResultGrid.vue`

### 验收结果

后端：

```powershell
.\.venv\Scripts\python.exe -m ruff check app scripts tests
.\.venv\Scripts\python.exe -m pytest
```

结果：

- ruff 通过。
- pytest 6 个测试全部通过。

前端：

```powershell
npm.cmd run build
```

结果：

- Vite production build 通过。

### 备注

- 该优化不会把 `32x32` CIFAR 原图变成高清图。
- 最终显示策略是：CIFAR 小图不强行铺满卡片，而是在预览区域居中显示原始尺寸，避免“糊”和“马赛克放大”两种问题。

### 后续优化

- 图库工具栏新增显示方式切换：
  - `原始尺寸`：CIFAR 小图在预览区域居中显示，不放大。
  - `平滑放大`：小图铺满卡片，便于快速浏览类别轮廓。
- 显示方式保存到 `localStorage`，刷新页面后保留用户选择。

## 2026-07-01：检索特征分组与推荐相似度提示

### 背景

用户希望检索页面中将 6 种传统特征与深度/综合特征分开展示，并且在选择不同特征时提示更适合的相似度度量。

### 完成内容

检索面板：

- 将特征选择拆分为两个区域：
  - `传统特征`：HSV 直方图、颜色矩、GLCM、LBP、Hu、EOH。
  - `深度与综合`：深度特征、综合特征。
- 相似度下拉框中对当前特征推荐的度量增加“推荐”标记。
- 特征切换时自动切换到推荐相似度。
- 相似度选择下方增加推荐说明，解释为什么该特征适合该度量。
- 搜索页标题从“传统特征检索”调整为“图像特征检索”，以覆盖传统、深度和综合检索。

### 推荐规则

- HSV 直方图：推荐直方图相交。
- 颜色矩：推荐欧氏距离。
- GLCM：推荐欧氏距离。
- LBP：推荐直方图相交。
- Hu：推荐欧氏距离。
- EOH：推荐直方图相交。
- 深度特征：推荐余弦相似度。
- 综合特征：推荐加权距离。

### 关键文件

- `frontend/src/components/QueryPanel.vue`
- `frontend/src/views/SearchView.vue`

### 验收结果

前端：

```powershell
npm.cmd run build
```

结果：

- Vite production build 通过。

## 2026-07-01：前端 Pages/Vercel + 后端 VPS 部署适配

### 背景

用户计划采用实际生产部署方式：

- 前端部署到 Cloudflare Pages、Vercel 或 Netlify。
- 后端部署到国外 VPS。
- 数据集、模型、索引和数据库存储在 VPS 磁盘上。
- 同时要求原来的本地开发和验收流程继续可用。

### 完成内容

前端：

- `frontend/src/api/client.js` 的 API 地址改为环境变量优先：
  - 有 `VITE_API_BASE_URL` 时使用线上后端。
  - 没有配置时仍使用 `/api`。
- 本地开发仍然通过 Vite proxy 访问后端，不影响原来的 `start_cbir.ps1` 流程。
- Pages/Vercel 部署时只需要配置：
  - `VITE_API_BASE_URL=https://api.example.com/api`

后端：

- `settings.yaml` 增加：
  - `app.public_base_url`
  - `app.cors_origins`
- `main.py` 的 CORS 放行来源改为读取配置。
- 新增 `app/services/url_service.py`，统一生成静态资源 URL。
- 图库列表和检索结果中的图片 URL 改为：
  - 本地：`/static/...`
  - 线上：`https://api.example.com/static/...`
- 这样前后端分域部署时，图片不会错误请求到前端域名。

部署文档：

- 新增 `DEPLOYMENT.md`。
- 文档包含：
  - 本地流程说明。
  - 域名规划。
  - VPS 后端部署。
  - systemd 后台服务。
  - Nginx 反向代理。
  - HTTPS 证书。
  - Cloudflare Pages 配置。
  - Vercel 配置。
  - 线上验收步骤。

### 关键文件

- `frontend/src/api/client.js`
- `backend/app/core/config.py`
- `backend/settings.yaml`
- `backend/app/main.py`
- `backend/app/services/url_service.py`
- `backend/app/services/dataset_service.py`
- `backend/app/retrieval.py`
- `DEPLOYMENT.md`

### 验收结果

后端：

```powershell
.\.venv\Scripts\python.exe -m ruff check app scripts tests
.\.venv\Scripts\python.exe -m pytest
```

结果：

- ruff 通过。
- pytest 6 个测试全部通过。

前端：

```powershell
npm.cmd run build
```

结果：

- Vite production build 通过。
- 仍有已知 chunk size 和 VueUse PURE 注释警告，不影响运行。

### 保留的本地行为

不配置 `VITE_API_BASE_URL` 时，前端仍请求 `/api`。

`backend/settings.yaml` 中 `public_base_url` 默认为空时，图片 URL 仍返回 `/static/...`。

因此本地原流程继续有效。

## 2026-07-01：修复深度特征相似度选择被忽略

### 背景

用户在检索页面发现：选择“深度特征”时，无论切换余弦、欧氏距离、直方图相交还是加权距离，返回结果都完全一样。

排查后确认后端存在两个固定分支：

- `Retriever.search_single()` 中只要 `feature == "deep"` 就直接调用 FAISS 内积索引。
- `evaluate.py` 中评估 deep 特征时也强制把度量改成 `cosine`。

因此前端传入的 `metric` 参数虽然进入 API，但深度特征实际始终按余弦相似度执行。

### 完成内容

后端检索逻辑：

- deep + 余弦相似度：继续使用 FAISS `IndexFlatIP`，保持最快检索速度。
- deep + 非余弦度量：改为读取 `deep.npy` 特征矩阵，并按用户选择的度量重新计算分数。
- deep 不再被 `intersection` 自动改回 `cosine`。
- 综合检索中 deep 分支也不再强制改回 `cosine`，而是尊重当前融合检索选择的度量。

相似度实现：

- 单特征 `weighted` 不再等同普通欧氏距离。
- 新增基于索引矩阵维度方差的稳定权重：
  - 先按维度标准差生成反比权重。
  - 再归一化到均值约为 1。
  - 最后裁剪到 `[0.1, 10.0]`，避免极端维度支配结果。

评估逻辑：

- 移除 deep 评估时强制使用 `cosine` 的逻辑。
- 评估页面后续选择 deep + 非余弦度量时，也会按实际选择的度量计算。

测试：

- 新增 `test_deep_non_cosine_metric_uses_matrix_scoring`。
- 测试只创建 `deep.npy` 和 `deep_ids.npy`，不创建 `deep.faiss`。
- 使用 deep + `intersection` 检索能正常返回结果，证明非余弦 deep 检索不再依赖 FAISS 固定内积路径。

### 需要说明

深度特征在提取时已经做了 L2 归一化。因此：

- 余弦相似度和欧氏距离在数学上通常会得到相同或非常接近的排序。
- 加权距离和直方图相交现在会走不同计算路径，结果会更容易和余弦区分。
- 实际论文/系统报告中，deep 特征仍建议默认使用余弦相似度。

### 关键文件

- `backend/app/retrieval.py`
- `backend/app/evaluate.py`
- `backend/tests/test_retrieval.py`

### 验收方式

后端：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m ruff check app scripts tests
.\.venv\Scripts\python.exe -m pytest
```

前端手动验收：

- 重启后端。
- 打开 `http://localhost:5173/search`。
- 选择“深度特征”。
- 分别切换余弦、直方图相交、加权距离执行检索。
- 观察返回分数和排序是否随度量变化。

---

## 2026-07-03：升级路线 M1 - CLIP 文本搜图与 CLIP 索引

### 背景

用户确定新的扩展路线：

- M1：加入 CLIP 文本搜图。
- M2：加入 DINOv2 图像特征。
- M3：加入 Triplet Loss 度量学习训练。
- M4：加入重排序和相关反馈。

本阶段先完成 M1，让系统支持“输入一句文字，检索 CIFAR-10 图库中语义相近的图片”。

### 完成内容

后端：

- 新增 CLIP/OpenCLIP 特征提取器 `app/features/clip.py`。
- 使用 `open_clip_torch` 加载 `ViT-B-32 + openai` 权重。
- 支持两类特征：
  - 图像向量：`extract_batch(imgs_bgr)`。
  - 文本向量：`extract_text(text)`。
- 图像和文本特征均做 L2 归一化，统一进入 512 维 CLIP 语义空间。
- `build_index.py` 支持 `--features clip`，并在 `all` 中包含 CLIP。
- CLIP 图像索引用 FAISS `IndexFlatIP` 构建，归一化后内积等价于余弦相似度。
- 新增文本检索接口：`POST /api/search/text`。
- 检索服务 `search_text()` 使用文本向量查询 `clip.faiss`，返回 Top-K 图片。
- 评估模块支持选择 `clip` 特征。

前端：

- `/search` 页面新增 `CLIP 文本搜图` 输入框。
- 用户可以直接输入英文描述，例如：
  - `an airplane`
  - `a dog`
  - `a red car`
- 高级检索特征中新增 `CLIP 图像`，推荐相似度为余弦。
- `/pipeline` 页面构建索引时可勾选 `CLIP`。
- `/evaluate` 页面可选择 `CLIP` 进行评估。
- `/gallery` 的索引重建特征列表加入 `clip`。

### 性能优化

最初 CLIP 图像索引使用 OpenCLIP 自带 PIL preprocess，速度较慢。

随后改为批量张量预处理：

- OpenCV 将 BGR 转 RGB。
- 批量 resize 到 `224x224`。
- `numpy.stack` 组成批量数组。
- 一次性转换为 PyTorch tensor。
- 使用 CLIP mean/std 批量归一化。
- 在 CUDA 上批量执行 `model.encode_image()`。

优化后，模型加载完成后的 64 张图片批处理约为 `0.25s`，适合全量 60000 张 CIFAR-10 构建索引。

### 关键文件

- `backend/app/features/clip.py`
- `backend/app/features/base.py`
- `backend/app/services/search_service.py`
- `backend/app/routers/search.py`
- `backend/app/retrieval.py`
- `backend/app/services/eval_service.py`
- `backend/scripts/build_index.py`
- `backend/settings.yaml`
- `backend/requirements.txt`
- `frontend/src/api/cbir.js`
- `frontend/src/components/QueryPanel.vue`
- `frontend/src/views/SearchView.vue`
- `frontend/src/views/PipelineView.vue`
- `frontend/src/views/EvaluateView.vue`
- `frontend/src/views/GalleryView.vue`

### 依赖安装

默认 PyPI 下载 `open_clip_torch` 时遇到 SSL/代理问题，最终使用清华镜像安装成功：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m pip install "open_clip_torch>=2.26" -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

安装结果：

- `open_clip_torch 3.3.0`
- CLIP 文本向量维度：`512`
- 文本向量 L2 norm 约为 `1.0`

### CLIP 索引构建结果

构建命令：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.build_index --dataset cifar10 --features clip
```

构建对象：

- 数据集：`cifar10`
- 图片数量：`60000`
- 批大小：`64`
- 批次数：`938`
- CLIP 维度：`512`
- 构建耗时：约 `6分48秒`

生成文件：

- `data/datasets/cifar10/index/clip.npy`
- `data/datasets/cifar10/index/clip_ids.npy`
- `data/datasets/cifar10/index/clip.faiss`

索引元数据：

```json
"clip": {
  "dim": 512,
  "count": 60000
}
```

### 验证结果

代码检查：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m ruff check app scripts tests
```

结果：

- ruff 通过。

前端构建：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm.cmd run build
```

结果：

- Vite production build 通过。
- 仍有已知 chunk size 和 VueUse PURE 注释警告，不影响运行。

文本检索验收：

- 查询文本：`an airplane`
- Top-5 返回结果全部为 `airplane` 类别。
- 代表结果：
  - `airplane_0439.jpg`
  - `airplane_1745.jpg`
  - `airplane_2353.jpg`
  - `airplane_4346.jpg`
  - `airplane_4979.jpg`

### 注意事项

- 后端重启后的第一次 CLIP 查询需要加载 PyTorch、CLIP 模型和 FAISS 索引，冷启动会明显慢一些。
- 模型和索引加载到进程缓存后，后续查询会明显变快。
- 2026-07-03 收尾验证时，当前 Windows 会话中最小 `import torch` 诊断出现长时间卡住，判断为本机 PyTorch/CUDA 运行时状态问题，不是 CLIP 索引或接口逻辑问题；已清理诊断残留进程。
- 若再次遇到第一次查询长时间不返回，建议重启后端，必要时重启当前终端或电脑后再验收 CUDA/PyTorch。

### 前端验收方式

1. 启动后端和前端。
2. 打开 `http://localhost:5173/search`。
3. 在 `CLIP 文本搜图` 输入框输入 `an airplane`。
4. 点击 `搜图`。
5. 观察结果中是否优先出现飞机类别图片。
6. 再测试 `a dog`、`a red car`、`a ship` 等文本，观察语义检索效果。

---

## 2026-07-03：M1 补充 - 中文文本转英文后进行 CLIP 搜图

### 背景

用户指出当前 `ViT-B-32 + openai` 版 CLIP 对英文文本效果更好，对中文文本搜图不稳定。

为快速完成 M1 验收，采用轻量方案：

前端输入中文
→ 后端规则翻译为英文短语
→ 使用现有 CLIP 文本编码器检索 `clip.faiss`
→ 前端显示原始文本和实际 CLIP 英文检索词。

### 完成内容

后端：

- 新增 `app/services/text_translation.py`。
- 支持识别常见中文颜色：
  - 红、蓝、绿、黄、黑、白、灰、棕、橙、紫。
- 支持识别 CIFAR-10 常见中文类别：
  - 飞机、汽车、鸟、猫、鹿、狗、青蛙、马、船、卡车。
- 支持少量修饰词：
  - 小、大、可爱、漂亮、模糊、清晰。
- `search_text()` 在调用 CLIP 前先执行 `rewrite_clip_query()`。
- `SearchResponse.query` 返回：
  - `text`：用户原始输入。
  - `clip_text`：实际送入 CLIP 的英文检索词。
  - `translated`：是否发生中文重写。

示例：

- `红色汽车` → `red car`
- `一只可爱的小狗` → `small cute dog`
- `蓝色飞机` → `blue airplane`
- `黄色卡车` → `yellow truck`

前端：

- `/search` 页面文本输入框提示改为 `红色汽车 / a red car`。
- 文本检索后，摘要区域显示：
  - 原始文本查询。
  - CLIP 英文检索词。

### 关键文件

- `backend/app/services/text_translation.py`
- `backend/app/services/search_service.py`
- `backend/app/schemas.py`
- `backend/tests/test_text_translation.py`
- `frontend/src/views/SearchView.vue`
- `frontend/src/components/QueryPanel.vue`

### 验收结果

后端静态检查：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m ruff check app scripts tests
```

结果：

- 通过。

中文重写单元测试：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m pytest tests\test_text_translation.py
```

结果：

- 3 个测试全部通过。

前端构建：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm.cmd run build
```

结果：

- Vite production build 通过。
- 仍有已知 VueUse PURE 注释和 chunk size 提醒，不影响运行。

### 2026-07-03 补充：视频检索结果展示调整

用户用飞机截图进行 deep 视频检索时，结果中除了飞机视频，也出现了汽车、狗、猫等其他视频。原因是当前视频检索按关键帧特征相似度返回 Top-K，并不会天然做类别过滤；deep 特征会同时受到主体、背景、颜色、构图等因素影响，因此非同类视频也可能作为低排名候选出现。

本次调整：

- 前端视频检索请求从 `Top-6` 改为 `Top-4`。
- 检索结果展示方式改为：
  - 1 个“最佳匹配”。
  - 3 个“候选结果”。
- 最佳匹配使用更大的卡片突出显示。
- 候选结果保留为辅助判断，不再和第一名呈现为同等权重。

关键文件：

- `frontend/src/views/VideoView.vue`

验收结果：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm.cmd run build
```

结果：

- 前端构建通过。

### 2026-07-03 补充：最佳匹配排版与相似度百分比

用户反馈视频检索“最佳匹配”卡片排版不够稳定，右侧视频区域过大，同时 `score 0.9858` 不够直观。

本次调整：

- 最佳匹配卡片改为：
  - 顶部信息栏。
  - 左侧匹配关键帧。
  - 右侧视频播放器。
- 限制最佳匹配媒体高度，避免视频播放器撑满屏幕。
- 将原始分数从小数改为百分比徽章：
  - `score 0.9858` → `相似度 98.58%`
- 候选结果也同步显示百分比相似度。
- 相似度徽章使用绿色强调色，突出可信度。

关键文件：

- `frontend/src/views/VideoView.vue`

验收结果：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm.cmd run build
```

结果：

- 前端构建通过。

### 前端验收方式

1. 重启后端和前端。
2. 打开 `http://localhost:5173/search`。
3. 在 `CLIP 文本搜图` 输入 `红色汽车`。
4. 点击 `搜图`。
5. 查看摘要是否显示 `CLIP 英文检索词：red car`。
6. 再测试 `蓝色飞机`、`一只小狗`、`黄色卡车`。

### 2026-07-03 补充：中文场景词增强

用户在前端输入 `傍晚在路上行驶的红色汽车` 后，系统最初只重写为 `red car`，丢失了“傍晚、路上、行驶”等场景信息。

本次补充：

- 增加动作词：
  - 行驶、开着、奔跑、飞行、航行、停放等。
- 增加位置词：
  - 路上、马路上、街道上、天空中、水上、草地上等。
- 增加时间词：
  - 傍晚、黄昏、晚上、白天、早晨、中午等。

现在示例重写结果：

- `傍晚在路上行驶的红色汽车` → `red car driving on the road at dusk`

新增测试：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m pytest tests\test_text_translation.py
```

结果：

- 4 个中文重写测试全部通过。

---

## 2026-07-03：升级路线 M3 - Triplet Loss 度量学习训练

### 背景

用户要求按照升级路线继续实现：

- M1：CLIP 文本搜图。
- M2：DINOv2 图像特征。
- M3：Triplet Loss 度量学习训练。
- M4：重排序和相关反馈。

本阶段完成 M3，让系统不只是训练分类 CNN，还可以用度量学习优化检索特征，使同类图片在特征空间中更近、异类图片更远。

### 方法说明

新增训练目标：

```text
总损失 = ce_weight * CrossEntropyLoss + triplet_weight * BatchHardTripletLoss
```

其中：

- CrossEntropyLoss：保持模型的分类判别能力。
- BatchHardTripletLoss：在一个 batch 内为每张图片寻找最难正样本和最难负样本。
- hardest positive：同类中距离最远的样本。
- hardest negative：异类中距离最近的样本。
- margin：要求负样本至少比正样本远一个间隔。

训练后的模型保存为：

```text
data/models/cifar_resnet18_metric.pt
```

deep 特征加载策略调整为：

1. 优先加载 `cifar_resnet18_metric.pt`。
2. 如果不存在，回退到 `cifar_resnet18.pt`。
3. 如果自训练模型都不存在，回退到 ImageNet ResNet50。

这样 Triplet 模型训练完成后，只需要重建 `deep` 索引，检索系统就会自动使用新的度量学习特征。

### 完成内容

后端：

- 新增 Triplet 训练脚本 `scripts/train_cifar_triplet.py`。
- 支持 CIFAR-10 / CIFAR-100。
- 支持 fine/coarse 标签。
- 支持 AMP 混合精度。
- 支持从已有 `cifar_resnet18.pt` 初始化骨干网络。
- 支持 CIFAR-100 时跳过分类头尺寸不匹配的权重，只加载兼容层。
- 每个 epoch 输出 JSON 日志：
  - `train_loss`
  - `ce_loss`
  - `triplet_loss`
  - `train_acc`
  - `val_acc`
  - `p_at_k`
- 新增 `TrainMetricModelRequest`。
- 新增接口 `POST /api/pipeline/train-metric`。
- `deep.py` 改为优先加载度量学习模型。

前端：

- `/pipeline` 的训练模块从“训练 CNN 模型”升级为“训练 CNN / Triplet 模型”。
- 新增训练目标切换：
  - 分类训练。
  - Triplet 度量学习。
- Triplet 模式下可设置：
  - `Triplet Margin`
  - `Triplet 权重`
  - `分类权重`
  - `Eval K`
- 任务中心训练进度支持显示 `P@K`。

### 关键文件

- `backend/scripts/train_cifar_triplet.py`
- `backend/app/features/deep.py`
- `backend/app/core/config.py`
- `backend/settings.yaml`
- `backend/app/schemas.py`
- `backend/app/routers/pipeline.py`
- `backend/tests/test_triplet_metric.py`
- `frontend/src/api/cbir.js`
- `frontend/src/views/PipelineView.vue`

### 验收命令

后端静态检查：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m ruff check app scripts tests
```

Triplet 单元测试：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m pytest tests\test_triplet_metric.py tests\test_text_translation.py
```

训练脚本帮助：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.train_cifar_triplet --help
```

前端构建：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm.cmd run build
```

### 验收结果

- ruff 通过。
- Triplet 与中文重写相关 6 个测试全部通过。
- `scripts.train_cifar_triplet --help` 正常显示参数。
- 前端 Vite production build 通过。
- 仍有已知 VueUse PURE 注释和 chunk size 提醒，不影响运行。

### 快速冒烟训练命令

如果只想确认训练链路能跑通，可以先跑 1 个 epoch：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.train_cifar_triplet --dataset cifar10 --src ..\data\raw\cifar-10-batches-py --epochs 1 --batch-size 128 --lr 0.01 --workers 2 --amp
```

正式训练建议：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.train_cifar_triplet --dataset cifar10 --src ..\data\raw\cifar-10-batches-py --epochs 40 --batch-size 128 --lr 0.01 --workers 2 --margin 0.2 --triplet-weight 1.0 --ce-weight 0.5 --amp
```

训练完成后重建 deep 索引：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.build_index --dataset cifar10 --features deep
```

然后在前端 `/evaluate` 重新评估 `deep + cosine`，与原模型的 mAP、P@K 对比。

---

## 2026-07-03：视频检索扩展 - 视频管理、关键帧、索引与以图搜视频

### 背景

用户提出在现有 CBIR 项目基础上扩展视频检索能力，路线为：

1. 视频管理页面：上传视频、显示视频列表、播放视频。
2. 视频关键帧抽取：用 OpenCV 每隔 N 秒抽帧，或用场景变化检测抽关键帧。
3. 视频索引：每个视频保存若干关键帧特征，复用现有 deep / HSV / LBP 特征。
4. 视频检索：上传图片或视频，返回相似视频。
5. 报告展示：展示关键帧、相似度、检索耗时、Top-K 结果。

本阶段先完成“以图搜视频”的最小闭环。

### 完成内容

后端数据模型：

- 新增 `videos` 表，保存上传视频元数据：
  - 文件名、路径、时长、fps、总帧数、关键帧数量。
- 新增 `video_keyframes` 表，保存关键帧：
  - 所属视频、帧号、时间戳、图片路径、宽高。

后端服务：

- 新增 `app/services/video_service.py`。
- 支持上传视频并保存到：
  - `data/videos/files/`
- 支持 OpenCV 固定间隔抽帧，关键帧保存到：
  - `data/videos/keyframes/{video_id}/`
- 支持构建视频关键帧索引：
  - `data/videos/index/{feature}.npy`
  - `data/videos/index/{feature}_keyframe_ids.npy`
  - `data/videos/index/{feature}_video_ids.npy`
- 支持复用现有图像特征：
  - deep
  - HSV
  - 颜色矩
  - GLCM
  - LBP
  - Hu
  - EOH
- 支持上传图片检索相似视频：
  - 先用图片特征匹配所有关键帧。
  - 再按视频聚合，取每个视频的最高关键帧得分。
  - 返回 Top-K 相似视频。

后端接口：

- `GET /api/videos`
- `POST /api/videos`
- `DELETE /api/videos/{video_id}`
- `POST /api/videos/index`
- `POST /api/videos/search`

前端：

- 新增 `/videos` 视频检索页面。
- 导航栏新增“视频检索”入口。
- 页面功能包括：
  - 上传视频。
  - 设置关键帧间隔。
  - 设置最多关键帧数量。
  - 显示视频列表。
  - 视频在线播放。
  - 展示视频关键帧。
  - 选择视频索引特征。
  - 构建视频索引。
  - 上传查询图片。
  - 返回相似视频 Top-K。
  - 展示匹配关键帧、相似度、匹配时间点、检索耗时。

### 关键文件

- `backend/app/db/models.py`
- `backend/app/schemas.py`
- `backend/app/services/video_service.py`
- `backend/app/routers/videos.py`
- `backend/app/main.py`
- `frontend/src/api/cbir.js`
- `frontend/src/views/VideoView.vue`
- `frontend/src/router/index.js`
- `frontend/src/App.vue`

### 当前实现边界

- 已完成固定间隔抽关键帧。
- 暂未实现视频作为查询输入。
- 暂未实现基于场景变化的关键帧检测。
- 暂未实现专门的视频时序特征，当前是“关键帧级图像特征 + 视频级聚合”。
- deep 视频索引会加载深度模型，首次构建可能较慢；快速验收可先选择 HSV 直方图。

### 验收命令

后端静态检查：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m ruff check app scripts tests
```

后端路由检查：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -c "from app.main import app; print([getattr(r, 'path', '') for r in app.router.routes if '/api/videos' in getattr(r, 'path', '')])"
```

前端构建：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm.cmd run build
```

### 验收结果

- ruff 通过。
- `/api/videos` 相关路由加载成功。
- 前端 Vite production build 通过。
- 仍有已知 VueUse PURE 注释和 chunk size 提醒，不影响运行。

### 前端验收流程

1. 重启后端和前端。
2. 打开 `http://localhost:5173/videos`。
3. 上传一个短视频。
4. 等待关键帧抽取完成。
5. 选择 `HSV 直方图`，点击“构建视频索引”。
6. 上传一张查询图片。
7. 点击“搜视频”。
8. 查看 Top-K 视频结果、匹配关键帧、相似度、匹配时间点和检索耗时。

### 2026-07-03 补充：扫描本地文件夹导入视频

用户希望可以不通过浏览器上传，而是直接把视频复制到本地文件夹，或通过网盘/同步盘把视频同步到项目目录，然后由系统扫描导入。

本次新增：

- 本地投放目录：

```text
C:\Users\wgq20\Documents\CBIR\cbir-system\data\videos\incoming
```

- 前端 `/videos` 页面新增“扫描导入本地视频”按钮。
- 后端新增接口：

```text
POST /api/videos/import-local
```

- 支持扫描的视频格式：
  - `.mp4`
  - `.mov`
  - `.avi`
  - `.mkv`
  - `.webm`
  - `.m4v`

导入流程：

```text
把视频复制到 data\videos\incoming
→ 前端点击“扫描导入本地视频”
→ 后端移动视频到 data\videos\files
→ 写入 videos 表
→ OpenCV 抽关键帧
→ 写入 video_keyframes 表
→ 清空旧视频索引，提示后续需要重新构建索引
```

### 验收结果

后端：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m ruff check app scripts tests
.\.venv\Scripts\python.exe -c "from app.main import app; print([getattr(r, 'path', '') for r in app.router.routes if '/api/videos' in getattr(r, 'path', '')])"
```

结果：

- ruff 通过。
- 路由列表包含 `/api/videos/import-local`。

前端：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm.cmd run build
```

结果：

- Vite production build 通过。
- 仍有已知 VueUse PURE 注释和 chunk size 提醒，不影响运行。
