"""El registro de capacidades pendientes es la SSOT de la configuración.

Por qué existe (2026-10-05). Pedido del owner:

    "todo lo que quede pendiente de configuración debe aparecer en la
     configuración del sistema (front)"

Antes esa información estaba dispersa: 145 `os.getenv()` por el backend, una
tupla de 16 keys en `setup/checklist.py`, y docstrings que prometían
capacidades contingent on keys que nadie listaba. Una capacidad gateada por
una key invisible es una capacidad que no existe.

Estos tests fijan las reglas que hacen que el registro sea confiable, no sólo
existente. La más importante: **el impacto declarado tiene que coincidir con
la realidad**. Si una capacidad marcada `bloqueada` arranca igual, el owner
chasea una key que no hace falta — y la próxima vez deja de mirar el panel.
"""

from __future__ import annotations

import pytest

from cores.setup.capability_config import (
    BY_ID,
    CAPABILITIES,
    Capability,
    ConfigRequirement,
    all_envs,
    snapshot,
)


class TestRegistryShape:
    def test_no_esta_vacio(self) -> None:
        assert len(CAPABILITIES) >= 10, "un registro de 3 capacidades no cubre el sistema"

    def test_ids_unicos(self) -> None:
        ids = [c.id for c in CAPABILITIES]
        dupes = {i for i in ids if ids.count(i) > 1}
        assert not dupes, f"ids duplicados: {dupes}"

    def test_by_id_cubre_todo(self) -> None:
        assert set(BY_ID) == {c.id for c in CAPABILITIES}

    def test_toda_capability_explica_que_hace(self) -> None:
        """Una capacidad sin `what` es un nombre sin significado."""
        sin_what = [c.id for c in CAPABILITIES if not c.what.strip()]
        assert not sin_what, f"capacidades sin explicación: {sin_what}"

    def test_toda_capability_tiene_categoria(self) -> None:
        sin_cat = [c.id for c in CAPABILITIES if not c.category.strip()]
        assert not sin_cat, f"capacidades sin categoría (el front no puede agrupar): {sin_cat}"

    def test_toda_requirement_explica_que_pierde(self) -> None:
        """`without` es el campo que hace útil el panel: sin él es una lista de keys."""
        sin = [(c.id, r.env) for c in CAPABILITIES for r in c.requirements if not r.without.strip()]
        assert not sin, f"requirements sin explicar qué se pierde: {sin}"


class TestImpactIsHonest:
    """El impacto declarado tiene que coincidir con la realidad."""

    def test_bloqueada_implica_una_key_requerida_faltante(self) -> None:
        env: dict[str, str] = {}
        for c in CAPABILITIES:
            if c.impact(env) == "bloqueada":
                assert c.missing_required(env), (
                    f"{c.id} se declara bloqueada sin ninguna key requerida faltando: "
                    "eso hace que el owner persiga una key que no existe"
                )

    def test_ninguno_implica_que_no_falta_nada(self) -> None:
        """`ninguno` + keys faltantes = el panel miente en la otra dirección."""
        env: dict[str, str] = {}
        for c in CAPABILITIES:
            if c.impact(env) == "ninguno":
                assert not c.missing_required(env) and not c.missing_optional(env), (
                    f"{c.id} dice 'sin configuración pendiente' pero le faltan keys"
                )

    def test_degradada_no_requiere_key_para_arrancar(self) -> None:
        env: dict[str, str] = {}
        for c in CAPABILITIES:
            if c.impact(env) == "degradada":
                assert not c.missing_required(env), (
                    f"{c.id} es degradada pero le falta una key requerida: eso la hace bloqueada"
                )

    def test_solo_trading_live_esta_bloqueada_de_a_default(self) -> None:
        """Guard del estado real: si esto cambia, el panel cambió de verdad.

        Sin `SOLANA_PRIVATE_KEY` lo único que no puede hacer el sistema es
        firmar transacciones. Todo lo demás debe reportar `degradada` o
        `ninguno` — si el panel dice "3 bloqueadas", algo se rompió.
        """
        env: dict[str, str] = {}
        bloqueadas = [c.id for c in CAPABILITIES if c.impact(env) == "bloqueada"]
        assert bloqueadas == ["trading_live"], f"cambió el set de bloqueadas: {bloqueadas}"


class TestSecretHygiene:
    def test_no_expone_valores_de_variables(self) -> None:
        """El snapshot dice presencia, nunca contenido."""
        env = {"SOLANA_PRIVATE_KEY": "base58-valor-secreto", "GROQ_API_KEY": "gsk-secreto"}
        s = snapshot(env)

        import json

        blob = json.dumps(s)
        assert "base58-valor-secreto" not in blob, "el snapshot filtró un valor de variable"
        assert "gsk-secreto" not in blob, "el snapshot filtró un valor de variable"

    def test_marca_presencia_por_variable(self) -> None:
        s = snapshot({"SOLANA_PRIVATE_KEY": "x"})
        reqs = {r["env"]: r for c in s["capabilities"] for r in c["requirements"]}
        assert reqs["SOLANA_PRIVATE_KEY"]["present"] is True
        assert reqs["GROQ_API_KEY"]["present"] is False


class TestWellKnownCapabilities:
    """Las capacidades que la auditoría destapó deben estar registradas.

    Si una de estas desaparece del registro, el panel vuelve a esconder
    exactamente lo que el owner pidió ver.
    """

    @pytest.mark.parametrize(
        "cap_id",
        [
            "trading_live",  # la única bloqueada: requiere private key
            "trading_onchain",  # Helius
            "ai_free_cloud",  # los 4 providers free que activamos
            "bugbounty_scan",
            "bugbounty_submission",
            "copy_trading",
            "osint_deep",
        ],
    )
    def test_la_capacidad_existe(self, cap_id: str) -> None:
        assert cap_id in BY_ID, f"{cap_id} desapareció del registro de configuración"

    def test_trading_live_usa_solana_private_key(self) -> None:
        assert "SOLANA_PRIVATE_KEY" in BY_ID["trading_live"].required_envs

    def test_helius_es_opcional_no_requerida(self) -> None:
        """Helius NO es necesaria: el sistema funciona con el RPC público.

        Marcarla como requerida haría que el panel diga "bloqueada" sin
        motivo, que es la mentira que este panel existe para no contar.
        """
        assert "HELIUS_API_KEY" in BY_ID["trading_onchain"].optional_envs
        assert "HELIUS_API_KEY" not in BY_ID["trading_onchain"].required_envs

    def test_trading_mode_es_opcional_porque_default_es_dry_run(self) -> None:
        """`TRADING_MODE` ausente = dry_run = seguro. No es un bloqueo."""
        assert "TRADING_MODE" in BY_ID["trading_live"].optional_envs

    def test_las_4_providers_free_esta_registradas(self) -> None:
        opt = BY_ID["ai_free_cloud"].optional_envs
        for env in ("GROQ_API_KEY", "CEREBRAS_API_KEY", "TOGETHER_API_KEY", "DEEPINFRA_API_KEY"):
            assert env in opt, f"{env} no aparece en la capacidad de providers free"


class TestHelpers:
    def test_all_envs_deduplica(self) -> None:
        envs = all_envs()
        assert len(envs) == len(set(envs))
        assert envs == sorted(envs)

    def test_envs_que_pertecen_a_varias_capacidades_se_listan_una_vez(self) -> None:
        """GROQ aparece en ai_free_cloud y trading_radar; la lista es única."""
        envs = all_envs()
        assert envs.count("GROQ_API_KEY") == 1

    def test_snapshot_totals_suman(self) -> None:
        s = snapshot({})
        t = s["totals"]
        assert t["configured"] + t["pending_blocking"] == t["capabilities"]

    def test_snapshot_tiene_la_forma_que_el_front_usa(self) -> None:
        s = snapshot({})
        assert set(s) == {"capabilities", "totals", "note"}
        for c in s["capabilities"]:
            assert {
                "id",
                "label",
                "category",
                "what",
                "impact",
                "configured",
                "missing_required",
                "missing_optional",
                "requirements",
            } == set(c)
            for r in c["requirements"]:
                assert {"env", "present", "optional", "without", "where"} == set(r)


class TestUnits:
    def test_requirement_inmutable(self) -> None:
        r = ConfigRequirement(env="X", without="y", optional=False, where="z")
        with pytest.raises((AttributeError, TypeError)):
            r.env = "otro"  # type: ignore[misc]

    def test_capability_acepta_env_explicito(self) -> None:
        c = Capability(id="x", label="X", category="C", what="w")
        assert c.missing_required({}) == []
        assert c.missing_optional({}) == []
