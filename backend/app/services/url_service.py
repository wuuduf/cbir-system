"""URL helpers for local and deployed static assets."""

from __future__ import annotations

from app.core.config import get_settings


def static_url(relative_path: str) -> str:
    """Return a static asset URL, absolute only when public_base_url is configured."""

    normalized = relative_path.replace("\\", "/").lstrip("/")
    base_url = get_settings().app.public_base_url.rstrip("/")
    if not base_url:
        return f"/static/{normalized}"
    return f"{base_url}/static/{normalized}"
