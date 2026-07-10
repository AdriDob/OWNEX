"""Integration Discovery — scans the system for all known integrations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("orion.core.integrations")


@dataclass
class IntegrationDef:
    """Descriptor for a known integration."""

    name: str
    category: str  # exchange, blockchain, platform, ai, messaging, financial
    description: str = ""
    icon: str = "🔌"
    env_keys: list[str] = field(default_factory=list)
    vault_provider: str = ""
    health_check: str = ""  # dotted path to a callable
    docs_url: str = ""
    tags: list[str] = field(default_factory=list)


# ── Built-in integrations ────────────────────────────────────────
# These define what the system knows about. Status is checked at runtime.

BUILTIN_INTEGRATIONS: list[IntegrationDef] = [
    # ── Bug Bounty Platforms ──
    IntegrationDef(
        "hackerone",
        "platform",
        "HackerOne bug bounty platform",
        env_keys=["HACKERONE_API_KEY"],
        vault_provider="hackerone",
        tags=["bugbounty"],
    ),
    IntegrationDef(
        "bugcrowd",
        "platform",
        "Bugcrowd bug bounty platform",
        env_keys=["BUGCROWD_TOKEN"],
        vault_provider="bugcrowd",
        tags=["bugbounty"],
    ),
    IntegrationDef("intigriti", "platform", "Intigriti bug bounty platform", tags=["bugbounty"]),
    IntegrationDef("immunefi", "platform", "Immunefi blockchain bug bounty platform", tags=["bugbounty"]),
    # ── AI Providers ──
    IntegrationDef(
        "openai", "ai", "OpenAI API (GPT models)", env_keys=["OPENAI_API_KEY"], vault_provider="openai", tags=["llm"]
    ),
    IntegrationDef(
        "gemini", "ai", "Google Gemini API", env_keys=["GEMINI_API_KEY"], vault_provider="gemini", tags=["llm"]
    ),
    IntegrationDef("ollama", "ai", "Local Ollama inference server", env_keys=["OLLAMA_HOST"], tags=["llm", "local"]),
    # ── Exchanges ──
    IntegrationDef(
        "binance",
        "exchange",
        "Binance cryptocurrency exchange",
        env_keys=["BINANCE_API_KEY", "BINANCE_SECRET_KEY"],
        vault_provider="binance",
        tags=["crypto"],
    ),
    IntegrationDef(
        "coinbase",
        "exchange",
        "Coinbase cryptocurrency exchange",
        env_keys=["COINBASE_API_KEY", "COINBASE_SECRET"],
        vault_provider="coinbase",
        tags=["crypto"],
    ),
    IntegrationDef(
        "kraken",
        "exchange",
        "Kraken cryptocurrency exchange",
        env_keys=["KRAKEN_API_KEY", "KRAKEN_SECRET"],
        vault_provider="kraken",
        tags=["crypto"],
    ),
    # ── Crypto Wallets / Chains ──
    IntegrationDef(
        "solana", "blockchain", "Solana blockchain wallet", vault_provider="solana", tags=["crypto", "wallet"]
    ),
    IntegrationDef(
        "bitcoin", "blockchain", "Bitcoin blockchain wallet", vault_provider="btc", tags=["crypto", "wallet"]
    ),
    IntegrationDef(
        "evm",
        "blockchain",
        "EVM-compatible chain (ETH/Polygon/BSC/Arbitrum)",
        vault_provider="evm",
        tags=["crypto", "wallet"],
    ),
    IntegrationDef("tron", "blockchain", "Tron blockchain wallet", vault_provider="tron", tags=["crypto", "wallet"]),
    # ── Financial ──
    IntegrationDef("coingecko", "financial", "CoinGecko cryptocurrency price feed", tags=["prices"]),
    IntegrationDef(
        "takenos", "financial", "Takenos fiat/crypto payment processor", vault_provider="takenos", tags=["payments"]
    ),
    # ── Messaging ──
    IntegrationDef(
        "gmail",
        "messaging",
        "Gmail OAuth2 for email notifications",
        vault_provider="gmail",
        env_keys=["CATEYE_GMAIL_CLIENT_ID"],
        tags=["notification"],
    ),
    IntegrationDef(
        "telegram", "messaging", "Telegram bot for push notifications", vault_provider="telegram", tags=["notification"]
    ),
    IntegrationDef(
        "whatsapp",
        "messaging",
        "WhatsApp via Twilio for notifications",
        vault_provider="twilio",
        env_keys=["CATEYE_TWILIO_ACCOUNT_SID"],
        tags=["notification"],
    ),
    # ── Infrastructure ──
    IntegrationDef("identity_vault", "infrastructure", "Encrypted credential store (AES-256-GCM)", tags=["system"]),
    IntegrationDef("event_bus", "infrastructure", "Internal pub/sub event system", tags=["system"]),
    IntegrationDef("database", "infrastructure", "SQLite / PostgreSQL database backend", tags=["system"]),
]


def get_builtin_integrations() -> list[IntegrationDef]:
    return list(BUILTIN_INTEGRATIONS)


def get_integrations_by_category(category: str) -> list[IntegrationDef]:
    return [i for i in BUILTIN_INTEGRATIONS if i.category == category]


def get_integration(name: str) -> IntegrationDef | None:
    for i in BUILTIN_INTEGRATIONS:
        if i.name == name:
            return i
    return None
