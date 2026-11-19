from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class ModelReply:
    text: str = ''
    calls: list[ToolCall] = field(default_factory=list)


class AgentUnavailable(Exception):
    def __init__(self, message, code='agent_unavailable', provider_status=None):
        self.code = code
        self.provider_status = provider_status
        super().__init__(message)
class BackendError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)
