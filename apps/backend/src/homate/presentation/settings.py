"""Home settings, command logs, and HITL policy APIs for the dashboard."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from homate.presentation.dependencies import get_current_user, require_admin
from homate.presentation.dependencies import get_household_service
from homate.infrastructure.realtime import pending_hitl
router = APIRouter(prefix='/api/dashboard', tags=['settings'])

def _home_id(user: dict[str, Any]) -> str:
    home_id = user.get('home_id')
    if not home_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing home')
    return str(home_id)

class SettingsOut(BaseModel):
    command_log_enabled: bool = True
    command_log_retention_days: int = 30
    hitl_timeout_seconds: int = 30

class SettingsPatch(BaseModel):
    command_log_enabled: bool | None = None
    command_log_retention_days: int | None = Field(default=None, ge=1, le=365)
    hitl_timeout_seconds: int | None = Field(default=None, ge=5, le=300)

class CommandLogOut(BaseModel):
    id: str
    utterance: str
    intent: str | None = None
    result: str
    note: str = ''
    session_id: str = ''
    created_at: str

class HitlPolicyOut(BaseModel):
    id: str
    device_id: str
    device_name: str = ''
    device_kind: str = ''
    action: str
    require_confirm: bool = True

class HitlPolicyWrite(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=64)
    action: str = Field(..., min_length=1, max_length=64)
    require_confirm: bool = True

class HitlPoliciesReplace(BaseModel):
    policies: list[HitlPolicyWrite] = Field(default_factory=list)

@router.get('/settings', response_model=SettingsOut)
async def get_settings(db_path=Depends(get_household_service), user: dict=Depends(get_current_user)) -> SettingsOut:
    return SettingsOut.model_validate(db_path.get_home_settings(_home_id(user)))

@router.patch('/settings', response_model=SettingsOut)
async def patch_settings(body: SettingsPatch, db_path=Depends(get_household_service), user: dict=Depends(require_admin)) -> SettingsOut:
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return SettingsOut.model_validate(db_path.get_home_settings(_home_id(user)))
    try:
        row = db_path.update_home_settings(_home_id(user), updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if 'hitl_timeout_seconds' in updates:
        pending_hitl.set_ttl_seconds(row['hitl_timeout_seconds'])
    return SettingsOut.model_validate(row)

@router.get('/command-logs', response_model=list[CommandLogOut])
async def get_command_logs(limit: int=Query(default=50, ge=1, le=200), db_path=Depends(get_household_service), user: dict=Depends(get_current_user)) -> list[CommandLogOut]:
    return [CommandLogOut.model_validate(row) for row in db_path.list_command_logs(_home_id(user), limit=limit)]

@router.get('/hitl-policies', response_model=list[HitlPolicyOut])
async def get_hitl_policies(db_path=Depends(get_household_service), user: dict=Depends(get_current_user)) -> list[HitlPolicyOut]:
    return [HitlPolicyOut.model_validate(row) for row in db_path.list_hitl_policies(_home_id(user))]

@router.put('/hitl-policies', response_model=list[HitlPolicyOut])
async def put_hitl_policies(body: HitlPoliciesReplace, background_tasks: BackgroundTasks, db_path=Depends(get_household_service), user: dict=Depends(require_admin)) -> list[HitlPolicyOut]:
    try:
        rows = db_path.replace_hitl_policies(_home_id(user), [item.model_dump() for item in body.policies])
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [HitlPolicyOut.model_validate(row) for row in rows]
