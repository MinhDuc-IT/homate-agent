"""The chat/voice workflow and its cached-request exit."""
from typing import Literal
from langgraph.graph import END, START, StateGraph
from homate_ai.agent.state import ConversationState


def after_load(state) -> Literal['interpret', '__end__']:
    return END if state['cached'] else 'interpret'


def build_graph(nodes):
    builder = StateGraph(ConversationState)
    names = ('load_dialogue', 'interpret', 'gather_data', 'plan_scope', 'ground', 'validate', 'decide', 'remember', 'commit')
    for name in names:
        builder.add_node(name, getattr(nodes, name))
    builder.add_edge(START, names[0])
    builder.add_conditional_edges(names[0], after_load)
    for before, after in zip(names[1:], names[2:]):
        builder.add_edge(before, after)
    builder.add_edge(names[-1], END)
    return builder.compile()
