"""Security Niches Registry (G1+G2) — subnichos de seguridad + fuentes VRP premium.

Decisión owner 2026-08-26: jerarquía de nichos para maximizar payout temprano
con barrera formal 0. NO extiende el enum canónico todavía (work_taxonomy
exige mapeo exhaustivo por CI); registra los subnichos como metadatos curados
que alimentan discovery/scoring cuando existan adapters.

Motores (Fase G3): cada nicho pertenece a un motor del portafolio:
CASHFLOW 🟢 · SOFTWARE 🔵 · SECURITY 🔴 · FRONTIER 🟣 · EXTREME 🟡
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Engine(StrEnum):
    CASHFLOW = "cashflow"  # 🟢 primer dólar rápido
    SOFTWARE = "software"  # 🔵 subir $/hora
    SECURITY = "security"  # 🔴 payouts grandes
    FRONTIER = "frontier"  # 🟣 mercados nuevos sin saturar
    EXTREME = "extreme_upside"  # 🟡 jackpots 6-7 cifras


@dataclass(frozen=True)
class SecurityNiche:
    slug: str
    name: str
    engine: Engine
    payout_potential: str  # rango real documentado
    barrier_technical: str  # low | medium | high | very_high
    automation_fit: int  # 0-100: cuánto puede asistir OWNEX
    attack_classes: tuple[str, ...]
    entry_programs: tuple[str, ...]  # programas concretos para arrancar

    def as_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "engine": self.engine.value,
            "payout_potential": self.payout_potential,
            "barrier_technical": self.barrier_technical,
            "automation_fit": self.automation_fit,
            "attack_classes": list(self.attack_classes),
            "entry_programs": list(self.entry_programs),
        }


# ── Subnichos priorizados por payout × barrera × automatizabilidad ──

SECURITY_NICHES: tuple[SecurityNiche, ...] = (
    SecurityNiche(
        slug="ai_llm_security",
        name="AI / LLM / Agent Security",
        engine=Engine.FRONTIER,
        payout_potential="$15k–100k+ por hallazgo (VRPs AI); mercado nuevo, poca competencia",
        barrier_technical="medium",
        automation_fit=95,
        attack_classes=(
            "prompt_injection",
            "indirect_prompt_injection",
            "agent_privilege_escalation",
            "tool_poisoning",
            "mcp_abuse",
            "rag_data_exfil",
            "excessive_agency",
            "cross_tenant_access",
            "secrets_leakage",
            "sandbox_escape",
        ),
        entry_programs=(
            "OpenAI Bug Bounty",
            "Anthropic Bug Bounty",
            "Google AI VRP",
            "HackerOne AI engagements",
            "Microsoft AI Bounty",
        ),
    ),
    SecurityNiche(
        slug="identity_iam",
        name="Identity / Auth / IAM",
        engine=Engine.SECURITY,
        payout_potential="$500–25k; relación payout/complejidad atractiva",
        barrier_technical="medium",
        automation_fit=90,
        attack_classes=(
            "bola_idor",
            "oauth_misconfig",
            "jwt_flaws",
            "session_management",
            "rbac_abac_bypass",
            "tenant_isolation",
            "invitation_flows",
            "api_key_scoping",
            "account_recovery",
        ),
        entry_programs=("HackerOne SaaS", "Bugcrowd multi-tenant", "Intigriti enterprise"),
    ),
    SecurityNiche(
        slug="web_api_authorization",
        name="Web / API Authorization",
        engine=Engine.SECURITY,
        payout_potential="$300–15k; motor de cashflow de seguridad",
        barrier_technical="medium",
        automation_fit=85,
        attack_classes=(
            "bola",
            "broken_access_control",
            "privilege_escalation",
            "business_logic",
            "race_conditions",
            "payment_logic",
            "webhook_abuse",
            "ssrf",
        ),
        entry_programs=("HackerOne public", "Bugcrowd public", "YesWeHack"),
    ),
    SecurityNiche(
        slug="cloud_infra",
        name="Cloud Infrastructure Security",
        engine=Engine.SECURITY,
        payout_potential="$5k–133k/cadena (Microsoft Zero Day Quest $100k cat.)",
        barrier_technical="high",
        automation_fit=70,
        attack_classes=(
            "iam_escalation",
            "s3_misconfig",
            "metadata_ssrf_chain",
            "serverless_abuse",
            "k8s_escape",
            "cicd_credential_leak",
            "tenant_isolation_cloud",
        ),
        entry_programs=("Microsoft Zero Day Quest", "Google VRP", "AWS Bounty", "Vercel Sandbox Challenge ($1M)"),
    ),
    SecurityNiche(
        slug="defi_smart_contracts",
        name="DeFi / Smart Contracts",
        engine=Engine.EXTREME,
        payout_potential="$50k–3M (Ethena $3M · Immutable $1M · Polygon $250k)",
        barrier_technical="very_high",
        automation_fit=40,
        attack_classes=(
            "reentrancy",
            "oracle_manipulation",
            "bridge_logic",
            "flash_loan_attacks",
            "accounting_drift",
            "access_control_defi",
            "liquidation_logic",
        ),
        entry_programs=("Immunefi (186 programas)", "Code4rena", "Sherlock", "Cantina"),
    ),
    SecurityNiche(
        slug="oss_supply_chain",
        name="OSS / Supply Chain",
        engine=Engine.SECURITY,
        payout_potential="$500–30k + reputación compuesta",
        barrier_technical="medium",
        automation_fit=80,
        attack_classes=(
            "dependency_confusion",
            "package_takeover",
            "prototype_pollution",
            "insecure_deserialization",
            "malicious_packages",
            "leaked_secrets",
            "github_actions_injection",
        ),
        entry_programs=("GitHub Security Lab", "npm/PyPI security programs", "Google OSS VRP"),
    ),
    SecurityNiche(
        slug="fintech_payment_logic",
        name="Fintech / Payment Logic",
        engine=Engine.SECURITY,
        payout_potential="$1k–50k; lógica de negocio > criptografía",
        barrier_technical="medium",
        automation_fit=75,
        attack_classes=(
            "payment_state_trust",
            "refund_abuse",
            "coupon_race",
            "wallet_double_spend",
            "withdrawal_limit_bypass",
            "merchant_admin_separation",
        ),
        entry_programs=("Fintech programs en H1/Bugcrowd", "Stripe ecosystem"),
    ),
    SecurityNiche(
        slug="devops_cicd",
        name="DevOps / CI-CD Security",
        engine=Engine.SECURITY,
        payout_potential="$2k–40k; cadena CI→cloud credential→production",
        barrier_technical="high",
        automation_fit=75,
        attack_classes=(
            "runner_compromise",
            "ci_token_leakage",
            "artifact_registry_persistence",
            "pipeline_injection",
            "helm_terraform_abuse",
        ),
        entry_programs=("GitLab Bounty", "GitHub Actions research", "Jenkins programs"),
    ),
)


def get_niches(engine: Engine | None = None) -> list[SecurityNiche]:
    """Nichos filtrados por motor (None = todos)."""
    return [n for n in SECURITY_NICHES if engine is None or n.engine == engine]


def get_vrp_entry_programs() -> list[dict[str, str]]:
    """Programas VRP/premium deduplicados con URL de entrada."""
    urls = {
        "OpenAI Bug Bounty": "https://bugcrowd.com/openai",
        "Anthropic Bug Bounty": "https://hackerone.com/anthropic",
        "Google AI VRP": "https://bughunters.google.com",
        "Microsoft Zero Day Quest": "https://www.microsoft.com/en-us/msrc/bounty",
        "Google VRP": "https://bughunters.google.com",
        "Vercel Sandbox Challenge": "https://vercel.com/security",
        "Immunefi (186 programas)": "https://immunefi.com/bug-bounty/",
        "HackerOne AI engagements": "https://hackerone.com/opportunities?asset_type=URL",
    }
    return [{"program": p, "url": u} for p, u in urls.items()]


# Motor recomendado para ARRANCAR (owner: payout temprano + frontera sin saturar)
RECOMMENDED_STARTER_ENGINE = Engine.FRONTIER
