"""Build feature indexes for prepared datasets."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session
from tqdm import tqdm

from app.core.config import get_settings
from app.db import crud
from app.db.database import SessionLocal, init_db
from app.features.base import get_extractor
from app.preprocess import load_image
from app.services.dataset_service import load_registry

TRADITIONAL_FEATURES = {"color_hist", "color_moments", "glcm", "lbp", "hu", "eoh"}
DEEP_FEATURES = {"deep", "deep_cnn", "deep_triplet", "clip", "dinov2"}
ALL_FEATURES = TRADITIONAL_FEATURES | DEEP_FEATURES
STANDARDIZED_FEATURES = {"color_moments", "glcm", "hu"}


def parse_features(value: str) -> list[str]:
    """Parse --features into a concrete feature list."""

    if value == "all":
        return [
            "color_hist",
            "color_moments",
            "glcm",
            "lbp",
            "hu",
            "eoh",
            "deep_cnn",
            "deep_triplet",
            "clip",
            "dinov2",
        ]
    features = [item.strip() for item in value.split(",") if item.strip()]
    unknown = set(features) - ALL_FEATURES
    if unknown:
        raise ValueError(
            f"当前支持特征: {sorted(ALL_FEATURES)}，收到: {sorted(unknown)}"
        )
    return features


def _dataset_index_dir(dataset: str) -> Path:
    registry = load_registry()
    if dataset not in registry:
        raise KeyError(f"数据集未注册: {dataset}")
    index_dir = get_settings().data_root_path / str(registry[dataset]["index_dir"])
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir


def _dataset_images(db: Session, dataset: str) -> list[object]:
    images, _total = crud.list_images(db, dataset, page=1, size=100000)
    return images


def build_index(dataset: str, features: list[str]) -> dict[str, object]:
    """Extract selected features and save .npy indexes."""

    init_db()
    settings = get_settings()
    index_dir = _dataset_index_dir(dataset)
    meta_path = index_dir / "meta.json"
    meta: dict[str, object]
    if meta_path.exists():
        with meta_path.open("r", encoding="utf-8") as file:
            meta = dict(json.load(file))
    else:
        meta = {"dataset": dataset}
    meta["generated_at"] = datetime.now(timezone.utc).isoformat()

    with SessionLocal() as db:
        images = _dataset_images(db, dataset)
        if not images:
            raise RuntimeError(
                f"数据集 {dataset} 还没有图像，请先运行对应的 prepare 脚本"
            )

        for feature in features:
            if feature in DEEP_FEATURES:
                matrix, ids = _extract_batch_feature(
                    settings.data_root_path,
                    images,
                    feature,
                    batch_size=_batch_size(feature),
                )
            else:
                matrix, ids = _extract_traditional(
                    settings.data_root_path, images, feature
                )
            feature_meta = _save_feature(index_dir, feature, matrix, ids)
            meta[feature] = feature_meta
            if feature in DEEP_FEATURES:
                _save_faiss(index_dir, feature, matrix)

    with (index_dir / "meta.json").open("w", encoding="utf-8") as file:
        json.dump(meta, file, ensure_ascii=False, indent=2)
    return meta


def _extract_traditional(
    data_root: Path, images: list[object], feature: str
) -> tuple[np.ndarray, np.ndarray]:
    """Extract one traditional feature for all images."""

    extractor = get_extractor(feature)
    vectors: list[np.ndarray] = []
    ids: list[int] = []
    for image in tqdm(images, desc=f"build {feature}"):
        img_bgr = load_image(data_root / image.path)
        # 每种传统特征逐图提取，行号与 image_id 通过 ids 文件一一对齐。
        vectors.append(extractor.extract(img_bgr))
        ids.append(int(image.id))
    return np.vstack(vectors).astype(np.float32), np.asarray(ids, dtype=np.int64)


def _extract_batch_feature(
    data_root: Path, images: list[object], feature: str, batch_size: int
) -> tuple[np.ndarray, np.ndarray]:
    """Extract batch-capable deep features for all images."""

    extractor = get_extractor(feature)
    if not hasattr(extractor, "extract_batch"):
        raise RuntimeError(f"{feature} extractor 缺少 extract_batch")
    vectors: list[np.ndarray] = []
    ids: list[int] = []
    for start in tqdm(range(0, len(images), batch_size), desc=f"build {feature}"):
        batch_images = images[start : start + batch_size]
        imgs_bgr = [load_image(data_root / image.path) for image in batch_images]
        # 深度/多模态特征批处理可利用 GPU；无 CUDA 时自动落到 CPU。
        batch_vectors = extractor.extract_batch(imgs_bgr)
        vectors.append(batch_vectors)
        ids.extend(int(image.id) for image in batch_images)
    return np.vstack(vectors).astype(np.float32), np.asarray(ids, dtype=np.int64)


def _save_feature(
    index_dir: Path, feature: str, matrix: np.ndarray, ids: np.ndarray
) -> dict[str, object]:
    """Save feature matrix and aligned ids."""

    feature_meta: dict[str, object] = {
        "dim": int(matrix.shape[1]),
        "count": int(matrix.shape[0]),
    }
    output_matrix = matrix
    if feature in STANDARDIZED_FEATURES:
        mean = matrix.mean(axis=0)
        std = matrix.std(axis=0)
        std = np.where(std < 1e-6, 1.0, std)
        output_matrix = ((matrix - mean) / std).astype(np.float32)
        feature_meta["standardization"] = {
            "mean": mean.astype(float).tolist(),
            "std": std.astype(float).tolist(),
        }
    np.save(index_dir / f"{feature}.npy", output_matrix.astype(np.float32))
    np.save(index_dir / f"{feature}_ids.npy", ids.astype(np.int64))
    return feature_meta


def _batch_size(feature: str) -> int:
    """Return configured batch size for a deep feature."""

    if feature == "clip":
        return int(get_settings().features.clip.get("batch_size", 64))
    if feature == "dinov2":
        return int(get_settings().features.dinov2.get("batch_size", 32))
    return 32


def _save_faiss(index_dir: Path, feature: str, matrix: np.ndarray) -> None:
    """Save a FAISS IndexFlatIP for L2-normalized vectors."""

    import faiss

    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix.astype(np.float32))
    faiss.write_index(index, str(index_dir / f"{feature}.faiss"))


def main() -> None:
    """Command-line entry."""

    parser = argparse.ArgumentParser(description="Build CBIR feature indexes")
    parser.add_argument("--dataset", required=True, help="Dataset key, e.g. corel1000")
    parser.add_argument(
        "--features", default="all", help="all or comma-separated names"
    )
    parser.add_argument("--cnn-model", default="", help="Checkpoint for deep_cnn index")
    parser.add_argument(
        "--triplet-model", default="", help="Checkpoint for deep_triplet index"
    )
    args = parser.parse_args()
    if args.cnn_model:
        os.environ["CBIR_DEEP_CNN_CHECKPOINT"] = args.cnn_model
    if args.triplet_model:
        os.environ["CBIR_DEEP_TRIPLET_CHECKPOINT"] = args.triplet_model
    meta = build_index(args.dataset, parse_features(args.features))
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
