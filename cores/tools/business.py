"""Free Business Tools Registry — herramientas 100% gratis para tareas especiales.

Capa negocio (no security): cada tool resuelve UNA tarea especial del flujo
real (${0}, OSS o free-tier). Ninguna ejecuta llamadas remotas aquí: solo se
inventaría disponibilidad (shutil.which / importlib) y se recomienda a la
tarea que la necesita. La ejecución queda en los adapters/módulos reales
(SupplierCatalogAdapter, MPT, voice, dev_bounty_pipeline, etc.).

Reglas:
- `available` = puro, sin subprocess, sin red, nunca miente.
- `used_by` = módulo OWNEX real que la consume ("" si es recomendación aún sin uso).
- Sin secretos: los servicios free-tier se detectan por env/vault, nunca se loguean.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import shutil
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.tools.business")

# ── Tareas especiales del sistema (canónicas) ──────────────────────────────

TASKS: dict[str, dict[str, str]] = {
    "catalog_fetch": {
        "name": "Traer catálogo proveedor a DRAFT",
        "desc": "SupplierCatalogAdapter sincroniza productos (httpx/json). Playwright ayuda si el catálogo es HTML pesado.",
    },
    "content_edit": {
        "name": "Editar/conformar Shorts sin edición manual",
        "desc": "ffmpeg corta/concatena/watermark el video del Content Factory.",
    },
    "media_download": {
        "name": "Bajar material/libre (b-roll, música SFX)",
        "desc": "yt-dlp descarga vids gratuitos para reels sin stock fijo.",
    },
    "stt": {
        "name": "Transcribir audio a texto (subtítulos/voz)",
        "desc": "whisper genera subs exactos para el Short; alimenta la revisión del script.",
    },
    "tts": {
        "name": "Voz sintética local (TTS $0)",
        "desc": "piper/edge-tts generan la narración sin API paga.",
    },
    "llm_local": {
        "name": "LLM local $0 (guion, planning, resumen)",
        "desc": "Ollama alimenta OAR/MPT para guiones y decisiones sin costo por token.",
    },
    "lead_enrich": {
        "name": "Enriquecer leads (email/empresa) free-tier",
        "desc": "Hunter/Apollo free tier completan contacto del lead capturado en web/scrape.",
    },
    "automation_workflow": {
        "name": "Automatización de flujos (n8n self-host)",
        "desc": "n8n self-host ejecuta workflows repetitivos (catalog_sync, report_bot, lead_bot).",
    },
    "data_cli": {
        "name": "Procesar CSV/JSON del negocio",
        "desc": "jq/csvkit/pandas limpian listas de proveedores y exports de leads.",
    },
    "oss_bounty": {
        "name": "Bounties OSS / Algora (git + gh)",
        "desc": "git clona y gh abre PRs para bounties (loop Algora real).",
    },
    "docs_render": {
        "name": "Renderer markdown → PDF/docx (packs/reportes)",
        "desc": "pandoc convierte templates markdown a PDF/docx vendibles.",
    },
    "security_signing": {
        "name": "Firma de archivos (gpg/openssl)",
        "desc": "gpg/openssl firman paquetes y verifican integridad de entregables.",
    },
    "db_cli": {
        "name": "Inspección/backups SQLite",
        "desc": "sqlite3 CLI audita y exporta la DB local (catseye.db).",
    },
}


# ── Registro canónico de herramientas gratis ────────────────────────────────


@dataclass(frozen=True, slots=True)
class FreeTool:
    id: str
    name: str
    task_id: str
    kind: str  # binary | module | service
    check_name: str  # binario en PATH | módulo importable | sin check local
    license: str
    install_hint: str
    free_tier_note: str
    used_by: str
    workspace_ids: tuple[str, ...] = ()


REGISTRY: tuple[FreeTool, ...] = (
    FreeTool(
        "playwright",
        "Playwright",
        "catalog_fetch",
        "module",
        "playwright",
        "Apache-2.0",
        "pip install playwright && playwright install chromium",
        "Browser headless free para catálogos HTML sin API JSON.",
        "SupplierCatalogAdapter (fallback HTML)",
        ("mercado_libre", "droppinglabel"),
    ),
    FreeTool(
        "ffmpeg",
        "FFmpeg",
        "content_edit",
        "binary",
        "ffmpeg",
        "LGPL/GPL",
        "winget install ffmpeg | apt install ffmpeg",
        "Corta/concatena/watermark el video MPT (sin editor).",
        "Content Factory (MoneyPrinterTurbo)",
        ("content_factory",),
    ),
    FreeTool(
        "yt_dlp",
        "yt-dlp",
        "media_download",
        "binary",
        "yt-dlp",
        "Unlicense",
        "pip install -U yt-dlp",
        "Descarga b-roll gratuito para reels.",
        "",
        ("content_factory",),
    ),
    FreeTool(
        "openai_whisper",
        "Whisper",
        "stt",
        "module",
        "whisper",
        "MIT",
        "pip install -U openai-whisper",
        "Subs/transcripción local $0 (no API paga).",
        "cores/voice",
        ("content_factory", "ownex"),
    ),
    FreeTool(
        "piper",
        "Piper TTS",
        "tts",
        "binary",
        "piper",
        "MIT",
        "pip install piper-tts  |  descargar modelo es-419",
        "Voz local OWNEX (calm_operator), sin API.",
        "cores/voice/voice_engine",
        ("ownex", "content_factory"),
    ),
    FreeTool(
        "edge_tts",
        "Edge TTS",
        "tts",
        "module",
        "edge_tts",
        "MIT",
        "pip install edge-tts",
        "Voz Edge gratuita (MPT la usa para narración).",
        "MoneyPrinterTurbo config",
        ("content_factory",),
    ),
    FreeTool(
        "ollama",
        "Ollama",
        "llm_local",
        "binary",
        "ollama",
        "MIT",
        "https://ollama.com  → ollama pull qwen2.5:3b",
        "LLM local: guiones y decisiones sin costo por token.",
        "OAR + MPT (qwen2.5:3b-instruct)",
        ("ownex", "content_factory", "asset_factory"),
    ),
    FreeTool(
        "hunter_env",
        "Hunter.io Free",
        "lead_enrich",
        "service",
        "HUNTER_API_KEY",
        "SaaS free",
        "https://hunter.io → key free 25 búsquedas/mes en env/vault",
        "Email del lead + verificación de dominio (free tier).",
        "client_acquisition.enrich_lead",
        ("lead_services",),
    ),
    FreeTool(
        "apollo_free",
        "Apollo Free",
        "lead_enrich",
        "service",
        "APOLLO_API_KEY",
        "SaaS free",
        "https://www.apollo.io → free credits",
        "Enriquecimiento B2B del lead capturado.",
        "client_acquisition.enrich_lead",
        ("lead_services",),
    ),
    FreeTool(
        "n8n",
        "n8n self-host",
        "automation_workflow",
        "binary",
        "n8n",
        "Sustainable Use License",
        "npm install -g n8n  |  docker run n8nio/n8n",
        "Workflows que el sistema ofrece (scrape→sheets, report_bot).",
        "cores/automation_service (stack de las ofertas)",
        ("lead_services", "ownex"),
    ),
    FreeTool(
        "jq",
        "jq",
        "data_cli",
        "binary",
        "jq",
        "MIT",
        "apt install jq | choco install jq",
        "Procesa JSON de catálogos y snapshots.",
        "",
        ("mercado_libre", "droppinglabel"),
    ),
    FreeTool(
        "pandas",
        "Pandas",
        "data_cli",
        "module",
        "pandas",
        "BSD-3-Clause",
        "pip install pandas",
        "Limpia listas de proveedores y exports de leads.",
        "cores/data_curation (indirecto)",
        ("knowledge_assets", "lead_services"),
    ),
    FreeTool(
        "git",
        "Git",
        "oss_bounty",
        "binary",
        "git",
        "GPL-2.0",
        "apt install git",
        "Clona repos para bounties y Algora (merge→payout).",
        "dev_bounty_pipeline / AlgoraExecutor",
        ("dev_bounty", "asset_factory"),
    ),
    FreeTool(
        "gh",
        "GitHub CLI",
        "oss_bounty",
        "binary",
        "gh",
        "MIT",
        "winget install GitHub.cli | apt install gh",
        "Crea PRs de bounties OSS sin fricción.",
        "AlgoraExecutor (create_pr)",
        ("dev_bounty",),
    ),
    FreeTool(
        "pandoc",
        "Pandoc",
        "docs_render",
        "binary",
        "pandoc",
        "GPL-2.0",
        "apt install pandoc | winget install pandoc",
        "Convierte templates MD a PDF/docx vendibles.",
        "cores/reports/factory + security_packs (render)",
        ("knowledge_assets",),
    ),
    FreeTool(
        "gpg",
        "GPG",
        "security_signing",
        "binary",
        "gpg",
        "GPL-3.0",
        "apt install gnupg",
        "Firma/verifica paquetes de entrega y packs.",
        "",
        ("ownex", "knowledge_assets"),
    ),
    FreeTool(
        "openssl",
        "OpenSSL",
        "security_signing",
        "binary",
        "openssl",
        "Apache-2.0",
        "viene con el OS / brew install openssl",
        "Hasheo/checksums y TLS para firmas.",
        "cores/backup + migración (sha256)",
        ("ownex",),
    ),
    FreeTool(
        "sqlite3",
        "SQLite3 CLI",
        "db_cli",
        "binary",
        "sqlite3",
        "Public Domain",
        "apt install sqlite3 | winget install SQLite.SQLite",
        "Audita y exporta la DB local sin UI.",
        "database/db.py (catseye.db)",
        ("ownex", "mercado_libre"),
    ),
)


_TASK_BY_ID: dict[str, FreeTool] = {tool.id: tool for tool in REGISTRY}
_TASK_ORDER: dict[str, int] = {tid: i for i, tid in enumerate(TASKS)}


def task_catalog() -> list[dict[str, str]]:
    """Tareas especiales canónicas (id, name, desc) ordenadas por definición."""
    return [{"id": tid, "name": TASKS[tid]["name"], "desc": TASKS[tid]["desc"]} for tid in TASKS]


def find_tool(tool_id: str) -> FreeTool | None:
    return _TASK_BY_ID.get(tool_id)


def _is_available(tool: FreeTool) -> tuple[bool, str]:
    """Detección pura, sin subprocess ni red. Nunca miente."""
    if tool.kind == "binary":
        if shutil.which(tool.check_name):
            return True, "installed"
        return False, "missing"
    if tool.kind == "module":
        if importlib.util.find_spec(tool.check_name) is not None:
            return True, "installed"
        return False, "missing"
    if tool.kind == "service":
        # Free-tier por env/vault. Nunca se muestra el valor, solo si existe.
        env_val = os.environ.get(tool.check_name, "").strip()
        if env_val:
            return True, "configured"
        try:
            from cores.credentials.vault import get_platform_credentials

            creds = get_platform_credentials(tool.id) or {}
            if any(str(v).strip() for v in creds.values()):
                return True, "configured"
        except Exception:  # noqa: BLE001
            pass
        return False, "missing"
    return False, "unknown_kind"


def inventory() -> list[dict[str, Any]]:
    """Por herramienta: disponibilidad real + licencia + hint + dónde se usa."""
    rows: list[dict[str, Any]] = []
    for tool in REGISTRY:
        ok, state = _is_available(tool)
        rows.append(
            {
                "id": tool.id,
                "name": tool.name,
                "task_id": tool.task_id,
                "task": TASKS[tool.task_id]["name"],
                "kind": tool.kind,
                "license": tool.license,
                "install_hint": tool.install_hint,
                "free_tier_note": tool.free_tier_note,
                "used_by": tool.used_by,
                "state": state,
                "available": ok,
            }
        )
    rows.sort(key=lambda r: (_TASK_ORDER.get(r["task_id"], 99), r["id"]))
    return rows


def by_task() -> dict[str, list[dict[str, Any]]]:
    """Agrupado por tarea especial: cada herramienta gratis que la resuelve."""
    grouped: dict[str, list[dict[str, Any]]] = {tid: [] for tid in TASKS}
    for row in inventory():
        grouped[row["task_id"]].append(row)
    return grouped


def recommended_installs() -> list[dict[str, Any]]:
    """Qué instalar y por qué: solo herramientas faltantes, por tarea."""
    out: list[dict[str, Any]] = []
    for tid, rows in by_task().items():
        missing = [r for r in rows if not r["available"]]
        if missing:
            out.append(
                {
                    "task_id": tid,
                    "task": TASKS[tid]["name"],
                    "missing": [{"id": r["id"], "name": r["name"], "install_hint": r["install_hint"]} for r in missing],
                }
            )
    return out


def summary() -> dict[str, Any]:
    rows = inventory()
    return {
        "total_tools": len(rows),
        "available": sum(1 for r in rows if r["available"]),
        "missing": sum(1 for r in rows if not r["available"]),
        "tasks": len(TASKS),
        "tasks_covered": len({r["task_id"] for r in rows if r["available"]}),
        "by_kind": {k: sum(1 for r in rows if r["kind"] == k) for k in ("binary", "module", "service")},
        "recommended_installs": recommended_installs(),
    }
