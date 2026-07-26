from __future__ import annotations

import logging
from typing import Any

from core.financial_intelligence.f1_assistant import F1Assistant
from core.financial_intelligence.models import AgentVote, Opportunity
from core.financial_intelligence.opportunity_engine import OpportunityEngine
from core.financial_intelligence.risk_engine import RiskEngine

logger = logging.getLogger("orion.financial_intelligence.agent_framework")


# ── Built-in agents ─────────────────────────────────────────────


class BaseAgent:
    name: str = "base"

    def evaluate(self, opp: Opportunity) -> AgentVote:
        raise NotImplementedError


class AtlasAgent(BaseAgent):
    """Atlas — investment management. Evaluates portfolio fit and allocation."""

    name = "atlas"

    def evaluate(self, opp: Opportunity) -> AgentVote:
        score = opp.expected_value * opp.historical_win_rate / max(opp.risk_score, 0.01)
        normalized = min(score / 50.0, 1.0)
        evidence = f"Expected value ${opp.expected_value:.0f} × win rate {opp.historical_win_rate:.0%} / risk {opp.risk_score:.2f}"
        return AgentVote(
            agent_name=self.name,
            score=round(normalized, 4),
            confidence=opp.model_confidence,
            evidence=evidence,
            reasoning="Portfolio fit and capital allocation potential",
        )


class MidasAgent(BaseAgent):
    """Midas — income multiplication. Evaluates expected ROI."""

    name = "midas"

    def evaluate(self, opp: Opportunity) -> AgentVote:
        roi = opp.expected_value / max(opp.estimated_effort_hours, 1)
        normalized = min(roi / 1000.0, 1.0)
        return AgentVote(
            agent_name=self.name,
            score=round(normalized, 4),
            confidence=opp.model_confidence * 0.9,
            evidence=f"ROI ${roi:.0f}/hr over {opp.estimated_time_to_payout_days:.0f} days",
            reasoning="Income multiplication potential per unit effort",
        )


class RiskAgent(BaseAgent):
    """Risk Engine — evaluates risk-adjusted return and safety."""

    name = "risk_engine"

    def __init__(self, engine: RiskEngine | None = None):
        self._engine = engine or RiskEngine()

    def evaluate(self, opp: Opportunity) -> AgentVote:
        check = self._engine.check_opportunity(opp)
        if not check["approved"]:
            return AgentVote(
                agent_name=self.name,
                score=0.0,
                confidence=1.0,
                evidence="; ".join(check["violations"]),
                reasoning="Risk policy violations block this opportunity",
            )
        score = 1.0 - opp.risk_score + opp.liquidity * 0.5
        return AgentVote(
            agent_name=self.name,
            score=round(max(0.0, min(score, 1.0)), 4),
            confidence=0.95,
            evidence=f"Risk check passed. Max position: ${check['max_position_size']:.0f}",
            reasoning="Risk-adjusted return and capital preservation",
        )


class PortfolioAgent(BaseAgent):
    """Portfolio Intelligence — evaluates diversification and correlation."""

    name = "portfolio"

    def evaluate(self, opp: Opportunity) -> AgentVote:
        if opp.correlation > 0.7:
            return AgentVote(
                agent_name=self.name,
                score=round(1.0 - opp.correlation, 4),
                confidence=0.85,
                evidence=f"Correlation {opp.correlation:.2f} exceeds 0.7 threshold",
                reasoning="High correlation reduces diversification benefit",
            )
        return AgentVote(
            agent_name=self.name,
            score=round(1.0 - opp.correlation, 4),
            confidence=0.85,
            evidence=f"Correlation {opp.correlation:.2f} — acceptable",
            reasoning="Portfolio diversification maintained",
        )


BUILTIN_AGENTS: dict[str, type] = {
    "atlas": AtlasAgent,
    "midas": MidasAgent,
    "risk_engine": RiskAgent,
    "portfolio": PortfolioAgent,
}


class AgentCouncil:
    """Multi-agent decision model.

    Every opportunity is evaluated by every registered agent.
    Each agent casts a vote (score, confidence, evidence).
    Consensus increases confidence; disagreement reduces it.
    Large disagreement blocks execution until manual review.
    """

    def __init__(self, risk_engine: RiskEngine | None = None):
        self._agents: dict[str, BaseAgent] = {}
        self._risk_engine = risk_engine or RiskEngine()
        for name, cls in BUILTIN_AGENTS.items():
            if name == "risk_engine":
                self._agents[name] = cls(self._risk_engine)
            else:
                self._agents[name] = cls()
        self._vote_history: list[dict[str, Any]] = []

    def register_agent(self, name: str, agent: BaseAgent) -> None:
        self._agents[name] = agent
        logger.info("[COUNCIL] Agent registered: %s", name)

    def evaluate(self, opp: Opportunity) -> dict[str, Any]:
        votes: dict[str, AgentVote] = {}
        for name, agent in self._agents.items():
            try:
                votes[name] = agent.evaluate(opp)
            except Exception as exc:
                logger.warning("[COUNCIL] Agent %s failed: %s", name, exc)
                votes[name] = AgentVote(name, 0.0, 0.0, str(exc), "Evaluation error")

        scores = [v.score for v in votes.values()]
        confidences = [v.confidence for v in votes.values()]
        consensus = sum(s * c for s, c in zip(scores, confidences, strict=False)) / max(sum(confidences), 0.001)
        disagreement = max(scores) - min(scores) if scores else 0.0

        opp.agent_votes = {name: v.score for name, v in votes.items()}
        opp.consensus_score = round(consensus, 4)

        blocked = disagreement > 0.6
        result = {
            "opportunity_id": opp.label,
            "consensus_score": opp.consensus_score,
            "disagreement": round(disagreement, 4),
            "blocked": blocked,
            "blocked_reason": "Large disagreement among agents — manual review required" if blocked else "",
            "votes": {name: v.__dict__ for name, v in votes.items()},
        }

        self._vote_history.append(result)
        return result

    def get_statistics(self) -> dict[str, Any]:
        if not self._vote_history:
            return {"total_evaluated": 0}
        scores = [v["consensus_score"] for v in self._vote_history]
        blocked = sum(1 for v in self._vote_history if v["blocked"])
        return {
            "total_evaluated": len(self._vote_history),
            "avg_consensus": round(sum(scores) / len(scores), 4),
            "blocked_count": blocked,
            "agent_count": len(self._agents),
            "agents": list(self._agents.keys()),
        }


class FinancialIntelligencePipeline:
    """Orchestrates the full financial intelligence pipeline.

    1. Collect opportunities from all sources
    2. Score via OpportunityEngine
    3. Evaluate via RiskEngine
    4. Vote via AgentCouncil
    5. Explain via F1Assistant
    6. Publish results
    """

    def __init__(
        self,
        opportunity_engine: OpportunityEngine | None = None,
        risk_engine: RiskEngine | None = None,
        council: AgentCouncil | None = None,
        f1: F1Assistant | None = None,
    ):
        self.opportunity_engine = opportunity_engine or OpportunityEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.council = council or AgentCouncil(self.risk_engine)
        self.f1 = f1 or F1Assistant()

    def process_opportunities(self, opportunities: list[Opportunity]) -> list[dict[str, Any]]:
        results = []
        scored = self.opportunity_engine.rank(opportunities)
        for opp in scored[:10]:
            risk_check = self.risk_engine.check_opportunity(opp)
            council_result = self.council.evaluate(opp)
            msg = self.f1.explain_opportunity(opp, rank=scored.index(opp) + 1) if opp.priority_score > 0.3 else None
            results.append(
                {
                    "opportunity": opp.to_dict(),
                    "risk_check": risk_check,
                    "council": council_result,
                    "f1_message": msg.to_dict() if msg else None,
                }
            )
        return results

    def get_status(self) -> dict[str, Any]:
        return {
            "opportunity_engine": self.opportunity_engine.get_statistics(),
            "risk_engine": self.risk_engine.get_status(),
            "council": self.council.get_statistics(),
        }
