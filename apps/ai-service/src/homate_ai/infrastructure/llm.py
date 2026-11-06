import json
import httpx
from homate_ai.domain.conversation import AgentUnavailable, ModelReply, ToolCall


class CompatibleChatModel:
    """Chat Completions adapter for the existing provider/model defaults."""
    def __init__(self, client: httpx.AsyncClient, model: str, api_key: str):
        self.client, self.model, self.api_key = client, model, api_key

    async def complete(self, messages, tools):
        if not self.api_key: raise AgentUnavailable('Chưa cấu hình API key cho LLM. Thêm key vào .env rồi khởi động lại ai-service.')
        try:
            response = await self.client.post('/chat/completions', headers={'Authorization':f'Bearer {self.api_key}'}, json={
                'model':self.model, 'messages':messages, 'tools':tools, 'parallel_tool_calls':False, 'max_completion_tokens':1200})
            response.raise_for_status()
            message = response.json()['choices'][0]['message']
            calls = []
            for item in message.get('tool_calls') or []:
                args = json.loads(item['function']['arguments'])
                if not isinstance(args, dict): raise ValueError('Invalid arguments')
                calls.append(ToolCall(item['id'], item['function']['name'], args))
            return ModelReply(message.get('content') or '', calls)
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            raise AgentUnavailable('LLM không phản hồi hợp lệ. Kiểm tra cấu hình provider, model và hạn mức.') from None
