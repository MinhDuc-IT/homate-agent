"""Authenticated conversation storage and explicit version-bound plan decisions."""
from hashlib import sha256
import asyncio
from typing import Literal
import json
import jwt
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue
from fastapi.security import HTTPAuthorizationCredentials
from homate.application.agent_tools import prepare, execute
from homate.application.agent_workflow import READ_TOOLS, WRITE_TOOLS, WorkflowConflict
from homate.application.action_policy import confirmation_policy
from homate.modules.home.application.devices import DeviceStore
from homate.modules.home.domain.conflicts import active, DeviceConflictError
from homate.modules.automation.application.service import ScheduleService
from homate.presentation.agent_tools import validated_arguments, EnergyQuery, ScheduleQuery
from homate.presentation.dependencies import get_current_user, bearer
from homate.infrastructure.tokens import create_agent_cleanup_token, decode_token
from homate.infrastructure.realtime import notify_device_updated

router = APIRouter(prefix='/api/dashboard/agent', tags=['agent-workflow'])


class Payload(BaseModel):
    model_config = ConfigDict(extra='forbid')


class BeginTurn(Payload):
    request_id: UUID
    conversation_id: UUID | None = None
    expected_version: int | None = Field(default=None, ge=0)
    text: str = Field(min_length=1, max_length=4000)


class PlanStep(Payload):
    tool: str
    arguments: dict[str, JsonValue]
    depends_on: list[int] = Field(default_factory=list, max_length=48)
    expected_state: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)


class CommitTurn(Payload):
    lease_id: UUID
    state: dict[str, JsonValue] = Field(default_factory=dict)
    response: dict[str, JsonValue]
    invalidate: bool = False
    steps: list[PlanStep] = Field(default_factory=list, max_length=48)
    summary: str = Field(default='Kế hoạch điều khiển', max_length=2000)
    confirmation_mode: Literal['policy', 'always'] = 'policy'


class PlanDecision(Payload):
    approved: bool
    version: int = Field(ge=1)


class AbortTurn(Payload):
    lease_id: UUID


class Recovery(Payload):
    version: int = Field(ge=1)
    acknowledged: Literal[True]


def handle_error(error):
    if isinstance(error, WorkflowConflict):
        return HTTPException(409, str(error))
    if isinstance(error, LookupError):
        return HTTPException(404, str(error))
    if isinstance(error, PermissionError):
        return HTTPException(403, str(error))
    return HTTPException(400, str(error))


def read_step(app, user, tool, arguments, validate_only=False):
    household, store = app.state.household_service, app.state.device_store
    rooms = household.load_rooms_ambient(user['home_id'])
    room_ids = {room['id'] for room in rooms}
    if tool == 'get_home_snapshot':
        if arguments: raise ValueError('Snapshot không nhận tham số')
        allowed = {d.id for d in store.list() if d.room in room_ids}
        rules = {key: [r for r in peers if r['device_id'] in allowed] for key, peers in store.conflict_rules().items() if key in allowed}
        return {} if validate_only else {'rooms': rooms, 'devices': [d.model_dump(mode='json') for d in store.list() if d.room in room_ids], 'scenes': household.list_scenes(user['home_id']), 'device_conflicts': rules}
    if tool == 'get_energy_report':
        query = EnergyQuery.model_validate(arguments)
        if query.room_id and query.room_id not in room_ids: raise ValueError('Không tìm thấy phòng')
        if query.device_id:
            device = store.get(query.device_id)
            if device.room not in room_ids or query.room_id and device.room != query.room_id: raise PermissionError('Thiết bị không thuộc phạm vi đã chọn')
        return {} if validate_only else app.state.energy_service.report(**query.model_dump())
    if tool in {'list_scenes', 'get_scene'}:
        if tool == 'list_scenes':
            if arguments: raise ValueError('Danh sách kịch bản không nhận tham số')
            data = {'scenes': household.list_scenes(user['home_id'])}
        else:
            data = household.get_scene(user['home_id'], arguments['scene_id'])
        return {} if validate_only else data
    if tool == 'list_schedules':
        query = ScheduleQuery.model_validate(arguments)
        if query.room_id and query.room_id not in room_ids: raise ValueError('Không tìm thấy phòng')
        if query.scene_id: household.get_scene(user['home_id'], query.scene_id)
        return {} if validate_only else {'schedules': app.state.schedule_service.list(user['home_id'], **query.model_dump())}
    app.state.schedule_service.get(user['home_id'], arguments['schedule_id'])
    return {} if validate_only else (app.state.schedule_service.get(user['home_id'], arguments['schedule_id'])
        if tool == 'get_schedule' else {'runs': app.state.schedule_service.runs(user['home_id'], arguments['schedule_id'])})


def prepare_steps(app, user, steps):
    store = app.state.device_store.fork()
    household = app.state.household_service
    room_ids = {room['id'] for room in household.load_rooms_ambient(user['home_id'])}
    schedules = ScheduleService(app.state.schedule_service.repository, household, store)
    prepared = []
    desired = {}
    for index, step in enumerate(steps):
        tool, arguments = step['tool'], step['arguments']
        if tool not in WRITE_TOOLS | READ_TOOLS:
            raise ValueError('Kế hoạch chứa tool chưa được cho phép')
        dependencies = step.get('depends_on', [])
        if any(type(dep) is not int or dep < 0 or dep >= index for dep in dependencies):
            raise ValueError('Phụ thuộc phải trỏ tới bước trước đó')
        expected = step.get('expected_state') or step.get('prepared', {}).get('agent_expected_state', {})
        for identifier, values in expected.items():
            device = store.get(identifier)
            if device.room not in room_ids:
                raise PermissionError('Thiết bị không thuộc nhà của bạn')
            if any(device.state.get(key) != value for key, value in values.items()):
                raise ValueError('Trạng thái dùng để tính thay đổi tương đối đã thay đổi; hãy lập lại kế hoạch')
        args = validated_arguments(tool, arguments)
        if tool in READ_TOOLS:
            read_step(app, user, tool, args, validate_only=True)
            data, summary = {'read': True, 'arguments': args}, {
                'get_home_snapshot': 'Đọc trạng thái nhà', 'get_energy_report': 'Đọc báo cáo điện năng',
                'list_scenes': 'Xem danh sách kịch bản', 'get_scene': 'Xem kịch bản',
                'list_schedules': 'Xem danh sách lịch', 'get_schedule': 'Xem lịch', 'get_schedule_runs': 'Xem lịch sử chạy lịch'}[tool]
        else:
            data, summary = prepare(household, store, schedules, user, tool, args)
        if expected:
            data['agent_expected_state'] = expected
        prepared.append({'tool': tool, 'arguments': args, 'prepared': data,
                         'summary': summary, 'depends_on': dependencies})
        for write in data.get('writes', []):
            store.apply_action(write['device_id'], write['key'], write['value'])
        for command in data.get('commands', []):
            identifier = command['device_id']
            desired[identifier] = active(store.get(identifier))
    if any(value is True and active(store.get(identifier)) is not True for identifier, value in desired.items()):
        raise ValueError('Kế hoạch yêu cầu giữ các thiết bị xung đột cùng bật. Hãy chọn thiết bị muốn dùng.')
    return prepared


def execution_callbacks(app, user, changed):
    def preflight(steps):
        fresh = prepare_steps(app, user, steps)
        if any(a['prepared'] != b['prepared'] for a, b in zip(fresh, steps)):
            raise ValueError('Dữ liệu kế hoạch đã thay đổi')

    def run(tool, args):
        for identifier, values in args.get('agent_expected_state', {}).items():
            device = app.state.device_store.get(identifier)
            if any(device.state.get(key) != value for key, value in values.items()):
                raise ValueError('Trạng thái thiết bị đã thay đổi trước khi thực thi')
        if tool in READ_TOOLS:
            return read_step(app, user, tool, args['arguments'])
        return execute(app.state.household_service, app.state.device_store,
                       app.state.schedule_service, user, changed, tool, args)
    return preflight, run


def refresh_auto_response(request, user, request_id, result, receipt=None):
    if not result.get('auto_plan_id'):
        return result
    repository = request.app.state.agent_workflow_service.repository
    receipt = receipt or repository.get_plan(user, result['auto_plan_id'])
    if receipt['status'] == 'executed':
        labels = []
        for step in receipt['steps']:
            values = ', '.join(str(v) for v in step['arguments'].get('parameters', {}).values())
            labels.append(step['summary'] + (f' ({values})' if values else ''))
        reply = 'Đã thực hiện: ' + '; '.join(labels) + '.'
    elif receipt['status'] == 'executing':
        reply = 'Yêu cầu đang được xử lý. Chưa có kết quả hoàn tất; không gửi lại thao tác.'
    else:
        completed = sum(s['status'] == 'succeeded' for s in receipt['steps'])
        reply = f'Đã hoàn tất {completed}/{len(receipt["steps"])} bước. ' + (receipt.get('result') or {}).get('message', 'Kế hoạch chưa hoàn tất.')
    result = {**result, 'reply': reply, 'pending_actions': [], 'completed_actions': [receipt],
              'dialogue_state': 'executing' if receipt['status'] == 'executing' else 'idle'}
    return repository.cache_auto_result(user, str(request_id), result)


@router.post('/turns/begin')
def begin(body: BeginTurn, request: Request, user=Depends(get_current_user)):
    digest = sha256(json.dumps(body.model_dump(mode='json'), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    try:
        result = request.app.state.agent_workflow_service.repository.begin(user, str(body.request_id), digest,
            str(body.conversation_id) if body.conversation_id else None, body.expected_version)
        if not result['cached']:
            result['cleanup_token'] = create_agent_cleanup_token(user_id=user['id'], home_id=user['home_id'],
                request_id=str(body.request_id), lease_id=result['lease_id'])
        else:
            result['response'] = refresh_auto_response(request, user, body.request_id, result['response'])
        return result
    except (ValueError, LookupError, PermissionError) as error:
        raise handle_error(error) from None


@router.post('/turns/{request_id}/commit')
async def commit(request_id: UUID, body: CommitTurn, request: Request, user=Depends(get_current_user)):
    if not isinstance(body.response.get('reply'), str) or len(body.response['reply']) > 16000:
        raise HTTPException(400, 'Cần phản hồi hợp lệ')
    changed = []
    try:
        service = request.app.state.agent_workflow_service
        cached = service.repository.cached_turn(user, str(request_id))
        if cached:
            return refresh_auto_response(request, user, request_id, cached)
        steps = prepare_steps(request.app, user, [step.model_dump() for step in body.steps])
        policy = confirmation_policy(steps, request.app.state.device_store) if steps else None
        if policy and body.confirmation_mode == 'always':
            policy = {'mode': 'require_confirmation', 'reason': 'explicit_confirmation_requested'}
        auto = bool(policy and policy['mode'] == 'auto_execute')
        response = {key: value for key, value in body.response.items()
                    if key not in {'confirmation_policy', 'auto_plan_id', 'completed_actions', '_claimed_plan'}}
        if policy:
            response['confirmation_policy'] = policy
            response['reply'] = 'Đang thực hiện yêu cầu.' if auto else 'Bạn xác nhận các thao tác bên dưới nhé. Chưa có thay đổi nào được thực hiện.'
        ttl = request.app.state.household_service.get_home_settings(user['home_id'])['hitl_timeout_seconds']
        result = service.repository.commit(user, str(request_id), body.state,
            response, body.invalidate, steps, body.summary, ttl, str(body.lease_id), auto_execute=auto)
        claimed = result.pop('_claimed_plan', None)
        receipt = await asyncio.to_thread(service.execute_claimed, claimed, *execution_callbacks(request.app, user, changed)) if claimed else None
        return refresh_auto_response(request, user, request_id, result, receipt)
    except (ValueError, LookupError, PermissionError) as error:
        raise handle_error(error) from None
    finally:
        for device in changed:
            await notify_device_updated(request.app.state.ws_manager, device)


@router.post('/turns/{request_id}/abort')
def abort(request_id: UUID, body: AbortTurn, request: Request, user=Depends(get_current_user)):
    request.app.state.agent_workflow_service.repository.abort(user, str(request_id), str(body.lease_id))
    return {'status': 'released'}


@router.post('/turns/{request_id}/release')
def release(request_id: UUID, body: AbortTurn, request: Request,
            credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise HTTPException(401, 'Missing cleanup credential')
    try:
        payload = decode_token(credentials.credentials, expected='agent_cleanup')
        if (payload.get('request_id') != str(request_id) or payload.get('lease_id') != str(body.lease_id)
                or not payload.get('sub') or not payload.get('home_id')):
            raise jwt.InvalidTokenError('Cleanup scope mismatch')
    except jwt.PyJWTError:
        raise HTTPException(401, 'Invalid cleanup credential') from None
    user = {'id': payload['sub'], 'home_id': payload['home_id']}
    # Repository locks the owned session and compares BOTH request and lease;
    # replay of an old credential cannot release a newer worker's lease.
    request.app.state.agent_workflow_service.repository.abort(user, str(request_id), str(body.lease_id))
    return {'status': 'released'}


@router.get('/conversations/{identifier}')
def conversation(identifier: UUID, request: Request, user=Depends(get_current_user)):
    try:
        return request.app.state.agent_workflow_service.repository.fetch(user, str(identifier))
    except LookupError as error:
        raise HTTPException(404, str(error)) from None


@router.post('/plans/{identifier}/decision')
async def decide(identifier: UUID, body: PlanDecision, request: Request, user=Depends(get_current_user)):
    app, changed = request.app, []
    preflight, run = execution_callbacks(app, user, changed)

    try:
        return await asyncio.to_thread(app.state.agent_workflow_service.decide, user, str(identifier), body.version,
                                                      body.approved, preflight, run)
    except (ValueError, LookupError, PermissionError) as error:
        raise handle_error(error) from None
    finally:
        for device in changed:
            await notify_device_updated(app.state.ws_manager, device)


@router.get('/plans/{identifier}')
def get_plan(identifier: UUID, request: Request, user=Depends(get_current_user)):
    try:
        return request.app.state.agent_workflow_service.repository.get_plan(user, str(identifier))
    except LookupError as error:
        raise HTTPException(404, str(error)) from None


@router.delete('/conversations/{identifier}')
def close(identifier: UUID, request: Request, user=Depends(get_current_user)):
    try:
        request.app.state.agent_workflow_service.repository.close(user, str(identifier))
        return {'status': 'cancelled'}
    except (ValueError, LookupError) as error:
        raise handle_error(error) from None


@router.post('/plans/{identifier}/recover')
def recover(identifier: UUID, body: Recovery, request: Request, user=Depends(get_current_user)):
    try:
        return request.app.state.agent_workflow_service.repository.recover(user, str(identifier), body.version)
    except (ValueError, LookupError) as error:
        raise handle_error(error) from None
