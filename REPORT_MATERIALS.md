# CBIR 实训报告素材

## 系统功能截图

1. 检索页 `/search`：选择 CIFAR-10，上传或从库内选择图片，展示 Top-12、类别标签、相似度分数、HSV/灰度直方图。
2. 图库页 `/gallery`：展示分页图库、类别筛选、上传、删除、重建索引。
3. 评估页 `/evaluate`：展示 mAP、P@K、PR 曲线和自动结论。
4. API 文档 `/docs`：展示 FastAPI 自动接口文档。

## 实验表格模板

| 特征 | 度量 | Sample | mAP | P@12 | 备注 |
|---|---|---:|---:|---:|---|
| HSV 直方图 | intersection | 100 |  |  | 颜色基线 |
| GLCM | cosine | 100 |  |  | 纹理特征 |
| Hu 不变矩 | cosine | 100 |  |  | 形状特征 |
| ResNet50 | cosine | 100 |  |  | 深度特征 |
| 综合融合 | cosine | 100 |  |  | 前端检索展示 |

## 算法描述提纲

- 图像预处理：统一尺寸、可选中值/高斯降噪、灰度化。
- 颜色检索：HSV 三维直方图与颜色矩。
- 纹理检索：GLCM 和 LBP。
- 形状检索：Hu 不变矩和 EOH。
- 深度检索：ResNet50 2048 维特征，L2 归一化，FAISS 内积检索。
- 综合检索：多特征相似度归一化后按权重加权。
- 评价指标：Precision@K、Average Precision、mAP、PR 曲线。

## 验收命令

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\backend
.\.venv\Scripts\python.exe -m scripts.verify_cuda
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app scripts tests
.\.venv\Scripts\python.exe -m black --check app scripts tests
```

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system\frontend
npm run build
```
