"""KYC Manager — tracks verification status per platform."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from core.financial_hub.models import KYCRecord
from database.db import SessionLocal

# Default KYC information for each major platform
_DEFAULT_KYC: dict[str, dict[str, Any]] = {
    "hackerone": {
        "platform_name": "HackerOne",
        "kyc_level": "dni",
        "documents_required": ["Government ID", "W-8BEN (US tax form for Argentina)"],
    },
    "bugcrowd": {
        "platform_name": "Bugcrowd",
        "kyc_level": "dni",
        "documents_required": ["Government ID"],
    },
    "intigriti": {
        "platform_name": "Intigriti",
        "kyc_level": "dni",
        "documents_required": ["Government ID", "Bank verification"],
    },
    "synack": {
        "platform_name": "Synack",
        "kyc_level": "passport",
        "documents_required": ["Passport", "W-8BEN"],
    },
    "yeswehack": {
        "platform_name": "YesWeHack",
        "kyc_level": "dni",
        "documents_required": ["Government ID"],
    },
    "immunefi": {
        "platform_name": "Immunefi",
        "kyc_level": "none",
        "documents_required": [],
    },
    "code4rena": {
        "platform_name": "Code4rena",
        "kyc_level": "none",
        "documents_required": [],
    },
    "huntr": {
        "platform_name": "Huntr",
        "kyc_level": "dni",
        "documents_required": ["Government ID"],
    },
}

KYC_STATUSES = ["not_started", "in_progress", "completed", "expired", "failed"]


class KYCManager:
    """Manages KYC verification status across all platforms."""

    def get_all(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            records = session.query(KYCRecord).order_by(KYCRecord.platform).all()
            return [self._record_to_dict(r) for r in records]
        finally:
            session.close()

    def get(self, platform: str) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            record = session.query(KYCRecord).filter_by(platform=platform.lower()).first()
            if record is None:
                return None
            return self._record_to_dict(record)
        finally:
            session.close()

    def upsert(
        self,
        platform: str,
        status: str | None = None,
        documents_submitted: list[str] | None = None,
        notes: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> dict[str, Any]:
        session = SessionLocal()
        try:
            record = session.query(KYCRecord).filter_by(platform=platform.lower()).first()

            if record is None:
                defaults = _DEFAULT_KYC.get(platform.lower(), {})
                record = KYCRecord(
                    platform=platform.lower(),
                    platform_name=defaults.get("platform_name", platform),
                    kyc_level=defaults.get("kyc_level", ""),
                    documents_required=json.dumps(defaults.get("documents_required", [])),
                    documents_submitted="[]",
                )
                session.add(record)

            if status is not None:
                if status not in KYC_STATUSES:
                    raise ValueError(f"Invalid KYC status: {status}. Must be one of {KYC_STATUSES}")
                record.status = status

            if documents_submitted is not None:
                record.documents_submitted = json.dumps(documents_submitted)

            if notes is not None:
                record.notes = notes

            if started_at is not None:
                record.started_at = datetime.fromisoformat(started_at)

            if completed_at is not None:
                record.completed_at = datetime.fromisoformat(completed_at)

            session.commit()
            session.refresh(record)
            return self._record_to_dict(record)
        finally:
            session.close()

    def get_summary(self) -> dict[str, Any]:
        session = SessionLocal()
        try:
            records = session.query(KYCRecord).all()
            total = len(records)
            completed = sum(1 for r in records if r.status == "completed")
            in_progress = sum(1 for r in records if r.status == "in_progress")
            not_started = sum(1 for r in records if r.status == "not_started")
            failed = sum(1 for r in records if r.status == "failed")
            expired = sum(1 for r in records if r.status == "expired")

            return {
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "not_started": not_started,
                "failed": failed,
                "expired": expired,
                "progress_pct": round(completed / total * 100, 1) if total > 0 else 0.0,
            }
        finally:
            session.close()

    def initialize_defaults(self) -> int:
        """Populate default KYC records for all known platforms if not existing."""
        session = SessionLocal()
        try:
            created = 0
            for platform, info in _DEFAULT_KYC.items():
                existing = session.query(KYCRecord).filter_by(platform=platform).first()
                if existing is None:
                    record = KYCRecord(
                        platform=platform,
                        platform_name=info["platform_name"],
                        kyc_level=info["kyc_level"],
                        documents_required=json.dumps(info["documents_required"]),
                        documents_submitted="[]",
                    )
                    session.add(record)
                    created += 1
            if created:
                session.commit()
            return created
        finally:
            session.close()

    def _record_to_dict(self, record: KYCRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "platform": record.platform,
            "platform_name": record.platform_name,
            "status": record.status,
            "kyc_level": record.kyc_level,
            "documents_required": json.loads(record.documents_required) if record.documents_required else [],
            "documents_submitted": json.loads(record.documents_submitted) if record.documents_submitted else [],
            "notes": record.notes,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
