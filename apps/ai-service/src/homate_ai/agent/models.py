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


class AgentUnavailable(Exception): pass
class BackendError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)
