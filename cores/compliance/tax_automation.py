"""Tax/Compliance Automation — W-8BEN, AFIP facturas, 1099, etc.

Handles tax form generation, compliance tracking, and filing automation
for international income (US, AR, etc.).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger("ownex.compliance.tax")


# ─── Tax Form Types ───


class TaxFormType(StrEnum):
    W8BEN = "w8ben"  # US: Foreign person beneficial owner
    W8BENE = "w8bene"  # US: Foreign entity beneficial owner
    W9 = "w9"  # US: Request for TIN
    FORM_1099_NEC = "1099_nec"  # US: Non-employee compensation
    FORM_1099_MISC = "1099_misc"  # US: Miscellaneous income
    AFIP_FACTURA_A = "afip_factura_a"  # AR: Factura A (IVA discriminado)
    AFIP_FACTURA_B = "afip_factura_b"  # AR: Factura B (sin IVA discriminado)
    AFIP_FACTURA_C = "afip_factura_c"  # AR: Factura C (consumidor final)
    AFIP_NOTA_CREDITO = "afip_nota_credito"  # AR: Nota de crédito
    AFIP_NOTA_DEBITO = "afip_nota_debito"  # AR: Nota de débito


class TaxJurisdiction(StrEnum):
    US = "us"
    AR = "ar"
    EU = "eu"
    UK = "uk"
    CA = "ca"


class FilingStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ─── Data Models ───


@dataclass
class TaxProfile:
    """User's tax profile for form generation."""

    # Personal
    full_name: str
    citizenship: str
    tax_residence: str
    permanent_address: str
    mailing_address: str | None = None

    # US Tax
    us_tin: str | None = None  # SSN or ITIN
    us_ein: str | None = None  # EIN for entities
    ftin: str | None = None  # Foreign TIN

    # AR Tax
    cuit: str | None = None  # CUIT/CUIL for Argentina
    iva_condition: str | None = None  # Responsable Inscripto, Monotributo, etc.
    iibb_number: str | None = None  # Ingresos Brutos

    # Business
    business_name: str | None = None
    entity_type: str = "individual"  # individual, llc, corp, etc.
    business_address: str | None = None

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class TaxForm:
    """A generated tax form."""

    id: str
    form_type: TaxFormType
    jurisdiction: TaxJurisdiction
    profile: TaxProfile
    data: dict[str, Any]  # Form-specific field values
    status: FilingStatus = FilingStatus.DRAFT
    pdf_path: str | None = None
    submitted_at: str | None = None
    accepted_at: str | None = None
    rejection_reason: str | None = None
    tax_year: int = field(default_factory=lambda: datetime.now(UTC).year)
    period: str | None = None  # e.g., "Q1 2026", "Enero 2026"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceDeadline:
    """A tax filing deadline."""

    id: str
    form_type: TaxFormType
    jurisdiction: TaxJurisdiction
    due_date: date
    tax_year: int
    period: str | None = None
    description: str = ""
    is_recurring: bool = False
    recurrence_rule: str | None = None  # e.g., "quarterly", "annual"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class PayoutTaxRecord:
    """Tax record for a payout received."""

    id: str
    platform: str
    amount_usd: float
    currency: str
    received_date: date
    tax_form: TaxFormType | None = None
    withholding_usd: float = 0.0
    net_amount_usd: float = 0.0
    tax_form_id: str | None = None
    status: str = "recorded"  # recorded, form_generated, filed
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ─── Form Generators ───


class TaxFormGenerator:
    """Generates tax forms from profiles and payout data."""

    def __init__(self) -> None:
        self.templates_dir = Path(__file__).parent / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def generate_w8ben(self, profile: TaxProfile, tax_year: int) -> TaxForm:
        """Generate IRS Form W-8BEN."""
        data = {
            "part1": {
                "name": profile.full_name,
                "citizenship": profile.citizenship,
                "permanent_address": profile.permanent_address,
                "mailing_address": profile.mailing_address or profile.permanent_address,
                "us_tin": profile.us_tin,
                "ftin": profile.ftin,
                "reference_number": "",  # Optional
            },
            "part2": {
                "country_of_residence": profile.tax_residence,
                "claiming_treaty_benefits": True,
                "treaty_article": "Article 15",  # Default for independent services
                "withholding_rate": "0%",  # Treaty rate for Argentina-US
            },
            "part3": {
                "notional_principal_contracts": False,
                "certification": True,
            },
        }

        return TaxForm(
            id=f"w8ben_{hashlib.sha256(f'{profile.full_name}{tax_year}'.encode()).hexdigest()[:12]}",
            form_type=TaxFormType.W8BEN,
            jurisdiction=TaxJurisdiction.US,
            profile=profile,
            data=data,
            tax_year=tax_year,
        )

    def generate_w9(self, profile: TaxProfile, tax_year: int) -> TaxForm:
        """Generate IRS Form W-9."""
        data = {
            "name": profile.full_name,
            "business_name": profile.business_name,
            "entity_type": profile.entity_type,
            "address": profile.mailing_address or profile.permanent_address,
            "tin": profile.us_tin or profile.us_ein,
        }

        return TaxForm(
            id=f"w9_{hashlib.sha256(f'{profile.full_name}{tax_year}'.encode()).hexdigest()[:12]}",
            form_type=TaxFormType.W9,
            jurisdiction=TaxJurisdiction.US,
            profile=profile,
            data=data,
            tax_year=tax_year,
        )

    def generate_afip_factura(
        self,
        profile: TaxProfile,
        amount_ars: float,
        concept: str,
        factura_type: TaxFormType = TaxFormType.AFIP_FACTURA_A,
        tax_year: int | None = None,
        period: str | None = None,
    ) -> TaxForm:
        """Generate AFIP Factura (A, B, or C)."""
        if not profile.cuit:
            raise ValueError("CUIT required for AFIP factura")

        tax_year = tax_year or datetime.now(UTC).year
        period = period or date.today().strftime("%B %Y")

        data = {
            "emisor": {
                "cuit": profile.cuit,
                "nombre": profile.full_name or profile.business_name,
                "direccion": profile.permanent_address,
                "condicion_iva": profile.iva_condition,
                "iibb": profile.iibb_number,
            },
            "receptor": {
                "cuit": "20222222222",  # AFIP test CUIT
                "nombre": "Cliente",
                "direccion": "",
                "condicion_iva": "Consumidor Final",
            },
            "factura": {
                "tipo": factura_type.value.split("_")[-1].upper(),
                "punto_venta": 1,
                "numero": 1,
                "fecha": date.today().isoformat(),
                "concepto": concept,
                "importe_total": amount_ars,
                "iva": 0.21 if factura_type == TaxFormType.AFIP_FACTURA_A else 0,
            },
        }

        return TaxForm(
            id=f"afip_{factura_type.value}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            form_type=factura_type,
            jurisdiction=TaxJurisdiction.AR,
            profile=profile,
            data=data,
            tax_year=tax_year,
            period=period,
        )


# ─── Compliance Engine ───


class ComplianceEngine:
    """Tracks tax deadlines and compliance status."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = (
            Path(data_dir)
            if data_dir
            else (
                Path(os.environ.get("OWNEX_DATA_DIR", ""))
                if os.environ.get("OWNEX_DATA_DIR")
                else Path.home() / ".ownex" / "compliance"
            )
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.deadlines_file = self.data_dir / "deadlines.json"
        self.forms_file = self.data_dir / "forms.json"
        self.payouts_file = self.data_dir / "payout_tax_records.json"
        self.profile_file = self.data_dir / "tax_profile.json"

    # ─── Deadlines ───

    def add_deadline(self, deadline: ComplianceDeadline) -> None:
        deadlines = self.get_deadlines()
        deadlines[deadline.id] = deadline.__dict__
        self._save_deadlines(deadlines)

    def get_deadlines(
        self, jurisdiction: TaxJurisdiction | None = None, upcoming_days: int | None = None
    ) -> dict[str, dict]:
        try:
            with open(self.deadlines_file, encoding="utf-8") as f:
                deadlines = json.load(f)
        except Exception:
            return {}

        result = {}
        now = date.today()
        for k, v in deadlines.items():
            if jurisdiction and v.get("jurisdiction") != jurisdiction.value:
                continue
            if upcoming_days:
                due = datetime.fromisoformat(v["due_date"]).date() if isinstance(v["due_date"], str) else v["due_date"]
                if (due - now).days > upcoming_days:
                    continue
            result[k] = v
        return result

    def get_upcoming_deadlines(self, days: int = 30) -> list[ComplianceDeadline]:
        deadlines = self.get_deadlines(upcoming_days=days)
        return [ComplianceDeadline(**v) for v in deadlines.values()]

    # ─── Forms ───

    def save_form(self, form: TaxForm) -> None:
        forms = self.get_forms()
        forms[form.id] = form
        self._save_forms(forms)

    def get_form(self, form_id: str) -> TaxForm | None:
        forms = self.get_forms()
        if form_id in forms:
            return forms[form_id]
        return None

    @staticmethod
    def _coerce_form(v: dict[str, Any]) -> TaxForm:
        """Rebuild TaxForm from a JSON dict (nested profile)."""
        data = dict(v)
        profile_data = data.get("profile")
        if isinstance(profile_data, dict):
            data["profile"] = TaxProfile(**profile_data)
        return TaxForm(**data)

    def get_forms(
        self, form_type: TaxFormType | None = None, jurisdiction: TaxJurisdiction | None = None
    ) -> dict[str, TaxForm]:
        try:
            with open(self.forms_file, encoding="utf-8") as f:
                forms = json.load(f)
        except Exception:
            return {}

        result = {}
        for k, v in forms.items():
            if form_type and v.get("form_type") != form_type.value:
                continue
            if jurisdiction and v.get("jurisdiction") != jurisdiction.value:
                continue
            result[k] = self._coerce_form(v)
        return result

    # ─── Payout Tax Records ───

    def record_payout(self, record: PayoutTaxRecord) -> None:
        records = self.get_payout_records()
        records[record.id] = record
        self._save_payouts(records)

    @staticmethod
    def _coerce_payout(v: dict[str, Any]) -> PayoutTaxRecord:
        data = dict(v)
        rd = data.get("received_date")
        if isinstance(rd, str):
            data["received_date"] = datetime.fromisoformat(rd).date()
        tax_form = data.get("tax_form")
        if isinstance(tax_form, dict):
            data["tax_form"] = tax_form.get("value") or next(iter(tax_form.values()), None)
        return PayoutTaxRecord(**data)

    def get_payout_records(
        self,
        platform: str | None = None,
        year: int | None = None,
    ) -> dict[str, PayoutTaxRecord]:
        try:
            with open(self.payouts_file, encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            return {}

        result = {}
        for k, v in records.items():
            if platform and v.get("platform") != platform:
                continue
            if year:
                received = (
                    datetime.fromisoformat(v["received_date"]).date()
                    if isinstance(v["received_date"], str)
                    else v["received_date"]
                )
                if received.year != year:
                    continue
            result[k] = self._coerce_payout(v)
        return result

    def get_tax_summary(self, year: int | None = None) -> dict[str, Any]:
        records = self.get_payout_records(year=year)
        total_gross = sum(r.amount_usd for r in records.values())
        total_withholding = sum(r.withholding_usd for r in records.values())
        total_net = sum(r.net_amount_usd for r in records.values())
        by_platform: dict[str, float] = {}
        for r in records.values():
            by_platform[r.platform] = by_platform.get(r.platform, 0) + r.net_amount_usd

        return {
            "year": year or datetime.now(UTC).year,
            "total_gross_usd": round(total_gross, 2),
            "total_withholding_usd": round(total_withholding, 2),
            "total_net_usd": round(total_net, 2),
            "by_platform": by_platform,
            "record_count": len(records),
        }

    # ─── Profile ───

    def save_profile(self, profile: TaxProfile) -> None:
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(profile.__dict__, f, indent=2, ensure_ascii=False, default=str)

    def get_profile(self) -> TaxProfile | None:
        try:
            with open(self.profile_file, encoding="utf-8") as f:
                return TaxProfile(**json.load(f))
        except Exception:
            return None

    # ─── Persistence ───

    @staticmethod
    def _dump(obj: Any) -> Any:
        """JSON-safe: dataclasses → dict, dates → ISO, enums → value."""
        from dataclasses import is_dataclass
        from enum import Enum

        if is_dataclass(obj):
            return {k: ComplianceEngine._dump(v) for k, v in obj.__dict__.items()}
        if isinstance(obj, dict):
            return {k: ComplianceEngine._dump(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [ComplianceEngine._dump(v) for v in obj]
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return obj

    def _save_deadlines(self, deadlines: dict[str, Any]) -> None:
        with open(self.deadlines_file, "w", encoding="utf-8") as f:
            json.dump(self._dump(deadlines), f, indent=2, ensure_ascii=False)

    def _save_forms(self, forms: dict[str, Any]) -> None:
        with open(self.forms_file, "w", encoding="utf-8") as f:
            json.dump(self._dump(forms), f, indent=2, ensure_ascii=False)

    def _save_payouts(self, records: dict[str, Any]) -> None:
        with open(self.payouts_file, "w", encoding="utf-8") as f:
            json.dump(self._dump(records), f, indent=2, ensure_ascii=False)

    # ─── Default Deadlines ───

    def seed_default_deadlines(self) -> None:
        """Seed default recurring deadlines for US and AR."""
        defaults = [
            # US Quarterly Estimated Tax
            ComplianceDeadline(
                id="us_estimated_q1",
                form_type=TaxFormType.FORM_1099_NEC,
                jurisdiction=TaxJurisdiction.US,
                due_date=date(datetime.now().year, 4, 15),
                tax_year=datetime.now().year,
                period="Q1",
                description="US Quarterly Estimated Tax Payment",
                is_recurring=True,
                recurrence_rule="quarterly",
            ),
            ComplianceDeadline(
                id="us_estimated_q2",
                form_type=TaxFormType.FORM_1099_NEC,
                jurisdiction=TaxJurisdiction.US,
                due_date=date(datetime.now().year, 6, 15),
                tax_year=datetime.now().year,
                period="Q2",
                description="US Quarterly Estimated Tax Payment",
                is_recurring=True,
                recurrence_rule="quarterly",
            ),
            ComplianceDeadline(
                id="us_estimated_q3",
                form_type=TaxFormType.FORM_1099_NEC,
                jurisdiction=TaxJurisdiction.US,
                due_date=date(datetime.now().year, 9, 15),
                tax_year=datetime.now().year,
                period="Q3",
                description="US Quarterly Estimated Tax Payment",
                is_recurring=True,
                recurrence_rule="quarterly",
            ),
            ComplianceDeadline(
                id="us_estimated_q4",
                form_type=TaxFormType.FORM_1099_NEC,
                jurisdiction=TaxJurisdiction.US,
                due_date=date(datetime.now().year + 1, 1, 15),
                tax_year=datetime.now().year,
                period="Q4",
                description="US Quarterly Estimated Tax Payment",
                is_recurring=True,
                recurrence_rule="quarterly",
            ),
            # US Annual
            ComplianceDeadline(
                id="us_1099_nec",
                form_type=TaxFormType.FORM_1099_NEC,
                jurisdiction=TaxJurisdiction.US,
                due_date=date(datetime.now().year, 1, 31),
                tax_year=datetime.now().year - 1,
                description="Form 1099-NEC filing deadline",
                is_recurring=True,
                recurrence_rule="annual",
            ),
            ComplianceDeadline(
                id="us_1099_misc",
                form_type=TaxFormType.FORM_1099_MISC,
                jurisdiction=TaxJurisdiction.US,
                due_date=date(datetime.now().year, 2, 28),
                tax_year=datetime.now().year - 1,
                description="Form 1099-MISC filing deadline",
                is_recurring=True,
                recurrence_rule="annual",
            ),
            # AR Monthly IVA
            ComplianceDeadline(
                id="ar_iva_mensual",
                form_type=TaxFormType.AFIP_FACTURA_A,
                jurisdiction=TaxJurisdiction.AR,
                due_date=date(datetime.now().year, datetime.now().month, 20),
                tax_year=datetime.now().year,
                period=date.today().strftime("%B %Y"),
                description="AFIP IVA Mensual",
                is_recurring=True,
                recurrence_rule="monthly",
            ),
            # AR Annual Ganancias
            ComplianceDeadline(
                id="ar_ganancias_anual",
                form_type=TaxFormType.AFIP_FACTURA_A,
                jurisdiction=TaxJurisdiction.AR,
                due_date=date(datetime.now().year, 6, 30),
                tax_year=datetime.now().year - 1,
                description="AFIP Ganancias Anual (Declaración Jurada)",
                is_recurring=True,
                recurrence_rule="annual",
            ),
        ]

        for deadline in defaults:
            self.add_deadline(deadline)


# ─── Global Instance ───

_compliance_engine: ComplianceEngine | None = None


def get_compliance_engine() -> ComplianceEngine:
    global _compliance_engine
    if _compliance_engine is None:
        _compliance_engine = ComplianceEngine()
        _compliance_engine.seed_default_deadlines()
    return _compliance_engine


# ─── API Functions ───


def get_tax_profile() -> TaxProfile | None:
    return get_compliance_engine().get_profile()


def save_tax_profile(profile: TaxProfile) -> TaxProfile:
    engine = get_compliance_engine()
    profile.updated_at = datetime.now(UTC).isoformat()
    engine.save_profile(profile)
    return profile


def generate_w8ben(tax_year: int | None = None) -> TaxForm:
    engine = get_compliance_engine()
    profile = engine.get_profile()
    if not profile:
        raise HTTPException(status_code=400, detail="Tax profile not configured")
    generator = TaxFormGenerator()
    form = generator.generate_w8ben(profile, tax_year or datetime.now(UTC).year)
    engine.save_form(form)
    return form


def generate_w9(tax_year: int | None = None) -> TaxForm:
    engine = get_compliance_engine()
    profile = engine.get_profile()
    if not profile:
        raise HTTPException(status_code=400, detail="Tax profile not configured")
    generator = TaxFormGenerator()
    form = generator.generate_w9(profile, tax_year or datetime.now(UTC).year)
    engine.save_form(form)
    return form


def generate_afip_factura(
    amount_ars: float,
    concept: str,
    factura_type: TaxFormType = TaxFormType.AFIP_FACTURA_A,
    tax_year: int | None = None,
) -> TaxForm:
    engine = get_compliance_engine()
    profile = engine.get_profile()
    if not profile:
        raise HTTPException(status_code=400, detail="Tax profile not configured")
    if not profile.cuit:
        raise HTTPException(status_code=400, detail="CUIT required for AFIP factura")
    generator = TaxFormGenerator()
    form = generator.generate_afip_factura(profile, amount_ars, concept, factura_type, tax_year)
    engine.save_form(form)
    return form


def get_upcoming_deadlines(days: int = 30) -> list[ComplianceDeadline]:
    return get_compliance_engine().get_upcoming_deadlines(days)


def get_tax_summary(year: int | None = None) -> dict[str, Any]:
    return get_compliance_engine().get_tax_summary(year)


def record_payout_tax(payout: PayoutTaxRecord) -> None:
    get_compliance_engine().record_payout(payout)


def get_payout_records(platform: str | None = None, year: int | None = None) -> dict[str, PayoutTaxRecord]:
    return get_compliance_engine().get_payout_records(platform, year)
