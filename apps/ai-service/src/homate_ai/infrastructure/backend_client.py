import httpx
from homate_ai.domain.conversation import BackendError, AgentUnavailable


class BackendClient:
    def __init__(self, client: httpx.AsyncClient): self.client = client

    async def request(self, token, method, path, **kwargs):
        try: response = await self.client.request(method, path, headers={'Authorization':f'Bearer {token}'}, **kwargs)
        except httpx.HTTPError: raise AgentUnavailable('Không kết nối được backend HomeMate') from None
        if not response.is_success:
            try: detail = response.json().get('detail', 'Backend từ chối thao tác')
            except ValueError: detail = 'Backend từ chối thao tác'
            raise BackendError(response.status_code, str(detail))
        return response.json()

    async def identity(self, token):
        return await self.request(token, 'GET', '/api/dashboard/agent/identity')

    async def call(self, token, request_id, name, arguments):
        return await self.request(token, 'POST', '/api/dashboard/agent/tools', json={'request_id':request_id,'tool':name,'arguments':arguments})
