"""Tests del SOURCE ADMISSION TEST (P0 del owner) + democión de Fiverr.

Sella:
- una fuente sólo entra si es trabajo técnico verificable (o se marca
  CONDITIONAL si el dato falta — nunca fail-closed de más, misma distinción
  que scope: "no sé" ≠ "sé que no");
- Fiverr es el generador de gigs propio de OWNEX, no un marketplace
  competidor: sale del núcleo pero NO se borra (es ingreso propio);
- el gate P0 corre ANTES del P1 y no lo desactiva.
"""

from __future__ import annotations

from types import SimpleNamespace

from cores.direct_work_engine.source_registry import (
    BARRIER_ASSESSMENT,
    BARRIER_CREDENTIALS,
    PAYOUT_NEGOTIATED,
    PAYOUT_UNKNOWN,
    RAIL_AR_NO,
    RAIL_AR_OK,
    SOURCE_ACTIVE,
    SOURCE_BLOCKED,
    SOURCE_CONDITIONAL,
    SOURCE_LOW_VALUE,
    admit_source,
    source_gate,
)


def _src(**kw):
    from cores.direct_work_engine.models import OpportunityCategory

    base = {
        "name": "X",
        "type": "platform",
        "category": OpportunityCategory.BUG_BOUNTY,
        "apply_method": "api",
        "estimated_payout_range": "$100-$500",
        "typical_hourly_rate_usd": 40.0,
        "requires_interview": False,
    }
    base.update(kw)
    return SimpleNamespace(**base)


# ══════════════════════════════════════════════════════════════════
# P0 — admisión
# ══════════════════════════════════════════════════════════════════


def test_fuente_tecnica_completa_queda_active():
    r = admit_source(_src())
    assert r.status == SOURCE_ACTIVE
    assert r.admitted is True


def test_marketplace_de_servicios_queda_blocked():
    """Un job board de servicios no es trabajo técnico verificable."""
    from cores.direct_work_engine.models import OpportunityCategory

    r = admit_source(_src(type="job_board", category=OpportunityCategory.EMPLOYMENT))
    assert r.status == SOURCE_BLOCKED
    assert r.admitted is False


def test_categoria_no_tecnica_queda_blocked():
    from cores.direct_work_engine.models import OpportunityCategory

    r = admit_source(_src(category=OpportunityCategory.EMPLOYMENT))
    assert r.status == SOURCE_BLOCKED


def test_datos_ausentes_es_conditional_no_blocked():
    """Fail-open de más sería bloquear por ignorancia. No sé ≠ sé que no."""
    r = admit_source(SimpleNamespace(name="sin datos"))
    assert r.status == SOURCE_CONDITIONAL
    assert r.admitted is True


def test_recompensa_no_documentada_es_conditional_con_requisito():
    """Una fuente que NO paga por resultado, sin cifra, exige verificación.

    Bounty/dev-bounty están excluidos a propósito: esas plataformas publican
    la tabla por programa, así que "sin cifra a nivel fuente" es
    `NEGOTIATED`, no `UNKNOWN` (ver `test_bounty_sin_cifra_es_negotiated`).
    """
    from cores.direct_work_engine.models import OpportunityCategory

    r = admit_source(
        _src(
            category=OpportunityCategory.AI_EVALUATION,
            estimated_payout_range="varies",
            typical_hourly_rate_usd=None,
        )
    )
    assert r.status == SOURCE_CONDITIONAL
    assert r.admitted is True
    assert "verificar" in r.reason


def test_bounty_sin_cifra_es_negotiated_no_unknown():
    """Bounty paga por hallazgo: la cifra va por programa, no por fuente.

    Antes estas ~166 fuentes caían en UNKNOWN ("paga pero sin cifra
    publicada") porque la rama que debía cubrirlas buscaba la palabra
    "bounty" en `type`, que nunca se llena (es platform/job_board/...).
    """
    r = admit_source(_src(estimated_payout_range="varies", typical_hourly_rate_usd=None))
    assert r.payout == PAYOUT_NEGOTIATED
    assert r.status == SOURCE_ACTIVE, "un bounty pagador no debe quedar CONDITIONAL"
    assert r.admitted is True


def test_pago_bajo_el_piso_es_low_value_pero_entra():
    r = admit_source(_src(typical_hourly_rate_usd=8.0))
    assert r.status == SOURCE_LOW_VALUE
    assert r.admitted is True  # entra, no prioriza


# ══════════════════════════════════════════════════════════════════
# Integración: P0 corre antes que P1 y no lo desactiva
# ══════════════════════════════════════════════════════════════════


def test_p0_falla_antes_que_p1():
    """Una plataforma de servicios no entra, aunque pase los gates P1."""
    from cores.direct_work_engine.models import OpportunityCategory

    ok, reason = source_gate(_src(type="job_board", category=OpportunityCategory.EMPLOYMENT))
    assert ok is False
    assert "técnico" in reason or "servicios" in reason or "verificables" in reason


def test_p1_sigue_aplicandose_tras_p0():
    ok, reason = source_gate(_src(requires_interview=True))
    assert ok is False and "entrevista" in reason


def test_p1_piso_de_pago_sigue_aplicandose():
    ok, reason = source_gate(_src(typical_hourly_rate_usd=5.0))
    assert ok is False and "piso" in reason


def test_fuente_limpia_pasa():
    ok, _ = source_gate(_src())
    assert ok is True


# ══════════════════════════════════════════════════════════════════
# Fiverr: carril secundario, NO borrado (es ingreso propio)
# ══════════════════════════════════════════════════════════════════


def test_fiverr_y_freelance_vetados_por_el_owner():
    """Todo el carril freelance queda fuera (decisión del owner, 2026-10-01).

    *"no quiero trabajar en fiverr ni en freelance"*. Se invierte la
    decisión del 2026-09-30 (fiverr ACTIVE y opcional): ahora es
    hard-excluded, o sea que **no admite override por HTTP** — un clic no
    puede devolver a la cola un carril que el dueño vetó. El motor de gigs
    sigue en el árbol (`cores/fiverr/`) por si el owner cambia de opinión.
    """
    from cores.freelance.channel_status import (
        _HARD_EXCLUDED,
        ChannelStatus,
        get_status,
    )

    assert get_status("fiverr") == ChannelStatus.EXCLUDED
    assert "fiverr" in _HARD_EXCLUDED, "un canal vetado no admite override"
    assert "freelance" in _HARD_EXCLUDED, "el carril freelance completo quedó fuera"
    # Workana ya estaba duro-excluido desde el purge 2026-09.
    assert get_status("workana") == ChannelStatus.EXCLUDED


# ══════════════════════════════════════════════════════════════════
# Regresión 2026-09-30: los DOS EJES no se vuelven a mezclar.
#
# El gate viejo usaba "payout documentado" como admisión, así que
# HackerOne/Bugcrowd/Intigriti/yeswehack (estimated_payout_range="varies")
# quedaban fuera del ranking: "no sé cuánto pagan" se trataba igual que
# "no podés entrar". Y `data_entry` no estaba en TECHNICAL_CATEGORIES, así
# que las 37 fuentes de AI training quedaban BLOCKED.
# ══════════════════════════════════════════════════════════════════


def test_payout_desconocido_no_bloquea_la_admision():
    """Payout es EJE B (ranking), no EJE A (admisión).

    Con una categoría que NO paga por resultado (AI evaluation), la falta de
    cifra es `UNKNOWN` real y exige verificación, pero nunca bloquea el
    acceso. Ver también `test_bounty_sin_cifra_es_negotiated_no_unknown`.
    """
    from cores.direct_work_engine.models import OpportunityCategory

    r = admit_source(
        _src(
            category=OpportunityCategory.AI_EVALUATION,
            estimated_payout_range="varies",
            typical_hourly_rate_usd=None,
        )
    )
    assert r.status != SOURCE_BLOCKED, "sin cifra no es una barrera de acceso"
    assert r.payout == PAYOUT_UNKNOWN
    assert r.admitted is True


def test_ai_training_y_data_entry_no_quedan_bloqueadas():
    """Las ramas de AI training del radar del owner deben entrar."""
    from cores.direct_work_engine.models import OpportunityCategory

    for cat in (OpportunityCategory.DATA_ANNOTATION, OpportunityCategory.AI_EVALUATION):
        r = admit_source(_src(category=cat, type="platform"))
        assert r.status != SOURCE_BLOCKED, f"{cat} quedó bloqueada"


def test_barrera_credentiales_va_por_separado():
    """CV / LinkedIn / años de oficio ⇒ CREDENTIALS (no entra al ranking 0 barrera)."""
    r = admit_source(_src(requires_experience=True))
    assert r.barrier == BARRIER_CREDENTIALS
    assert r.status == SOURCE_BLOCKED

    r2 = admit_source(_src(requires_interview=True))
    assert r2.barrier == BARRIER_CREDENTIALS


def test_assessment_permitido_es_distinto_de_entrevista():
    """El owner permite assessment/evaluation; la entrevista no."""
    a = admit_source(_src(requires_assessment=True))
    assert a.barrier == BARRIER_ASSESSMENT
    assert a.status != SOURCE_BLOCKED, "un assessment no debe sacar la fuente"
    assert a.zero_barrier is True


def test_rail_incompatible_con_argentina_no_se_prioriza():
    """0 barrera + rail Stripe = nunca cobrarías en Argentina (Stripe no cubre AR)."""
    ok = admit_source(_src(payout_rail="stripe", rail_pays_in_argentina="FALSE"))
    assert ok.rail_ar == RAIL_AR_NO
    # Sigue siendo admisible (la barrera no depende del rail), pero el dato
    # queda expuesto para que el ranking pueda descontarlo.
    assert ok.status != SOURCE_BLOCKED


def test_rail_compatible_con_argentina_se_marca():
    for rail in ("payoneer", "deel", "paypal", "wise"):
        assert admit_source(_src(payout_rail=rail)).rail_ar == RAIL_AR_OK, rail


def test_catalogo_real_esta_lleno_de_trabajo_0_barrera():
    """Regresión directa del bug: el radar debe tener volumen utilizable."""
    from cores.direct_work_engine.source_registry import _all_sources

    results = [admit_source(s) for s in _all_sources()]
    cero = sum(1 for r in results if r.zero_barrier)
    assert cero >= 150, f"sólo {cero} fuentes 0 barrera de {len(results)}"
    assert sum(1 for r in results if r.status == SOURCE_BLOCKED) <= 20
