"""Discovery MECÁNICO de trabajo de seguridad y de bounties open source.

Por qué este adapter existe
---------------------------
Había 20 archivos de adapter, casi todos "uno por plataforma"
(HackerOne, Opire, Algora, Cantina…). Ese es el anti-patrón: cada
plataforma nueva cuesta código, tests y mantenimiento, y la mayoría muere
sin avisar (dework quedó en 0 durante días con un `except` silencioso).

Aquí hay DOS mecanismos que escalan solos:

1. **security.txt (RFC 9116)** — estándar público. Cualquier proyecto con
   canal de disclosure lo publica en `/.well-known/security.txt`. Un solo
   adapter que lo consulte descubre **cientos** de programas de seguridad a
   la vez, sin código nuevo por plataforma.

2. **Barrido de issues de GitHub con múltiples marcadores** — las bounties
   open source viven en issues de GitHub conMarkers distintos por plataforma
   (`/bounty`, `/reward`, `PAID BOUNTY - $X`, label `bounty`, `help wanted`,
   …). Un adapter con N patrones cubre todas las plataformas que usan
   GitHub, en vez de una API por plataforma.

Resultado: 1 adapter → cobertura de cientos de fuentes, en vez de 100 APIs.

Contrato: nunca raisea, jamás inventa montos, y separa explícitamente
`vdp` (sin recompensa) de `bounty` (con recompensa). Un programa sin cifra
pública queda en UNKNOWN (0.0), nunca en un número inventado.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource
from cores.direct_work_engine.models import (
    DifficultyLevel,
    EmploymentType,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
)

logger = logging.getLogger("ownex.discovery.multiscale")

# ── 1) security.txt (RFC 9116) ──────────────────────────────────
_SECURITY_TXT_PATHS = (
    "/.well-known/security.txt",
    "/security.txt",
)

# Campos del estándar que nos interesan.
_FIELD_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 _-]*)\s*:\s*(.+?)\s*$")
_REWARD_HINT_RE = re.compile(r"(bounty|reward|payout|hall of fame|paid)", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"(?:\$|usd\b)\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*([kKmM])?\b", re.IGNORECASE)
# Canales conocidos → plataforma de referencia (para access_status real).
_KNOWN_CHANNELS = {
    "hackerone.com": "hackerone",
    "bugcrowd.com": "bugcrowd",
    "intigriti.com": "intigriti",
    "yeswehack.com": "yeswehack",
    "immunefi.com": "imunefi",
    "huntr.com": "huntr",
    "huntr.dev": "huntr",
}

_SUFFIX_MULT = {"k": 1_000.0, "m": 1_000_000.0}


def _first_amount(text: str) -> float:
    """Monto con marcador de moneda. Sin marcador ⇒ 0.0 (UNKNOWN, nunca inventado)."""
    m = _AMOUNT_RE.search(text or "")
    if not m:
        return 0.0
    try:
        amount = float(m.group(1).replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0
    suffix = m.group(2)
    if suffix:
        amount *= _SUFFIX_MULT.get(suffix.lower(), 1.0)
    return amount


def _channel_platform(url: str) -> str:
    """Plataforma detrás del canal de disclosure ('' si es email directo)."""
    if not url:
        return ""
    if url.startswith("mailto:"):
        return ""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    for needle, platform in _KNOWN_CHANNELS.items():
        if needle in host:
            return platform
    return ""


# ── 2) Barrido de bounties en issues de GitHub ───────────────────
# Un solo adapter cubre TODAS las plataformas que师兄 publican en GitHub.
GITHUB_BOUNTY_QUERIES: tuple[str, ...] = (
    "label:bounty state:open",
    "label:reward state:open",
    'label:"paid bounty" state:open',
    "label:paid state:open",
    'label:"help wanted" state:open label:bounty',
    "in:title bounty $ state:open",
    'in:title "paid bounty" state:open',
    "in:title reward $ state:open",
    'in:title "USD" "bounty" state:open',
    'in:title "PR" "bounty" state:open',
)

# Extractores de monto desde el título/labels. Ambos exigen marcador.
_TITLE_AMOUNT_RE = re.compile(
    r"(?:bounty|reward|prize|payout)\s*(?:of|for|is|:|=|-|–|—)?\s*"
    r"(?:\$|usd\b)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*([kKmM])?\b",
    re.IGNORECASE,
)
_LABEL_AMOUNT_RE = re.compile(
    r"(?:\$|usd\b)\s*(\d+(?:,\d{3})*(?:\.\d+)?)"
    r"|\b(?:bounty|reward|prize|payout|price)\s*[:=]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*([kKmM])?\b",
    re.IGNORECASE,
)


def _amount_from(text: str) -> float:
    m = _TITLE_AMOUNT_RE.search(text or "") or _LABEL_AMOUNT_RE.search(text or "")
    if not m:
        return 0.0
    groups = [g for g in m.groups() if g]
    raw = next((g for g in groups if g[0].isdigit()), None)
    if raw is None:
        return 0.0
    try:
        amount = float(raw.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0
    suffix = m.groups()[-1] if m.groups() and m.groups()[-1] and not m.groups()[-1][0].isdigit() else None
    if suffix:
        amount *= _SUFFIX_MULT.get(suffix.lower(), 1.0)
    return amount


class MultiScaleSecurityAdapter(BaseDiscoveryAdapter):
    """Descubre programas de seguridad vía security.txt + bounties vía GitHub.

    Un adapter, dos mecanismos escalables, cientos de fuentes. Cada programa
    se clasifica como:

    - ``security_bounty``: el canal menciona recompensa/pago.
    - ``security_vdp``: sólo *disclosure* (NO hay dinero — y se marca así,
      para que nadie lo lea como ingreso).
    """

    def __init__(
        self,
        source: DiscoverySource,
        *,
        security_txt_targets: list[str] | None = None,
        github_queries: tuple[str, ...] = GITHUB_BOUNTY_QUERIES,
        timeout_s: float = 12.0,
        concurrency: int = 8,
    ) -> None:
        super().__init__(source)
        self._security_txt_targets = security_txt_targets or []
        self._github_queries = github_queries
        self._timeout_s = timeout_s
        self._sem = asyncio.Semaphore(concurrency)
        self._http = httpx.AsyncClient(
            timeout=timeout_s,
            follow_redirects=True,
            headers={"User-Agent": "OWNEX-security-txt/1.0 (+discovery)"},
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def validate_connection(self) -> bool:
        try:
            r = await self._http.get("https://api.github.com/rate_limit")
            return r.status_code == 200
        except Exception as exc:
            logger.debug("multiscale: validate_connection falló: %s", exc)
            return False

    # ── security.txt ────────────────────────────────────────────
    async def _from_security_txt(self, client: httpx.AsyncClient) -> list[Opportunity]:
        out: list[Opportunity] = []
        for target in self._security_txt_targets:
            base = target.rstrip("/")
            if not base.startswith(("http://", "https://")):
                base = f"https://{base}"
            found = False
            for path in _SECURITY_TXT_PATHS:
                url = f"{base}{path}"
                try:
                    async with self._sem:
                        r = await client.get(url)
                    if r.status_code != 200 or not r.text.strip():
                        continue
                    opp = self._parse_security_txt(r.text, base, url)
                    if opp is not None:
                        out.append(opp)
                    found = True
                    break
                except Exception as exc:
                    logger.debug("multiscale: security.txt %s falló: %s", url, exc)
            if not found:
                logger.debug("multiscale: sin security.txt en %s", base)
        return out

    def _parse_security_txt(self, text: str, base: str, txt_url: str) -> Opportunity | None:
        fields: dict[str, str] = {}
        for line in text.splitlines():
            m = _FIELD_RE.match(line)
            if m:
                fields[m.group(1).strip().lower()] = m.group(2).strip()

        contact = fields.get("contact") or fields.get("contacts") or ""
        if not contact:
            return None
        # Puede traer varias líneas separadas por comas.
        first_contact = contact.split(",")[0].strip()
        policy = fields.get("policy") or first_contact
        encrypt = fields.get("encryption") or ""
        expires = fields.get("expires") or ""
        ack = fields.get("acknowledgments") or fields.get("acknowledgement") or ""
        canonical = fields.get("canonical") or ""

        platform = _channel_platform(first_contact)
        has_money = bool(_REWARD_HINT_RE.search(f"{text}"))
        amount = _first_amount(text)

        is_bounty = has_money
        title = f"{urlparse(base).hostname} — {'Bug bounty' if is_bounty else 'VDP (sin recompensa)'}"
        desc_parts = [
            "Programa de seguridad descubierto vía security.txt (RFC 9116).",
            f"Contacto: {first_contact}",
        ]
        if platform:
            desc_parts.append(f"Canal: {platform}")
        if amount:
            desc_parts.append(f"Recompensa declarada: ${amount:,.0f}")
        elif is_bounty:
            desc_parts.append("Recompensa: no publicada (UNKNOWN).")
        else:
            desc_parts.append("Sin recompensa publicada: es un VDP, NO genera ingreso.")
        if policy:
            desc_parts.append(f"Política: {policy[:120]}")
        if ack:
            desc_parts.append(f"Acuses: {ack}")
        if expires:
            desc_parts.append(f"Expira: {expires}")

        external_id = f"sectxt::{base}"
        try:
            return self._create_opportunity(
                external_id=external_id,
                title=title[:100],
                category=OpportunityCategory.SECURITY_RESEARCH if is_bounty else OpportunityCategory.OPEN_SOURCE,
                url=canonical or first_contact or txt_url,
                description=" | ".join(desc_parts),
                company=urlparse(base).hostname or base,
                region="global",
                payment=amount,
                difficulty=DifficultyLevel.INTERMEDIATE,
                experience_required=ExperienceLevel.NONE,
                interview_required=False,
                portfolio_required=False,
                technical_test_required=False,
                registration_required=bool(platform),
                payment_method=PaymentMethod.OTHER,
                employment_type=EmploymentType.BOUNTY if is_bounty else EmploymentType.OPEN_CALL,
                time_to_payout_days=None,
                reputation=0.6 if is_bounty else 0.3,
                risk=0.6,
                # El monto es UNKNOWN salvo que el propio programa lo publique.
                payment_proven=bool(amount),
                stability=0.7,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                metadata={
                    "discovery": "security_txt",
                    "has_paid_bounty": is_bounty,
                    "channel": first_contact,
                    "platform": platform,
                    "payout_known": bool(amount),
                    "payout": amount or None,
                    "encryption": encrypt,
                },
            )
        except Exception as exc:
            logger.debug("multiscale: no se pudo crear oportunidad %s: %s", external_id, exc)
            return None

    # ── GitHub bounty sweep ─────────────────────────────────────
    async def _from_github(self, client: httpx.AsyncClient) -> list[Opportunity]:
        out: list[Opportunity] = []
        seen: set[str] = set()
        for q in self._github_queries:
            try:
                async with self._sem:
                    r = await client.get(
                        "https://api.github.com/search/issues",
                        params={"q": q, "per_page": 30, "sort": "updated"},
                    )
                if r.status_code != 200:
                    continue
                items = (r.json() or {}).get("items") or []
            except Exception as exc:
                logger.debug("multiscale: github q=%s falló: %s", q, exc)
                continue

            for it in items:
                if not it.get("html_url") or it["html_url"] in seen:
                    continue
                seen.add(it["html_url"])
                opp = self._issue_to_opportunity(it)
                if opp is not None:
                    out.append(opp)
        return out

    def _issue_to_opportunity(self, it: dict[str, Any]) -> Opportunity | None:
        labels = [lb.get("name", "") for lb in (it.get("labels") or [])]
        title = str(it.get("title") or "")
        body = str(it.get("body") or "")[:600]
        text = f"{title} {body}"

        amount = _amount_from(text)
        if amount <= 0.0:
            # Sin cifra verificable ⇒ UNKNOWN, no entra al banco de entregables
            # (el filtro programable + el gate de payout lovdashn en su mayoría).
            amount = 0.0

        repo_full = (
            (it.get("repository_url") or "").rstrip("/").split("/")[-1]
            + "/"
            + (
                (it.get("repository_url") or "").rstrip("/").split("/")[-2]
                if "/" in (it.get("repository_url") or "")
                else ""
            )
        )

        try:
            return self._create_opportunity(
                external_id=f"ghbounty::{it['html_url']}",
                title=title[:100],
                category=OpportunityCategory.DEV_BOUNTY,
                url=it["html_url"],
                description=(f"Bounty en issue de GitHub. Labels: {', '.join(labels)}"),
                company=repo_full or "github",
                region="global",
                payment=amount,
                difficulty=DifficultyLevel.INTERMEDIATE,
                experience_required=ExperienceLevel.NONE,
                interview_required=False,
                portfolio_required=False,
                technical_test_required=False,
                registration_required=False,
                payment_method=PaymentMethod.OTHER,
                employment_type=EmploymentType.BOUNTY,
                time_to_payout_days=None,
                reputation=0.55,
                risk=0.5,
                payment_proven=bool(amount),
                stability=0.6,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                metadata={
                    "discovery": "github_bounty_sweep",
                    "payout_known": bool(amount),
                    "payout": amount or None,
                    "labels": labels,
                },
            )
        except Exception as exc:
            logger.debug("multiscale: issue %s no convertido: %s", it.get("html_url"), exc)
            return None

    # ── entry point ─────────────────────────────────────────────
    async def fetch_opportunities(self) -> list[Opportunity]:
        out: list[Opportunity] = []
        try:
            async with self._http as client:
                if self._security_txt_targets:
                    out.extend(await self._from_security_txt(client))
                out.extend(await self._from_github(client))
        except Exception as exc:
            # Nunca romper el ciclo por un adapter.
            logger.warning("multiscale: discovery falló: %s", exc)
        return out


def build_multiscale_adapter(
    security_txt_targets: list[str] | None = None,
) -> MultiScaleSecurityAdapter:
    from cores.direct_work_engine.models import WorkPlatform

    source = DiscoverySource(
        name="multiscale_security",
        platform=WorkPlatform.GITHUB,
        tier=1,  # público + autónomo
        categories=[OpportunityCategory.SECURITY_RESEARCH, OpportunityCategory.DEV_BOUNTY],
        analysis_cadence_hours=12,
        requires_auth=False,
    )
    return MultiScaleSecurityAdapter(source, security_txt_targets=security_txt_targets)
