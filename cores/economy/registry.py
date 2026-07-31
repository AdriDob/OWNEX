from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CapabilityCategory(str, Enum):
    RECON = "recon"
    FUZZING = "fuzzing"
    EXPLOIT_GENERATION = "exploit_generation"
    BYPASS = "bypass"
    VALIDATION = "validation"
    EVIDENCE_COLLECTION = "evidence_collection"
    REPORTING = "reporting"
    POST_EXPLOITATION = "post_exploitation"


class PricingModel(str, Enum):
    PER_USE = "per_use"
    PER_HOUR = "per_hour"
    PER_FINDING = "per_finding"
    SUBSCRIPTION = "subscription"
    REVENUE_SHARE = "revenue_share"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"
    DISPUTED = "disputed"
    SUSPENDED = "suspended"


@dataclass(slots=True)
class Capability:
    id: str
    name: str
    category: CapabilityCategory
    description: str
    provider_id: str
    pricing_model: PricingModel
    base_price: float
    currency: str = "USDC"
    min_price: float = 0.0
    max_price: float = 10000.0
    sla_seconds: int = 300
    success_rate: float = 1.0
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def can_handle(self, task_type: str, budget: float) -> bool:
        if budget < self.min_price or budget > self.max_price:
            return False
        return task_type.lower() in self.tags or self.category.value in task_type.lower()


@dataclass(slots=True)
class AgentProfile:
    id: str
    name: str
    owner_id: str
    capabilities: list[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.ACTIVE
    reputation_score: float = 100.0
    total_earnings: float = 0.0
    total_jobs: int = 0
    success_rate: float = 1.0
    avg_completion_time: float = 0.0
    stake: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)

    def is_available(self) -> bool:
        return self.status == AgentStatus.ACTIVE and self.stake > 0


class CapabilityRegistry:
    def __init__(self):
        self._capabilities: dict[str, Capability] = {}
        self._agents: dict[str, AgentProfile] = {}
        self._category_index: dict[CapabilityCategory, set[str]] = {cat: set() for cat in CapabilityCategory}
        self._provider_index: dict[str, set[str]] = {}

    def register_capability(self, capability: Capability) -> str:
        if capability.id in self._capabilities:
            raise ValueError(f"Capability {capability.id} already exists")
        self._capabilities[capability.id] = capability
        self._category_index[capability.category].add(capability.id)
        self._provider_index.setdefault(capability.provider_id, set()).add(capability.id)
        return capability.id

    def register_agent(self, agent: AgentProfile) -> str:
        if agent.id in self._agents:
            raise ValueError(f"Agent {agent.id} already exists")
        self._agents[agent.id] = agent
        return agent.id

    def find_capabilities(
        self,
        category: CapabilityCategory | None = None,
        tags: list[str] | None = None,
        max_price: float | None = None,
        min_success_rate: float = 0.0,
    ) -> list[Capability]:
        candidates = list(self._capabilities.values())
        if category:
            candidates = [c for c in candidates if c.category == category]
        if tags:
            tag_set = set(tags)
            candidates = [c for c in candidates if any(t in c.tags for t in tags)]
        if max_price is not None:
            candidates = [c for c in candidates if c.base_price <= max_price]
        if min_success_rate > 0:
            candidates = [c for c in candidates if c.success_rate >= min_success_rate]
        return sorted(candidates, key=lambda c: (c.base_price, -c.success_rate))

    def get_capability(self, capability_id: str) -> Capability | None:
        return self._capabilities.get(capability_id)

    def get_agent(self, agent_id: str) -> AgentProfile | None:
        return self._agents.get(agent_id)

    def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.status = status
        agent.last_active = datetime.utcnow()
        return True

    def update_agent_reputation(self, agent_id: str, delta: float) -> float | None:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.reputation_score = max(0.0, min(1000.0, agent.reputation_score + delta))
        return agent.reputation_score

    def record_job_completion(self, agent_id: str, earnings: float, success: bool, duration: float) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.total_jobs += 1
        agent.total_earnings += earnings
        agent.success_rate = (
            agent.success_rate * (agent.total_jobs - 1) + (1.0 if success else 0.0)
        ) / agent.total_jobs
        agent.avg_completion_time = (agent.avg_completion_time * (agent.total_jobs - 1) + duration) / agent.total_jobs
        agent.last_active = datetime.utcnow()
        return True


registry = CapabilityRegistry()
