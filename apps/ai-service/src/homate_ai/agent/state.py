from homate_ai.agent.analysis import AnalysisState


class ConversationState(AnalysisState, total=False):
    conversation_id: str | None
    conversation_version: int | None
    session: dict
    cached: bool
    response: dict
    fixed_reply: str
    planning_error: str
    steps: list[dict]
    next_state: dict
    invalidate: bool
    lease: dict
    observations: list[dict]
