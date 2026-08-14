"""Payment Compatibility Engine tests — deterministic, no network."""

from __future__ import annotations

from fastapi.testclient import TestClient

from cores.payment_compat.engine import PaymentRequirement, get_payment_engine
from cores.payment_compat.network import (
    PAYMENT_NETWORK,
    PaymentFunction,
    PaymentLayer,
    accounts_by_function,
    accounts_by_layer,
    get_account,
)


def test_catalog_has_all_layers() -> None:
    """The curated network covers every architectural layer."""
    layers = {a.layer for a in PAYMENT_NETWORK}
    assert PaymentLayer.BANKING in layers
    assert PaymentLayer.PROCESSORS in layers
    assert PaymentLayer.CRYPTO in layers
    assert PaymentLayer.SELF_CUSTODY in layers
    assert PaymentLayer.WITHDRAWAL in layers


def test_catalog_has_core_nucleus_accounts() -> None:
    """The 10 core accounts the owner prioritizes are present."""
    for account_id in (
        "grabrfi",
        "global66",
        "airtm",
        "takenos",
        "dolarapp",
        "belo",
        "payoneer",
        "wise",
        "astro_pay",
        "mercadopago",
    ):
        assert get_account(account_id) is not None, f"missing {account_id}"


def test_catalog_has_crypto_and_self_custody() -> None:
    """Exchanges, AR ramps, stablecoin ramps and self-custody wallets exist."""
    for account_id in ("binance", "kraken", "coinbase", "okx", "bybit", "bitget"):
        assert get_account(account_id) is not None
    for account_id in ("lemon", "bitso", "buenbit", "ripio", "fiwind", "satoshi_tango", "decrypto"):
        assert get_account(account_id) is not None
    for account_id in ("metamask", "rabby", "phantom", "ledger", "trezor", "safe"):
        assert get_account(account_id) is not None


def test_us_account_function_classification() -> None:
    """GrabrFi is the US receiving account; Mercado Pago is local."""
    grabrfi = get_account("grabrfi")
    assert grabrfi is not None
    assert grabrfi.function == PaymentFunction.US_ACCOUNT
    assert grabrfi.matches_method("ach")
    mercadopago = get_account("mercadopago")
    assert mercadopago is not None
    assert mercadopago.function == PaymentFunction.LOCAL
    assert mercadopago.matches_method("cvu")


def test_usdc_chain_viable() -> None:
    """USDC/Base bounty: receive + off-ramp to ARS is viable."""
    verdict = get_payment_engine().evaluate_chain(
        PaymentRequirement(method="crypto", currency="USDC", region="global", amount=250, platform="Bounty")
    )
    assert verdict.compatible is True
    assert verdict.viable is True
    assert verdict.score > 50
    assert any(m.account_id == "binance" for m in verdict.matches)
    assert any(m.account_id == "binance" for m in verdict.off_ramp)
    assert any(m.account_id == "metamask" for m in verdict.matches)


def test_ach_usa_viable_with_grabrfi() -> None:
    """ACH USA payout: GrabrFi makes the receive viable (conversion manual)."""
    verdict = get_payment_engine().evaluate_chain(
        PaymentRequirement(method="ach", currency="USD", region="usa", amount=250)
    )
    assert verdict.compatible is True
    assert verdict.viable is True
    assert any(m.account_id == "grabrfi" for m in verdict.matches)
    assert any("manual" in note for note in verdict.honest_notes)


def test_region_mismatch_incompatible() -> None:
    """ACH required for a non-USA region is flagged as incompatible."""
    verdict = get_payment_engine().evaluate(PaymentRequirement(method="ach", currency="USD", region="argentina"))
    assert verdict.compatible is False
    assert any("cuenta en USA" in m for m in verdict.missing)


def test_documentation_honesty_rule() -> None:
    """Platform requiring an LLC → incompatible, no workaround suggested."""
    verdict = get_payment_engine().evaluate(
        PaymentRequirement(method="ach", currency="USD", region="usa", required_documentation="llc")
    )
    assert verdict.compatible is False
    assert verdict.score == 0.0
    assert any("LLC" in m for m in verdict.missing)
    assert any("no se sugiere ningún workaround" in note for note in verdict.honest_notes)


def test_kyc_documentation_does_not_block() -> None:
    """Platform requiring personal KYC → accounts remain compatible."""
    verdict = get_payment_engine().evaluate(
        PaymentRequirement(method="crypto", currency="USDC", region="global", required_documentation="kyc")
    )
    assert verdict.compatible is True


def test_local_cvu_payout_viable() -> None:
    """ARS CVU payout → local accounts (Mercado Pago, Ualá...) match."""
    verdict = get_payment_engine().evaluate(
        PaymentRequirement(method="cvu", currency="ARS", region="argentina", amount=100)
    )
    assert verdict.compatible is True
    assert any(m.account_id == "mercadopago" for m in verdict.matches)


def test_network_summary_shape() -> None:
    """Summary exposes layer/function/region grouping."""
    summary = get_payment_engine().network_summary()
    assert summary["total_accounts"] == len(PAYMENT_NETWORK)
    assert "banking" in summary["by_layer"]
    assert "self_custody" in summary["by_layer"]
    assert "primary" in summary["by_function"]
    assert "usa" in summary["by_region"]


def test_account_helpers() -> None:
    """Layer/function helpers return non-empty lists for known layers."""
    assert len(accounts_by_layer(PaymentLayer.CRYPTO)) >= 15
    assert len(accounts_by_function(PaymentFunction.LOCAL)) >= 10


def _authed_client() -> TestClient:
    from api.main import app

    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"device_id": "pytest-payment-compat"})
    if resp.status_code == 200 and "data" in resp.json():
        client.headers.update({"Authorization": f"Bearer {resp.json()['data']['token']}"})
    csrf = resp.cookies.get("csrf_token") or resp.cookies.get("csrf")
    if csrf:
        client.headers.update({"X-CSRF-Token": csrf})
    return client


def test_payment_network_api() -> None:
    """API: network overview, evaluate and chain endpoints respond."""
    client = _authed_client()
    response = client.get("/api/payment-compat")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_accounts"] == len(PAYMENT_NETWORK)

    response = client.get("/api/payment-compat/network")
    assert response.status_code == 200
    assert "banking" in response.json()["grouped"]

    response = client.post(
        "/api/payment-compat/evaluate",
        json={"method": "crypto", "currency": "USDC", "region": "global", "amount": 250},
    )
    assert response.status_code == 200
    verdict = response.json()
    assert verdict["compatible"] is True
    assert verdict["score"] > 50

    response = client.post(
        "/api/payment-compat/evaluate/chain",
        json={"method": "ach", "currency": "USD", "region": "usa", "amount": 250, "final_currency": "ARS"},
    )
    assert response.status_code == 200
    assert response.json()["viable"] is True

    response = client.get("/api/payment-compat/account/grabrfi")
    assert response.status_code == 200
    assert response.json()["function"] == "us_account"

    response = client.get("/api/payment-compat/account/does_not_exist")
    assert response.status_code == 404
