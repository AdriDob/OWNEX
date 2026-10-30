"""El "potencial de ingresos" del sistema era arithmetic sobre números inventados.

Hallazgo 2026-10-08, continuando el patrón de
`test_fake_source_discovery.py`. `GET /api/pillars/dashboard` emitía, con la
precisión de una medición:

    total_monthly_potential : "$5,000 - $39,000"
    combined_ev_per_hour    : "$222"

Los dos se derivaban de `monthly_potential_low/high` **escritos a mano** en
los 5 pillars. Y `GET /api/pillars/startup-plan` traía seis
`expected_income` inventados que suman ~$80-$310 en la semana 1.

Medido el mismo día: el revenue loop real tiene **0 acciones registradas**.
No había nada que proyectar. Un número proyectado sin base no es una
proyección: es una afirmación.

Distinción que estos tests fijan:

- **Hecho de mercado** (verificable en la página de la plataforma): se
  declara → `pay_range`, `platforms`, `barrier`.
- **Proyección** (depende de horas disponibles y tasa de aceptación real):
  `None` = UNKNOWN mientras no haya datos → `avg_pay_rate`,
  `monthly_potential_*`, `expected_income`.

Además, `RevenueLearningLoop.get_totals()` devolvía `0.0` de $/hora con 0
acciones, por el mismo `max(total, 1)` que ya se corrigió dos veces en el
feedback loop.
"""

from __future__ import annotations

import pytest

from cores.pillars.orchestrator import (
    FivePillarOrchestrator,
    _fmt_money_range,
    _measured_revenue_per_hour,
)


@pytest.fixture
def orch() -> FivePillarOrchestrator:
    return FivePillarOrchestrator()


# ══════════════════════════════════════════════════════════════════
# Los hechos de mercado se siguen declarando
# ══════════════════════════════════════════════════════════════════


def test_los_hechos_de_mercado_siguen_declarados(orch: FivePillarOrchestrator) -> None:
    """Pay range y plataformas son verificables: no se borran.

    Este test existe para que el fix no se convierta en "borrar el dato":
    lo que no tiene base seUNKNOWN, lo verificable se declara.
    """
    for p in orch.pillars:
        assert p.pay_range, f"{p.name}: el rango de pago es un hecho verificable"
        assert p.platforms, f"{p.name}: las plataformas son un hecho verificable"
        assert p.barrier, f"{p.name}: la barrera es un hecho verificable"


def test_el_rango_publicado_no_se_vende_como_promedio(orch: FivePillarOrchestrator) -> None:
    """`avg_pay_rate` era un promedio inventado (75.0, 50.0, 18.0, 13.0)."""
    for p in orch.pillars:
        assert p.avg_pay_rate is None, (
            f"{p.name}: volvió avg_pay_rate={p.avg_pay_rate}. Un 'promedio' sin "
            "fuente es inventado; si tenés la fuente, ponela en el pay_range con su fecha."
        )


# ══════════════════════════════════════════════════════════════════
# Las proyecciones son UNKNOWN, no ceros
# ══════════════════════════════════════════════════════════════════


def test_el_potencial_mensual_por_pillar_es_unknown(orch: FivePillarOrchestrator) -> None:
    for p in orch.pillars:
        assert p.monthly_potential_low is None, f"{p.name}: potencial bajo inventado"
        assert p.monthly_potential_high is None, f"{p.name}: potencial alto inventado"


def test_el_dashboard_no_advertiza_ingresos_sin_medir(orch: FivePillarOrchestrator) -> None:
    """El contrato: sin datos, los totales y el $/hora son `None`.

    Antes: `"$5,000 - $39,000"` y `"$222"`, calculados con dos decimales de
    precisión sobre cinco números escritos a mano.
    """
    d = orch.get_dashboard()
    assert d.total_monthly_low is None
    assert d.total_monthly_high is None
    assert d.combined_ev_per_hour is None
    assert d.next_best_pillar is None, (
        "next_best_pillar salió de un dict literal de prioridades. Rankear "
        "exige el payout POR pillar y RevenueLearningLoop no guarda esa dimensión."
    )

    payload = d.to_dict()
    assert payload["total_monthly_potential"] is None
    assert payload["total_monthly_potential_status"] == "UNKNOWN"
    assert "MEASURED" not in payload["combined_ev_per_hour_source"]


def test_el_total_mensual_exige_los_cinco_pillars(orch: FivePillarOrchestrator) -> None:
    """Un total con 3 de 5 pillars se lee como completo. No se calcula."""
    orch.pillars[0].monthly_potential_low = 1000
    orch.pillars[0].monthly_potential_high = 2000
    assert orch.get_dashboard().total_monthly_low is None, (
        "1 de 5 con proyección ⇒ el total es UNKNOWN, no la suma de los que sí"
    )

    for p in orch.pillars:
        p.monthly_potential_low = 1000
        p.monthly_potential_high = 2000
    d = orch.get_dashboard()
    assert d.total_monthly_low == 5000
    assert d.total_monthly_high == 10000


def test_el_startup_plan_no_proyecta_ingresos(orch: FivePillarOrchestrator) -> None:
    """Los 6 `expected_income` eran inventados: `"$0-30"`, `"$50-150"`, …"""
    plan = orch.get_startup_plan()
    dias = [k for k in plan if k.startswith("day")]
    assert len(dias) == 6, f"el plan cambió deshape: {dias}"
    for dia in dias:
        assert plan[dia]["expected_income"] is None, f"{dia}: volvió expected_income={plan[dia]['expected_income']!r}"
        assert plan[dia]["expected_income_note"], f"{dia}: el Unknown necesita motivo a la vista"
        assert plan[dia]["actions"], f"{dia}: las acciones SÍ son reales, no se borran"


def test_fmt_money_range_no_inventa_un_extremo() -> None:
    assert _fmt_money_range(1000, 2000) == "$1,000 - $2,000"
    assert _fmt_money_range(None, 2000) is None, "un rango sin un extremo no se completa"
    assert _fmt_money_range(1000, None) is None
    assert _fmt_money_range(None, None) is None


# ══════════════════════════════════════════════════════════════════
# El $/hora viene del revenue loop real
# ══════════════════════════════════════════════════════════════════


def test_el_dolar_por_hora_es_unknown_sin_acciones() -> None:
    """Medido 2026-10-08: `total_actions == 0` ⇒ sin tasa.

    Antes `combined_ev_per_hour` se derivaba de las proyecciones inventadas
    y daba `$222` sin un solo dato. Ahora sale del revenue loop.
    """
    rate = _measured_revenue_per_hour()
    from cores.learning.revenue_loop import get_revenue_loop

    if get_revenue_loop().get_totals()["total_actions"] == 0:
        assert rate is None, "sin acciones registradas no hay $/hora honesto"
    else:  # pragma: no cover — depende del estado del store
        assert rate is not None


def test_el_dashboard_toma_el_dolar_por_hora_del_revenue_loop(orch: FivePillarOrchestrator) -> None:
    """El número del dashboard y el del revenue loop no pueden divergir."""
    from cores.learning.revenue_loop import get_revenue_loop

    esperado = get_revenue_loop().get_totals()["avg_revenue_per_hour"]
    assert orch.get_dashboard().combined_ev_per_hour == esperado


# ══════════════════════════════════════════════════════════════════
# RevenueLearningLoop: tasas UNKNOWN sin minutos registrados
# ══════════════════════════════════════════════════════════════════


def test_las_tasas_del_revenue_loop_son_unknown_sin_minutos() -> None:
    """`max(total_minutes, 1)` devolvía 0.0 $/hora con cero acciones.

    Es la tercera vez que un denominador de relleno convierte "no lo sé" en
    un cero medido (feedback loop #69, `acceptance_rate`, y esto).
    """
    from cores.learning.revenue_loop import RevenueLearningLoop

    loop = RevenueLearningLoop()
    loop.actions = []
    loop.daily = {}
    t = loop.get_totals()
    assert t["total_actions"] == 0
    assert t["total_human_minutes"] == 0.0
    assert t["avg_revenue_per_hour"] is None, "0.0 $/hora sin acciones es un resultado inventado"
    assert t["avg_ev_per_hour"] is None
    assert t["ev_accuracy"] is None
    assert "UNKNOWN" in t["rates_status"]


def test_las_tasas_se_calculan_cuando_hay_datos() -> None:
    """Con minutos registrados, la tasa es aritmética real.

    Distinción que importa: acá `avg_revenue_per_hour` es **`0.0`, no
    `None`** — se trabajó 1 hora y se cobró $0. Esa es una medición verdadera
    con valor cero. `None` es para cuando no hubo medición. Confundir las dos
    es el bug que se corrigió, en dirección contraria.
    """
    from cores.learning.revenue_loop import RevenueLearningLoop

    loop = RevenueLearningLoop()
    loop.record_action(
        opportunity_id="o1",
        action_type="apply",
        title="a",
        description="",
        human_minutes=60.0,
        expected_value=50.0,
    )
    t = loop.get_totals()
    assert t["total_actions"] == 1
    assert t["avg_ev_per_hour"] == 50.0, "50 USD esperados en 1h"
    assert t["avg_revenue_per_hour"] == 0.0, "se registrar minutos sin payout: 0 es verdad"
    assert t["rates_status"] == "MEASURED"

    # Con payout, la tasa es real y distinta de cero.
    loop.record_result("action_1", actual_revenue=80.0, status="accepted", learning_tags=[])
    t2 = loop.get_totals()
    assert t2["avg_revenue_per_hour"] == 80.0
    assert t2["ev_accuracy"] == 1.6, "cobraste 80 sobre 50 esperado"
