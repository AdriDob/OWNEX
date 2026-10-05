"""Setup Checklist — plan de configuración progresiva presentado como tarea diaria.

OWNEX presenta UNA tarea de configuración por día hasta llegar al 100% de
configuración para su óptimo uso diario. Los ítems con detección automática se
completan solos cuando el estado real del sistema los confirma (nunca se marca
done por decreto); los ítems de onboarding externo (assessments, perfiles en
plataformas de terceros) se marcan manual y persisten en ``data/setup_checklist.json``.

Reutiliza detectores existentes — cero duplicación (Regla de Oro):
- ProfileKitEngine.has_profile()            → perfil del usuario guardado
- PaymentCompatibilityEngine                → cuentas de pago configuradas
- cores.credentials.vault.get_credentials()  → API keys de plataformas
- env keys remotas u Ollama local            → proveedor de IA disponible
- database SessionLocal(Target)             → al menos un target agregado
- VaultManager (Knowledge Bridge)           → vault de Obsidian conectado
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("cores.setup.checklist")

STORE_FILENAME = "setup_checklist.json"

PHASE_ESSENTIALS = "essentials"
PHASE_PLATFORMS = "platforms"
PHASE_OPTIONAL = "optional"

PHASE_LABELS = {
    PHASE_ESSENTIALS: "Esencial para ingreso",
    PHASE_PLATFORMS: "Onboarding de plataformas",
    PHASE_OPTIONAL: "Opcional",
}

_AUTO = True
_MANUAL = False


def _default_store_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / STORE_FILENAME


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ── Detectores (introspeccionan estado real; nunca inventan) ──


def _detect_profile_kit() -> bool:
    try:
        from cores.direct_work_engine.profile_kit import ProfileKitEngine

        return bool(ProfileKitEngine().has_profile())
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector profile_kit falló: %s", exc)
        return False


def _detect_payment_accounts(min_rails: int = 3) -> bool:
    """True when ≥``min_rails`` payment accounts are configured.

    MONEY VALIDATION + SETUP_BLOCKERS: con 1 solo rail la cobrabilidad real
    sigue siendo dudosa y P(CASH) no se puede afirmar. El mínimo honesto para
    'podés cobrar' son 3 rails (US/wire + internacional + local ARS).
    """
    try:
        from cores.payment_compat.engine import PaymentCompatibilityEngine

        return len(PaymentCompatibilityEngine().get_configured_accounts()) >= min_rails
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector payment_accounts falló: %s", exc)
        return False


def _detect_bounty_api_key() -> bool:
    try:
        from cores.credentials.vault import get_credentials

        # force_refresh: the vault singletons credentials at import; the user
        # may have just pasted a key and expects the checklist to notice now.
        creds = get_credentials(force_refresh=True)
        return any(
            [
                getattr(creds, "hackerone_api_key", ""),
                getattr(creds, "bugcrowd_api_key", ""),
                getattr(creds, "intigriti_api_key", ""),
                getattr(creds, "yeswehack_api_key", ""),
                getattr(creds, "immunefi_api_key", ""),
            ]
        )
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector bounty_api_key falló: %s", exc)
        return False


def _detect_first_target() -> bool:
    try:
        from database.db import SessionLocal
        from database.models import Target

        with SessionLocal() as session:
            return session.query(Target.id).first() is not None
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector first_target falló: %s", exc)
        return False


def _detect_obsidian_vault() -> bool:
    try:
        from cores.knowledge import VaultManager, load_config

        info = VaultManager(load_config()).verify()
        return bool(info.connected)
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector obsidian_vault falló: %s", exc)
        return False


def _detect_smtp_mail() -> bool:
    try:
        return bool(os.environ.get("OWNNEX_MAIL_SMTP_HOST"))
    except Exception:  # pragma: no cover - trivial
        return False


# Env keys that prove a remote AI provider is configured (no network call).
_AI_API_KEY_ENVS = (
    # Stack OAR (cores/ai/runtime/adapters.py) — las que leeenabled_providers
    "GROQ_API_KEY",
    "CEREBRAS_API_KEY",
    "TOGETHER_API_KEY",
    "DEEPINFRA_API_KEY",
    "OLLAMA_CLOUD_API_KEY",
    "OMNIROUTE_API_KEY",
    "FREELLMAPI_API_KEY",
    "NVIDIA_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    # Stack legacy (cores/ai/providers/*) — providers que OAR no cubre
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOSEAI_API_KEY",
    "NIM_API_KEY",
    "FCC_API_KEY",
    "OPENCODE_API_KEY",
)


def _ollama_reachable(timeout: float = 2.0) -> bool:
    """True when a local Ollama answers /api/tags. Loopback-only, fast timeout."""
    try:
        import urllib.request

        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        req = urllib.request.Request(f"{host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _detect_ai_provider() -> bool:
    """True when ANY AI provider can serve: remote key configured or Ollama up.

    Without this, copilot/chat/briefs degrade silently — hence essential.
    Order matters: env keys first (instant), Ollama last (loopback, 2s cap).
    """
    try:
        if any(os.environ.get(key) for key in _AI_API_KEY_ENVS):
            return True
        return _ollama_reachable()
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector ai_provider falló: %s", exc)
        return False


def _detect_github_token() -> bool:
    """True when a GitHub token exists (vault github_token o env GITHUB_TOKEN).

    GITHUB_TOKEN es el bloqueador #1 del pipeline de dev bounty: sin él no hay
    claim → clone → PR en Algora/Opire/IssueHunt ni CoderAgent con write de PR.
    """
    try:
        if os.environ.get("GITHUB_TOKEN"):
            return True
        from cores.credentials.vault import get_credentials

        return bool(getattr(get_credentials(force_refresh=True), "github_token", ""))
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector github_token falló: %s", exc)
        return False


def _detect_devbounty_api_key() -> bool:
    """True when at least one dev-bounty platform key exists (Opire/IssueHunt/Algora)."""
    try:
        from cores.credentials.vault import get_credentials

        creds = get_credentials(force_refresh=True)
        return any(
            [
                getattr(creds, "opire_api_key", ""),
                getattr(creds, "issuehunt_api_key", ""),
                getattr(creds, "algora_api_key", ""),
            ]
        )
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector devbounty_api_key falló: %s", exc)
        return False


def _mpt_config_path() -> Path | None:
    """Locate the MoneyPrinterTurbo sidecar config.toml (outside this repo)."""
    candidates = []
    env_path = os.environ.get("MPT_CONFIG_PATH")
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path.home() / "projects" / "MoneyPrinterTurbo" / "config.toml")
    for cand in candidates:
        try:
            if cand.is_file():
                return cand
        except OSError:
            continue
    return None


# ── Detectores por dominio económico (avisan CADA plataforma pendiente) ──


def _platform_env_has(*keys: str) -> bool:
    """True si ALGUNA de las env keys está configurada (no vacía)."""
    return any(bool(os.environ.get(k, "").strip()) for k in keys)


def _detect_trading_exchange() -> bool:
    """Trading CEX (DRY_RUN→LIVE): exchange_api_key + secret."""
    return _platform_env_has("EXCHANGE_API_KEY", "EXCHANGE_SECRET")


def _detect_memecoin_wallet() -> bool:
    """Memecoins (Solana on-chain): helius key o solver/wallet key."""
    return _platform_env_has("HELIUS_API_KEY", "SOLANA_PRIVATE_KEY", "SOLANA_WALLET_PATH")


def _detect_betfair() -> bool:
    """Apuestas deportivas (Betfair): app key + credenciales de login."""
    return _platform_env_has("BETFAIR_APP_KEY", "BETFAIR_USERNAME", "BETFAIR_PASSWORD")


def _detect_outlook() -> bool:
    """Calendario/agenda externa (Outlook/Microsoft Graph)."""
    return _platform_env_has("OUTLOOK_CLIENT_ID", "OUTLOOK_CLIENT_SECRET", "MICROSOFT_CLIENT_ID")


def _detect_ccxt_exchange() -> bool:
    """Inversión/ahorro vía CCXT (Binance/Kraken/etc): keys de exchange."""
    return _platform_env_has("CCXT_API_KEY", "CCXT_SECRET", "BINANCE_API_KEY", "KRAKEN_API_KEY")


def _detect_aux_bounty_keys() -> bool:
    """Keys auxiliares de bug bounty (Cantina/Sherlock/CodeHawks) — upside."""
    return _platform_env_has("CANTINA_API_KEY", "SHERLOCK_API_KEY", "CODEHAWKS_API_KEY", "SYNACK_API_KEY")


def _detect_ai_work_keys() -> bool:
    """Plataformas AI-work/data (Outlier/Mindrift/DataAnnotation) — canal $15-40/h."""
    return _platform_env_has("OUTLIER_API_KEY", "MINDRIFT_API_KEY", "DATAANNOTATION_API_KEY")


def _detect_meta_account() -> bool:
    """Cuenta Meta (Instagram/WhatsApp para ecommerce/social)."""
    return _platform_env_has("META_ACCESS_TOKEN", "IG_USER_ID", "WHATSAPP_PHONE_ID")


def _detect_meli_account() -> bool:
    """Cuenta MercadoLibre (ecommerce: catálogo + ventas + sync)."""
    return _platform_env_has("MELI_ACCESS_TOKEN", "MELI_REFRESH_TOKEN")


def _detect_affiliate_networks() -> bool:
    """Redes de afiliación (Amazon/Hotmart/ClickBank): keys si el workspace está activo."""
    return _platform_env_has("AMAZON_ASSOCIATES_TAG", "HOTMART_TOKEN", "CLICKBANK_DEV_KEY")


def _detect_mpt_material_key() -> bool:
    """True when the MPT sidecar has a free stock-material key (Pexels/Coverr).

    Without it, video generation fails at the materials stage
    (`pexels_api_keys is not set`) — verified end-to-end 2026-09-11.
    """
    try:
        import tomllib

        path = _mpt_config_path()
        if path is None:
            return False
        with path.open("rb") as f:
            cfg = tomllib.load(f)
        for key in ("pexels_api_keys", "coverr_api_keys"):
            values = cfg.get(key) or []
            if any(str(v).strip() for v in values):
                return True
        return False
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector mpt_material_key falló: %s", exc)
        return False


def _detect_supplier_outreach(min_contacted: int = 3) -> bool:
    """True cuando ≥3 proveedores fueron contactados por WA (desbloqueo $50k).

    Lee el OutreachStore real (contacted/replied/verified). Sin contactos
    registrados sigue pendiente y visible como advertencia.
    """
    try:
        from cores.ecommerce.outreach import get_outreach_store

        recs = get_outreach_store().list_all() or {}
        n = sum(1 for r in recs.values() if getattr(r, "status", "") in ("contacted", "replied", "verified"))
        return n >= min_contacted
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector supplier_outreach falló: %s", exc)
        return False


def _catalog() -> list[dict[str, Any]]:
    """Checklist curado, ordenado por prioridad dentro de cada fase."""
    return [
        {
            "id": "ai_provider",
            "phase": PHASE_ESSENTIALS,
            "priority": 1,
            "title": "Activar un proveedor de IA",
            "why": (
                "Sin esto, copilot, briefs y chat degradan en silencio. OAR tiene 10 providers "
                "activados; los que no tienen key reportan UNKNOWN (no healthy) y no aportan."
            ),
            "est_minutes": 10,
            "how_to": (
                "Sin key: Ollama local (:11434) y opencode. Con key gratis (tier free, $0): "
                "GROQ_API_KEY, CEREBRAS_API_KEY, TOGETHER_API_KEY, DEEPINFRA_API_KEY, "
                "NVIDIA_API_KEY, OLLAMA_CLOUD_API_KEY. Registrarte en la consola de cada "
                "proveedor y exportar la variable. El failover ante 429 ya está activo: con "
                "2+ keys, un rate limit de uno cae al siguiente en vez de cortar."
            ),
            "url": "/operations/settings",
            "url_label": "Configurar IA",
            "auto": _AUTO,
        },
        {
            "id": "profile_kit",
            "phase": PHASE_ESSENTIALS,
            "priority": 2,
            "title": "Completar tu Profile Kit",
            "why": "Alimenta el autofill de TODAS las postulaciones y propuestas.",
            "est_minutes": 10,
            "how_to": "Panel Profile Kit → guardar nombre, skills, experiencia y links.",
            "url": "/operations/profile-kit",
            "url_label": "Completar perfil",
            "auto": _AUTO,
        },
        {
            "id": "payment_accounts",
            "phase": PHASE_ESSENTIALS,
            "priority": 3,
            "title": "Marcar tus cuentas de cobro (mínimo 3 rails)",
            "why": "El Payment Compatibility Engine verifica cobrabilidad ANTES de invertir tiempo. Con solo 1 rail, P(CASH) queda UNKNOWN y el scorer dice 'sin rail configurado no es cobrable'.",
            "est_minutes": 15,
            "how_to": "POST /api/payment-compat/configured con [grabrfi,wise,airtm,mercadopago] o UI → Payment Network",
            "url": "/operations/payment-compat",
            "url_label": "Configurar rails",
            "auto": _AUTO,
        },
        {
            "id": "bounty_api_key",
            "phase": PHASE_ESSENTIALS,
            "priority": 4,
            "title": "Configurar al menos 1 API key de bug bounty",
            "why": "Habilita envío de reportes y sync de earnings (HackerOne/Bugcrowd/Intigriti/YesWeHack/Immunefi).",
            "est_minutes": 5,
            "how_to": "~/.config/ownex/opportunity.env → HACKERONE_API_KEY=<token> (Settings → API de la plataforma).",
            "url": "/operations/settings",
            "url_label": "Configurar keys",
            "auto": _AUTO,
        },
        {
            "id": "devbounty_api_key",
            "phase": PHASE_ESSENTIALS,
            "priority": 5,
            "title": "Configurar al menos 1 API key de dev bounty",
            "why": "Sin esto no hay submit ni tracking en Opire/IssueHunt/Algora.",
            "est_minutes": 5,
            "how_to": "~/.config/ownex/opportunity.env → OPIRE_API_KEY / ISSUEHUNT_API_KEY / ALGORA_API_KEY.",
            "url": "/operations/settings",
            "url_label": "Configurar keys",
            "auto": _AUTO,
        },
        {
            "id": "github_token",
            "phase": PHASE_ESSENTIALS,
            "priority": 6,
            "title": "Configurar GITHUB_TOKEN (bloqueador #1 de dev bounty)",
            "why": "Sin esto NO hay claim→clone→PR en Algora/Opire/IssueHunt ni CoderAgent con write de PR. Es el token que desbloquea los $2,700 de Algora en el WorkBank ahora mismo.",
            "est_minutes": 3,
            "how_to": "github.com/settings/tokens → Generate new token (classic) con scope `repo` → agregá la línea GITHUB_TOKEN=ghp_XXX en ~/.config/ownex/opportunity.env (o export GITHUB_TOKEN=ghp_XXX en ~/.bashrc). El detector y el executor de Algora lo leen de ahí.",
            "url": "https://github.com/settings/tokens",
            "url_label": "Abrir GitHub Tokens",
            "auto": _AUTO,
        },
        {
            "id": "first_target",
            "phase": PHASE_ESSENTIALS,
            "priority": 7,
            "title": "Agregar tu primer target",
            "why": "Sin target no hay pipeline: recon → hipótesis → finding → reporte.",
            "est_minutes": 3,
            "how_to": "Botón 'Add Target' en /operations/surface o POST /api/targets",
            "url": "/operations/surface",
            "url_label": "Agregar target",
            "auto": _AUTO,
        },
        {
            "id": "outlier_onboarding",
            "phase": PHASE_PLATFORMS,
            "priority": 1,
            "title": "Completar assessment inicial de Outlier",
            "why": "Plataforma AI-training #1 acepta Argentina directo; coding tier paga $8–18/h.",
            "est_minutes": 45,
            "how_to": "outlier.ai → registrarte con email real + completar prueba técnica. Argentina sin VPN.",
            "url": "https://outlier.ai",
            "url_label": "Abrir Outlier",
            "auto": _MANUAL,
        },
        {
            "id": "mercor_onboarding",
            "phase": PHASE_PLATFORMS,
            "priority": 2,
            "title": "Assessment de Mercor (mejor paga: $20–55/h)",
            "why": "Assessment puro, sin entrevista. Coding/reasoning paga $20–55/h (expert hasta $250/h). Es el canal con mejor $/hora humana del sistema.",
            "est_minutes": 120,
            "how_to": "work.mercor.com → registrarte + completar assessment de coding/reasoning (2-3h, es el más largo).",
            "url": "https://work.mercor.com",
            "url_label": "Abrir Mercor",
            "auto": _MANUAL,
        },
        {
            "id": "alignerr_onboarding",
            "phase": PHASE_PLATFORMS,
            "priority": 3,
            "title": "Assessment de Alignerr (especialidad)",
            "why": "Tareas expertas $15–30/h. Sin experiencia profesional previa — solo assessment por especialidad.",
            "est_minutes": 60,
            "how_to": "alignerr.com → registrarte + assessment de tu especialidad (coding/math).",
            "url": "https://alignerr.com",
            "url_label": "Abrir Alignerr",
            "auto": _MANUAL,
        },
        {
            "id": "mindrift_onboarding",
            "phase": PHASE_PLATFORMS,
            "priority": 4,
            "title": "Crear cuenta y onboarding de Mindrift",
            "why": "Tareas de español nativo pagan mejor ($15–40/h); tu inglés técnico es un activo acá.",
            "est_minutes": 30,
            "how_to": "mindrift.ai → registro + perfil de escritura técnica es/en.",
            "url": "https://mindrift.ai",
            "url_label": "Abrir Mindrift",
            "auto": _MANUAL,
        },
        {
            "id": "freelance_profile",
            "phase": PHASE_PLATFORMS,
            "priority": 5,
            "title": "Perfil freelance verificado (Fiverr)",
            "why": "Los textos ya los genera tu Profile Kit — solo pegarlos y verificar método de pago.",
            "est_minutes": 40,
            "how_to": "Copiar textos del Profile Kit → crear perfil → verificar payout (Payoneer/Airtm).",
            "url": "https://www.fiverr.com",
            "url_label": "Abrir Fiverr",
            "auto": _MANUAL,
        },
        {
            "id": "mpt_material_key",
            "phase": PHASE_PLATFORMS,
            "priority": 6,
            "title": "Key gratis de materiales para Shorts (Pexels o Coverr)",
            "why": "Sin esto el pipeline MPT muere en materiales (verificado: guion + voz + subs OK, solo falta la key). Desbloquea el primer Short EN.",
            "est_minutes": 2,
            "how_to": 'pexels.com/api (o coverr.co/developers) → crear key gratis → pegarla en ~/projects/MoneyPrinterTurbo/config.toml → pexels_api_keys = ["tu-key"].',
            "url": "https://www.pexels.com/api/",
            "url_label": "Abrir Pexels API",
            "auto": _AUTO,
        },
        {
            "id": "mercor_marketplace",
            "phase": PHASE_PLATFORMS,
            "priority": 7,
            "title": "Activar Mercor (post-assessment)",
            "why": "Tras el assessment aprobado: entrar al pool y aceptar proyectos $20–55/h recurrentes.",
            "est_minutes": 15,
            "how_to": "work.mercor.com → completar perfil + disponibilidad → aceptar primer proyecto cuando llegue.",
            "url": "https://work.mercor.com",
            "url_label": "Abrir Mercor",
            "auto": _MANUAL,
        },
        {
            "id": "supplier_football",
            "phase": PHASE_PLATFORMS,
            "priority": 8,
            "title": "Conseguir proveedores fútbol (camisetas/indumentaria)",
            "why": "Categoría principal. 3-5 proveedores a comisión/dropshipping con logística propia.",
            "est_minutes": 120,
            "how_to": "Contactar 5+ proveedores (Nebbux, ShopTrend, RM, MK10, Flex Sport) → completar ficha → POST /api/ecommerce/suppliers → sync-catalog.",
            "url": "/operations/ecommerce",
            "url_label": "Cargar proveedor",
            "auto": _MANUAL,
        },
        {
            "id": "supplier_streetwear",
            "phase": PHASE_PLATFORMS,
            "priority": 9,
            "title": "Conseguir proveedores streetwear/urbana",
            "why": "Complemento natural a fútbol. 3-5 proveedores comisión/dropshipping.",
            "est_minutes": 120,
            "how_to": "Contactar mayoristas (SAMPLES, CMMNTY) → ficha completa → POST /api/ecommerce/suppliers → sync-catalog.",
            "url": "/operations/ecommerce",
            "url_label": "Cargar proveedor",
            "auto": _MANUAL,
        },
        {
            "id": "supplier_perfumes",
            "phase": PHASE_PLATFORMS,
            "priority": 10,
            "title": "Conseguir proveedores perfumes/decants",
            "why": "Alto margen (100-200%), sin talles, recompra. 2-3 proveedores decants nicho.",
            "est_minutes": 90,
            "how_to": "Contactar Fábrica de Aromas, Aromas de Lujo, Once Mayorista → POST /api/ecommerce/suppliers → validar dropshipping.",
            "url": "/operations/ecommerce",
            "url_label": "Cargar proveedor",
            "auto": _MANUAL,
        },
        {
            "id": "supplier_accessories",
            "phase": PHASE_PLATFORMS,
            "priority": 11,
            "title": "Conseguir proveedores accesorios/relojes",
            "why": "Ticket bajo, sin talles, complemento ideal. Gorras, relojes, accesorios.",
            "est_minutes": 60,
            "how_to": "Contactar mayoristas accesorios/relojes → POST /api/ecommerce/suppliers → sync-catalog.",
            "url": "/operations/ecommerce",
            "url_label": "Cargar proveedor",
            "auto": _MANUAL,
        },
        {
            "id": "exchange_binance",
            "phase": PHASE_PLATFORMS,
            "priority": 12,
            "title": "Conectar exchange crypto (Binance vía CCXT)",
            "why": "Balances reales, escaneo de arbitraje y paper con tus fondos. Sin esto, inversión trabaja ciega o solo-paper.",
            "est_minutes": 10,
            "how_to": "Binance → API Management → crear key (solo lectura + spot, sin retiros) → POST /api/investment/ccxt/connect {exchange,api_key,api_secret}. Las keys son por-request y NUNCA se guardan.",
            "url": "/trading",
            "url_label": "Ver Trading",
            "auto": _MANUAL,
        },
        {
            "id": "exchange_alpaca",
            "phase": PHASE_PLATFORMS,
            "priority": 13,
            "title": "Conectar broker de acciones (Alpaca paper)",
            "why": "Paper trading de acciones con datos reales y $0. Puerta a stocks sin capital.",
            "est_minutes": 10,
            "how_to": "alpaca.markets → paper keys gratis → POST /api/investment/stocks/algopaca/connect {api_key,secret_key}. Por-request, no se guardan.",
            "url": "/trading",
            "url_label": "Ver Trading",
            "auto": _MANUAL,
        },
        {
            "id": "whop_account",
            "phase": PHASE_PLATFORMS,
            "priority": 14,
            "title": "Cuenta Whop + 1 campaña de clipping",
            "why": "Clipping paga por 1K views (típico $0.50-1.50, fee 10%, cobro ~10 días). Sin cuenta no hay submissions ni PAID.",
            "est_minutes": 30,
            "how_to": "whop.com → cuenta → Content Rewards → reclamar 1 campaña (rate≥$1/1K, cap≥$100, gratis). Cuentas TikTok/IG/YT con 7-14d de warm-up antes de enviar.",
            "url": "https://whop.com/",
            "url_label": "Abrir Whop →",
            "auto": _MANUAL,
        },
        {
            "id": "supplier_outreach_3wa",
            "phase": PHASE_PLATFORMS,
            "priority": 15,
            "title": "Contactar 3 proveedores por WA (desbloqueo $50k)",
            "why": "Sin 3 WA no hay verify→ACTIVE→vidriera→venta. Es el desbloqueo humano #1 del plan $50k/mes.",
            "est_minutes": 60,
            "how_to": "GET /suppliers/{id}/outreach (Dropsheable, Canevic, Flex) → mandar WA con las 5 preguntas → se marca solo al contactar.",
            "url": "/operations/ecommerce",
            "url_label": "Ver proveedores",
            "auto": True,
        },
        {
            "id": "obsidian_vault",
            "phase": PHASE_OPTIONAL,
            "priority": 1,
            "title": "Conectar vault de Obsidian",
            "why": "Tu conocimiento personal entra al pipeline: búsqueda híbrida + contexto para OWNEX.",
            "est_minutes": 5,
            "how_to": "POST /api/knowledge/connect con el path absoluto de tu vault.",
            "auto": _AUTO,
        },
        {
            "id": "smtp_mail",
            "phase": PHASE_OPTIONAL,
            "priority": 2,
            "title": "Configurar SMTP (verificación de email opcional)",
            "why": "Solo si querés verificación de email por usuario. Sin esto nada se rompe.",
            "est_minutes": 5,
            "how_to": ".env → OWNNEX_MAIL_SMTP_HOST/USER/PASSWORD (app password de Gmail).",
            "auto": _AUTO,
        },
        {
            "id": "trading_live",
            "phase": PHASE_OPTIONAL,
            "priority": 3,
            "title": "Habilitar trading LIVE (opcional, requiere decisión)",
            "why": "Hoy todo corre en DRY_RUN. Pasar a live mueve plata REAL — solo si lo decidís conscientemente.",
            "est_minutes": 30,
            "how_to": "API key de exchange + modo live explícito en TradingStore. Revisar drawdown settings primero.",
            "auto": _MANUAL,
        },
        {
            "id": "trading_exchange",
            "phase": PHASE_OPTIONAL,
            "priority": 4,
            "title": "Configurar exchange de trading (CEX)",
            "why": "Sin keys de exchange el copy-trading queda en DRY_RUN siempre. Config para LIVE cuando lo decidas.",
            "est_minutes": 10,
            "how_to": "IdentityVault/env → EXCHANGE_API_KEY + EXCHANGE_SECRET (Binance/Kraken).",
            "url": "/operations/settings",
            "url_label": "Configurar exchange",
            "auto": _AUTO,
        },
        {
            "id": "memecoin_wallet",
            "phase": PHASE_OPTIONAL,
            "priority": 5,
            "title": "Configurar wallet Solana para memecoins",
            "why": "El paper loop de memecoins corre solo, pero live requiere wallet + Helius API.",
            "est_minutes": 10,
            "how_to": "env → HELIUS_API_KEY o SOLANA_PRIVATE_KEY (vault). Nunca en logs.",
            "url": "/operations/settings",
            "url_label": "Configurar wallet",
            "auto": _AUTO,
        },
        {
            "id": "betfair",
            "phase": PHASE_OPTIONAL,
            "priority": 6,
            "title": "Configurar apuestas deportivas (Betfair)",
            "why": "Activa el conector de apuestas (apps/odyssey). Sin credenciales queda deshabilitado.",
            "est_minutes": 15,
            "how_to": "IdentityVault/env → BETFAIR_APP_KEY + BETFAIR_USERNAME + BETFAIR_PASSWORD.",
            "url": "https://developer.betfair.com",
            "url_label": "Abrir Betfair Dev",
            "auto": _AUTO,
        },
        {
            "id": "ccxt_exchange",
            "phase": PHASE_OPTIONAL,
            "priority": 7,
            "title": "Configurar exchange para capital/inversión (CCXT)",
            "why": "El motor de capital usa CCXT para ahorro+inversión. Sin keys queda read-only.",
            "est_minutes": 10,
            "how_to": "IdentityVault/env → CCXT_API_KEY + CCXT_SECRET (o BINANCE/KRAKEN).",
            "url": "/operations/capital",
            "url_label": "Configurar capital",
            "auto": _AUTO,
        },
        {
            "id": "outlook",
            "phase": PHASE_OPTIONAL,
            "priority": 8,
            "title": "Conectar Outlook / calendario",
            "why": "Integración agenda: calendario externo + sync. Sin esto la agenda es solo local.",
            "est_minutes": 10,
            "how_to": "IdentityVault/env → OUTLOOK_CLIENT_ID/SECRET (Microsoft app).",
            "url": "/operations/agenda",
            "url_label": "Configurar agenda",
            "auto": _AUTO,
        },
        {
            "id": "aux_bounty_keys",
            "phase": PHASE_OPTIONAL,
            "priority": 9,
            "title": "Keys auxiliares de bug bounty (upside)",
            "why": "Cantina/Sherlock/CodeHawks/Synack son upside extra — sin key quedan en el radar como unknown.",
            "est_minutes": 10,
            "how_to": "opportunity.env → CANTINA_API_KEY / SHERLOCK_API_KEY / CODEHAWKS_API_KEY / SYNACK_API_KEY.",
            "url": "/operations/settings",
            "url_label": "Configurar keys",
            "auto": _AUTO,
        },
        {
            "id": "ai_work_keys",
            "phase": PHASE_OPTIONAL,
            "priority": 10,
            "title": "Plataformas AI-work/data (Outlier/Mindrift/DAN)",
            "why": "Canal $15-40/h. Con los assessments hechos, las keys completan el sync de earnings.",
            "est_minutes": 10,
            "how_to": "opportunity.env → OUTLIER_API_KEY / MINDRIFT_API_KEY / DATAANNOTATION_API_KEY.",
            "url": "/operations/settings",
            "url_label": "Configurar keys",
            "auto": _AUTO,
        },
        {
            "id": "meta_account",
            "phase": PHASE_OPTIONAL,
            "priority": 11,
            "title": "Conectar cuenta Meta (IG/WhatsApp)",
            "why": "El ecommerce social (Droppinglabel) publica a IG/WA vía Graph API. Sin token, prepara pero no publica.",
            "est_minutes": 10,
            "how_to": "IdentityVault → META_ACCESS_TOKEN + IG_USER_ID + WHATSAPP_PHONE_ID.",
            "url": "/operations/ecommerce",
            "url_label": "Configurar Meta",
            "auto": _AUTO,
        },
        {
            "id": "meli_account",
            "phase": PHASE_OPTIONAL,
            "priority": 12,
            "title": "Conectar cuenta MercadoLibre",
            "why": "Marketplace: catálogo, ventas y sync de órdenes. Sin token, publicar queda en preparación.",
            "est_minutes": 15,
            "how_to": "IdentityVault → MELI_ACCESS_TOKEN (+ refresh). developers.mercadolibre.com → OAuth.",
            "url": "/operations/ecommerce",
            "url_label": "Conectar Meli",
            "auto": _AUTO,
        },
        {
            "id": "affiliate_networks",
            "phase": PHASE_OPTIONAL,
            "priority": 13,
            "title": "Redes de afiliación (Amazon/Hotmart/ClickBank)",
            "why": "Monetiza el contenido affiliate. Sin tags/keys, los links quedan sin tracking.",
            "est_minutes": 10,
            "how_to": "IdentityVault/env → AMAZON_ASSOCIATES_TAG / HOTMART_TOKEN / CLICKBANK_DEV_KEY.",
            "url": "/operations/affiliate",
            "url_label": "Configurar affiliate",
            "auto": _AUTO,
        },
    ]


class SetupChecklist:
    """Plan guiado de configuración total, presentado como tarea diaria única."""

    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = Path(store_path) if store_path else _default_store_path()

    # ── Persistencia (solo ítems manuales) ──

    def _load_state(self) -> dict[str, Any]:
        try:
            if self.store_path.exists():
                data = json.loads(self.store_path.read_text(encoding="utf-8"))
                if isinstance(data.get("manual_done"), dict):
                    return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("setup store corrupto, se reinicia: %s", exc)
        return {"manual_done": {}}

    def _save_state(self, state: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Estado ──

    def status(self) -> dict[str, Any]:
        state = self._load_state()
        manual_done: set[str] = set(state["manual_done"].keys())
        done: list[str] = []
        pending: list[dict[str, Any]] = []
        phases: dict[str, dict[str, int]] = {}
        for item in _catalog():
            phase_stats = phases.setdefault(item["phase"], {"total": 0, "done": 0})
            phase_stats["total"] += 1
            is_done = self._is_done(item, manual_done)
            if is_done:
                done.append(item["id"])
                phase_stats["done"] += 1
            else:
                pending.append(item)
        total = len(_catalog())
        pct = round(len(done) / total * 100) if total else 0
        next_task = self.next_daily_task(pending=pending)
        return {
            "generated_at": _now_iso(),
            "complete_pct": pct,
            "total_items": total,
            "done_items": len(done),
            "done": done,
            "pending": pending,
            "phases": {k: {"label": PHASE_LABELS[k], **v} for k, v in phases.items()},
            "next_task": next_task,
            "complete": not pending,
        }

    def _is_done(self, item: dict[str, Any], manual_done: set[str]) -> bool:
        detector: Callable[[], bool] | None = _DETECTORS.get(item["id"]) if item["auto"] else None
        if detector is not None:
            return detector()
        return item["id"] in manual_done

    def next_daily_task(self, pending: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
        """UNA tarea de config por día: fase esencial > plataformas > opcional,
        luego menor número de prioridad y menor esfuerzo. Al 100% guía a First Money."""
        pending = _catalog() if pending is None else pending
        if not pending:
            # Post-setup: never leave the user without a next step
            try:
                from cores.first_money.tracker import get_first_money_tracker

                fm = get_first_money_tracker().get_next_action()
                if fm:
                    return {
                        "id": "first_money_next",
                        "phase": PHASE_ESSENTIALS,
                        "phase_label": "Próximo dinero",
                        "title": fm.get("title", "Siguiente paso de dinero"),
                        "why": fm.get("description", "Seguir el funnel de First Money"),
                        "est_minutes": fm.get("est_minutes", 15),
                        "how_to": f"{fm.get('description', '')} → {fm.get('endpoint', '')} en {fm.get('url', '')}",
                        "url": fm.get("url", "/operations/first-money"),
                        "url_label": "Ir a First Money",
                    }
            except Exception:
                pass
            return {
                "id": "all_done",
                "phase": PHASE_ESSENTIALS,
                "phase_label": "¡Listo!",
                "title": "¡Configuración completa! Pasar a ganar",
                "why": "Sistema al 100% — ahora el foco es ejecutar y cobrar",
                "est_minutes": 10,
                "how_to": "Income Home → ¿Qué hago ahora? → Work Queue (cola) → Deliver pending",
                "url": "/",
                "url_label": "Ir a Income Home",
            }
        phase_rank = {PHASE_ESSENTIALS: 0, PHASE_PLATFORMS: 1, PHASE_OPTIONAL: 2}
        ordered = sorted(pending, key=lambda i: (phase_rank.get(i["phase"], 9), i["priority"], i["est_minutes"]))
        task = ordered[0]
        return {
            "id": task["id"],
            "phase": task["phase"],
            "phase_label": PHASE_LABELS[task["phase"]],
            "title": task["title"],
            "why": task["why"],
            "est_minutes": task["est_minutes"],
            "how_to": task["how_to"],
            "url": task.get("url", ""),
            "url_label": task.get("url_label", ""),
        }

    # ── Mutaciones ──

    def mark_done(self, item_id: str) -> dict[str, Any]:
        item = self._find_item(item_id)
        if item["auto"]:
            raise ValueError(f"'{item_id}' se completa solo por detección automática — no se puede marcar a mano")
        state = self._load_state()
        state["manual_done"].setdefault(item_id, {"done_at": _now_iso()})
        self._save_state(state)
        return {"success": True, "item": item_id}

    def mark_undone(self, item_id: str) -> dict[str, Any]:
        self._find_item(item_id)
        state = self._load_state()
        state["manual_done"].pop(item_id, None)
        self._save_state(state)
        return {"success": True, "item": item_id}

    def _find_item(self, item_id: str) -> dict[str, Any]:
        for item in _catalog():
            if item["id"] == item_id:
                return item
        raise KeyError(f"ítem desconocido: {item_id}")


_DETECTORS: dict[str, Callable[[], bool]] = {
    "ai_provider": _detect_ai_provider,
    "profile_kit": _detect_profile_kit,
    "payment_accounts": _detect_payment_accounts,
    "bounty_api_key": _detect_bounty_api_key,
    "devbounty_api_key": _detect_devbounty_api_key,
    "github_token": _detect_github_token,
    "first_target": _detect_first_target,
    "mpt_material_key": _detect_mpt_material_key,
    "supplier_outreach_3wa": _detect_supplier_outreach,
    "obsidian_vault": _detect_obsidian_vault,
    "smtp_mail": _detect_smtp_mail,
    "trading_exchange": _detect_trading_exchange,
    "memecoin_wallet": _detect_memecoin_wallet,
    "betfair": _detect_betfair,
    "ccxt_exchange": _detect_ccxt_exchange,
    "outlook": _detect_outlook,
    "aux_bounty_keys": _detect_aux_bounty_keys,
    "ai_work_keys": _detect_ai_work_keys,
    "meta_account": _detect_meta_account,
    "meli_account": _detect_meli_account,
    "affiliate_networks": _detect_affiliate_networks,
}

_singleton: SetupChecklist | None = None


def get_setup_checklist() -> SetupChecklist:
    global _singleton
    if _singleton is None:
        _singleton = SetupChecklist()
    return _singleton
