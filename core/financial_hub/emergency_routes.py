"""Emergency Routes — backup withdrawal plans when primary routes fail."""

from __future__ import annotations

from typing import Any

from core.financial_hub.models import WithdrawalRoute
from database.db import SessionLocal


class EmergencyRoutes:
    """Manages emergency/backup withdrawal routes."""

    def list_all(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            routes = (
                session.query(WithdrawalRoute)
                .filter_by(is_emergency=True)
                .order_by(WithdrawalRoute.priority.desc())
                .all()
            )
            return [self._route_to_dict(r) for r in routes]
        finally:
            session.close()

    def get_primary_fallback(self) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            route = (
                session.query(WithdrawalRoute)
                .filter_by(is_emergency=True, is_active=True)
                .order_by(WithdrawalRoute.priority.desc())
                .first()
            )
            if route is None:
                return None
            return self._route_to_dict(route)
        finally:
            session.close()

    def get_quickest_emergency(self) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            routes = session.query(WithdrawalRoute).filter_by(is_emergency=True, is_active=True).all()
            if not routes:
                return None

            def _arrival_to_days(d: str) -> int:
                d = d.lower().strip()
                if d == "instantáneo" or d == "mismo día" or d == "1":
                    return 0
                parts = d.split("-")
                try:
                    return int(parts[0])
                except (ValueError, IndexError):
                    return 999

            best = min(routes, key=lambda r: _arrival_to_days(r.arrival_days))
            return self._route_to_dict(best)
        finally:
            session.close()

    def enable(self, route_id: int) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            route = session.query(WithdrawalRoute).filter_by(id=route_id).first()
            if route is None:
                return None
            route.is_active = True
            session.commit()
            session.refresh(route)
            return self._route_to_dict(route)
        finally:
            session.close()

    def disable(self, route_id: int) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            route = session.query(WithdrawalRoute).filter_by(id=route_id).first()
            if route is None:
                return None
            route.is_active = False
            session.commit()
            session.refresh(route)
            return self._route_to_dict(route)
        finally:
            session.close()

    def _route_to_dict(self, record: WithdrawalRoute) -> dict[str, Any]:
        import json

        return {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "route_type": record.route_type,
            "source_currency": record.source_currency,
            "target_currency": record.target_currency,
            "fee_percent": record.fee_percent,
            "fee_fixed": record.fee_fixed,
            "arrival_days": record.arrival_days,
            "is_active": record.is_active,
            "is_emergency": record.is_emergency,
            "priority": record.priority,
            "steps": json.loads(record.steps) if record.steps else [],
            "requirements": json.loads(record.requirements) if record.requirements else [],
            "notes": record.notes,
        }
