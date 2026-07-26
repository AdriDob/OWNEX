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
    pending_manual_note: str = ""  # shown when disconnected


# ── Built-in integrations ────────────────────────────────────────
# These define what the system knows about. Status is checked at runtime.

BUILTIN_INTEGRATIONS: list[IntegrationDef] = [
    # ── Bug Bounty Platforms ──
    IntegrationDef(
        "hackerone",
        "platform",
        "HackerOne bug bounty platform",
        env_keys=["HACKERONE_API_USERNAME", "HACKERONE_API_TOKEN"],
        vault_provider="hackerone",
        tags=["bugbounty"],
        pending_manual_note="Setear HACKERONE_API_USERNAME y HACKERONE_API_TOKEN desde HackerOne > Settings > API",
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
        "telegram",
        "messaging",
        "Telegram bot for push notifications",
        env_keys=["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
        vault_provider="telegram",
        tags=["notification"],
        pending_manual_note="Crear bot con @BotFather, setear TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID",
    ),
    IntegrationDef(
        "whatsapp",
        "messaging",
        "WhatsApp via Twilio for notifications",
        vault_provider="twilio",
        env_keys=["CATEYE_TWILIO_ACCOUNT_SID"],
        tags=["notification"],
    ),
    IntegrationDef(
        "discord",
        "messaging",
        "Discord webhook for push notifications",
        env_keys=["CATEYE_DISCORD_WEBHOOK_URL"],
        vault_provider="discord",
        tags=["notification"],
    ),
    # ── Infrastructure ──
    IntegrationDef("identity_vault", "infrastructure", "Encrypted credential store (AES-256-GCM)", tags=["system"]),
    IntegrationDef("event_bus", "infrastructure", "Internal pub/sub event system", tags=["system"]),
    IntegrationDef("database", "infrastructure", "SQLite / PostgreSQL database backend", tags=["system"]),
    # ── Fiscal / Tax ──
    IntegrationDef(
        "arca",
        "financial",
        "ARCA (ex AFIP) — Argentine tax authority electronic invoicing",
        env_keys=["ARCA_CUIT", "ARCA_CERT_PATH", "ARCA_ENVIRONMENT"],
        vault_provider="arca",
        tags=["tax", "argentina", "invoicing"],
    ),
    # ── Productivity ──
    IntegrationDef(
        "outlook",
        "messaging",
        "Microsoft Outlook / Graph API — email, calendar, contacts sync",
        env_keys=["CATEYE_OUTLOOK_CLIENT_ID", "CATEYE_OUTLOOK_TENANT_ID"],
        vault_provider="outlook",
        tags=["productivity", "email", "calendar"],
    ),
    # ── Bug Bounty Intelligence (Open Source integrations) ──
    IntegrationDef(
        "claude_bug_bounty",
        "intelligence",
        "claude-bug-bounty (shuvonsec) — 20 vuln class autonomous hunting pipeline",
        icon="🎯",
        health_check="core.integrations.ext.hunter_bridge.check_hunter",
        docs_url="https://github.com/shuvonsec/claude-bug-bounty",
        tags=["bugbounty", "opensource", "claude-code", "hunting"],
        pending_manual_note="git clone https://github.com/shuvonsec/claude-bug-bounty.git ~/.orion/tools/claude-bug-bounty",
    ),
    IntegrationDef(
        "web3_bug_bounty_skills",
        "intelligence",
        "Web3 Bug Bounty Skills (freloque) — 18 smart contract classes from 2,749 Immunefi reports",
        icon="🔗",
        health_check="core.integrations.ext.hunter_bridge.check_web3_skills",
        docs_url="https://github.com/freloque/web3-bug-bounty-hunting-ai-skills",
        tags=["web3", "opensource", "claude-code", "smart-contracts"],
        pending_manual_note="git clone https://github.com/freloque/web3-bug-bounty-hunting-ai-skills.git ~/.orion/tools/web3-bug-bounty-skills",
    ),
    IntegrationDef(
        "bounty_hunter_mcp",
        "intelligence",
        "Bounty Hunter MCP (L-ubu) — MCP server with route extraction, SSRF callback, CVSS scoring",
        icon="🔌",
        health_check="core.integrations.ext.hunter_bridge.check_mcp_hunter",
        docs_url="https://github.com/L-ubu/bounty-hunter-mcp",
        tags=["mcp", "opensource", "claude-code", "tool"],
        pending_manual_note="git clone https://github.com/L-ubu/bounty-hunter-mcp.git ~/.orion/tools/bounty-hunter-mcp && cd ~/.orion/tools/bounty-hunter-mcp && uv sync",
    ),
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
