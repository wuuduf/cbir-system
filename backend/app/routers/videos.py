"""Video management and image-to-video retrieval routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas import (
    VideoImportResponse,
    VideoIndexResponse,
    VideoItem,
    VideoListResponse,
    VideoSearchResponse,
)
from app.services.video_service import (
    build_video_index,
    delete_video,
    list_videos,
    save_video_upload,
    scan_incoming_videos,
    search_videos_by_image,
)

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("", response_model=VideoListResponse)
def get_videos(
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
) -> VideoListResponse:
    """List uploaded videos."""

    return list_videos(db, page=page, size=size)


@router.post("", response_model=VideoItem)
async def upload_video(
    file: UploadFile = File(...),
    interval_seconds: float = Form(2.0),
    max_keyframes: int = Form(60),
    db: Session = Depends(get_db),
) -> VideoItem:
    """Upload one video and extract keyframes."""

    try:
        return save_video_upload(
            db,
            file_obj=file.file,
            filename=file.filename or "video.mp4",
            interval_seconds=interval_seconds,
            max_keyframes=max_keyframes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{video_id}")
def remove_video(video_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Delete one uploaded video."""

    deleted = delete_video(db, video_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"视频不存在: {video_id}")
    return {"deleted": True}


@router.post("/index", response_model=VideoIndexResponse)
def build_index(
    feature: str = Form("deep"),
    db: Session = Depends(get_db),
) -> VideoIndexResponse:
    """Build a video keyframe index."""

    try:
        return build_video_index(db, feature=feature)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import-local", response_model=VideoImportResponse)
def import_local_videos(
    interval_seconds: float = Form(2.0),
    max_keyframes: int = Form(60),
    db: Session = Depends(get_db),
) -> VideoImportResponse:
    """Scan data/videos/incoming and import supported videos."""

    try:
        return scan_incoming_videos(
            db,
            interval_seconds=interval_seconds,
            max_keyframes=max_keyframes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/search", response_model=VideoSearchResponse)
async def search_videos(
    file: UploadFile = File(...),
    feature: str = Form("deep"),
    metric: str = Form("cosine"),
    top_k: int = Form(6),
    db: Session = Depends(get_db),
) -> VideoSearchResponse:
    """Search uploaded videos with an image query."""

    file_bytes = await file.read()
    try:
        return search_videos_by_image(
            db,
            file_bytes=file_bytes,
            feature=feature,
            metric=metric,
            top_k=top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
