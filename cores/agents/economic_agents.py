"""Example economic agent — demonstrates Agent Economy + Swarm integration."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import timedelta
from typing import Any, Optional

from cores.agents.base import BaseAgent
from cores.agents.types import AgentEvent, AgentId, AgentStatus, EventType
from cores.agents.economic_mixin import EconomicAgentMixin
from cores.economy.registry import CapabilityCategory
from cores.economy import marketplace, registry
from cores.swarm import coordinator, graph, message_bus
from cores.swarm.coordinator import AgentRole
from cores.swarm.graph import NodeType, EdgeType
from cores.swarm.communication import MessageType, Priority, AgentMessage


class ReconAgent(BaseAgent, EconomicAgentMixin):
    """Reconnaissance agent with economic and swarm capabilities."""

    def __init__(self, *args, stake: float = 100.0, **kwargs):
        # Must set agent_id BEFORE calling BaseAgent.__init__
        self.agent_id = AgentId.RECON
        BaseAgent.__init__(self)
        EconomicAgentMixin.__init__(
            self,
            stake=stake,
            role="recon",
            auto_register_capabilities=True,
            auto_bid=True,
            min_bid_margin=0.15,
            max_concurrent_jobs=2,
        )

        self._economic_traits.agent_id = self.agent_id.value

        # Register recon-specific capabilities
        self.register_capability(
            name="subdomain_enum",
            category="recon",
            description="Fast subdomain enumeration using multiple sources",
            base_price=5.0,
            min_price=1.0,
            max_price=50.0,
            tags=("subdomain", "dns", "recon"),
            sla_seconds=120,
        )

        self.register_capability(
            name="port_scan",
            category="recon",
            description="Fast port scanning with service detection",
            base_price=3.0,
            min_price=1.0,
            max_price=30.0,
            tags=("port", "service", "nmap"),
            sla_seconds=180,
        )

        self.register_capability(
            name="tech_fingerprint",
            category="recon",
            description="Technology fingerprinting and version detection",
            base_price=4.0,
            min_price=1.0,
            max_price=40.0,
            tags=("fingerprint", "tech", "wappalyzer"),
            sla_seconds=150,
        )

    def _get_agent_id(self) -> AgentId:
        return self.agent_id

    def _get_subscriptions(self) -> list[str]:
        return [
            "job_created",
            "task_assigned",
            "recon_request",
        ]

    def handle_event(self, event) -> None:
        """Handle incoming events."""
        event_type = event.event_type if hasattr(event, "event_type") else str(event)

        if event_type == "job_created":
            self._on_job_created(event)
        elif event_type == "task_assigned":
            self._on_task_assigned(event)
        elif event_type == "recon_request":
            self._on_recon_request(event)

    def _on_job_created(self, event) -> None:
        """Auto-bid on matching jobs."""
        payload = getattr(event, "payload", {})
        job_id = payload.get("job_id")
        if job_id and self._economic_traits.auto_bid_enabled:
            job = marketplace.get_job(job_id)
            if job:
                for cap_id in self._economic_traits.capabilities_registered:
                    cap = registry.get_capability(cap_id)
                    if cap and cap.category.value in job.required_tags:
                        bid_amount = min(job.budget * 0.85, cap.max_price)
                        if bid_amount >= cap.min_price:
                            self.bid_on_job(job_id, bid_amount)
                            break

    def _on_task_assigned(self, event) -> None:
        """Handle task assignment from swarm coordinator."""
        payload = getattr(event, "payload", {})
        task_id = payload.get("task_id")
        action = payload.get("action")

        if action == "subdomain_enum":
            asyncio.create_task(self._execute_subdomain_enum(task_id, payload))
        elif action == "port_scan":
            asyncio.create_task(self._execute_port_scan(task_id, payload))
        elif action == "tech_fingerprint":
            asyncio.create_task(self._execute_tech_fingerprint(task_id, payload))

    async def _execute_subdomain_enum(self, task_id: str, payload: dict) -> dict:
        """Execute subdomain enumeration."""
        target = payload.get("target", "")
        start = time.time()

        await asyncio.sleep(2)

        subdomains = [f"api.{target}", f"admin.{target}", f"dev.{target}", f"staging.{target}"]

        result = {
            "task_id": task_id,
            "action": "subdomain_enum",
            "target": target,
            "subdomains": subdomains,
            "count": len(subdomains),
            "duration_ms": (time.time() - start) * 1000,
        }

        for sub in subdomains:
            self.share_intel(
                node_type="subdomain",
                value=sub,
                label=sub,
                exploitability=0.3,
                metadata={"source": "recon_agent", "method": "subdomain_enum"},
            )

        if any("admin" in s for s in subdomains):
            admin_sub = next(s for s in subdomains if "admin" in s)
            self.report_vulnerability(
                target_node=admin_sub,
                vuln_type="admin_panel_exposure",
                exploitability=0.6,
                risk_score=5.0,
                evidence={"subdomains": subdomains},
            )

        self.learn_from_engagement(
            engagement_data={"input": {"target": target}, "output": result},
            success=True,
            reward=5.0,
        )

        return result

    async def _execute_port_scan(self, task_id: str, payload: dict) -> dict:
        """Execute port scan."""
        target = payload.get("target", "")
        start = time.time()

        await asyncio.sleep(3)

        open_ports = [
            {"port": 80, "service": "http", "version": "nginx/1.20"},
            {"port": 443, "service": "https", "version": "nginx/1.20"},
            {"port": 22, "service": "ssh", "version": "OpenSSH 8.2"},
            {"port": 3306, "service": "mysql", "version": "MySQL 8.0"},
        ]

        result = {
            "task_id": task_id,
            "action": "port_scan",
            "target": target,
            "open_ports": open_ports,
            "duration_ms": (time.time() - start) * 1000,
        }

        for port_info in open_ports:
            self.share_intel(
                node_type="port",
                value=str(port_info["port"]),
                label=f"{port_info['port']}/{port_info['service']}",
                exploitability=0.4,
                metadata={"service": port_info["service"], "version": port_info["version"]},
            )

        self.learn_from_engagement(
            engagement_data={"input": {"target": target}, "output": result},
            success=True,
            reward=3.0,
        )

        return result

    async def _execute_tech_fingerprint(self, task_id: str, payload: dict) -> dict:
        """Execute technology fingerprinting."""
        target = payload.get("target", "")
        start = time.time()

        await asyncio.sleep(1.5)

        tech = [
            {"name": "nginx", "version": "1.20.1", "category": "web_server", "confidence": 0.95},
            {"name": "PHP", "version": "8.1", "category": "language", "confidence": 0.85},
            {"name": "Laravel", "version": "9.x", "category": "framework", "confidence": 0.75},
        ]

        result = {
            "task_id": task_id,
            "action": "tech_fingerprint",
            "target": target,
            "technologies": tech,
            "duration_ms": (time.time() - start) * 1000,
        }

        for t in tech:
            self.share_intel(
                node_type="technology",
                value=f"{t['name']} {t['version']}",
                label=f"{t['name']} {t['version']}",
                exploitability=0.2,
                metadata=t,
            )

        self.learn_from_engagement(
            engagement_data={"input": {"target": target}, "output": result},
            success=True,
            reward=4.0,
        )

        return result


class FuzzerAgent(BaseAgent, EconomicAgentMixin):
    """Fuzzing agent with economic capabilities."""

    def __init__(self, *args, stake: float = 150.0, **kwargs):
        self.agent_id = AgentId.FUZZER
        BaseAgent.__init__(self)
        EconomicAgentMixin.__init__(
            self,
            stake=stake,
            role="fuzzer",
            auto_bid=True,
            min_bid_margin=0.2,
            max_concurrent_jobs=1,
        )

        self._economic_traits.agent_id = self.agent_id.value

        self.register_capability(
            name="vuln_scan",
            category="fuzzing",
            description="Automated vulnerability scanning with custom payloads",
            base_price=20.0,
            min_price=5.0,
            max_price=200.0,
            tags=("vuln", "scan", "fuzzing", "payload"),
            sla_seconds=600,
        )

        self.register_capability(
            name="param_fuzz",
            category="fuzzing",
            description="Parameter fuzzing for injection vulnerabilities",
            base_price=15.0,
            min_price=5.0,
            max_price=150.0,
            tags=("param", "injection", "fuzzing"),
            sla_seconds=300,
        )

    def _get_subscriptions(self) -> list[str]:
        return ["fuzz_request", "task_assigned"]

    def handle_event(self, event) -> None:
        pass

    def _get_agent_id(self) -> AgentId:
        return self.agent_id


class ValidatorAgent(BaseAgent, EconomicAgentMixin):
    """Validation agent — verifies PoCs and collects evidence."""

    def __init__(self, *args, stake: float = 200.0, **kwargs):
        self.agent_id = AgentId.VALIDATOR_ECON
        BaseAgent.__init__(self)
        EconomicAgentMixin.__init__(
            self,
            stake=stake,
            role="validator",
            auto_bid=False,
            max_concurrent_jobs=2,
        )

        self._economic_traits.agent_id = self.agent_id.value

        self.register_capability(
            name="poc_validate",
            category="validation",
            description="Proof-of-concept validation and verification",
            base_price=25.0,
            min_price=10.0,
            max_price=300.0,
            tags=("poc", "verify", "evidence"),
            sla_seconds=300,
        )

        self.register_capability(
            name="evidence_collect",
            category="validation",
            description="Evidence collection and documentation",
            base_price=10.0,
            min_price=5.0,
            max_price=50.0,
            tags=("evidence", "documentation", "report"),
            sla_seconds=120,
        )

    def _get_subscriptions(self) -> list[str]:
        return ["validate_request", "task_assigned"]

    def handle_event(self, event) -> None:
        pass

    def _get_agent_id(self) -> AgentId:
        return self.agent_id
