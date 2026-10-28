"""Health de adapter: un non-200 no es todo lo mismo.

Por qué existe este archivo: `OpenAICompatibleAdapter.check_health` mapeaba
**todo** non-200 a `UNHEALTHY` y **sin** `last_error`. Consecuencia medida en
vivo (2026-10-05): `groq` con key inválida reportaba

    unhealthy   last_error=None

El owner veía "—" en el panel y no tenía forma de saber que el problema era
la key. Un 401 (key inválida), un 429 (cuota) y un 503 (transitorio) exigen
acciones distintas: arreglar la key / esperar / reintentar.

Estos tests fijan que el status refleje el código HTTP y que `last_error`
lleve el detalle.
"""

from __future__ import annotations

import httpx
import pytest

from cores.ai.runtime.adapters import create_openrouter_adapter
from cores.ai.runtime.interfaces import HealthStatus
from cores.ai.runtime.resilience import health_status_for


@pytest.mark.asyncio
async def test_401_reports_auth_failed_with_detail(monkeypatch):
    """401 = key inválida. Debe decir auth_failed y traer el body del error."""

    class _Resp:
        status_code = 401
        text = '{"error":{"message":"Invalid API Key"}}'

    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)

    adapter = create_openrouter_adapter()
    adapter._api_key = "invalid-key-for-test"
    health = await adapter.check_health()

    assert health.status is HealthStatus.AUTH_FAILED
    assert health.last_error is not None
    assert "401" in health.last_error
    assert "Invalid API Key" in health.last_error


@pytest.mark.asyncio
async def test_429_reports_quota_not_generic_unhealthy(monkeypatch):
    """429 = cuota. Debe distinguishse de un fallo genérico."""

    class _Resp:
        status_code = 429
        text = "rate limit exceeded"

    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)

    adapter = create_openrouter_adapter()
    adapter._api_key = "k"
    health = await adapter.check_health()

    assert health.status is HealthStatus.QUOTA_EXCEEDED
    assert health.last_error and "429" in health.last_error


@pytest.mark.asyncio
async def test_503_reports_unhealthy_with_detail(monkeypatch):
    """5xx = transitorio, pero tampoco puede perder el detalle."""

    class _Resp:
        status_code = 503
        text = "upstream unavailable"

    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)

    adapter = create_openrouter_adapter()
    adapter._api_key = "k"
    health = await adapter.check_health()

    assert health.status is HealthStatus.UNHEALTHY
    assert health.last_error and "503" in health.last_error


@pytest.mark.asyncio
async def test_200_is_healthy_without_error(monkeypatch):
    """El camino feliz no debe inventar un last_error."""

    class _Resp:
        status_code = 200
        text = '{"data":[]}'

    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)

    adapter = create_openrouter_adapter()
    adapter._api_key = "k"
    health = await adapter.check_health()

    assert health.status is HealthStatus.HEALTHY
    assert health.last_error is None


@pytest.mark.asyncio
async def test_missing_key_is_auth_failed_without_network(monkeypatch):
    """Sin key no se toca la red y el motivo queda explícito."""

    def _boom(*a, **kw):
        raise AssertionError("no debe abrir conexión sin credencial")

    monkeypatch.setattr(httpx, "AsyncClient", _boom)

    adapter = create_openrouter_adapter()
    adapter._api_key = ""
    health = await adapter.check_health()

    assert health.status is HealthStatus.AUTH_FAILED
    assert health.last_error and "missing" in health.last_error.lower()


def test_health_status_for_covers_the_codes_we_route_on():
    """El helper reusa _STATUS_MAP: 401/403 y 402/429 deben separarse."""
    assert health_status_for(401) == "auth_failed"
    assert health_status_for(403) == "auth_failed"
    assert health_status_for(402) == "quota_exceeded"
    assert health_status_for(429) == "quota_exceeded"
    assert health_status_for(500) == "unhealthy"
    assert health_status_for(503) == "unhealthy"
    # Sin mapeo: nunca "healthy" por defecto, que es el modo de fallo caro.
    assert health_status_for(418) == "unhealthy"
