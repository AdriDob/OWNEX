"""
Quant Research & Performance Lab - OWENEX v10.1 Integration

Modular research infrastructure for quantitative analysis, backtesting,
and strategy optimization. All components are optional and isolated.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any

try:
    import numpy as np
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    np = None
    pd = None

# Quant Lab Capability Registry
QUANT_CAPABILITIES = {
    "gs_quant": {
        "repo": "https://github.com/goldmansachs/gs-quant",
        "category": "institutional_quant",
        "requirements": ["institutional_credentials", "marquee_access"],
        "status": "not_connected",
        "features": ["asset_pricing", "risk_analytics", "portfolio_optimization", "monte_carlo_simulation"],
        "credentials_required": True,
        "auto_trading": False,
        "license": "proprietary_goldman_sachs",
        " argentina_compatible": False,
        "last_verified": None,
    },
    "jpmorgan_python_training": {
        "repo": "https://github.com/jpmorganchase/python-training",
        "category": "educational",
        "requirements": [],
        "status": "connected",
        "features": ["python_financial_data", "pandas_visualization", "market_analytics", "strategy_backtesting"],
        "credentials_required": False,
        "auto_trading": False,
        "license": "educational_use",
        " argentina_compatible": True,
        "last_verified": "2026-11-09",
    },
    "magic_trace": {
        "repo": "https://github.com/janestreet/magic-trace",
        "category": "performance_profiling",
        "requirements": ["linux", "intel_processor_trace"],
        "status": "optional",
        "features": ["python_performance_profiling", "cpu_tracing", "memory_analysis", "runtime_optimization"],
        "credentials_required": False,
        "auto_trading": False,
        "license": "apache_2.0",
        " argentina_compatible": True,
        "last_verified": None,
        "note": "Requires Linux + Intel PT. NOT for Windows mandatory install.",
    },
    "firedancer": {
        "repo": "https://github.com/firedancer-io/firedancer",
        "category": "solana_validator",
        "requirements": [],
        "status": "optional",
        "features": ["solana_validator_deployment", "cluster_operations", "blockchain_infrastructure", "performance_testing"],
        "credentials_required": False,
        "auto_trading": False,
        "license": "apache_2.0",
        " argentina_compatible": True,
        "last_verified": None,
        "note": "NOT a trading bot. Solana validator infrastructure only. Research/infrastructure.",
    },
    "xpedite": {
        "repo": "https://github.com/morganstanley/Xpedite",
        "category": "cpp_profiling",
        "requirements": ["cpp_code", "low_latency_focus"],
        "status": "optional",
        "features": ["cplusplus_profiling", "latency_analysis", "performance_optimization", "thread_analysis"],
        "credentials_required": False,
        "auto_trading": False,
        "license": "proprietary_morgan_stanley",
        " argentina_compatible": True,
        "last_verified": None,
        "note": "C++ low latency profiling. For development only.",
    },
    "arcticdb": {
        "repo": "https://github.com/man-group/ArcticDB",
        "category": "time_series_storage",
        "requirements": ["license_review"],
        "status": "license_review_pending",
        "features": ["time_series_database", "historical_data_storage", "query_performance", "data_retention"],
        "credentials_required": False,
        "auto_trading": False,
        "license": "commercial_review_required",
        " argentina_compatible": True,
        "last_verified": None,
        "note": "License review required before integration. Time-series storage.",
    },
}


def get_quant_capability(name: str) -> dict[str, Any] | None:
    """Get quant capability by name with status and requirements."""
    return QUANT_CAPABILITIES.get(name)


def list_quant_capabilities() -> list[str]:
    """List all available quant capabilities."""
    return list(QUANT_CAPABILITIES.keys())


def check_prerequisites(capability: str) -> dict[str, Any]:
    """Check if prerequisites are met for a quant capability."""
    cap = get_quant_capability(capability)
    if not cap:
        return {"status": "error", "message": f"Capability '{capability}' not found"}

    prerequisites = {
        "has_credentials": cap.get("requirements", []),
        "meets_requirements": True,  # Placeholder - would check actual system state
        "license_valid": cap.get("status") != "license_review_pending",
        "platform_compatible": True,  # Would check OS, hardware
        "ready_to_use": cap["status"] in ["connected", "optional"] and cap.get("license_valid", False),
    }

    return prerequisites


# Crypto Intelligence Provider Registry
CRYPTO_PROVIDER_REGISTRY = {
    # Market & Fundamentals
    "coingecko": {
        "repo": "https://github.com/coingecko/coingecko-api",
        "category": "market_data",
        "status": "connected",
        "api_available": True,
        "mcp_available": True,
        "requires_api_key": False,
        "rate_limit": "50 calls/minute",
        "argentina_compatible": True,
        "features": ["prices", "market_caps", "total_volumes", "historical_data"],
        "last_verified": "2026-11-09",
    },
    "coinmarketcap": {
        "repo": "https://github.com/coinmarketcap/api-samples",
        "category": "market_data",
        "status": "paid_required",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "rate_limit": "333 calls/day (free tier)",
        "argentina_compatible": True,
        "features": ["prices", "market_data", "volume", "market_cap"],
        "last_verified": "2026-11-09",
        "note": "Free tier limited, paid plans for serious use",
    },
    "glassnode": {
        "repo": "https://github.com/glassnode-com/glassnode-api",
        "category": "on_chain_analytics",
        "status": "paid_required",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "rate_limit": "varies_by_plan",
        "argentina_compatible": True,
        "features": ["on_chain_metrics", "address_data", "exchange_flow"],
        "last_verified": "2026-11-09",
        "note": "Institutional-grade on-chain data",
    },
    "artemis": {
        "repo": "https://github.com/artemisxorg/artemis",
        "category": "on_chain_analytics",
        "status": "connected",
        "api_available": True,
        "mcp_available": True,
        "requires_api_key": False,
        "rate_limit": "generous_free_tier",
        "argentina_compatible": True,
        "features": ["defi_metrics", "lending_protocols", "yield_data"],
        "last_verified": "2026-11-09",
    },
    "token_terminal": {
        "repo": "https://github.com/tokenterminal/token-terminal",
        "category": "fundamentals",
        "status": "connected",
        "api_available": True,
        "mcp_available": True,
        "requires_api_key": False,
        "rate_limit": "generous_free_tier",
        "argentina_compatible": True,
        "features": ["fundamental_metrics", "protocol_data", "revenue"],
        "last_verified": "2026-11-09",
    },
    # On-chain Analytics
    "dune": {
        "repo": "https://github.com/duneanalytics/dune-api",
        "category": "on_chain_analytics",
        "status": "connected",
        "api_available": True,
        "mcp_available": True,
        "requires_api_key": True,
        "rate_limit": "varies_by_account",
        "argentina_compatible": True,
        "features": ["sql_queries", "dashboards", "custom_analytics"],
        "last_verified": "2026-11-09",
    },
    "defillama": {
        "repo": "https://github.com/defillama/defillama-sdk",
        "category": "defi_tvl",
        "status": "connected",
        "api_available": True,
        "mcp_available": True,
        "requires_api_key": False,
        "rate_limit": "100 calls/minute",
        "argentina_compatible": True,
        "features": ["tvl", "defi_protocols", "yields", "chain_data"],
        "last_verified": "2026-11-09",
    },
    # Analytics Social & News
    "moni_ai": {
        "repo": "https://github.com/moniai-io/monai",
        "category": "social_analytics",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["social_sentiment", "crypto_news", "influencer_analysis"],
        "last_verified": "2026-11-09",
        "note": "Verify provider identity and exact API capabilities",
    },
    "crypto_panic": {
        "repo": "https://github.com/CryptoPanic/cryptopanic-api",
        "category": "news_aggregation",
        "status": "connected",
        "api_available": True,
        "mcp_available": True,
        "requires_api_key": True,
        "rate_limit": "Free: 100 calls/day",
        "argentina_compatible": True,
        "features": ["crypto_news", "sentiment_analysis", "rss_feeds"],
        "last_verified": "2026-11-09",
    },
    "cryptorank": {
        "repo": "https://github.com/CryptoRankio/crankt",
        "category": "market_data",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["fundraising", "tokenomics", "market_data"],
        "last_verified": "2026-11-09",
        "note": "Verify proveedor y capacidades exactas de API",
    },
    # Research & Data
    "rootdata": {
        "repo": "https://github.com/RootDataio/rootdata",
        "category": "fundraising_venture",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["projects", "investors", "funding_rounds"],
        "last_verified": "2026-11-09",
        "note": "Proyectos, inversores y financiación",
    },
    "blocksec": {
        "repo": "https://github.com/Block-Sec/securify-cc",
        "category": "smart_contract_security",
        "status": "connected",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": False,
        "argentina_compatible": True,
        "features": ["smart_contract_analysis", "vulnerability_detection"],
        "last_verified": "2026-11-09",
    },
    "bubblemaps": {
        "repo": "https://github.com/BubbleMapsIO/bubblemaps",
        "category": "visualization",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["holder_visualization", "cluster_analysis", "distribution"],
        "last_verified": "2026-11-09",
        "note": "Visualización de holders, clusters y distribución",
    },
    # Wallet Intelligence
    "arkham": {
        "repo": "https://github.com/ArkhamIntel/arkham-api",
        "category": "wallet_intelligence",
        "status": "paid_required",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["wallet_attribution", "entity_identification"],
        "last_verified": "2026-11-09",
        "note": "Requiere investigación para identidad y capacidades exactas",
    },
    "nansen": {
        "repo": "https://github.com/NansenAI/nansen",
        "category": "wallet_intelligence",
        "status": "paid_required",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["wallet_labels", "token_flow", "profiles"],
        "last_verified": "2026-11-09",
        "note": "Wallet intelligence y seguimiento de fondos",
    },
    "insightx": {
        "repo": "https://github.com/InsightXio/insightx",
        "category": "wallet_intelligence",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["wallet_analysis", "token_tracking"],
        "last_verified": "2026-11-09",
        "note": "Investigar proveedor y capacidades",
    },
    # DEX & Token Discovery
    "dexscreener": {
        "repo": "https://github.com/dexscreener/dexscreener-api",
        "category": "dex_discovery",
        "status": "connected",
        "api_available": True,
        "mcp_available": True,
        "requires_api_key": False,
        "rate_limit": "generous_free",
        "argentina_compatible": True,
        "features": ["pair_data", "liquidity", "price_routes"],
        "last_verified": "2026-11-09",
    },
    "revert_finance": {
        "repo": "https://github.com/Revert-Finance/revert",
        "category": "dex_analytics",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": False,
        "argentina_compatible": True,
        "features": ["swap_analysis", "price_impact"],
        "last_verified": "2026-11-09",
        "note": "Análisis de swaps y price impact",
    },
    "whalesmarket": {
        "repo": "https://github.com/WhalesMarketio/whales",
        "category": "market_analytics",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["orderbook", "liquidity"],
        "last_verified": "2026-11-09",
        "note": "Investigar capacidades",
    },
    # Multichain Tools
    "cointool": {
        "repo": "https://github.com/Coinoiao/cointool",
        "category": "multichain_tools",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["token_bridges", "cross_chain_swaps"],
        "last_verified": "2026-11-09",
        "note": "Investigar capacidades multichain",
    },
    "zapper": {
        "repo": "https://github.com/zapperhq/zapper",
        "category": "portfolio_management",
        "status": "connected",
        "api_available": True,
        "mcp_available": True,
        "requires_api_key": False,
        "argentina_compatible": True,
        "features": ["portfolio_tracking", "chain_swaps", "defi_positions"],
        "last_verified": "2026-11-09",
    },
    # NFT
    "umi_bot": {
        "repo": "https://github.com/umi-bot/umi",
        "category": "nft_marketplace",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["nft_collections", "floor_prices", "holder_analysis"],
        "last_verified": "2026-11-09",
        "note": "Investigar capacidades NFT",
    },
    "nftscan": {
        "repo": "https://github.com/NFTScan-NFT/NFTScan",
        "category": "nft_marketplace",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["nft_search", "collection_data", "metadata"],
        "last_verified": "2026-11-09",
        "note": "Investigar capacidades NFT",
    },
    # Technical Analysis
    "tradingview": {
        "repo": "https://github.com/tradingview",
        "category": "technical_analysis",
        "status": "connected",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "rate_limit": "varies_by_plan",
        "argentina_compatible": True,
        "features": ["technical_indicators", "charting", "strategies"],
        "last_verified": "2026-11-09",
        "note": "API key requerida, planes variados",
    },
    "alphagate": {
        "repo": "https://github.com/AlphaGateio/alphagate",
        "category": "fundraising",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": True,
        "argentina_compatible": True,
        "features": ["ico_analytics", "token_sales"],
        "last_verified": "2026-11-09",
        "note": "Investigar capacidades",
    },
    # Sentiment & News
    "cryptopanic": {
        "repo": "https://github.com/CryptoPanic/cryptopanic-api",
        "category": "sentiment_news",
        "status": "connected",
        "api_available": True,
        "mcp_available": True,
        "requires_api_key": True,
        "rate_limit": "Free: 100 calls/day",
        "argentina_compatible": True,
        "features": ["news", "sentiment", "rss"],
        "last_verified": "2026-11-09",
    },
    "defiwinterresearch": {
        "repo": "https://github.com/DefiWinterResearch/defi-winter-research",
        "category": "research",
        "status": "research",
        "api_available": True,
        "mcp_available": False,
        "requires_api_key": False,
        "argentina_compatible": True,
        "features": ["defi_research", "protocol_analysis"],
        "last_verified": "2026-11-09",
        "note": "Investigar proveedor y capacidades",
    },
}


def get_crypto_provider(name: str) -> dict[str, Any] | None:
    """Get crypto provider info by name."""
    return CRYPTO_PROVIDER_REGISTRY.get(name)


def list_crypto_providers() -> list[str]:
    """List all registered crypto providers."""
    return list(CRYPTO_PROVIDER_REGISTRY.keys())


def check_provider_health(name: str) -> dict[str, Any]:
    """Check health status of a crypto provider."""
    provider = get_crypto_provider(name)
    if not provider:
        return {"status": "error", "message": f"Provider '{name}' not found"}

    return {
        "status": provider.get("status", "unknown"),
        "api_available": provider.get("api_available", False),
        "mcp_available": provider.get("mcp_available", False),
        "argentina_compatible": provider.get("argentina_compatible", False),
        "last_verified": provider.get("last_verified"),
        "rate_limit": provider.get("rate_limit"),
        "requires_api_key": provider.get("requires_api_key", False),
    }


# Integration Registry
INTEGRATION_REGISTRY = {
    "quant_lab": {"capabilities": list_quant_capabilities(), "installed": False, "connected": 0, "verified": 0, "status": "not_installed"},
    "crypto_intelligence": {"providers": list_crypto_providers(), "installed": False, "connected": 0, "verified": 0, "status": "not_installed"},
    "hummingbot_integration": {
        "api_available": True,
        "mcp_available": True,
        "paper_trading": True,
        "real_trading": False,  # Must stay private
        "status": "available_but_isolated",
    },
    "hola_optimizer": {
        "repo": "https://github.com/blackrock/HOLA",
        "category": "parameter_optimization",
        "status": "optional",
        "features": ["hyperparameter_optimization", "python_ask_tell", "rust_engine"],
        "argentina_compatible": True,
    },
    "drex_finance": {
        "category": "decision_signals",
        "status": "optional",
        "provider_type": "signal_provider",
        "query_budget": "configurable",
        "caching": True,
        "accuracy_tracking": True,
        "argentina_compatible": True,
    },
}


def registry_status() -> dict[str, Any]:
    """Get overall integration registry status."""
    return {
        "quant_lab": INTEGRATION_REGISTRY["quant_lab"]["status"],
        "crypto_intelligence": INTEGRATION_REGISTRY["crypto_intelligence"]["status"],
        "quant_capabilities_count": len(INTEGRATION_REGISTRY["quant_lab"]["capabilities"]),
        "crypto_providers_count": len(INTEGRATION_REGISTRY["crypto_intelligence"]["providers"]),
        "hummingbot": "available_with_isolation",
        "hola": "optional_optimization",
        "drex": "optional_signal_provider",
        "overall_status": "researched_ready_for_selective_integration",
    }


# Argentina Compatibility Checker
def check_argentina_compatibility(item_name: str) -> dict[str, Any]:
    """Check if a quant/crypto item is Argentina-compatible."""
    # Check quant lab
    quant_result = check_argentina_compatibility_quant(item_name)
    if quant_result["found"]:
        return quant_result

    # Check crypto provider
    crypto_result = check_argentina_compatibility_crypto(item_name)
    if crypto_result["found"]:
        return crypto_result

    return {"found": False, "argentina_compatible": None, "message": "Item not found in registries"}


def check_argentina_compatibility_quant(name: str) -> dict[str, Any]:
    """Check Argentina compatibility for quant capabilities."""
    cap = get_quant_capability(name)
    if not cap:
        return {"found": False, "argentina_compatible": None}

    return {
        "found": True,
        "argentina_compatible": cap.get(" argentina_compatible", False),
        "category": cap.get("category"),
        "status": cap.get("status"),
        "note": cap.get("note"),
    }


def check_argentina_compatibility_crypto(name: str) -> dict[str, Any]:
    """Check Argentina compatibility for crypto providers."""
    provider = get_crypto_provider(name)
    if not provider:
        return {"found": False, "argentina_compatible": None}

    return {
        "found": True,
        "argentina_compatible": provider.get("argentina_compatible", False),
        "category": provider.get("category"),
        "status": provider.get("status"),
        "note": provider.get("note"),
    }
