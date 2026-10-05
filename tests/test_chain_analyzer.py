"""Tests Chain Analyzer — casos controlados, 100% offline, sin ejecución."""

from __future__ import annotations

from cores.offensive.chain_analyzer import MAX_CONFIDENCE, analyze, list_rules


def _f(fid: str, vtype: str, target: str = "acme") -> dict:
    return {"id": fid, "vulnerability_type": vtype, "target": target}


def test_twelve_rules() -> None:
    assert len(list_rules()) == 12
    assert {r.rule_id for r in list_rules()} == {
        "cors_plus_session",
        "open_redirect_plus_token",
        "ssrf_to_cloud",
        "idor_mass_extraction",
        "auth_bypass_to_privileged",
        "stored_xss_to_admin",
        "sqli_to_rce_path",
        "leaked_key_to_api_abuse",
        "prompt_injection_to_tool_abuse",
        "rate_limit_missing_to_takeover",
        "bacl_to_privilege",
        "flow_value_on_foreign_object",
    }


def test_bacl_to_privilege_fires() -> None:
    out = analyze([_f("a", "bacl"), _f("b", "admin_endpoint")])
    assert [h.rule_id for h in out] == ["bacl_to_privilege"]
    assert out[0].severity == "critical"


def test_flow_value_on_foreign_object_fires() -> None:
    out = analyze([_f("a", "business_logic"), _f("b", "idor")])
    assert [h.rule_id for h in out] == ["flow_value_on_foreign_object"]
    assert out[0].severity == "high"


def test_bacl_chain_needs_both_groups() -> None:
    assert analyze([_f("a", "bacl")]) == []


def test_cors_plus_session_fires() -> None:
    out = analyze([_f("a", "cors_misconfiguration"), _f("b", "token_exposure")])
    assert [h.rule_id for h in out] == ["cors_plus_session"]
    h = out[0]
    assert h.severity == "critical" and h.finding_ids == ["a", "b"]
    assert h.prerequisites and h.evidence_required and h.human_validation_steps
    assert "Human Gate" in h.expected_impact or "CROSS" not in h.relationship


def test_ssrf_to_cloud_needs_both_groups() -> None:
    assert analyze([_f("a", "ssrf_blind")]) == []  # falta segundo grupo
    out = analyze([_f("a", "ssrf"), _f("b", "cloud_metadata")])
    assert out[0].rule_id == "ssrf_to_cloud"


def test_prompt_injection_chain_maps_ai() -> None:
    out = analyze([_f("a", "prompt_injection"), _f("b", "tool_execution")])
    assert out[0].rule_id == "prompt_injection_to_tool_abuse"
    assert "repro harness" in " ".join(out[0].human_validation_steps)


def test_cross_target_penalizes_confidence() -> None:
    same = analyze([_f("a", "cors_misconfiguration"), _f("b", "token_exposure")])[0]
    cross = analyze([_f("a", "cors_misconfiguration", "acme"), _f("b", "token_exposure", "other")])[0]
    assert cross.confidence < same.confidence
    assert "CROSS-TARGET" in cross.relationship


def test_confidence_never_exceeds_cap() -> None:
    out = analyze([_f("a", "cors_misconfiguration"), _f("b", "session_exposure")])
    assert all(h.confidence <= MAX_CONFIDENCE for h in out)


def test_unrelated_findings_no_fire() -> None:
    assert analyze([_f("a", "xss_reflected"), _f("b", "info_disclosure")]) == []


def test_unknown_types_ignored() -> None:
    assert analyze([_f("a", "whatever"), _f("b", "cors_misconfiguration")]) == []


def test_empty_and_missing_ids() -> None:
    assert analyze([]) == []
    assert analyze([{"vulnerability_type": "ssrf"}]) == []


def test_sorted_by_confidence_desc() -> None:
    out = analyze([_f("a", "cors_misconfiguration"), _f("b", "token_exposure"), _f("c", "sqli"), _f("d", "file_read")])
    confs = [h.confidence for h in out]
    assert confs == sorted(confs, reverse=True) and len(out) == 2


def test_deterministic() -> None:
    fs = [_f("a", "idor"), _f("b", "collection_endpoint")]
    assert [h.to_dict() for h in analyze(fs)] == [h.to_dict() for h in analyze(fs)]


def test_to_dict_shape() -> None:
    d = analyze([_f("a", "idor"), _f("b", "user_enumeration")])[0].to_dict()
    assert set(d) == {
        "chain_id",
        "rule_id",
        "finding_ids",
        "prerequisites",
        "relationship",
        "expected_impact",
        "severity",
        "confidence",
        "novelty_risk",
        "evidence_required",
        "human_validation_steps",
    }
    assert d["chain_id"].startswith("idor_mass_extraction:")


class _FakeFinding:
    def __init__(self, fid: int, target_id: int, vtype: str, status: str = "open") -> None:
        self.id = fid
        self.target_id = target_id
        self.vulnerability_type = vtype
        self.status = status
        self.notes = "{}"


class _FakeQuery:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def filter(self, *args: object, **kwargs: object) -> _FakeQuery:
        return self

    def limit(self, n: int) -> _FakeQuery:
        return self

    def all(self) -> list:
        return list(self._rows)

    def first(self) -> object | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, findings: list) -> None:
        self._findings = findings

    def query(self, model: object) -> _FakeQuery:
        return _FakeQuery(self._findings)


class TestAnalyzeChainsForFinding:
    def test_sin_vecinos_retorna_vacio(self) -> None:
        from cores.offensive.chain_analyzer import analyze_chains_for_finding

        session = _FakeSession([_FakeFinding(1, 10, "sqli")])
        assert analyze_chains_for_finding(session, 1) == []

    def test_vecino_compatible_retorna_cadena(self) -> None:
        from cores.offensive.chain_analyzer import analyze_chains_for_finding

        session = _FakeSession([_FakeFinding(1, 10, "sqli"), _FakeFinding(2, 10, "file_read")])
        out = analyze_chains_for_finding(session, 1)
        assert len(out) == 1 and out[0]["rule_id"] == "sqli_to_rce_path"
        assert out[0]["finding_ids"] == ["1", "2"]

    def test_umbral_filtra_bajas(self) -> None:
        from cores.offensive.chain_analyzer import analyze_chains_for_finding

        session = _FakeSession([_FakeFinding(1, 10, "sqli"), _FakeFinding(2, 10, "file_read")])
        assert analyze_chains_for_finding(session, 1, min_confidence=0.9) == []

    def test_finding_inexistente_retorna_vacio(self) -> None:
        from cores.offensive.chain_analyzer import analyze_chains_for_finding

        assert analyze_chains_for_finding(_FakeSession([]), 999) == []

    def test_nunca_raisea_con_sesion_rota(self) -> None:
        from cores.offensive.chain_analyzer import analyze_chains_for_finding

        class Broken:
            def query(self, model: object) -> object:
                raise RuntimeError("db caída")

        assert analyze_chains_for_finding(Broken(), 1) == []


class TestPromoterChainHook:
    def test_promote_anota_sin_romper(self) -> None:
        from cores.validation.promoter import ValidationPromoter

        promoter = ValidationPromoter()
        session = _FakeSession([_FakeFinding(1, 10, "sqli"), _FakeFinding(2, 10, "file_read")])
        chains = promoter._annotate_chain_hypotheses(session, 1)
        assert len(chains) == 1 and chains[0]["rule_id"] == "sqli_to_rce_path"

    def test_hook_nunca_raisea(self) -> None:
        from cores.validation.promoter import ValidationPromoter

        promoter = ValidationPromoter()

        class Broken:
            def query(self, model: object) -> object:
                raise RuntimeError("db caída")

        assert promoter._annotate_chain_hypotheses(Broken(), 1) == []
        assert promoter._annotate_chain_hypotheses(None, 1) == []  # type: ignore[arg-type]
