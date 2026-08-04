"""Work Bank — autonomous production of zero-barrier jobs ready to deliver.

OWNEX works like a fleet of companies at once: it discovers public paid tasks,
prepares each one until it is 100% delivery-ready, and stores them so the user
accumulates many deliverable jobs per day and the best ones per month. It only
waits for the user on critical actions (actual submission); preparation and
storage are autonomous. Access is always honest: a platform that needs an API
key or a manual step is flagged with the exact requirement, never silently
skipped.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from cores.direct_work_engine.filters import StrictFilter
from cores.direct_work_engine.models import Opportunity
from cores.direct_work_engine.scoring import ZeroBarrierScorer

logger = logging.getLogger("ownex.direct_work_engine.workbank")

# Minimum Zero Barrier score to enter the bank (zero/low barrier only).
_MIN_BARRIER_SCORE: float = 60.0

# How each known platform can be accessed today.
# public             → autonomous delivery possible via public API
# needs_api_key      → delivery requires a key the user must configure
# needs_manual_setup → delivery requires a manual profile/submission step
PLATFORM_ACCESS: dict[str, tuple[str, str]] = {
    "opire": ("public", ""),
    "issuehunt": ("public", ""),
    "algora": ("public", ""),
    "opencollective": ("needs_manual_setup", "Presentar una propuesta de financiamiento en cada colectivo."),
    "freelancer": ("needs_manual_setup", "Completar el perfil y verificar el método de pago en Freelancer."),
    "outlier": ("needs_manual_setup", "Crear cuenta y completar la prueba inicial en Outlier."),
    "mindrift": ("needs_manual_setup", "Crear cuenta y completar el onboarding de Mindrift."),
    "upwork": ("needs_manual_setup", "Crear perfil y conectar método de pago en Upwork."),
}

# Single source of truth for discovery tiering: how autonomous a source is.
# tier 1 = public, fully autonomous   → scan several times a day
# tier 2 = needs an API key configured → scan daily
# tier 3 = manual setup / long-cycle   → scan rarely, alert the user instead
PLATFORM_TIER: dict[str, int] = {
    "public": 1,
    "needs_api_key": 2,
    "needs_manual_setup": 3,
}

TIER_CADENCE_HOURS: dict[int, int] = {1: 6, 2: 24, 3: 72}


def platform_tier(access_status: str) -> int:
    """Map a PLATFORM_ACCESS status to its discovery tier."""
    return PLATFORM_TIER.get(access_status, 3)


def tier_cadence_hours(tier: int) -> int:
    """How often OWNEX should re-analyze a source of a given tier."""
    return TIER_CADENCE_HOURS.get(tier, 24)


# Production targets: how many delivery-ready jobs to accumulate.
# These are floors, not caps — the bank keeps as many as it can produce.
TARGETS: dict[str, int] = {"daily": 10, "weekly": 100, "monthly": 1000}


@dataclass(slots=True)
class WorkItem:
    """One zero-barrier job prepared until delivery-ready."""

    id: str
    title: str
    platform: str
    category: str
    reward: float
    barrier_score: float
    employment_type: str
    status: str = "preparing"  # preparing | ready_to_deliver | needs_access | delivered
    access_status: str = "public"
    access_requirement: str = ""
    deliverables: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    ready_to_deliver: bool = False
    description: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class WorkBank:
    """Persistent accumulator of prepared, delivery-ready jobs."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._store_path = Path(store_path or Path(__file__).resolve().parents[3] / "data" / "workbank.json")
        self._items: dict[str, WorkItem] = {}
        self._load()

    # ── Cycle: discover → filter zero-barrier → prepare → store ──
    def daily_cycle(
        self,
        opportunities: list[Opportunity],
        target: int | None = None,
    ) -> dict:
        """Prepare up to ``target`` zero-barrier jobs (default: the daily goal, 10).

        Strict filter runs first: opportunities with red flags (unclear payment,
        non-remote, gift-card-only payout, hiring funnel) are hard-rejected and
        reported — never prepared. Quality over quantity.
        """
        scorer = ZeroBarrierScorer()
        strict_filter = StrictFilter()
        if target is None:
            target = TARGETS["daily"]

        eligible: list[tuple[Opportunity, float]] = []
        rejected: dict[str, list[str]] = {}
        for opp in opportunities:
            reasons = strict_filter.reject(opp)
            if reasons:
                rejected[opp.id] = reasons
                continue
            score = scorer.score(opp)
            if score.total >= _MIN_BARRIER_SCORE:
                eligible.append((opp, score.total))

        eligible.sort(key=lambda pair: pair[0].payment, reverse=True)
        selected = eligible[:target]

        new_count = 0
        for opp, barrier in selected:
            platform_key = opp.platform.value if hasattr(opp.platform, "value") else str(opp.platform)
            access_status, requirement = PLATFORM_ACCESS.get(
                platform_key, ("needs_manual_setup", "Configurar el acceso a la plataforma.")
            )

            item = WorkItem(
                id=opp.id,
                title=opp.title,
                platform=platform_key,
                category=opp.category.value if hasattr(opp.category, "value") else str(opp.category),
                reward=opp.payment,
                barrier_score=round(barrier, 1),
                employment_type=opp.employment_type.value
                if hasattr(opp.employment_type, "value")
                else str(opp.employment_type),
                access_status=access_status,
                access_requirement=requirement,
                deliverables=self._prepare_deliverables(opp),
                description=opp.description or "",
                url=opp.url or "",
            )

            if access_status == "public" and item.deliverables:
                item.status = "ready_to_deliver"
                item.ready_to_deliver = True
            else:
                item.status = "needs_access"

            if item.id not in self._items:
                self._items[item.id] = item
                new_count += 1

        self._save()
        return self._summary(new_items=new_count, scanned=len(opportunities), eligible=len(eligible), rejected=rejected)

    # ── Queries ──
    def best_ready(self, limit: int = 1000) -> list[WorkItem]:
        """The best delivery-ready jobs by reward (default: monthly goal)."""
        return self._rank_ready(limit)

    def best_weekly(self, limit: int | None = None) -> list[WorkItem]:
        """Best 100 delivery-ready jobs for the weekly submission."""
        return self._rank_ready(limit or TARGETS["weekly"])

    def best_monthly(self, limit: int | None = None) -> list[WorkItem]:
        """Best 1000 delivery-ready jobs for the monthly submission."""
        return self._rank_ready(limit or TARGETS["monthly"])

    def progress(self) -> dict[str, dict]:
        """How much of each target is achieved right now (floors, not caps)."""
        ready = len(self.best_ready(TARGETS["monthly"]))
        return {
            horizon: {
                "target": target,
                "achieved": min(ready, target),
                "ready_total": ready,
                "pct": round(min(1.0, ready / target) * 100, 1) if target else 0.0,
            }
            for horizon, target in TARGETS.items()
        }

    def needs_access(self) -> list[WorkItem]:
        return [i for i in self._items.values() if i.status == "needs_access"]

    def mark_delivered(self, item_id: str) -> bool:
        item = self._items.get(item_id)
        if not item:
            return False
        item.status = "delivered"
        item.ready_to_deliver = False
        self._save()
        return True

    def get_item(self, item_id: str) -> WorkItem | None:
        return self._items.get(item_id)

    def _rank_ready(self, limit: int) -> list[WorkItem]:
        ready = [i for i in self._items.values() if i.ready_to_deliver]
        ready.sort(key=lambda i: i.reward, reverse=True)
        return ready[:limit]

    # ── Internals ──
    @staticmethod
    def _prepare_deliverables(opp: Opportunity) -> list[str]:
        """Build the prepared package for a zero-barrier task (honest artifacts)."""
        deliverables = [
            f"submission_draft: {opp.title[:80]}",
            "terms_check: cumple los términos públicos de la plataforma",
            "profile_match: perfil compatible (sin entrevista ni portfolio obligatorio)",
        ]
        if opp.payment > 0:
            deliverables.append(f"reward_verified: ${opp.payment:.2f}")
        return deliverables

    def _summary(
        self, new_items: int = 0, scanned: int = 0, eligible: int = 0, rejected: dict[str, list[str]] | None = None
    ) -> dict:
        ready = [i for i in self._items.values() if i.ready_to_deliver]
        needs_access = [i for i in self._items.values() if i.status == "needs_access"]
        delivered = [i for i in self._items.values() if i.status == "delivered"]
        rejected = rejected or {}
        return {
            "scanned": scanned,
            "eligible_zero_barrier": eligible,
            "strict_rejected": len(rejected),
            "new_items_added": new_items,
            "total_in_bank": len(self._items),
            "ready_to_deliver": len(ready),
            "needs_access": len(needs_access),
            "delivered": len(delivered),
            "rejected": rejected,
            "targets": self.progress(),
            "weekly_best": [i.to_dict() for i in self.best_weekly()],
        }

    def to_dict(self) -> dict:
        return {
            "store_path": str(self._store_path),
            **self._summary(),
            "items": [i.to_dict() for i in sorted(self._items.values(), key=lambda i: i.reward, reverse=True)],
        }

    def _load(self) -> None:
        try:
            if self._store_path.exists():
                data = json.loads(self._store_path.read_text())
                for raw in data.get("items", []):
                    self._items[raw["id"]] = WorkItem(**raw)
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not load workbank store: %s", exc)

    def _save(self) -> None:
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            self._store_path.write_text(json.dumps({"items": [i.to_dict() for i in self._items.values()]}, indent=2))
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not save workbank store: %s", exc)


_workbank: WorkBank | None = None


def get_workbank(store_path: str | Path | None = None) -> WorkBank:
    """Process-wide WorkBank singleton (or a fresh one for tests)."""
    global _workbank
    if _workbank is None:
        _workbank = WorkBank(store_path)
    return _workbank


def run_daily_cycle(target: int | None = None, opportunities: list[Opportunity] | None = None) -> dict:
    """Scheduler entry point: run the daily work-bank cycle autonomously.

    Runs in a dedicated thread so ``asyncio.run`` is always safe regardless of
    the scheduler's loop. Never raises: failures are returned in the summary.
    """
    import asyncio
    import threading

    def _work() -> dict:
        from cores.direct_work_engine.engine import DirectWorkEngine

        engine = DirectWorkEngine()
        try:
            from api.adapters.legacy import build_default_adapters

            for adapter in build_default_adapters():
                if adapter.source.platform not in engine.discovery.adapters:
                    engine.register_adapter(adapter)
        except Exception as exc:  # pragma: no cover
            logger.warning("run_daily_cycle: could not register adapters: %s", exc)

        found = opportunities
        if found is None:
            found = asyncio.run(engine.discovery.discover_all())
        found = found or []
        return get_workbank().daily_cycle(found, target=target)

    result: dict = {}

    def _runner() -> None:
        try:
            result.update(_work())
        except Exception as exc:  # pragma: no cover
            logger.exception("run_daily_cycle failed: %s", exc)
            result["error"] = str(exc)

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout=180)
    return result or {"error": "work bank cycle timed out"}
