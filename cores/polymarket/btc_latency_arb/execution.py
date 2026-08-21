"""Order Execution (EIP-712) for Polymarket CLOB."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from core.polymarket.btc_latency_arb.config import BTCArbConfig, LiveTradingConfig

logger = logging.getLogger("orion.polymarket.btc_latency_arb.execution")


@dataclass(slots=True)
class OrderParams:
    """Order parameters for Polymarket CLOB."""

    market_id: str
    token_id: str
    side: str  # "BUY" or "SELL"
    price: float  # 0-1
    size: float  # in shares
    expiration: int = 0  # 0 = GTC


@dataclass(slots=True)
class SignedOrder:
    """EIP-712 signed order."""

    order: OrderParams
    signature: str
    signer: str
    nonce: int


@dataclass(slots=True)
class OrderResult:
    """Order execution result."""

    success: bool
    order_id: str | None = None
    error: str | None = None
    filled_size: float = 0.0
    avg_price: float = 0.0
    timestamp: int = 0


class OrderExecutor:
    """Execute orders on Polymarket CLOB with EIP-712 signing."""

    # Polymarket CLOB EIP-712 Domain
    CLOB_DOMAIN = {
        "name": "Polymarket CLOB",
        "version": "1",
        "chainId": 137,  # Polygon
        "verifyingContract": "0x4D97ECdAaD2256A6C85eA5b3A0C45c124a264f04",
    }

    ORDER_TYPES = {
        "Order": [
            {"name": "salt", "type": "uint256"},
            {"name": "maker", "type": "address"},
            {"name": "signer", "type": "address"},
            {"name": "taker", "type": "address"},
            {"name": "tokenId", "type": "address"},
            {"name": "makerAmount", "type": "uint256"},
            {"name": "takerAmount", "type": "uint256"},
            {"name": "expiration", "type": "uint256"},
            {"name": "nonce", "type": "uint256"},
            {"name": "feeRateBps", "type": "uint16"},
            {"name": "side", "type": "uint8"},  # 0 = BUY, 1 = SELL
            {"name": "signatureType", "type": "uint8"},
        ]
    }

    def __init__(self, config: LiveTradingConfig) -> None:
        self.config = config
        self._nonce = int(time.time() * 1000)
        self._private_key: str | None = None
        self._signer_address: str | None = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize executor with private key from IdentityVault."""
        if not self.config.enable_live:
            logger.info("Live trading disabled - executor in simulation mode")
            return False

        if not self.config.private_key_path and not self.config.polymarket_secret:
            logger.error("No private key configured for live trading")
            return False

        try:
            # Load private key (from IdentityVault or config)
            if self.config.private_key_path:
                from pathlib import Path

                key_path = Path(self.config.private_key_path).expanduser()
                if key_path.exists():
                    self._private_key = key_path.read_text().strip()
                else:
                    logger.error("Private key file not found: %s", key_path)
                    return False
            elif self.config.polymarket_secret:
                self._private_key = self.config.polymarket_secret

            if not self._private_key:
                return False

            # Derive address
            from eth_account import Account

            account = Account.from_key(self._private_key)
            self._signer_address = account.address
            self._initialized = True

            logger.info("OrderExecutor initialized for %s", self._signer_address)
            return True

        except Exception as e:
            logger.error("OrderExecutor initialization failed: %s", e)
            return False

    def is_ready(self) -> bool:
        return self._initialized

    def sign_order(self, params: OrderParams) -> SignedOrder | None:
        """Sign order using EIP-712."""
        if not self._initialized:
            logger.error("Executor not initialized")
            return None

        try:
            from eth_account import Account
            from eth_account.messages import encode_structured_data

            # Prepare order struct
            order_struct = {
                "salt": int(time.time() * 1e6) % (2**256),
                "maker": self._signer_address,
                "signer": self._signer_address,
                "taker": "0x0000000000000000000000000000000000000000",
                "tokenId": params.token_id,
                "makerAmount": int(params.size * 1e18),  # USDC has 6 decimals, but CLOB uses 18
                "takerAmount": int(params.price * params.size * 1e18),
                "expiration": params.expiration,
                "nonce": self._nonce,
                "feeRateBps": 200,  # 2% fee
                "side": 0 if params.side == "BUY" else 1,
                "signatureType": 1,  # EIP-712
            }

            # Encode and sign
            data = {
                "types": self.ORDER_TYPES,
                "primaryType": "Order",
                "domain": self.CLOB_DOMAIN,
                "message": order_struct,
            }

            signed = Account.sign_message(encode_structured_data(data), self._private_key)
            self._nonce += 1

            return SignedOrder(
                order=params,
                signature=signed.signature.hex(),
                signer=self._signer_address,
                nonce=self._nonce - 1,
            )

        except Exception as e:
            logger.error("Order signing failed: %s", e)
            return None

    async def place_order(self, params: OrderParams) -> OrderResult:
        """Place order on Polymarket CLOB."""
        if not self._initialized:
            return OrderResult(success=False, error="Executor not initialized")

        if self.config.enable_live is False:
            # Simulation mode
            logger.info("SIMULATION: Would place %s order for %s shares @ %.4f", params.side, params.size, params.price)
            return OrderResult(
                success=True,
                order_id=f"sim_{int(time.time() * 1000)}",
                filled_size=params.size,
                avg_price=params.price,
                timestamp=int(time.time() * 1000),
            )

        # Sign order
        signed = self.sign_order(params)
        if not signed:
            return OrderResult(success=False, error="Failed to sign order")

        # Submit to CLOB
        try:
            import httpx
            import json

            url = "https://clob.polymarket.com/order"

            payload = {
                "order": {
                    "salt": str(signed.order.__dict__["salt"]),
                    "maker": signed.signer,
                    "signer": signed.signer,
                    "taker": "0x0000000000000000000000000000000000000000",
                    "tokenId": signed.order.token_id,
                    "makerAmount": str(int(signed.order.size * 1e18)),
                    "takerAmount": str(int(signed.order.price * signed.order.size * 1e18)),
                    "expiration": str(signed.order.expiration),
                    "nonce": str(signed.nonce),
                    "feeRateBps": 200,
                    "side": 0 if signed.order.side == "BUY" else 1,
                    "signatureType": 1,
                },
                "signature": signed.signature,
            }

            headers = {
                "Content-Type": "application/json",
                "POL-SIGNER": signed.signer,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    return OrderResult(
                        success=True,
                        order_id=data.get("orderID"),
                        filled_size=0.0,  # Will be filled async
                        avg_price=params.price,
                        timestamp=int(time.time() * 1000),
                    )
                else:
                    error_text = await resp.text()
                    logger.error("CLOB order failed: %d %s", resp.status_code, error_text)
                    return OrderResult(success=False, error=f"CLOB {resp.status_code}: {error_text}")

        except Exception as e:
            logger.error("Order placement failed: %s", e)
            return OrderResult(success=False, error=str(e))

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if not self._initialized:
            return False

        try:
            import httpx

            url = f"https://clob.polymarket.com/order/{order_id}"

            headers = {"POL-SIGNER": self._signer_address or ""}

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(url, headers=headers)
                return resp.status_code == 200
        except Exception as e:
            logger.error("Order cancellation failed: %s", e)
            return False

    async def get_order_status(self, order_id: str) -> dict[str, Any] | None:
        """Get order status."""
        try:
            import httpx

            url = f"https://clob.polymarket.com/order/{order_id}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning("Get order status failed: %s", e)
        return None

    async def get_positions(self) -> list[dict[str, Any]]:
        """Get current positions."""
        # This would require querying the CLOB positions endpoint
        # Implementation depends on Polymarket API
        return []
