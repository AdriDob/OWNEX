"""Change Monitor — baselines de superficie + deltas que importan (P3).

Guarda snapshots (sha256) de respuestas HTTP y bundles JS por target y
emite alertas SOLO cuando el delta trae estructuras relevantes: rutas API,
parámetros, endpoints GraphQL, claves/secretos, consola admin.

Diseño honesto y $0:
- Sin red dentro del módulo: el `fetcher` se inyecta (tests 100% offline).
- Nunca raisea: todo error de fetch/parse es un skip con motivo.
- Sin inventos: una URL nueva es "nueva", no "vulnerable".
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.recon.change_monitor")

STORE_FILENAME = "recon_change_baselines.json"
ALERTS_FILENAME = "recon_change_alerts.jsonl"
MAX_ALERTS_KEPT = 200

# Rutas y fragmentos JS que vale la pena extraer de un bundle/página
_ROUTE_PATTERNS = (
    re.compile(r"""["'`](/(?:api|v\d|graphql|gql|rest|internal|admin|auth|oauth|callback)[^"'`\s]*)["'`]"""),
    re.compile(r"""fetch\(\s*["'`]([^"'`]+)["'`]"""),
    re.compile(r"""axios\.(?:get|post|put|patch|delete)\(\s*["'`]([^"'`]+)["'`]"""),
    re.compile(r"""(?:url|endpoint|path)\s*[:=]\s*["'`]([^"'`]+)["'`]"""),
)

# Señales que elevan un delta a alerta (no a finding: novedad ≠ vulnerabilidad)
_SECRET_PATTERNS = (
    re.compile(
        r"(?i)(api[_-]?key|secret|token|password|passwd|aws_|sk-live|ghp_|xox[bap]-)\s*[:=]\s*['\"][^'\"]{4,}['\"]"
    ),
    re.compile(r"(?i)(graphql|/\.env|/admin|/console|/actuator|debug\s*=\s*true)"),
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def extract_js_routes(content: str) -> list[str]:
    """Extrae rutas/parámetros de un bundle JS o HTML. Puro, nunca raisea."""
    found: list[str] = []
    try:
        for rx in _ROUTE_PATTERNS:
            for m in rx.findall(content or ""):
                route = m.strip()
                if route and route not in found and len(route) < 300:
                    found.append(route)
    except Exception as exc:
        logger.warning("change_monitor: extract falló: %s", exc)
    return found[:100]


def interesting_signals(routes: list[str], raw: str = "") -> list[str]:
    """Filtra qué del delta merece alerta. Vacío = ruido, sin alerta."""
    hits: list[str] = []
    try:
        for r in routes or []:
            rl = r.lower()
            if any(k in rl for k in ("graphql", "gql", "admin", "internal", ".env", "actuator", "debug")):
                hits.append(f"ruta sensible nueva: {r}")
        for rx in _SECRET_PATTERNS:
            if rx.search(raw or ""):
                hits.append("posible secreto o superficie sensible en contenido")
                break
        if len(routes or []) >= 5:
            hits.append(f"{len(routes)} rutas nuevas en un solo delta")
    except Exception as exc:
        logger.warning("change_monitor: filter falló: %s", exc)
    return hits


def _store_path() -> Path:
    return Path(os.environ.get("OWNEX_DATA_DIR", "data")) / STORE_FILENAME


def _alerts_path() -> Path:
    return Path(os.environ.get("OWNEX_DATA_DIR", "data")) / ALERTS_FILENAME


class ChangeMonitor:
    """Snapshots por clave (target+recurso) con diff y alertas persistidas."""

    def __init__(self, path: Path | None = None, alerts_path: Path | None = None) -> None:
        self.path = path or _store_path()
        self.alerts_path = alerts_path or _alerts_path()
        self._baselines: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._baselines = raw
        except (OSError, ValueError) as exc:
            logger.warning("change_monitor: store ilegible, se empieza vacío: %s", exc)

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._baselines, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("change_monitor: no se pudo persistir: %s", exc)

    def diff(self, key: str, content: str) -> dict[str, Any]:
        """Compara contra baseline. Primera vez = baseline (no alerta)."""
        digest = _sha256(content or "")
        prev = self._baselines.get(key)
        routes = extract_js_routes(content or "")
        result: dict[str, Any] = {"key": key, "changed": False, "first_seen": prev is None, "routes": routes}
        if prev is None:
            self._baselines[key] = {"sha256": digest, "seen_at": _now_iso(), "routes": routes}
            self._save()
            return result
        if prev.get("sha256") != digest:
            old_routes = set(prev.get("routes", []))
            new_routes = [r for r in routes if r not in old_routes]
            result.update({"changed": True, "new_routes": new_routes, "old_sha": prev.get("sha256")})
            self._baselines[key] = {"sha256": digest, "seen_at": _now_iso(), "routes": routes}
            self._save()
        return result

    def record_alert(self, alert: dict[str, Any]) -> None:
        try:
            self.alerts_path.parent.mkdir(parents=True, exist_ok=True)
            with self.alerts_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"at": _now_iso(), **alert}, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("change_monitor: no se pudo guardar alerta: %s", exc)

    def recent_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        try:
            if not self.alerts_path.exists():
                return []
            lines = self.alerts_path.read_text(encoding="utf-8").splitlines()
            out = []
            for line in lines[-MAX_ALERTS_KEPT:]:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
            return out[-max(1, limit) :]
        except OSError:
            return []


# Scope pages de programas AI frontier: un asset nuevo o un cambio de scope
# es la ventana de mayor P(unique). Se vigilan como superficie, no como vuln.
AI_SCOPE_URLS: dict[str, list[str]] = {
    "openai_safety": ["https://openai.com/security/bounty"],
    "anthropic_safety": ["https://www.anthropic.com/security/bounty"],
    "microsoft_ai": ["https://www.microsoft.com/en-us/msrc/bounty"],
}


def ai_scope_targets() -> dict[str, list[str]]:
    """Claves estables → URLs de scope AI. Puro, testeable sin red."""
    return {k: list(v) for k, v in AI_SCOPE_URLS.items()}


def run_change_cycle(
    targets: dict[str, list[str]],
    fetcher: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    """Un ciclo: fetch → diff → alertas filtradas. Nunca raisea.

    targets: {clave: [urls]}. fetcher(url) -> contenido o None (skip).
    Sin fetcher = dry-run que solo inicializa baselines vacíos (no alerta).
    """
    monitor = ChangeMonitor()
    summary: dict[str, Any] = {"checked": 0, "changed": 0, "alerts": 0, "skipped": 0}
    try:
        for key, urls in (targets or {}).items():
            for url in urls or []:
                content: str | None = None
                if fetcher is not None:
                    try:
                        content = fetcher(url)
                    except Exception as exc:
                        logger.warning("change_monitor: fetch %s falló: %s", url, exc)
                        summary["skipped"] += 1
                        continue
                if content is None:
                    summary["skipped"] += 1
                    continue
                summary["checked"] += 1
                delta = monitor.diff(f"{key}::{url}", content)
                if delta.get("changed"):
                    summary["changed"] += 1
                    signals = interesting_signals(delta.get("new_routes", []), content)
                    if signals:
                        monitor.record_alert({"key": key, "url": url, "signals": signals})
                        summary["alerts"] += 1
    except Exception as exc:
        logger.warning("change_monitor: ciclo falló: %s", exc)
        summary["error"] = "cycle_failed"
    return summary


def fresh_domains_with_alerts(limit: int = 50, days: int = 7) -> dict[str, int]:
    """Dominios con alertas recientes → conteo. Alimenta el hunt (primicia).

    Puro en cómputo (solo lee el store), nunca raisea. Vacío = sin primicias.
    """
    from urllib.parse import urlparse

    try:
        alerts = ChangeMonitor().recent_alerts(limit=limit)
        cutoff = datetime.now(UTC).timestamp() - days * 86400
        counts: dict[str, int] = {}
        for alert in alerts:
            try:
                ts = datetime.fromisoformat(str(alert.get("at", ""))).timestamp()
            except (ValueError, TypeError):
                continue
            if ts < cutoff:
                continue
            host = (urlparse(str(alert.get("url", ""))).hostname or "").lower().strip()
            if host:
                counts[host] = counts.get(host, 0) + 1
        return counts
    except Exception as exc:
        logger.warning("change_monitor: fresh_domains falló: %s", exc)
        return {}
