"""Login / refresh / logout — JWT access + refresh cookie."""
from __future__ import annotations
from typing import Any, Literal
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from homate.infrastructure.tokens import create_access_token, create_refresh_token, decode_token
from homate.config import get_settings
from homate.presentation.dependencies import get_household_service
router = APIRouter(prefix='/api/dashboard/auth', tags=['auth'])
REFRESH_COOKIE_PATH = '/api/dashboard/auth'

class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    pin: str = Field(..., min_length=4, max_length=4, pattern='^\\d{4}$')

class AuthUser(BaseModel):
    id: str
    name: str
    initial: str
    role: Literal['admin', 'member']

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int
    user: AuthUser

def _cookie_kwargs() -> dict[str, Any]:
    settings = get_settings()
    return {'key': settings.jwt_cookie_name, 'httponly': True, 'samesite': 'lax', 'secure': settings.app_env == 'production', 'path': REFRESH_COOKIE_PATH, 'max_age': settings.jwt_refresh_days * 24 * 3600}

def _set_refresh_cookie(response: Response, token: str) -> None:
    kwargs = _cookie_kwargs()
    key = kwargs.pop('key')
    response.set_cookie(key, token, **kwargs)

def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.jwt_cookie_name, path=REFRESH_COOKIE_PATH, httponly=True, samesite='lax', secure=settings.app_env == 'production')

def _tokens_for(user: dict[str, Any]) -> tuple[str, str, int]:
    settings = get_settings()
    access = create_access_token(user_id=user['id'], role=user['role'], home_id=user['home_id'], name=user['name'])
    refresh = create_refresh_token(user_id=user['id'], role=user['role'], home_id=user['home_id'], name=user['name'])
    return (access, refresh, settings.jwt_access_minutes * 60)

def _user_public(user: dict[str, Any]) -> AuthUser:
    return AuthUser(id=user['id'], name=user['name'], initial=user['initial'], role=user['role'])

@router.post('/login', response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db_path=Depends(get_household_service)) -> TokenResponse:
    user = db_path.get_user(body.user_id)
    if user is None or not user['is_active'] or (not verify_pin(user['pin_hash'], body.pin)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='PIN không đúng')
    access, refresh, expires_in = _tokens_for(user)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, expires_in=expires_in, user=_user_public(user))

@router.post('/refresh', response_model=TokenResponse)
async def refresh_access(request: Request, response: Response, db_path=Depends(get_household_service)) -> TokenResponse:
    settings = get_settings()
    raw = request.cookies.get(settings.jwt_cookie_name)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing refresh token')
    try:
        payload = decode_token(raw, expected='refresh')
    except jwt.PyJWTError as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token') from exc
    user = db_path.get_user(str(payload.get('sub') or ''))
    if user is None or not user['is_active']:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User inactive')
    access, refresh, expires_in = _tokens_for(user)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, expires_in=expires_in, user=_user_public(user))

@router.post('/logout')
async def logout(response: Response) -> dict[str, bool]:
    _clear_refresh_cookie(response)
    return {'ok': True}
from homate.modules.identity.domain.security import verify_pin
