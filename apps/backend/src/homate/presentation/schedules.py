"""Dashboard schedule CRUD and execution history."""
from __future__ import annotations
from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field, model_validator
from homate.presentation.dependencies import get_current_user, require_admin
from homate.modules.automation.application.service import ScheduleService
router = APIRouter(prefix='/api/dashboard/schedules', tags=['schedules'])

class RecurrenceRule(BaseModel):
    frequency: Literal['daily', 'weekly'] = 'daily'
    time: str = Field(..., pattern='^(?:[01]\\d|2[0-3]):[0-5]\\d$')
    days_of_week: list[int] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_weekly_days(self):
        if self.frequency == 'weekly' and (not self.days_of_week):
            raise ValueError('Lịch theo tuần cần chọn ít nhất một ngày')
        if any((day < 0 or day > 6 for day in self.days_of_week)):
            raise ValueError('Ngày trong tuần phải từ 0 đến 6')
        return self

class ScheduleWrite(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    schedule_type: Literal['once', 'recurring']
    target_type: Literal['device_action', 'scene']
    device_id: str | None = None
    action: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    scene_id: str | None = None
    timezone: str = 'Asia/Ho_Chi_Minh'
    run_at: str | None = None
    recurrence_rule: RecurrenceRule | None = None
    enabled: bool = True

    @model_validator(mode='after')
    def validate_target_and_time(self):
        if self.target_type == 'device_action' and (not self.device_id or not self.action):
            raise ValueError('Lịch thiết bị cần device_id và action')
        if self.target_type == 'scene' and (not self.scene_id):
            raise ValueError('Lịch kịch bản cần scene_id')
        if self.schedule_type == 'once' and (not self.run_at):
            raise ValueError('Lịch một lần cần run_at')
        if self.schedule_type == 'recurring' and (not self.recurrence_rule):
            raise ValueError('Lịch lặp cần recurrence_rule')
        return self

class SchedulePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    schedule_type: Literal['once', 'recurring'] | None = None
    target_type: Literal['device_action', 'scene'] | None = None
    device_id: str | None = None
    action: str | None = None
    parameters: dict[str, Any] | None = None
    scene_id: str | None = None
    timezone: str | None = None
    run_at: str | None = None
    recurrence_rule: RecurrenceRule | None = None
    enabled: bool | None = None

def service(request: Request) -> ScheduleService:
    return request.app.state.schedule_service

def home_id(user: dict[str, Any]) -> str:
    return str(user.get('home_id') or '')

@router.get('')
async def list_all(request: Request, room_id: str | None=Query(None), scene_id: str | None=Query(None), include_finished: bool=Query(False), user: dict=Depends(get_current_user)) -> list[dict]:
    return service(request).list(home_id(user), room_id=room_id, scene_id=scene_id, include_finished=include_finished)

@router.post('', status_code=status.HTTP_201_CREATED)
async def create(body: ScheduleWrite, request: Request, user: dict=Depends(require_admin)) -> dict:
    try:
        return service(request).create(home_id(user), str(user['id']), body.model_dump())
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.patch('/{schedule_id}')
async def update(schedule_id: str, body: SchedulePatch, request: Request, user: dict=Depends(require_admin)) -> dict:
    try:
        return service(request).update(home_id(user), schedule_id, body.model_dump(exclude_unset=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.delete('/{schedule_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete(schedule_id: str, request: Request, user: dict=Depends(require_admin)) -> Response:
    try:
        service(request).delete(home_id(user), schedule_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)

@router.get('/{schedule_id}/runs')
async def runs(schedule_id: str, request: Request, user: dict=Depends(get_current_user)) -> list[dict]:
    try:
        return service(request).runs(home_id(user), schedule_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
