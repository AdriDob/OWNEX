"""Affiliate Content Engine — reviews con links de afiliado ($0, sin stock).

Une Content Factory (MPT genera el video) con monetización por afiliación
(Amazon Associates, Meli Afiliados, Hotmart, ClickBank). Todo determinista,
sin red: los clicks/conversiones entran por API/webhook y aquí se ordenan.

Modelo honesto: comisión estimada, nunca PAID hasta confirmación de la red.
Publicar contenido = Human Gate (igual que MPT / Meli publish).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger("ownex.affiliate")


class AffiliateNetwork(StrEnum):
    AMAZON = "amazon"
    MERCADOLIBRE = "mercadolibre"
    HOTMART = "hotmart"
    CLICKBANK = "clickbank"
    OTHER = "other"


class AffiliateStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"  # contenido + link listos, esperando Human Gate
    PUBLISHED = "published"
    PAUSED = "paused"


@dataclass(slots=True)
class AffiliateLink:
    id: str
    network: AffiliateNetwork = AffiliateNetwork.OTHER
    url: str = ""
    product_name: str = ""
    commission_pct: float = 0.0  # declarada por la red, 0 = desconocida
    clicks: int = 0
    conversions: int = 0
    earned_usd: float = 0.0  # solo confirmado por la red
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class AffiliateContent:
    id: str
    product_name: str = ""
    angle: str = "review"  # review | comparativa | tutorial | unboxing
    script_md: str = ""
    hashtags: list[str] = field(default_factory=list)
    link_ids: list[str] = field(default_factory=list)
    status: AffiliateStatus = AffiliateStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    published_at: datetime | None = None


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "item"


def _data_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / "affiliate.json"


def _parse_dt(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return datetime.now(UTC)


class AffiliateEngine:
    """Persistente JSON en data-dir (como OutreachStore/AssetFactory). Nunca raisea en load/save."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = Path(path) if path else _data_path()
        self._links: dict[str, AffiliateLink] = {}
        self._contents: dict[str, AffiliateContent] = {}
        self._load()

    # ── Persistencia (JSON data-dir, best-effort, nunca raisea) ──
    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return
            for d in raw.get("links", []):
                try:
                    link = AffiliateLink(
                        id=str(d["id"]),
                        network=AffiliateNetwork(str(d.get("network", "other"))),
                        url=str(d.get("url", "")),
                        product_name=str(d.get("product_name", "")),
                        commission_pct=float(d.get("commission_pct", 0.0) or 0.0),
                        clicks=int(d.get("clicks", 0) or 0),
                        conversions=int(d.get("conversions", 0) or 0),
                        earned_usd=float(d.get("earned_usd", 0.0) or 0.0),
                        created_at=_parse_dt(d.get("created_at")),
                    )
                    self._links[link.id] = link
                except Exception:
                    continue
            for d in raw.get("contents", []):
                try:
                    content = AffiliateContent(
                        id=str(d["id"]),
                        product_name=str(d.get("product_name", "")),
                        angle=str(d.get("angle", "review")),
                        script_md=str(d.get("script_md", "")),
                        hashtags=list(d.get("hashtags", []) or []),
                        link_ids=list(d.get("link_ids", []) or []),
                        status=AffiliateStatus(str(d.get("status", "draft"))),
                        created_at=_parse_dt(d.get("created_at")),
                        published_at=_parse_dt(d["published_at"]) if d.get("published_at") else None,
                    )
                    self._contents[content.id] = content
                except Exception:
                    continue
        except Exception as exc:
            logger.warning("affiliate load failed: %s", exc)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "links": [
                    {
                        "id": link.id,
                        "network": link.network.value,
                        "url": link.url,
                        "product_name": link.product_name,
                        "commission_pct": link.commission_pct,
                        "clicks": link.clicks,
                        "conversions": link.conversions,
                        "earned_usd": link.earned_usd,
                        "created_at": link.created_at.isoformat(),
                    }
                    for link in self._links.values()
                ],
                "contents": [
                    {
                        "id": c.id,
                        "product_name": c.product_name,
                        "angle": c.angle,
                        "script_md": c.script_md,
                        "hashtags": c.hashtags,
                        "link_ids": c.link_ids,
                        "status": c.status.value,
                        "created_at": c.created_at.isoformat(),
                        "published_at": c.published_at.isoformat() if c.published_at else None,
                    }
                    for c in self._contents.values()
                ],
            }
            self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ── Links ──
    def add_link(
        self,
        url: str,
        product_name: str = "",
        network: AffiliateNetwork = AffiliateNetwork.OTHER,
        commission_pct: float = 0.0,
    ) -> AffiliateLink | None:
        clean = (url or "").strip()
        if not clean.startswith(("http://", "https://")):
            return None
        link_id = f"aff_{_slug(product_name or clean)}_{int(datetime.now(UTC).timestamp())}"
        try:
            comm = max(0.0, min(100.0, float(commission_pct or 0.0)))
        except (TypeError, ValueError):
            comm = 0.0
        link = AffiliateLink(
            id=link_id, network=network, url=clean, product_name=product_name.strip(), commission_pct=comm
        )
        self._links[link.id] = link
        logger.info("Affiliate link added: %s (%s)", link.product_name, link.network.value)
        self._save()
        return link

    def get_link(self, link_id: str) -> AffiliateLink | None:
        return self._links.get(link_id)

    def list_links(self, network: AffiliateNetwork | None = None) -> list[AffiliateLink]:
        rows = list(self._links.values())
        if network:
            rows = [link for link in rows if link.network == network]
        return sorted(rows, key=lambda link: link.created_at, reverse=True)

    def record_click(self, link_id: str) -> AffiliateLink | None:
        link = self._links.get(link_id)
        if not link:
            return None
        link.clicks += 1
        self._save()
        return link

    def record_conversion(self, link_id: str, earned_usd: float = 0.0) -> AffiliateLink | None:
        """Solo con monto confirmado por la red. earned=0 = conversión sin monto aún."""
        link = self._links.get(link_id)
        if not link:
            return None
        link.conversions += 1
        with contextlib.suppress(TypeError, ValueError):
            link.earned_usd = round(link.earned_usd + max(0.0, float(earned_usd or 0.0)), 2)
        self._save()
        return link

    # ── Content ──
    def plan_content(
        self,
        product_name: str,
        angle: str = "review",
        link_ids: list[str] | None = None,
        price_txt: str = "",
    ) -> AffiliateContent:
        name = (product_name or "producto").strip()
        valid_angles = ("review", "comparativa", "tutorial", "unboxing")
        use_angle = angle if angle in valid_angles else "review"
        linked = [lid for lid in (link_ids or []) if lid in self._links]
        hooks = {
            "review": f"Probé {name} {price_txt} — ¿vale la pena? 🤔".strip(),
            "comparativa": f"{name} vs alternativas: cuál conviene en 2026 ⚖️",
            "tutorial": f"Cómo sacarle el máximo a {name} en 5 minutos 🚀",
            "unboxing": f"Unboxing honesto: {name} {price_txt} 📦".strip(),
        }
        script = "\n".join(
            [
                f"HOOK (0-3s): {hooks[use_angle]}",
                "CONTENIDO (3-35s): demo real, pros y contras honestos, para quién SÍ y para quién NO.",
                "PRUEBA (35-42s): precio, dónde comprar, garantía/devolución.",
                "CTA (42-45s): link de afiliado en bio/comentario fijo 🔗 (transparencia: es link afiliado).",
            ]
        )
        content = AffiliateContent(
            id=f"affc_{_slug(name)}_{int(datetime.now(UTC).timestamp())}",
            product_name=name,
            angle=use_angle,
            script_md=script,
            hashtags=["#reviewhonesta", "#ofertasargentina", f"#{_slug(name)[:24]}"],
            link_ids=linked,
        )
        self._contents[content.id] = content
        self._save()
        return content

    def mark_ready(self, content_id: str) -> AffiliateContent | None:
        content = self._contents.get(content_id)
        if not content:
            return None
        content.status = AffiliateStatus.READY
        self._save()
        return content

    def mark_published(self, content_id: str) -> AffiliateContent | None:
        content = self._contents.get(content_id)
        if not content:
            return None
        content.status = AffiliateStatus.PUBLISHED
        content.published_at = datetime.now(UTC)
        self._save()
        return content

    # ── Funnel (honesto: clicks ≠ plata) ──
    def funnel(self) -> dict[str, float | int]:
        clicks = sum(link.clicks for link in self._links.values())
        convs = sum(link.conversions for link in self._links.values())
        earned = round(sum(link.earned_usd for link in self._links.values()), 2)
        return {
            "links": len(self._links),
            "contents": len(self._contents),
            "clicks": clicks,
            "conversions": convs,
            "ctr_pct": round(convs / clicks * 100, 2) if clicks else 0.0,
            "earned_confirmed_usd": earned,
        }

    def get_status(self) -> dict[str, object]:
        return {"funnel": self.funnel()}


_engine: AffiliateEngine | None = None


def get_affiliate_engine() -> AffiliateEngine:
    global _engine
    if _engine is None:
        _engine = AffiliateEngine()
    return _engine
