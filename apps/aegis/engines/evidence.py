"""Evidence Engine — collects, stores, and organizes proof of exploitation."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.database.manager import get_db_manager

logger = logging.getLogger("orion.aegis.engines.evidence")

EVIDENCE_DIR = Path.home() / ".orion" / "aegis_evidence"


class EvidenceEngine:
    """Manages evidence artifacts: screenshots, request/response pairs, logs."""

    def __init__(self) -> None:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    async def store(self, finding_id: int, content: bytes, filename: str, mime: str = "text/plain") -> dict[str, Any]:
        """Store an evidence artifact."""
        sha256 = hashlib.sha256(content).hexdigest()
        safe_name = f"{finding_id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{filename}"
        path = EVIDENCE_DIR / safe_name
        path.write_bytes(content)

        db = get_db_manager().get_session("aegis")
        try:
            from apps.aegis.models import ScanResult

            db.execute(
                ScanResult.__table__.update()
                .where(ScanResult.id == finding_id)
                .values(evidence=f"stored:{path.name}:{sha256}")
            )
            db.commit()
        finally:
            db.close()

        return {
            "path": str(path),
            "size": len(content),
            "sha256": sha256,
            "mime": mime,
        }

    async def get(self, finding_id: int) -> list[dict]:
        """List evidence for a finding."""
        path = EVIDENCE_DIR
        files = []
        for f in sorted(path.glob(f"{finding_id}_*")):
            files.append(
                {
                    "filename": f.name,
                    "size": f.stat().st_size,
                }
            )
        return files
