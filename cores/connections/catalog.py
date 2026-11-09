"""Canonical catalog of connectable providers across OWNEX domains.

Each entry describes HOW a human connects and syncs real data — never
credentials. Consumed by ``api/routers/connection_manager.py`` to expose
per-provider setup actions to the frontend.

Domains:
- ``opportunity``: work/bounty platforms (filled from SOURCE_PLATFORM_MAP + vault)
- ``investment_ar``: Argentine brokers, wallets and fintechs
- ``ai_tool``: external AI tooling OWNEX can drive or integrate with
- ``infra``: infrastructure OWNEX itself may consume
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderSetup:
    """Human-facing setup instructions for one connectable provider."""

    domain: str
    login_url: str = ""
    docs_url: str = ""
    credential_fields: tuple[str, ...] = ("email", "token")
    sync_mode: str = "manual_export"  # api | manual_export | cli | none
    setup_steps: tuple[str, ...] = ()
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "login_url": self.login_url,
            "docs_url": self.docs_url,
            "credential_fields": list(self.credential_fields),
            "sync_mode": self.sync_mode,
            "setup_steps": list(self.setup_steps),
            "notes": self.notes,
        }


# ── Argentine investment / fintech providers ──────────────────────────────
# sync_mode "api" = OWNEX can pull real data with stored credentials.
# "manual_export" = user exports/imports data manually; OWNEX stores snapshots.
# "cli" = external CLI tool the user installs and authenticates.

INVESTMENT_AR: dict[str, ProviderSetup] = {
    "iol": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.invertironline.com",
        docs_url="https://developers.iolinversiones.com",
        credential_fields=("email", "password"),
        sync_mode="api",
        setup_steps=(
            "Abrí tu cuenta comitente en IOL Inversiones",
            "Generá/confirmá tu usuario y contraseña de plataforma",
            "Conectá acá con email + contraseña — OWNEX obtiene un token JWT",
            "Usá 'Sincronizar' para traer saldos y posiciones reales (ARS/USD)",
        ),
        notes="API REST + WebSocket gratuita para clientes IOL. Cubre acciones, CEDEARs, bonos, FCIs, cripto.",
    ),
    "cocos": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.cocos.capital",
        credential_fields=("email", "password"),
        sync_mode="manual_export",
        setup_steps=(
            "Cocos no tiene API pública — la conexión queda como MANUAL_SETUP",
            "En la app/web de Cocos exportá tu resumen de portafolio (captura o PDF/CSV)",
            "Pegá el resumen en el snapshot de sincronización manual",
        ),
        notes="Broker argentino (FCI, acciones, CEDEARs). Sync manual hasta que exista API.",
    ),
    "uala": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.uala.com.ar",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        setup_steps=(
            "Ualá no expone API pública de portafolio",
            "En la app, sacá captura del resumen de inversiones/cripto",
            "Cargá el snapshot manual en OWNEX",
        ),
        notes="Billetera + inversiones + cripto. Sync manual.",
    ),
    "ripio": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.ripio.com",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        setup_steps=(
            "Ripio no tiene API pública para clientes minoristas",
            "Exportá movimientos/saldos desde la app o web",
            "Cargá el snapshot manual en OWNEX",
        ),
        notes="Cripto + pesos. Sync manual.",
    ),
    "belo": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.belo.app",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        setup_steps=(
            "Belo no tiene API pública de cuenta",
            "Exportá el resumen de tu portfolio desde la app",
            "Cargá el snapshot manual en OWNEX",
        ),
        notes="Broker cripto/regulado argentino. Sync manual.",
    ),
    "balanz": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.balanz.com",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        setup_steps=(
            "Balanz no tiene API pública para retail",
            "Descargá el estado de cuenta / resumen de posiciones",
            "Cargá el snapshot manual en OWNEX",
        ),
        notes="ALyC con cauciones, MEP, FCIs. Sync manual.",
    ),
    "ppi": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.portfoliopersonal.com",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        setup_steps=(
            "PPI (Portfolio Personal Inversiones) no tiene API pública",
            "Descargá el resumen de tu comitente",
            "Cargá el snapshot manual en OWNEX",
        ),
        notes="ALyC clásica: bonos, CEDEARs, acciones. Sync manual.",
    ),
    "ieb": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.ieb.com.ar",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        setup_steps=(
            "IEB no tiene API pública para retail",
            "Exportá posiciones y saldos desde homebanking",
            "Cargá el snapshot manual en OWNEX",
        ),
        notes="ALyC/banco con cauciones y FCI. Sync manual.",
    ),
    "buenbit": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.buenbit.com",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        setup_steps=(
            "Buenbit no tiene API pública de portafolio",
            "Exportá movimientos desde la app",
            "Cargá el snapshot manual en OWNEX",
        ),
        notes="Exchange cripto argentino. Sync manual.",
    ),
    "lemon": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.lemon.me",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        setup_steps=(
            "Lemon Cash no tiene API pública para retail",
            "Exportá movimientos/saldos desde la app",
            "Cargá el snapshot manual en OWNEX",
        ),
        notes="Billetera virtual + cripto. Sync manual.",
    ),
}

# ── AI tools OWNEX can drive or integrate with ────────────────────────────

AI_TOOLS: dict[str, ProviderSetup] = {
    "perchai": ProviderSetup(
        domain="ai_tool",
        login_url="https://chat.perchai.app",
        docs_url="https://www.perchai.app/docs",
        credential_fields=("email", "token"),
        sync_mode="cli",
        setup_steps=(
            "Perch AI no tiene API de inferencia pública — se usa vía CLI/MCP",
            "Instalá el CLI: npm install -g perchai-cli",
            "Autenticá el CLI con tu cuenta Perch (starter es gratis, sin tarjeta)",
            "OWNEX puede invocar `perch` en terminal para tareas de agentes/documentos",
        ),
        notes="Multi-agent AI (web/desktop/CLI), MCP-compatible, citas verificables.",
    ),
}

# ── Infrastructure OWNEX may consume ──────────────────────────────────────

INFRA: dict[str, ProviderSetup] = {
    "opensandbox": ProviderSetup(
        domain="infra",
        login_url="https://open-sandbox.ai",
        docs_url="https://github.com/opensandbox-group/OpenSandbox",
        credential_fields=(),
        sync_mode="none",
        setup_steps=(
            "OpenSandbox es runtime de sandboxes para agentes IA (self-hosted)",
            "Requiere deploy propio (Kubernetes/manifests) — no es una cuenta",
            "Evaluar como backend de ejecución aislada para agentes OWNEX",
        ),
        notes="Sandbox runtime open-source (Apache-2.0). Infra opcional, no conexión de datos.",
    ),
}

# Providers with a real API sync implemented in OWNEX today.
API_SYNC_PROVIDERS = {"iol"}
