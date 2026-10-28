"""Guards del perfil de modelo de seguridad (skill `security-ai`).

Sellan tres cosas:
1. El routing elige el modelo con EVIDENCIA medida, no por opinión.
2. El perfil marca explícitamente que la IA NO es autoridad (advisory_only).
3. `pool_runs` no hace cherry-picking: reporta consenso Y disidencia.
"""

from __future__ import annotations

from cores.ai.security_profile import (
    MODEL_CHEAP,
    MODEL_DISCOVERY,
    MODEL_EVIDENCE,
    MODEL_OFFENSIVE,
    pool_runs,
    profile_for,
)

# ══════════════════════════════════════════════════════════════════
# 1. Routing con evidencia
# ══════════════════════════════════════════════════════════════════


def test_ejecucion_ofensiva_usa_el_benchmark_winner():
    p = profile_for("exploit")
    assert p.model == MODEL_OFFENSIVE
    assert p.evidence, "el modelo de ejecución debe traer evidencia medida"


def test_descubrimiento_usa_el_benchmark_winner_alcanzable():
    """Discovery usa el de mayor pass rate **entre los que responden**.

    El 98.5% de TrustedSec es de `gemma-4-31b-it`, que da HTTP 500 en Google
    (verificado en vivo): pinear ese número sobre otro modelo sería la misma
    clase de mentira que un contador en 0. El perfil tiene que declarar el
    pass rate del modelo que realmente elige.
    """
    p = profile_for("discovery")
    assert p.model == MODEL_DISCOVERY
    assert p.evidence["pass_rate"] == 0.920, "el pass rate debe ser el del modelo elegido"
    assert "736/800" in p.evidence["sample"]


def test_el_ganador_del_benchmark_inalcanzable_no_se_declara_como_elegido():
    """El ranking público no determina el perfil: lo determina qué responde.

    Si alguien "arregla" el perfil para volver al ganador de TrustedSec
    reintroduciría un modelo que devuelve HTTP 500 — el fallo silencioso que
    este módulo existe para evitar.
    """
    assert "gemma" not in MODEL_OFFENSIVE, "gemma-4-* da HTTP 500 en Google (medido)"
    assert "deepseek" not in MODEL_DISCOVERY, "deepseek-v4-pro no tiene provider con key (medido)"
    for task in ("exploit", "discovery"):
        why = profile_for(task).why.lower()
        assert "500" in why or "nemotron" in why or "groq" in why, f"{task}: el why debe decir quién responde"


def test_tarea_desconocida_cae_a_barato():
    assert profile_for("lo que sea").model == MODEL_CHEAP
    assert profile_for("").model == MODEL_CHEAP


def test_todo_modelo_seleccionado_tiene_evidencia():
    for task in ("exploit", "discovery", "review", "raro"):
        p = profile_for(task)
        assert p.evidence, f"{task} sin evidencia"
        assert p.evidence.get("evidence") == "measured"


# ══════════════════════════════════════════════════════════════════
# 2. La IA no es autoridad (spec §22/§56)
# ══════════════════════════════════════════════════════════════════


def test_perfil_siempre_es_advisory():
    for task in ("exploit", "discovery", "review"):
        p = profile_for(task)
        assert p.advisory_only is True
        assert p.require_tool_verification is True


def test_perfil_no_declara_verificacion_automatica():
    """El gap medido (0% multi-paso) obliga a verificación por herramienta."""
    for task in ("exploit", "discovery"):
        assert profile_for(task).require_tool_verification is True


def test_evidencia_declara_el_caveat_de_falsos_positivos():
    """El modelo barato tiene que declarar su riesgo de falsos positivos.

    Es el único guard que impide que un triage masivo se lea como veredicto:
    si el caveat se reescribe sin mencionar FP, el riesgo desaparece del
    payload que el usuario lee.
    """
    caveat = MODEL_EVIDENCE[MODEL_CHEAP].get("caveat", "").lower()
    assert "falso" in caveat, f"el caveat del modelo barato debe nombrar los falsos positivos: {caveat!r}"


# ══════════════════════════════════════════════════════════════════
# 3. Pooling honesto (sin cherry-picking)
# ══════════════════════════════════════════════════════════════════


def test_pool_sin_respuestas_es_no_data():
    out = pool_runs([None, "", "   "])
    assert out["verdict"] == "NO_DATA"
    assert out["runs"] == 0
    assert out["agreement"] is None


def test_pool_consenso_unanime():
    out = pool_runs(["IDOR en /api/users/1", "IDOR en /api/users/1", "IDOR en /api/users/1"])
    assert out["verdict"] == "CONSENSUS"
    assert out["agreement"] == 1.0
    assert out["unique_findings"] == 1


def test_pool_mayoritario_es_consenso():
    out = pool_runs(["A", "A", "B"])
    assert out["verdict"] == "CONSENSUS"
    assert out["consensus"] == "A"
    assert out["unique_findings"] == 2  # la disidencia NO se oculta


def test_pool_dividido_no_se_presenta_como_confirmado():
    out = pool_runs(["A", "B", "C"])
    assert out["verdict"] == "SPLIT"
    assert out["agreement"] < 0.5
    # Y debe decirlo explícitamente
    assert "NO" in out["note"]


def test_pool_recupera_alcance_que_una_pasada_perdio():
    """El motivo del pooling: 17/32 en una pasada, 28/32 en tres."""
    una = ["hallazgo A"] * 1
    tres = ["hallazgo A", "hallazgo B", "hallazgo C"]
    assert pool_runs(una)["unique_findings"] == 1
    assert pool_runs(tres)["unique_findings"] == 3


# ══════════════════════════════════════════════════════════════════
# Regresión 2026-09-30 (NVIDIA NIM integrado):
#  · NIM da la familia Nemotron, NO glm-5.3 ni deepseek-v4-pro. Esos
#    rutean a z-ai/deepseek, providers sin key. Verificado en vivo.
#  · Los reasoning models devuelven HTTP 200 con content:null si el
#    presupuesto no alcanza para terminar de pensar (GLM-5.3: 431 tokens
#    de razonamiento antes de 104 de respuesta). Fallo silencioso.
# ══════════════════════════════════════════════════════════════════


def test_nvidia_da_nemotron_no_glm_ni_deepseek():
    """La key de NVIDIA sirve Nemotron; glm/deepseek son otro provider."""
    from cores.ai.security_profile import MODEL_DISCOVERY, MODEL_LARGE

    assert "nemotron" in MODEL_DISCOVERY
    assert "nemotron" in MODEL_LARGE
    assert "glm" not in MODEL_DISCOVERY
    assert "deepseek" not in MODEL_DISCOVERY


def test_perfil_registra_el_provider_nvidia():
    assert profile_for("discovery").evidence["provider"].startswith("nvidia")


def test_reasoning_models_necesitan_presupuesto_de_tokens():
    """Un floor bajo = HTTP 200 con content null = falsoillusion."""
    from cores.ai.security_profile import REASONING_TOKEN_FLOOR

    assert REASONING_TOKEN_FLOOR >= 2000, "medido: 431 tokens de razonamiento mínimo"
    for task in ("exploit", "discovery", "review"):
        assert profile_for(task).min_max_tokens >= REASONING_TOKEN_FLOOR
