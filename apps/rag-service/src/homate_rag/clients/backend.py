from uuid import uuid4
import httpx


class BackendAccessError(Exception):
    def __init__(self, status, message): self.status, self.message = status, message


class BackendAccess:
    def __init__(self, client): self.client = client

    def request(self, token, method, path, **kwargs):
        try:
            response = self.client.request(method, path, headers={'Authorization':'Bearer '+token}, **kwargs)
        except httpx.HTTPError:
            raise BackendAccessError(503, 'Không kết nối được backend để xác thực') from None
        if not response.is_success:
            raise BackendAccessError(response.status_code if response.status_code in (401,403) else 503, 'Backend từ chối yêu cầu')
        return response.json()

    def identity(self, token): return self.request(token, 'GET', '/api/dashboard/agent/identity')

    def directory(self, token): return DeviceDirectory(self, token)


class DeviceDirectory:
    def __init__(self, backend, token): self.backend, self.token = backend, token

    def validate(self, identifiers):
        if not identifiers: return
        snapshot = self.backend.request(self.token, 'POST', '/api/dashboard/agent/tools', json={
            'request_id':str(uuid4()), 'tool':'get_home_snapshot', 'arguments':{}})
        allowed = {device['id'] for device in snapshot['devices']}
        if not set(identifiers) <= allowed:
            raise ValueError('Thiết bị không tồn tại trong nhà của bạn')
