"""Verification Tracker — tracks multi-step verification progress per platform."""

from __future__ import annotations

from typing import Any

from core.financial_hub.models import KYCRecord, PayoutDocument
from database.db import SessionLocal


class VerificationTracker:
    """Tracks overall verification progress across platforms and documents."""

    def get_overall_progress(self) -> dict[str, Any]:
        kyc = self._get_kyc_progress()
        docs = self._get_document_progress()

        total_items = kyc["total"] + docs["total"]
        completed_items = kyc["completed"] + docs["completed"]

        return {
            "overall_progress_pct": round(completed_items / total_items * 100, 1) if total_items > 0 else 0.0,
            "kyc": kyc,
            "documents": docs,
            "total_items": total_items,
            "completed_items": completed_items,
            "pending_items": total_items - completed_items,
        }

    def get_pending_verifications(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            pending: list[dict[str, Any]] = []

            kyc_records = session.query(KYCRecord).filter(KYCRecord.status != "completed").all()
            for r in kyc_records:
                pending.append(
                    {
                        "type": "kyc",
                        "platform": r.platform,
                        "platform_name": r.platform_name,
                        "status": r.status,
                        "description": f"KYC verification for {r.platform_name}",
                    }
                )

            docs = session.query(PayoutDocument).filter_by(is_completed=False).all()
            for d in docs:
                pending.append(
                    {
                        "type": "document",
                        "id": d.id,
                        "name": d.name,
                        "category": d.category,
                        "status": "pending",
                        "description": d.description,
                    }
                )

            return pending
        finally:
            session.close()

    def _get_kyc_progress(self) -> dict[str, Any]:
        session = SessionLocal()
        try:
            records = session.query(KYCRecord).all()
            total = len(records)
            completed = sum(1 for r in records if r.status == "completed")
            return {"total": total, "completed": completed}
        finally:
            session.close()

    def _get_document_progress(self) -> dict[str, Any]:
        session = SessionLocal()
        try:
            docs = session.query(PayoutDocument).all()
            total = len(docs)
            completed = sum(1 for d in docs if d.is_completed)
            return {"total": total, "completed": completed}
        finally:
            session.close()
