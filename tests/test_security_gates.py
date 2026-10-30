"""Guards de seguridad: scope, autorización y Human Gate (spec §1, §22-§24, §52, §79).

Sella la REGLA DE ORO:

    NO SCOPE         -> NO ACTION
    NO AUTHORIZATION -> NO ACTION
    NO HUMAN GATE    -> NO IRREVERSIBLE EXTERNAL ACTION

Estos tresholes estaban ABIERTOS y se cerraron en esta fase:

1. `ScopeEnforcementEngine.enforce_endpoint` con scope UNKNOWN sólo logueaba
   un warning y dejaba pasar.
2. `enforce_asset` no tenía ni rama UNKNOWN: pasaba en silencio.
3. `AlgoraExecutor.create_pr` empujaba la rama y abría el PR **sin** token de
   aprobación (a diferencia de `PRBuilder.create_pr`, que sí lo exige).
4. `submit_gate` pasaba con nota cuando no había policy de scope.
"""

from __future__ import annotations

import pytest

from cores.scope_enforcement import (
    AssetType,
    ProgramScopePolicy,
    ScopeDecision,
    ScopeEnforcer,
    ScopeNotVerifiedError,
    ScopeRule,
    ScopeViolationError,
)


@pytest.fixture
def enforcer() -> ScopeEnforcer:
    return ScopeEnforcer()


def _policy(rules: list[ScopeRule]) -> ProgramScopePolicy:
    return ProgramScopePolicy(
        program_id="prog",
        program_name="prog",
        platform="hackerone",
        rules=rules,
    )


# ══════════════════════════════════════════════════════════════════
# 1-2. UNKNOWN scope = FAIL CLOSED (era fail-open)
# ══════════════════════════════════════════════════════════════════


def test_scope_unknown_bloquea_endpoint(enforcer):
    """Sin policy registrada no se puede afirmar autorización."""
    with pytest.raises(ScopeNotVerifiedError):
        enforcer.enforce_endpoint("prog", "https://objetivo.example/api")


def test_scope_unknown_bloquea_asset(enforcer):
    """Antes esta función NO tenía rama UNKNOWN y pasaba en silencio."""
    with pytest.raises(ScopeNotVerifiedError):
        enforcer.enforce_asset("prog", AssetType.DOMAIN, "objetivo.example")


def test_scope_unknown_no_es_la_misma_excepcion_que_out_of_scope(enforcer):
    """'no sé' y 'sé que no' son hechos distintos y no deben confundirse."""
    enforcer.register_policy(
        _policy(
            [
                ScopeRule(asset_type=AssetType.DOMAIN, pattern="permitido.example", is_in_scope=True),
                ScopeRule(asset_type=AssetType.DOMAIN, pattern="otro.example", is_in_scope=False),
            ]
        )
    )
    with pytest.raises(ScopeViolationError):
        enforcer.enforce_endpoint("prog", "https://otro.example/x")


def test_scope_verificado_pasa(enforcer):
    enforcer.register_policy(
        _policy([ScopeRule(asset_type=AssetType.DOMAIN, pattern="permitido.example", is_in_scope=True)])
    )
    assert enforcer.check_endpoint("prog", "https://permitido.example/api") is ScopeDecision.IN_SCOPE
    enforcer.enforce_endpoint("prog", "https://permitido.example/api")  # no lanza


def test_la_excepcion_dice_como_desbloquear(enforcer):
    """El bloqueo debe ser accionable, no un muro ciego."""
    with pytest.raises(ScopeNotVerifiedError) as exc:
        enforcer.enforce_endpoint("prog", "https://x.example")
    assert "ProgramScopePolicy" in str(exc.value)


# ══════════════════════════════════════════════════════════════════
# 3. submit_gate: scope sin verificar NO es autorización
# ══════════════════════════════════════════════════════════════════


def _inp(**kw):
    from cores.auto_submit.submit_gate import SubmitGateInput

    base = {
        "scope": "in_scope",
        "vulnerability_type": "sqli",
        "measured_rate": 0.8,
        "has_repro_text": True,
        "already_submitted": False,
    }
    base.update(kw)
    return SubmitGateInput(**base)


def test_submit_gate_bloquea_scope_no_verificado():
    from cores.auto_submit.submit_gate import submit_gate

    r = submit_gate(_inp(scope="unknown"))
    assert r.allow_submit is False
    assert r.parked_reason == "scope_not_verified"


def test_submit_gate_bloquea_out_of_scope():
    from cores.auto_submit.submit_gate import submit_gate

    r = submit_gate(_inp(scope="out_of_scope"))
    assert r.allow_submit is False and r.parked_reason == "out_of_scope"


def test_submit_gate_pasa_con_scope_verificado():
    from cores.auto_submit.submit_gate import submit_gate

    r = submit_gate(_inp(scope="in_scope"))
    assert r.allow_submit is True


# ══════════════════════════════════════════════════════════════════
# 4. Human Gate en el push de un PR (era inexistente)
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pr_de_algora_exige_human_gate(tmp_path, monkeypatch):
    """Un PR es acción externa irreversible: sin token no se ejecuta nada."""
    from cores.opportunity.executors.algora_executor import AlgoraConfig, AlgoraExecutor

    ex = AlgoraExecutor(AlgoraConfig(github_token="x"))
    called = {"push": False}

    def _boom(*a, **k):
        called["push"] = True
        raise AssertionError("no debe tocar git/red sin approval")

    monkeypatch.setattr(ex, "_clone", _boom, raising=False)
    monkeypatch.setattr(ex, "_setup_repo", _boom, raising=False)
    monkeypatch.setattr(ex, "_apply_changes", _boom, raising=False)

    r = await ex.create_pr(tmp_path, "https://github.com/a/b/issues/1", "msg")
    assert r.success is False
    assert "approval" in (r.error or "").lower()
    assert called["push"] is False


def test_pr_de_algora_tiene_la_misma_superficie_que_prbuilder():
    """Paridad de contrato con PRBuilder.create_pr (approval_token/require_approval)."""
    import inspect

    from cores.autonomy.pr_builder import PRBuilder
    from cores.opportunity.executors.algora_executor import AlgoraExecutor

    for fn in (AlgoraExecutor.create_pr, PRBuilder.create_pr):
        params = inspect.signature(fn).parameters
        assert "approval_token" in params, fn
        assert "require_approval" in params, fn


# ══════════════════════════════════════════════════════════════════
# 5. La escalera de autorización de una oportunidad ya es explícita
# ══════════════════════════════════════════════════════════════════


def test_automatizacion_y_ai_desconocidas_no_permiten_auto_act():
    """UNKNOWN no se convierte en permiso (spec §46/§58)."""
    from cores.direct_work_engine.models import (
        AIPolicy,
        AutomationLevel,
        Opportunity,
        OpportunityCategory,
        WorkPlatform,
        ai_assist_allowed,
        can_auto_act,
    )

    opp = Opportunity(id="x", title="t", platform=WorkPlatform.GITHUB, category=OpportunityCategory.BUG_BOUNTY)
    assert opp.ai_policy is AIPolicy.UNKNOWN
    assert opp.automation_level is AutomationLevel.UNKNOWN
    assert can_auto_act(opp) is False
    assert ai_assist_allowed(opp) is False


def test_argentina_es_dimension_separada_de_global():
    """'global' NO significa 'disponible en Argentina' (spec §8)."""
    from cores.direct_work_engine.models import (
        Opportunity,
        OpportunityCategory,
        WorkPlatform,
        country_access_for,
    )

    global_opp = Opportunity(id="g", title="t", platform=WorkPlatform.GITHUB, category=OpportunityCategory.BUG_BOUNTY)
    assert country_access_for(global_opp) == "UNKNOWN"

    listed = Opportunity(
        id="a",
        title="t",
        platform=WorkPlatform.GITHUB,
        category=OpportunityCategory.BUG_BOUNTY,
        allowed_countries=("argentina",),
    )
    assert country_access_for(listed) == "VERIFIED"
