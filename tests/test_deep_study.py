"""Tests for AEGIS Deep Study Mode — TechAnalyzer, PlaybookEngine, DeepStudyEngine."""

from __future__ import annotations

from apps.aegis.engines.deep_study import (
    TECH_PLAYBOOKS,
    DeepStudyResult,
    PlaybookEngine,
    TechAnalyzer,
)

# ── TechAnalyzer ───────────────────────────────────────────────────


def test_tech_risk_high():
    assert TechAnalyzer.classify_tech_risk("spring boot") == 0.85
    assert TechAnalyzer.classify_tech_risk("firebase") == 0.90
    assert TechAnalyzer.classify_tech_risk("graphql") == 0.75
    assert TechAnalyzer.classify_tech_risk("stripe") == 0.70


def test_tech_risk_medium():
    assert TechAnalyzer.classify_tech_risk("laravel") == 0.55
    assert TechAnalyzer.classify_tech_risk("django") == 0.50
    assert TechAnalyzer.classify_tech_risk("express") == 0.45
    assert TechAnalyzer.classify_tech_risk("nginx") == 0.35


def test_tech_risk_low():
    assert TechAnalyzer.classify_tech_risk("unknown") == 0.20
    assert TechAnalyzer.classify_tech_risk("react") == 0.20
    assert TechAnalyzer.classify_tech_risk("") == 0.20


def test_tech_risk_case_insensitive():
    assert TechAnalyzer.classify_tech_risk("Spring Boot") == 0.85
    assert TechAnalyzer.classify_tech_risk("LARAVEL") == 0.55


def test_aggregate_from_httpx_empty():
    result = TechAnalyzer.aggregate_from_httpx([])
    assert result == []


def test_aggregate_from_httpx():
    httpx_results = [
        {"evidence": {"technologies": ["Vue.js", "nginx"]}},
        {"evidence": {"technologies": ["Laravel"]}},
        {"evidence": {"technologies": ["Vue.js"]}},  # duplicate
    ]
    result = TechAnalyzer.aggregate_from_httpx(httpx_results)
    names = {t["name"].lower() for t in result}
    assert "vue.js" in names
    assert "nginx" in names
    assert "laravel" in names
    assert len(result) == 3


def test_aggregate_from_httpx_no_technologies():
    httpx_results = [
        {"evidence": {"status_code": 200}},
        {"evidence": {}},
        {},
    ]
    result = TechAnalyzer.aggregate_from_httpx(httpx_results)
    assert result == []


def test_aggregate_risk_empty():
    assert TechAnalyzer.aggregate_risk([]) == 0.0


def test_aggregate_risk_single():
    techs = [{"name": "firebase", "risk": 0.90}]
    risk = TechAnalyzer.aggregate_risk(techs)
    assert 0.89 <= risk <= 0.91  # 0.9*0.6 + 0.9*0.4 = 0.9


def test_aggregate_risk_mixed():
    techs = [
        {"name": "react", "risk": 0.20},
        {"name": "spring boot", "risk": 0.85},
        {"name": "nginx", "risk": 0.35},
    ]
    risk = TechAnalyzer.aggregate_risk(techs)
    avg = (0.20 + 0.85 + 0.35) / 3
    expected = round(min(1.0, 0.85 * 0.6 + avg * 0.4), 2)
    assert abs(risk - expected) < 0.01


# ── PlaybookEngine ─────────────────────────────────────────────────


def test_playbook_engine_empty():
    actions = PlaybookEngine.get_actions([])
    assert actions == []


def test_playbook_engine_react():
    actions = PlaybookEngine.get_actions([{"name": "react", "risk": 0.20}])
    assert len(actions) >= 1
    assert actions[0]["tech"] == "react"
    assert actions[0]["action"] in ("check_api_authorization", "check_env_exposure")


def test_playbook_engine_spring_boot():
    actions = PlaybookEngine.get_actions([{"name": "Spring Boot", "risk": 0.85}])
    actions_by_name = {a["action"]: a for a in actions}
    assert "check_actuator" in actions_by_name
    assert "check_spel_injection" in actions_by_name
    assert all(a["tech"].lower() == "spring boot" for a in actions)


def test_playbook_engine_multiple_techs():
    actions = PlaybookEngine.get_actions(
        [
            {"name": "spring boot", "risk": 0.85},
            {"name": "graphql", "risk": 0.75},
        ]
    )
    actions_by_name = {a["action"]: a for a in actions}
    assert "check_actuator" in actions_by_name
    assert "check_introspection" in actions_by_name


def test_playbook_engine_sorted_by_risk():
    """Higher risk actions should come first."""
    actions = PlaybookEngine.get_actions(
        [
            {"name": "spring boot", "risk": 0.85},
            {"name": "react", "risk": 0.20},
        ]
    )
    risks = [a.get("risk", 0) for a in actions]
    assert risks == sorted(risks, reverse=True)


# ── DeepStudyResult ────────────────────────────────────────────────


def test_deep_study_result_defaults():
    result = DeepStudyResult(
        target_name="test",
        domain="test.com",
        score=7.5,
        endpoints_analyzed=10,
        technologies=[{"name": "nginx"}],
        hypotheses=[],
        playbook_actions=[],
        attack_surfaces=["api", "admin"],
        recommendations=["Check API"],
        summary="Test summary",
    )
    assert result.target_name == "test"
    assert result.domain == "test.com"
    assert result.score == 7.5
    assert result.endpoints_analyzed == 10
    assert result.technologies == [{"name": "nginx"}]
    assert result.attack_surfaces == ["api", "admin"]
    assert result.recommendations == ["Check API"]
    assert result.summary == "Test summary"
    assert result.raw == {}

    d = result.raw
    assert isinstance(d, dict)


def test_deep_study_result_not_found():
    result = DeepStudyResult(
        target_name="unknown",
        domain="",
        score=0.0,
        endpoints_analyzed=0,
        technologies=[],
        hypotheses=[],
        playbook_actions=[],
        attack_surfaces=[],
        recommendations=[],
        summary="Target not found",
    )
    assert result.score == 0.0
    assert result.summary == "Target not found"


# ── TECH_PLAYBOOKS registrations ───────────────────────────────────


def test_all_playbooks_have_required_fields():
    for tech_name, steps in TECH_PLAYBOOKS.items():
        for step in steps:
            assert "action" in step, f"{tech_name} playbook missing action"
            assert "description" in step, f"{tech_name} playbook missing description"
            assert "tool" in step, f"{tech_name} playbook missing tool"
            assert "risk" in step, f"{tech_name} playbook missing risk"
            assert isinstance(step["risk"], (int, float)), f"{tech_name} risk not numeric"
            assert 0 <= step["risk"] <= 1, f"{tech_name} risk out of range"


def test_deep_study_runner_creates_result():
    """Validate that DeepStudyEngine can be instantiated and creates a proper result shape."""
    from apps.aegis.engines.deep_study import DeepStudyEngine

    engine = DeepStudyEngine()
    assert engine is not None
    assert engine._httpx is None
    assert engine._copilot is None
