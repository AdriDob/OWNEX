from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from threading import Lock
from concurrent.futures import ThreadPoolExecutor


class MessageType(str, Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    NODE_DISCOVERED = "node_discovered"
    EDGE_DISCOVERED = "edge_discovered"
    VULN_FOUND = "vuln_found"
    EXPLOIT_READY = "exploit_ready"
    POC_VALIDATED = "poc_validated"
    EVIDENCE_COLLECTED = "evidence_collected"
    SWARM_STATUS = "swarm_status"
    AGENT_HEARTBEAT = "agent_heartbeat"
    COORDINATION = "coordination"
    BROADCAST = "broadcast"
    QUERY = "query"
    RESPONSE = "response"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(slots=True)
class AgentMessage:
    id: str
    type: MessageType
    sender: str
    recipient: str | None
    payload: dict[str, Any]
    priority: Priority = Priority.NORMAL
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str | None = None
    expires_at: datetime | None = None
    requires_ack: bool = False


class MessageBus:
    def __init__(self, max_workers: int = 4):
        self._subscriptions: dict[str, list[Callable]] = defaultdict(list)
        self._agent_queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._broadcast_queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running = True
        self._message_history: list[AgentMessage] = []
        self._max_history = 10000

    def subscribe(self, agent_id: str, msg_type: MessageType, handler: Callable) -> None:
        key = f"{agent_id}:{msg_type.value}"
        with self._lock:
            self._subscriptions[key].append(handler)

    def subscribe_all(self, agent_id: str, handler: Callable) -> None:
        key = f"{agent_id}:*"
        with self._lock:
            self._subscriptions[key].append(handler)

    def publish(self, message: AgentMessage) -> bool:
        with self._lock:
            self._message_history.append(message)
            if len(self._message_history) > self._max_history:
                self._message_history = self._message_history[-self._max_history :]

        recipients = [message.recipient] if message.recipient else []
        if message.type == MessageType.BROADCAST:
            with self._lock:
                recipients = list(self._agent_queues.keys())

        for recipient in recipients:
            if recipient in self._agent_queues:
                try:
                    self._agent_queues[recipient].put_nowait(message)
                except asyncio.QueueFull:
                    pass

        self._deliver_to_handlers(message)
        return True

    def _deliver_to_handlers(self, message: AgentMessage) -> None:
        handlers = []
        with self._lock:
            specific_key = f"{message.recipient}:{message.type.value}" if message.recipient else None
            wildcard_key = f"{message.recipient}:*" if message.recipient else None
            if specific_key:
                handlers.extend(self._subscriptions.get(specific_key, []))
            if wildcard_key:
                handlers.extend(self._subscriptions.get(wildcard_key, []))
            if message.type == MessageType.BROADCAST:
                for key, hs in self._subscriptions.items():
                    if key.endswith(f":{message.type.value}") or key.endswith(":*"):
                        handlers.extend(hs)

        for handler in handlers:
            try:
                self._executor.submit(handler, message)
            except Exception:
                pass

    def get_queue(self, agent_id: str) -> asyncio.Queue:
        if agent_id not in self._agent_queues:
            self._agent_queues[agent_id] = asyncio.Queue(maxsize=1000)
        return self._agent_queues[agent_id]

    async def receive(self, agent_id: str, timeout: float | None = None) -> AgentMessage | None:
        queue = self.get_queue(agent_id)
        try:
            if timeout:
                return await asyncio.wait_for(queue.get(), timeout=timeout)
            return await queue.get()
        except asyncio.TimeoutError:
            return None

    def send_direct(
        self, sender: str, recipient: str, msg_type: MessageType, payload: dict[str, Any], **kwargs
    ) -> bool:
        msg = AgentMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            type=msg_type,
            sender=sender,
            recipient=recipient,
            payload=payload,
            **kwargs,
        )
        return self.publish(msg)

    def broadcast(self, sender: str, msg_type: MessageType, payload: dict[str, Any], **kwargs) -> bool:
        msg = AgentMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            type=msg_type,
            sender=sender,
            recipient=None,
            payload=payload,
            **kwargs,
        )
        return self.publish(msg)

    def request_response(
        self, sender: str, recipient: str, msg_type: MessageType, payload: dict[str, Any], timeout: float = 30.0
    ) -> Any | None:
        correlation_id = uuid.uuid4().hex
        future = asyncio.Future()

        def response_handler(msg: AgentMessage):
            if msg.correlation_id == correlation_id:
                future.set_result(msg.payload)

        self.subscribe(recipient, msg_type, response_handler)
        self.send_direct(sender, recipient, msg_type, payload, correlation_id=correlation_id, requires_ack=True)

        return future

    def get_history(
        self, agent_id: str | None = None, msg_type: MessageType | None = None, limit: int = 100
    ) -> list[AgentMessage]:
        with self._lock:
            msgs = self._message_history
            if agent_id:
                msgs = [m for m in msgs if m.sender == agent_id or m.recipient == agent_id]
            if msg_type:
                msgs = [m for m in msgs if m.type == msg_type]
            return msgs[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_messages": len(self._message_history),
            "active_agents": len(self._agent_queues),
            "subscriptions": sum(len(v) for v in self._subscriptions.values()),
        }

    def shutdown(self) -> None:
        self._running = False
        self._executor.shutdown(wait=True)


message_bus = MessageBus()
