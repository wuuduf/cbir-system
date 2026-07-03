"""Pydantic API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    """Dataset metadata returned by the API."""

    key: str
    display_name: str
    image_dir: str
    index_dir: str
    count: int = 0
    num_classes: int = 0


class ImageItem(BaseModel):
    """Image metadata returned by the API."""

    id: int
    dataset: str
    name: str
    path: str
    url: str
    category: str | None
    width: int
    height: int


class ImageListResponse(BaseModel):
    """Paginated image list."""

    items: list[ImageItem]
    total: int


class Hit(BaseModel):
    """One retrieval result."""

    image_id: int
    name: str
    path: str
    url: str = ""
    score: float
    category: str | None = None
    width: int | None = None
    height: int | None = None


class SearchResponse(BaseModel):
    """Search response with query info and ranked hits."""

    query: dict[str, str | int | float | bool | None]
    hits: list[Hit]
    elapsed_ms: float = Field(ge=0)


class EvalResponse(BaseModel):
    """Feature evaluation metrics."""

    map: float
    p_at_k: float
    pr_curve: list[tuple[float, float]]
    query_count: int = 0
    feature: str = ""
    metric: str = ""
    k: int = 12
    elapsed_ms: float = Field(default=0, ge=0)


class BuildIndexRequest(BaseModel):
    """Index build request."""

    dataset: str
    features: list[str]


class BuildIndexResponse(BaseModel):
    """Index build response."""

    dataset: str
    features: list[str]
    meta: dict[str, object]


class HistogramData(BaseModel):
    """Histogram chart data placeholder."""

    bins: list[str]
    values: list[float]


class TaskInfo(BaseModel):
    """Background task state for frontend polling."""

    id: str
    name: str
    kind: str
    status: str
    created_at: str
    updated_at: str
    command: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    progress: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] | None = None
    error: str | None = None
    returncode: int | None = None


class PrepareDatasetRequest(BaseModel):
    """Request to prepare an official CIFAR dataset directory."""

    dataset: str = Field(pattern="^(cifar10|cifar100)$")
    src: str
    split: str = Field(default="all", pattern="^(train|test|all)$")
    per_class: int | None = Field(default=None, ge=1)
    label_level: str = Field(default="fine", pattern="^(fine|coarse)$")


class TrainModelRequest(BaseModel):
    """Request to train a CIFAR CNN from the frontend."""

    dataset: str = Field(default="cifar10", pattern="^(cifar10|cifar100)$")
    src: str
    epochs: int = Field(default=80, ge=1, le=500)
    batch_size: int = Field(default=128, ge=16, le=1024)
    lr: float = Field(default=0.1, gt=0)
    weight_decay: float = Field(default=5e-4, ge=0)
    workers: int = Field(default=2, ge=0, le=16)
    amp: bool = True
    label_level: str = Field(default="fine", pattern="^(fine|coarse)$")


class TrainMetricModelRequest(TrainModelRequest):
    """Request to train a CIFAR metric-learning model from the frontend."""

    margin: float = Field(default=0.2, gt=0, le=2)
    triplet_weight: float = Field(default=1.0, ge=0, le=10)
    ce_weight: float = Field(default=0.5, ge=0, le=10)
    eval_k: int = Field(default=12, ge=1, le=100)
    pretrained: str = "../data/models/cifar_resnet18.pt"
    output: str = "../data/models/cifar_resnet18_metric.pt"


class PipelineIndexRequest(BaseModel):
    """Request to rebuild feature indexes as a background task."""

    dataset: str
    features: list[str] = Field(default_factory=lambda: ["deep"])


class PipelineEvaluateRequest(BaseModel):
    """Request to evaluate a feature through the task panel."""

    dataset: str = "cifar10"
    feature: str = "deep"
    metric: str = "cosine"
    k: int = Field(default=12, ge=1, le=100)
    sample: int = Field(default=100, ge=1, le=5000)


class PipelineUploadResponse(BaseModel):
    """Uploaded archive metadata."""

    filename: str
    saved_path: str
    extract_dir: str | None = None


class VideoKeyframeItem(BaseModel):
    """Video keyframe metadata returned by the API."""

    id: int
    video_id: int
    frame_index: int
    timestamp: float
    path: str
    url: str
    width: int
    height: int


class VideoItem(BaseModel):
    """Uploaded video metadata returned by the API."""

    id: int
    name: str
    path: str
    url: str
    duration: float
    fps: float
    frame_count: int
    keyframe_count: int
    keyframes: list[VideoKeyframeItem] = Field(default_factory=list)


class VideoListResponse(BaseModel):
    """Paginated video list."""

    items: list[VideoItem]
    total: int


class VideoIndexResponse(BaseModel):
    """Video index build response."""

    feature: str
    count: int
    videos: int


class VideoImportResponse(BaseModel):
    """Result of scanning the local incoming video folder."""

    incoming_dir: str
    imported: list[VideoItem] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)


class VideoSearchHit(BaseModel):
    """One video retrieval result."""

    video_id: int
    name: str
    url: str
    score: float
    duration: float
    keyframe_id: int | None = None
    keyframe_url: str = ""
    timestamp: float | None = None


class VideoSearchResponse(BaseModel):
    """Image-to-video search response."""

    query: dict[str, str | int | float | bool | None]
    hits: list[VideoSearchHit]
    elapsed_ms: float = Field(ge=0)
