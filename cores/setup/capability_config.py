"""Registro de capacidades pendientes de configuración — fuente única de verdad.

Por qué existe (2026-10-05). El pedido del owner:

    "todo lo que quede pendiente de configuración debe aparecer en la
     configuración del sistema (front)"

Antes, la configuración viva estaba dispersa en tres lugares que nadie
podía ver juntos:

1. 145 `os.getenv(...)` repartidos por `cores/` y `api/`.
2. `_AI_API_KEY_ENVS` en `cores/setup/checklist.py` — 16 keys, de las cuales
   sólo 4 de las 10 activadas aparecían en algún lado.
3. Docstrings que prometían capacidades contingent on keys que nadie listaba.

Un capability gateado por una key que no está en ninguna superficie visible
es un capability que no existe, y además **nadie puede activar sin leer
código**. Este módulo es el índice: para cada capacidad, qué key la
habilita, qué pasa si falta, y quéNO depende de configuración.

Reglas de este módulo:

- **Una entrada por capacidad, no por variable.** Una key que sirve a tres
  capacidades se lista en las tres, no en un fourth sitio.
- **`impact` es honesto.** Si la capacidad funciona igual sin la key
  ( degradada ), el impacto NO es "bloqueada": es "degradada". Decir
  "bloqueada" cuando el sistema funciona es la clase de mentira que este
  proyecto ya pagó.
- **`optional` significa opcional.** Si está en False, la capacidad
  realmente no arranca sin la key.
- **Nada de secretos.** Sólo nombres de variables, nunca valores.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Literal

Impact = Literal["bloqueada", "degradada", "ninguno"]


@dataclass(frozen=True, slots=True)
class ConfigRequirement:
    """Una key y qué pasa sin ella."""

    env: str
    #: Sin esta key, ¿qué se pierde exactamente?
    without: str
    #: True = sin la key la capacidad NO arranca. False = funciona peor.
    optional: bool
    #: Dónde se configura (para el front).
    where: str


@dataclass(frozen=True, slots=True)
class Capability:
    """Una capacidad del sistema y su dependencia de configuración."""

    id: str
    label: str
    category: str
    #: Qué hace, en una línea. Para que el owner sepa si le sirve.
    what: str
    requirements: tuple[ConfigRequirement, ...] = field(default_factory=tuple)

    def impact(self, env: Mapping[str, str] | None = None) -> Impact:
        """Qué pasa con esta capacidad si le falta configuración.

        `bloqueada` = hay una key sin la cual NO arranca.
        `degradada` = arranca pero pierde rendimiento/alcance.
        `ninguno`   = no depende de configuración (las keyless).

        Acepta `env` explícito para poder testear sin mutear el proceso.
        """
        if self.missing_required(env):
            return "bloqueada"
        if self.missing_optional(env):
            return "degradada"
        return "ninguno"

    @property
    def required_envs(self) -> tuple[str, ...]:
        """Keys sin las cuales la capacidad NO arranca."""
        return tuple(r.env for r in self.requirements if not r.optional)

    @property
    def optional_envs(self) -> tuple[str, ...]:
        return tuple(r.env for r in self.requirements if r.optional)

    def missing_required(self, env: Mapping[str, str] | None = None) -> list[str]:
        e = os.environ if env is None else env
        return [r.env for r in self.requirements if not r.optional and not e.get(r.env)]

    def missing_optional(self, env: Mapping[str, str] | None = None) -> list[str]:
        e = os.environ if env is None else env
        return [r.env for r in self.requirements if r.optional and not e.get(r.env)]


def _c(
    env: str,
    without: str,
    *,
    optional: bool = False,
    where: str = "Variables de entorno",
) -> ConfigRequirement:
    return ConfigRequirement(env=env, without=without, optional=optional, where=where)


# ══════════════════════════════════════════════════════════════════
# EL REGISTRO
#
# Ordenado por categoría para que el front pueda agrupar sin adivinar.
# Si agregás una capacidad, agregala acá: no en un router, no en un
# componente. Este módulo es el único lugar donde se declara.
# ══════════════════════════════════════════════════════════════════

CAPABILITIES: tuple[Capability, ...] = (
    # ── Bug bounty: el core del negocio ──────────────────────────
    Capability(
        id="bugbounty_scan",
        label="Escaneo de programas de bounty",
        category="Bug Bounty",
        what=" nuclei + sqlmap + katana + ffuf sobre targets públicos de HackerOne.",
        requirements=(
            _c(
                "HTTP_PROXY",
                "Sin proxy no se escanea (o se escanea desde tu IP real, lo que expone tu IP a los escaneados).",
                optional=True,
            ),
        ),
    ),
    Capability(
        id="bugbounty_submission",
        label="Envío de reportes a plataformas",
        category="Bug Bounty",
        what="Auto-submit con gate humano previo.",
        requirements=(
            _c(
                "HACKERONE_API_KEY",
                "No se puede reportar a HackerOne. Los findings se acumulan para enviar a mano.",
                optional=True,
            ),
            _c("BUGCROWD_API_KEY", "No se puede reportar a Bugcrowd.", optional=True),
        ),
    ),
    Capability(
        id="bounty_target_discovery",
        label="Descubrimiento automático de targets",
        category="Bug Bounty",
        what="Lee el dataset público de bounty-targets (449 programas).",
        requirements=(),
    ),
    # ── IA: capacidad general del sistema ───────────────────────
    Capability(
        id="ai_local",
        label="Inferencia IA local",
        category="Inteligencia",
        what="Ollama en localhost. Funciona sin configurar nada.",
        # Sin requirements: `OLLAMA_HOST` tiene un default funcional
        # (http://localhost:11434). Declararlo como "pendiente" haría que
        # una capacidad 100% operativa aparezca en la lista de faltantes, y
        # el owner tendría que inventar un valor para callar el panel.
        requirements=(),
    ),
    Capability(
        id="ai_free_cloud",
        label="Providers IA gratis (failover)",
        category="Inteligencia",
        what=("Groq, Cerebras, Together, DeepInfra. Con 2+ keys el failover ante 429 salta al siguiente provider."),
        requirements=(
            _c("GROQ_API_KEY", "Sin key Groq no entra al pool.", optional=True),
            _c("CEREBRAS_API_KEY", "Sin key Cerebras no entra al pool.", optional=True),
            _c("TOGETHER_API_KEY", "Sin key Together no entra al pool.", optional=True),
            _c("DEEPINFRA_API_KEY", "Sin key DeepInfra no entra al pool.", optional=True),
            _c("NVIDIA_API_KEY", "Sin key NVIDIA NIM no entra al pool.", optional=True),
            _c("OLLAMA_CLOUD_API_KEY", "Sin key ollama.com no entra al pool.", optional=True),
            _c(
                "ANTHROPIC_API_KEY",
                "Sin key el copilot con persona FCC no responde.",
                optional=True,
            ),
        ),
    ),
    # ── Trading ──────────────────────────────────────────────────
    Capability(
        id="trading_onchain",
        label="Trading en Solana (lectura de mercado)",
        category="Trading",
        what="Quotes de Jupiter, precios y balance. Funciona sin configurar nada.",
        # DECISION DEL OWNER (2026-10-05): nada de pago. NO poner HELIUS_API_KEY.
        # Medido en KNOWN_DEBT #60: el RPC oficial declara x-ratelimit-tier: free
        # y aguanta 30 requests secuenciales sin un solo 429. Un swap son ~3
        # llamadas. El problema real era la concurrencia (10 hilos x 20 -> 160/200
        # con 429), y se resolvio con retry + rotacion entre DOS RPCs gratuitos
        # (api.mainnet-beta.solana.com y solana-rpc.publicnode.com, el segundo
        # 3x mas rapido). Pagar un RPC para evitar un problema que ya no existe
        # seria gastar plata prometiendo un rendimiento que no hace falta.
        requirements=(),
    ),
    Capability(
        id="trading_live",
        label="Trading con fondos reales",
        category="Trading",
        what="Firma y broadcast de transacciones. Requiere Human Gate.",
        requirements=(
            _c(
                "SOLANA_PRIVATE_KEY",
                "Sin key NO se puede firmar nada. El sistema queda en dry_run.",
            ),
            _c(
                "TRADING_MODE",
                "Sin esto el default es dry_run: NUNCA se mueven fondos. Pasarlo a 'real' es una decisión explícita.",
                optional=True,
            ),
            _c(
                "OWNEX_APPROVAL_KEY",
                "Sin key la del Human Gate es efímera por proceso: tras cada "
                "restart los approvals emitidos quedan inválidos.",
                optional=True,
            ),
        ),
    ),
    Capability(
        id="trading_radar",
        label="Radares de mercado (pump/dip/spread)",
        category="Trading",
        what="DexScreener + RugCheck + Binance, todos keyless. Corre solo.",
        requirements=(
            _c(
                "GROQ_API_KEY",
                "Sin key el scoring cualitativo de candidatos no tiene modelo detrás.",
                optional=True,
            ),
        ),
    ),
    # ── OSINT ───────────────────────────────────────────────────
    Capability(
        id="osint_keyless",
        label="OSINT sin key (Shodan, Censys, VirusTotal…)",
        category="OSINT",
        what="16 fuentes. Las keyless funcionan siempre.",
        requirements=(),
    ),
    Capability(
        id="osint_deep",
        label="OSINT con historial y DNS",
        category="OSINT",
        what="SecurityTrails, Hunter.io, BuiltWith, HIBP.",
        requirements=(
            _c("SECURITYTRAILS_API_KEY", "Sin key no hay historial de DNS.", optional=True),
            _c("HUNTER_API_KEY", "Sin key no se buscan emails por dominio.", optional=True),
            _c("BUILTWITH_API_KEY", "Sin key no hay perfil de tecnologías.", optional=True),
            _c("HIBP_API_KEY", "Sin key no hay verificación de breaches.", optional=True),
        ),
    ),
    # ── Copy trading ─────────────────────────────────────────────
    Capability(
        id="copy_trading",
        label="Copy trading (masters de Polymarket)",
        category="Trading",
        what="Descubre y puntúa traders reales del leaderboard público.",
        requirements=(),
    ),
)

BY_ID: dict[str, Capability] = {c.id: c for c in CAPABILITIES}


def all_envs() -> list[str]:
    """Todas las keys que el sistema consulta, deduplicadas y ordenadas."""
    return sorted({r.env for c in CAPABILITIES for r in c.requirements})


def snapshot(env: Mapping[str, str] | None = None) -> dict[str, object]:
    """Estado de configuración para el front.

    Nunca incluye valores de las variables: sólo si están presentes o no.
    """
    e = os.environ if env is None else env
    caps = []
    for c in CAPABILITIES:
        caps.append(
            {
                "id": c.id,
                "label": c.label,
                "category": c.category,
                "what": c.what,
                "impact": c.impact(env),
                "configured": not c.missing_required(e),
                "missing_required": c.missing_required(e),
                "missing_optional": c.missing_optional(e),
                "requirements": [
                    {
                        "env": r.env,
                        "present": bool(e.get(r.env)),
                        "optional": r.optional,
                        "without": r.without,
                        "where": r.where,
                    }
                    for r in c.requirements
                ],
            }
        )
    return {
        "capabilities": caps,
        "totals": {
            "capabilities": len(CAPABILITIES),
            "configured": sum(1 for c in caps if c["configured"]),
            "pending_blocking": len([c for c in caps if not c["configured"]]),
            "envs_referenced": len(all_envs()),
            "envs_set": len([k for k in all_envs() if e.get(k)]),
        },
        "note": "sólo presencia de variables, nunca valores",
    }


# ── Techo de resultados por fuente ─────────────────────────────────────────
#
# Los adapters truncan en duro: `bounties[:20]`, `projects[:30]`,
# `job_cards[:15]`. Eso descarta oportunidades que la API YA devolvió, así que
# el techo —no la red— es lo que limita el sistema. En un sistema pensado para
# correr meses, el límite tiene que ser visible y ajustable, no un literal.
#
# Se lee en cada fetch (no al importar) para que cambiarlo surta efecto sin
# reiniciar el backend.
DEFAULT_MAX_PER_SOURCE = 200
_ENV_MAX = "OWNEX_MAX_PER_SOURCE"


def max_per_source() -> int:
    """Máximo de oportunidades que devuelve un adapter por consulta."""
    raw = os.environ.get(_ENV_MAX, "")
    if raw.strip().isdigit() and int(raw) > 0:
        return int(raw)
    return DEFAULT_MAX_PER_SOURCE


# ── Dónde conseguir cada llave, con el enlace exacto ────────────────────────
#
# La primera versión decía `where="Variables de entorno"` en las 14 entradas: un
# texto que no dice nada accionable. Cada valor es una instrucción ejecutable.
KEY_SOURCES: dict[str, str] = {
    "GITHUB_TOKEN": (
        "https://github.com/settings/tokens/new?scopes=repo&description=OWNEX\n"
        "1. GitHub > Settings (arriba a la derecha) > Developer settings\n"
        "2. Personal access tokens > Fine-grained tokens > Generate new token\n"
        "3. Resource owner: tu cuenta. Repository access: solo los repos que toques.\n"
        "4. Permissions > Repository permissions > Contents: Read and write.\n"
        "5. Generate y copia el token (ghp_...). Solo se muestra una vez."
    ),
    "SOLANA_PRIVATE_KEY": (
        "No se pide en ninguna web: es la clave de tu wallet. RIESGO: una wallet "
        "con fondos reales puede perderlos. Usa una wallet de pruebas con 0 SOL. "
        "Si nunca vas a operar, puede quedar vacio."
    ),
    "HELIUS_API_KEY": (
        "https://www.helius.dev/ > Get Started > genera una API key. El plan "
        "gratuito basta para el RPC publico (OWNEX lo detecta solo)."
    ),
    "ANTHROPIC_API_KEY": (
        "https://console.anthropic.com/settings/keys > Create Key. Requiere "
        "facturacion. Opcional: sin ella el sistema usa la cadena local."
    ),
    "GROQ_API_KEY": "https://console.groq.com/keys > Create API Key. Free tier generoso.",
    "NVIDIA_API_KEY": "https://build.nvidia.com/ > Get API Key.",
    "TOGETHER_API_KEY": "https://api.together.xyz/settings/api-keys > Create API Key.",
    "DEEPINFRA_API_KEY": "https://deepinfra.com/dash/api_keys > crear clave.",
    "OLLAMA_CLOUD_API_KEY": "https://ollama.com/settings/keys > generar clave.",
    "HUNTER_API_KEY": "https://hunter.io/api_keys > crear clave.",
    "SECURITYTRAILS_API_KEY": "https://securitytrails.com/account/api-keys > copiar clave.",
    "HIBP_API_KEY": (
        "https://haveibeenpwned.com/API/Key > requiere suscripcion de pago. "
        "Opcional: sin clave usa el endpoint publico."
    ),
    "BUILDWITH_API_KEY": "https://app.buildwith.com/api > copiar API key.",
    "HTTP_PROXY": (
        "No se compra. Si tu red bloquea escaneos, configura un proxy y expon "
        "HTTP_PROXY (ej. http://127.0.0.1:8080). Sin proxy se escanea desde tu "
        "IP real, que es lo que la plataforma puede ver."
    ),
    "TRADING_MODE": (
        "No es una llave: pon dry_run para operar sin dinero real. Es el valor mas "
        "importante de esta lista: leelo antes de activarlo."
    ),
    "OWNEX_APPROVAL_KEY": (
        "No se pide: lo genera OWNEX la primera vez que apruebes una accion. Solo "
        "rellenalo si ya lo copiaste de ~/.ownex/."
    ),
    "OWNEX_MAX_PER_SOURCE": (
        "No se compra: es un numero. Quantas oportunidades acepta un adapter por "
        f"consulta. Default {DEFAULT_MAX_PER_SOURCE}. Si lo subis, OWNEX "
        "recorre mas trabajo por ciclo y usa mas memoria."
    ),
}


def where_to_get(env: str) -> str:
    """Instruccion accionable para conseguir `env`. Nunca devuelve vacio."""
    return KEY_SOURCES.get(env, f"Busca {env} en la documentacion de la plataforma que integra.")


@dataclass
class CheckResult:
    """`usable` no es `present`: una clave puesta con un valor de ejemplo NO es
    usable, y el panel necesita poder decirlo en vez de pintar un check verde."""

    env: str
    present: bool
    usable: bool
    detail: str
    where: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_PLACEHOLDERS = frozenset({"changeme", "none", "null", "your_key_here", "todo", "xxx", "<key>"})


def check_env(env: str) -> CheckResult:
    """Comprueba si una variable esta puesta y si parece utilizable."""
    where = where_to_get(env)
    raw = os.environ.get(env, "")
    if not raw.strip():
        return CheckResult(env, False, False, "No esta configurada.", where)
    if raw.strip().lower() in _PLACEHOLDERS:
        return CheckResult(env, True, False, "Tiene un valor de ejemplo, no una llave real.", where)
    if env == "GITHUB_TOKEN" and not raw.startswith(("ghp_", "github_pat_")):
        return CheckResult(env, True, False, "No tiene el formato de un token de GitHub.", where)
    if env == "TRADING_MODE" and raw.lower() not in {"dry_run", "paper", "live"}:
        return CheckResult(env, True, False, "Valor no reconocido (usa dry_run, paper o live).", where)
    if env == "SOLANA_PRIVATE_KEY" and len(raw) < 32:
        return CheckResult(env, True, False, "Demasiado corta para ser una clave de wallet.", where)
    if env == _ENV_MAX and not raw.strip().isdigit():
        return CheckResult(env, True, False, "Tiene que ser un numero entero positivo.", where)
    return CheckResult(env, True, True, "Configurada.", where)


def check_all() -> list[CheckResult]:
    """Verifica cada variable de todas las capacidades, sin duplicados."""
    seen: dict[str, CheckResult] = {}
    for cap in CAPABILITIES:
        for req in cap.requirements:
            if req.env not in seen:
                seen[req.env] = check_env(req.env)
    return list(seen.values())
