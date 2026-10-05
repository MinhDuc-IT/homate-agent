"""JWT access (Bearer) + refresh (httpOnly cookie)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt

from homate.config import get_settings

TokenType = Literal["access", "refresh"]


def _encode(payload: dict[str, Any], *, minutes: float | None = None, days: float | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if minutes is not None:
        exp = now + timedelta(minutes=minutes)
    else:
        exp = now + timedelta(days=days or 7)
    body = {**payload, "iat": int(now.timestamp()), "exp": exp}
    return jwt.encode(body, settings.jwt_secret, algorithm="HS256")


def create_access_token(*, user_id: str, role: str, home_id: str, name: str) -> str:
    settings = get_settings()
    return _encode(
        {
            "sub": user_id,
            "role": role,
            "home_id": home_id,
            "name": name,
            "typ": "access",
        },
        minutes=settings.jwt_access_minutes,
    )


def create_refresh_token(*, user_id: str, role: str, home_id: str, name: str) -> str:
    settings = get_settings()
    return _encode(
        {
            "sub": user_id,
            "role": role,
            "home_id": home_id,
            "name": name,
            "typ": "refresh",
        },
        days=settings.jwt_refresh_days,
    )


def decode_token(token: str, *, expected: TokenType) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    if payload.get("typ") != expected:
        raise jwt.InvalidTokenError(f"expected typ={expected}")
    return payload
