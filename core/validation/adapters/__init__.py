"""HTTP adapter for the Validation Engine.

Ejecuta probes HTTP contra endpoints reales usando httpx.
Captura:
  - Status code, headers, response body
  - Timing (response time ms)
  - Response size
  - Errores de conexión

Soporta:
  - GET, POST, PUT, PATCH, DELETE
  - Headers personalizados (auth, content-type, etc.)
  - Query params y body JSON
  - Timeout configurable
  - Redirecciones (follow_redirects configurable)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("orion.core.validation.http_adapter")

# ── Defaults ───────────────────────────────────────────────────

DEFAULT_TIMEOUT = 15.0
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class ProbeResponse:
    """Respuesta normalizada de una probe HTTP."""

    def __init__(
        self,
        status_code: int = 0,
        headers: dict[str, str] | None = None,
        body: str = "",
        body_bytes: int = 0,
        elapsed_ms: float = 0.0,
        error: str = "",
        success: bool = False,
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body
        self.body_bytes = body_bytes
        self.elapsed_ms = elapsed_ms
        self.error = error
        self.success = success

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "headers": dict(list(self.headers.items())[:20]),  # top 20 headers
            "body_preview": self.body[:500],
            "body_bytes": self.body_bytes,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "error": self.error[:200] if self.error else "",
            "success": self.success,
        }

    @property
    def has_data_leak(self) -> bool:
        """Heurística simple de data leak: respuesta grande con datos JSON."""
        if self.status_code != 200:
            return False
        if self.body_bytes < 50:
            return False
        # Si tiene JSON con múltiples campos
        try:
            data = json.loads(self.body)
            if isinstance(data, dict) and len(data) > 2:
                return True
            if isinstance(data, list) and len(data) > 0:
                return True
        except (json.JSONDecodeError, ValueError):
            pass
        return False


class HTTPAdapter:
    """Adaptador HTTP para ejecutar probes contra endpoints reales.

    Uso:
        adapter = HTTPAdapter()
        resp = adapter.fire(method="GET", url="https://api.target.com/users/123", headers={...})
        print(resp.status_code, resp.elapsed_ms)
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, max_redirects: int = DEFAULT_MAX_REDIRECTS) -> None:
        self._timeout = timeout
        self._max_redirects = max_redirects
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            max_redirects=max_redirects,
            headers={"User-Agent": DEFAULT_USER_AGENT},
            verify=False,  # SSL verify off para endpoints de bug bounty
        )

    def fire(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> ProbeResponse:
        """Ejecuta una request HTTP y devuelve la respuesta normalizada."""
        start = time.monotonic()
        try:
            final_headers = dict(headers or {})
            if "User-Agent" not in {k.lower() for k in final_headers}:
                final_headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

            response = self._client.request(
                method=method.upper(),
                url=url,
                headers=final_headers or None,
                params=params or None,
                json=body if body else None,
            )

            elapsed_ms = (time.monotonic() - start) * 1000
            body_text = response.text
            body_bytes = len(response.content)

            probe_resp = ProbeResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=body_text,
                body_bytes=body_bytes,
                elapsed_ms=elapsed_ms,
                success=True,
            )

            logger.debug(
                "[HTTP] %s %s → %d (%dms, %d bytes)",
                method.upper(),
                url,
                response.status_code,
                elapsed_ms,
                body_bytes,
            )
            return probe_resp

        except httpx.TimeoutException as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.warning("[HTTP] Timeout: %s %s (%.0fms)", method.upper(), url, elapsed_ms)
            return ProbeResponse(
                elapsed_ms=elapsed_ms,
                error=f"Timeout after {self._timeout}s: {exc}",
            )

        except httpx.ConnectError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.warning("[HTTP] Connection error: %s %s: %s", method.upper(), url, exc)
            return ProbeResponse(
                elapsed_ms=elapsed_ms,
                error=f"Connection error: {exc}",
            )

        except httpx.HTTPStatusError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.debug("[HTTP] HTTP error: %s %s → %s", method.upper(), url, exc)
            return ProbeResponse(
                status_code=exc.response.status_code if exc.response else 0,
                headers=dict(exc.response.headers) if exc.response else {},
                body=exc.response.text if exc.response else "",
                body_bytes=len(exc.response.content) if exc.response else 0,
                elapsed_ms=elapsed_ms,
                error=str(exc)[:200],
                success=False,
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.warning("[HTTP] Error: %s %s: %s", method.upper(), url, exc)
            return ProbeResponse(
                elapsed_ms=elapsed_ms,
                error=f"Unexpected error: {exc}",
            )

    def build_url(self, base_url: str, path: str) -> str:
        """Construye URL completa desde base + path."""
        base = base_url.rstrip("/")
        path_clean = path.lstrip("/")
        return f"{base}/{path_clean}" if path_clean else base

    def compare_responses(
        self, baseline: ProbeResponse, probe: ProbeResponse
    ) -> dict[str, Any]:
        """Compara dos respuestas y devuelve diferencias estructuradas."""
        diff: dict[str, Any] = {
            "status_code_diff": baseline.status_code != probe.status_code,
            "size_diff_bytes": probe.body_bytes - baseline.body_bytes,
            "time_diff_ms": round(probe.elapsed_ms - baseline.elapsed_ms, 1),
            "body_changed": baseline.body != probe.body,
            "body_size_change_ratio": round(
                probe.body_bytes / max(baseline.body_bytes, 1), 2
            ),
        }
        return diff

    def close(self) -> None:
        """Cierra el client HTTP."""
        self._client.close()
