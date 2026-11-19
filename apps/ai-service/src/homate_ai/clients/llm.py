import json
import httpx
from homate_ai.agent.models import AgentUnavailable, ModelReply, ToolCall


class CompatibleChatModel:
    """Chat Completions adapter for the existing provider/model defaults."""
    def __init__(self, client: httpx.AsyncClient, model: str, api_key: str):
        self.client, self.model, self.api_key = client, model, api_key

    async def complete(self, messages, tools):
        if not self.api_key: raise AgentUnavailable('Chưa cấu hình API key cho LLM. Thêm key vào .env rồi khởi động lại ai-service.')
        try:
            interpreting = len(tools) == 1 and tools[0]['function']['name'] == 'submit_interpretation'
            payload = {'model': self.model, 'messages': messages, 'tools': tools,
                       'parallel_tool_calls': False, 'max_completion_tokens': 4000 if interpreting else 1200}
            if interpreting:
                payload['tool_choice'] = {'type': 'function', 'function': {'name': 'submit_interpretation'}}
            response = await self.client.post('/chat/completions', headers={'Authorization':f'Bearer {self.api_key}'}, json=payload)
            response.raise_for_status()
            message = response.json()['choices'][0]['message']
            calls = []
            for item in message.get('tool_calls') or []:
                args = json.loads(item['function']['arguments'])
                if not isinstance(args, dict): raise ValueError('Invalid arguments')
                calls.append(ToolCall(item['id'], item['function']['name'], args))
            return ModelReply(message.get('content') or '', calls)
        except httpx.TimeoutException:
            raise AgentUnavailable('Dịch vụ AI phản hồi quá chậm. Bạn thử lại sau nhé.', 'provider_timeout') from None
        except httpx.HTTPStatusError as error:
            code = 'provider_rate_limited' if error.response.status_code == 429 else 'provider_http_error'
            raise AgentUnavailable('Dịch vụ AI hiện chưa sẵn sàng. Bạn thử lại sau nhé.', code, error.response.status_code) from None
        except httpx.HTTPError:
            raise AgentUnavailable('LLM không phản hồi hợp lệ. Kiểm tra cấu hình provider, model và hạn mức.', 'provider_http_error') from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise AgentUnavailable('LLM trả output không hợp lệ. Vui lòng thử diễn đạt lại.', 'provider_response_invalid') from None
