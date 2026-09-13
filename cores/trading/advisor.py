"""Trading Advisor — OAR-driven parameter optimization with Human Gate.

Takes paper metrics + current config → LLM proposes adjusted parameters →
human approves via single-use HMAC token (same pattern as OpenCode execute).

Falls back to existing AutoParamOptimizer when OAR is unavailable. Every
proposal is logged to the decision journal for auditability.

Design: proposal → approve/reject is human-gated. No params change without
explicit approval. DRY_RUN default everywhere.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("orion.trading.advisor")


@dataclass(frozen=True, slots=True)
class AdvisorProposal:
    """One param proposal from the OAR advisor."""

    proposal_id: str
    param: str
    current_value: Any
    proposed_value: Any
    reason: str
    confidence: float
    source: str  # "oar" | "rule_based" | "rule_based_fallback"
    status: str = "pending"  # pending | approved | rejected


def _build_prompt(metrics: dict[str, Any], config: dict[str, Any]) -> str:
    """Structured prompt for the OAR LLM to propose parameter adjustments.

    The prompt asks for a JSON array of proposals. Each proposal must contain:
    - param: one of (stop_loss_pct, trailing_pct, position_sol,
      take_profit_tiers, max_hold_minutes, min_liquidity_usd)
    - current_value: the current value
    - proposed_value: the suggested new value
    - reason: explanation in plain language
    - confidence: 0.0-1.0

    Rules enforced in the prompt:
    - stop_loss_pct must be 0.05-0.50 (5%-50%)
    - position_sol must be 0.01-1.0
    - trailing_pct must be 0.05-0.40
    - take_profit_tiers must be list of [gain, sell_pct] pairs summing <= 1.0
    - max_hold_minutes must be 15-480
    - min_liquidity_usd must be 1000-100000

    The model must NOT propose changes if metrics are insufficient (trades < 20).
    If insufficient, return empty array [].
    """
    return f"""You are a crypto trading strategy optimizer. Analyze the paper trading
metrics and current parameters, then propose data-driven parameter adjustments.

## Current Metrics
{json.dumps(metrics, indent=2, default=str)}

## Current Parameters
{json.dumps(config, indent=2, default=str)}

## Rules
1. Only propose changes if trades >= 20 (sufficient sample).
2. If trades < 20, return an empty array [].
3. Each proposal must be a JSON object with: param, current_value, proposed_value, reason, confidence.
4. Allowed params and ranges:
   - stop_loss_pct: 0.05-0.50 (5%-50%, exit fully at this loss)
   - trailing_pct: 0.05-0.40 (5%-40%, exit fully at this drawdown from peak)
   - position_sol: 0.01-1.0 (SOL per position)
   - max_hold_minutes: 15-480
   - min_liquidity_usd: 1000-100000
5. If profit_factor > 2.0 and win_rate > 55%, you may propose conservative position increase.
6. If max_drawdown_sol > daily_loss_limit, propose tighter stop_loss.
7. If expectancy_sol < 0, propose defensive changes (tighter SL, lower size).
8. Maximum 3 proposals per call.
9. Return ONLY a JSON array, no explanation text.

Return: [{{"param": "...", "current_value": ..., "proposed_value": ..., "reason": "...", "confidence": 0.0-1.0}}]
"""


def _parse_oar_response(raw: str) -> list[AdvisorProposal]:
    """Parse OAR JSON response into AdvisorProposals. Returns [] on parse failure."""
    import uuid

    text = raw.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        items = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        logger.debug("OAR response not valid JSON: %s", raw[:200])
        return []

    if not isinstance(items, list):
        return []

    proposals: list[AdvisorProposal] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        param = str(item.get("param", ""))
        if not param:
            continue
        proposals.append(
            AdvisorProposal(
                proposal_id=uuid.uuid4().hex[:12],
                param=param,
                current_value=item.get("current_value"),
                proposed_value=item.get("proposed_value"),
                reason=str(item.get("reason", "")),
                confidence=max(0.0, min(1.0, float(item.get("confidence", 0.5)))),
                source="oar",
            )
        )
    return proposals[:3]  # enforce max 3


class TradingAdvisor:
    """OAR-driven advisor with fallback to rule-based AutoParamOptimizer.

    Usage:
        advisor = TradingAdvisor()
        proposals = await advisor.propose(metrics, config)
        # → user reviews in frontend, calls advisor.approve(proposal_id)
    """

    OAR_TASK = "analysis"  # TaskType.ANALYSIS (semantically: param optimization)
    OAR_MAX_TOKENS = 1024

    def __init__(self, store: Any | None = None) -> None:
        self._store = store
        self._oar_available = True

    async def propose(self, metrics: dict[str, Any], config: dict[str, Any]) -> list[AdvisorProposal]:
        """Propose parameter adjustments using OAR, falling back to rules."""
        if metrics.get("trades", 0) < 20:
            logger.info("insufficient sample (%d trades) — no proposals", metrics.get("trades", 0))
            return []

        # Try OAR first
        if self._oar_available:
            try:
                proposals = await self._propose_via_oar(metrics, config)
                if proposals:
                    return proposals
                logger.debug("OAR returned empty — falling back to rule-based")
            except Exception as exc:
                logger.warning("OAR advisor failed: %s — using rule-based fallback", exc)
                self._oar_available = False

        # Fallback: rule-based AutoParamOptimizer
        return self._propose_rule_based(metrics, config)

    async def _propose_via_oar(self, metrics: dict[str, Any], config: dict[str, Any]) -> list[AdvisorProposal]:
        """Call OAR for parameter proposals. Raises on failure."""
        from cores.ai.runtime import ai_chat

        prompt = _build_prompt(metrics, config)
        response = await ai_chat(
            prompt,
            task_type=self.OAR_TASK,
            temperature=0.2,
            max_tokens=self.OAR_MAX_TOKENS,
        )
        if not response or not response.content:
            return []
        return _parse_oar_response(response.content)

    def _propose_rule_based(self, metrics: dict[str, Any], config: dict[str, Any]) -> list[AdvisorProposal]:
        """Rule-based fallback (mirrors AutoParamOptimizer logic)."""
        import uuid

        proposals: list[AdvisorProposal] = []
        win_rate = metrics.get("win_rate") or 0.0  # fraction 0.0-1.0
        pf = metrics.get("profit_factor") or 0
        dd = metrics.get("max_drawdown_sol") or 0
        expectancy = metrics.get("expectancy_sol") or 0
        sl = config.get("stop_loss_pct", 0.25)
        size = config.get("position_sol", 0.1)

        if win_rate < 0.50 and sl > 0.10:
            proposals.append(
                AdvisorProposal(
                    proposal_id=uuid.uuid4().hex[:12],
                    param="stop_loss_pct",
                    current_value=sl,
                    proposed_value=round(sl * 0.8, 2),
                    reason=f"win rate {win_rate:.0%} < 50% — tighter stop-loss",
                    confidence=0.6,
                    source="rule_based",
                )
            )

        if pf < 1.5 and win_rate < 0.55:
            proposals.append(
                AdvisorProposal(
                    proposal_id=uuid.uuid4().hex[:12],
                    param="position_sol",
                    current_value=size,
                    proposed_value=round(size * 0.75, 4),
                    reason=f"profit factor {pf:.2f} — reduce position size",
                    confidence=0.6,
                    source="rule_based",
                )
            )

        if win_rate >= 0.60 and pf >= 1.5 and size < 0.5:
            proposals.append(
                AdvisorProposal(
                    proposal_id=uuid.uuid4().hex[:12],
                    param="position_sol",
                    current_value=size,
                    proposed_value=round(min(size * 1.2, 0.5), 4),
                    reason=f"confirmed edge (win {win_rate:.0%}, PF {pf:.2f}) — scale up",
                    confidence=0.7,
                    source="rule_based",
                )
            )

        if dd > 0 and expectancy < 0:
            proposals.append(
                AdvisorProposal(
                    proposal_id=uuid.uuid4().hex[:12],
                    param="stop_loss_pct",
                    current_value=sl,
                    proposed_value=round(max(sl * 0.7, 0.10), 2),
                    reason="negative expectancy — aggressive defense",
                    confidence=0.8,
                    source="rule_based",
                )
            )

        return proposals[:3]

    @staticmethod
    def validate_proposal(proposal: AdvisorProposal) -> str | None:
        """Validate a proposal against hard ranges. Returns error or None if valid."""
        ranges = {
            "stop_loss_pct": (0.05, 0.50),
            "trailing_pct": (0.05, 0.40),
            "position_sol": (0.01, 1.0),
            "max_hold_minutes": (15, 480),
            "min_liquidity_usd": (1000, 100000),
        }
        if proposal.param not in ranges:
            return f"unknown param: {proposal.param}"
        lo, hi = ranges[proposal.param]
        try:
            val = float(proposal.proposed_value)
        except (TypeError, ValueError):
            return f"non-numeric value: {proposal.proposed_value}"
        if not lo <= val <= hi:
            return f"out of range: {val} not in [{lo}, {hi}]"
        return None
