"""Authenticated tools: only this backend may authorize and execute writes."""
from uuid import UUID
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from homate.presentation.dependencies import get_current_user
from homate.presentation.schedules import ScheduleWrite, SchedulePatch
from homate.presentation.scenes import SceneWrite, SceneStepWrite
from homate.application.agent_tools import prepare, execute as execute_tool
from homate.modules.home.application.devices import DeviceNotFoundError, InvalidDeviceActionError
from homate.infrastructure.realtime import notify_device_updated

router = APIRouter(prefix='/api/dashboard/agent', tags=['agent-tools'])


@router.get('/identity')
def identity(user=Depends(get_current_user)):
    return {'id':user['id'], 'home_id':user['home_id'], 'role':user['role']}


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    tool: Literal['get_home_snapshot','get_energy_report','control_device','execute_scene','create_schedule',
        'list_scenes','get_scene','create_scene','update_scene','delete_scene','set_scene_enabled',
        'list_schedules','get_schedule','update_schedule','delete_schedule','set_schedule_enabled','get_schedule_runs']
    arguments: dict = Field(default_factory=dict)




class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    approved: bool


class ScenePatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str | None = Field(default=None,min_length=1,max_length=80)
    voice_keyword: str | None = Field(default=None,min_length=1,max_length=80)
    is_enabled: bool | None = None
    steps: list[SceneStepWrite] | None = None


class Identifier(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scene_id: str | None = None
    schedule_id: str | None = None
    enabled: bool | None = None
    changes: dict | None = None


class EnergyQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    period: Literal['today','7days','30days','3months','week','month','year'] = 'today'
    room_id: str | None = None
    device_id: str | None = None
    anchor: date | None = None


class ScheduleQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    room_id: str | None = None
    scene_id: str | None = None
    include_finished: bool = False


def validated_arguments(tool, arguments):
    if tool == 'create_schedule':
        if set(arguments) - set(ScheduleWrite.model_fields): raise ValueError('Tham số lịch không hợp lệ')
        return ScheduleWrite.model_validate(arguments).model_dump()
    if tool == 'create_scene':
        if set(arguments) - set(SceneWrite.model_fields): raise ValueError('Tham số kịch bản không hợp lệ')
        return SceneWrite.model_validate(arguments).model_dump()
    if tool in {'get_scene','delete_scene','set_scene_enabled','update_scene','get_schedule','get_schedule_runs','delete_schedule','set_schedule_enabled','update_schedule'}:
        field = 'scene_id' if 'scene' in tool else 'schedule_id'
        allowed = {field} | ({'changes'} if tool.startswith('update_') else {'enabled'} if tool.startswith('set_') else set())
        if set(arguments) != allowed: raise ValueError(f'Cần đúng các tham số: {sorted(allowed)}')
        data = Identifier.model_validate(arguments).model_dump(exclude_none=True)
        if not data.get(field): raise ValueError('Thiếu mã đối tượng')
        if tool.startswith('set_') and 'enabled' not in data: raise ValueError('Cần trạng thái bật/tắt')
        if tool.startswith('update_'):
            if not isinstance(arguments.get('changes'),dict) or not arguments['changes']:
                raise ValueError('Nội dung cập nhật phải là object không rỗng')
            patch = ScenePatch if field == 'scene_id' else SchedulePatch
            if set(arguments['changes']) - set(patch.model_fields): raise ValueError('Trường cập nhật không hợp lệ')
            data['changes'] = patch.model_validate(arguments['changes']).model_dump(exclude_unset=True)
            if not data['changes'] or any(value is None for key,value in data['changes'].items() if field == 'scene_id'):
                raise ValueError('Nội dung cập nhật không hợp lệ')
        return data
    return arguments




@router.post('/tools')
async def call_tool(body: ToolRequest, request: Request, user=Depends(get_current_user)):
    household = request.app.state.household_service
    if body.tool == 'get_home_snapshot':
        if body.arguments: raise HTTPException(400, 'Tool này không nhận tham số')
        rooms = household.load_rooms_ambient(user['home_id'])
        room_ids = {room['id'] for room in rooms}
        return {'rooms': rooms, 'devices': [d.model_dump(mode='json') for d in request.app.state.device_store.list() if d.room in room_ids], 'scenes': household.list_scenes(user['home_id'])}
    try:
        arguments = validated_arguments(body.tool, body.arguments)
        if body.tool == 'get_energy_report':
            query = EnergyQuery.model_validate(arguments)
            room_ids = {room['id'] for room in household.load_rooms_ambient(user['home_id'])}
            if query.room_id and query.room_id not in room_ids: raise LookupError('Không tìm thấy phòng')
            if query.device_id:
                device = request.app.state.device_store.get(query.device_id)
                if device.room not in room_ids: raise PermissionError('Thiết bị không thuộc nhà của bạn')
                if query.room_id and device.room != query.room_id: raise ValueError('Thiết bị không thuộc phòng đã chọn')
            return request.app.state.energy_service.report(**query.model_dump())
        if body.tool == 'list_scenes':
            if arguments: raise ValueError('Tool không nhận tham số')
            return {'scenes':household.list_scenes(user['home_id'])}
        if body.tool == 'get_scene': return household.get_scene(user['home_id'],arguments['scene_id'])
        if body.tool == 'list_schedules':
            query = ScheduleQuery.model_validate(arguments)
            if query.room_id and query.room_id not in {r['id'] for r in household.load_rooms_ambient(user['home_id'])}: raise LookupError('Không tìm thấy phòng')
            if query.scene_id: household.get_scene(user['home_id'],query.scene_id)
            return {'schedules':request.app.state.schedule_service.list(user['home_id'],**query.model_dump())}
        if body.tool == 'get_schedule': return request.app.state.schedule_service.get(user['home_id'],arguments['schedule_id'])
        if body.tool == 'get_schedule_runs': return {'runs':request.app.state.schedule_service.runs(user['home_id'],arguments['schedule_id'])}
        args, summary = prepare(household, request.app.state.device_store, request.app.state.schedule_service, user, body.tool, arguments)
        return request.app.state.agent_action_service.propose(user, str(body.request_id), body.tool, args, summary, household.get_home_settings(user['home_id'])['hitl_timeout_seconds'])
    except PermissionError as exc: raise HTTPException(403, str(exc)) from exc
    except (ValueError, LookupError, DeviceNotFoundError, InvalidDeviceActionError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post('/actions/{identifier}/decision')
async def decide(identifier: UUID, body: Decision, request: Request, user=Depends(get_current_user)):
    household = request.app.state.household_service
    store = request.app.state.device_store
    changed = []
    def execute(tool, args):
        return execute_tool(household, store, request.app.state.schedule_service, user, changed, tool, args)

    try:
        receipt = request.app.state.agent_action_service.decide(user, str(identifier), body.approved, execute)
    except PermissionError as exc: raise HTTPException(403, str(exc)) from exc
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc
    except (ValueError, DeviceNotFoundError, InvalidDeviceActionError) as exc: raise HTTPException(400, str(exc)) from exc
    finally:
        for device in changed: await notify_device_updated(request.app.state.ws_manager, device)
    return receipt
