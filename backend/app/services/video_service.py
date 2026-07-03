"""Video upload, keyframe extraction, indexing, and retrieval."""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Video, VideoKeyframe
from app.features.base import get_extractor
from app.preprocess import decode_image_bytes, load_image
from app.schemas import (
    VideoImportResponse,
    VideoIndexResponse,
    VideoItem,
    VideoKeyframeItem,
    VideoListResponse,
    VideoSearchHit,
    VideoSearchResponse,
)
from app.services.url_service import static_url
from app.similarity import (
    cosine_sim,
    euclidean,
    histogram_intersection,
    to_similarity,
    weighted_euclidean,
)

VIDEO_FEATURES = {"color_hist", "color_moments", "glcm", "lbp", "hu", "eoh", "deep"}
VIDEO_METRICS = {"intersection", "cosine", "euclidean", "weighted"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def list_videos(db: Session, page: int = 1, size: int = 12) -> VideoListResponse:
    """List uploaded videos with a few preview keyframes."""

    total = db.scalar(select(func.count()).select_from(Video)) or 0
    stmt = (
        select(Video)
        .order_by(Video.id.desc())
        .offset(max(page - 1, 0) * size)
        .limit(size)
    )
    items = [_to_video_item(db, video, keyframe_limit=4) for video in db.scalars(stmt)]
    return VideoListResponse(items=items, total=int(total))


def save_video_upload(
    db: Session,
    *,
    file_obj,
    filename: str,
    interval_seconds: float = 2.0,
    max_keyframes: int = 60,
) -> VideoItem:
    """Save an uploaded video and extract keyframes."""

    settings = get_settings()
    video_dir = settings.data_root_path / "videos" / "files"
    video_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(filename or "video.mp4")
    target = _unique_path(video_dir / safe_name)
    with target.open("wb") as output:
        shutil.copyfileobj(file_obj, output)
    return import_video_file(
        db,
        source_path=target,
        interval_seconds=interval_seconds,
        max_keyframes=max_keyframes,
        move_into_library=False,
    )


def scan_incoming_videos(
    db: Session,
    *,
    interval_seconds: float = 2.0,
    max_keyframes: int = 60,
) -> VideoImportResponse:
    """Import every supported video found in data/videos/incoming."""

    incoming_dir = get_settings().data_root_path / "videos" / "incoming"
    incoming_dir.mkdir(parents=True, exist_ok=True)
    imported: list[VideoItem] = []
    skipped: list[str] = []
    for source in sorted(incoming_dir.iterdir()):
        if not source.is_file():
            continue
        if source.suffix.lower() not in VIDEO_EXTENSIONS:
            skipped.append(f"{source.name}: 不支持的格式")
            continue
        try:
            imported.append(
                import_video_file(
                    db,
                    source_path=source,
                    interval_seconds=interval_seconds,
                    max_keyframes=max_keyframes,
                    move_into_library=True,
                )
            )
        except ValueError as exc:
            skipped.append(f"{source.name}: {exc}")
    return VideoImportResponse(
        incoming_dir=str(incoming_dir),
        imported=imported,
        skipped=skipped,
    )


def import_video_file(
    db: Session,
    *,
    source_path: Path,
    interval_seconds: float = 2.0,
    max_keyframes: int = 60,
    move_into_library: bool = True,
) -> VideoItem:
    """Register a local video file, extract keyframes, and return metadata."""

    if interval_seconds <= 0:
        raise ValueError("抽帧间隔必须大于 0")
    if max_keyframes <= 0:
        raise ValueError("关键帧数量必须大于 0")

    settings = get_settings()
    video_dir = settings.data_root_path / "videos" / "files"
    video_dir.mkdir(parents=True, exist_ok=True)
    target = source_path
    if move_into_library:
        target = _unique_path(video_dir / _safe_filename(source_path.name))
        shutil.move(str(source_path), str(target))

    relative_video_path = _relative_data_path(target)
    video = Video(name=target.name, path=relative_video_path)
    db.add(video)
    db.commit()
    db.refresh(video)

    try:
        metadata, keyframes = extract_keyframes(
            video_id=video.id,
            video_path=target,
            interval_seconds=interval_seconds,
            max_keyframes=max_keyframes,
        )
    except Exception:
        db.delete(video)
        db.commit()
        if target.exists():
            target.unlink(missing_ok=True)
        raise

    video.duration = metadata["duration"]
    video.fps = metadata["fps"]
    video.frame_count = int(metadata["frame_count"])
    video.keyframe_count = len(keyframes)
    db.add_all(VideoKeyframe(video_id=video.id, **row) for row in keyframes)
    db.commit()
    db.refresh(video)
    _clear_video_indexes()
    return _to_video_item(db, video, keyframe_limit=8)


def extract_keyframes(
    *,
    video_id: int,
    video_path: Path,
    interval_seconds: float,
    max_keyframes: int,
) -> tuple[dict[str, float], list[dict[str, object]]]:
    """Extract video keyframes at a fixed time interval."""

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError("无法打开视频文件")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if fps <= 0:
        fps = 25.0
    duration = frame_count / fps if frame_count > 0 else 0.0
    step = max(int(round(fps * interval_seconds)), 1)

    settings = get_settings()
    keyframe_dir = settings.data_root_path / "videos" / "keyframes" / str(video_id)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    frame_index = 0
    saved = 0
    while saved < max_keyframes:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_index % step == 0:
            timestamp = frame_index / fps
            frame_path = keyframe_dir / f"frame_{saved:04d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            height, width = frame.shape[:2]
            rows.append(
                {
                    "frame_index": frame_index,
                    "timestamp": float(timestamp),
                    "path": _relative_data_path(frame_path),
                    "width": int(width),
                    "height": int(height),
                }
            )
            saved += 1
        frame_index += 1
    capture.release()
    if not rows:
        raise ValueError("未能从视频中抽取关键帧")
    return {"duration": duration, "fps": fps, "frame_count": frame_count}, rows


def build_video_index(db: Session, feature: str = "deep") -> VideoIndexResponse:
    """Build a keyframe feature index for uploaded videos."""

    if feature not in VIDEO_FEATURES:
        raise ValueError(f"不支持视频特征: {feature}")
    keyframes = list(db.scalars(select(VideoKeyframe).order_by(VideoKeyframe.id.asc())))
    if not keyframes:
        raise ValueError("暂无视频关键帧，请先上传视频")

    extractor = get_extractor(feature)
    images = [load_image(get_settings().data_root_path / frame.path) for frame in keyframes]
    if hasattr(extractor, "extract_batch"):
        matrix = extractor.extract_batch(images)  # type: ignore[attr-defined]
    else:
        matrix = np.vstack([extractor.extract(image) for image in images])
    matrix = matrix.astype(np.float32)
    index_dir = _video_index_dir()
    index_dir.mkdir(parents=True, exist_ok=True)
    np.save(index_dir / f"{feature}.npy", matrix)
    np.save(index_dir / f"{feature}_keyframe_ids.npy", np.asarray([f.id for f in keyframes]))
    np.save(index_dir / f"{feature}_video_ids.npy", np.asarray([f.video_id for f in keyframes]))
    with (index_dir / "meta.json").open("w", encoding="utf-8") as file:
        json.dump(
            {
                "feature": feature,
                "count": int(matrix.shape[0]),
                "dim": int(matrix.shape[1]) if matrix.ndim == 2 else 0,
                "videos": int(db.scalar(select(func.count()).select_from(Video)) or 0),
                "generated_at": time.time(),
            },
            file,
            ensure_ascii=False,
            indent=2,
        )
    return VideoIndexResponse(
        feature=feature,
        count=int(matrix.shape[0]),
        videos=int(db.scalar(select(func.count()).select_from(Video)) or 0),
    )


def search_videos_by_image(
    db: Session,
    *,
    file_bytes: bytes,
    feature: str = "deep",
    metric: str = "cosine",
    top_k: int = 6,
) -> VideoSearchResponse:
    """Search uploaded videos with an image query."""

    if feature not in VIDEO_FEATURES:
        raise ValueError(f"不支持视频特征: {feature}")
    if metric not in VIDEO_METRICS:
        raise ValueError(f"不支持视频度量: {metric}")
    start = time.perf_counter()
    img_bgr = decode_image_bytes(file_bytes)
    query = get_extractor(feature).extract(img_bgr).astype(np.float32)
    matrix, keyframe_ids, video_ids = _load_video_index(feature)
    scores = _score(query, matrix, _effective_metric(feature, metric))
    best: dict[int, tuple[float, int]] = {}
    for score, keyframe_id, video_id in zip(scores, keyframe_ids, video_ids):
        current = best.get(int(video_id))
        if current is None or float(score) > current[0]:
            best[int(video_id)] = (float(score), int(keyframe_id))
    ranked = sorted(best.items(), key=lambda item: item[1][0], reverse=True)[:top_k]
    hits = [_to_video_hit(db, video_id, score, keyframe_id) for video_id, (score, keyframe_id) in ranked]
    return VideoSearchResponse(
        query={"feature": feature, "metric": metric, "top_k": top_k},
        hits=[hit for hit in hits if hit is not None],
        elapsed_ms=(time.perf_counter() - start) * 1000,
    )


def delete_video(db: Session, video_id: int) -> bool:
    """Delete one video, keyframes, and stale index files."""

    video = db.get(Video, video_id)
    if video is None:
        return False
    settings = get_settings()
    (settings.data_root_path / video.path).unlink(missing_ok=True)
    keyframe_dir = settings.data_root_path / "videos" / "keyframes" / str(video_id)
    shutil.rmtree(keyframe_dir, ignore_errors=True)
    db.execute(delete(VideoKeyframe).where(VideoKeyframe.video_id == video_id))
    db.delete(video)
    db.commit()
    _clear_video_indexes()
    return True


def _to_video_item(db: Session, video: Video, keyframe_limit: int = 4) -> VideoItem:
    keyframes = list(
        db.scalars(
            select(VideoKeyframe)
            .where(VideoKeyframe.video_id == video.id)
            .order_by(VideoKeyframe.frame_index.asc())
            .limit(keyframe_limit)
        )
    )
    return VideoItem(
        id=video.id,
        name=video.name,
        path=video.path,
        url=static_url(video.path),
        duration=float(video.duration),
        fps=float(video.fps),
        frame_count=int(video.frame_count),
        keyframe_count=int(video.keyframe_count),
        keyframes=[_to_keyframe_item(frame) for frame in keyframes],
    )


def _to_keyframe_item(frame: VideoKeyframe) -> VideoKeyframeItem:
    return VideoKeyframeItem(
        id=frame.id,
        video_id=frame.video_id,
        frame_index=frame.frame_index,
        timestamp=float(frame.timestamp),
        path=frame.path,
        url=static_url(frame.path),
        width=frame.width,
        height=frame.height,
    )


def _to_video_hit(
    db: Session, video_id: int, score: float, keyframe_id: int
) -> VideoSearchHit | None:
    video = db.get(Video, video_id)
    keyframe = db.get(VideoKeyframe, keyframe_id)
    if video is None:
        return None
    return VideoSearchHit(
        video_id=video.id,
        name=video.name,
        url=static_url(video.path),
        score=score,
        duration=float(video.duration),
        keyframe_id=keyframe.id if keyframe is not None else None,
        keyframe_url=static_url(keyframe.path) if keyframe is not None else "",
        timestamp=float(keyframe.timestamp) if keyframe is not None else None,
    )


def _load_video_index(feature: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    index_dir = _video_index_dir()
    matrix_path = index_dir / f"{feature}.npy"
    keyframe_ids_path = index_dir / f"{feature}_keyframe_ids.npy"
    video_ids_path = index_dir / f"{feature}_video_ids.npy"
    if not matrix_path.exists() or not keyframe_ids_path.exists() or not video_ids_path.exists():
        raise FileNotFoundError(f"视频索引不存在，请先构建 {feature} 索引")
    return (
        np.load(matrix_path).astype(np.float32),
        np.load(keyframe_ids_path).astype(np.int64),
        np.load(video_ids_path).astype(np.int64),
    )


def _score(query_vec: np.ndarray, matrix: np.ndarray, metric: str) -> np.ndarray:
    if metric == "intersection":
        return histogram_intersection(query_vec, matrix)
    if metric == "cosine":
        return cosine_sim(query_vec, matrix)
    if metric == "euclidean":
        return to_similarity(euclidean(query_vec, matrix))
    if metric == "weighted":
        weights = 1.0 / np.maximum(matrix.std(axis=0), 1e-6)
        weights = np.clip(weights / max(float(weights.mean()), 1e-6), 0.1, 10.0)
        return to_similarity(weighted_euclidean(query_vec, matrix, weights))
    raise ValueError(f"不支持度量: {metric}")


def _effective_metric(feature: str, metric: str) -> str:
    if metric == "intersection" and feature not in {"color_hist", "lbp", "eoh"}:
        return "cosine"
    return metric


def _video_index_dir() -> Path:
    return get_settings().data_root_path / "videos" / "index"


def _clear_video_indexes() -> None:
    index_dir = _video_index_dir()
    if not index_dir.exists():
        return
    for path in index_dir.glob("*"):
        path.unlink(missing_ok=True)


def _relative_data_path(path: Path) -> str:
    return path.relative_to(get_settings().data_root_path).as_posix()


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem).strip("._") or "video"
    suffix = Path(name).suffix.lower() or ".mp4"
    return f"{stem}{suffix}"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 10000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("无法生成唯一视频文件名")
