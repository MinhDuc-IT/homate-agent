import asyncio
from uuid import uuid4
import httpx
from homate_ai.agent.runtime import ConversationAgent
from homate_ai.agent.models import ModelReply, BackendError
from homate_ai.clients.rag import HttpKnowledgeRetriever
from test_runtime import Backend, Model, Workflow
from test_analysis import output, interpretation


def knowledge_request(arguments):
    return output(interpretation({'goal': 'Help', 'capability': 'search_knowledge', 'arguments': arguments}, 'query'))


def test_retrieval_reaches_model_and_returns_grounded_sources():
    model = Model([knowledge_request({'query': 'How to use HomeMate?'}), ModelReply('Use confirm [1].')])
    result = asyncio.run(ConversationAgent(model, Backend(), Workflow(), retriever=Retriever()).chat('valid', str(uuid4()), 'Help', []))
    assert result['sources'][0]['citation'] == 1
    assert result['sources'][0]['content'] == 'Use the confirm button.'
    assert 'Use the confirm button.' in str(model.messages[-1])
    assert not result['pending_actions']


def test_empty_and_unavailable_retrieval_do_not_invent_sources():
    class Empty:
        async def retrieve(self, *args): return []
    class Unavailable:
        async def retrieve(self, *args): raise BackendError(503, 'Unavailable')
    for retriever in (Empty(), Unavailable()):
        model = Model([knowledge_request({'query': 'Help'}), ModelReply('No information.')])
        result = asyncio.run(ConversationAgent(model, Backend(), Workflow(), retriever=retriever).chat('valid', str(uuid4()), 'Help', []))
        assert result['sources'] == []


def test_model_cannot_supply_a_home_id_to_knowledge_search():
    class Never:
        async def retrieve(self, *args): raise AssertionError('Foreign scope must be blocked before RAG')
    model = Model([knowledge_request({'query': 'Help', 'home_id': 'other'})])
    workflow = Workflow()
    result = asyncio.run(ConversationAgent(model, Backend(), workflow, retriever=Never()).chat('valid', str(uuid4()), 'Help', []))
    assert not result['sources'] and not result['pending_actions']
    assert workflow.commits[-1]['steps'] == []


class Retriever:
    async def retrieve(self, token, query, device_id=None):
        assert token == 'valid'
        return [{'chunk_id':'chunk', 'document_id':'doc', 'title':'Guide', 'content':'Use the confirm button.', 'ordinal':0, 'metadata':{}}]



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
