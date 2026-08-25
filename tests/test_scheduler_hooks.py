"""Guards para el hook pipeline→EventBus del ScanScheduler (P0-1 audit 2026-08-25).

El bug original: el cuerpo real vivía en un def interno nunca invocado →
cero eventos PIPELINE_STAGE_* llegaban al EventBus.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def scheduler():
    from api.scheduler import ScanScheduler

    return ScanScheduler()


def test_hook_publishes_stage_completed_event(scheduler, monkeypatch):
    """_copilot_hook debe publicar PIPELINE_STAGE_COMPLETED al EventBus."""
    from cores.events.event_bus import get_event_bus

    bus = get_event_bus()
    received: list[tuple] = []

    def fake_publish(event_type, **data):
        received.append((event_type, data))

    monkeypatch.setattr(bus, "publish", fake_publish)
    monkeypatch.setattr("api.scheduler._get_copilot", lambda: None)  # COPILOT opcional

    scheduler._copilot_hook("discover", "completed", pipeline_id="abcd1234")

    assert received, "el hook no publicó ningún evento al EventBus"
    event_type, data = received[0]
    assert "pipeline.stage.completed" in event_type or "completed" in event_type
    assert data.get("stage") == "discover"
    assert data.get("pipeline_id") == "abcd1234"


def test_hook_publishes_failed_event_with_error(scheduler, monkeypatch):
    from cores.events.event_bus import get_event_bus

    bus = get_event_bus()
    received: list[str] = []
    monkeypatch.setattr(bus, "publish", lambda et, **d: received.append(et))
    monkeypatch.setattr("api.scheduler._get_copilot", lambda: None)

    scheduler._copilot_hook("recon", "failed", pipeline_id="abcd1234", error_message="boom")

    assert any("failed" in et for et in received), f"esperado evento failed, recibido {received}"


def test_hook_never_raises(scheduler, monkeypatch):
    """El hook es best-effort: un EventBus caído no puede romper el pipeline."""
    from cores.events.event_bus import get_event_bus

    def boom(*a, **k):
        raise RuntimeError("bus down")

    monkeypatch.setattr(get_event_bus(), "publish", boom)
    monkeypatch.setattr("api.scheduler._get_copilot", lambda: None)

    scheduler._copilot_hook("report", "completed")  # no debe lanzar
