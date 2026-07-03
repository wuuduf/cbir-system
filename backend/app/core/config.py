"""Application configuration loaded from settings.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    """Top-level application options."""

    data_root: str = "../data"
    device: str = "auto"
    top_k: int = 12
    public_base_url: str = ""
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )


class DatabaseConfig(BaseModel):
    """Database connection options."""

    url: str = "sqlite:///../data/cbir.db"


class PreprocessConfig(BaseModel):
    """Image preprocessing options."""

    size: tuple[int, int] = (256, 256)
    denoise: str = "median"
    equalize: bool = False


class FeatureConfig(BaseModel):
    """Feature extractor parameters."""

    color_hist: dict[str, int] = Field(
        default_factory=lambda: {"h_bins": 8, "s_bins": 8, "v_bins": 8}
    )
    color_moments: dict[str, Any] = Field(default_factory=dict)
    glcm: dict[str, Any] = Field(
        default_factory=lambda: {
            "levels": 8,
            "distances": [1],
            "angles_deg": [0, 45, 90, 135],
        }
    )
    lbp: dict[str, Any] = Field(
        default_factory=lambda: {"P": 8, "R": 1, "method": "uniform"}
    )
    hu: dict[str, Any] = Field(default_factory=dict)
    eoh: dict[str, int] = Field(default_factory=lambda: {"bins": 36})
    deep: dict[str, Any] = Field(
        default_factory=lambda: {
            "model": "auto",
            "dim": 2048,
            "checkpoint": "../data/models/cifar_resnet18_metric.pt",
        }
    )
    clip: dict[str, Any] = Field(
        default_factory=lambda: {
            "model": "ViT-B-32",
            "pretrained": "openai",
            "dim": 512,
            "batch_size": 64,
        }
    )


class Settings(BaseSettings):
    """Strongly typed settings object for the whole backend."""

    model_config = SettingsConfigDict(extra="ignore", env_nested_delimiter="__")

    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)
    preprocess: PreprocessConfig = Field(default_factory=PreprocessConfig)
    datasets_registry: str = "../data/registry.json"
    project_root: Path = Path(__file__).resolve().parents[3]
    backend_root: Path = Path(__file__).resolve().parents[2]

    def resolve_backend_path(self, value: str) -> Path:
        """Resolve a path written relative to backend/."""

        path = Path(value)
        if path.is_absolute():
            return path
        return (self.backend_root / path).resolve()

    @property
    def data_root_path(self) -> Path:
        """Absolute data root path."""

        return self.resolve_backend_path(self.app.data_root)

    @property
    def registry_path(self) -> Path:
        """Absolute dataset registry path."""

        return self.resolve_backend_path(self.datasets_registry)

    @property
    def sqlite_url(self) -> str:
        """Return a SQLite URL with an absolute path when configured relatively."""

        prefix = "sqlite:///"
        if not self.database.url.startswith(prefix):
            return self.database.url
        raw_path = self.database.url.removeprefix(prefix)
        db_path = Path(raw_path)
        if not db_path.is_absolute():
            db_path = self.resolve_backend_path(raw_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefix}{db_path.as_posix()}"


def _load_yaml_settings() -> dict[str, Any]:
    settings_path = Path(__file__).resolve().parents[2] / "settings.yaml"
    if not settings_path.exists():
        return {}
    with settings_path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}
    return dict(loaded)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    settings = Settings(**_load_yaml_settings())
    settings.data_root_path.mkdir(parents=True, exist_ok=True)
    settings.registry_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
