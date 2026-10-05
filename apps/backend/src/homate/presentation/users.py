"""Authenticated user profile and admin-managed household user CRUD."""
from __future__ import annotations
from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from homate.presentation.dependencies import get_current_user, require_admin
from homate.presentation.dependencies import get_household_service
router = APIRouter(prefix='/api/dashboard/users', tags=['users'])

class UserOut(BaseModel):
    id: str
    name: str
    initial: str
    role: Literal['admin', 'member']
    email: str | None = None
    phone: str | None = None
    is_active: bool = True

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    role: Literal['admin', 'member'] = 'member'
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    pin: str = Field(..., pattern='^\\d{4}$')

class UserPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    role: Literal['admin', 'member'] | None = None
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    pin: str | None = Field(default=None, pattern='^\\d{4}$')

def _home_id(user: dict[str, Any]) -> str:
    value = user.get('home_id')
    if not value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing home')
    return str(value)

def _public(user: dict[str, Any]) -> UserOut:
    return UserOut.model_validate(user)

@router.get('/me', response_model=UserOut)
async def me(db_path=Depends(get_household_service), user: dict[str, Any]=Depends(get_current_user)) -> UserOut:
    result = db_path.get_user(str(user['id']))
    if result is None or not result['is_active']:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Không tìm thấy tài khoản')
    return _public(result)

@router.get('', response_model=list[UserOut])
async def users(db_path=Depends(get_household_service), user: dict[str, Any]=Depends(require_admin)) -> list[UserOut]:
    return [_public(item) for item in db_path.list_users(_home_id(user))]

@router.post('', response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def add_user(body: UserCreate, db_path=Depends(get_household_service), user: dict[str, Any]=Depends(require_admin)) -> UserOut:
    return _public(db_path.create_user(_home_id(user), body.model_dump()))

@router.patch('/{user_id}', response_model=UserOut)
async def edit_user(user_id: str, body: UserPatch, db_path=Depends(get_household_service), user: dict[str, Any]=Depends(require_admin)) -> UserOut:
    updates = body.model_dump(exclude_unset=True)
    if user_id == user['id'] and updates.get('role') not in (None, user['role']):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Không thể tự thay đổi vai trò')
    try:
        return _public(db_path.update_user(_home_id(user), user_id, updates))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

@router.delete('/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(user_id: str, db_path=Depends(get_household_service), user: dict[str, Any]=Depends(require_admin)) -> Response:
    if user_id == user['id']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Không thể tự xóa tài khoản')
    try:
        db_path.deactivate_user(_home_id(user), user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
