"""WebSocket connection manager for realtime device updates."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect, WebSocketState

logger = logging.getLogger(__name__)

# Drop unanswered HITL / clarify entries after this many seconds.
PENDING_TTL_SECONDS = 300


class ConnectionManager:
    """Track active WS clients and broadcast JSON payloads.

    Mutations are guarded by an ``asyncio.Lock`` so connect/disconnect/broadcast
    cannot interleave unsafely on the event loop.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.debug("WS connected (%s clients)", self.connection_count)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            removed = websocket in self._connections
            self._connections.discard(websocket)
        if removed:
            logger.debug("WS disconnected (%s clients)", self.connection_count)

    async def send_json(self, websocket: WebSocket, data: dict[str, Any]) -> bool:
        """Send to one client. Returns False and drops client on failure."""
        if websocket.client_state != WebSocketState.CONNECTED:
            await self.disconnect(websocket)
            return False
        try:
            await websocket.send_json(data)
            return True
        except (WebSocketDisconnect, RuntimeError) as exc:
            logger.debug("WS send failed, dropping client: %s", exc)
            await self.disconnect(websocket)
            return False

    async def broadcast_json(self, data: dict[str, Any]) -> None:
        """Send payload to a snapshot of clients; drop dead connections."""
        async with self._lock:
            recipients = list(self._connections)

        stale: list[WebSocket] = []
        for websocket in recipients:
            try:
                if websocket.client_state != WebSocketState.CONNECTED:
                    stale.append(websocket)
                    continue
                await websocket.send_json(data)
            except (WebSocketDisconnect, RuntimeError) as exc:
                logger.debug("WS broadcast failed: %s", exc)
                stale.append(websocket)

        if not stale:
            return
        async with self._lock:
            for websocket in stale:
                self._connections.discard(websocket)

    async def broadcast_model(self, message: BaseModel) -> None:
        """Broadcast a Pydantic WS message (snapshot / device.updated / ping)."""
        await self.broadcast_json(message.model_dump(mode="json"))


class AgentTraceManager:
    """Session-scoped trace fan-out with a small replay buffer for late clients."""

    def __init__(self, max_events_per_session: int = 80) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()
        self._max_events = max_events_per_session

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(session_id, set()).add(websocket)
            replay = list(self._events.get(session_id, []))
        for event in replay:
            if not await self._send(websocket, session_id, event):
                return

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(session_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(session_id, None)

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            if event.get("phase") == "started":
                self._events[session_id] = []
            buffer = self._events.setdefault(session_id, [])
            buffer.append(event)
            del buffer[:-self._max_events]
            sockets = list(self._connections.get(session_id, set()))

        stale: list[WebSocket] = []
        for websocket in sockets:
            if not await self._send(websocket, session_id, event):
                stale.append(websocket)
        for websocket in stale:
            await self.disconnect(session_id, websocket)

    @staticmethod
    async def _send(websocket: WebSocket, session_id: str, event: dict[str, Any]) -> bool:
        if websocket.client_state != WebSocketState.CONNECTED:
            return False
        try:
            await websocket.send_json({"type": "agent.trace", "session_id": session_id, "payload": event})
            return True
        except (WebSocketDisconnect, RuntimeError):
            return False


@dataclass
class PendingHitlRequest:
    session_id: str
    action_summary: str
    device_id: str | None = None
    action: str | None = None
    parameters: dict[str, Any] | None = None
    room: str = ""
    device_type: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class PendingClarifyRequest:
    session_id: str
    question: str
    original_text: str = ""
    created_at: float = field(default_factory=time.time)


class PendingHitlStore:
    """In-memory HITL / clarify bridge keyed by request_id / session_id."""

    def __init__(self, ttl_seconds: float = PENDING_TTL_SECONDS) -> None:
        self._by_id: dict[str, PendingHitlRequest] = {}
        self._clarify_by_session: dict[str, PendingClarifyRequest] = {}
        self._ui_manager: ConnectionManager | None = None
        self._ttl_seconds = ttl_seconds

    def bind_ui_manager(self, manager: ConnectionManager) -> None:
        self._ui_manager = manager

    def set_ttl_seconds(self, ttl_seconds: float) -> None:
        self._ttl_seconds = max(5.0, min(300.0, float(ttl_seconds)))
        self.purge_expired()

    def purge_expired(self) -> int:
        """Remove stale pending HITL/clarify entries. Returns number removed."""
        now = time.time()
        expired_hitl = [
            rid
            for rid, req in self._by_id.items()
            if now - req.created_at > self._ttl_seconds
        ]
        for rid in expired_hitl:
            self._by_id.pop(rid, None)
        expired_clarify = [
            sid
            for sid, req in self._clarify_by_session.items()
            if now - req.created_at > self._ttl_seconds
        ]
        for sid in expired_clarify:
            self._clarify_by_session.pop(sid, None)
        removed = len(expired_hitl) + len(expired_clarify)
        if removed:
            logger.info(
                "[PENDING] purged expired hitl=%s clarify=%s ttl=%ss",
                len(expired_hitl),
                len(expired_clarify),
                self._ttl_seconds,
            )
        return removed

    def pop(self, request_id: str) -> PendingHitlRequest | None:
        self.purge_expired()
        return self._by_id.pop(request_id, None)

    def get_hitl(self, request_id: str) -> PendingHitlRequest | None:
        self.purge_expired()
        return self._by_id.get(request_id)

    def get_clarify(self, session_id: str) -> PendingClarifyRequest | None:
        self.purge_expired()
        return self._clarify_by_session.get(session_id)

    def pop_clarify(self, session_id: str) -> PendingClarifyRequest | None:
        self.purge_expired()
        return self._clarify_by_session.pop(session_id, None)

    def save_clarify(
        self,
        session_id: str,
        *,
        question: str,
        original_text: str = "",
    ) -> PendingClarifyRequest:
        self.purge_expired()
        existing = self._clarify_by_session.get(session_id)
        merged_original = original_text or (existing.original_text if existing else "")
        merged_question = question or (existing.question if existing else "")
        pending = PendingClarifyRequest(
            session_id=session_id,
            question=merged_question,
            original_text=merged_original,
        )
        self._clarify_by_session[session_id] = pending
        return pending

    async def push_clarify(
        self,
        session_id: str,
        question: str,
        original_text: str = "",
    ) -> None:
        self.save_clarify(session_id, question=question, original_text=original_text)
        if self._ui_manager is None:
            return
        await self._ui_manager.broadcast_json(
            {
                "type": "clarify",
                "session_id": session_id,
                "question": question,
                "original_text": original_text,
            }
        )

    async def push_hitl(
        self,
        session_id: str,
        action_summary: str,
        *,
        device_id: str | None = None,
        action: str | None = None,
        parameters: dict[str, Any] | None = None,
        room: str = "",
        device_type: str = "",
    ) -> str:
        self.purge_expired()
        request_id = str(uuid.uuid4())
        self._by_id[request_id] = PendingHitlRequest(
            session_id=session_id,
            action_summary=action_summary,
            device_id=device_id,
            action=action,
            parameters=parameters or {},
            room=room,
            device_type=device_type,
        )
        if self._ui_manager is not None:
            await self._ui_manager.broadcast_json(
                {
                    "type": "hitl",
                    "request_id": request_id,
                    "session_id": session_id,
                    "action_summary": action_summary,
                    "device_id": device_id,
                    "action": action,
                }
            )
        return request_id


pending_hitl = PendingHitlStore()
agent_trace = AgentTraceManager()


async def notify_device_updated(ws_manager: ConnectionManager, device: Any) -> None:
    """Broadcast device.updated to Visual UI clients."""
    from homate.modules.home.domain.device import WsDeviceUpdatedMessage

    await ws_manager.broadcast_model(
        WsDeviceUpdatedMessage(
            device_id=device.id,
            state=dict(device.state),
        )
    )
