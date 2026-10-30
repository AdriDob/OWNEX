"""Tests for the OAR trading advisor (human-gated param proposals)."""

from __future__ import annotations

import asyncio
from typing import Any

from cores.trading.advisor import (
    AdvisorProposal,
    TradingAdvisor,
    _build_prompt,
    _parse_oar_response,
)
from cores.trading.backtest import BacktestConfig


def _metrics(trades: int = 30, win_rate: float = 0.6, pf: float = 1.8, dd: float = 0.05) -> dict[str, Any]:
    return {
        "trades": trades,
        "wins": int(trades * win_rate),
        "win_rate": win_rate,
        "profit_factor": pf,
        "expectancy_sol": 0.03,
        "realized_pnl_sol": 0.9,
        "max_drawdown_sol": dd,
        "verdict": "EDGE_CANDIDATE",
    }


def _config() -> dict[str, Any]:
    return BacktestConfig().to_dict()


def test_prompt_build_contains_metrics_and_ranges():
    prompt = _build_prompt(_metrics(), _config())
    assert '"trades": 30' in prompt
    assert "stop_loss_pct" in prompt
    assert "trades >= 20" in prompt


def test_parse_valid_oar_json():
    raw = '[{"param":"stop_loss_pct","current_value":0.25,"proposed_value":0.20,"reason":"tighter","confidence":0.7}]'
    proposals = _parse_oar_response(raw)
    assert len(proposals) == 1
    assert proposals[0].param == "stop_loss_pct"
    assert proposals[0].source == "oar"


def test_parse_markdown_fenced_json():
    raw = '```json\n[{"param":"position_sol","current_value":0.1,"proposed_value":0.05,"reason":"reduce","confidence":0.6}]\n```'
    proposals = _parse_oar_response(raw)
    assert len(proposals) == 1
    assert proposals[0].proposed_value == 0.05


def test_parse_invalid_json_returns_empty():
    assert _parse_oar_response("not json at all") == []
    assert _parse_oar_response("") == []


def test_parse_caps_at_three_proposals() -> None:
    items = ",".join(
        f'{{"param":"p{i}","current_value":1,"proposed_value":2,"reason":"r","confidence":0.5}}' for i in range(6)
    )
    raw = f"[{items.rstrip(',')}]"
    proposals = _parse_oar_response(raw)
    assert len(proposals) == 3


def test_no_proposals_below_20_trades():
    advisor = TradingAdvisor()
    result = asyncio.run(advisor.propose(_metrics(trades=10), _config()))
    assert result == []


def test_rule_based_fallback_when_oar_unavailable():
    advisor = TradingAdvisor()
    advisor._oar_available = True

    async def _raises(*args: Any, **kwargs: Any):
        raise RuntimeError("provider down")

    original = advisor._propose_via_oar
    advisor._propose_via_oar = _raises  # type: ignore[method-assign]
    try:
        result = asyncio.run(advisor.propose(_metrics(win_rate=0.4, pf=0.8), _config()))
    finally:
        advisor._propose_via_oar = original  # type: ignore[method-assign]
    assert result
    assert all(p.source == "rule_based" for p in result)
    assert any(p.param == "stop_loss_pct" for p in result)


def test_validate_ranges():
    ok = AdvisorProposal("id", "stop_loss_pct", 0.25, 0.20, "x", 0.5, "oar")
    assert TradingAdvisor.validate_proposal(ok) is None

    bad_param = AdvisorProposal("id", "nonsense", 1, 2, "x", 0.5, "oar")
    assert "unknown param" in str(TradingAdvisor.validate_proposal(bad_param))

    out_of_range = AdvisorProposal("id", "stop_loss_pct", 0.25, 2.5, "x", 0.5, "oar")
    assert "out of range" in str(TradingAdvisor.validate_proposal(out_of_range))

    non_numeric = AdvisorProposal("id", "position_sol", 0.1, "abc", "x", 0.5, "oar")
    assert "non-numeric" in str(TradingAdvisor.validate_proposal(non_numeric))


def test_validate_passfor_all_params():
    for param, (_lo, _hi), val in [
        ("stop_loss_pct", (0.05, 0.50), 0.30),
        ("trailing_pct", (0.05, 0.40), 0.25),
        ("position_sol", (0.01, 1.0), 0.5),
        ("max_hold_minutes", (15, 480), 120),
        ("min_liquidity_usd", (1000, 100000), 20000),
    ]:
        p = AdvisorProposal("id", param, val, val, "x", 0.5, "oar")
        assert TradingAdvisor.validate_proposal(p) is None, f"{param} should be valid"


def test_rule_based_positive_scale_up():
    advisor = TradingAdvisor()
    result = advisor._propose_rule_based(_metrics(win_rate=0.65, pf=2.2), _config())
    assert any(p.param == "position_sol" and p.proposed_value > p.current_value for p in result)


def test_oar_proposals_capped_at_3():
    advisor = TradingAdvisor()

    async def _many(*args: Any, **kwargs: Any):
        items = ",".join(
            f'{{"param":"position_sol","current_value":0.1,"proposed_value":0.0{i},"reason":"r{i}","confidence":0.5}}'
            for i in range(5)
        )
        return _parse_oar_response(f"[{items}]")

    advisor._propose_via_oar = _many  # type: ignore[method-assign]
    result = asyncio.run(advisor.propose(_metrics(), _config()))
    assert len(result) <= 3


def test_import_oar_runtime_available():
    from cores.ai.runtime import ai_chat  # noqa: F401 — ensure OAR surface importable

    assert callable(ai_chat)
