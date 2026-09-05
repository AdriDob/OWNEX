"""Achievement Engine - Gamification, streaks, badges, and milestone tracking."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cores.autopilot.config.autopilot_config import AutopilotConfig

logger = logging.getLogger(__name__)


@dataclass
class Achievement:
    id: str
    name: str
    description: str
    category: str
    trigger: str  # e.g., "first_$100", "weekly_$500", "100_ready"
    unlocked_at: datetime | None = None
    progress: float = 0.0
    target: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Streak:
    name: str
    current: int = 0
    longest: int = 0
    last_increment: datetime | None = None


class AchievementEngine:
    """
    Achievement and milestone tracking system.

    Tracks:
    - One-time achievements (badges)
    - Streaks (daily/weekly consistency)
    - Progress milestones
    - Automatic unlocking based on system metrics
    """

    def __init__(self, config: AutopilotConfig):
        self.config = config
        self._achievements: dict[str, Achievement] = {}
        self._streaks: dict[str, Streak] = {}
        self._unlocked: set[str] = set()
        self._storage_path = Path.home() / ".ownex" / "achievements.json"
        self._callbacks: list[Callable[[str], None]] = []

        # Define all achievements
        self._define_achievements()

    def _define_achievements(self) -> None:
        """Define all system achievements."""
        achievements = [
            # Onboarding
            Achievement(
                "first_platform",
                "🏁 Primera Plataforma",
                "Activaste tu primera plataforma",
                "onboarding",
                "first_platform",
                target=1,
            ),
            Achievement(
                "keys_configured",
                "🔐 Keys Configuradas",
                "4+ API keys configuradas",
                "onboarding",
                "keys_configured",
                target=4,
            ),
            Achievement(
                "profile_complete",
                "👤 Perfil Completo",
                "Profile Kit 100% completado",
                "onboarding",
                "profile_complete",
                target=1,
            ),
            # Cashflow
            Achievement(
                "first_100", "💰 Primeros $100", "Primeros $100 netos cobrados", "cashflow", "first_100", target=100
            ),
            Achievement("first_1k", "💵 Primeros $1,000", "$1k netos acumulados", "cashflow", "first_1k", target=1000),
            Achievement(
                "first_10k", "💸 Primeros $10,000", "$10k netos acumulados", "cashflow", "first_10k", target=10000
            ),
            Achievement(
                "weekly_500", "🏆 Semana de $500+", "Una semana generando $500+", "cashflow", "weekly_500", target=500
            ),
            # WorkBank
            Achievement(
                "hundred_ready",
                "📦 100 Listos",
                "100 items ready_to_deliver en WorkBank",
                "workbank",
                "hundred_ready",
                target=100,
            ),
            Achievement(
                "thousand_ready",
                "📦 1,000 Listos",
                "1,000 items ready_to_deliver",
                "workbank",
                "thousand_ready",
                target=1000,
            ),
            Achievement(
                "fifty_delivered", "🚀 50 Entregas", "50 entregas confirmadas", "workbank", "fifty_delivered", target=50
            ),
            # Security
            Achievement(
                "first_valid",
                "🐛 Primer Finding Válido",
                "Primer finding aceptado por plataforma",
                "security",
                "first_valid",
                target=1,
            ),
            Achievement(
                "private_invite",
                "🔒 Invite Privado",
                "Primer invite a programa privado",
                "security",
                "private_invite",
                target=1,
            ),
            Achievement(
                "critical_bounty",
                "💎 Bounty Crítico",
                "Primer critical bounty ($10k+)",
                "security",
                "critical_bounty",
                target=10000,
            ),
            # Capital
            Achievement(
                "first_10k_saved",
                "🏦 Primeros $10k Ahorrados",
                "$10k en reserva de emergencia",
                "capital",
                "first_10k_saved",
                target=10000,
            ),
            Achievement(
                "hundred_k_capital",
                "📈 $100k Capital",
                "$100k invertidos y creciendo",
                "capital",
                "hundred_k_capital",
                target=100000,
            ),
            Achievement(
                "half_million",
                "💰 Half Million Club",
                "$500k patrimonio neto",
                "capital",
                "half_million",
                target=500000,
            ),
            # Team (for future)
            Achievement("hunter_1", "👥 Hunter 1 Contratado", "Primer hunter onboard", "team", "hunter_1", target=1),
            Achievement(
                "team_10k", "👥 Equipo $10k/mes", "Equipo genera $10k/mes netos", "team", "team_10k", target=10000
            ),
            # Product
            Achievement("saas_pilot", "🚀 SaaS Pilot", "Primer piloto pagando", "product", "saas_pilot", target=1),
            Achievement(
                "saas_10k_mrr", "💸 SaaS $10k MRR", "$10k MRR recurrente", "product", "saas_10k_mrr", target=10000
            ),
        ]

        for ach in achievements:
            self._achievements[ach.id] = ach

    async def initialize(self) -> None:
        """Load persisted achievements and streaks."""
        await self._load()
        # Check streak continuity
        self._check_streak_continuity()
        logger.info(f"AchievementEngine initialized: {len(self._unlocked)} unlocked")

    def register_callback(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    async def check_and_unlock(self) -> list[str]:
        """Check all achievements and unlock newly qualified ones."""
        newly_unlocked = []

        for ach in self._achievements.values():
            if ach.id in self._unlocked:
                continue

            if await self._check_trigger(ach):
                await self._unlock(ach)
                newly_unlocked.append(ach.id)

        if newly_unlocked:
            await self._save()

        return newly_unlocked

    async def check_workbank_milestones(self) -> list[str]:
        """Check WorkBank-specific milestones."""
        # This would be called after WorkBank cycle
        # Metrics would come from WorkBank instance
        return await self.check_and_unlock()

    async def increment_streak(self, name: str) -> int:
        """Increment a streak counter."""
        streak = self._streaks.get(name, Streak(name=name))
        now = datetime.utcnow()

        if streak.last_increment:
            days_diff = (now - streak.last_increment).days
            if days_diff == 1:
                streak.current += 1
            elif days_diff > 1:
                streak.current = 1  # Broken streak
            # Same day = no increment
        else:
            streak.current = 1

        streak.last_increment = now
        streak.longest = max(streak.longest, streak.current)
        self._streaks[name] = streak

        await self._save()
        return streak.current

    def get_streak(self, name: str) -> int:
        return self._streaks.get(name, Streak(name=name)).current

    def get_longest_streak(self, name: str) -> int:
        return self._streaks.get(name, Streak(name=name)).longest

    def get_unlocked(self) -> list[Achievement]:
        return [self._achievements[aid] for aid in self._unlocked if aid in self._achievements]

    def get_locked(self) -> list[Achievement]:
        return [ach for aid, ach in self._achievements.items() if aid not in self._unlocked]

    def get_progress(self, achievement_id: str) -> float:
        ach = self._achievements.get(achievement_id)
        return ach.progress if ach else 0.0

    # --- Internal Methods ---

    async def _check_trigger(self, ach: Achievement) -> bool:
        """Check if an achievement trigger condition is met."""
        # This would integrate with actual system metrics
        # For now, return False - real implementation needs system integration
        return False

    async def _unlock(self, ach: Achievement) -> None:
        ach.unlocked_at = datetime.utcnow()
        ach.progress = ach.target
        self._unlocked.add(ach.id)

        for callback in self._callbacks:
            try:
                callback(ach.id)
            except Exception as e:
                logger.error(f"Achievement callback error: {e}")

        logger.info(f"🏆 Achievement unlocked: {ach.name} ({ach.id})")

    def _check_streak_continuity(self) -> None:
        """Check if daily streaks should be reset."""
        now = datetime.utcnow()
        for streak in self._streaks.values():
            if streak.last_increment:
                days_since = (now - streak.last_increment).days
                if days_since > 1:
                    streak.current = 0

    async def _save(self) -> None:
        """Persist achievements and streaks."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "unlocked": list(self._unlocked),
            "achievements": {
                aid: {
                    "progress": ach.progress,
                    "unlocked_at": ach.unlocked_at.isoformat() if ach.unlocked_at else None,
                }
                for aid, ach in self._achievements.items()
            },
            "streaks": {
                name: {
                    "current": streak.current,
                    "longest": streak.longest,
                    "last_increment": streak.last_increment.isoformat() if streak.last_increment else None,
                }
                for name, streak in self._streaks.items()
            },
        }
        self._storage_path.write_text(json.dumps(data, indent=2))

    async def _load(self) -> None:
        if not self._storage_path.exists():
            return

        try:
            data = json.loads(self._storage_path.read_text())

            self._unlocked = set(data.get("unlocked", []))

            for aid, data_ach in data.get("achievements", {}).items():
                if aid in self._achievements:
                    self._achievements[aid].progress = data_ach.get("progress", 0)
                    if data_ach.get("unlocked_at"):
                        self._achievements[aid].unlocked_at = datetime.fromisoformat(data_ach["unlocked_at"])

            for name, streak_data in data.get("streaks", {}).items():
                streak = Streak(name=name)
                streak.current = streak_data.get("current", 0)
                streak.longest = streak_data.get("longest", 0)
                if streak_data.get("last_increment"):
                    streak.last_increment = datetime.fromisoformat(streak_data["last_increment"])
                self._streaks[name] = streak

            logger.info(f"Loaded {len(self._unlocked)} unlocked achievements")
        except Exception as e:
            logger.error(f"Failed to load achievements: {e}")

    def get_all_achievements(self) -> list[dict[str, Any]]:
        """Get all achievements with status for frontend."""
        result = []
        for ach in self._achievements.values():
            result.append(
                {
                    "id": ach.id,
                    "name": ach.name,
                    "description": ach.description,
                    "category": ach.category,
                    "unlocked": ach.id in self._unlocked,
                    "unlocked_at": ach.unlocked_at.isoformat() if ach.unlocked_at else None,
                    "progress": ach.progress,
                    "target": ach.target,
                    "progress_pct": (ach.progress / ach.target * 100) if ach.target > 0 else 0,
                }
            )
        return result

    def get_streaks_status(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "current": streak.current,
                "longest": streak.longest,
                "last_increment": streak.last_increment.isoformat() if streak.last_increment else None,
            }
            for name, streak in self._streaks.items()
        }
