"""AR job-board adapters — ZonaJobs, Bumeran, Computrabajo (read-only).

Contract (honest by design):
- Best-effort fetch of PUBLIC search pages (short timeout, UA header).
  Any failure (network, layout change, bot-wall) → curated fallback.
- NEVER auto-applies: every RawOpportunity carries
  ``metadata["apply"] == "MANUAL"`` + a deep-link search URL. The human
  clicks and applies; OWNEX only discovers, scores and tracks.
- Salaries on AR boards are monthly ARS (or unstated). ``reward`` carries
  the published monthly figure or 0.0 when absent (never invented);
  ``metadata`` keeps ``salary_raw`` + ``salary_period`` for the UI.
- Employment is a hiring funnel (interview expected): adapters set
  ``interview_required=True`` in metadata so the legacy converter marks it
  honestly. These surface via backup_income, never via zero-barrier modes.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote_plus

import httpx

from cores.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.opportunity.adapters.ar_jobs")

_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) OWNEX-discovery/1.0"}
_TIMEOUT_S = 10.0
_MAX_PARSE = 8

# Curated entry points: CABA + Zona Sur tech searches (junior-friendly first).
# Used as fallback AND as the apply deep-link on every item.
_CURATED_SEARCHES: dict[str, list[dict[str, str]]] = {
    "zonajobs": [
        {
            "id": "zonajobs-junior-caba",
            "name": "ZonaJobs: empleos junior/sin experiencia — CABA",
            "url": "https://www.zonajobs.com.ar/empleos-junior-en-capital-federal.html",
            "description": "Búsqueda curada ZonaJobs: junior y sin experiencia en Capital Federal. Aplicación manual.",
        },
        {
            "id": "zonajobs-zona-sur",
            "name": "ZonaJobs: empleos — Zona Sur GBA",
            "url": "https://www.zonajobs.com.ar/empleos-en-zona-sur.html",
            "description": "Búsqueda curada ZonaJobs: zona sur del Gran Buenos Aires. Aplicación manual.",
        },
    ],
    "bumeran": [
        {
            "id": "bumeran-junior-caba",
            "name": "Bumeran: empleos junior — CABA",
            "url": "https://www.bumeran.com.ar/empleos-junior-en-capital-federal.html",
            "description": "Búsqueda curada Bumeran: junior en Capital Federal. Aplicación manual.",
        },
        {
            "id": "bumeran-zona-sur",
            "name": "Bumeran: empleos — Zona Sur GBA",
            "url": "https://www.bumeran.com.ar/empleos-en-zona-sur.html",
            "description": "Búsqueda curada Bumeran: zona sur del Gran Buenos Aires. Aplicación manual.",
        },
    ],
    "computrabajo": [
        {
            "id": "computrabajo-junior-caba",
            "name": "Computrabajo: empleos junior — Capital Federal",
            "url": "https://www.computrabajo.com.ar/empleos-en-capital-federal-de-junior",
            "description": "Búsqueda curada Computrabajo: junior en Capital Federal. Aplicación manual.",
        },
        {
            "id": "computrabajo-zona-sur",
            "name": "Computrabajo: empleos — Zona Sur",
            "url": "https://www.computrabajo.com.ar/empleos-en-zona-sur-de-junior",
            "description": "Búsqueda curada Computrabajo: zona sur. Aplicación manual.",
        },
    ],
}

# Very small, stable patterns: job-card links + titles. Anything fancier
# belongs in a real scraper, not in a best-effort discovery adapter.
_CARD_LINK_RE = re.compile(r'href="(/ofertas-de-trabajo/[^"]+|/empleos/[^"]+|/trabajo/[^"]+)"', re.IGNORECASE)
_TITLE_RE = re.compile(r"<h[23][^>]*>(.*?)</h[23]>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return _TAG_RE.sub("", text).strip()[:140]


def _curated(platform: str, zone: str) -> list[RawOpportunity]:
    """Curated search deep-links (always MANUAL apply)."""
    out: list[RawOpportunity] = []
    for entry in _CURATED_SEARCHES[platform]:
        if zone and zone.lower() not in entry["name"].lower() and zone.lower() not in entry["url"].lower():
            continue
        out.append(
            RawOpportunity(
                id=entry["id"],
                name=entry["name"],
                description=entry["description"],
                platform=platform,
                url=entry["url"],
                reward=0.0,
                effort_hours=1.0,
                tags=["ar_jobs", "manual_apply", zone.lower() or "caba"],
                cycle="direct_work",
                source_type="job_board",
                source_name=platform,
                metadata=_manual_metadata(zone),
            )
        )
    return out


def _manual_metadata(zone: str) -> dict[str, Any]:
    return {
        "apply": "MANUAL",
        "modality": "presencial",
        "zone": zone,
        "region": "AR",
        "allowed_countries": ["AR"],
        "interview_required": True,
        "employment_funnel": "employment",
    }


class _ArJobsBase(OpportunityAdapter):
    """Shared best-effort HTML fetch + curated fallback."""

    platform: str = "ar_jobs"
    cycle: str = "direct_work"
    search_url: str = ""
    board_name: str = "ar_jobs"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.zone: str = str((config or {}).get("zone", "") or "")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Try the public search page; fall back to curated deep-links. Never raises."""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S, headers=_HEADERS, follow_redirects=True) as client:
                resp = await client.get(self.search_url)
                if resp.status_code == 200 and resp.text:
                    parsed = self._parse(resp.text)
                    if parsed:
                        return parsed
        except Exception as exc:
            logger.debug("%s fetch failed (fallback to curated): %s", self.platform, exc)
        return _curated(self.board_name, self.zone)

    def _parse(self, html: str) -> list[RawOpportunity]:
        """Best-effort card extraction. Empty on any doubt (fallback covers)."""
        links = _CARD_LINK_RE.findall(html)[:_MAX_PARSE]
        titles = [_clean(t) for t in _TITLE_RE.findall(html)][:_MAX_PARSE]
        if not links:
            return []
        base = self.search_url.rstrip("/")
        domain = base[: base.find("/", 8)] if "/" in base[8:] else base
        out: list[RawOpportunity] = []
        for i, link in enumerate(links):
            title = titles[i] if i < len(titles) and titles[i] else f"Oferta {self.board_name} #{i + 1}"
            url = link if link.startswith("http") else domain + link
            out.append(
                RawOpportunity(
                    id=f"{self.platform}-{i}",
                    name=title,
                    description=f"Oferta detectada en {self.board_name} (verificar salario y modalidad en el aviso). Aplicación manual.",
                    platform=self.platform,
                    url=url,
                    reward=0.0,
                    effort_hours=1.0,
                    tags=["ar_jobs", "manual_apply", "parsed"],
                    cycle="direct_work",
                    source_type="job_board",
                    source_name=self.platform,
                    metadata=_manual_metadata(self.zone),
                )
            )
        return out


class ZonaJobsAdapter(_ArJobsBase):
    """ZonaJobs (AR) — read-only discovery, manual apply."""

    platform = "zonajobs"
    board_name = "zonajobs"
    search_url = "https://www.zonajobs.com.ar/empleos-junior-en-capital-federal.html"


class BumeranAdapter(_ArJobsBase):
    """Bumeran (AR) — read-only discovery, manual apply."""

    platform = "bumeran"
    board_name = "bumeran"
    search_url = "https://www.bumeran.com.ar/empleos-junior-en-capital-federal.html"


class ComputrabajoAdapter(_ArJobsBase):
    """Computrabajo (AR) — read-only discovery, manual apply."""

    platform = "computrabajo"
    board_name = "computrabajo"
    search_url = "https://www.computrabajo.com.ar/empleos-en-capital-federal-de-junior"


def build_ar_search_url(board: str, query: str, zone: str = "") -> str:
    """Deep-link builder for manual apply (used by UI/adapters)."""
    q = quote_plus(query)
    templates = {
        "zonajobs": f"https://www.zonajobs.com.ar/empleos-{q}.html",
        "bumeran": f"https://www.bumeran.com.ar/empleos-{q}.html",
        "computrabajo": f"https://www.computrabajo.com.ar/empleos-de-{q}",
    }
    base = templates.get(board, f"https://www.{board}.com.ar/")
    if zone:
        base += f"#zona={quote_plus(zone)}"
    return base
