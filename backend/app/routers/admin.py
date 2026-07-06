"""Admin and AI analysis API routes."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    AiConfigResponse,
    AiConfigUpdate,
    EvalAnalysisRequest,
    EvalAnalysisResponse,
)
from app.services.admin_service import (
    analyze_evaluation,
    make_admin_token,
    safe_ai_config,
    verify_admin_password,
    verify_admin_token,
    write_ai_config,
)

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/admin/login", response_model=AdminLoginResponse)
def login(payload: AdminLoginRequest) -> AdminLoginResponse:
    """Login to the local admin page."""

    if not verify_admin_password(payload.password):
        raise HTTPException(status_code=401, detail="管理员密码不正确")
    return AdminLoginResponse(token=make_admin_token(payload.password))


@router.get("/admin/ai-config", response_model=AiConfigResponse)
def get_ai_config(x_admin_token: str = Header(default="")) -> AiConfigResponse:
    """Return AI settings without the secret key."""

    _require_admin(x_admin_token)
    return safe_ai_config()


@router.post("/admin/ai-config", response_model=AiConfigResponse)
def update_ai_config(
    payload: AiConfigUpdate,
    x_admin_token: str = Header(default=""),
) -> AiConfigResponse:
    """Save AI settings."""

    _require_admin(x_admin_token)
    return write_ai_config(payload)


@router.post("/ai/evaluate-analysis", response_model=EvalAnalysisResponse)
def evaluate_analysis(payload: EvalAnalysisRequest) -> EvalAnalysisResponse:
    """Analyze evaluation metrics with the configured AI provider."""

    try:
        return analyze_evaluation(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _require_admin(token: str) -> None:
    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="请先登录管理员页面")
