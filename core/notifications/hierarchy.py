"""Jerarquía de Información reusable — 3 niveles para todo el sistema."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class InfoLevel(IntEnum):
    """Nivel de detalle de la información."""

    SUMMARY = 1  # L1 — 3-4 líneas, accionable
    DETAILS = 2  # L2 — KPIs importantes, "ver más"
    DEBUG = 3  # L3 — Todos los datos técnicos


@dataclass
class HierarchicalMessage:
    """Mensaje con 3 niveles de detalle."""

    summary: str = ""
    details: str = ""
    debug: dict[str, Any] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    title: str = ""


def render(msg: HierarchicalMessage, level: InfoLevel | int = InfoLevel.SUMMARY) -> str:
    """Renderiza un HierarchicalMessage al nivel especificado."""
    level = InfoLevel(level) if isinstance(level, int) else level
    parts: list[str] = []

    if msg.title:
        parts.append(msg.title)

    if level >= InfoLevel.SUMMARY and msg.summary:
        parts.append(msg.summary)

    if level >= InfoLevel.DETAILS and msg.details:
        parts.append("")
        parts.append(msg.details)

    if msg.suggestions and level >= InfoLevel.DETAILS:
        parts.append("")
        parts.append("💡 Sugerencias:")
        for s in msg.suggestions[:3]:
            parts.append(f"  → {s}")

    if level >= InfoLevel.DEBUG and msg.debug:
        parts.append("")
        parts.append("🔍 Debug:")
        import json

        debug_str = json.dumps(msg.debug, indent=2, default=str)[:500]
        parts.append(f"```\n{debug_str}\n```")

    return "\n".join(parts).strip()


def build(
    summary: str = "",
    details: str = "",
    debug: dict[str, Any] | None = None,
    suggestions: list[str] | None = None,
    title: str = "",
) -> HierarchicalMessage:
    """Construye un HierarchicalMessage rápidamente."""
    return HierarchicalMessage(
        summary=summary,
        details=details,
        debug=debug or {},
        suggestions=suggestions or [],
        title=title,
    )


def extract(
    level: InfoLevel | int,
    data: dict[str, Any],
    *,
    summary_key: str = "summary",
    details_key: str = "details",
    debug_key: str = "debug",
) -> str:
    """Extrae texto del nivel correspondiente de un dict."""
    level = InfoLevel(level) if isinstance(level, int) else level
    parts: list[str] = []
    if level >= InfoLevel.SUMMARY:
        parts.append(data.get(summary_key, ""))
    if level >= InfoLevel.DETAILS:
        d = data.get(details_key, "")
        if d:
            parts.append(f"\n{d}")
    if level >= InfoLevel.DEBUG:
        db = data.get(debug_key, {})
        if db:
            import json

            parts.append(f"\n🔍 {json.dumps(db, indent=2, default=str)[:300]}")
    return "\n".join(parts).strip()
