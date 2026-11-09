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
    integration_method: str = ""  # api_rest | api_rest_ws | mcp_remote | cli | manual_import | browser_session
    permissions: tuple[str, ...] = ()  # read-only permission set granted to OWNEX
    mcp_url: str = ""  # official remote MCP endpoint, if the provider publishes one

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "login_url": self.login_url,
            "docs_url": self.docs_url,
            "credential_fields": list(self.credential_fields),
            "sync_mode": self.sync_mode,
            "setup_steps": list(self.setup_steps),
            "notes": self.notes,
            "integration_method": self.integration_method
            or {
                "api": "api_rest",
                "manual_export": "manual_import",
                "cli": "cli",
                "none": "none",
            }.get(self.sync_mode, ""),
            "permissions": list(self.permissions),
            "mcp_url": self.mcp_url,
        }


# Read-only permission set applied to every financial connection by default.
# Write/trade/withdrawal capabilities are NEVER granted by OWNEX.
READ_ONLY_PERMISSIONS = (
    "PUBLIC_DATA_READ",
    "PRIVATE_ACCOUNT_READ",
    "PORTFOLIO_READ",
    "TRANSACTION_READ",
)


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
        integration_method="api_rest_ws",
        permissions=READ_ONLY_PERMISSIONS,
        mcp_url="https://mcp.invertironline.com",
        setup_steps=(
            "Abrí tu cuenta comitente en IOL Inversiones",
            "Confirmá tu usuario y contraseña de plataforma (la API usa OAuth2 password grant)",
            "Conectá acá con email + contraseña — OWNEX obtiene un token JWT",
            "IOL además publica MCP oficial https://mcp.invertironline.com (OAuth interactivo en browser, modos Automático/Confirmar/Solo lectura) — pensable para Hermes/OpenCode/Perch como cliente MCP",
            "Usá 'Sincronizar' para traer saldos, posiciones y movimientos reales (ARS/USD)",
        ),
        notes="API REST + WebSocket (stream-marketdata) + MCP oficial con OAuth. Solo lectura en OWNEX: nunca opera ni retira.",
    ),
    "ppi": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.portfoliopersonal.com",
        docs_url="https://itatppi.github.io/ppi-official-api-docs/",
        credential_fields=("email", "token", "password"),
        sync_mode="api",
        integration_method="api_rest",
        permissions=READ_ONLY_PERMISSIONS,
        setup_steps=(
            "En PPI entrá a Gestiones → Gestión de servicio API y activá el servicio",
            "Generá tus credenciales: ApiKey, ApiSecret, AuthorizedClient y ClientKey",
            "En OWNEX: email = alias de cuenta, token = ApiKey, password = ApiSecret",
            "Enviá AuthorizedClient y ClientKey en metadata al conectar (metadata.authorized_client / client_key)",
            "Usá 'Sincronizar' para traer cuentas, saldos, posiciones y movimientos",
        ),
        notes="API REST oficial v1.0 con sandbox. LoginApi devuelve accessToken+refreshToken. Solo lectura.",
    ),
    "binance": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.binance.com",
        docs_url="https://developers.binance.com",
        credential_fields=("email", "token", "password"),
        sync_mode="api",
        integration_method="api_rest",
        permissions=READ_ONLY_PERMISSIONS,
        setup_steps=(
            "En Binance generá una API key con permisos SOLO de lectura (Enable Reading)",
            "NO habilites trading, withdrawals ni transfers — OWNEX es solo lectura",
            "Restringí la key por IP si es posible",
            "En OWNEX: email = alias, token = API Key, password = API Secret",
            "Usá 'Sincronizar' para traer balances spot y datos de cuenta",
        ),
        notes="API oficial ccxt. Config inicial: USER_DATA/lectura + datos públicos. Sin trading ni retiros.",
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
        integration_method="manual_import",
        permissions=READ_ONLY_PERMISSIONS,
        setup_steps=(
            "Ripio Retail API existe pero su disponibilidad para clientes argentinos",
            "y permisos de lectura debe verificarse por cuenta — OWNEX la clasifica CONDITIONAL",
            "Mientras tanto: exportá movimientos/saldos desde la app o web",
            "Cargá el snapshot manual o importá el archivo exportado",
        ),
        notes="CONDITIONAL: apidocs.ripio.com contempla lectura y retiros — OWNEX solo lectura. Sync manual hasta verificar disponibilidad AR.",
    ),
    "bullmarket": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.bullmarket.com.ar",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        integration_method="manual_import",
        permissions=READ_ONLY_PERMISSIONS,
        setup_steps=(
            "Bull Market Brokers: API/exportaciones oficiales pendientes de verificación",
            "Descargá estado de cuenta o resumen de cartera desde la plataforma",
            "Importá el archivo o cargá el snapshot manual",
        ),
        notes="Broker argentino. Integración pendiente de verificación — importación manual.",
    ),
    "banza": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.banza.com.ar",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        integration_method="manual_import",
        permissions=READ_ONLY_PERMISSIONS,
        setup_steps=(
            "Banza: métodos de integración pendientes de investigación",
            "Exportá resumen de inversiones desde la app/web",
            "Importá el archivo o cargá el snapshot manual",
        ),
        notes="Fintech de inversión argentina. Importación manual.",
    ),
    "inviu": ProviderSetup(
        domain="investment_ar",
        login_url="https://www.inviu.com.ar",
        credential_fields=("email", "token"),
        sync_mode="manual_export",
        integration_method="manual_import",
        permissions=READ_ONLY_PERMISSIONS,
        setup_steps=(
            "Inviu: métodos de integración pendientes de investigación",
            "Exportá estado de cuenta desde la plataforma",
            "Importá el archivo o cargá el snapshot manual",
        ),
        notes="ALyC/banco de inversión. Importación manual.",
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
API_SYNC_PROVIDERS = {"iol", "ppi", "binance"}
