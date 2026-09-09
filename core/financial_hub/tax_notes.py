"""Tax Notes — tax reference information for bug bounty income in Argentina."""

from __future__ import annotations

import json
from typing import Any

from core.financial_hub.models import TaxRecord
from database.db import SessionLocal

# Tax reference data for Argentina and common scenarios
_DEFAULT_TAX_NOTES: list[dict[str, Any]] = [
    {
        "country": "AR",
        "title": "Impuesto a las Ganancias — Personas Físicas",
        "description": (
            "Los ingresos por bug bounty están sujetos a Impuesto a las Ganancias en Argentina "
            "si superan el mínimo no imponible (aproximadamente $2.5M ARS anuales, actualizable). "
            "Se declaran como 'ganancias de fuente extranjera' si la plataforma está fuera del país. "
            "Se recomienda consultar con un contador para determinar si corresponde el pago."
        ),
        "category": "general",
        "platforms": ["hackerone", "bugcrowd", "intigriti", "synack", "yeswehack", "immunefi", "code4rena", "huntr"],
    },
    {
        "country": "AR",
        "title": "Bienes Personales — Criptoactivos",
        "description": (
            "Los criptoactivos (USDC, USDT, ETH, BTC) están sujetos al impuesto de Bienes Personales "
            "si el total de tus bienes supera el mínimo exento. Se declaran al 31/12 de cada año "
            "al valor de mercado en USD (tipo de cambio oficial). "
            "A partir de 2023, rigen nuevas alícuotas progresivas."
        ),
        "category": "regulation",
        "platforms": ["immunefi", "code4rena"],
    },
    {
        "country": "AR",
        "title": "W-8BEN — Exención de Retención IRS",
        "description": (
            "El W-8BEN es un formulario del IRS de EE.UU. que certifica que no eres residente fiscal "
            "estadounidense. Sin este formulario, las plataformas estadounidenses (HackerOne, Bugcrowd) "
            "te retendrán el 24-30% del pago. "
            "Se renueva cada 3 años. Se puede presentar electrónicamente en cada plataforma."
        ),
        "category": "form",
        "platforms": ["hackerone", "bugcrowd", "synack"],
    },
    {
        "country": "AR",
        "title": "Facturación Electrónica — ARCA (ex AFIP)",
        "description": (
            "Al recibir pagos del exterior, puede ser necesario emitir factura electrónica "
            "a través de ARCA (ex AFIP). El tipo de factura depende de tu situación fiscal: "
            "Factura E (exportación de servicios) si estás registrado como exportador de servicios, "
            "o Factura C si eres responsable inscripto. "
            "Es recomendable estar registrado en el impuesto a las ganancias y tener CUIT activa."
        ),
        "category": "regulation",
        "platforms": ["hackerone", "bugcrowd", "intigriti", "synack", "yeswehack", "immunefi", "code4rena", "huntr"],
    },
    {
        "country": "AR",
        "title": "Régimen Simplificado (Monotributo) vs General",
        "description": (
            "Los ingresos en USD por bug bounty pueden hacer que no encajes en Monotributo "
            "(límite de facturación anual ~$16M ARS en 2024). "
            "Si superás el límite, deberás migrar al Régimen General (Responsable Inscripto). "
            "Monotributo tiene un componente impositivo fijo mensual. "
            "El RG requiere liquidación de IVA y Ganancias mensual/anual."
        ),
        "category": "general",
        "platforms": [],
    },
    {
        "country": "AR",
        "title": "Ingreso de Divisas — BCRA",
        "description": (
            "Si convertís USD a ARS a través del sistema bancario formal (CBU), "
            "el banco puede requerir declaración de origen de fondos. "
            "El cupo para compra de USD ahorro/turista aplica sobre ingresos declarados. "
            "Las transferencias del exterior pueden estar sujetas a plazos de liquidación (5 días hábiles)."
        ),
        "category": "regulation",
        "platforms": [],
    },
    {
        "country": "AR",
        "title": "Crypto — Tratamiento Fiscal",
        "description": (
            "La venta de criptoactivos (USDC→ARS) está gravada por Ganancias si hay ganancia. "
            "La tenencia no es hecho imponible (solo la venta). "
            "Las operaciones P2P no declaradas pueden generar riesgo fiscal. "
            "Se recomienda mantener registro de todas las operaciones: fecha, monto, contraparte, tasa."
        ),
        "category": "regulation",
        "platforms": ["immunefi", "code4rena"],
    },
    {
        "country": "AR",
        "title": "Plazos de Declaración Jurada",
        "description": (
            "Ganancias: presentación anual entre abril-junio del año siguiente. "
            "Bienes Personales: presentación anual (mismo período que Ganancias). "
            "IVA: mensual si estás en RG. "
            "Si no presentaste años anteriores, hay planes de regularización."
        ),
        "category": "deadline",
        "platforms": [],
    },
    {
        "country": "AR",
        "title": "Exención por Menor Cuantía",
        "description": (
            "Si tus ingresos totales (incluyendo bug bounty) no superan el mínimo no imponible "
            "de Ganancias, no estás obligado a presentar declaración jurada. "
            "Sin embargo, si tenés bienes que superan el mínimo de Bienes Personales, "
            "puede ser necesario igualmente."
        ),
        "category": "exemption",
        "platforms": [],
    },
]


class TaxNotes:
    """Reference information about tax obligations for bug bounty income."""

    def list_all(self, country: str = "AR") -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            records = session.query(TaxRecord).filter_by(country=country.upper(), is_active=True).all()
            return [self._record_to_dict(r) for r in records]
        finally:
            session.close()

    def get(self, record_id: int) -> dict[str, Any] | None:
        session = SessionLocal()
        try:
            record = session.query(TaxRecord).filter_by(id=record_id).first()
            if record is None:
                return None
            return self._record_to_dict(record)
        finally:
            session.close()

    def by_category(self, country: str = "AR") -> dict[str, list[dict[str, Any]]]:
        records = self.list_all(country)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for r in records:
            cat = r["category"]
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(r)
        return grouped

    def for_platform(self, platform_id: str, country: str = "AR") -> list[dict[str, Any]]:
        session = SessionLocal()
        try:
            records = session.query(TaxRecord).filter_by(country=country.upper(), is_active=True).all()
            result: list[dict[str, Any]] = []
            for r in records:
                platforms = json.loads(r.platforms) if r.platforms else []
                if not platforms or platform_id.lower() in [p.lower() for p in platforms]:
                    result.append(self._record_to_dict(r))
            return result
        finally:
            session.close()

    def initialize_defaults(self) -> int:
        session = SessionLocal()
        try:
            created = 0
            for note_data in _DEFAULT_TAX_NOTES:
                existing = session.query(TaxRecord).filter_by(title=note_data["title"]).first()
                if existing is None:
                    record = TaxRecord(
                        country=note_data["country"],
                        title=note_data["title"],
                        description=note_data["description"],
                        category=note_data["category"],
                        platforms=json.dumps(note_data["platforms"]),
                    )
                    session.add(record)
                    created += 1
            if created:
                session.commit()
            return created
        finally:
            session.close()

    def _record_to_dict(self, record: TaxRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "country": record.country,
            "title": record.title,
            "description": record.description,
            "category": record.category,
            "platforms": json.loads(record.platforms) if record.platforms else [],
            "reference_url": record.reference_url,
            "is_active": record.is_active,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
