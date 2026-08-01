from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from cores.economy.escrow import EscrowManager, escrow_manager
from cores.economy.registry import CapabilityCategory, CapabilityRegistry, registry
from cores.economy.reputation import ReputationEngine, ReputationEvent, ReputationEventType, reputation_engine
from cores.economy.settlement import SettlementEngine, settlement_engine


class JobStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class BidStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


@dataclass(slots=True)
class Job:
    id: str
    requester_id: str
    title: str
    description: str
    category: CapabilityCategory
    required_tags: list[str] = field(default_factory=list)
    budget: float = 0.0
    currency: str = "USDC"
    status: JobStatus = JobStatus.OPEN
    escrow_id: str | None = None
    assigned_provider: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    assigned_at: datetime | None = None
    deadline: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return self.deadline and datetime.utcnow() > self.deadline


@dataclass(slots=True)
class Bid:
    id: str
    job_id: str
    provider_id: str
    amount: float
    currency: str = "USDC"
    estimated_duration: timedelta | None = None
    message: str = ""
    status: BidStatus = BidStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    accepted_at: datetime | None = None


@dataclass(slots=True)
class Delivery:
    id: str
    job_id: str
    provider_id: str
    content: dict[str, Any]
    evidence: dict[str, Any] = field(default_factory=dict)
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    accepted: bool | None = None
    reviewed_at: datetime | None = None


class Marketplace:
    def __init__(
        self,
        capability_registry: CapabilityRegistry = registry,
        escrow_mgr: EscrowManager = escrow_manager,
        reputation: ReputationEngine = reputation_engine,
        settlement: SettlementEngine = settlement_engine,
    ):
        self.registry = capability_registry
        self.escrow = escrow_mgr
        self.reputation = reputation
        self.settlement = settlement
        self._jobs: dict[str, Job] = {}
        self._bids: dict[str, list[Bid]] = {}
        self._deliveries: dict[str, Delivery] = {}
        self._match_hooks: list[Callable[[Job, list[Bid]], str | None]] = []

    def register_match_hook(self, hook: Callable[[Job, list[Bid]], str | None]) -> None:
        self._match_hooks.append(hook)

    def post_job(
        self,
        requester_id: str,
        title: str,
        description: str,
        category: CapabilityCategory,
        budget: float,
        required_tags: list[str] | None = None,
        deadline_hours: int = 24,
        currency: str = "USDC",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = Job(
            id=job_id,
            requester_id=requester_id,
            title=title,
            description=description,
            category=category,
            required_tags=required_tags or [],
            budget=budget,
            currency=currency,
            deadline=datetime.utcnow() + timedelta(hours=deadline_hours),
            metadata=metadata or {},
        )
        self._jobs[job_id] = job
        self._bids[job_id] = []
        return job_id

    def place_bid(
        self,
        job_id: str,
        provider_id: str,
        amount: float,
        estimated_duration: timedelta | None = None,
        message: str = "",
    ) -> str | None:
        job = self._jobs.get(job_id)
        if not job or job.status != JobStatus.OPEN:
            return None
        if amount > job.budget * 1.2:
            return None
        provider = self.registry.get_agent(provider_id)
        if not provider or not provider.is_available():
            return None
        caps = self.registry.find_capabilities(category=job.category, tags=job.required_tags, max_price=amount)
        if not any(provider_id in c.provider_id for c in caps):
            return None
        bid_id = f"bid_{uuid.uuid4().hex[:12]}"
        bid = Bid(
            id=bid_id,
            job_id=job_id,
            provider_id=provider_id,
            amount=amount,
            currency=job.currency,
            estimated_duration=estimated_duration,
            message=message,
        )
        self._bids.setdefault(job_id, []).append(bid)
        return bid_id

    def accept_bid(self, job_id: str, bid_id: str, requester_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.requester_id != requester_id or job.status != JobStatus.OPEN:
            return False
        bids = self._bids.get(job_id, [])
        bid = next((b for b in bids if b.id == bid_id), None)
        if not bid or bid.status != BidStatus.PENDING:
            return False
        for hook in self._match_hooks:
            chosen = hook(job, bids)
            if chosen and chosen != bid_id:
                return False
        escrow_id = self.escrow.create_escrow(
            requester_id=requester_id,
            provider_id=bid.provider_id,
            amount=bid.amount,
            currency=job.currency,
            description=f"Job {job_id}: {job.title}",
            expires_in=job.deadline - datetime.utcnow() if job.deadline else None,
            auto_release_after=timedelta(hours=2),
        )
        if not self.escrow.fund_escrow(escrow_id, requester_id):
            return False
        if not self.escrow.lock_escrow(escrow_id):
            return False
        bid.status = BidStatus.ACCEPTED
        bid.accepted_at = datetime.utcnow()
        for b in bids:
            if b.id != bid_id:
                b.status = BidStatus.REJECTED
        job.status = JobStatus.ASSIGNED
        job.assigned_provider = bid.provider_id
        job.assigned_at = datetime.utcnow()
        job.escrow_id = escrow_id
        return True

    def submit_delivery(
        self, job_id: str, provider_id: str, content: dict[str, Any], evidence: dict[str, Any] | None = None
    ) -> str | None:
        job = self._jobs.get(job_id)
        if not job or job.status != JobStatus.ASSIGNED or job.assigned_provider != provider_id:
            return None
        delivery_id = f"del_{uuid.uuid4().hex[:12]}"
        delivery = Delivery(
            id=delivery_id,
            job_id=job_id,
            provider_id=provider_id,
            content=content,
            evidence=evidence or {},
        )
        self._deliveries[delivery_id] = delivery
        job.status = JobStatus.SUBMITTED
        return delivery_id

    def accept_delivery(self, job_id: str, delivery_id: str, requester_id: str) -> bool:
        job = self._jobs.get(job_id)
        delivery = self._deliveries.get(delivery_id)
        if not job or not delivery or job.requester_id != requester_id:
            return False
        if job.status != JobStatus.SUBMITTED or delivery.job_id != job_id:
            return False
        delivery.accepted = True
        delivery.reviewed_at = datetime.utcnow()
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        escrow = self.escrow.get_escrow(job.escrow_id) if job.escrow_id else None
        if escrow:
            self.escrow.release_escrow(job.escrow_id, requester_id)
        self._finalize_job(job, delivery, success=True)
        return True

    def reject_delivery(self, job_id: str, delivery_id: str, requester_id: str, reason: str) -> bool:
        job = self._jobs.get(job_id)
        delivery = self._deliveries.get(delivery_id)
        if not job or not delivery or job.requester_id != requester_id:
            return False
        if job.status != JobStatus.SUBMITTED:
            return False
        delivery.accepted = False
        delivery.reviewed_at = datetime.utcnow()
        job.status = JobStatus.FAILED
        escrow = self.escrow.get_escrow(job.escrow_id) if job.escrow_id else None
        if escrow:
            self.escrow.open_dispute(job.escrow_id, requester_id, reason, {"delivery_id": delivery_id})
        self._finalize_job(job, delivery, success=False)
        return True

    def _finalize_job(self, job: Job, delivery: Delivery, success: bool) -> None:
        if job.assigned_provider:
            self.registry.record_job_completion(
                job.assigned_provider,
                earnings=delivery.content.get("earnings", 0) if success else 0,
                success=success,
                duration=(delivery.submitted_at - (job.assigned_at or datetime.utcnow())).total_seconds(),
            )
            event_type = ReputationEventType.JOB_COMPLETED if success else ReputationEventType.JOB_FAILED
            self.reputation.record_event(
                ReputationEvent(
                    agent_id=job.assigned_provider,
                    event_type=event_type,
                    delta=1.0 if success else -1.0,
                    related_entity_id=job.id,
                )
            )
        if job.requester_id:
            self.reputation.record_event(
                ReputationEvent(
                    agent_id=job.requester_id,
                    event_type=ReputationEventType.PAYMENT_SENT if success else ReputationEventType.JOB_FAILED,
                    delta=0.5 if success else -0.5,
                    related_entity_id=job.id,
                )
            )

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def get_bids(self, job_id: str) -> list[Bid]:
        return self._bids.get(job_id, [])

    def get_delivery(self, delivery_id: str) -> Delivery | None:
        return self._deliveries.get(delivery_id)

    def list_open_jobs(self, category: CapabilityCategory | None = None) -> list[Job]:
        jobs = [j for j in self._jobs.values() if j.status == JobStatus.OPEN]
        if category:
            jobs = [j for j in jobs if j.category == category]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)


marketplace = Marketplace()
