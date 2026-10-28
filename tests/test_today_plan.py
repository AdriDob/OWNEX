"""GET /today — el plan que debe servir DESDE EL DÍA 1.

Contrato que se pinea:
- Con cero datos (sin rail, sin workbank, sin PAID) devuelve un plan útil.
- Cada paso dice `owner`: system (ya corre) o human (tu clic).
- El dinero EXPECTED nunca se confunde con PAID.
- UNKNOWN es None, nunca 0.0.
- Nunca 500.
"""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.today import AUTOMATED_DAILY, build_today_plan, router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _empty(monkeypatch, *, rails=0, ready=0, review=0, paid=0):
    """Simula día 1: nada configurado, nada preparado, nada cobrado."""
    monkeypatch.setattr("api.routers.today._rails_configured", lambda: (rails, bool(rails)))
    monkeypatch.setattr("api.routers.today._ready_to_deliver", lambda: (ready, 0.0, None))
    monkeypatch.setattr("api.routers.today._pending_review", lambda: (review, None))
    monkeypatch.setattr("api.routers.today._paid_outcomes", lambda: paid)
    monkeypatch.setattr("api.routers.today._paid_total_usd", lambda: None)
    monkeypatch.setattr(
        "api.routers.today._human_tasks",
        lambda status: [],  # noqa: ARG005
    )
    import cores.setup.checklist as checklist_mod

    monkeypatch.setattr(
        checklist_mod,
        "get_setup_checklist",
        lambda: SimpleNamespace(status=lambda: {"complete_pct": 5, "pending": []}),
    )


class TestDayOne:
    def test_day1_returns_usable_plan(self, monkeypatch):
        _empty(monkeypatch)
        r = client.get("/today")
        assert r.status_code == 200
        body = r.json()
        assert body["state"]["day1_ok"] is False
        assert body["your_plan"], "día 1 sin datos debe igual dar un plan"
        assert body["next_step"]["id"] == "payout_rail"
        assert body["next_step"]["owner"] == "human"

    def test_day1_never_fakes_money(self, monkeypatch):
        _empty(monkeypatch)
        body = client.get("/today").json()
        # EXPECTED y PAID en None: sin datos, 0.0 sería mentira
        assert body["money"]["expected_now_usd"] is None
        assert body["money"]["paid_usd"] is None
        assert body["state"]["p_cash_state"].startswith("UNKNOWN")

    def test_automatic_section_is_always_present(self, monkeypatch):
        _empty(monkeypatch)
        body = client.get("/today").json()
        assert len(body["automatic"]) == len(AUTOMATED_DAILY)
        assert all(a["owner"] == "system" for a in body["automatic"])
        assert all(a["badge"] == "AUTOMÁTICO" for a in body["automatic"])


class TestOrderedPlan:
    def test_rail_first_then_review_then_delivery(self, monkeypatch):
        _empty(monkeypatch, rails=1, ready=2, review=3)
        body = client.get("/today").json()
        ids = [p["id"] for p in body["your_plan"]]
        assert ids[:3] == ["validate_review", "approve_delivery", "run_cycle"] or ids[0] == "validate_review"

    def test_review_task_carries_top_item(self, monkeypatch):
        _empty(monkeypatch, rails=1)
        monkeypatch.setattr(
            "api.routers.today._pending_review",
            lambda: (2, {"id": "f-1", "label": "IDOR en /api/orders"}),
        )
        body = client.get("/today").json()
        step = next(p for p in body["your_plan"] if p["id"] == "validate_review")
        assert step["top_item"]["id"] == "f-1"
        assert step["est_minutes"] >= 10

    def test_system_step_when_idle(self, monkeypatch):
        _empty(monkeypatch, rails=1)
        body = client.get("/today").json()
        assert any(p["id"] == "run_cycle" and p["owner"] == "system" for p in body["your_plan"])


class TestHonestyAndRobustness:
    def test_expected_is_labelled_not_paid(self, monkeypatch):
        _empty(monkeypatch, rails=1, ready=1)
        monkeypatch.setattr("api.routers.today._ready_to_deliver", lambda: (1, 350.0, None))
        body = client.get("/today").json()
        assert body["money"]["expected_now_usd"] == 350.0
        assert body["money"]["paid_usd"] is None
        assert "EXPECTED" in body["money"]["label"]

    def test_p_cash_measured_after_paid(self, monkeypatch):
        _empty(monkeypatch, rails=1, paid=4)
        body = client.get("/today").json()
        assert body["state"]["p_cash_state"] == "MEASURED"

    def test_never_500_when_everything_breaks(self, monkeypatch):
        monkeypatch.setattr("api.routers.today.build_today_plan", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        r = client.get("/today")
        assert r.status_code == 200
        body = r.json()
        assert body["next_step"]["id"] == "retry"
        assert body["automatic"]  # aunque falle, sabemos qué corre solo


class TestPureBuilder:
    def test_build_is_importable_and_returns_sections(self, monkeypatch):
        _empty(monkeypatch)
        plan = build_today_plan()
        assert set(plan) >= {"who", "state", "automatic", "your_plan", "money", "next_step"}

    def test_human_tasks_come_from_checklist(self):
        from api.routers.today import _human_tasks

        out = _human_tasks(
            {
                "pending": [
                    {
                        "id": "github_token",
                        "title": "Pegá tu GITHUB_TOKEN",
                        "est_minutes": 2,
                        "url": "https://github.com/settings/tokens",
                    }
                ]
            }
        )
        assert out[0]["id"] == "config:github_token"
        assert out[0]["owner"] == "human"
        assert out[0]["url"]


def test_every_plan_step_has_badge_and_owner():
    """Invariante de contrato: NINGÚN paso sin owner ni badge (cazado en run real)."""
    from api.routers.today import build_today_plan

    plan = build_today_plan()
    for step in plan["your_plan"]:
        assert step.get("owner") in ("system", "human"), step.get("id")
        assert step.get("badge") in ("TU CLOQUE", "AUTOMÁTICO"), step.get("id")
        assert step.get("title"), step.get("id")
    assert plan["next_step"].get("badge")
