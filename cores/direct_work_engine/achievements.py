"""Achievement System — Daily check, streaks, and verified completions.

Provides a daily check system so the user can see:
- What OWNEX completed automatically
- What requires manual action
- Verified achievements (submissions, payments, PRs merged)
- Streaks and progress tracking
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.direct_work_engine.achievements")


# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_STORE = "achievements.json"
ACHIEVEMENT_TYPES = {
    "bounty_submit": {"icon": "🎯", "label": "Bounty enviado"},
    "dev_bounty_pr": {"icon": "💻", "label": "PR dev bounty creado"},
    "dev_bounty_submit": {"icon": "✅", "label": "Dev bounty enviado"},
    "ai_training_task": {"icon": "🤖", "label": "Task AI training completado"},
    "payment_received": {"icon": "💰", "label": "Pago recibido"},
    "pr_merged": {"icon": "🔀", "label": "PR mergeado"},
    "skill_acquired": {"icon": "📚", "label": "Skill adquirida"},
    "streak_milestone": {"icon": "🔥", "label": "Racha de días"},
    "capital_milestone": {"icon": "📈", "label": "Meta de capital"},
    "config_completed": {"icon": "⚙️", "label": "Config completada"},
}

# ── Models ──────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Achievement:
    """Single achievement entry."""

    id: str
    type: str
    title: str
    detail: str
    reward_usd: float = 0.0
    verified: bool = False
    verified_at: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        type_: str,
        title: str,
        detail: str,
        reward_usd: float = 0.0,
        verified: bool = False,
        metadata: dict | None = None,
    ) -> Achievement:
        now = datetime.now(UTC).isoformat()
        return cls(
            id=f"{type_}_{now}_{hash(title) % 10000}",
            type=type_,
            title=title,
            detail=detail,
            reward_usd=reward_usd,
            verified=verified,
            verified_at=now if verified else None,
            metadata=metadata or {},
        )


@dataclass(slots=True)
class DailyCheck:
    """Daily check result — what happened today."""

    date: str  # ISO date YYYY-MM-DD
    achievements: list[Achievement]
    auto_completed: int
    human_approved: int
    total_reward_usd: float
    streak_days: int
    pending_manual: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "achievements": [a.to_dict() for a in self.achievements],
            "auto_completed": self.auto_completed,
            "human_approved": self.human_approved,
            "total_reward_usd": self.total_reward_usd,
            "streak_days": self.streak_days,
            "pending_manual": self.pending_manual,
        }


# ── Store ───────────────────────────────────────────────────────────────────


def _default_store_path() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[1] / "data"
    return root / DEFAULT_STORE


class AchievementStore:
    """Persistent store for achievements and daily checks."""

    def __init__(self, store_path: str | Path | None = None):
        self._path = Path(store_path or _default_store_path())
        self._achievements: dict[str, Achievement] = {}
        self._daily_checks: dict[str, DailyCheck] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text())
                self._achievements = {k: Achievement(**v) for k, v in data.get("achievements", {}).items()}
                self._daily_checks = {k: DailyCheck(**v) for k, v in data.get("daily_checks", {}).items()}
        except Exception as e:
            logger.warning(f"Failed to load achievements: {e}")
            self._achievements = {}
            self._daily_checks = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                {
                    "achievements": {k: v.to_dict() for k, v in self._achievements.items()},
                    "daily_checks": {k: v.to_dict() for k, v in self._daily_checks.items()},
                },
                indent=2,
            )
        )

    # ── Achievements ──
    def add(self, achievement: Achievement) -> Achievement:
        self._achievements[achievement.id] = achievement
        self._save()
        return achievement

    def get(self, achievement_id: str) -> Achievement | None:
        return self._achievements.get(achievement_id)

    def get_all(self) -> list[Achievement]:
        return list(self._achievements.values())

    def get_by_type(self, type_: str) -> list[Achievement]:
        return [a for a in self._achievements.values() if a.type == type_]

    def get_by_date(self, date_: date) -> list[Achievement]:
        target = date_.isoformat()
        return [a for a in self._achievements.values() if a.verified_at and a.verified_at.startswith(target)]

    def mark_verified(self, achievement_id: str) -> bool:
        ach = self._achievements.get(achievement_id)
        if ach and not ach.verified:
            ach.verified = True
            ach.verified_at = datetime.now(UTC).isoformat()
            self._save()
            return True
        return False

    # ── Daily Checks ──
    def get_daily_check(self, date_: date) -> DailyCheck | None:
        return self._daily_checks.get(date_.isoformat())

    def set_daily_check(self, check: DailyCheck) -> DailyCheck:
        self._daily_checks[check.date] = check
        self._save()
        return check

    def get_streak(self) -> int:
        """Calculate current streak of consecutive days with activity."""
        if not self._daily_checks:
            return 0
        dates = sorted([date.fromisoformat(d) for d in self._daily_checks])
        if not dates:
            return 0
        streak = 1
        today = date.today()
        # Check if yesterday or today has activity
        if dates[-1] != today and dates[-1] != today - timedelta(days=1):
            return 0
        for i in range(len(dates) - 1, 0, -1):
            if (dates[i] - dates[i - 1]).days == 1:
                streak += 1
            else:
                break
        return streak


# ── Engine ──────────────────────────────────────────────────────────────────


class AchievementEngine:
    """Computes daily check from all OWNEX systems."""

    def __init__(self, store: AchievementStore | None = None):
        self.store = store or AchievementStore()

    def compute_daily_check(self, target_date: date | None = None) -> DailyCheck:
        """Compute today's check from all sources."""
        target = target_date or date.today()
        today_iso = target.isoformat()

        # Check if already computed
        existing = self.store.get_daily_check(target)
        if existing:
            return existing

        achievements: list[Achievement] = []
        auto_completed = 0
        human_approved = 0
        total_reward = 0.0
        pending_manual: list[dict] = []

        # 1. WorkBank - delivered today
        auto_completed += self._scan_workbank(achievements, target, auto_completed, human_approved, total_reward)

        # 2. Payment Pipeline - paid today
        self._scan_payments(achievements, target, total_reward)

        # 3. Execution Queue - PRs merged/paid today
        self._scan_execution_queue(achievements, target, total_reward)

        # 4. Pending manual actions (config, approvals)
        pending_manual = self._scan_pending_manual(target)

        # Calculate streak
        streak = self.store.get_streak()
        if streak > 0 and (
            today_iso in self.store._daily_checks
            or (target - timedelta(days=1)).isoformat() in self.store._daily_checks
        ):
            pass  # streak maintained
        elif streak == 0:
            streak = 1

        check = DailyCheck(
            date=today_iso,
            achievements=achievements,
            auto_completed=auto_completed,
            human_approved=human_approved,
            total_reward_usd=total_reward,
            streak_days=streak,
            pending_manual=pending_manual,
        )

        self.store.set_daily_check(check)
        return check

    def _scan_workbank(
        self, achievements: list, target: date, auto_completed: int, human_approved: int, total_reward: float
    ) -> int:
        try:
            from cores.direct_work_engine.workbank import get_workbank

            wb = get_workbank()
            for item in wb._items.values():
                if item.status == "delivered" and item.delivered_at:
                    delivered_date = datetime.fromisoformat(item.delivered_at.replace("Z", "+00:00")).date()
                    if delivered_date == target:
                        ach = Achievement.create(
                            type_="dev_bounty_submit" if item.category == "dev_bounty" else "bounty_submit",
                            title=f"Entregado: {item.title[:50]}",
                            detail=f"Plataforma: {item.platform} · Recompensa: ${item.reward:,.0f}",
                            reward_usd=float(item.reward or 0),
                            verified=True,
                            metadata={"item_id": item.id, "platform": item.platform},
                        )
                        achievements.append(ach)
                        if item.access_status == "public":
                            auto_completed += 1
                        else:
                            human_approved += 1
                        total_reward += float(item.reward or 0)
        except Exception as e:
            logger.debug(f"WorkBank scan failed: {e}")
        return auto_completed

    def _scan_payments(self, achievements: list, target: date, total_reward: float) -> None:
        try:
            from cores.revenue_tracker.revenue_tracker import RevenueTracker

            rt = RevenueTracker()
            for opp in rt.get_all_opportunities():
                if hasattr(opp, "status") and opp.status == "paid" and hasattr(opp, "paid_at"):
                    paid_date = datetime.fromisoformat(opp.paid_at.replace("Z", "+00:00")).date()
                    if paid_date == target:
                        ach = Achievement.create(
                            type_="payment_received",
                            title=f"Pago recibido: {opp.title[:50]}",
                            detail=f"Plataforma: {opp.platform} · ${opp.amount:,.0f}",
                            reward_usd=float(opp.amount or 0),
                            verified=True,
                            metadata={"opportunity_id": getattr(opp, "id", "")},
                        )
                        achievements.append(ach)
                        total_reward += float(opp.amount or 0)
        except Exception as e:
            logger.debug(f"Payment scan failed: {e}")

    def _scan_execution_queue(self, achievements: list, target: date, total_reward: float) -> None:
        try:
            from core.execution_queue.models import ExecutionQueueStore

            eq = ExecutionQueueStore()
            for item in eq.get_all():
                if item.state == "PAID" and item.updated_at:
                    updated = datetime.fromisoformat(item.updated_at.replace("Z", "+00:00")).date()
                    if updated == target:
                        p = item.payload
                        ach = Achievement.create(
                            type_="pr_merged",
                            title=f"PR mergeado: {p.get('title', 'Unknown')[:50]}",
                            detail=f"Repo: {p.get('repo', '?')}",
                            reward_usd=float(p.get("reward", 0)),
                            verified=True,
                            metadata={"item_id": item.item_id},
                        )
                        achievements.append(ach)
                        total_reward += float(p.get("reward", 0))
        except Exception as e:
            logger.debug(f"Execution queue scan failed: {e}")

    def _scan_pending_manual(self, target: date) -> list[dict]:
        pending = []
        try:
            # Config actions needed
            from cores.direct_work_engine.workbank import get_workbank

            wb = get_workbank()
            for item in wb._items.values():
                if item.status == "needs_access" and item.access_requirement:
                    pending.append(
                        {
                            "type": "config",
                            "title": f"Configurar acceso: {item.platform}",
                            "detail": item.access_requirement,
                            "impact": f"Desbloquea ${item.reward:,.0f}",
                            "effort_min": 10,
                        }
                    )
        except Exception:
            pass
        return pending[:5]  # max 5

    def get_achievement_summary(self) -> dict[str, Any]:
        """Get summary for UI display."""
        all_ach = self.store.get_all()
        by_type = {}
        for a in all_ach:
            by_type[a.type] = by_type.get(a.type, 0) + 1
        total_earned = sum(a.reward_usd for a in all_ach if a.verified)
        streak = self.store.get_streak()
        return {
            "total_achievements": len(all_ach),
            "verified_count": sum(1 for a in all_ach if a.verified),
            "by_type": by_type,
            "total_earned_usd": total_earned,
            "streak_days": streak,
        }


# ── Singleton ───────────────────────────────────────────────────────────────

_engine: AchievementEngine | None = None


def get_achievement_engine() -> AchievementEngine:
    global _engine
    if _engine is None:
        _engine = AchievementEngine()
    return _engine


# ── API Helpers ─────────────────────────────────────────────────────────────


def compute_today_check() -> DailyCheck:
    """Entry point for API/scheduler."""
    return get_achievement_engine().compute_daily_check()
