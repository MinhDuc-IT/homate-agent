"""Read-only observation graph; model output can never choose a backend tool."""
from typing import TypedDict
from copy import deepcopy
import re
from uuid import UUID, uuid5
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ValidationError
from homate_ai.agent.grounding import ground, normalize
from homate_ai.agent.interpretation import AnalysisReport, Interpretation, Issue
from homate_ai.agent.interpreter import Interpreter
from homate_ai.agent.memory import context_for, resolve_references
from homate_ai.agent.read_scope import resolve_read_scope
from homate_ai.agent.models import AgentUnavailable
from homate_ai.agent.validation import review_intent, validate_device


class Snapshot(BaseModel):
    rooms: list[dict]
    devices: list[dict]
    scenes: list[dict]

    def checked(self):
        self.rooms = [{**room, 'name': room.get('name') or room.get('label')} for room in self.rooms]
        for collection, fields in ((self.rooms, ('id', 'name')),
                                   (self.devices, ('id', 'name', 'room', 'kind', 'controls', 'state')),
                                   (self.scenes, ('id', 'name'))):
            if any(not all(key in item for key in fields) for item in collection):
                raise ValueError('Incomplete backend snapshot')
            if any(not isinstance(item['id'], str) or not isinstance(item['name'], str) for item in collection):
                raise ValueError('Invalid entity identifiers')
        for device in self.devices:
            if not isinstance(device['state'], dict) or not isinstance(device['controls'], list):
                raise ValueError('Invalid device state or controls')
            for control in device['controls']:
                if not isinstance(control, dict) or not isinstance(control.get('key'), str):
                    raise ValueError('Invalid control')
                kind = control.get('type')
                if kind not in {'range', 'step', 'level', 'enum', 'action', 'toggle'}:
                    raise ValueError('Invalid control type')
                if kind in {'range', 'step'} and not all(type(control.get(key)) in (int, float) for key in ('min', 'max')):
                    raise ValueError('Invalid numeric control')
                if kind == 'level' and (not isinstance(control.get('levels'), list) or not all(type(v) is int for v in control['levels'])):
                    raise ValueError('Invalid levels')
                if kind == 'enum' and (not isinstance(control.get('options'), list) or not all(isinstance(o, dict) and 'value' in o for o in control['options'])):
                    raise ValueError('Invalid enum options')
                if control.get('when') is not None and not isinstance(control['when'], dict):
                    raise ValueError('Invalid control precondition')
        return self.model_dump()


class AnalysisState(TypedDict):
    token: str
    request_id: str
    text: str
    history: list[dict]
    user: dict
    interpretation: Interpretation
    snapshot: dict
    schedules: list[dict]
    grounded: list[tuple]
    report: AnalysisReport


class RequestAnalyzer:
    def __init__(self, model, backend, planning=False):
        self.interpreter, self.backend = Interpreter(model), backend
        self.planning = planning
        builder = StateGraph(AnalysisState)
        for name in ('authenticate', 'interpret', 'gather_data', 'ground', 'validate'):
            builder.add_node(name, getattr(self, name))
        builder.add_edge(START, 'authenticate')
        builder.add_edge('authenticate', 'interpret')
        builder.add_edge('interpret', 'gather_data')
        builder.add_edge('gather_data', 'ground')
        builder.add_edge('ground', 'validate')
        builder.add_edge('validate', END)
        self.graph = builder.compile()

    async def authenticate(self, state):
        return {'user': await self.backend.identity(state['token'])}

    async def interpret(self, state):
        result = await self.interpreter.interpret(state['text'], state['history'])
        return {'interpretation': result}

    async def read(self, state, tool, arguments):
        if tool not in {'get_home_snapshot', 'list_schedules', 'get_schedule'}:
            raise ValueError('The observation graph only permits fixed read tools')
        identifier = str(uuid5(UUID(state['request_id']), 'analysis:' + tool))
        return await self.backend.call(state['token'], identifier, tool, arguments)

    async def gather_data(self, state):
        intents = state['interpretation'].intents
        if not intents:
            return {'snapshot': {'rooms': [], 'devices': [], 'scenes': []}, 'schedules': []}
        try:
            snapshot = Snapshot.model_validate(await self.read(state, 'get_home_snapshot', {})).checked()
            schedules = []
            if any(any(target.entity == 'schedule' for target in intent.targets)
                   or 'schedule_id' in intent.arguments for intent in intents):
                result = await self.read(state, 'list_schedules', {'include_finished': True})
                schedules = result['schedules']
                if not isinstance(schedules, list) or any(not isinstance(s, dict) or not all(k in s for k in ('id', 'name')) for s in schedules):
                    raise ValueError('Incomplete schedule data')
            return {'snapshot': snapshot, 'schedules': schedules}
        except (ValidationError, KeyError, TypeError, ValueError):
            raise AgentUnavailable('Dữ liệu backend chưa đầy đủ để đối chiếu yêu cầu.') from None

    def ground(self, state):
        return {'grounded': [ground(intent, state['snapshot'], state['schedules'],
                                    state['text'], state['history'], contextual=self.planning)
                             for intent in state['interpretation'].intents]}

    async def validate(self, state):
        interpretation = state['interpretation']
        reviews = []
        snapshot = deepcopy(state['snapshot'])
        for intent, (arguments, provenance, issues) in zip(interpretation.intents, state['grounded']):
            reference_errors = []
            if state.get('session'):
                intent, reference_errors = resolve_references(intent, context_for(state['session']), snapshot, state['schedules'], state['history'])
            if self.planning:
                arguments, provenance, issues = ground(intent, snapshot, state['schedules'], state['text'], state['history'], contextual=True)
            issues = [*issues, *reference_errors]
            current = None
            if intent.capability == 'update_schedule' and isinstance(arguments.get('schedule_id'), str):
                if any(s['id'] == arguments['schedule_id'] for s in state['schedules']):
                    current = await self.read(state, 'get_schedule', {'schedule_id': arguments['schedule_id']})
                    if not isinstance(current, dict) or current.get('id') != arguments['schedule_id']:
                        raise AgentUnavailable('Không đọc được lịch hiện tại để kiểm tra thay đổi.')
            context = {}
            if intent.read_focus:
                context, errors = resolve_read_scope(intent, snapshot, state['schedules'], state['text'], state['history'], contextual=self.planning)
                issues.extend(errors)
            review = review_intent(intent, arguments, provenance, issues, snapshot, state['schedules'],
                                   state['user'], state['text'], state['history'], current, allow_plan=self.planning)
            review.read_context = context
            reviews.append(review)
            if review.requires_confirmation and re.search(
                    r'\b(?:dung|khong|khoi)\s+(?:(?:co|duoc|can|muon|phai|bao gio)\s+)*'
                    r'(?:bat|tat|mo|dong|tang|giam|dat|chay|tao|sua|xoa)\b', normalize(state['text'])):
                review.status = 'needs_clarification'
                review.issues.append(Issue(code='unresolved_meaning', path='action',
                    message='Yêu cầu có phủ định thao tác. Bạn muốn giữ nguyên trạng thái hay thực hiện thao tác nào?'))
            if self.planning and review.status == 'ready_for_review' and intent.capability == 'control_device':
                writes = validate_device(review.arguments, snapshot['devices'], lambda *args: None) or []
                device = next(d for d in snapshot['devices'] if d['id'] == review.arguments['device_id'])
                device['state'].update(dict(writes))
        statuses = {review.status for review in reviews}
        if not reviews:
            decision = 'answer' if interpretation.kind in {'conversation', 'query'} else (
                'no_active_session' if interpretation.kind in {'cancel', 'correction'} else 'needs_clarification')
        elif len(statuses) > 1:
            decision = 'mixed'
        else:
            decision = next(iter(statuses))
        questions = list(dict.fromkeys(issue.message for review in reviews for issue in review.issues))
        if not reviews and decision == 'needs_clarification':
            questions.append('Bạn muốn tôi giúp việc gì hoặc thao tác với đối tượng nào?')
        if decision == 'no_active_session':
            questions.append('Luồng phân tích chưa có phiên đang chờ để sửa hoặc hủy.')
        return {'report': AnalysisReport(interpretation=interpretation, reviews=reviews,
                                         decision=decision, questions=questions)}

    async def analyze(self, token, request_id, text, history):
        result = await self.graph.ainvoke({'token': token, 'request_id': request_id,
                                           'text': text, 'history': history},
                                          config={'recursion_limit': 10})
        return result['report']
