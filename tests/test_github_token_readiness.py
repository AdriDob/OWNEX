"""Readiness de OWNEX 1.0: la cadena GITHUB_TOKEN → submission → revenue.

Contexto (2026-10-04). El owner decidió dejar el `GITHUB_TOKEN` **pendiente**
en `~/.config/ownex/opportunity.env` y preparar el resto al 100%. Eso exige que
la cadena esté auditada eslabón por eslabón. Este archivo es el que dice, de
forma falsable, que cuando el token aparezca el camino no tiene agujeros.

Dos bugs reales encontrados al auditar (`KNOWN_DEBT #56`):

**Bug 1 — el fail-closed del adapter era código muerto.** `_execute_submission`
hacía `raise ValueError` si `_get_api_key` no encontraba nada. Pero
`GitHubBountyAdapter.submit_work()` tiene un camino `needs_access` fail-closed
escrito exactamente para ese caso (`requirement` con el path exacto, `human_gate`,
`attempted_external_action: false`) — y nunca se alcanzaba. Peor: `_get_api_key`
sólo miraba `IdentityVault`, así que un token pegado en `opportunity.env` (donde
el propio adapter dice pegarlo) era **ignorado** y el item iba a DLQ tras 3
reintentos con esperas.

**Bug 2 — un envío fallido se registraba como enviado.** `record.status =
SUBMITTED` se seteaba incondicionalmente, antes de mirar `result["success"]`.
Consecuencias: el revenue bridge recibía SUBMITTED → REVIEWING (un estado
pendiente que no ocurrió), y `_find_submission` contaba el item como ya-enviado
para siempre, impidiendo el reintento.

Network-free: platform clients, assisted executor y adapters se fakean. Ningún
test de este archivo envía nada a GitHub.
"""

from __future__ import annotations

import asyncio
import types
from pathlib import Path

import pytest

from cores.opportunity.executors.auto_submit import (
    AutoSubmitEngine,
    SubmissionStatus,
)


class _FakeVault:
    def __init__(self, keys=None):
        self._keys = keys if keys is not None else {}

    def get_credentials(self, provider: str) -> dict:
        return self._keys.get(provider, {})


class _FakeAssisted:
    def __init__(self, base_executor=None):
        self.base_executor = base_executor

    async def prepare_work(self, opportunity):
        return types.SimpleNamespace(
            platform="github",
            title="t",
            files={"work.md": "# ok"},
            metadata={"opportunity": opportunity},
            submission_url=None,
        )

    async def save_work_to_disk(self, prepared):
        return "/tmp/pkg"


class _RecordingAdapter:
    """Adapter fake que registra si el motor llegó a consultarlo."""

    def __init__(self, result: dict):
        self.result = result
        self.calls = 0
        self.api_keys_seen: list[str] = []

    async def submit_work(self, prepared, api_key):
        self.calls += 1
        self.api_keys_seen.append(api_key or "")
        return dict(self.result)


NEEDS_ACCESS = {
    "success": False,
    "state": "needs_access",
    "provider": "github",
    "issue_url": "https://github.com/o/r/issues/1",
    "error": "GITHUB_TOKEN no configurada",
    "requirement": "Pegar GITHUB_TOKEN en ~/.config/ownex/opportunity.env",
    "human_gate": "required_before_send",
    "attempted_external_action": False,
}


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    e = AutoSubmitEngine(
        vault=_FakeVault(),
        dlq_path=str(tmp_path / "dlq"),
        queue_path=str(tmp_path / "queue.json"),
    )
    e.base_retry_delay = 0.01
    e.max_retry_delay = 0.02
    monkeypatch.setattr("cores.opportunity.executors.auto_submit.AssistedExecutor", _FakeAssisted)
    monkeypatch.setattr(e, "_get_platform", lambda key: None)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(
        "cores.credentials.vault.get_credentials",
        lambda force_refresh=True: (_ for _ in ()).throw(RuntimeError("sin vault")),
    )
    return e


# ── Eslabón 1 · el token se resuelve ───────────────────────────────────────


def test_env_github_token_is_found(engine, monkeypatch):
    """Un GITHUB_TOKEN en el entorno DEBE encontrarlo `_get_api_key`."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fixture")
    assert engine._get_api_key("github_bounty") == "ghp_fixture"
    assert engine._get_api_key("github") == "ghp_fixture"


def test_credentials_vault_github_token_is_found(engine, monkeypatch):
    """Y también desde `cores.credentials.vault` (el archivo opportunity.env)."""
    monkeypatch.setattr(
        "cores.credentials.vault.get_credentials",
        lambda force_refresh=True: types.SimpleNamespace(github_token="ghp_from_file"),
    )
    assert engine._get_api_key("github_bounty") == "ghp_from_file"


def test_absent_token_returns_none_not_raises(engine):
    """Sin token devuelve None — nunca lanza. El fail-closed lo maneja el adapter."""
    assert engine._get_api_key("github_bounty") is None


# ── Eslabón 2 · el fail-closed es alcanzable (regresión Bug 1) ─────────────


async def test_needs_access_is_reachable_without_token(engine, monkeypatch):
    """REGRESIÓN Bug 1: sin token, el adapter debe ALCANZAR su salida fail-closed.

    Antes el motor hacía `raise ValueError` antes de llegar al adapter, así que su
    `needs_access` —con el requisito humano exacto— era código muerto.
    """
    adapter = _RecordingAdapter(NEEDS_ACCESS)
    monkeypatch.setattr(engine, "_get_adapter", lambda key: adapter)

    record = await engine.submit_workbank_item("item-1", "github_bounty", {"title": "t", "url": "u"})

    assert adapter.calls > 0, "el adapter no fue consultado: el raise lo precede"
    assert set(adapter.api_keys_seen) == {""}, "sin token no debe inventarse una key"
    assert record.submission_result.get("state") == "needs_access"
    assert record.submission_result.get("attempted_external_action") is False
    assert "GITHUB_TOKEN" in (record.submission_result.get("requirement") or "")
    assert record.status is not SubmissionStatus.SUBMITTED, (
        f"un needs_access no puede registrarse como enviado (quedó {record.status})"
    )


async def test_platform_without_adapter_still_goes_to_dlq(engine, monkeypatch):
    """El fix NO debe romper el DLQ real: sin adapter y sin key, sigue a DLQ."""
    monkeypatch.setattr(engine, "_get_adapter", lambda key: None)
    record = await engine.submit_workbank_item("item-2", "bugcrowd", {"title": "t"})
    assert record.status is SubmissionStatus.DLQ
    assert "No API key" in (record.last_error or "")


# ── Eslabón 3 · honestidad del estado (regresión Bug 2) ─────────────────────


async def test_failed_submission_is_not_marked_submitted(engine, monkeypatch):
    """REGRESIÓN Bug 2: `success=False` NO puede quedar como SUBMITTED.

    Contrato real: cada intento fallido queda FAILED mientras reintenta, y DLQ al
    agotar los 3 intentos. Lo que NUNCA debe pasar es SUBMITTED.
    """
    adapter = _RecordingAdapter({"success": False, "error": "boom", "state": "failed"})
    monkeypatch.setattr(engine, "_get_adapter", lambda key: adapter)

    record = await engine.submit_workbank_item("item-3", "github_bounty", {"title": "t"})

    assert record.status is not SubmissionStatus.SUBMITTED, (
        f"un envío fallido quedó como {record.status} — afirmación falsa sobre el mundo"
    )
    assert record.submitted_at is None, "un envío fallido no puede tener submitted_at"
    assert record.last_error == "boom"
    assert record.status is SubmissionStatus.DLQ, "3 intentos fallidos ⇒ DLQ"


async def test_failed_submission_is_retried_not_skipped(engine, monkeypatch):
    """Un DLQ debe poder reintentarse: `_find_submission` sólo salta SUBMITTED/CONFIRMED."""
    adapter = _RecordingAdapter({"success": False, "error": "boom"})
    monkeypatch.setattr(engine, "_get_adapter", lambda key: adapter)

    first = await engine.submit_workbank_item("item-4", "github_bounty", {"title": "t"})
    assert first.status is SubmissionStatus.DLQ

    calls_before = adapter.calls
    second = await engine.submit_workbank_item("item-4", "github_bounty", {"title": "t"})

    assert adapter.calls > calls_before, "un envío fallido fue contado como ya-enviado y nunca se reintentó"
    assert second.status is not SubmissionStatus.SUBMITTED


async def test_successful_submission_still_marks_submitted(engine, monkeypatch):
    """No regresión: el camino feliz sigue exactamente igual."""
    adapter = _RecordingAdapter({"success": True, "external_id": "", "url": "https://x/1"})
    monkeypatch.setattr(engine, "_get_adapter", lambda key: adapter)

    async def _never_confirmed(platform, external_id, api_key):
        return False

    monkeypatch.setattr(engine, "_poll_confirmation", _never_confirmed)

    record = await engine.submit_workbank_item("item-5", "github_bounty", {"title": "t"})

    assert record.status is SubmissionStatus.SUBMITTED
    assert record.submitted_at is not None
    assert adapter.calls == 1, "un envío exitoso no debe reintentarse"


async def test_revenue_bridge_only_sees_honest_states(engine, monkeypatch):
    """El bridge sólo debe ver el estado real, nunca un envío disfrazado.

    `execution_bridge` mapea SUBMITTED → REVIEWING (pendiente, no caja). Un fallo
    presentado como SUBMITTED fabricaría un estado económico que no ocurrió.
    """
    seen: list[str] = []

    def _spy(record, opportunity=None):
        seen.append(str(record.status))
        return None

    monkeypatch.setattr("cores.revenue_tracker.execution_bridge.record_submission_outcome", _spy)
    adapter = _RecordingAdapter({"success": False, "error": "boom"})
    monkeypatch.setattr(engine, "_get_adapter", lambda key: adapter)

    await engine.submit_workbank_item("item-6", "github_bounty", {"title": "t"})

    assert seen == ["dlq"], f"el bridge sólo debería ver el estado real, recibió: {seen}"


# ── El criterio de OWNEX 1.0, fijado ───────────────────────────────────────


def test_paid_has_a_single_gate_that_requires_evidence():
    """`PAID` tiene UN solo camino y exige evidencia: monto > 0 y referencia.

    Es lo que distingue "software que creemos que puede ganar dinero" de "software
    que ganó dinero" (criterio OWNEX 1.0). Si este test falla, alguien abrió un
    segundo camino a PAID o relajó la exigencia de evidencia.
    """
    from cores.revenue_tracker.execution_bridge import record_bounty_paid

    with pytest.raises(ValueError, match="amount_usd"):
        record_bounty_paid("sub-x", 0.0, "ref-123")
    with pytest.raises(ValueError, match="payout_ref"):
        record_bounty_paid("sub-x", 10.0, "   ")
    assert record_bounty_paid("sub-inexistente", 10.0, "ref-123") is None, (
        "sin oportunidad registrada no se inventa un pago"
    )


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Los backoff del engine no deben costingar tiempo real al test."""
    real = asyncio.sleep

    async def _instant(delay, *a, **kw):
        return await real(0, *a, **kw)

    monkeypatch.setattr(asyncio, "sleep", _instant)


# ── El revenue bridge no puede fallar en silencio ────────────────────────
#
# Patrón repetido 5 veces en este proyecto: un `except: return []` convierte
# "el conector está roto" en "no hay oportunidades". Aquí la versión es más
# grave: si el bridge de revenue falla, el envío queda registrado como enviado
# y el revenue_event NO existe — y nada lo dice fuera del log.


def test_revenue_bridge_failure_is_persisted_not_swallowed(tmp_path) -> None:
    """Si el bridge falla, el error queda en el registro persistido."""
    import builtins
    import json

    from cores.opportunity.executors.auto_submit import (
        AutoSubmitEngine,
        SubmissionRecord,
        SubmissionStatus,
    )

    tmp = Path(tmp_path)
    engine = AutoSubmitEngine(dlq_path=str(tmp / "dlq"), queue_path=str(tmp / "queue.json"))
    record = SubmissionRecord(
        id="s1",
        platform="opire",
        opportunity_id="o1",
        opportunity_title="t",
        idempotency_key="k",
        status=SubmissionStatus.SUBMITTED,
        metadata={"reward": 100.0},
    )
    engine._submissions[record.id] = record

    real_import = builtins.__import__

    def boom(name, *a, **kw):
        if name.endswith("execution_bridge"):
            raise RuntimeError("tracker caido")
        return real_import(name, *a, **kw)

    builtins.__import__ = boom
    try:
        engine._record_revenue_bridge(record, {"reward": 100.0})
    finally:
        builtins.__import__ = real_import

    assert "revenue_bridge_error" in record.metadata, (
        "el fallo del bridge se tragó: el envío queda 'correcto' sin revenue_event y nadie lo sabe"
    )
    persisted = json.loads((tmp / "queue.json").read_text())["submissions"]["s1"]
    assert "revenue_bridge_error" in persisted["metadata"], (
        "el fallo no sobrevivió al reinicio: la cola es lo que persiste"
    )
