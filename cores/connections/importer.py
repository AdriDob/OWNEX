"""Manual import engine — CSV/JSON/XLSX financial data into OWNEX.

Providers without an authorized API fall back to file import. The engine:
- detects format (csv / json / xlsx when openpyxl is available)
- normalizes rows into a canonical financial record shape
- computes a dedup hash per record (provider + content)
- stores batches with provenance (file hash, provider, timestamp)

Records keep their origin: provider, batch id, source file hash, import
timestamp. No parallel database — batches live under OWNEX data dir.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.env.config import get_config

logger = logging.getLogger("ownex.connections.importer")

MAX_PREVIEW_ROWS = 25
MAX_IMPORT_ROWS = 50_000

# Canonical column aliases -> normalized field. Lowercased, accents stripped.
_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "fecha", "fecha_operacion", "trade_date", "operation_date", "fecha de operacion"),
    "type": ("type", "tipo", "movement_type", "tipo_movimiento", "operation", "operacion"),
    "ticker": ("ticker", "symbol", "simbolo", "instrumento", "instrument", "asset", "activo"),
    "description": ("description", "descripcion", "detail", "detalle", "concepto", "memo"),
    "amount": ("amount", "importe", "monto", "quantity", "cantidad", "qty", "volume"),
    "currency": ("currency", "moneda", "divisa", "coin"),
    "price": ("price", "precio", "unit_price", "precio_unitario"),
    "balance": ("balance", "saldo"),
    "external_id": ("id", "external_id", "operation_id", "movimiento_id", "reference", "referencia"),
}


def _norm_header(h: str) -> str:
    return "".join(c for c in h.strip().lower() if c.isalnum() or c == "_").replace(" ", "_")


def _detect_format(filename: str, content: bytes) -> str:
    name = filename.lower()
    if name.endswith(".json") or content[:1] in (b"{", b"["):
        return "json"
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return "xlsx"
    return "csv"


def _read_rows(fmt: str, content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Return (headers, rows-as-dicts). Raises ValueError on unsupported/empty."""
    if fmt == "json":
        data = json.loads(content.decode("utf-8-sig"))
        if isinstance(data, dict):
            # common export shape: {"movements": [...]} or {"data": [...]}
            for key in ("movements", "data", "operations", "rows", "items"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
            else:
                data = [data]
        if not isinstance(data, list) or not data:
            raise ValueError("JSON sin filas de datos")
        if not all(isinstance(r, dict) for r in data):
            raise ValueError("JSON debe contener una lista de objetos")
        headers = sorted({k for r in data for k in r})
        return headers, [{str(k): ("" if v is None else str(v)) for k, v in r.items()} for r in data]

    if fmt == "xlsx":
        try:
            import openpyxl  # optional dep
        except ImportError as exc:
            raise ValueError("XLSX requiere openpyxl (no instalado)") from exc
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration as exc:
            raise ValueError("XLSX vacío") from exc
        headers = [str(c) if c is not None else f"col_{i}" for i, c in enumerate(header_row)]
        rows = []
        for r in rows_iter:
            if r is None or all(c is None for c in r):
                continue
            rows.append({headers[i]: ("" if v is None else str(v)) for i, v in enumerate(r) if i < len(headers)})
        wb.close()
        return headers, rows

    # csv (also fallback for unknown text exports)
    text = content.decode("utf-8-sig", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = reader.fieldnames or []
    rows = [{(k or ""): (v or "") for k, v in r.items()} for r in reader]
    if not headers:
        raise ValueError("CSV sin encabezados")
    return list(headers), rows


def _normalize_row(row: dict[str, str], mapping: dict[str, str]) -> dict[str, Any]:
    """Map source columns to canonical fields using the proposed mapping."""
    record: dict[str, Any] = {}
    for canon, source_col in mapping.items():
        if source_col and source_col in row:
            record[canon] = row[source_col].strip()
    return record


def _record_hash(provider: str, record: dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, default=str)
    return hashlib.sha256(f"{provider}|{canonical}".encode()).hexdigest()[:16]


def _import_dir(provider: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in provider.lower())
    return get_config().data_dir / "connections" / "imports" / safe


def preview_import(provider: str, filename: str, content: bytes) -> dict[str, Any]:
    """Parse a file and return column mapping proposal + preview rows."""
    fmt = _detect_format(filename, content)
    headers, rows = _read_rows(fmt, content)
    if len(rows) > MAX_IMPORT_ROWS:
        raise ValueError(f"Archivo excede {MAX_IMPORT_ROWS} filas")
    if not rows:
        raise ValueError("Archivo sin filas de datos")

    normalized_headers = {_norm_header(h): h for h in headers}
    mapping: dict[str, str] = {}
    for canon, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized_headers:
                mapping[canon] = normalized_headers[alias]
                break

    preview = [_normalize_row(r, mapping) for r in rows[:MAX_PREVIEW_ROWS]]
    file_hash = hashlib.sha256(content).hexdigest()[:16]

    return {
        "provider": provider,
        "format": fmt,
        "filename": filename,
        "file_hash": file_hash,
        "total_rows": len(rows),
        "headers": headers,
        "mapping": mapping,
        "unmapped_headers": [h for h in headers if h not in mapping.values()],
        "preview": preview,
    }


def confirm_import(
    provider: str,
    filename: str,
    content: bytes,
    mapping: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Persist an import batch with normalized, deduplicated records."""
    fmt = _detect_format(filename, content)
    headers, rows = _read_rows(fmt, content)
    if len(rows) > MAX_IMPORT_ROWS:
        raise ValueError(f"Archivo excede {MAX_IMPORT_ROWS} filas")

    normalized_headers = {_norm_header(h): h for h in headers}
    if mapping is None:
        mapping = {}
        for canon, aliases in _COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in normalized_headers:
                    mapping[canon] = normalized_headers[alias]
                    break
    else:
        # mapping values are canonical->source; validate source cols exist
        mapping = {c: s for c, s in mapping.items() if s in headers}

    batch_id = uuid.uuid4().hex[:12]
    imported_at = datetime.now(UTC).isoformat()
    file_hash = hashlib.sha256(content).hexdigest()

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates = 0
    rejected = 0
    for row in rows:
        rec = _normalize_row(row, mapping)
        if not rec:
            rejected += 1
            continue
        rec["_hash"] = _record_hash(provider, rec)
        if rec["_hash"] in seen:
            duplicates += 1
            continue
        seen.add(rec["_hash"])
        rec.update(
            {
                "provider": provider,
                "batch_id": batch_id,
                "source_file": filename,
                "source_hash": file_hash[:16],
                "imported_at": imported_at,
            }
        )
        records.append(rec)

    batch = {
        "batch_id": batch_id,
        "provider": provider,
        "format": fmt,
        "filename": filename,
        "source_hash": file_hash,
        "imported_at": imported_at,
        "total_rows": len(rows),
        "imported": len(records),
        "duplicates": duplicates,
        "rejected": rejected,
        "mapping": mapping,
        "records": records,
    }

    out_dir = _import_dir(provider)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{batch_id}.json").write_text(json.dumps(batch, indent=2, default=str))
    logger.info(
        "Import confirmed provider=%s batch=%s rows=%d imported=%d dup=%d rejected=%d",
        provider,
        batch_id,
        len(rows),
        len(records),
        duplicates,
        rejected,
    )
    return {k: v for k, v in batch.items() if k != "records"} | {"records_count": len(records)}


def list_imports(provider: str) -> list[dict[str, Any]]:
    """List import batches for a provider (metadata only, no records)."""
    out_dir = _import_dir(provider)
    if not out_dir.exists():
        return []
    batches = []
    for path in sorted(out_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text())
            batches.append({k: v for k, v in data.items() if k != "records"})
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read import batch %s: %s", path, exc)
    return batches[:50]


def load_import_records(provider: str, batch_id: str) -> list[dict[str, Any]]:
    path = _import_dir(provider) / f"{batch_id}.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text()).get("records", [])
    except (json.JSONDecodeError, OSError):
        return []
