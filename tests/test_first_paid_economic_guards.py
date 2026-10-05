"""Guards de honestidad económica + FIRST PAID (spec §13-§36).

Un único archivo que sella las reglas que no pueden romperse sin que el
sistema mienta sobre el dinero:

1. PAID es el ÚNICO estado que genera REALIZED_CASH (ACCEPTED/AWARDED/
   SUBMITTED/EXPECTED/PROJECTED no son cash).
2. 0 PAID ⇒ P(CASH), $/hora y calibración siguen UNKNOWN (nunca 0.0).
3. Los escenarios siguen siendo PLANNING_SCENARIO / is_forecast=false, y su
   base es auditable con el estado de evidencia de cada variable.
4. Los fixtures no pueden contaminar las métricas económicas.
5. El banco de entregables no contiene *programas* de bug bounty.
6. Trading sigue PAPER / NO_EDGE / sin capital live.
7. El adaptador de GitHub falla cerrado sin token.

Nada de esto calcula escenarios nuevos ni inventa probabilidades: sella lo que
ya existe.
"""

from __future__ import annotations

import pytest

from cores.direct_work_engine.workbank import (
    _BUG_BOUNTY_PLATFORMS,
    WorkBank,
    WorkItem,
)
from cores.economic_trajectory.trajectory import (
    PLANNING_SCENARIOS,
    REAL_CASH_STATES,
    SPECULATIVE_STATES,
    VERIFIABLE_PENDING_STATES,
    calibrate_scenarios,
    calibration_level,
    scenarios_block,
)

# ══════════════════════════════════════════════════════════════════
# 1-2. PAID es el único cash; 0 PAID ⇒ UNKNOWN
# ══════════════════════════════════════════════════════════════════


def test_paid_es_el_unico_cash():
    assert REAL_CASH_STATES == frozenset({"paid", "net"})


def test_aceptado_awardado_submitted_esperado_no_son_cash():
    for state in ("accepted", "awarded", "submitted", "expected", "projected"):
        assert state not in REAL_CASH_STATES
    # Verificables-pero-no-cash y especulativos tampoco entran al cash
    assert not (VERIFIABLE_PENDING_STATES & REAL_CASH_STATES)
    assert not (SPECULATIVE_STATES & REAL_CASH_STATES)


def test_cero_paid_deja_pcash_y_por_hora_unknown():
    calib = calibration_level(0)
    assert calib["level"] == 0
    assert calib["label"] == "NO_DATA"
    # None, NO 0.0 — "0 cash / 0 horas" no es una tasa observada
    assert calib["net_cash_per_hour"] is None


def test_un_paid_es_evidencia_inicial_pero_no_calibrado():
    assert calibration_level(1)["level"] >= 1
    assert calibration_level(1)["label"] != "NO_DATA"


# ══════════════════════════════════════════════════════════════════
# 3. Escenarios: preservados + base auditable
# ══════════════════════════════════════════════════════════════════


def test_escenarios_siguen_siendo_planning_no_forecast():
    s = scenarios_block()
    assert s["label"] == "PLANNING_SCENARIO"
    assert s["is_forecast"] is False
    assert s["kind"] == "scenario"
    # Los valores NO se tocan en esta fase
    assert s["horizons"] == {t: {h: list(v) for h, v in bands.items()} for t, bands in PLANNING_SCENARIOS.items()}
    for item in s["long_term"]:
        assert item["label"] == "LONG_TERM_SCENARIO"


def test_base_auditable_deja_unknown_sin_evidencia():
    basis = scenarios_block()["basis"]
    # Sin argumentos => nada observado: todo UNKNOWN, jamás un invento
    assert basis["formula"] is None
    assert basis["calibration"]["evidence"] == "UNKNOWN"
    assert basis["calibration"]["recalibrated"] is False
    assert basis["calibration"]["recalibration_requires_months"] == 3
    for name in ("p_cash", "acceptance_rate", "time_to_cash", "repeatability", "net_cash_per_human_hour"):
        var = basis["variables"][name]
        assert var["value"] is None, name
        assert var["evidence"] == "UNKNOWN", name
        assert var["requires"], name  # dice qué evidencia falta


def test_base_marca_los_estados_que_no_son_caja():
    basis = scenarios_block()["basis"]
    excl = basis["excluded_from_cash"]
    assert set(excl["speculative"]) == {"potential", "expected"}
    assert set(excl["verifiable_pending"]) == {"submitted", "accepted", "awarded"}
    assert not (set(excl["speculative"]) | set(excl["verifiable_pending"])) & REAL_CASH_STATES


def test_capacidad_observada_cuando_se_pasa():
    basis = scenarios_block(None, available_hours_per_week=77.0)["basis"]
    cap = basis["variables"]["capacity_weekly_hours"]
    assert cap["value"] == 77.0
    assert cap["evidence"] == "OBSERVED"
    # p_cash sigue UNKNOWN aunque haya capacidad
    assert basis["variables"]["p_cash"]["evidence"] == "UNKNOWN"


def test_calibrate_no_recalibra_sin_meses_reales():
    out = calibrate_scenarios(measured_monthly=5000.0, samples=1)
    assert out["calibrated"] is False
    assert "3 meses" in out["reason"]


# ══════════════════════════════════════════════════════════════════
# 4. Fixtures fuera de las métricas económicas
# ══════════════════════════════════════════════════════════════════


def _item(**kw) -> WorkItem:
    base = {
        "id": "x",
        "title": "t",
        "platform": "github",
        "category": "dev_bounty",
        "reward": 100.0,
        "barrier_score": 90.0,
        "employment_type": "bounty",
        "url": "https://github.com/acme/repo/issues/1",
    }
    base.update(kw)
    return WorkItem(**base)


def test_fixtures_excluidos_del_banco_real(tmp_path):
    from cores.direct_work_engine.workbank import fixture_item_ids

    bank = WorkBank(store_path=tmp_path / "wb.json")
    bank._items["real-1"] = _item(id="real-1")
    bank._items["bounty-1"] = _item(id="bounty-1", url="https://x.example/program/1")
    fixtures = fixture_item_ids(bank._items)
    assert "bounty-1" in fixtures
    assert "real-1" not in fixtures
    # best_ready (lo que alimenta el ranking económico) excluye fixtures
    assert all(i.id != "bounty-1" for i in bank.best_ready())


# ══════════════════════════════════════════════════════════════════
# 5. El banco de entregables no contiene programas de bug bounty
# ══════════════════════════════════════════════════════════════════


def test_programas_de_bug_bounty_no_son_tareas_entregables():
    # Un programa (con max bounty publicado) no se "entrega": se elige una
    # vulnerabilidad dentro y se reporta. No va al banco de entregables.
    assert {"hackerone", "bugcrowd", "intigriti", "yeswehack"} <= _BUG_BOUNTY_PLATFORMS
    # Y el acceso real de esos platforms sigue siendo needs_api_key (honesto),
    # no el "public" que forzaba el override eliminado.
    from cores.direct_work_engine.workbank import PLATFORM_ACCESS

    for p in ("hackerone", "bugcrowd", "intigriti", "yeswehack"):
        assert PLATFORM_ACCESS[p][0] == "needs_api_key", p
        assert not hasattr(
            __import__("cores.direct_work_engine.workbank", fromlist=["x"]),
            "_PLATFORM_ACCESS_OVERRIDE",
        ), "el override que mintió 'public' no debe volver"


def test_purga_programas_no_toca_delivered(tmp_path):
    bank = WorkBank(store_path=tmp_path / "wb.json")
    bank._items["prog"] = _item(id="prog", platform="hackerone", status="ready_to_deliver", url="https://x/p")
    bank._items["done"] = _item(id="done", platform="hackerone", status="delivered", url="https://x/d")
    bank._items["keep"] = _item(id="keep", platform="github")
    purged = bank.purge_bug_bounty_programs()
    assert purged == ["prog"]
    assert set(bank._items) == {"done", "keep"}


def test_ready_refleja_workbank_real_no_cero_fijo(tmp_path):
    """Regresión del bug P0: los contadores deben salir de `_summary()`,
    no de claves inexistentes (que devolvían 0/0 con 12 items reales).

    `_summary()` cuenta el booleano `ready_to_deliver` (el ciclo setea status Y
    booleano, workbank.py:379-380), igual que hace `best_ready()`.
    """
    bank = WorkBank(store_path=tmp_path / "wb.json")
    bank._items["a"] = _item(id="a", status="ready_to_deliver", ready_to_deliver=True)
    bank._items["b"] = _item(id="b", status="needs_access")
    bank._items["c"] = _item(id="c", status="delivered")
    s = bank._summary()
    assert s["ready_to_deliver"] == 1
    assert s["needs_access"] == 1
    assert s["delivered"] == 1
    assert s["total_in_bank"] == 3


# ══════════════════════════════════════════════════════════════════
# 6. Trading: PAPER / NO_EDGE / sin capital live (intocable)
# ══════════════════════════════════════════════════════════════════


def test_trading_verdict_sigue_no_edge_sin_tocar_el_criterio():
    """Sella el criterio de edge tal cual está (spec §21: no se modifica).

    El umbral vive como literal en `memecoin_paper._paper_verdict`: n>=20 y
    profit_factor>1.2. Este test falla si alguien lo ablanda para que un
    resultado mediocre se reporte como EDGE_CANDIDATE.
    """
    import inspect

    from cores.trading.paper import memecoin_paper

    src = inspect.getsource(memecoin_paper)
    assert "if n >= 20 and gross_loss > 0 and gross_win / gross_loss > 1.2:" in src, (
        "el criterio de edge (n>=20, PF>1.2) no debe modificarse en esta fase"
    )


def test_trading_paper_no_tiene_capital_live():
    from cores.trading.config import TradingConfig

    cfg = TradingConfig()
    assert getattr(cfg, "dry_run", True) is True


# ══════════════════════════════════════════════════════════════════
# 7. GitHub: fail-closed sin token
# ══════════════════════════════════════════════════════════════════


class _Prepared:
    metadata = {"opportunity": {"url": "https://github.com/acme/repo/issues/7"}}
    files = {"f.py": "x"}


@pytest.fixture(autouse=True)
def _sin_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)


@pytest.mark.asyncio
async def test_github_sin_token_falla_cerrado():
    from cores.opportunity.executors.auto_submit import GitHubBountyAdapter

    r = await GitHubBountyAdapter().submit_work(_Prepared(), api_key="")
    assert r["success"] is False
    assert r["state"] == "needs_access"
    assert r["attempted_external_action"] is False
    assert r["human_gate"] == "required_before_send"


def test_github_esta_cableado_en_auto_submit():
    from cores.opportunity.executors.auto_submit import AutoSubmitEngine

    e = AutoSubmitEngine()
    assert e._get_adapter("github").provider_id == "github"
    assert e._get_adapter("github_bounty").provider_id == "github"
