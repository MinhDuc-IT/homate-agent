import asyncio
from uuid import uuid4
from homate_ai.application.orchestrator import Agent
from homate_ai.domain.conversation import ModelReply, ToolCall, BackendError
import httpx
from homate_ai.infrastructure.rag import HttpKnowledgeRetriever


class Model:
    def __init__(self, replies): self.replies, self.messages = iter(replies), []
    async def complete(self, messages, tools):
        self.messages.append(list(messages))
        return next(self.replies)


class Backend:
    async def identity(self, token): return {'id':'user','role':'member','home_id':'home'}
    async def call(self, token, request_id, tool, arguments):
        raise AssertionError('Knowledge must not be routed through backend tools')


class Retriever:
    async def retrieve(self, token, query, device_id=None):
        assert token == 'valid'
        return [{'chunk_id':'chunk', 'document_id':'doc', 'title':'Guide', 'content':'Use the confirm button.', 'ordinal':0, 'metadata':{}}]


def test_retrieval_reaches_model_and_returns_grounded_source_metadata():
    model = Model([ModelReply(calls=[ToolCall('call','search_knowledge',{'query':'How to use HomeMate?'})]), ModelReply('Use confirm [1].')])
    result = asyncio.run(Agent(model,Backend(),retriever=Retriever()).chat('valid',str(uuid4()),'Help',[]))
    assert result['sources'][0]['citation'] == 1
    assert result['sources'][0]['content'] == 'Use the confirm button.'
    assert 'Use the confirm button.' in model.messages[-1][-1]['content']
    assert not result['pending_actions']


def test_empty_knowledge_and_unavailable_backend_return_no_invented_sources():
    class Empty:
        async def retrieve(self, *args): return []
    class Unavailable:
        async def retrieve(self, *args): raise BackendError(503, 'Unavailable')
    for retriever in (Empty(),Unavailable()):
        model = Model([ModelReply(calls=[ToolCall('call','search_knowledge',{'query':'Help'})]), ModelReply('No information.')])
        result = asyncio.run(Agent(model,Backend(),retriever=retriever).chat('valid',str(uuid4()),'Help',[]))
        assert result['sources'] == []


def test_model_cannot_supply_home_id_to_knowledge_search():
    class Never(Backend):
        async def call(self, *args): raise AssertionError('Unexpected backend call')
    model = Model([ModelReply(calls=[ToolCall('call','search_knowledge',{'query':'Help','home_id':'other'})]), ModelReply('Invalid request')])
    result = asyncio.run(Agent(model,Never()).chat('valid',str(uuid4()),'Help',[]))
    assert result['trace'][0]['status'] == 400
    assert result['sources'] == []


def test_http_retriever_calls_rag_service_directly_with_user_token():
    async def run():
        def handler(request):
            assert request.url.path == '/api/rag/search'
            assert request.headers['authorization'] == 'Bearer valid'
            assert dict(request.url.params) == {'query':'Help','device_id':'light'}
            return httpx.Response(200,json={'chunks':[]})
        async with httpx.AsyncClient(base_url='http://rag',transport=httpx.MockTransport(handler)) as client:
            assert await HttpKnowledgeRetriever(client).retrieve('valid','Help','light') == []
    asyncio.run(run())
