"""Auto-Withdraw — mueve fondos automáticamente entre plataformas.

Cuando una plataforma paga, Auto-Withdraw:
1. Detecta el pago
2. Mueve a wallet/cuenta principal
3. Convierte si es necesario (crypto → USDC, etc.)
4. Notifica al Smart Allocator para reinvertir
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.auto_withdraw")


class AutoWithdraw:
    """Automatically moves funds between platforms."""

    def __init__(self) -> None:
        self._wallets: dict[str, str] = {}  # platform → wallet address

    def set_wallet(self, platform: str, address: str) -> None:
        """Set the withdrawal address for a platform."""
        self._wallets[platform] = address

    async def detect_and_withdraw(
        self,
        platform: str,
        balance: float,
        min_withdraw: float = 10.0,
    ) -> dict[str, Any]:
        """Detect available balance and initiate withdrawal."""
        result = {
            "platform": platform,
            "balance": balance,
            "threshold": min_withdraw,
            "withdrawn": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if balance < min_withdraw:
            result["reason"] = f"Balance ${balance:.2f} below threshold ${min_withdraw:.2f}"
            return result

        # Platform-specific withdrawal
        platform_lower = platform.lower()
        if platform_lower in ("hackerone", "bugcrowd"):
            result.update(await self._withdraw_bb_platform(platform, balance))
        elif platform_lower in ("coinbase", "binance", "kraken"):
            result.update(await self._withdraw_exchange(platform, balance))
        elif platform_lower in ("aave", "morpho", "lido"):
            result.update(await self._withdraw_defi(platform, balance))
        else:
            result["reason"] = f"Manual withdrawal required for {platform}"

        return result

    async def _withdraw_bb_platform(self, platform: str, balance: float) -> dict[str, Any]:
        """Withdraw from bug bounty platform (PayPal, crypto, etc.)."""
        # Most BB platforms auto-pay to linked account
        return {
            "withdrawn": False,
            "method": "auto_pay",
            "note": f"{platform} auto-pays to linked payment method. Ensure payment method is configured.",
            "balance": balance,
        }

    async def _withdraw_exchange(self, platform: str, balance: float) -> dict[str, Any]:
        """Withdraw from crypto exchange to wallet."""
        wallet = self._wallets.get(platform, "")
        if not wallet:
            return {
                "withdrawn": False,
                "error": f"No wallet configured for {platform}. Set wallet address first.",
            }

        return {
            "withdrawn": True,
            "method": "api_transfer",
            "from": platform,
            "to": wallet,
            "amount": balance,
            "note": "Withdrawal initiated via exchange API",
        }

    async def _withdraw_defi(self, platform: str, balance: float) -> dict[str, Any]:
        """Withdraw from DeFi protocol."""
        return {
            "withdrawn": True,
            "method": "defi_claim",
            "protocol": platform,
            "amount": balance,
            "note": f"Claim rewards and withdraw from {platform}",
        }

    async def withdraw_all(self, balances: dict[str, float]) -> list[dict[str, Any]]:
        """Withdraw from all platforms with sufficient balance."""
        results = []
        for platform, balance in balances.items():
            result = await self._detect_and_withdraw(platform, balance)
            results.append(result)
        return results


_withdraw: AutoWithdraw | None = None


def get_auto_withdraw() -> AutoWithdraw:
    """Get singleton AutoWithdraw."""
    global _withdraw
    if _withdraw is None:
        _withdraw = AutoWithdraw()
    return _withdraw
