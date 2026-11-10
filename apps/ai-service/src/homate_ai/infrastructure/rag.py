import httpx
from homate_ai.domain.conversation import BackendError


class HttpKnowledgeRetriever:
    def __init__(self, client: httpx.AsyncClient): self.client = client

    async def retrieve(self, token: str, query: str, device_id: str | None = None) -> list[dict]:
        params = {'query':query}
        if device_id: params['device_id'] = device_id
        try:
            response = await self.client.get('/api/rag/search', params=params, headers={'Authorization':'Bearer '+token})
            if response.status_code in (401,403): raise BackendError(response.status_code, 'RAG từ chối truy cập')
            response.raise_for_status()
            return response.json()['chunks']
        except (httpx.HTTPError, ValueError, KeyError):
            raise BackendError(503, 'Kho kiến thức chưa sẵn sàng') from None
