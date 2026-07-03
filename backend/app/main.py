"""FastAPI entrypoint for the CBIR backend."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.device import get_device_status
from app.db.database import init_db
from app.routers import datasets, evaluate, images, pipeline, search, videos


def _include_flat_router(app: FastAPI, router: APIRouter) -> None:
    """Register APIRouter routes directly for the FastAPI version used here."""

    app.router.routes.extend(router.routes)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    init_db()
    app = FastAPI(title="CBIR Web System", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    settings.data_root_path.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=settings.data_root_path), name="static")
    _include_flat_router(app, datasets.router)
    _include_flat_router(app, search.router)
    _include_flat_router(app, images.router)
    _include_flat_router(app, evaluate.router)
    _include_flat_router(app, pipeline.router)
    _include_flat_router(app, videos.router)
    return app


app = create_app()


@app.get("/api/health")
def health() -> dict[str, object]:
    """Health check endpoint for M0 acceptance."""

    return {"status": "ok", "device": get_device_status()}
