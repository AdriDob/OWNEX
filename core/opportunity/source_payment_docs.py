# Payment documentation for opportunity sources
# Single Source of Truth: cores/opportunity/source_payment_docs.py
# This module re-exports from cores for backward compatibility

from __future__ import annotations

# Documented payment methods for various platforms
# Format: {platform_name: {methods: [...], currencies: [...], ...}}
KNOWN_PAYMENT_METHODS = {
    # Alignerr platforms
    "alignerr": {
        "methods": ["usdc", "usdt", "payoneer", "airtm", "crypto", "btc", "eth"],
        "currencies": ["USD"],
    },
    # codeforai.tech platforms
    "codeforai": {
        "methods": ["usdc", "usdt", "crypto", "btc", "eth", "stablecoin"],
        "currencies": ["USD"],
    },
    # datannotation platforms
    "datannotation": {
        "methods": ["usdc", "usdt", "airtm", "payoneer", "crypto", "btc", "eth"],
        "currencies": ["USD"],
    },
    # Generic fallback
    "default": {
        "methods": ["usdc", "usdt", "crypto"],
        "currencies": ["USD"],
    },
}


def get_methods_for_platform(platform: str) -> list[str]:
    """Get documented payment methods for a platform."""
    platform_lower = platform.lower()
    if platform_lower in KNOWN_PAYMENT_METHODS:
        return KNOWN_PAYMENT_METHODS[platform_lower]["methods"]
    return KNOWN_PAYMENT_METHODS["default"]["methods"]


def get_currencies_for_platform(platform: str) -> list[str]:
    """Get supported currencies for a platform."""
    platform_lower = platform.lower()
    if platform_lower in KNOWN_PAYMENT_METHODS:
        return KNOWN_PAYMENT_METHODS[platform_lower].get("currencies", ["USD"])
    return KNOWN_PAYMENT_METHODS["default"]["currencies"]
