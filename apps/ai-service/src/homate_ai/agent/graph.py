from typing import Literal
from langgraph.graph import END, START, StateGraph
from homate_ai.agent.executor import ToolExecutor
from homate_ai.agent.nodes import AgentNodes
from homate_ai.agent.state import AgentState
from homate_ai.contracts import BackendTools, KnowledgeRetriever, LanguageModel


def after_model(state: AgentState) -> Literal['execute_tools', 'respond']:
    return 'execute_tools' if state['model_reply'].calls else 'respond'


def after_tools(state: AgentState) -> Literal['call_model', 'respond']:
    # Durable backend proposals are returned without another provider call.
    return 'respond' if state['pending_actions'] else 'call_model'


def build_graph(nodes: AgentNodes):
    builder = StateGraph(AgentState)
    builder.add_node('authenticate', nodes.authenticate)
    builder.add_node('call_model', nodes.call_model)
    builder.add_node('execute_tools', nodes.execute_tools)
    builder.add_node('respond', nodes.respond)
    builder.add_edge(START, 'authenticate')
    builder.add_edge('authenticate', 'call_model')
    builder.add_conditional_edges('call_model', after_model)
    builder.add_conditional_edges('execute_tools', after_tools)
    builder.add_edge('respond', END)
    # Request state only: credentials must never be written to a checkpointer.
    return builder.compile()


class Agent:
    def __init__(self, model: LanguageModel, backend: BackendTools, max_rounds=6,
                 retriever: KnowledgeRetriever | None = None):
        if max_rounds < 1:
            raise ValueError('max_rounds must be positive')
        self.max_rounds = max_rounds
        self.graph = build_graph(AgentNodes(model, backend, ToolExecutor(backend, retriever), max_rounds))

    async def chat(self, token, request_id, text, history):
        result = await self.graph.ainvoke({
            'token': token, 'request_id': request_id, 'text': text, 'history': history,
            'messages': [], 'rounds': 0, 'trace': [], 'pending_actions': [], 'sources': [],
        }, config={'recursion_limit': self.max_rounds * 2 + 5})
        return {key: result[key] for key in ('reply', 'pending_actions', 'trace', 'sources')}
