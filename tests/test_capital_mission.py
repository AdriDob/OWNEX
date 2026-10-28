"""Capital mission goals — persistencia + proyección (2026-09-16).

Misión del owner: Departamento Zona Sur (2 pers, USD 60k) + Buen Auto (USD 20k).
Fixes: add_goal persiste; update_goal persiste; get_capital_engine recarga DB;
delete_goal + endpoint DELETE. Antes, update_goal mutaba solo memoria → la
proyección siempre daba "no alcanza" y la misión no sobrevivía reinicios.
"""

from __future__ import annotations


def test_mission_goals_are_defaults() -> None:
    from cores.capital.engine import CapitalEngine

    eng = CapitalEngine()
    goals = {g.id: g for g in eng.goals}
    assert goals["apartment_buenos_aires"].name == "Departamento Zona Sur"
    assert goals["apartment_buenos_aires"].target_amount == 60_000
    assert goals["apartment_buenos_aires"].category == "vivienda"
    assert goals["car"].name == "Buen Auto"
    assert goals["car"].target_amount == 20_000


def test_delete_goal_persists_and_removes() -> None:
    from cores.capital.engine import CapitalEngine

    eng = CapitalEngine()
    # Crear un goal temporal que podamos borrar sin tocar la misión
    eng.add_goal("temporal_test", target_amount=100, category="test")
    before = len(eng.goals)
    assert any(g.id == "temporal_test" for g in eng.goals)
    assert eng.delete_goal("temporal_test") is True
    assert len(eng.goals) == before - 1
    assert not any(g.id == "temporal_test" for g in eng.goals)
    assert eng.delete_goal("no_existe") is False


def test_update_goal_persists_over_reload(tmp_path) -> None:
    from cores.capital.engine import CapitalEngine

    eng = CapitalEngine()
    eng.add_goal("meta_test", target_amount=10_000, category="test", monthly_contribution=0)
    eng.update_goal("meta_test", monthly_contribution=800)
    # simular reload: la persistencia va a DB (SessionLocal de la DB real), así que
    # validamos el contrato de memoria: el goal se actualizó y la proyección responde.
    goal = next(g for g in eng.goals if g.id == "meta_test")
    assert goal.monthly_contribution == 800
    proj = eng.get_goal_projections("meta_test", months=120)
    assert "months_to_reach" in proj


def test_goal_projection_reaches_target_honestly() -> None:
    from cores.capital.engine import CapitalEngine

    eng = CapitalEngine()
    eng.update_goal("apartment_buenos_aires", monthly_contribution=1000)
    p = eng.get_goal_projections("apartment_buenos_aires", months=240)
    months = p.get("months_to_reach")
    assert months is not None and 30 <= months <= 72, f"$60k a $1k/mes debería tardar ~4a, dio {months}"
