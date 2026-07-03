"""Database models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Image(Base):
    """Image metadata stored in the database."""

    __tablename__ = "images"
    __table_args__ = (
        Index("ix_images_dataset_name", "dataset", "name", unique=True),
        Index("ix_images_dataset_category", "dataset", "category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dataset: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(1024))
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    width: Mapped[int] = mapped_column()
    height: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Video(Base):
    """Uploaded video metadata."""

    __tablename__ = "videos"
    __table_args__ = (Index("ix_videos_name", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(1024))
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    frame_count: Mapped[int] = mapped_column(default=0)
    keyframe_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VideoKeyframe(Base):
    """Keyframe metadata extracted from uploaded videos."""

    __tablename__ = "video_keyframes"
    __table_args__ = (
        Index("ix_video_keyframes_video", "video_id"),
        Index("ix_video_keyframes_video_frame", "video_id", "frame_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    frame_index: Mapped[int] = mapped_column(default=0)
    timestamp: Mapped[float] = mapped_column(Float, default=0.0)
    path: Mapped[str] = mapped_column(String(1024))
    width: Mapped[int] = mapped_column()
    height: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
