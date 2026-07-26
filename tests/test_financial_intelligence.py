from __future__ import annotations

from core.financial_intelligence.agent_framework import (
    AgentCouncil,
    AtlasAgent,
    FinancialIntelligencePipeline,
    MidasAgent,
    PortfolioAgent,
    RiskAgent,
)
from core.financial_intelligence.f1_assistant import F1Assistant
from core.financial_intelligence.models import F1Message, Opportunity, RiskPolicy
from core.financial_intelligence.opportunity_engine import OpportunityEngine
from core.financial_intelligence.publisher import FinancialIntelligencePublisher
from core.financial_intelligence.risk_engine import RiskEngine


def _make_opp(**kw) -> Opportunity:
    defaults = {
        "source": "bug_bounty",
        "label": "Test opportunity",
        "expected_value": 5000.0,
        "confidence_interval": (4000.0, 6000.0),
        "historical_win_rate": 0.6,
        "volatility": 0.3,
        "liquidity": 0.8,
        "risk_score": 0.4,
        "correlation": 0.3,
        "opportunity_cost": 100.0,
        "execution_complexity": 0.5,
        "market_regime": "bull",
        "data_quality": 0.9,
        "model_confidence": 0.8,
        "consensus_score": 0.0,
        "priority_score": 0.0,
        "estimated_effort_hours": 10.0,
        "estimated_time_to_payout_days": 30.0,
    }
    defaults.update(kw)
    return Opportunity(**defaults)


# ── Opportunity Engine ──────────────────────────────────────────


class TestOpportunityEngine:
    def test_score_high_value(self):
        opp = _make_opp(expected_value=10000.0, risk_score=0.1, historical_win_rate=0.9)
        engine = OpportunityEngine()
        score = engine.score(opp)
        assert 0.0 <= score <= 1.0

    def test_score_low_value(self):
        opp = _make_opp(expected_value=10.0, risk_score=0.9, historical_win_rate=0.1)
        engine = OpportunityEngine()
        score = engine.score(opp)
        assert score >= 0.0

    def test_evaluate_applies_rejection(self):
        opp = _make_opp(risk_score=0.95)
        engine = OpportunityEngine()
        result = engine.evaluate(opp)
        assert "Risk score exceeds 0.8 threshold" in result.rejected_reasons

    def test_rank_orders_by_score(self):
        opps = [
            _make_opp(label="low", expected_value=100.0, risk_score=0.9),
            _make_opp(label="high", expected_value=10000.0, risk_score=0.1),
        ]
        engine = OpportunityEngine()
        ranked = engine.rank(opps)
        assert ranked[0].label == "high"

    def test_top_n(self):
        opps = [_make_opp(label=f"opp{i}") for i in range(10)]
        engine = OpportunityEngine()
        top = engine.top_n(opps, 3)
        assert len(top) == 3

    def test_get_statistics(self):
        opp = _make_opp()
        engine = OpportunityEngine()
        engine.evaluate(opp)
        stats = engine.get_statistics()
        assert stats["total_evaluated"] >= 1


# ── Risk Engine ─────────────────────────────────────────────────


class TestRiskEngine:
    def test_check_opportunity_approves(self):
        opp = _make_opp(risk_score=0.3)
        engine = RiskEngine()
        result = engine.check_opportunity(opp)
        assert result["approved"]

    def test_emergency_stop_blocks(self):
        opp = _make_opp()
        engine = RiskEngine()
        engine.activate_emergency_stop()
        result = engine.check_opportunity(opp)
        assert not result["approved"]
        assert "Emergency stop" in result["violations"][0]

    def test_circuit_breaker_blocks(self):
        opp = _make_opp()
        engine = RiskEngine()
        engine.activate_circuit_breaker()
        result = engine.check_opportunity(opp)
        assert not result["approved"]

    def test_max_position_size(self):
        opp = _make_opp(expected_value=10000.0)
        engine = RiskEngine()
        result = engine.check_opportunity(opp, current_portfolio_value=50000.0)
        assert result["max_position_size"] == 1000.0  # 2% of 50K

    def test_record_trade_updates_daily_pnl(self):
        engine = RiskEngine()
        engine.record_trade(1000.0, -50.0)
        assert engine._daily_loss() > 0

    def test_get_status(self):
        engine = RiskEngine()
        status = engine.get_status()
        assert "emergency_stop" in status


# ── Agent Council ───────────────────────────────────────────────


class TestAgentCouncil:
    def test_evaluate_returns_votes(self):
        opp = _make_opp()
        council = AgentCouncil()
        result = council.evaluate(opp)
        assert "consensus_score" in result
        assert "votes" in result
        assert "atlas" in result["votes"]
        assert "midas" in result["votes"]
        assert "risk_engine" in result["votes"]
        assert "portfolio" in result["votes"]

    def test_high_risk_opportunity_blocked(self):
        opp = _make_opp(risk_score=0.9, liquidity=0.1)
        council = AgentCouncil()
        result = council.evaluate(opp)
        assert result["consensus_score"] >= 0.0

    def test_register_custom_agent(self):
        opp = _make_opp()
        council = AgentCouncil()
        agent = PortfolioAgent()
        council.register_agent("custom", agent)
        result = council.evaluate(opp)
        assert "custom" in result["votes"]

    def test_get_statistics(self):
        opp = _make_opp()
        council = AgentCouncil()
        council.evaluate(opp)
        stats = council.get_statistics()
        assert stats["total_evaluated"] == 1


# ── Individual Agents ───────────────────────────────────────────


class TestAgents:
    def test_atlas_agent(self):
        opp = _make_opp()
        agent = AtlasAgent()
        vote = agent.evaluate(opp)
        assert vote.agent_name == "atlas"
        assert 0.0 <= vote.score <= 1.0

    def test_midas_agent(self):
        opp = _make_opp(expected_value=5000.0, estimated_effort_hours=10.0)
        agent = MidasAgent()
        vote = agent.evaluate(opp)
        assert vote.agent_name == "midas"

    def test_risk_agent_approves(self):
        opp = _make_opp(risk_score=0.3)
        agent = RiskAgent()
        vote = agent.evaluate(opp)
        assert vote.agent_name == "risk_engine"
        assert vote.score > 0.0

    def test_risk_agent_rejects_high_risk(self):
        opp = _make_opp(risk_score=0.95, liquidity=0.0)
        engine = RiskEngine()
        engine.activate_emergency_stop()
        agent = RiskAgent(engine)
        vote = agent.evaluate(opp)
        assert vote.score == 0.0

    def test_portfolio_agent_low_correlation(self):
        opp = _make_opp(correlation=0.3)
        agent = PortfolioAgent()
        vote = agent.evaluate(opp)
        assert vote.score > 0.5

    def test_portfolio_agent_high_correlation(self):
        opp = _make_opp(correlation=0.9)
        agent = PortfolioAgent()
        vote = agent.evaluate(opp)
        assert vote.score < 0.5


# ── F1 Assistant ────────────────────────────────────────────────


class TestF1Assistant:
    def test_greet(self):
        f1 = F1Assistant()
        msg = f1.greet()
        assert msg.category == "info"
        assert "F1" in msg.title

    def test_explain_opportunity(self):
        opp = _make_opp(priority_score=0.8)
        f1 = F1Assistant()
        msg = f1.explain_opportunity(opp)
        assert "Test opportunity" in msg.body

    def test_warn_risk(self):
        f1 = F1Assistant()
        msg = f1.warn_risk("High risk", "Drawdown at 20%")
        assert msg.category == "risk"

    def test_celebrate_success(self):
        f1 = F1Assistant()
        msg = f1.celebrate_success("Trade", 500.0)
        assert msg.category == "success"

    def test_request_confirmation(self):
        f1 = F1Assistant()
        msg = f1.request_confirmation("Confirm trade", "Buy $1000 of BTC")
        assert msg.requires_action
        assert msg.action_label == "Confirmar"

    def test_daily_briefing(self):
        opp = _make_opp(expected_value=5000.0, priority_score=0.8)
        f1 = F1Assistant()
        msg = f1.daily_briefing([opp], 25000.0, {"drawdown": 0.05, "daily_loss": 0.01})
        assert msg.category == "info"

    def test_get_messages(self):
        f1 = F1Assistant()
        f1.greet()
        msgs = f1.get_messages()
        assert len(msgs) >= 1


# ── Publisher ───────────────────────────────────────────────────


class TestPublisher:
    def test_bind_and_publish(self):
        published: list[str] = []

        def fake_publish(event, **data):
            published.append(event)

        pub = FinancialIntelligencePublisher()
        pub.bind(fake_publish)
        opp = _make_opp()
        pub.opportunity_evaluated(opp, {"blocked": False})
        assert "financial_intelligence:opportunity:evaluated" in published

    def test_no_bind_does_not_crash(self):
        pub = FinancialIntelligencePublisher()
        opp = _make_opp()
        pub.opportunity_evaluated(opp, {"blocked": False})
        pub.opportunity_accepted(opp)
        pub.opportunity_rejected(opp, ["test"])
        pub.risk_alert_triggered("drawdown", {"pct": 0.2})
        pub.daily_briefing_ready(5, 10000.0)


# ── Pipeline ────────────────────────────────────────────────────


class TestPipeline:
    def test_process_opportunities(self):
        opps = [_make_opp(expected_value=5000.0, priority_score=0.8)]
        pipeline = FinancialIntelligencePipeline()
        results = pipeline.process_opportunities(opps)
        assert len(results) >= 1
        assert results[0]["opportunity"]["label"] == "Test opportunity"

    def test_get_status(self):
        pipeline = FinancialIntelligencePipeline()
        status = pipeline.get_status()
        assert "opportunity_engine" in status
        assert "risk_engine" in status
        assert "council" in status

    def test_low_priority_skipped_by_f1(self):
        opps = [_make_opp(expected_value=1.0, historical_win_rate=0.01, model_confidence=0.01, data_quality=0.01)]
        pipeline = FinancialIntelligencePipeline()
        results = pipeline.process_opportunities(opps)
        score = results[0]["opportunity"]["priority_score"]
        assert score < 0.3, f"Expected score < 0.3, got {score}"


# ── Models ──────────────────────────────────────────────────────


class TestModels:
    def test_opportunity_to_dict(self):
        opp = _make_opp()
        d = opp.to_dict()
        assert d["source"] == "bug_bounty"
        assert d["label"] == "Test opportunity"

    def test_risk_policy_defaults(self):
        policy = RiskPolicy()
        assert policy.position_size_pct == 0.02

    def test_f1_message_to_dict(self):
        msg = F1Message("info", "Test", "Hello")
        d = msg.to_dict()
        assert d["category"] == "info"
