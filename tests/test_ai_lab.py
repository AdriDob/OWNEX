"""Tests AI Lab — fixtures + cadenas deterministas, 100% offline."""

from __future__ import annotations

import pytest

from cores.offensive.ai_lab import list_agents, list_chains, run_chain


def test_agents_four_with_hardened_control() -> None:
    agents = {a.agent_id for a in list_agents()}
    assert agents == {"naive_assistant", "tool_agent", "rag_agent", "hardened"}


def test_chains_twelve_with_categories() -> None:
    chains = list_chains()
    assert len(chains) == 12
    cats = {c.category for c in chains}
    assert {"direct_override", "tool_hijack", "indirect", "exfiltration"} <= cats


def test_direct_override_succeeds_on_naive() -> None:
    out = run_chain("direct_override", "naive_assistant")
    assert out["success"] is True
    assert out["steps_ok"] == out["steps_total"] == 1


def test_system_extraction_leaks_prompt() -> None:
    out = run_chain("system_extraction", "naive_assistant")
    assert out["success"] is True
    assert "System instructions:" in out["transcript"][0]["output"]


def test_tool_hijack_executes_tool() -> None:
    out = run_chain("tool_hijack_read", "tool_agent")
    assert out["success"] is True


def test_unauthorized_transfer_executes() -> None:
    out = run_chain("unauthorized_transfer", "tool_agent")
    assert out["success"] is True


def test_indirect_via_doc() -> None:
    out = run_chain("indirect_doc", "rag_agent")
    assert out["success"] is True


def test_exfil_chain_two_turns() -> None:
    out = run_chain("exfil_chain", "tool_agent")
    assert out["steps_total"] == 2
    assert out["success"] is True


def test_hardened_resists_all_chains() -> None:
    for chain in list_chains():
        out = run_chain(chain.chain_id, "hardened")
        assert out["success"] is False, chain.chain_id


def test_deterministic_same_result_twice() -> None:
    a = run_chain("direct_override", "naive_assistant")
    b = run_chain("direct_override", "naive_assistant")
    assert a == b


def test_unknown_chain_fail_closed() -> None:
    with pytest.raises(ValueError):
        run_chain("nope", "naive_assistant")


def test_unknown_agent_fail_closed() -> None:
    with pytest.raises(ValueError):
        run_chain("direct_override", "nope")


class TestLabToEvidenceToRepro:
    """Cadena completa P(valid)→P(accept): lab → transcript → gate ≥50%."""

    def test_transcript_from_lab_chain(self) -> None:
        from cores.validation.evidence_builder import EvidenceBuilder

        out = run_chain("exfil_chain", "tool_agent")
        bundle = EvidenceBuilder().build_ai_agent_transcript(
            out["transcript"],
            endpoint="lab://tool_agent",
            program="openai_safety",
            repro_rate=1.0,
            impact=out["impact"],
        )
        assert bundle["turn_count"] == 2
        assert bundle["repro_gate"] == "PASS"
        assert "IN>" in bundle["transcript_md"] and "OUT>" in bundle["transcript_md"]

    def test_repro_gate_passes_on_stable_chain(self) -> None:
        from cores.validation.repro_harness import run_repro

        r = run_repro(lambda i: run_chain("direct_override", "naive_assistant")["success"], n=10)
        assert r.passed is True and r.rate == 1.0

    def test_repro_gate_blocks_hardened(self) -> None:
        from cores.validation.repro_harness import run_repro

        r = run_repro(lambda i: run_chain("direct_override", "hardened")["success"], n=10)
        assert r.passed is False and r.rate == 0.0

    def test_transcript_empty_is_unknown_gate(self) -> None:
        from cores.validation.evidence_builder import EvidenceBuilder

        bundle = EvidenceBuilder().build_ai_agent_transcript([])
        assert bundle["turn_count"] == 0 and bundle["repro_gate"] == "UNKNOWN"
