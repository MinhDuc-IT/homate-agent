from homate_ai.clients.backend import BackendClient


class WorkflowClient(BackendClient):
    async def begin(self, token, request_id, text, conversation_id=None, version=None):
        return await self.request(token, 'POST', '/api/dashboard/agent/turns/begin', json={
            'request_id': request_id, 'text': text, 'conversation_id': conversation_id, 'expected_version': version})

    async def commit(self, token, request_id, state, response, invalidate=False, steps=None, summary='Kế hoạch HomeMate', lease_id=None):
        return await self.request(token, 'POST', f'/api/dashboard/agent/turns/{request_id}/commit', json={
            'state': state, 'response': response, 'invalidate': invalidate, 'steps': steps or [], 'summary': summary[:2000], 'lease_id': lease_id})

    async def abort(self, token, request_id, lease_id):
        return await self.request(token, 'POST', f'/api/dashboard/agent/turns/{request_id}/abort', json={'lease_id': lease_id})

    async def release(self, cleanup_token, request_id, lease_id):
        return await self.request(cleanup_token, 'POST', f'/api/dashboard/agent/turns/{request_id}/release',
                                  json={'lease_id': lease_id})

    async def plan(self, token, plan_id):
        return await self.request(token, 'GET', f'/api/dashboard/agent/plans/{plan_id}')
