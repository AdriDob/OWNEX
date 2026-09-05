"""Tests for Tax/Compliance Automation (cores/compliance/tax_automation.py)."""

from __future__ import annotations

import pytest

from cores.compliance.tax_automation import (
    ComplianceEngine,
    PayoutTaxRecord,
    TaxFormGenerator,
    TaxFormType,
    TaxJurisdiction,
    TaxProfile,
)


@pytest.fixture()
def profile():
    return TaxProfile(
        full_name="Adriel Dobrzycki",
        citizenship="Argentina",
        tax_residence="Argentina",
        permanent_address="Buenos Aires, Argentina",
        ftin="20-12345678-9",
        cuit="20-12345678-9",
        iva_condition="Responsable Inscripto",
    )


@pytest.fixture()
def engine(tmp_path):
    return ComplianceEngine(data_dir=tmp_path)


def test_generate_w8ben(profile):
    form = TaxFormGenerator().generate_w8ben(profile, 2026)
    assert form.form_type == TaxFormType.W8BEN
    assert form.jurisdiction == TaxJurisdiction.US
    assert form.data["part1"]["name"] == profile.full_name


def test_generate_w9(profile):
    form = TaxFormGenerator().generate_w9(profile, 2026)
    assert form.form_type == TaxFormType.W9
    assert form.data["name"] == profile.full_name


def test_generate_afip_factura(profile):
    form = TaxFormGenerator().generate_afip_factura(
        profile, 1000.0, "Servicios de investigación", TaxFormType.AFIP_FACTURA_A, 2026
    )
    assert form.jurisdiction == TaxJurisdiction.AR
    assert form.data["factura"]["punto_venta"] == 1


def test_generate_afip_factura_requires_cuit(engine):
    without_cuit = TaxProfile(full_name="X", citizenship="AR", tax_residence="AR", permanent_address="addr")
    with pytest.raises(ValueError):
        TaxFormGenerator().generate_afip_factura(without_cuit, 100.0, "c")


def test_save_and_load_form(engine, profile):
    form = TaxFormGenerator().generate_w8ben(profile, 2026)
    engine.save_form(form)
    loaded = engine.get_form(form.id)
    assert loaded is not None
    assert loaded.form_type == TaxFormType.W8BEN


def test_record_payout_and_summary(engine):
    from datetime import date

    engine.record_payout(
        PayoutTaxRecord(
            id="p1",
            platform="hackerone",
            amount_usd=1000.0,
            currency="USD",
            received_date=date(2026, 8, 30),
            withholding_usd=100.0,
            net_amount_usd=900.0,
        )
    )
    engine.record_payout(
        PayoutTaxRecord(
            id="p2",
            platform="bugcrowd",
            amount_usd=500.0,
            currency="USD",
            received_date=date(2026, 8, 30),
            net_amount_usd=500.0,
        )
    )
    summary = engine.get_tax_summary(year=2026)
    assert summary["total_gross_usd"] == 1500.0
    assert summary["total_net_usd"] == 900.0 + 500.0
    assert summary["record_count"] == 2


def test_profile_persistence(engine, profile):
    engine.save_profile(profile)
    loaded = engine.get_profile()
    assert loaded is not None
    assert loaded.full_name == profile.full_name


def test_seed_default_deadlines(engine):
    engine.seed_default_deadlines()
    deadlines = engine.get_upcoming_deadlines(days=365)
    ids = {d.id for d in deadlines}
    assert "us_1099_nec" in ids
    assert "ar_ganancias_anual" in ids


def test_add_custom_deadline(engine):
    from datetime import date

    from cores.compliance.tax_automation import ComplianceDeadline

    deadline = ComplianceDeadline(
        id="eu_vat_q2",
        form_type=TaxFormType.AFIP_FACTURA_A,
        jurisdiction=TaxJurisdiction.EU,
        due_date=date(2026, 7, 31),
        tax_year=2026,
        period="Q2",
        description="EU VAT quarter",
    )
    engine.add_deadline(deadline)
    assert "eu_vat_q2" in engine.get_deadlines(jurisdiction=TaxJurisdiction.EU)
