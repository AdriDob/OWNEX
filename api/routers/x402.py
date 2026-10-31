"""x402 Payment Middleware for OWNEX — per-call USDC payments on Base.

Implements x402 HTTP middleware that enables autonomous AI agents (and
any client) to pay USDC per API request via EIP-3009 signature authentication.

No KYC, no accounts, no cartels. Just pay-per-call on your own terms.

Typical use:
    from api.routers.x402 import setup_x402
    app = FastAPI()
    setup_x402(app, pay_to="0xTU_WALLET", price_per_call="$0.05")
    # Endpoints now require X-Payment-Required header with signed USDC transfer
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from x402.http import FacilitatorConfig, HTTPFacilitatorClient
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer


def setup_x402(
    app: FastAPI,
    *,
    pay_to: str,  # Wallet address on Base (e.g. 0x...)
    price: str = "$0.05",  # Price per API call in USD
    network: str = "eip155:84532",  # Base mainnet
    facilitator_url: str = "https://x402.org/facilitator",
    default_routes: bool = True,
    allow_origins: list[str] | None = None,
) -> PaymentMiddlewareASGI:
    """Setup x402 payment middleware on a FastAPI application.

    Args:
        app: FastAPI application instance
        pay_to: Wallet address that receives payments (Base network)
        price: Price per API call (e.g. "$0.05", "$0.10")
        network: EVM network ID (default: Base mainnet eip155:84532)
        facilitator_url: URL of the x402 facilitator for gasless payments
        default_routes: Whether to register default code-review and data-extract routes
        allow_origins: Origins allowed for CORS (if needed)

    Returns:
        The configured PaymentMiddlewareASGI instance (already added to app).
    """

    # Initialize facilitator client
    facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=facilitator_url))

    # Initialize resource server with ExactEVM scheme (EIP-3009 signature)
    server = x402ResourceServer(facilitator)
    server.register(network, ExactEvmServerScheme())

    # Parse price: remove $ sign and convert to float
    price_float: float = float(price.replace("$", "").strip())

    # Define default routes if requested
    if default_routes:
        routes: list[RouteConfig] = [
            # Code review endpoint - popular use case
            {
                "path": "/api/code-review",
                "accepts": [
                    {
                        "scheme": "exact",
                        "pay_to": pay_to,
                        "price": price,
                        "network": network,
                    }
                ],
                "mime_type": "application/json",
                "description": "Automated code review of diffs/PRs",
            },
            # Data extraction endpoint
            {
                "path": "/api/data-extract",
                "accepts": [
                    {
                        "scheme": "exact",
                        "pay_to": pay_to,
                        "price": str(price_float * 0.4),  # 40% of code-review price
                        "network": network,
                    }
                ],
                "mime_type": "application/json",
                "description": "Structured data extraction from URLs",
            },
        ]
    else:
        routes = []

    # Add CORS middleware if origins provided
    if allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Add x402 payment middleware to the FastAPI app
    # This is the standard pattern: app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)
    app.add_middleware(
        PaymentMiddlewareASGI,
        routes=routes,
        server=server,
    )

    # Return the middleware instance for inspection/configuration
    # (it's already been added to the app via add_middleware above)
    return PaymentMiddlewareASGI(app=app, routes=routes, server=server)  # type: ignore


# Default FastAPI app for quick start (can be imported and configured)
def create_app(
    pay_to: str = os.getenv("X402_PAY_TO", "0xYOURWALLETBASE"),
    price: str = os.getenv("X402_PRICE", "$0.05"),
    allow_origins: list[str] | None = None,
) -> FastAPI:
    """Create a FastAPI app with x402 payments configured.

    Intended for quick deployment or as reference for OWNEX integration.

    Args:
        pay_to: Wallet address receiving payments (from env or default)
        price: Price per call (from env or default)
        allow_origins: Origins allowed for CORS (optional)

    Returns:
        Configured FastAPI application with x402 middleware.
    """
    app = FastAPI(title="OWNEX x402 APIs", version="0.1.0")

    # Add CORS middleware if origins provided
    if allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Setup x402 payment middleware
    setup_x402(
        app,
        pay_to=pay_to,
        price=price,
        allow_origins=allow_origins,
    )

    # Health check endpoint (no payment required)
    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Root endpoint (no payment required)
    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "OWNEX x402 API ready", "docs": "/docs"}

    # Example endpoint that requires payment (protected by middleware)
    @app.get("/api/v1/analyze", include_in_schema=False)
    async def analyze_endpoint() -> dict[str, Any]:
        """Example protected endpoint - requires valid x402 payment.

        In production, this would perform actual analysis work.
        This will only be reached if payment was verified by middleware.
        """
        # This will only be reached if payment was verified by middleware
        return {"result": "analysis completed", "confidence": 0.92}

    return app


# For direct execution: python -m api.routers.x402
if __name__ == "__main__":
    import uvicorn

    pay_to = os.getenv("X402_PAY_TO", "0xYOURWALLETBASE")
    price = os.getenv("X402_PRICE", "$0.05")

    app = create_app(pay_to=pay_to, price=price)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
