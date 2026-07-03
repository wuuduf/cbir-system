"""Experiment pipeline APIs for dataset preparation, training, and indexing."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.core.config import get_settings
from app.schemas import (
    PipelineEvaluateRequest,
    PipelineIndexRequest,
    PipelineUploadResponse,
    PrepareDatasetRequest,
    TaskInfo,
    TrainMetricModelRequest,
    TrainModelRequest,
)
from app.services.task_service import TaskRecord, python_command, task_manager

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/tasks", response_model=list[TaskInfo])
def list_tasks() -> list[TaskInfo]:
    """List recent background tasks."""

    return [_to_task_info(task) for task in task_manager.list_tasks()]


@router.delete("/tasks", response_model=list[TaskInfo])
def clear_tasks(
    mode: str = Query(
        "finished",
        description="'finished' only clears completed tasks; 'all' cancels and clears every task.",
        pattern="^(finished|all)$",
    ),
) -> list[TaskInfo]:
    """Clear task records from the in-memory task center."""

    task_manager.clear(mode)
    return [_to_task_info(task) for task in task_manager.list_tasks()]


@router.post("/tasks/clear", response_model=list[TaskInfo])
def clear_tasks_compat(
    mode: str = Query(
        "finished",
        description="'finished' only clears completed tasks; 'all' cancels and clears every task.",
        pattern="^(finished|all)$",
    ),
) -> list[TaskInfo]:
    """Clear task records with a POST route for browser/client compatibility."""

    task_manager.clear(mode)
    return [_to_task_info(task) for task in task_manager.list_tasks()]


@router.get("/tasks/{task_id}", response_model=TaskInfo)
def get_task(task_id: str) -> TaskInfo:
    """Return one background task by id."""

    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return _to_task_info(task)


@router.post("/tasks/{task_id}/cancel", response_model=TaskInfo)
def cancel_task(task_id: str) -> TaskInfo:
    """Cancel a queued or running background task."""

    task = task_manager.cancel(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return _to_task_info(task)


@router.post("/upload", response_model=PipelineUploadResponse)
async def upload_dataset_archive(
    file: UploadFile = File(...), extract: bool = True
) -> PipelineUploadResponse:
    """Upload a local dataset archive for later preparation."""

    settings = get_settings()
    upload_dir = settings.data_root_path / "raw" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(file.filename or "dataset.bin").name
    saved_path = upload_dir / filename
    with saved_path.open("wb") as target:
        shutil.copyfileobj(file.file, target)

    extract_dir: Path | None = None
    if extract:
        extract_dir = upload_dir / saved_path.stem.replace(".tar", "")
        extract_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.unpack_archive(str(saved_path), str(extract_dir))
        except (shutil.ReadError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"无法解压文件: {exc}") from exc
    return PipelineUploadResponse(
        filename=filename,
        saved_path=str(saved_path),
        extract_dir=str(extract_dir) if extract_dir is not None else None,
    )


@router.post("/download", response_model=TaskInfo)
def download_dataset(url: str, filename: str | None = None) -> TaskInfo:
    """Download a dataset archive from a URL as a background task."""

    settings = get_settings()
    download_dir = settings.data_root_path / "raw" / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    target_name = filename or Path(url.split("?")[0]).name or "dataset.bin"
    target_path = download_dir / Path(target_name).name
    task = task_manager.start_command(
        name=f"下载数据集 {target_path.name}",
        kind="download",
        command=python_command("scripts.download_file", url, str(target_path)),
    )
    return _to_task_info(task)


@router.post("/prepare", response_model=TaskInfo)
def prepare_dataset(payload: PrepareDatasetRequest) -> TaskInfo:
    """Prepare CIFAR-10 or CIFAR-100 from an official extracted directory."""

    task = task_manager.start_command(
        name=f"预处理 {payload.dataset.upper()}",
        kind="prepare",
        command=python_command(
            "scripts.prepare_cifar_dataset",
            "--dataset",
            payload.dataset,
            "--src",
            payload.src,
            "--split",
            payload.split,
            "--label-level",
            payload.label_level,
            *(
                ["--per-class", str(payload.per_class)]
                if payload.per_class is not None
                else []
            ),
        ),
    )
    return _to_task_info(task)


@router.post("/train", response_model=TaskInfo)
def train_model(payload: TrainModelRequest) -> TaskInfo:
    """Train a CIFAR CNN as a background process."""

    command = python_command(
        "scripts.train_cifar_cnn",
        "--dataset",
        payload.dataset,
        "--src",
        payload.src,
        "--label-level",
        payload.label_level,
        "--epochs",
        str(payload.epochs),
        "--batch-size",
        str(payload.batch_size),
        "--lr",
        str(payload.lr),
        "--weight-decay",
        str(payload.weight_decay),
        "--workers",
        str(payload.workers),
    )
    if payload.amp:
        command.append("--amp")
    task = task_manager.start_command(
        name=f"训练 {payload.dataset.upper()} CNN",
        kind="train",
        command=command,
        parser="train_json",
        progress={"total_epochs": payload.epochs},
    )
    return _to_task_info(task)


@router.post("/train-metric", response_model=TaskInfo)
def train_metric_model(payload: TrainMetricModelRequest) -> TaskInfo:
    """Train a CIFAR CNN with Triplet Loss as a background process."""

    command = python_command(
        "scripts.train_cifar_triplet",
        "--dataset",
        payload.dataset,
        "--src",
        payload.src,
        "--label-level",
        payload.label_level,
        "--epochs",
        str(payload.epochs),
        "--batch-size",
        str(payload.batch_size),
        "--lr",
        str(payload.lr),
        "--weight-decay",
        str(payload.weight_decay),
        "--workers",
        str(payload.workers),
        "--margin",
        str(payload.margin),
        "--triplet-weight",
        str(payload.triplet_weight),
        "--ce-weight",
        str(payload.ce_weight),
        "--eval-k",
        str(payload.eval_k),
        "--pretrained",
        payload.pretrained,
        "--output",
        payload.output,
    )
    if payload.amp:
        command.append("--amp")
    task = task_manager.start_command(
        name=f"Triplet 训练 {payload.dataset.upper()}",
        kind="train_metric",
        command=command,
        parser="train_json",
        progress={"total_epochs": payload.epochs},
    )
    return _to_task_info(task)


@router.post("/index", response_model=TaskInfo)
def build_index(payload: PipelineIndexRequest) -> TaskInfo:
    """Rebuild feature indexes as a background task."""

    task = task_manager.start_command(
        name=f"重建 {payload.dataset} 索引",
        kind="index",
        command=python_command(
            "scripts.build_index",
            "--dataset",
            payload.dataset,
            "--features",
            ",".join(payload.features),
        ),
    )
    return _to_task_info(task)


@router.post("/evaluate", response_model=TaskInfo)
def evaluate_feature(payload: PipelineEvaluateRequest) -> TaskInfo:
    """Evaluate one feature as a background task."""

    task = task_manager.start_command(
        name=f"评估 {payload.dataset} {payload.feature}",
        kind="evaluate",
        command=python_command(
            "scripts.run_evaluate",
            "--dataset",
            payload.dataset,
            "--feature",
            payload.feature,
            "--metric",
            payload.metric,
            "--k",
            str(payload.k),
            "--sample",
            str(payload.sample),
        ),
    )
    return _to_task_info(task)


def _to_task_info(task: TaskRecord) -> TaskInfo:
    return TaskInfo(
        id=task.id,
        name=task.name,
        kind=task.kind,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        command=task.command,
        logs=task.logs,
        progress=task.progress,
        result=task.result,
        error=task.error,
        returncode=task.returncode,
    )
