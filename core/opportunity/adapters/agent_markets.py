"""Agent-native market adapters — Taskmarket (Daydreams) and Agent Hansa.

Read-only discovery only: these adapters fetch public task listings.
Claiming tasks, registering an agent identity, submitting work, and any
wallet/payment action remain blocked behind explicit human authorization
(see docs/FINAL_HUMAN_ACTIONS.md).
"""

from __future__ import annotations

from typing import Any

import httpx

from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

_TASKMARKET_URL = "https://api.taskmarket.dev/api/tasks"
_AGENTHANSA_URL = "https://www.agenthansa.com/api/community/tasks"
_AGENTICS_URL = "https://agentics.page/api/jobs"

# Currencies treated as ~USD-equivalent for reward display. Anything else
# (Credits, OW, EUR, unknown) keeps reward=0.0 and the raw currency in
# metadata — never invent a conversion.
_USD_STABLES = {"USD", "USDC", "OUSD", "USDG"}

# Taskmarket rewards are integer strings denominated in the chain's base
# units (USDC, 6 decimals on EVM chains). We convert to USD-equivalent
# float and keep the raw value in metadata for auditability.
_USDC_BASE_UNITS = 1_000_000

# Agent Hansa statuses that represent claimable/open work.
_HANSA_OPEN_STATUSES = {"open", "active", "published", "in_progress"}


class TaskmarketAdapter(OpportunityAdapter):
    """Daydreams TaskMarket adapter — public open task/bounty listing.

    Endpoint: GET https://api.taskmarket.dev/api/tasks (no auth required).
    Rewards are escrowed USDC on-chain; claiming requires agent
    registration (ERC-8004 identity) — NOT performed by this adapter.
    """

    platform: str = "taskmarket"
    cycle: str = "forge"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch open tasks from the public Taskmarket API."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(_TASKMARKET_URL, timeout=15)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data if isinstance(data, list) else data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks:
                    if task.get("status") != "open":
                        continue
                    raw_reward = task.get("reward")
                    try:
                        reward_usd = float(raw_reward) / _USDC_BASE_UNITS if raw_reward else 0.0
                    except (TypeError, ValueError):
                        reward_usd = 0.0

                    raw_opps.append(
                        RawOpportunity(
                            id=f"taskmarket_{task.get('referenceCode') or task.get('id')}",
                            name=f"[{task.get('referenceCode', 'taskmarket')}] {(task.get('description') or 'Task').splitlines()[0][:80]}",
                            description=task.get("description") or "",
                            platform="taskmarket",
                            url=f"https://taskmarket.dev/tasks/{task.get('id')}",
                            reward=reward_usd,
                            effort_hours=2.0,
                            tags=list(task.get("tags") or []) + ["agent-market", "usdc-escrow"],
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="taskmarket",
                            metadata={
                                "original": task,
                                "reward_raw": raw_reward,
                                "reward_unit": "usdc_base_units_assumed",
                                "chain_id": task.get("chainId"),
                                "mode": task.get("mode"),
                                "expiry_time": task.get("expiryTime"),
                                "submission_count": task.get("submissionCount"),
                                "requires_registration": True,
                                "registration_blocked_on_user": True,
                            },
                            created_at=task.get("createdAt") or "",
                        )
                    )

                return raw_opps[:25]
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("TaskmarketAdapter fetch failed: %s", e)
            return []


class AgentHansaAdapter(OpportunityAdapter):
    """Agent Hansa adapter — community task/quest listing (USDC rewards).

    Endpoint: GET https://www.agenthansa.com/api/community/tasks (public).
    Most historical tasks are expired/completed; only open-status tasks
    are surfaced. Registration and claiming require an agent identity —
    NOT performed by this adapter.
    """

    platform: str = "agent_hansa"
    cycle: str = "forge"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch open community tasks from Agent Hansa."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(_AGENTHANSA_URL, timeout=15)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data if isinstance(data, list) else data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks:
                    status = (task.get("status") or "").lower()
                    if status not in _HANSA_OPEN_STATUSES:
                        continue

                    raw_opps.append(
                        RawOpportunity(
                            id=f"agenthansa_{task.get('id')}",
                            name=task.get("title") or "Agent Hansa Task",
                            description=task.get("description") or task.get("goal") or "",
                            platform="agent_hansa",
                            url="https://www.agenthansa.com/community/tasks",
                            reward=float(task.get("reward_amount") or 0.0),
                            effort_hours=2.0,
                            tags=list(task.get("tags") or []) + ["agent-market", task.get("category") or "quest"],
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="agent_hansa",
                            metadata={
                                "original": task,
                                "currency": task.get("currency", "USD"),
                                "status": status,
                                "split_method": task.get("split_method"),
                                "participant_count": task.get("participant_count"),
                                "requires_registration": True,
                                "registration_blocked_on_user": True,
                            },
                            created_at="",
                        )
                    )

                return raw_opps[:25]
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("AgentHansaAdapter fetch failed: %s", e)
            return []


class AgenticsAdapter(OpportunityAdapter):
    """Agentics aggregator adapter — unified feed of agent-work markets.

    Endpoint: GET https://agentics.page/api/jobs (public JSON, no auth).
    Aggregates listings from ~15 agent markets (taskmarket, basedagents,
    immunefi, cantina, opire, rentahuman, etc). This is a DISCOVERY feed:
    the paying source is ``job['source']``/``sourceName`` — OWNEX must
    dedupe against direct adapters and verify payout at the origin market.
    """

    platform: str = "agentics"
    cycle: str = "forge"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch aggregated agent-market jobs from the Agentics feed."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(_AGENTICS_URL, params={"limit": 250}, timeout=20)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                jobs = data.get("jobs", []) if isinstance(data, dict) else []

                raw_opps: list[RawOpportunity] = []
                for job in jobs:
                    currency = (job.get("currency") or "").upper()
                    try:
                        amount = float(job.get("amount") or 0)
                    except (TypeError, ValueError):
                        amount = 0.0
                    reward = amount if currency in _USD_STABLES else 0.0

                    origin = job.get("sourceName") or job.get("source") or "agentics"
                    raw_opps.append(
                        RawOpportunity(
                            id=f"agentics_{job.get('id')}",
                            name=(job.get("title") or "Agent job")[:120],
                            description=job.get("description") or "",
                            platform="agentics",
                            url=job.get("url"),
                            reward=reward,
                            effort_hours=2.0,
                            tags=["agent-market", job.get("source") or "unknown", job.get("payModel") or "unknown"],
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name=str(origin),
                            metadata={
                                "original": job,
                                "origin_source": job.get("source"),
                                "origin_name": job.get("sourceName"),
                                "currency": currency or None,
                                "amount_raw": job.get("amount"),
                                "amount_note": job.get("amountNote"),
                                "pay_model": job.get("payModel"),
                                "pay_rail": job.get("payRail"),
                                "pay_note": job.get("payNote"),
                                "kind": job.get("kind"),
                                "deadline": job.get("deadline"),
                                "posted_at": job.get("postedAt"),
                                "aggregator": "agentics",
                                "requires_registration": True,
                                "registration_blocked_on_user": True,
                            },
                            created_at=job.get("postedAt") or "",
                        )
                    )

                return raw_opps[:100]
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("AgenticsAdapter fetch failed: %s", e)
            return []
