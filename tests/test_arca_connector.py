"""Tests for ARCA (ex AFIP) tax invoicing connector."""

from __future__ import annotations

from cores.integrations.arca.connector import (
    ArcaConnector,
    ArcaInvoice,
    get_arca_connector,
    reset_arca_connector,
)


def test_arca_invoice_dataclass() -> None:
    inv = ArcaInvoice(
        id="ARCA-B-12345678",
        invoice_number=12345678,
        invoice_type="B",
        cuit="20-12345678-9",
        recipient_cuit="20-98765432-1",
        recipient_name="Client Name",
        amount=100000.0,
        vat_amount=21000.0,
        total=121000.0,
        concept="Security services",
        status="emitted",
        cae="12345678901234",
    )
    assert inv.invoice_type == "B"
    assert inv.total == 121000.0
    assert inv.cae == "12345678901234"
    assert inv.status == "emitted"


def test_calculate_iva_general() -> None:
    connector = ArcaConnector()
    result = connector.calculate_iva(100000.0, "general")
    assert result["net_amount"] == 100000.0
    assert result["vat_amount"] == 21000.0
    assert result["total"] == 121000.0
    assert result["rate"] == 0.21


def test_calculate_iva_reduced() -> None:
    connector = ArcaConnector()
    result = connector.calculate_iva(100000.0, "reduced")
    assert result["vat_amount"] == 10500.0


def test_calculate_iva_exempt() -> None:
    connector = ArcaConnector()
    result = connector.calculate_iva(100000.0, "exempt")
    assert result["vat_amount"] == 0.0
    assert result["total"] == 100000.0


def test_calculate_iva_invalid_rate_fallback() -> None:
    connector = ArcaConnector()
    result = connector.calculate_iva(1000.0, "invalid_rate")
    assert result["rate"] == 0.21  # fallback to general


def test_validate_cuit_valid() -> None:
    connector = ArcaConnector()
    # Valid CUITs (check digit computed with modulo 11)
    assert connector.validate_cuit("20-23188483-2") is True  # known valid test CUIT
    assert connector.validate_cuit("27-12345678-0") is True


def test_validate_cuit_invalid_format() -> None:
    connector = ArcaConnector()
    assert connector.validate_cuit("not-a-cuit") is False
    assert connector.validate_cuit("123") is False
    assert connector.validate_cuit("") is False
    assert connector.validate_cuit("20-23188483-3") is False  # bad check digit


def test_validate_cuit_without_dashes() -> None:
    connector = ArcaConnector()
    # Without dashes should also work
    assert connector.validate_cuit("20231884832") is True
    assert connector.validate_cuit("20231884833") is False


def test_connector_initialization() -> None:
    connector = ArcaConnector()
    assert connector.is_connected() is False


def test_connector_health_when_not_connected() -> None:
    connector = ArcaConnector()
    import asyncio

    health = asyncio.run(connector.health())
    assert health.get("connected") is False


def test_connector_create_invoice_when_not_connected() -> None:
    connector = ArcaConnector()
    import asyncio

    inv = asyncio.run(connector.create_invoice(amount=1000.0))
    assert inv is None


def test_create_invoice_in_test_mode() -> None:
    import os

    os.environ["ARCA_CUIT"] = "20-23188483-2"
    os.environ["ARCA_ENVIRONMENT"] = "test"
    os.environ["ARCA_INVOICE_TYPE"] = "B"
    connector = ArcaConnector()
    import asyncio

    connected = asyncio.run(connector.connect())
    assert connected is True
    inv = asyncio.run(
        connector.create_invoice(
            invoice_type="B",
            recipient_cuit="20-23188483-2",
            recipient_name="Test Client",
            amount=150000.0,
            concept="Bug bounty services",
        )
    )
    assert inv is not None
    assert inv.status == "emitted"
    assert inv.total == 181500.0  # 150000 + 21% IVA
    assert inv.cae != ""
    # Clean up env
    del os.environ["ARCA_CUIT"]
    del os.environ["ARCA_ENVIRONMENT"]
    del os.environ["ARCA_INVOICE_TYPE"]


def test_list_invoices() -> None:
    import os

    os.environ["ARCA_CUIT"] = "20-23188483-2"
    os.environ["ARCA_ENVIRONMENT"] = "test"
    os.environ["ARCA_INVOICE_TYPE"] = "B"
    connector = ArcaConnector()
    import asyncio

    asyncio.run(connector.connect())
    asyncio.run(connector.create_invoice(amount=50000.0, recipient_cuit="20-23188483-2"))
    asyncio.run(connector.create_invoice(amount=75000.0, recipient_cuit="20-23188483-2"))
    invoices = asyncio.run(connector.list_invoices())
    assert len(invoices) == 2
    # Clean up env
    del os.environ["ARCA_CUIT"]
    del os.environ["ARCA_ENVIRONMENT"]
    del os.environ["ARCA_INVOICE_TYPE"]


def test_get_arca_connector_singleton() -> None:
    reset_arca_connector()
    c1 = get_arca_connector()
    c2 = get_arca_connector()
    assert c1 is c2


def test_reset_arca_connector_clears_singleton() -> None:
    reset_arca_connector()
    c1 = get_arca_connector()
    reset_arca_connector()
    c2 = get_arca_connector()
    assert c1 is not c2
