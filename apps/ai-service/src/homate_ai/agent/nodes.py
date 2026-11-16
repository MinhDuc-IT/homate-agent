import json
from datetime import datetime
from zoneinfo import ZoneInfo
from homate_ai.agent.models import AgentUnavailable
from homate_ai.agent.prompts import SYSTEM
from homate_ai.agent.tools import TOOLS


class AgentNodes:
    def __init__(self, model, backend, executor, max_rounds):
        self.model, self.backend = model, backend
        self.executor, self.max_rounds = executor, max_rounds

    async def authenticate(self, state):
        user = await self.backend.identity(state['token'])
        now = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat()
        messages = [{'role': 'system', 'content': SYSTEM + f'\nThời gian hiện tại: {now}. Vai trò: {user["role"]}.'}]
        messages.extend(state['history'][-12:])
        messages.append({'role': 'user', 'content': state['text']})
        return {'messages': messages}

    async def call_model(self, state):
        if state['rounds'] >= self.max_rounds:
            raise AgentUnavailable('Agent đạt giới hạn xử lý. Hãy thử yêu cầu cụ thể hơn.')
        reply = await self.model.complete(state['messages'], TOOLS)
        messages = list(state['messages'])
        if reply.calls:
            messages.append({'role': 'assistant', 'content': reply.text or None, 'tool_calls': [
                {'id': call.id, 'type': 'function', 'function': {
                    'name': call.name, 'arguments': json.dumps(call.arguments, ensure_ascii=False)}}
                for call in reply.calls]})
        return {'model_reply': reply, 'messages': messages, 'rounds': state['rounds'] + 1}

    async def execute_tools(self, state):
        return await self.executor.run(state)

    def respond(self, state):
        if state['pending_actions']:
            reply = 'Vui lòng kiểm tra và xác nhận thao tác bên dưới.'
        else:
            reply = state['model_reply'].text or 'Bạn muốn điều khiển thiết bị nào?'
        return {'reply': reply}
