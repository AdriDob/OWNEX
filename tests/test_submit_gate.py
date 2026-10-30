"""Tests Submit Gate — choke point pre-envío, offline salvo DB aislada de tests."""

from __future__ import annotations

import pytest

from cores.auto_submit.submit_gate import SubmitGateInput, submit_gate


def _inp(**kw) -> SubmitGateInput:
    base = {
        "scope": "in_scope",
        "vulnerability_type": "sqli",
        "measured_rate": None,
        "has_repro_text": True,
        "already_submitted": False,
    }
    base.update(kw)
    return SubmitGateInput(**base)


class TestPureGate:
    def test_happy_path_permite(self) -> None:
        r = submit_gate(_inp())
        assert r.allow_submit is True and r.parked_reason is None
        assert all(c.passed for c in r.checks) and len(r.checks) == 3

    def test_out_of_scope_bloquea(self) -> None:
        r = submit_gate(_inp(scope="out_of_scope"))
        assert r.allow_submit is False and r.parked_reason == "out_of_scope"

    def test_scope_unknown_bloquea_fail_closed(self) -> None:
        """Scope sin verificar NO es autorización (spec §1/§79).

        Antes pasaba con nota ("no inventa bloqueo"). Se invirtió porque
        enviar un reporte a un tercero sobre un target cuyo scope no se puede
        confirmar es exactamente el riesgo que el Human Gate debe evitar.
        """
        r = submit_gate(_inp(scope="unknown"))
        assert r.allow_submit is False
        assert r.parked_reason == "scope_not_verified"
        # El bloqueo dice qué hacer para desbloquearlo (no es un muro ciego)
        assert "ProgramScopePolicy" in r.checks[0].detail

    def test_ia_sin_tasa_medida_aparca(self) -> None:
        r = submit_gate(_inp(vulnerability_type="prompt_injection", measured_rate=None))
        assert r.allow_submit is False and r.parked_reason == "needs_measured_repro"

    def test_ia_tasa_baja_aparca(self) -> None:
        r = submit_gate(_inp(vulnerability_type="prompt_injection", measured_rate=0.3))
        assert r.allow_submit is False and r.parked_reason == "repro_below_threshold"

    def test_ia_tasa_50_pasa(self) -> None:
        r = submit_gate(_inp(vulnerability_type="prompt_injection", measured_rate=0.5))
        assert r.allow_submit is True

    def test_web_sin_texto_aparca(self) -> None:
        r = submit_gate(_inp(has_repro_text=False))
        assert r.allow_submit is False and r.parked_reason == "missing_repro_steps"

    def test_duplicado_aparca(self) -> None:
        r = submit_gate(_inp(already_submitted=True))
        assert r.allow_submit is False and r.parked_reason == "duplicate"

    def test_to_dict_shape(self) -> None:
        d = submit_gate(_inp()).to_dict()
        assert set(d) == {"allow_submit", "parked_reason", "checks"}
        assert all(set(c) == {"check", "passed", "detail"} for c in d["checks"])


@pytest.fixture(autouse=True)
def _scope_policy_gate_test():
    """Registra el scope del programa de los findings de estos tests.

    Sin policy, `_resolve_scope` devuelve UNKNOWN y el gate bloquea
    (fail-closed). Antes pasaba "por accidente" (fail-open), o sea estos tests
    nunca verificaron el scope que dicen verificar. Con la policy, verifican
    el camino real: scope in_scope + evidencia → pasa.
    """
    from cores.scope_enforcement import (
        AssetType,
        ProgramScopePolicy,
        ScopeRule,
        get_scope_enforcer,
    )

    get_scope_enforcer().register_policy(
        ProgramScopePolicy(
            program_id="hackerone",
            program_name="gate-test",
            platform="hackerone",
            rules=[
                ScopeRule(
                    asset_type=AssetType.DOMAIN,
                    pattern="gate-test.example.com",
                    is_in_scope=True,
                    description="dominio de test",
                )
            ],
        )
    )


def _make_finding(session, models, **kw):
    target = models.Target(name="hackerone_gate-test", domain="gate-test.example.com")
    session.add(target)
    session.commit()
    args = {
        "title": "t",
        "severity": "high",
        "status": "confirmed",
        "target_id": target.id,
        "vulnerability_type": "sqli",
        **kw,
    }
    f = models.Finding(**args)
    session.add(f)
    session.commit()
    return f


class TestAdapterDB:
    def test_web_con_texto_pasa(self) -> None:
        from cores.auto_submit.submit_gate import submit_gate_for_finding
        from database import db, models

        session = db.SessionLocal()
        try:
            f = _make_finding(session, models, description="Steps to reproduce: 1. open login " + "x" * 120)
            fid = f.id
        finally:
            session.close()
        r = submit_gate_for_finding(fid)
        assert r.allow_submit is True

    def test_ia_sin_medicion_aparca(self) -> None:
        from cores.auto_submit.submit_gate import submit_gate_for_finding
        from database import db, models

        session = db.SessionLocal()
        try:
            f = _make_finding(
                session, models, vulnerability_type="prompt_injection", description="Steps to reproduce: " + "y" * 120
            )
            fid = f.id
        finally:
            session.close()
        r = submit_gate_for_finding(fid)
        assert r.allow_submit is False and r.parked_reason == "needs_measured_repro"

    def test_ia_con_tasa_medida_pasa(self) -> None:
        from cores.auto_submit.submit_gate import submit_gate_for_finding
        from database import db, models

        session = db.SessionLocal()
        try:
            f = _make_finding(
                session, models, vulnerability_type="prompt_injection", description="Steps to reproduce: " + "z" * 120
            )
            fid = f.id
        finally:
            session.close()
        r = submit_gate_for_finding(fid, measured_rate=0.8)
        assert r.allow_submit is True

    def test_finding_inexistente_fail_closed(self) -> None:
        from cores.auto_submit.submit_gate import submit_gate_for_finding

        r = submit_gate_for_finding(999999999)
        assert r.allow_submit is False and r.parked_reason == "finding_not_found"


class TestReviewQueueAnnotation:
    def test_finding_lleva_factor_submit_gate(self) -> None:
        from cores.review_queue import build_review_queue
        from database import db, models

        session = db.SessionLocal()
        try:
            f = _make_finding(
                session, models, vulnerability_type="sqli", description="Steps to reproduce: " + "w" * 120
            )
            fid = int(f.id)
        finally:
            session.close()
        queue = build_review_queue(limit=100)
        items = [
            i
            for i in queue.high_confidence + queue.medium_confidence + queue.low_confidence
            if i.item_id == f"finding_{fid}"
        ]
        assert items, "el finding high debe aparecer en la cola"
        gate_factors = [x for x in items[0].factors if x["name"] == "submit_gate"]
        assert gate_factors, "falta el factor submit_gate"
        assert gate_factors[0]["value"] in ("ready",) or str(gate_factors[0]["value"]).startswith("parked:")

    def test_cola_sigue_viva_si_gate_falla(self) -> None:
        from unittest.mock import patch

        from cores.review_queue import build_review_queue

        with patch("cores.auto_submit.submit_gate.submit_gate_for_finding", side_effect=RuntimeError("db down")):
            queue = build_review_queue(limit=10)
            assert queue.total_items >= 0
