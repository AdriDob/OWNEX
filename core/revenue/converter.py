from __future__ import annotations


def usd_to_ars(amount_usd: float, rate: float = 1000.0) -> float:
    """Convert USD to ARS at the given exchange rate."""
    return round(amount_usd * rate, 2)


def ars_to_usd(amount_ars: float, rate: float = 1000.0) -> float:
    """Convert ARS to USD at the given exchange rate."""
    return round(amount_ars / rate, 2)


def calculate_fee(amount_usd: float, method: str) -> float:
    """Calculate the fee for a payment method."""
    from core.revenue.models import ARGENTINA_METHODS

    info = ARGENTINA_METHODS.get(method)
    if info is None:
        return 0.0
    return round(amount_usd * info.fee_percent / 100, 2)


def net_after_fee(amount_usd: float, method: str) -> float:
    """Calculate net amount after deducting the payment method fee."""
    fee = calculate_fee(amount_usd, method)
    return round(amount_usd - fee, 2)
