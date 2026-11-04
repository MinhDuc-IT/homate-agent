"""Agent writes require an explicit, durable decision from their requesting user."""
from typing import Protocol, Callable


class ActionRepository(Protocol):
    def propose(self, user: dict, request_id: str, tool: str, arguments: dict, summary: str, ttl: int) -> dict: ...
    def claim(self, user: dict, identifier: str, approved: bool) -> dict: ...
    def finish(self, identifier: str, status: str, result: dict) -> dict: ...


class AgentActionService:
    def __init__(self, repository: ActionRepository):
        self.repository = repository

    def propose(self, user, request_id, tool, arguments, summary, ttl):
        return self.repository.propose(user, request_id, tool, arguments, summary, ttl)

    def decide(self, user, identifier, approved, execute: Callable):
        receipt = self.repository.claim(user, identifier, approved)
        if not receipt.pop("claimed", False):
            return receipt
        try:
            result = execute(receipt["tool"], receipt["arguments"])
        except Exception:
            self.repository.finish(identifier, "failed", {"message": "Thao tác thất bại; kiểm tra trạng thái trước khi gửi yêu cầu mới."})
            raise
        return self.repository.finish(identifier, "executed", result)
