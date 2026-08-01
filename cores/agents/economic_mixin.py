"""Economic agent mixin — adds Agent Economy + Swarm participation to any BaseAgent."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from cores.economy import (
    AgentProfile,
    Capability,
    CapabilityCategory,
    marketplace,
    registry,
    reputation_engine,
)
from cores.economy import (
    AgentStatus as EconAgentStatus,
)
from cores.swarm import coordinator, message_bus
from cores.swarm.communication import AgentMessage, MessageType, Priority


# Lazy imports for learning to avoid circular imports
def _get_learning():
    from cores.learning import embed_engagement, record_engagement_outcome

    return embed_engagement, record_engagement_outcome


@dataclass(slots=True)
class EconomicTraits:
    """Economic profile for an agent."""

    agent_id: str
    stake: float = 0.0
    capabilities_registered: list[str] = field(default_factory=list)
    total_earnings: float = 0.0
    jobs_completed: int = 0
    jobs_failed: int = 0
    current_swarm: str | None = None
    swarm_role: str | None = None
    last_bid_at: float = 0
    auto_bid_enabled: bool = True
    min_bid_margin: float = 0.1
    max_concurrent_jobs: int = 3
    current_jobs: int = 0


class EconomicAgentMixin:
    """
    Mixin that adds Agent Economy + Swarm participation to a BaseAgent.

    Usage:
        class MyAgent(BaseAgent, EconomicAgentMixin):
            def __init__(self, *args, **kwargs):
                BaseAgent.__init__(self, *args, **kwargs)
                EconomicAgentMixin.__init__(self, stake=100.0, role=AgentRole.RECON)
    """

    def __init__(
        self,
        *args,
        stake: float = 100.0,
        role: str = "specialist",
        auto_register_capabilities: bool = True,
        auto_bid: bool = True,
        min_bid_margin: float = 0.1,
        max_concurrent_jobs: int = 3,
        **kwargs,
    ):
        # Initialize economic traits
        self._economic_traits = EconomicTraits(
            agent_id=self.agent_id.value if hasattr(self, "agent_id") else str(uuid.uuid4()),
            stake=stake,
            auto_bid_enabled=auto_bid,
            min_bid_margin=min_bid_margin,
            max_concurrent_jobs=max_concurrent_jobs,
        )
        self._economic_role = role
        self._swarm_tasks: dict[str, Any] = {}
        self._pending_deliveries: dict[str, Any] = {}

        # Register with economy registry
        self._register_with_economy(auto_register_capabilities)

        # Subscribe to economy/marketplace events
        self._subscribe_economy_events()

        # Call original init if needed
        if hasattr(super(), "__init__"):
            super().__init__(*args, **kwargs)

    def _register_with_economy(self, auto_register: bool) -> None:
        """Register this agent and its capabilities with the economy registry."""

        traits = self._economic_traits
        traits.agent_id = self.agent_id.value if hasattr(self, "agent_id") else str(uuid.uuid4())

        # Register agent profile
        profile = AgentProfile(
            id=traits.agent_id,
            name=self.name if hasattr(self, "name") else traits.agent_id,
            owner_id="system",
            capabilities=[],
            status=EconAgentStatus.ACTIVE,
            reputation_score=100.0,
            stake=traits.stake,
        )
        registry.register_agent(profile)

        # Register capabilities from agent's declared capabilities
        if hasattr(self, "capabilities") and self.capabilities:
            for cap_name in self.capabilities:
                self._register_capability_from_string(cap_name)

        # Subscribe to swarm messages
        message_bus.subscribe(traits.agent_id, MessageType.BROADCAST, self._on_swarm_message)
        message_bus.subscribe_all(traits.agent_id, self._on_any_economy_message)

    def _register_capability_from_string(self, cap_str: str) -> str | None:
        """Register a capability from a capability string like 'recon:subdomain_enum'."""
        try:
            parts = cap_str.split(":")
            if len(parts) >= 2:
                category_str = parts[0]
                name = parts[-1]

                cat_map = {
                    "recon": CapabilityCategory.RECON,
                    "fuzzing": CapabilityCategory.FUZZING,
                    "exploit": CapabilityCategory.EXPLOIT_GENERATION,
                    "exploit_generation": CapabilityCategory.EXPLOIT_GENERATION,
                    "bypass": CapabilityCategory.BYPASS,
                    "validation": CapabilityCategory.VALIDATION,
                    "evidence": CapabilityCategory.EVIDENCE_COLLECTION,
                    "reporting": CapabilityCategory.REPORTING,
                    "post_exploit": CapabilityCategory.POST_EXPLOITATION,
                }
                category = cat_map.get(category_str, CapabilityCategory.SPECIALIST)

                cap_id = f"cap_{self._economic_traits.agent_id}_{name}"
                cap = Capability(
                    id=cap_id,
                    name=name,
                    category=category,
                    description=f"Capability for {name}",
                    provider_id=self._economic_traits.agent_id,
                    pricing_model="per_use",
                    base_price=5.0,
                    min_price=1.0,
                    max_price=100.0,
                    tags=(name, category_str),
                    sla_seconds=300,
                )
                registry.register_capability(cap)
                self._economic_traits.capabilities_registered.append(cap_id)
                return cap_id
        except Exception:
            pass
        return None

    def _subscribe_economy_events(self) -> None:
        """Subscribe to marketplace and swarm events."""
        from cores.swarm.communication import MessageType

        message_bus.subscribe(self._economic_traits.agent_id, MessageType.TASK_ASSIGNED, self._on_task_assigned)
        message_bus.subscribe(self._economic_traits.agent_id, MessageType.TASK_COMPLETED, self._on_task_completed)
        message_bus.subscribe(self._economic_traits.agent_id, MessageType.NODE_DISCOVERED, self._on_node_discovered)
        message_bus.subscribe(self._economic_traits.agent_id, MessageType.VULN_FOUND, self._on_vuln_found)

    # ===== Economy Event Handlers =====

    def _on_swarm_message(self, msg) -> None:
        """Handle swarm coordination messages."""
        pass

    def _on_any_economy_message(self, msg) -> None:
        """Catch-all for economy-related messages."""
        pass

    def _on_task_assigned(self, msg) -> None:
        """Handle task assignment from swarm coordinator."""
        pass

    def _on_task_completed(self, msg) -> None:
        """Handle task completion notification."""
        pass

    def _on_node_discovered(self, msg) -> None:
        """Handle node discovery from other agents."""
        pass

    def _on_vuln_found(self, msg) -> None:
        """Handle vulnerability discovery."""
        pass

    # ===== Economy Actions =====

    def register_capability(
        self,
        name: str,
        category: str,
        description: str,
        base_price: float = 5.0,
        min_price: float = 1.0,
        max_price: float = 100.0,
        tags: tuple = (),
        sla_seconds: int = 300,
    ) -> str:
        """Register a new capability for this agent."""
        from cores.economy.registry import CapabilityCategory

        cat_map = {
            "recon": CapabilityCategory.RECON,
            "fuzzing": CapabilityCategory.FUZZING,
            "exploit": CapabilityCategory.EXPLOIT_GENERATION,
            "exploit_generation": CapabilityCategory.EXPLOIT_GENERATION,
            "bypass": CapabilityCategory.BYPASS,
            "validation": CapabilityCategory.VALIDATION,
            "evidence": CapabilityCategory.EVIDENCE_COLLECTION,
            "reporting": CapabilityCategory.REPORTING,
            "post_exploit": CapabilityCategory.POST_EXPLOITATION,
        }
        category_enum = cat_map.get(category, CapabilityCategory.SPECIALIST)

        cap_id = f"cap_{self._economic_traits.agent_id}_{name}"
        cap = Capability(
            id=cap_id,
            name=name,
            category=category_enum,
            description=description,
            provider_id=self._economic_traits.agent_id,
            pricing_model="per_use",
            base_price=base_price,
            min_price=min_price,
            max_price=max_price,
            tags=tags,
            sla_seconds=sla_seconds,
        )
        registry.register_capability(cap)
        self._economic_traits.capabilities_registered.append(cap_id)
        return cap_id

    def bid_on_job(
        self,
        job_id: str,
        amount: float,
        estimated_duration: timedelta = None,
        message: str = "",
    ) -> str | None:
        """Place a bid on a marketplace job."""
        if self._economic_traits.current_jobs >= self._economic_traits.max_concurrent_jobs:
            return None

        bid_id = marketplace.place_bid(
            job_id=job_id,
            provider_id=self._economic_traits.agent_id,
            amount=amount,
            estimated_duration=estimated_duration,
            message=message,
        )
        if bid_id:
            self._economic_traits.last_bid_at = time.time()
            self._economic_traits.current_jobs += 1
        return bid_id

    def auto_bid_on_matching_jobs(self, max_bids: int = 5) -> int:
        """Automatically bid on jobs matching this agent's capabilities."""
        if not self._economic_traits.auto_bid_enabled:
            return 0

        bids_placed = 0
        for cap_id in self._economic_traits.capabilities_registered:
            cap = registry.get_capability(cap_id)
            if not cap:
                continue

            matching_jobs = marketplace.list_open_jobs(category=cap.category)
            for job in matching_jobs[:max_bids]:
                if job.status != "open":
                    continue
                matching_caps = registry.find_capabilities(category=job.category, tags=job.required_tags)
                if any(c.id == cap_id for c in matching_caps):
                    # Calculate bid with margin
                    bid_amount = min(job.budget * (1 - self._economic_traits.min_bid_margin), cap.max_price)
                    if bid_amount >= cap.min_price:
                        self.bid_on_job(job.id, bid_amount)
                        bids_placed += 1
                        if bids_placed >= max_bids:
                            return bids_placed
        return bids_placed

    def submit_delivery(self, job_id: str, content: dict, evidence: dict = None) -> str | None:
        """Submit work delivery for a job."""
        delivery_id = marketplace.submit_delivery(
            job_id=job_id,
            provider_id=self._economic_traits.agent_id,
            content=content,
            evidence=evidence,
        )
        if delivery_id:
            self._pending_deliveries[delivery_id] = {
                "job_id": job_id,
                "submitted_at": time.time(),
            }
        return delivery_id

    def join_swarm(
        self,
        swarm_id: str,
        role: str = "specialist",
    ) -> bool:
        """Join an existing swarm."""
        swarm = coordinator._swarms.get(swarm_id)
        if not swarm:
            return False

        # Check if already in swarm
        if self._economic_traits.current_swarm:
            return False

        # Find or create agent in swarm
        agent_id = f"{swarm_id}_{self._economic_role}_{self._economic_traits.agent_id[-6:]}"
        for aid, agent in swarm.agents.items():
            if self._economic_traits.agent_id in aid:
                self._economic_traits.current_swarm = swarm_id
                self._economic_traits.swarm_role = role
                return True
        return False

    def leave_swarm(self) -> bool:
        """Leave current swarm."""
        if not self._economic_traits.current_swarm:
            return False

        swarm = coordinator._swarms.get(self._economic_traits.current_swarm)
        if swarm:
            # Remove agent from swarm
            to_remove = [aid for aid in swarm.agents if self._economic_traits.agent_id in aid]
            for aid in to_remove:
                del swarm.agents[aid]

        self._economic_traits.current_swarm = None
        self._economic_traits.swarm_role = None
        return True

    def publish_to_swarm(
        self,
        msg_type: str,
        payload: dict,
        priority: str = "normal",
    ) -> bool:
        """Publish a message to the swarm message bus."""
        from cores.swarm.communication import MessageType

        msg_type_member = getattr(MessageType, msg_type.upper(), None)
        priority_member = getattr(Priority, priority.upper(), None)
        msg = AgentMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            type=msg_type_member if msg_type_member is not None else MessageType.BROADCAST,
            sender=self._economic_traits.agent_id,
            recipient=None,
            payload=payload,
            priority=priority_member if priority_member is not None else Priority.NORMAL,
        )
        return message_bus.publish(msg)

    def share_intel(
        self,
        node_type: str,
        value: str,
        label: str = None,
        exploitability: float = 0.0,
        risk_score: float = 0.0,
        metadata: dict = None,
    ) -> str | None:
        """Share discovered intelligence to the attack surface graph."""
        from cores.swarm import graph
        from cores.swarm.graph import NodeType

        node_type_enum = getattr(NodeType, node_type.upper(), NodeType.NOTE)
        node_id = graph.add_node(
            node_type=node_type_enum,
            value=value,
            label=label or value,
            discovered_by=self._economic_traits.agent_id,
            exploitability=exploitability,
            risk_score=risk_score,
            metadata=metadata or {},
        )

        # Notify swarm
        self.publish_to_swarm(
            msg_type="node_discovered",
            payload={
                "node_id": node_id,
                "node_type": node_type,
                "value": value,
                "exploitability": exploitability,
                "risk_score": risk_score,
            },
        )
        return node_id

    def report_vulnerability(
        self,
        target_node: str,
        vuln_type: str,
        exploitability: float,
        risk_score: float,
        evidence: dict = None,
    ) -> str | None:
        """Report a vulnerability finding."""
        vuln_id = self.share_intel(
            node_type="vulnerability",
            value=vuln_type,
            label=vuln_type,
            exploitability=exploitability,
            risk_score=risk_score,
            metadata={"evidence": evidence or {}},
        )

        # Link to target
        from cores.swarm import graph
        from cores.swarm.graph import EdgeType

        if vuln_id and target_node:
            graph.add_edge(target_node, vuln_id, EdgeType.VULNERABLE_TO, discovered_by=self._economic_traits.agent_id)

        # Notify swarm
        self.publish_to_swarm(
            msg_type="vuln_found",
            payload={
                "vuln_id": vuln_id,
                "target": target_node,
                "type": vuln_type,
                "exploitability": exploitability,
                "risk_score": risk_score,
                "evidence": evidence or {},
            },
            priority="high",
        )
        return vuln_id

    def learn_from_engagement(
        self,
        engagement_data: dict,
        success: bool,
        reward: float = 0.0,
    ) -> None:
        """Record engagement outcome for continuous learning."""
        _, record_engagement_outcome = _get_learning()

        record_engagement_outcome(
            agent_id=self._economic_traits.agent_id,
            engagement_data=engagement_data,
            success=success,
            reward=reward,
        )

        # Update local stats
        if success:
            self.tasks_completed += 1
            self._economic_traits.jobs_completed += 1
            self._economic_traits.total_earnings += reward
        else:
            self.tasks_failed += 1
            self._economic_traits.jobs_failed += 1

        # Update economy reputation
        from cores.economy import ReputationEvent, ReputationEventType

        event_type = ReputationEventType.JOB_COMPLETED if success else ReputationEventType.JOB_FAILED
        reputation_engine.record_event(
            ReputationEvent(
                agent_id=self._economic_traits.agent_id,
                event_type=event_type,
                delta=1.0 if success else -1.0,
                metadata={"engagement": engagement_data},
            )
        )

    def get_economic_health(self) -> dict:
        """Return economic health snapshot."""
        from cores.economy import reputation_engine

        traits = self._economic_traits
        profile = registry.get_agent(traits.agent_id)
        rep_snapshot = reputation_engine.get_snapshot(traits.agent_id) if profile else None

        return {
            "agent_id": traits.agent_id,
            "stake": traits.stake,
            "capabilities": len(traits.capabilities_registered),
            "current_swarm": traits.current_swarm,
            "swarm_role": traits.swarm_role,
            "current_jobs": traits.current_jobs,
            "max_concurrent_jobs": traits.max_concurrent_jobs,
            "jobs_completed": traits.jobs_completed,
            "jobs_failed": traits.jobs_failed,
            "total_earnings": traits.total_earnings,
            "reputation_score": profile.reputation_score if profile else 0,
            "reputation_tier": rep_snapshot.tier if rep_snapshot else "unranked",
            "reputation_percentile": rep_snapshot.percentile if rep_snapshot else 0,
        }

    # Override stop to clean up economy registrations
    def stop(self) -> None:
        # Leave swarm if in one
        if self._economic_traits.current_swarm:
            self.leave_swarm()

        # Update agent status in registry
        profile = registry.get_agent(self._economic_traits.agent_id)
        if profile:
            profile.status = EconAgentStatus.OFFLINE

        # Call parent stop
        if hasattr(super(), "stop"):
            super().stop()
