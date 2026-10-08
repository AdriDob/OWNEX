"""
La discovery automática devuelve datos FICTICIOS — cerrado.

Hallazgo 2026-10-05. Las 7 "fuentes" de
`cores/financial_intelligence/infinite_source_discovery.py` (LinkedIn, Indeed,
RemoteOK, WeWorkRemotely, FlexJobs, GitHub, Fiverr) **no hacen ninguna
llamada de red**: `discover_sources()` devuelve listas escritas a mano con
URLs inventadas (`linkedin.com/jobs/view/123`, `fiverr.com/gig/123`) y rates
inventados. Se los bardea como "oportunidades zero-barrier".

Eso es la misma clase de mentira que el proyecto ya pagó dos veces (pipeline
de $5.810 sin pago real; `UNKNOWN` renderizado como `$0`), y era exactamente
la feature que el owner pedía — "más fuentes sin experiencia ni entrevista".

Estos tests fijan que la puerta no se reabra por descuido.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MODULE = Path("cores/financial_intelligence/infinite_source_discovery.py")


@pytest.fixture(scope="module")
def client():
    from api.main import app

    return TestClient(app)


def test_ninguna_fuente_hace_llamada_de_red():
    """Si algún día hay red real, este test obliga a revisarlo a propósito."""
    src = MODULE.read_text(encoding="utf-8")
    for name in re.findall(r"def (_search_\w+)", src):
        block = src[src.index(f"def {name}") : src.index(f"def {name}") + 3000]
        simulated = "simulated_jobs" in block or "Simulated results" in block
        real = bool(re.search(r"httpx|requests\.get|res\.json|resp\.json", block))
        assert simulated and not real, (
            f"{name}: cambió la forma (simulated={simulated}, red={real}). "
            "Si pasó a ser real, sacá el `410` del endpoint y actualizá este test."
        )


def test_discover_responde_410_con_el_motivo(client):
    """410 y no 5xx: el handler oculta el detail de todo 5xx (política correcta)."""
    tok = client.post("/api/auth/login", json={"username": "infinite_probe", "password": "probe-12345"})
    if tok.status_code != 200:
        tok = client.post("/api/auth/register", json={"username": "infinite_probe", "password": "probe-12345"})
    token = tok.json().get("data", {}).get("token")
    if not token:
        pytest.skip("no se pudo autenticar")
    client.get("/api/system/status", headers={"Authorization": f"Bearer {token}"})
    h = {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": client.cookies.get("csrf-token", ""),
    }

    r = client.post("/api/infinite-sources/discover", json={}, headers=h)
    assert r.status_code == 410, "la discovery simulada no debe volver a servirse"
    detail = r.json().get("detail", "")
    assert "simulad" in detail.lower(), f"el motivo debe explicar el porqué: {detail!r}"


def test_ultra_fast_no_fabrica_oportunidades(client):
    """`generate_plan()` sin datos reales falla en vez de inventar trabajo."""
    from cores.financial_intelligence.ultra_fast_income import get_ultra_fast_income_engine

    engine = get_ultra_fast_income_engine()
    with pytest.raises(ValueError, match="oportunidades reales"):
        engine.generate_plan(None)


def test_http_exception_conserva_su_detalle(client):
    """Regresión del middleware: `except Exception` degradaba los 4xx a 500.

    Sin el `except HTTPException: raise`, todo mensaje deliberado de los
    routers (404 "no encontrado", 410 "retirado") llegaba al usuario como
    "Internal server error".
    """
    tok = (
        client.post("/api/auth/login", json={"username": "infinite_probe", "password": "probe-12345"})
        .json()
        .get("data", {})
        .get("token")
    )
    if not tok:
        pytest.skip("no se pudo autenticar")
    r = client.get("/api/does-not-exist-xyz", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404
    assert r.json().get("detail") == "Not Found", "el detail de un 4xx no puede genéricizarse"


# ══════════════════════════════════════════════════════════════════
# `acceptance_rate: 0.0` con 960 registros SIN clasificar
# ══════════════════════════════════════════════════════════════════


def test_acceptance_rate_es_unknown_sin_outcomes_clasificados():
    """Con 0 clasificados la tasa es UNKNOWN (None), no 0.0.

    Medido 2026-10-08: el resumen reportaba `acceptance_rate: 0.0`
    sobre 960 registros cuyo outcome es `"unknown"`. Leído por el owner
    eso dice "rechazaste el 100%" cuando en realidad nadie evaluó nada.
    Es KNOWN_DEBT #34 (UNKNOWN renderizado como 0) en otro endpoint.
    """
    from cores.opportunity.feedback import FeedbackLoop

    loop = FeedbackLoop()
    loop.get_feedback_history = lambda **kw: [  # type: ignore[method-assign]
        {"outcome": "unknown", "category": "c", "platform": "p"},
        {"outcome": "unknown", "category": "c", "platform": "p"},
    ]
    s = loop.get_feedback_summary()
    assert s["total_feedback"] == 2
    assert s["classified"] == 0
    assert s["acceptance_rate"] is None, "sin outcomes clasificados la tasa es UNKNOWN"
    assert "0/0" in s["acceptance_rate_basis"]


def test_acceptance_rate_real_cuando_hay_clasificados():
    from cores.opportunity.feedback import FeedbackLoop

    loop = FeedbackLoop()
    loop.get_feedback_history = lambda **kw: [  # type: ignore[method-assign]
        {"outcome": "accepted", "category": "c", "platform": "p"},
        {"outcome": "rejected", "category": "c", "platform": "p"},
    ]
    s = loop.get_feedback_summary()
    assert s["acceptance_rate"] == 0.5
    assert s["classified"] == 2


def test_los_fixtures_de_test_no_cuentan_como_aprendizaje():
    """960 registros `test-*` no son 960 resultados: no aprendió nada.

    Medido 2026-10-08: los 960 registros del store tienen TODOS clave
    `test-opp-N`, y el resumen reportaba `acceptance_rate: 0.667` — una
    tasa de aceptación compuesta enteramente por datos de prueba. Sin
    este filtro, el sistema afirma aprender de trabajo que nunca hizo.
    """
    from cores.opportunity.feedback import FeedbackLoop

    loop = FeedbackLoop()
    loop.get_feedback_history = lambda **kw: [  # type: ignore[method-assign]
        {"outcome": "accepted", "category": "web3", "_store_key": "test-opp-1"},
        {"outcome": "accepted", "category": "web3", "_store_key": "test-opp-2"},
        {"outcome": "rejected", "category": "platform", "_store_key": "test-opp-3"},
        {"outcome": "rejected", "category": "platform", "_store_key": "algo-real-1"},
    ]
    s = loop.get_feedback_summary()
    assert s["total_feedback"] == 1, "sólo el registro real cuenta"
    assert s["excluded_fixtures"] == 3, "los 3 fixtures se declaran aparte"
    assert s["acceptance_rate"] == 0.0, "1 real rechazado ⇒ 0.0 es un dato verdadero"


def test_fixture_no_es_aprendizaje_pero_sigue_visible():
    """El dato real no se pierde: UNKNOWN con el conteo de fixtures a la vista."""
    from cores.opportunity.feedback import FeedbackLoop

    loop = FeedbackLoop()
    loop.get_feedback_history = lambda **kw: [  # type: ignore[method-assign]
        {"outcome": "accepted", "_store_key": "test-opp-1"},
    ]
    s = loop.get_feedback_summary()
    assert s["acceptance_rate"] is None, "sin feedback real la tasa es UNKNOWN"
    assert s["excluded_fixtures"] == 1, "y se dice cuántos se descartaron y por qué"


# ══════════════════════════════════════════════════════════════════
# auto-apply: 2 plataformas "postulaban" sin enviar nada
# ══════════════════════════════════════════════════════════════════


def test_auto_apply_no_afirma_un_envio_que_no_ocurrio():
    """`_apply_indeed`/`_apply_fiverr` devolvían SUBMITTED sin enviar nada.

    Medido 2026-10-08: ambas hacían `time.sleep(...)` y retornaban
    `ApplyStatus.SUBMITTED` con `submitted_at` puesto, sin contactar a
    ninguna API. El registro se leía como una postulación real.
    Misma clase de mentira que `infinite-sources`.
    """
    from cores.financial_intelligence.auto_apply import ApplyStatus, AutoApplySystem

    s = AutoApplySystem()
    for platform in ("_apply_indeed", "_apply_fiverr"):
        rec = getattr(s, platform)({"id": "x", "title": "Job"})
        assert rec.status is ApplyStatus.MANUAL_REQUIRED, f"{platform} debe pedir acción manual"
        assert rec.submitted_at is None, f"{platform} no puede poner fecha de envío"
        assert "no implementado" in (rec.error_message or "").lower()


def test_auto_apply_no_tiene_fiverr_por_default():
    """Veto del owner (2026-08-08): *"no quiero trabajar en fiverr ni en freelance"*.

    Fiverr seguía en `enabled_platforms` por default, o sea que el veto no
    estaba aplicado donde importa: en la lista desde la que se postula.
    Upwork ya se había purgeado el 2026-09-13; faltaba Fiverr.
    """
    from cores.financial_intelligence.auto_apply import AutoApplyConfig

    platforms = AutoApplyConfig().enabled_platforms
    assert "fiverr" not in platforms
    for vetoed in ("upwork", "workana", "freelancer"):
        assert vetoed not in platforms, f"{vetoed} también está vetado"


# ══════════════════════════════════════════════════════════════════
# llm_scanner: fabricaba lo que un modelo respondió
# ══════════════════════════════════════════════════════════════════


def test_llm_scanner_sin_garak_no_fabrica_checks_de_seguridad():
    """Sin Garak, `NOT_SCANNED` con 0 checks y score None.

    Antes devolvía `SIMULATED_CHECKS`, que incluía `model_response`
    inventados — es decir, **fabricaba la conversación del modelo** con el
    endpoint del usuario, y calculaba `score` y severidad sobre checks que
    nunca se ejecutaron. `api/routers/intel.py` está montado: un
    "3 fallos altos, 34%" de un escaneo inexistente se lee como un
    veredicto de seguridad.
    """
    import asyncio

    from cores.intel.llm_scanner import scan_llm_endpoint

    result = asyncio.run(scan_llm_endpoint("https://api.ejemplo.com/chat"))

    if result.model == "NOT_SCANNED":
        assert result.checks == [], "no puede devolver checks si no escaneó"
        assert result.summary["score"] is None, "score inventado"
        assert result.summary["status"] == "NOT_SCANNED"
        assert result.summary["high_severity"] is None
        assert "Garak" in result.methodology, "el motivo tiene que decir cómo escanear de verdad"
    else:
        # Garak presente: los checks son reales, no simulados.
        assert result.methodology == "Garak real execution"


# ══════════════════════════════════════════════════════════════════
# La UI que muestra UNKNOWN como si fuera una medición
# ══════════════════════════════════════════════════════════════════

_STATUS_BAR = Path("frontend/src/components/ui/StatusBar.vue")


def test_el_status_bar_no_pinta_un_cero_como_si_fuera_una_medida():
    """`healthScore = ref(0)` + 404 ⇒ "Health: 0" en rojo, para siempre.

    `/mission/status` no existe (verificado contra `app.openapi()['paths']`).
    El `catch` del `Promise.allSettled` dejaba el valor inicial, y el
    template hacía `healthScore >= 80 ? success : ... : destructive` ⇒ **0 en
    rojo en el status bar de todas las pantallas**, de forma permanente.

    Es la versión visual de `acceptance_rate: 0.0` sobre 960 registros sin
    clasificar: no sabemos, y el componente afirma "cero".
    """
    src = _STATUS_BAR.read_text(encoding="utf-8")

    assert "/mission/status" not in src, "volvió a pedir un endpoint inexistente"
    assert "healthScore" not in src, "healthScore quedó sin fuente: no puede seguir en el template"
    assert "health_score" not in src, "se inventó otra fuente para el mismo número"


def test_las_plantillas_no_convierten_unknown_en_cero():
    """`|| 0` en un campo que puede ser `null` = afirmar "cero" sin saberlo.

    Los tiles de la tab Executive hacían `executive?.findings?.total || 0`:
    con el endpoint en 404 la tab entera enseñaba 0/0/0/$0, indistinguible de
    un pipeline realmente vacío. Ahora los Unknown se renderizan `—`.
    """
    for rel in (
        "frontend/src/pages/SecurityConsolidated.vue",
        "frontend/src/pages/CopilotConsolidated.vue",
        "frontend/src/pages/ProfileConsolidated.vue",
    ):
        src = Path(rel).read_text(encoding="utf-8")
        assert "?.total || 0" not in src, f"{rel}: `|| 0` convierte UNKNOWN en 0"
        assert "?.confirmed || 0" not in src, f"{rel}: `|| 0` convierte UNKNOWN en 0"


# ══════════════════════════════════════════════════════════════════
# health: un check que nunca puede pasar mantiene RED al sistema
# ══════════════════════════════════════════════════════════════════


def test_agents_idle_no_degradan_el_sistema(monkeypatch):
    """`check_agents_health` exigía que los 8 agentes estuvieran `running`.

    Los agentes departamentales corren por demanda: los 8 reportan
    `offline` cuando están idle, así que el check **nunca pasaba** y el
    sistema queda RED para siempre (con ~50k errores acumulados) sin que
    nada estuviera roto. Sólo un agente en `error` con `last_error` debe
    degradar.

    Este test corre el check REAL contra un registry falso. La versión
    anterior afirmaba la misma regla sobre objetos `_Idle`/`_Broken`
    construidos en el propio test: pasaba con cualquier implementación del
    check, incluso con la que era el bug — el `import cores.health.checks`
    quedaba sin usar. Era un test que no podía fallar, o sea confianza
    falsa. Para que valga tiene que entrar en `cores/health/checks.py`, y de
    ahí la necesidad de monkeypatchear `get_all_agents`.
    """
    import cores.agents as agents_module
    from cores.health.checks import register_default_checks
    from cores.health.engine import HealthCenter

    class _Idle:
        def health(self):
            return {"status": "offline", "last_error": None}

    class _Broken:
        def health(self):
            return {"status": "error", "last_error": "boom"}

    def _check(agents: list) -> bool:
        """Ejecuta `check_agents_health` real contra `agents`, y solo él."""
        monkeypatch.setattr(agents_module, "get_all_agents", lambda: agents)
        center = HealthCenter()
        register_default_checks(center)
        # Quedarnos con el check bajo prueba: correr los ~20 restantes
        # agregaría tiempo y dependencias (DB, vault) sin probar nada más.
        for name in [c["name"] for c in center.list_checks() if c["name"] != "agents_health"]:
            center.unregister(name)
        return center.run_all().checks["agents_health"]

    # 8 agentes idle (el estado real en reposo) ⇒ sano.
    assert _check([_Idle() for _ in range(8)]) is True

    # Uno en error ⇒ degradado. Éste es el assert que distingue el fix del bug:
    # con la versión anterior (`all(status == "running")`) también daba False,
    # con lo que el test viejo no habría detectado la regresión a "todo rojo".
    assert _check([_Idle() for _ in range(7)] + [_Broken()]) is False

    # Sin agentes ⇒ no se puede afirmar nada ⇒ degradado, no verde por descarte.
    assert _check([]) is False
