"""Route Optimizer — finds the best withdrawal route for a given amount and platform."""

from __future__ import annotations

import json
from typing import Any

from core.financial_hub.models import WithdrawalRoute
from database.db import SessionLocal

# Default routes for Argentina
_DEFAULT_ROUTES: list[dict[str, Any]] = [
    {
        "name": "Takenos → CBU (Banco Argentino)",
        "description": "Recibir USD en Takenos, transferir a banco argentino vía CBU",
        "route_type": "wallet",
        "source_currency": "USD",
        "target_currency": "ARS",
        "fee_percent": 1.0,
        "fee_fixed": 0.0,
        "arrival_days": "1-2",
        "is_emergency": False,
        "priority": 10,
        "steps": [
            "Recibir el pago en Takenos (cuenta virtual USD)",
            "Solicitar transferencia a CBU argentino desde Takenos",
            "El banco recibe ARS al tipo de cambio de Takenos",
            "Los fondos están disponibles en tu cuenta bancaria",
        ],
        "requirements": ["Cuenta Takenos con KYC completo", "CBU de banco argentino"],
        "notes": "Opción más directa. Takenos convierte USD a ARS automáticamente.",
    },
    {
        "name": "Crypto P2P → Binance → ARS",
        "description": "Recibir USDC/USDT, enviar a Binance, vender por P2P a ARS",
        "route_type": "p2p",
        "source_currency": "USD",
        "target_currency": "ARS",
        "fee_percent": 0.0,
        "fee_fixed": 0.0,
        "arrival_days": "mismo día",
        "is_emergency": False,
        "priority": 9,
        "steps": [
            "Recibir USDC/USDT en tu wallet de Binance (u otro exchange)",
            "Publicar orden P2P en Binance para vender USDC/USDT por ARS",
            "Recibir ARS por transferencia bancaria del comprador",
            "Fondos disponibles en tu cuenta bancaria argentina",
        ],
        "requirements": ["Cuenta Binance con KYC completo", "Wallet de Binance configurada"],
        "notes": "Mejor tasa de cambio. Sin comisiones. Requiere entender P2P trading.",
    },
    {
        "name": "Payoneer → Extracción a Banco Argentino",
        "description": "Recibir en Payoneer, retirar a banco argentino",
        "route_type": "bank_transfer",
        "source_currency": "USD",
        "target_currency": "ARS",
        "fee_percent": 2.0,
        "fee_fixed": 1.5,
        "arrival_days": "2-5",
        "is_emergency": False,
        "priority": 7,
        "steps": [
            "Recibir el pago en Payoneer (cuenta virtual USD)",
            "Solicitar retiro a cuenta bancaria argentina desde Payoneer",
            "Payoneer convierte USD a ARS y transfiere vía SWIFT/local",
            "Los fondos llegan a tu banco argentino en 2-5 días hábiles",
        ],
        "requirements": ["Cuenta Payoneer con KYC (pasaporte)", "CBU de banco argentino", "W-8BEN firmado"],
        "notes": "Requiere pasaporte (no solo DNI). Comisiones moderadas.",
    },
    {
        "name": "PayPal → Lemon Cash → ARS",
        "description": "Recibir por PayPal, pasar a Lemon Cash, retirar a banco",
        "route_type": "crypto_exchange",
        "source_currency": "USD",
        "target_currency": "ARS",
        "fee_percent": 4.4,
        "fee_fixed": 0.0,
        "arrival_days": "1-2",
        "is_emergency": True,
        "priority": 5,
        "steps": [
            "Recibir el pago en PayPal",
            "Transferir de PayPal a Lemon Cash (conversión a USDC)",
            "Vender USDC por ARS en Lemon Cash",
            "Retirar ARS a tu banco argentino vía transferencia",
        ],
        "requirements": ["Cuenta PayPal verificada", "Cuenta Lemon Cash con KYC (DNI)"],
        "notes": "PayPal cobra 4.4% de comisión. Usar solo si no hay alternativa.",
    },
    {
        "name": "Crypto Directo → Exchange Argentino",
        "description": "Recibir crypto directo a Lemon/Belo, vender a ARS, retirar",
        "route_type": "crypto_exchange",
        "source_currency": "USD",
        "target_currency": "ARS",
        "fee_percent": 0.0,
        "fee_fixed": 0.0,
        "arrival_days": "instantáneo",
        "is_emergency": False,
        "priority": 8,
        "steps": [
            "Recibir USDC/USDT directo a tu wallet de Lemon Cash o Belo",
            "Vender crypto por ARS dentro de la app",
            "Transferir ARS a tu cuenta bancaria",
        ],
        "requirements": ["Cuenta Lemon Cash o Belo con KYC (DNI)"],
        "notes": "Ideal para Immunefi/Code4rena. Sin comisiones de por medio.",
    },
]


class RouteOptimizer:
    """Finds and ranks optimal withdrawal routes for given parameters."""

    def list_routes(self, include_emergency: bool = False) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            query = session.query(WithdrawalRoute).order_by(WithdrawalRoute.priority.desc())
            if not include_emergency:
                query = query.filter_by(is_emergency=False)
            records = query.all()

            if not records:
                return []
            return [self._route_to_dict(r) for r in records]
        finally:
            session.close()

    def get_route(self, route_id: int) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            record = session.query(WithdrawalRoute).filter_by(id=route_id).first()
            if record is None:
                return None
            return self._route_to_dict(record)
        finally:
            session.close()

    def calculate_optimal(self, amount_usd: float, source_platform: str) -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            routes = (
                session.query(WithdrawalRoute).filter_by(is_active=True).order_by(WithdrawalRoute.priority.desc()).all()
            )
            results: list[dict[str, Any]] = []

            for route in routes:
                total_fee = amount_usd * (route.fee_percent / 100.0) + route.fee_fixed
                net = amount_usd - total_fee
                results.append(
                    {
                        "route_id": route.id,
                        "name": route.name,
                        "description": route.description,
                        "type": route.route_type,
                        "fee_percent": route.fee_percent,
                        "fee_fixed": route.fee_fixed,
                        "total_fee_usd": round(total_fee, 2),
                        "net_amount_usd": round(net, 2),
                        "arrival_days": route.arrival_days,
                        "is_emergency": route.is_emergency,
                        "priority": route.priority,
                        "steps": json.loads(route.steps) if route.steps else [],
                        "requirements": json.loads(route.requirements) if route.requirements else [],
                    }
                )

            results.sort(key=lambda r: (r["is_emergency"], -r["priority"]))

            return results
        finally:
            session.close()

    def initialize_defaults(self) -> int:
        session = SessionLocal()
        try:
            created = 0
            for route_data in _DEFAULT_ROUTES:
                existing = session.query(WithdrawalRoute).filter_by(name=route_data["name"]).first()
                if existing is None:
                    record = WithdrawalRoute(
                        name=route_data["name"],
                        description=route_data["description"],
                        route_type=route_data["route_type"],
                        source_currency=route_data["source_currency"],
                        target_currency=route_data["target_currency"],
                        fee_percent=route_data["fee_percent"],
                        fee_fixed=route_data["fee_fixed"],
                        arrival_days=route_data["arrival_days"],
                        is_emergency=route_data["is_emergency"],
                        priority=route_data["priority"],
                        steps=json.dumps(route_data["steps"]),
                        requirements=json.dumps(route_data["requirements"]),
                        notes=route_data.get("notes", ""),
                    )
                    session.add(record)
                    created += 1
            if created:
                session.commit()
            return created
        finally:
            session.close()

    def _route_to_dict(self, record: WithdrawalRoute) -> dict[str, Any]:
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
