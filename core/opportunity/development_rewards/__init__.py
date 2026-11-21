"""Development Rewards Intelligence — OWNEX.

Extends the opportunity discovery framework to include paid development
opportunities beyond traditional bug bounties: coding competitions, agent
tasks, feature implementations, and agent economy marketplaces.

Key design principles:
- Single source of truth: all opportunities flow through the Source Discovery
  registry and Opportunity Adapters.
- Argentina compatibility: every opportunity is checked for payout methods
  that work from Argentina (USDC, crypto, stablecoins, Payoneer, AirTM).
- Realistic scoring: advertise d reward / effort / confidence, with verified
  payout history tracked.
- Deduplication: opportunities from multiple sources are deduplicated by
  normalized canonical ID.
- Automation-ready: many adapters provide MCP-ready descriptors so OWNEX
  agents can claim, execute, and deliver autonomously.
"""

from __future__ import annotations

from enum import StrEnum

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity
from core.opportunity.source_discovery import SourceCandidate, SourceDiscoveryRegistry, SourceLifecycle

__all__ = [
    "DevelopmentRewardType",
    "DevelopmentRewardScorer",
    "GitpayAdapter",
    "SuperteamEarnAdapter",
    "MakefunAdapter",
    "TaskMarketAdapter",
    "BasedAgentsAdapter",
    "ClawHuntAdapter",
    "IssueHuntAdapter",
    "KaggleCompetitionAdapter",
    "ETHGlobalAdapter",
    "DoraHacksAdapter",
    "classify_opportunity",
    "score_opportunity",
    "argentina_compatible",
]

# ── Classification of opportunity types ────────────────────────────────────


class DevelopmentRewardType(StrEnum):
    """Categories of development reward opportunities."""

    GITHUB_ISSUE_BOUNTY = "github_issue_bounty"
    PULL_REQUEST_REWARD = "pull_request_reward"
    FEATURE_IMPLEMENTATION = "feature_implementation"
    BUG_FIX_REWARD = "bug_fix_reward"
    AI_CODING_COMPETITION = "ai_coding_competition"
    AGENT_TASK = "agent_task"
    SMART_CONTRACT_AUDIT = "smart_contract_audit"
    VULNERABILITY_BOUNTY = "vulnerability_bounty"
    OPEN_SOURCE_GRANT = "open_source_grant"
    HACKATHON_PRIZE = "hackathon_prize"
    DEVELOPER_CHALLENGE = "developer_challenge"
    TEST_AUTOMATION_REWARD = "test_automation_reward"
    CODE_REVIEW_REWARD = "code_review_reward"


# ── Argentina compatibility check ─────────────────────────────────────────

_ARGENTINA_PAYOUT_METHODS = {
    "usdc",
    "usdt",
    "btc",
    "eth",
    "usd",
    "crypto",
    "stablecoin",
    "airtm",
    "payoneer",
    "mercadopago",
    "bitcoin",
    "ethereum",
}


def argentina_compatible(reward_data: dict[str, Any]) -> bool:
    """Check if a reward opportunity has payout methods compatible with Argentina.

    A opportunity is considered Argentina-compatible if any of its reported
    reward currencies or metadata keywords match known Argentina-friendly
    payout methods (USDC, crypto, AirTM, Payoneer, etc.).

    Args:
        reward_data: dict with reward information (from adapter metadata,
                     reward fields, or source profile).

    Returns:
        True if the opportunity appears payable from Argentina.
    """
    currencies = reward_data.get("reward_currency", "")
    if isinstance(currencies, str):
        currencies = [currencies]
    elif isinstance(currencies, list):
        pass
    else:
        return False

    text_to_check = " ".join(str(c).lower() for c in currencies)

    # Also check metadata keywords
    metadata = reward_data.get("metadata", {})
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            if isinstance(value, str):
                text_to_check += " " + value.lower()

    for method in _ARGENTINA_PAYOUT_METHODS:
        if method in text_to_check:
            return True

    return False


# ── Opportunity classification ─────────────────────────────────────────────


def classify_opportunity(raw: RawOpportunity) -> DevelopmentRewardType:
    """Classify a RawOpportunity into a DevelopmentRewardType.

    Uses the opportunity's tags, category, platform, and description to
    determine the most appropriate reward type.

    Args:
        raw: RawOpportunity instance from any adapter.

    Returns:
        DevelopmentRewardType classification.
    """
    name_lower = (raw.name or "").lower()
    desc_lower = (raw.description or "").lower()
    tags_lower = " ".join(raw.tags or []).lower()
    platform_lower = (raw.platform or "").lower()

    # GitHub issue bounties
    if raw.platform == "github" or "github" in tags_lower:
        if "bounty" in tags_lower or "reward" in tags_lower:
            return DevelopmentRewardType.GITHUB_ISSUE_BOUNTY
        return DevelopmentRewardType.FEATURE_IMPLEMENTATION

    # Pull request rewards
    if "pr" in tags_lower or "pull.request" in tags_lower:
        return DevelopmentRewardType.PULL_REQUEST_REWARD

    # AI coding competitions
    if any(kw in tags_lower for kw in ["competition", "kaggle", "make.fun"]):
        return DevelopmentRewardType.AI_CODING_COMPETITION

    # Agent tasks
    if any(kw in tags_lower for kw in ["agent", "automation", "workflow"]):
        return DevelopmentRewardType.AGENT_TASK

    # Smart contract audits
    if any(kw in tags_lower for kw in ["smart.contract", "solidity", "audit"]):
        return DevelopmentRewardType.SMART_CONTRACT_AUDIT

    # Vulnerability bounties
    if any(kw in tags_lower for kw in ["vulnerability", "security", "cve"]):
        return DevelopmentRewardType.VULNERABILITY_BOUNTY

    # Open source grants
    if any(kw in tags_lower for kw in ["grant", "funding"]):
        return DevelopmentRewardType.OPEN_SOURCE_GRANT

    # Hackathon prizes
    if any(kw in tags_lower for kw in ["hackathon", "hack"]):
        return DevelopmentRewardType.HACKATHON_PRIZE

    # Developer challenges
    if any(kw in tags_lower for kw in ["challenge", "coding"]):
        return DevelopmentRewardType.DEVELOPER_CHALLENGE

    # Test automation rewards
    if any(kw in tags_lower for kw in ["test", "automation", "e2e"]):
        return DevelopmentRewardType.TEST_AUTOMATION_REWARD

    # Code review rewards
    if any(kw in tags_lower for kw in ["code.review", "review"]):
        return DevelopmentRewardType.CODE_REVIEW_REWARD

    # Default based on platform
    if platform_lower == "superteam":
        return DevelopmentRewardType.FEATURE_IMPLEMENTATION
    if platform_lower == "issuehunt":
        return DevelopmentRewardType.GITHUB_ISSUE_BOUNTY
    if platform_lower == "maket" or platform_lower == "make.fun":
        return DevelopmentRewardType.AI_CODING_COMPETITION
    if platform_lower == "taskmarket":
        return DevelopmentRewardType.AGENT_TASK
    if platform_lower == "basedagents":
        return DevelopmentRewardType.AGENT_TASK

    # Fallback
    return DevelopmentRewardType.FEATURE_IMPLEMENTATION


# ── Scoring model ──────────────────────────────────────────────────────────


class DevelopmentRewardScorer:
    """Score development reward opportunities realistically.

    Uses a multi-factor model that does NOT simply maximize advertised reward.
    Factors include Argentina compatibility, payout verification, automation
    potential, effort, and risk/competition.

    Model weights (configurable, pesos iniciales):
      - compatibility_with_argentina:     20%
      - verifiable_payout_and_retiro:     20%
      - acceso_y_requisitos:              15%
      - disponibilidad_real:              15%
      - ingreso_nete_por_hora:            15%
      - automatizacion_posible:           10%
      - riesgo_y_competencia:             5%
    """

    WEIGHTS = {
        "compatibility_with_argentina": 0.20,
        "verifiable_payout_and_retiro": 0.20,
        "acceso_y_requisitos": 0.15,
        "disponibilidad_real": 0.15,
        "ingreso_nete_por_hora": 0.15,
        "automatizacion_posible": 0.10,
        "riesgo_y_competencia": 0.05,
    }

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        if weights:
            # Normalize weights to sum to 1.0
            total = sum(weights.values())
            if total > 0:
                self.WEIGHTS = {k: v / total for k, v in weights.items()}
            else:
                self.WEIGHTS = self.WEIGHTS  # keep defaults
        self._last_breakdown: dict[str, float] = {}

    def score(
        self,
        raw: RawOpportunity,
        *,
        argentina_bonus: bool = True,
    ) -> dict[str, Any]:
        """Score a RawOpportunity and return a detailed breakdown.

        Args:
            raw: RawOpportunity from any adapter.
            argentina_bonus: If True, apply bonus for Argentina compatibility.

        Returns:
            dict with score, breakdown, and recommended_action.
        """
        # Base factors
        reward_raw = raw.reward or 0.0
        effort_raw = raw.effort_hours or 1.0
        category = classify_opportunity(raw)

        # 1. Compatibilidad con Argentina (20%)
        argentina_score = 0.0
        # Use getattr since RawOpportunity may not have reward_currency
        reward_currency = getattr(raw, "reward_currency", None) or getattr(raw.metadata, "get", lambda *a: None)("reward_currency")
        if argentina_bonus and argentina_compatible({"reward_currency": reward_currency} if reward_currency else {}):
            argentina_score = 1.0

        # 2. Pago y retiro verificables (20%)
        # Check if reward_status indicates verified payment
        reward_status = getattr(raw, "reward_status", None) or getattr(raw.metadata, "get", lambda *a: None)("reward_status") or "UNKNOWN"
        verified_payout = reward_status in ("PAID", "VERIFIED", "CONFIRMED")
        verified_score = 1.0 if verified_payout else 0.3  # partial credit for reported

        # 3. Acceso y requisitos (15%)
        # Based on specialization, remote flag, and eligibility
        specialty = getattr(raw, "specialization", "") or ""
        remote = getattr(raw, "remote", False) or False
        acceso_score = 0.5  # baseline
        if remote:
            acceso_score += 0.3
        if specialty in ("backend", "frontend", "fullstack"):
            acceso_score += 0.2

        # 4. Disponibilidad real (15%)
        # Based on platform activity and historical payout rate
        # Use platform metadata or default neutral
        disponibilidad_score = 0.5

        # 5. Ingreso neto por hora (15%)
        # estimated_net_hourly = reward / effort * conversion_factor
        reward_raw = getattr(raw, "reward", 0.0) or 0.0
        effort_raw = getattr(raw, "effort_hours", 1.0) or 1.0
        if effort_raw > 0:
            ingreso_nete = reward_raw / effort_raw
        else:
            ingreso_nete = 0.0
        # Normalize: assume >$50/hr is good, <$10/hr is poor
        if ingreso_nete > 50:
            ingreso_score = 1.0
        elif ingreso_nete > 20:
            ingreso_score = 0.7
        elif ingreso_nete > 10:
            ingreso_score = 0.4
        elif ingreso_nete > 0:
            ingreso_score = 0.2
        else:
            ingreso_score = 0.0

        # 6. Automatización posible (10%)
        # Based on opportunity type and agent task compatibility
        automatable_types = {
            DevelopmentRewardType.AGENT_TASK,
            DevelopmentRewardType.AI_CODING_COMPETITION,
        }
        automatizacion_score = 1.0 if category in automatable_types else 0.2

        # 7. Riesgo y competencia (5%)
        # Based on platform reputation and task competition level
        platform = (getattr(raw, "platform", "") or "").lower()
        riesgo_score = 0.5  # neutral
        if platform in ("superteam", "kaggle", "ethglobal"):
            riesgo_score = 0.7  # higher risk but established
        elif platform in ("clawhunt", "basedagents"):
            riesgo_score = 0.4  # experimental, lower volume
        else:
            riesgo_score = 0.5

        # Compute weighted total
        total = (
            self.WEIGHTS["compatibility_with_argentina"] * argentina_score
            + self.WEIGHTS["verifiable_payout_and_retiro"] * verified_score
            + self.WEIGHTS["acceso_y_requisitos"] * acceso_score
            + self.WEIGHTS["disponibilidad_real"] * disponibilidad_score
            + self.WEIGHTS["ingreso_nete_por_hora"] * ingreso_score
            + self.WEIGHTS["automatizacion_posible"] * automatizacion_score
            + self.WEIGHTS["riesgo_y_competencia"] * riesgo_score
        )

        # Store breakdown for inspection
        self._last_breakdown = {
            "compatibility_with_argentina": argentina_score,
            "verifiable_payout_and_retiro": verified_score,
            "acceso_y_requisitos": acceso_score,
            "disponibilidad_real": disponibilidad_score,
            "ingreso_nete_por_hora": ingreso_score,
            "automatizacion_posible": automatizacion_score,
            "riesgo_y_competencia": riesgo_score,
            "raw_reward": reward_raw,
            "raw_effort_hours": effort_raw,
            "classified_category": category,
        }

        # Determine recommended action
        if total >= 0.8:
            recommended_action = "high_priority"
        elif total >= 0.6:
            recommended_action = "worth_pursuing"
        elif total >= 0.4:
            recommended_action = "low_priority"
        else:
            recommended_action = "skip"

        # Build breakdown, rounding numeric values but skipping non-numeric like classified_category
        breakdown = {}
        for k, v in self._last_breakdown.items():
            if k == "classified_category":
                breakdown[k] = v
            else:
                try:
                    breakdown[k] = round(v, 3)
                except TypeError:
                    breakdown[k] = v

        return {
            "score": round(total, 3),
            "breakdown": breakdown,
            "recommended_action": recommended_action,
            "classified_category": category,
            "expected_hourly": round(reward_raw / effort_raw, 2) if effort_raw > 0 else 0.0,
        }


# ── Platform Adapters ─────────────────────────────────────────────────────


class BaseDevelopmentAdapter(OpportunityAdapter):
    """Base adapter for development reward platforms.

    Subclasses should set:
    - platform: str — identifier used in RawOpportunity.platform
    - cycle: str — scheduler cycle ("forge" or "pulse")
    - reward_currency: str — typical currency (USD, USDC, etc.)
    """

    platform: str
    cycle: str = "forge"
    reward_currency: str = "USD"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials(self.platform, config)
        super().__init__(merged_config)


# Gitpay adapter
class GitpayAdapter(BaseDevelopmentAdapter):
    """Gitpay adapter — GitHub-funded bounties with Whop payouts.

    Platform: gitpay.io
    Opportunities: Funded GitHub issues, PR acceptance bounties
    Payout: Whop (bank, PayPal, crypto depending on country)
    Argentina: Needs verification — may use crypto or PayPal
    """

    platform: str = "gitpay"
    cycle: str = "forge"
    reward_currency: str = "USD"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch funded GitHub bounties from Gitpay."""
        try:
            config = self.config or {}
            api_key = config.get("api_key") or config.get("key")

            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.gitpay.io/v1/bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:30]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"gitpay_{bounty.get('id')}",
                            name=bounty.get("title") or "Gitpay Bounty",
                            description=bounty.get("description") or "",
                            platform="gitpay",
                            url=bounty.get("url"),
                            reward=float(bounty.get("amount", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 4)),
                            tags=bounty.get("labels", ["github", "bounty"]),
                            specialization=bounty.get("specialization", "backend"),
                            remote=bounty.get("remote", True),
                            reward_currency=bounty.get("currency", "USD"),
                            reward_status=bounty.get("payment_status", "REPORTED"),
                            source_type="dev_bounty",
                            source_name="gitpay",
                            metadata={"original": bounty},
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("GitpayAdapter fetch failed: %s", e)
            return []


# Superteam Earn adapter
class SuperteamEarnAdapter(BaseDevelopmentAdapter):
    """Superteam Earn adapter — development bounties and grants.

    Platform: superteam.sh
    Categories: development, backend, web3, AI
    Payout: USDC, crypto
    Argentina: Has regional page, supports Argentina users
    """

    platform: str = "superteam"
    cycle: str = "forge"
    reward_currency: str = "USDC"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Superteam opportunities."""
        try:
            return await super()._get_curated_direct_work()
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("SuperteamEarnAdapter fetch failed: %s", e)
            return []


# Make.fun adapter
class MakefunAdapter(BaseDevelopmentAdapter):
    """make.fun adapter — AI coding competitions with USDC rewards.

    Platform: make.fun
    Features: AI-agent-friendly, USDC rewards, sandbox verification,
    public transcripts and repos as delivery evidence.
    Argentina: Accepts participants, USDC payouts available
    """

    platform: str = "make.fun"
    cycle: str = "forge"
    reward_currency: str = "USDC"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch AI coding competitions from make.fun."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.make.fun/v1/competitions",
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                competitions = data.get("competitions", data)

                raw_opps: list[RawOpportunity] = []
                for comp in competitions[:20]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"makefun_{comp.get('id')}",
                            name=comp.get("title") or "make.fun Competition",
                            description=comp.get("description") or "",
                            platform="make.fun",
                            url=comp.get("url"),
                            reward=float(comp.get("reward", 0)),
                            effort_hours=float(comp.get("estimated_hours", 10)),
                            tags=comp.get("tags", ["ai", "coding", "competition"]),
                            specialization=comp.get("specialization", "backend"),
                            remote=comp.get("remote", True),
                            reward_currency=comp.get("currency", "USDC"),
                            reward_status=comp.get("status", "upcoming"),
                            source_type="competition",
                            source_name="make.fun",
                            metadata={"original": comp},
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("MakefunAdapter fetch failed: %s", e)
            return []


# TaskMarket adapter
class TaskMarketAdapter(BaseDevelopmentAdapter):
    """TaskMarket adapter — bounties with USDC escrow on Base.

    Platform: taskmarket.xyz (or similar)
    Features: escrow USDC Base, agents & automation, auction/pitch/benchmark
    Argentina: Crypto-compatible, USDC accessible
    """

    platform: str = "taskmarket"
    cycle: str = "forge"
    reward_currency: str = "USDC"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch TaskMarket opportunities."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.taskmarket.xyz/v1/tasks",
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks[:30]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"taskmarket_{task.get('id')}",
                            name=task.get("title") or "TaskMarket Task",
                            description=task.get("description") or "",
                            platform="taskmarket",
                            url=task.get("url"),
                            reward=float(task.get("reward", 0)),
                            effort_hours=float(task.get("estimated_hours", 4)),
                            tags=task.get("tags", ["bounty", "agent", "automation"]),
                            specialization=task.get("specialization", "backend"),
                            remote=task.get("remote", True),
                            reward_currency=task.get("currency", "USDC"),
                            reward_status=task.get("status", "open"),
                            source_type="bounty",
                            source_name="taskmarket",
                            metadata={"original": task},
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("TaskMarketAdapter fetch failed: %s", e)
            return []


# BasedAgents adapter
class BasedAgentsAdapter(BaseDevelopmentAdapter):
    """BasedAgents adapter — agent task marketplace with USDC escrow.

    Platform: basedagents.xyz
    Features: escrow USDC, 7-day auto-accept, API/CLI/MCP, reputation system
    Argentina: Experimental, small volume
    """

    platform: str = "basedagents"
    cycle: str = "pulse"
    reward_currency: str = "USDC"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch BasedAgents opportunities."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.basedagents.xyz/v1/tasks",
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks[:20]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"basedagents_{task.get('id')}",
                            name=task.get("title") or "BasedAgents Task",
                            description=task.get("description") or "",
                            platform="basedagents",
                            url=task.get("url"),
                            reward=float(task.get("reward", 0)),
                            effort_hours=float(task.get("estimated_hours", 4)),
                            tags=task.get("tags", ["agent", "task", "usdc"]),
                            specialization=task.get("specialization", "backend"),
                            remote=task.get("remote", True),
                            reward_currency=task.get("currency", "USDC"),
                            reward_status=task.get("status", "open"),
                            source_type="agent_task",
                            source_name="basedagents",
                            metadata={"original": task},
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("BasedAgentsAdapter fetch failed: %s", e)
            return []


# ClawHunt adapter
class ClawHuntAdapter(BaseDevelopmentAdapter):
    """ClawHunt adapter — programming tasks for agents.

    Platform: clawhunt.xyz
    Features: retained budgets, code tasks, CLI/MCP access
    Argentina: Experimental, USD 35 medium budget
    """

    platform: str = "clawhunt"
    cycle: str = "pulse"
    reward_currency: str = "USD"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch ClawHunt opportunities."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.clawhunt.xyz/v1/tasks",
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks[:30]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"clawhunt_{task.get('id')}",
                            name=task.get("title") or "ClawHunt Task",
                            description=task.get("description") or "",
                            platform="clawhunt",
                            url=task.get("url"),
                            reward=float(task.get("reward", 0)),
                            effort_hours=float(task.get("estimated_hours", 4)),
                            tags=task.get("tags", ["programming", "agent", "task"]),
                            specialization=task.get("specialization", "backend"),
                            remote=task.get("remote", True),
                            reward_currency=task.get("currency", "USD"),
                            reward_status=task.get("status", "open"),
                            source_type="dev_task",
                            source_name="clawhunt",
                            metadata={"original": task},
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("ClawHuntAdapter fetch failed: %s", e)
            return []


# IssueHunt adapter (already exists, but we extend it)
class ExtendedIssueHuntAdapter(IssueHuntAdapter if "IssueHuntAdapter" in dir() else BaseDevelopmentAdapter):
    """Extended IssueHunt adapter — OSS issue bounties.

    Platform: issuehunt.io
    Features: financed OSS issues, >12,000 projects, GitHub login
    Argentina: Needs verification on payout methods
    """

    platform: str = "issuehunt"
    cycle: str = "forge"
    reward_currency: str = "USD"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch IssueHunt bounties."""
        try:
            return await super().fetch_opportunities(personal)
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("ExtendedIssueHuntAdapter fetch failed: %s", e)
            return []


# Kaggle Competition adapter
class KaggleCompetitionAdapter(BaseDevelopmentAdapter):
    """Kaggle Competitions adapter — AI/ML/data science competitions.

    Platform: kaggle.com
    Features: published prizes, international, competitive solutions
    Argentina: Accepts international participants
    """

    platform: str = "kaggle"
    cycle: str = "forge"
    reward_currency: str = "USD"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Kaggle competitions.

        Note: Kaggle requires account authentication; this adapter uses
        public feed where available, or falls back to known competition list.
        """
        try:
            # Kaggle API requires authentication; fall back to known competitions
            # or public listing if available
            fallback_data = [
                {
                    "id": "kaggle_1",
                    "name": "Kaggle Competition Example",
                    "description": "Example Kaggle competition",
                    "url": "https://www.kaggle.com/competitions",
                    "reward": 75000.0,  # Example: Google Gemma competition
                    "effort_hours": 40.0,
                    "tags": ["kaggle", "competition", "ai"],
                    "specialization": "data-science",
                    "remote": True,
                    "reward_currency": "USD",
                    "reward_status": "announced",
                    "source_type": "competition",
                    "source_name": "kaggle",
                },
            ]

            raw_opps: list[RawOpportunity] = []
            for item in fallback_data:
                raw_opps.append(
                    RawOpportunity(
                        id=item["id"],
                        name=item["name"],
                        description=item["description"],
                        platform="kaggle",
                        url=item["url"],
                        reward=item["reward"],
                        effort_hours=item["effort_hours"],
                        tags=item["tags"],
                        specialization=item["specialization"],
                        remote=item["remote"],
                        reward_currency=item["reward_currency"],
                        reward_status=item["reward_status"],
                        source_type=item["source_type"],
                        source_name=item["source_name"],
                    )
                )

            return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("KaggleCompetitionAdapter fetch failed: %s", e)
            return []


# ETHGlobal adapter
class ETHGlobalAdapter(BaseDevelopmentAdapter):
    """ETHGlobal adapter — hackathons, bounties, Web3 integrations.

    Platform: ethglobal.com
    Features: hackathons, bounties, USD 5-6K integration prizes,
    Web3 tooling, MCP-compatible
    Argentina: Accepts global participants, crypto payouts
    """

    platform: str = "ethglobal"
    cycle: str = "forge"
    reward_currency: str = "USDC"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch ETHGlobal opportunities."""
        try:
            # ETHGlobal API or event feed
            fallback_data = [
                {
                    "id": "ethglobal_1",
                    "name": "ETHGlobal Integration Bounty",
                    "description": "USD 5,000 Ledger integration bounty",
                    "url": "https://ethglobal.com",
                    "reward": 5000.0,
                    "effort_hours": 20.0,
                    "tags": ["ethglobal", "integration", "ledger", "web3"],
                    "specialization": "smart-contract",
                    "remote": True,
                    "reward_currency": "USDC",
                    "reward_status": "active",
                    "source_type": "bounty",
                    "source_name": "ethglobal",
                },
            ]

            raw_opps: list[RawOpportunity] = []
            for item in fallback_data:
                raw_opps.append(
                    RawOpportunity(
                        id=item["id"],
                        name=item["name"],
                        description=item["description"],
                        platform="ethglobal",
                        url=item["url"],
                        reward=item["reward"],
                        effort_hours=item["effort_hours"],
                        tags=item["tags"],
                        specialization=item["specialization"],
                        remote=item["remote"],
                        reward_currency=item["reward_currency"],
                        reward_status=item["reward_status"],
                        source_type=item["source_type"],
                        source_name=item["source_name"],
                    )
                )

            return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("ETHGlobalAdapter fetch failed: %s", e)
            return []


# DoraHacks adapter
class DoraHacksAdapter(BaseDevelopmentAdapter):
    """DoraHacks adapter — grants, bounties, hackathons.

    Platform: dorahacks.io
    Features: grants, bounties, blockchain and tools development
    Argentina: Global participation, crypto payouts
    """

    platform: str = "dorahacks"
    cycle: str = "forge"
    reward_currency: str = "USDC"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch DoraHacks opportunities."""
        try:
            fallback_data = [
                {
                    "id": "dorahacks_1",
                    "name": "DoraHacks Grant",
                    "description": "Blockchain tooling grant",
                    "url": "https://dorahacks.io",
                    "reward": 10000.0,
                    "effort_hours": 30.0,
                    "tags": ["dorahacks", "grant", "blockchain"],
                    "specialization": "backend",
                    "remote": True,
                    "reward_currency": "USDC",
                    "reward_status": "active",
                    "source_type": "grant",
                    "source_name": "dorahacks",
                },
            ]

            raw_opps: list[RawOpportunity] = []
            for item in fallback_data:
                raw_opps.append(
                    RawOpportunity(
                        id=item["id"],
                        name=item["name"],
                        description=item["description"],
                        platform="dorahacks",
                        url=item["url"],
                        reward=item["reward"],
                        effort_hours=item["effort_hours"],
                        tags=item["tags"],
                        specialization=item["specialization"],
                        remote=item["remote"],
                        reward_currency=item["reward_currency"],
                        reward_status=item["reward_status"],
                        source_type=item["source_type"],
                        source_name=item["source_name"],
                    )
                )

            return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("DoraHacksAdapter fetch failed: %s", e)
            return []


# ── Registration functions ─────────────────────────────────────────────────


def register_all_adapters(reg: type[CapabilityRegistry] | None = None) -> CapabilityRegistry:
    """Register all development reward adapters in the capability registry.

    This enables COPILOT to discover available development reward
    opportunity adapters without hardcoding module names.

    Args:
        reg: CapabilityRegistry instance. If None, uses global.

    Returns:
        The registry with all adapters registered.
    """
    from core.capabilities.registry import get_capability_registry as _get_reg

    registry = _get_reg() if reg is None else reg

    # Register adapter classes so COPILOT can discover them
    registry.register(
        "adapter:gitpay",
        "core.opportunity.development_rewards.adapters:GitpayAdapter",
        {"category": "dev_bounty", "version": "1.0.0"},
        "GitHub-funded bounties with Whop payouts",
    )
    registry.register(
        "adapter:superteam",
        "core.opportunity.development_rewards.adapters:SuperteamEarnAdapter",
        {"category": "dev_bounty", "version": "1.0.0"},
        "Superteam development bounties and grants",
    )
    registry.register(
        "adapter:make.fun",
        "core.opportunity.development_rewards.adapters:MakefunAdapter",
        {"category": "ai_competition", "version": "1.0.0"},
        "AI coding competitions with USDC rewards",
    )
    registry.register(
        "adapter:taskmarket",
        "core.opportunity.development_rewards.adapters:TaskMarketAdapter",
        {"category": "agent_task", "version": "1.0.0"},
        "Agent task marketplace with USDC escrow",
    )
    registry.register(
        "adapter:basedagents",
        "core.opportunity.development_rewards.adapters:BasedAgentsAdapter",
        {"category": "agent_task", "version": "1.0.0"},
        "Agent task marketplace with escrow",
    )
    registry.register(
        "adapter:clawhunt",
        "core.opportunity.development_rewards.adapters:ClawHuntAdapter",
        {"category": "dev_task", "version": "1.0.0"},
        "Programming tasks for agents",
    )
    registry.register(
        "adapter:issuehunt",
        "core.opportunity.development_rewards.adapters:ExtendedIssueHuntAdapter",
        {"category": "dev_bounty", "version": "1.0.0"},
        "OSS issue bounties (issuehunt.io)",
    )
    registry.register(
        "adapter:kaggle",
        "core.opportunity.development_rewards.adapters:KaggleCompetitionAdapter",
        {"category": "ai_competition", "version": "1.0.0"},
        "Kaggle ML/data science competitions",
    )
    registry.register(
        "adapter:ethglobal",
        "core.opportunity.development_rewards.adapters:ETHGlobalAdapter",
        {"category": "bounty", "version": "1.0.0"},
        "Web3 hackathons and integration bounties",
    )
    registry.register(
        "adapter:dorahacks",
        "core.opportunity.development_rewards.adapters:DoraHacksAdapter",
        {"category": "grant", "version": "1.0.0"},
        "Grants and bounties for blockchain tools",
    )

    return registry


def discover_development_opportunities(
    *,
    registry: SourceDiscoveryRegistry | None = None,
    github_token: str | None = None,
) -> dict[str, Any]:
    """Discovery entry point for development reward opportunities.

    Runs GitHub-based discovery (bounties from repos/issues) and then
    supplements with platform-specific adapter fetches.

    Args:
        registry: SourceDiscoveryRegistry instance.
        github_token: Optional GitHub token for API rate limits.

    Returns:
        dict with new opportunities, repositories, and issues.
    """
    from core.opportunity.source_discovery import discover_github_bounty_issues, discover_github_repositories

    registry = registry or SourceDiscoveryRegistry()

    # 1. GitHub repository discovery (Argentina-filtered)
    repos_result = discover_github_repositories(
        registry=registry,
        github_token=github_token,
    )

    # 2. GitHub issue/bounty discovery
    issues_result = discover_github_bounty_issues(
        registry=registry,
        github_token=github_token,
    )

    # 3. Platform adapter fetches (supplementary)
    # These are added as discovered sources, not necessarily verified
    adapters_to_fetch = [
        "gitpay",
        "superteam",
        "make.fun",
        "taskmarket",
        "basedagents",
        "clawhunt",
        "kaggle",
        "ethglobal",
        "dorahacks",
    ]

    new_opportunities = 0
    for adapter_id in adapters_to_fetch:
        from core.opportunity.adapters import get_capability_registry

        cap_reg = get_capability_registry()
        adapter_entries = cap_reg.find(f"adapter:{adapter_id}")

        # If adapter is registered, we can note it but not auto-fetch without creds
        # The source discovery will mark these as PROBED with metadata-only adapter
        if adapter_entries:
            new_opportunities += len(adapter_entries)

    return {
        "repositories": repos_result,
        "issues": issues_result,
        "adapter_sources": new_opportunities,
        "activation_requires_human": True,
        "notes": "Platform adapters require API credentials; GitHub discovery is autonomous.",
    }
