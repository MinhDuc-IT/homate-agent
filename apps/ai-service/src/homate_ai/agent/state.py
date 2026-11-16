from typing import TypedDict
from homate_ai.agent.models import ModelReply


class AgentState(TypedDict):
    token: str
    request_id: str
    text: str
    history: list[dict]
    messages: list[dict]
    rounds: int
    model_reply: ModelReply
    reply: str
    trace: list[dict]
    pending_actions: list[dict]
    sources: list[dict]
