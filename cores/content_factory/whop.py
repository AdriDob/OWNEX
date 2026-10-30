"""Whop Content Rewards clipping — campaign evaluator + clip-pack tracker.

Two pieces, both $0-local and fully deterministic:

1. ``evaluate_campaign`` — pure math over a campaign brief (rate per 1K views,
   per-clip cap, minimum threshold, remaining budget, entry fee). No network,
   no guessing: UNKNOWN stays UNKNOWN (``net_hint_usd`` is None without
   ``expected_views``).
2. ``ClipPackStore`` — JSON tracker (data-dir aware, path injectable) for the
   human pipeline building → ready → posted → submitted → paid. Posting and
   submitting are human clicks; this module only tracks evidence. Auto-posting
   and view bots are out of scope by policy (permanent ban on Whop).

Thresholds below come from third-party 2026 trackers (avg ~$1.25/1K, caps
commonly $100-500, 10% CPM fee in Whop terms) — conservative floors, not
promises. A campaign that fails a floor is SKIP, never "maybe".
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.content_factory.whop")

# ── Evaluator floors (conservative; documented 2026 trackers) ──
MIN_RATE_PER_1K_USD: float = 1.0  # below this the math rarely survives review friction
MIN_CAP_USD: float = 100.0  # per-clip ceiling below this bounds even a viral clip
PLATFORM_FEE_PCT: float = 10.0  # Whop terms: flat 10% on every CPM payout
SETTLE_DAYS: int = 10  # ~7d earning window + 3d hold before balance is yours

# Ceiling for the MPT health gate. A blackholed port (firewall DROP) can hold
# a single request up to the client timeout, so the gate has its own bound —
# the job/endpoint never hangs on a dead motor.
HEALTH_GATE_TIMEOUT: float = 25.0

# ── Clip-pack lifecycle ──
STATUS_BUILDING = "building"
STATUS_READY = "ready"
STATUS_POSTED = "posted"
STATUS_SUBMITTED = "submitted"
STATUS_PAID = "paid"
STATUS_REJECTED = "rejected"
TERMINAL_STATUSES = frozenset({STATUS_PAID, STATUS_REJECTED})

CAMPAIGN_TYPES = ("clipping", "ugc")  # clipping = brand assets; ugc = original about the brand
CAMPAIGN_TYPES_LABEL = "clipping|ugc"

# Auto-build policy: only free + verified + ES/EN + VIABLE briefs move alone.
AUTO_LANGUAGES = ("es", "en")
AUTO_MAX_NEW_PER_RUN = 2

# Video subject templates per language (UGC-style, faceless). Voice stays on
# the MPT server default unless the brief pins voice_name (the human reads it
# from their own MPT/Edge setup — never invented here).
SUBJECT_TEMPLATES = {
    "es": "Video promocional estilo UGC sin mostrar cara sobre {name} para TikTok, 60 segundos",
    "en": "Faceless UGC-style promo video about {name} for TikTok, 60 seconds",
}


def evaluate_campaign(
    rate_per_1k_usd: float | None,
    cap_usd: float | None,
    minimum_usd: float | None = None,
    budget_remaining_usd: float | None = None,
    entry_fee_usd: float = 0.0,
    expected_views: float | None = None,
) -> dict[str, Any]:
    """Verdict over a Whop campaign brief. Pure function, never raises."""
    reasons: list[str] = []

    def _num(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None

    rate = _num(rate_per_1k_usd)
    cap = _num(cap_usd)
    minimum = _num(minimum_usd)
    budget = _num(budget_remaining_usd)
    fee = _num(entry_fee_usd) or 0.0

    if rate is None:
        reasons.append("rate desconocido (sin rate no hay matemática)")
    elif rate < MIN_RATE_PER_1K_USD:
        reasons.append(f"rate ${rate:.2f}/1K bajo el piso ${MIN_RATE_PER_1K_USD:.2f}")
    if cap is None:
        reasons.append("cap por clip desconocido (un viral podría pagar $0 extra)")
    elif cap < MIN_CAP_USD:
        reasons.append(f"cap ${cap:.2f} bajo el piso ${MIN_CAP_USD:.2f}")
    if minimum is not None and cap is not None and minimum > cap:
        reasons.append(f"mínimo ${minimum:.2f} > cap ${cap:.2f} (brief incoherente)")
    if fee > 0:
        reasons.append(f"entry fee ${fee:.2f} (señal de walk-away)")
    if budget is not None and budget <= 0:
        reasons.append("budget agotado (0 remanente)")

    verdict = "SKIP" if reasons else "VIABLE"

    net_hint: float | None = None
    views = _num(expected_views)
    if views is not None and rate is not None and verdict == "VIABLE":
        gross = views / 1000.0 * rate
        if cap is not None:
            gross = min(gross, cap)
        net_hint = round(gross * (1.0 - PLATFORM_FEE_PCT / 100.0), 2)

    return {
        "verdict": verdict,
        "reasons": reasons,
        "rate_per_1k_usd": rate,
        "cap_usd": cap,
        "minimum_usd": minimum,
        "budget_remaining_usd": budget,
        "net_hint_usd": net_hint,  # None = UNKNOWN honesto (sin expected_views no se inventa)
        "settle_days": SETTLE_DAYS,
        "fee_pct": PLATFORM_FEE_PCT,
    }


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class CampaignBrief:
    """A Whop campaign brief as pasted by the human from the Whop app.

    Numbers are human-confirmed (``verified``); nothing here is scraped or
    guessed. Unverified briefs are visible but never auto-build.
    """

    id: str
    name: str
    campaign_type: str = "ugc"
    rate_per_1k_usd: float = 0.0
    cap_usd: float = 0.0
    minimum_usd: float | None = None
    budget_remaining_usd: float | None = None
    entry_fee_usd: float = 0.0
    language: str = "en"  # es | en | other
    brief_url: str = ""
    voice_name: str = ""  # pinned by human from their MPT/Edge setup; "" = server default
    verified: bool = False
    created_at: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ClipPack:
    """One clip through the human pipeline. Evidence tracker, not an agent."""

    id: str
    campaign_name: str
    campaign_type: str = "ugc"  # clipping | ugc
    rate_per_1k_usd: float = 0.0
    cap_usd: float = 0.0
    brief_url: str = ""
    status: str = STATUS_BUILDING
    video_path: str = ""
    post_url: str = ""
    submitted_at: str | None = None
    paid_at: str | None = None
    amount_usd: float = 0.0
    reject_reason: str = ""
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _default_store_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / "whop_clips.json"


class ClipPackStore:
    """Persistent clip-pack + campaign-brief tracker. Best-effort I/O, never raises on load/save."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._store_path = Path(store_path) if store_path else _default_store_path()
        self._packs: dict[str, ClipPack] = {}
        self._campaigns: dict[str, CampaignBrief] = {}
        self._load()

    # ── CRUD ──
    def create(
        self,
        campaign_name: str,
        campaign_type: str = "ugc",
        rate_per_1k_usd: float = 0.0,
        cap_usd: float = 0.0,
        brief_url: str = "",
    ) -> ClipPack:
        if campaign_type not in CAMPAIGN_TYPES:
            raise ValueError(f"campaign_type debe ser {CAMPAIGN_TYPES_LABEL}")
        pack_id = f"clip_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
        pack = ClipPack(
            id=pack_id,
            campaign_name=campaign_name.strip(),
            campaign_type=campaign_type,
            rate_per_1k_usd=float(rate_per_1k_usd or 0.0),
            cap_usd=float(cap_usd or 0.0),
            brief_url=brief_url.strip(),
        )
        self._packs[pack.id] = pack
        self._save()
        return pack

    def get(self, pack_id: str) -> ClipPack | None:
        return self._packs.get(pack_id)

    def list(self) -> list[ClipPack]:
        return sorted(self._packs.values(), key=lambda p: p.created_at, reverse=True)

    # ── Lifecycle (guarded; returns ok + reason, never raises) ──
    def attach_video(self, pack_id: str, video_path: str) -> tuple[bool, str]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return False, "pack desconocido"
        if pack.status in TERMINAL_STATUSES:
            return False, f"pack terminal ({pack.status})"
        if not (video_path or "").strip():
            return False, "video_path vacío"
        pack.video_path = video_path.strip()
        if pack.status == STATUS_BUILDING:
            pack.status = STATUS_READY
        pack.updated_at = _utcnow_iso()
        self._save()
        return True, "ok"

    def mark_posted(self, pack_id: str, post_url: str) -> tuple[bool, str]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return False, "pack desconocido"
        if pack.status in TERMINAL_STATUSES:
            return False, f"pack terminal ({pack.status})"
        if pack.status != STATUS_READY or not pack.video_path:
            return False, "requiere video listo (status ready)"
        if not (post_url or "").strip():
            return False, "post_url vacío (el posteo lo hace el humano)"
        pack.post_url = post_url.strip()
        pack.status = STATUS_POSTED
        pack.updated_at = _utcnow_iso()
        self._save()
        return True, "ok"

    def mark_submitted(self, pack_id: str) -> tuple[bool, str]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return False, "pack desconocido"
        if pack.status in TERMINAL_STATUSES:
            return False, f"pack terminal ({pack.status})"
        if pack.status != STATUS_POSTED or not pack.post_url:
            return False, "requiere post publicado con URL"
        pack.status = STATUS_SUBMITTED
        pack.submitted_at = _utcnow_iso()
        pack.updated_at = pack.submitted_at
        self._save()
        return True, "ok"

    def record_paid(self, pack_id: str, amount_usd: float) -> tuple[bool, str]:
        """PAID solo con monto acreditado > 0. La aprobación sola no es cobro."""
        pack = self._packs.get(pack_id)
        if pack is None:
            return False, "pack desconocido"
        if pack.status == STATUS_REJECTED:
            return False, "pack rechazado (terminal)"
        try:
            amount = float(amount_usd)
        except (TypeError, ValueError):
            return False, "monto inválido"
        if amount <= 0:
            return False, "PAID exige monto acreditado > 0"
        pack.amount_usd = round(amount, 2)
        pack.status = STATUS_PAID
        pack.paid_at = _utcnow_iso()
        pack.updated_at = pack.paid_at
        self._save()
        return True, "ok"

    def mark_rejected(self, pack_id: str, reason: str) -> tuple[bool, str]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return False, "pack desconocido"
        if pack.status in TERMINAL_STATUSES:
            return False, f"pack terminal ({pack.status})"
        if not (reason or "").strip():
            return False, "rechazo exige motivo (evidencia para apelar)"
        pack.status = STATUS_REJECTED
        pack.reject_reason = reason.strip()
        pack.updated_at = _utcnow_iso()
        self._save()
        return True, "ok"

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        paid_usd = 0.0
        for pack in self._packs.values():
            by_status[pack.status] = by_status.get(pack.status, 0) + 1
            if pack.status == STATUS_PAID:
                paid_usd += pack.amount_usd
        return {
            "total": len(self._packs),
            "by_status": by_status,
            "paid_usd": round(paid_usd, 2),  # solo PAID acreditado, jamás aprobado-pendiente
            "settle_days": SETTLE_DAYS,
        }

    # ── Campaign briefs (human-pasted, auto-ranked) ──
    def register_campaign(
        self,
        name: str,
        campaign_type: str = "ugc",
        rate_per_1k_usd: float = 0.0,
        cap_usd: float = 0.0,
        minimum_usd: float | None = None,
        budget_remaining_usd: float | None = None,
        entry_fee_usd: float = 0.0,
        language: str = "en",
        brief_url: str = "",
        voice_name: str = "",
        verified: bool = False,
    ) -> tuple[CampaignBrief | None, dict[str, Any]]:
        """Register a brief; returns (brief, verdict). Invalid input → (None, verdict with reasons)."""
        if campaign_type not in CAMPAIGN_TYPES:
            return None, {"verdict": "SKIP", "reasons": [f"campaign_type debe ser {CAMPAIGN_TYPES_LABEL}"]}
        language = (language or "en").strip().lower()
        if language not in ("es", "en", "other"):
            return None, {"verdict": "SKIP", "reasons": ["language debe ser es|en|other"]}
        brief = CampaignBrief(
            id=f"cmp_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            name=name.strip(),
            campaign_type=campaign_type,
            rate_per_1k_usd=float(rate_per_1k_usd or 0.0),
            cap_usd=float(cap_usd or 0.0),
            minimum_usd=minimum_usd,
            budget_remaining_usd=budget_remaining_usd,
            entry_fee_usd=float(entry_fee_usd or 0.0),
            language=language,
            brief_url=(brief_url or "").strip(),
            voice_name=(voice_name or "").strip(),
            verified=bool(verified),
        )
        if not brief.name:
            return None, {"verdict": "SKIP", "reasons": ["campaign_name vacío"]}
        verdict = evaluate_campaign(
            rate_per_1k_usd=brief.rate_per_1k_usd,
            cap_usd=brief.cap_usd,
            minimum_usd=brief.minimum_usd,
            budget_remaining_usd=brief.budget_remaining_usd,
            entry_fee_usd=brief.entry_fee_usd,
        )
        self._campaigns[brief.id] = brief
        self._save()
        return brief, verdict

    def list_campaigns(self) -> list[CampaignBrief]:
        return sorted(self._campaigns.values(), key=lambda c: c.created_at, reverse=True)

    def rank_campaigns(self, languages: tuple[str, ...] = AUTO_LANGUAGES) -> list[dict[str, Any]]:
        """Best free verified ES/EN briefs first. Unverified/paid/non-viable never rank."""
        ranked: list[dict[str, Any]] = []
        for brief in self._campaigns.values():
            if not brief.verified or brief.entry_fee_usd > 0 or brief.language not in languages:
                continue
            verdict = evaluate_campaign(
                rate_per_1k_usd=brief.rate_per_1k_usd,
                cap_usd=brief.cap_usd,
                minimum_usd=brief.minimum_usd,
                budget_remaining_usd=brief.budget_remaining_usd,
                entry_fee_usd=brief.entry_fee_usd,
            )
            if verdict["verdict"] != "VIABLE":
                continue
            ranked.append({"brief": brief.to_dict(), "verdict": verdict})
        ranked.sort(
            key=lambda r: (r["brief"]["rate_per_1k_usd"], r["brief"]["cap_usd"]),
            reverse=True,
        )
        return ranked

    def _has_active_pack(self, campaign_name: str) -> bool:
        return any(p.campaign_name == campaign_name and p.status not in TERMINAL_STATUSES for p in self._packs.values())

    # ── Persistence ──
    def _load(self) -> None:
        try:
            if self._store_path.exists():
                data = json.loads(self._store_path.read_text(encoding="utf-8"))
                for raw in data.get("packs", []):
                    try:
                        self._packs[raw["id"]] = ClipPack(**raw)
                    except TypeError:
                        logger.warning("Clip pack corrupto ignorado: %s", raw.get("id"))
                for raw in data.get("campaigns", []):
                    try:
                        self._campaigns[raw["id"]] = CampaignBrief(**raw)
                    except TypeError:
                        logger.warning("Campaign brief corrupto ignorado: %s", raw.get("id"))
        except Exception as exc:
            logger.warning("Could not load whop clips store: %s", exc)

    def _save(self) -> None:
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            self._store_path.write_text(
                json.dumps(
                    {
                        "packs": [p.to_dict() for p in self._packs.values()],
                        "campaigns": [c.to_dict() for c in self._campaigns.values()],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Could not save whop clips store: %s", exc)


async def auto_build_packs(
    store: ClipPackStore,
    mpt_client: Any = None,
    max_new: int = AUTO_MAX_NEW_PER_RUN,
    languages: tuple[str, ...] = AUTO_LANGUAGES,
    generation_timeout: float = 600.0,
) -> dict[str, Any]:
    """Rank verified free ES/EN briefs → create packs → generate video via MPT → ready.

    Fully local and reversible. Never raises: MPT down/unhealthy, zero viable
    briefs, or generation failures are reported in ``skipped``. Posting and
    submitting stay human (accounts + Human Gate, out of scope here).
    """
    result: dict[str, Any] = {"created": 0, "videos_ready": 0, "skipped": []}
    ranked = store.rank_campaigns(languages=languages)
    if not ranked:
        result["skipped"].append("sin briefs viables verificados (registrar + verificar primero)")
        return result

    if mpt_client is None:
        try:
            from cores.content_factory.mpt_client import create_mpt_client

            # Short per-request timeout + single retry: status polls are quick
            # GETs; a dead motor must fail fast, never hold the job.
            mpt_client = await create_mpt_client(timeout=20.0, max_retries=1)
        except Exception as exc:
            result["skipped"].append(f"mpt_no_disponible: {type(exc).__name__}")
            return result
    try:
        healthy = await asyncio.wait_for(
            mpt_client.wait_for_healthy(timeout=10.0, interval=2.0),
            timeout=HEALTH_GATE_TIMEOUT,
        )
    except Exception as exc:
        result["skipped"].append(f"mpt_unreachable: {type(exc).__name__}")
        return result
    if not healthy:
        result["skipped"].append("mpt_unhealthy (server :8081 caído o sin materiales)")
        return result

    from cores.content_factory.mpt_client import VideoGenerationRequest

    built = 0
    for entry in ranked:
        if built >= max_new:
            break
        brief = entry["brief"]
        if store._has_active_pack(brief["name"]):
            result["skipped"].append(f"pack activo ya existe: {brief['name']}")
            continue
        pack = store.create(
            campaign_name=brief["name"],
            campaign_type=brief["campaign_type"],
            rate_per_1k_usd=brief["rate_per_1k_usd"],
            cap_usd=brief["cap_usd"],
            brief_url=brief["brief_url"],
        )
        result["created"] += 1
        built += 1
        try:
            template = SUBJECT_TEMPLATES.get(brief["language"], SUBJECT_TEMPLATES["en"])
            request = VideoGenerationRequest(
                video_subject=template.format(name=brief["name"]),
                video_count=1,
            )
            if brief.get("voice_name"):
                request.voice_name = brief["voice_name"]
            response = await mpt_client.generate_video(request)
            if not response.task_id:
                raise RuntimeError("MPT sin task_id")
            status = await mpt_client.wait_for_completion(response.task_id, timeout=generation_timeout)
            videos = getattr(status, "videos", None) or []
            first = videos[0] if videos else None
            video_path = (
                first
                if isinstance(first, str)
                else (first.get("path") or first.get("url") if isinstance(first, dict) else None)
            )
            if not video_path:
                raise RuntimeError("MPT completó sin video")
            ok, reason = store.attach_video(pack.id, str(video_path))
            if ok:
                result["videos_ready"] += 1
            else:
                result["skipped"].append(f"attach falló {pack.id}: {reason}")
        except Exception as exc:
            result["skipped"].append(f"generación falló {pack.id}: {type(exc).__name__}")
    return result
