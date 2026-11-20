"""Human Actions router — exposes docs/FINAL_HUMAN_ACTIONS.md as structured JSON.

Single source of truth stays the markdown doc; this endpoint parses it so
the frontend can render pending owner actions (credentials, consents,
financial authorizations) without duplicating data.

Doc formats handled:
  - "### A1. Title" sections with Campo/Detalle tables (FASE A)
  - Phase tables "| B6 | acción | plataforma | estado |" under "## FASE" headings
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/human-actions", tags=["human-actions"])

_DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "FINAL_HUMAN_ACTIONS.md"

_SECTION_RE = re.compile(r"^###\s+(?P<id>[A-Z]+\d+)\.\s+(?P<title>.+)$", re.MULTILINE)
_FIELD_RE = re.compile(r"^\|\s*(?P<key>[^|]+?)\s*\|\s*(?P<value>[^|]+?)\s*\|\s*$", re.MULTILINE)
_PHASE_RE = re.compile(r"^##\s+FASE\s+(?P<phase>[A-Z])\b", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\|\s*(?P<id>[A-Z]+\d+)\s*\|(?P<rest>.+?)\|\s*$", re.MULTILINE)

_SKIP_KEYS = {"campo", "---", ""}


def _clean(value: str) -> str:
    return value.strip().strip("*").strip()


def _status_of(raw: str) -> str:
    for token in ("BLOCKED_ON_USER", "READY_FOR_AUTHORIZATION", "BLOCKED_ON_PLATFORM", "COMPLETED"):
        if token in raw:
            return token
    return raw.strip() or "UNKNOWN"


def _parse_detail_sections(text: str) -> list[dict]:
    """Parse '### A1. Title' sections with Campo/Detalle tables."""
    matches = list(_SECTION_RE.finditer(text))
    actions: list[dict] = []

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        next_h2 = re.search(r"^##\s", block, re.MULTILINE)
        if next_h2:
            block = block[: next_h2.start()]

        fields: dict[str, str] = {}
        for fm in _FIELD_RE.finditer(block):
            key = fm.group("key").strip().lower()
            if key in _SKIP_KEYS:
                continue
            fields[key] = _clean(fm.group("value"))

        status_raw = fields.get("estado", "")
        actions.append(
            {
                "id": m.group("id"),
                "title": m.group("title").strip(),
                "platform": fields.get("plataforma", ""),
                "motivo": fields.get("motivo", ""),
                "url": fields.get("url", ""),
                "instrucciones": fields.get("instrucciones", ""),
                "que_hace_ownex": fields.get("qué hace ownex después", ""),
                "riesgo": fields.get("riesgo", ""),
                "permisos": fields.get("permisos que solicita", ""),
                "estado": _status_of(status_raw),
                "estado_raw": status_raw,
            }
        )

    return actions


def _parse_phase_tables(text: str) -> list[dict]:
    """Parse '| B6 | acción | plataforma/motivo | estado |' rows per FASE block."""
    actions: list[dict] = []
    phases = list(_PHASE_RE.finditer(text))

    for i, pm in enumerate(phases):
        phase = pm.group("phase")
        start = pm.end()
        end = phases[i + 1].start() if i + 1 < len(phases) else len(text)
        block = text[start:end]

        # Determine column semantics from the table header row.
        header_match = re.search(r"^\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|", block, re.MULTILINE)
        if not header_match:
            continue
        headers = [_clean(h).lower() for h in header_match.groups()]
        # headers like ['#', 'acción', 'plataforma', 'estado'] or ['#', 'acción', 'motivo', 'estado']
        col2_name = headers[2] if len(headers) > 2 else ""
        third_is_platform = "plataforma" in col2_name

        for rm in _TABLE_ROW_RE.finditer(block):
            row_id = rm.group("id")
            if not row_id.startswith(phase):
                continue
            cells = [_clean(c) for c in rm.group("rest").split("|")]
            # rest starts after first '|' of the row; split gives the remaining cells
            while cells and cells[-1] == "":
                cells.pop()
            if len(cells) < 3:
                continue
            action_text, third, status_raw = cells[0], cells[1], cells[2] if len(cells) > 2 else ""
            # For 4-col rows: cells = [acción, plataforma/motivo, estado]; status is last
            status_raw = cells[-1]
            action_text = cells[0]
            third = cells[1] if len(cells) >= 2 else ""

            entry = {
                "id": row_id,
                "title": action_text,
                "estado": _status_of(status_raw),
                "estado_raw": status_raw,
            }
            if third_is_platform:
                entry["platform"] = third
            else:
                entry["motivo"] = third
            actions.append(entry)

    return actions


@router.get("")
def list_human_actions() -> dict:
    """Return all pending human actions parsed from FINAL_HUMAN_ACTIONS.md."""
    if not _DOC_PATH.exists():
        return {"doc": "docs/FINAL_HUMAN_ACTIONS.md", "total": 0, "actions": []}

    text = _DOC_PATH.read_text(encoding="utf-8")
    actions = _parse_detail_sections(text) + _parse_phase_tables(text)
    # Stable order by id.
    actions.sort(key=lambda a: a["id"])

    return {
        "doc": "docs/FINAL_HUMAN_ACTIONS.md",
        "total": len(actions),
        "blocked_on_user": sum(1 for a in actions if a["estado"] == "BLOCKED_ON_USER"),
        "ready_for_authorization": sum(1 for a in actions if a["estado"] == "READY_FOR_AUTHORIZATION"),
        "blocked_on_platform": sum(1 for a in actions if a["estado"] == "BLOCKED_ON_PLATFORM"),
        "completed": sum(1 for a in actions if a["estado"] == "COMPLETED"),
        "actions": actions,
    }
