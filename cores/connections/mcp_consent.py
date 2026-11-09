"""MCP consent + audit — permission scopes and call log for external agents.

Two data classes:
  - metadata: catalog/status/sync-health (low sensitivity, always allowed)
  - financial: positions, cash balances, transaction history (requires consent)

Consent is stored per data class in OWNEX_DATA_DIR/mcp/consent.json.
Audit is append-only JSONL: tool name, data class, provider arg, outcome —
never payloads or secrets.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.env.config import get_config

logger = logging.getLogger("ownex.mcp.consent")

DATA_CLASSES = ("metadata", "financial")

# tool name -> required data class
TOOL_CLASS: dict[str, str] = {
    "get_ownex_status": "metadata",
    "list_connected_providers": "metadata",
    "get_connection_status": "metadata",
    "get_last_sync_results": "metadata",
    "get_data_quality_report": "metadata",
    "get_portfolio_snapshot": "financial",
    "get_portfolio_positions": "financial",
    "get_cash_balances": "financial",
    "get_transaction_history": "financial",
}


def _dir() -> Path:
    return get_config().data_dir / "mcp"


def _consent_path() -> Path:
    return _dir() / "consent.json"


def _audit_path() -> Path:
    return _dir() / "audit.jsonl"


def get_consents() -> dict[str, bool]:
    path = _consent_path()
    if not path.exists():
        return {c: False for c in DATA_CLASSES}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {c: False for c in DATA_CLASSES}
    return {c: bool(data.get(c, False)) for c in DATA_CLASSES}


def set_consent(data_class: str, granted: bool) -> dict[str, bool]:
    if data_class not in DATA_CLASSES:
        raise ValueError(f"data_class inválida: {data_class}")
    consents = get_consents()
    consents[data_class] = granted
    _dir().mkdir(parents=True, exist_ok=True)
    _consent_path().write_text(json.dumps(consents, indent=2))
    logger.info("MCP consent %s=%s", data_class, granted)
    return consents


def check_tool_allowed(tool_name: str) -> tuple[bool, str]:
    """Return (allowed, reason). Unknown tools are always denied."""
    data_class = TOOL_CLASS.get(tool_name)
    if data_class is None:
        return False, "tool no permitida"
    if data_class == "metadata":
        return True, ""
    if get_consents().get("financial"):
        return True, ""
    return False, "requiere consentimiento para datos financieros (clase 'financial')"


def record_call(tool_name: str, provider: str, outcome: str) -> None:
    """Append audit entry. Never logs arguments payloads or secrets."""
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "tool": tool_name,
        "data_class": TOOL_CLASS.get(tool_name, "unknown"),
        "provider": provider,
        "outcome": outcome,
    }
    try:
        _dir().mkdir(parents=True, exist_ok=True)
        with _audit_path().open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as exc:
        logger.warning("MCP audit write failed: %s", exc)


def get_audit(limit: int = 100) -> list[dict[str, Any]]:
    path = _audit_path()
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("MCP audit read failed: %s", exc)
        return []
    return entries[-max(1, min(limit, 1000)) :][::-1]
