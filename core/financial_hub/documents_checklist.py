"""Documents Checklist — tracks required documents for payouts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from core.financial_hub.models import PayoutDocument
from database.db import SessionLocal

_DEFAULT_DOCUMENTS: list[dict[str, Any]] = [
    {
        "name": "DNI (Documento Nacional de Identidad)",
        "description": "Documento de identidad argentino. Necesario para KYC en exchanges y plataformas.",
        "category": "identity",
        "platforms": ["hackerone", "bugcrowd", "intigriti", "yeswehack", "huntr"],
    },
    {
        "name": "Pasaporte",
        "description": "Pasaporte argentino vigente. Requerido para Payoneer y Synack.",
        "category": "identity",
        "platforms": ["synack"],
    },
    {
        "name": "W-8BEN (Formulario IRS)",
        "description": "Formulario de IRS para no-residentes de EE.UU. Exime de retención de impuestos.",
        "category": "tax",
        "platforms": ["hackerone", "bugcrowd", "synack"],
    },
    {
        "name": "CBU / CVU Bancario",
        "description": "Clave Bancaria Universal para recibir transferencias en Argentina.",
        "category": "bank",
        "platforms": [],
    },
    {
        "name": "Cuenta Payoneer",
        "description": "Cuenta virtual en USD. Requiere pasaporte y W-8BEN.",
        "category": "platform",
        "platforms": ["hackerone", "bugcrowd", "synack"],
    },
    {
        "name": "Cuenta Takenos",
        "description": "Cuenta virtual USD con KYC por DNI. Transferencias a CBU argentino.",
        "category": "platform",
        "platforms": [],
    },
    {
        "name": "Cuenta Binance (KYC Nivel 2)",
        "description": "Exchange con KYC completo para P2P trading. DNI + selfie.",
        "category": "crypto",
        "platforms": [],
    },
    {
        "name": "Cuenta Lemon Cash",
        "description": "Exchange argentino. DNI + selfie. Recibir crypto, vender a ARS, retirar.",
        "category": "crypto",
        "platforms": [],
    },
    {
        "name": "Wallet de Solana (Phantom/Backpack)",
        "description": "Wallet para recibir USDC en Solana. Usado por Immunefi, Code4rena.",
        "category": "crypto",
        "platforms": ["immunefi", "code4rena"],
    },
    {
        "name": "Wallet de Ethereum (MetaMask)",
        "description": "Wallet para recibir ETH/USDC en Ethereum. Usado por Immunefi.",
        "category": "crypto",
        "platforms": ["immunefi", "code4rena"],
    },
]


class DocumentsChecklist:
    """Manages the document checklist for payout readiness."""

    def list_all(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            docs = session.query(PayoutDocument).order_by(PayoutDocument.category, PayoutDocument.name).all()
            return [self._doc_to_dict(d) for d in docs]
        finally:
            session.close()

    def get(self, doc_id: int) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            doc = session.query(PayoutDocument).filter_by(id=doc_id).first()
            if doc is None:
                return None
            return self._doc_to_dict(doc)
        finally:
            session.close()

    def mark_completed(self, doc_id: int) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            doc = session.query(PayoutDocument).filter_by(id=doc_id).first()
            if doc is None:
                return None
            doc.is_completed = True
            doc.completed_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(doc)
            return self._doc_to_dict(doc)
        finally:
            session.close()

    def mark_incomplete(self, doc_id: int) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            doc = session.query(PayoutDocument).filter_by(id=doc_id).first()
            if doc is None:
                return None
            doc.is_completed = False
            doc.completed_at = None
            session.commit()
            session.refresh(doc)
            return self._doc_to_dict(doc)
        finally:
            session.close()

    def get_summary(self) -> dict[str, Any]:
        session = SessionLocal()
        try:
            docs = session.query(PayoutDocument).all()
            total = len(docs)
            completed = sum(1 for d in docs if d.is_completed)
            categories: dict[str, dict[str, int]] = {}
            for d in docs:
                cat = d.category
                if cat not in categories:
                    categories[cat] = {"total": 0, "completed": 0}
                categories[cat]["total"] += 1
                if d.is_completed:
                    categories[cat]["completed"] += 1

            return {
                "total": total,
                "completed": completed,
                "pending": total - completed,
                "progress_pct": round(completed / total * 100, 1) if total > 0 else 0.0,
                "by_category": categories,
            }
        finally:
            session.close()

    def initialize_defaults(self) -> int:
        session = SessionLocal()
        try:
            created = 0
            for doc_data in _DEFAULT_DOCUMENTS:
                existing = session.query(PayoutDocument).filter_by(name=doc_data["name"]).first()
                if existing is None:
                    doc = PayoutDocument(
                        name=doc_data["name"],
                        description=doc_data["description"],
                        category=doc_data["category"],
                        platforms=json.dumps(doc_data["platforms"]),
                    )
                    session.add(doc)
                    created += 1
            if created:
                session.commit()
            return created
        finally:
            session.close()

    def _doc_to_dict(self, doc: PayoutDocument) -> dict[str, Any]:
        return {
            "id": doc.id,
            "name": doc.name,
            "description": doc.description,
            "category": doc.category,
            "is_required": doc.is_required,
            "is_completed": doc.is_completed,
            "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
            "notes": doc.notes,
            "platforms": json.loads(doc.platforms) if doc.platforms else [],
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        }
