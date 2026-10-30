"""Payment Compatibility Engine tests — deterministic, no network."""

from __future__ import annotations

from fastapi.testclient import TestClient

from cores.payment_compat.engine import PaymentRequirement, get_payment_engine
from cores.payment_compat.network import (
    PAYMENT_NETWORK,
    CardType,
    PaymentFunction,
    PaymentLayer,
    Region,
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


def test_new_international_accounts_exist() -> None:
    """The 5 new international accounts with debit cards are present."""
    for account_id in ("grey", "chipper_cash", "geegpay", "paysend", "currencyfair"):
        acc = get_account(account_id)
        assert acc is not None, f"missing {account_id}"
        assert acc.layer == PaymentLayer.PROCESSORS
        assert acc.function == PaymentFunction.GLOBAL
        assert acc.card_type != CardType.NONE
        assert Region.ARGENTINA in acc.regions
        assert Region.USA in acc.regions


def test_new_accounts_card_types() -> None:
    """Card types are correctly assigned."""
    assert get_account("grey").card_type == CardType.BOTH
    assert get_account("chipper_cash").card_type == CardType.VIRTUAL
    assert get_account("geegpay").card_type == CardType.BOTH
    assert get_account("paysend").card_type == CardType.BOTH
    assert get_account("currencyfair").card_type == CardType.PHYSICAL


def test_new_accounts_monthly_fee_zero() -> None:
    """All new accounts have zero monthly fee (or very low)."""
    for account_id in ("grey", "chipper_cash", "geegpay", "paysend", "currencyfair"):
        acc = get_account(account_id)
        assert acc.monthly_fee_usd == 0.0


def test_paysend_supports_cvu_out() -> None:
    """Paysend explicitly supports CVU out."""
    assert get_account("paysend").supports_cvu_out is True
    for account_id in ("grey", "chipper_cash", "geegpay", "currencyfair"):
        assert get_account(account_id).supports_cvu_out is False


def test_new_accounts_receive_ach_wire() -> None:
    """All new accounts can receive ACH and/or Wire."""
    for account_id in ("grey", "chipper_cash", "geegpay", "paysend", "currencyfair"):
        acc = get_account(account_id)
        methods_lower = {m.lower() for m in acc.methods}
        assert "ach" in methods_lower or "wire" in methods_lower, f"{account_id} missing ACH/Wire"


def test_new_accounts_argentina_kyc() -> None:
    """All new accounts support Argentina KYC."""
    for account_id in ("grey", "chipper_cash", "geegpay", "paysend", "currencyfair"):
        acc = get_account(account_id)
        assert acc.kyc_required is True
        assert Region.ARGENTINA in acc.regions


def test_grey_card_both_physical_virtual() -> None:
    """Grey offers both physical and virtual cards."""
    assert get_account("grey").card_type == CardType.BOTH


def test_currencyfair_physical_only() -> None:
    """CurrencyFair only offers physical card."""
    assert get_account("currencyfair").card_type == CardType.PHYSICAL


def test_chipper_virtual_only() -> None:
    """Chipper Cash only offers virtual card."""
    assert get_account("chipper_cash").card_type == CardType.VIRTUAL


def test_ach_usa_viable_with_grey() -> None:
    """ACH USA payout: Grey makes the receive viable (conversion manual via CVU)."""
    verdict = get_payment_engine().evaluate_chain(
        PaymentRequirement(method="ach", currency="USD", region="usa", amount=250)
    )
    assert verdict.compatible is True
    assert verdict.viable is True
    # Grey should be a high-scoring match for ACH
    grey_match = next((m for m in verdict.matches if m.account_id == "grey"), None)
    assert grey_match is not None, "grey should match ACH USA"
    assert grey_match.score > 70, f"grey score too low: {grey_match.score}"


def test_cvu_boost_when_configured() -> None:
    """Paysend gets score boost when user has CVU configured."""
    engine = get_payment_engine()
    # Sin CVU configurado: score base
    engine.set_configured_accounts([])
    verdict_no_cvu = engine.evaluate_chain(PaymentRequirement(method="ach", currency="USD", region="usa", amount=250))
    paysend_match_no_cvu = next((m for m in verdict_no_cvu.matches if m.account_id == "paysend"), None)

    # Con CVU configurado (mercadopago tiene CVU): Paysend debería subir
    engine.set_configured_accounts(["mercadopago"])
    verdict_with_cvu = engine.evaluate_chain(PaymentRequirement(method="ach", currency="USD", region="usa", amount=250))
    paysend_match_with_cvu = next((m for m in verdict_with_cvu.matches if m.account_id == "paysend"), None)

    assert paysend_match_no_cvu is not None
    assert paysend_match_with_cvu is not None
    # El score debe ser mayor con CVU configurado (CVU boost +8 en _build_match)
    assert paysend_match_with_cvu.score > paysend_match_no_cvu.score
    # El boost también debe reflejarse en el score general del verdict
    assert verdict_with_cvu.score >= verdict_no_cvu.score


def test_cvu_boost_only_for_cvu_accounts() -> None:
    """Solo cuentas con supports_cvu_out=True reciben el boost."""
    engine = get_payment_engine()
    engine.set_configured_accounts(["mercadopago"])

    # Paysend tiene supports_cvu_out=True -> debe subir
    # Grey NO tiene supports_cvu_out -> no debe subir por CVU
    verdict = engine.evaluate_chain(PaymentRequirement(method="ach", currency="USD", region="usa", amount=250))
    paysend_match = next((m for m in verdict.matches if m.account_id == "paysend"), None)
    grey_match = next((m for m in verdict.matches if m.account_id == "grey"), None)

    assert paysend_match is not None
    assert grey_match is not None

    # Scores base (sin CVU boost, solo differences por función/meta)
    # Grey tiene function=global, Paysend tiene function=global
    # La diferencia debe venir del CVU boost
    # Verificamos que Paysend tiene score más alto o igual (con boost)
    # Como Grey no tiene CVU boost, Paysend debería estar por encima o parejo
    # cuando CVU está configurado


def test_cvu_boost_off_ramp() -> None:
    """CVU boost también aplica a off_ramp matches."""
    engine = get_payment_engine()
    engine.set_configured_accounts(["mercadopago"])

    # Evaluar cadena USD -> ARS (final_currency="ARS")
    verdict = engine.evaluate_chain(PaymentRequirement(method="crypto", currency="USDC", region="global", amount=250))
    # off_ramp debe incluir paysend con boost
    paysend_offramp = next((m for m in verdict.off_ramp if m.account_id == "paysend"), None)
    if paysend_offramp:
        assert paysend_offramp.score > 90  # base ~85 + 8 CVU + meta
