"""Auto-Apply System — Automatic application to zero-barrier opportunities.

This system automatically applies to jobs where API-based application is possible:
- Indeed API (Indeed Easy Apply)
- Upwork API (proposal submission)
- Fiverr API (gig offers)
- LinkedIn API (Easy Apply)
- Rate limiting and anti-detection measures
- Automatic alerts for errors and human intervention
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.financial_intelligence.alert_system import (
    get_alert_system,
)

logger = logging.getLogger("ownex.auto_apply")


class ApplyStatus(StrEnum):
    """Status of auto-application."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"
    # 2026-10-08: el envío a plataformas sin cliente real NO se simula.
    # Antes `_apply_indeed`/`_apply_fiverr` devolvían SUBMITTED sin haber
    # contactado a nadie, y el registro se leía como una postulación real.
    MANUAL_REQUIRED = "manual_required"


@dataclass
class AutoApplyConfig:
    """Configuration for auto-apply system."""

    # Rate limiting
    max_applications_per_hour: int = 10
    min_delay_between_applications: float = 5.0  # seconds
    max_delay_between_applications: float = 30.0  # seconds

    # Anti-detection
    random_user_agents: list[str] = field(default_factory=list)
    rotate_ip_addresses: bool = False

    # Auto-apply enabled platforms.
    #
    # 2026-10-08 (owner): el carril freelance completo quedó vetado —
    # *"no quiero trabajar en fiverr ni en freelance"*. Fiverr seguía en la
    # lista por default (y en la ruta de aplicación), o sea que el veto no
    # estaba aplicado donde importa: donde se postula. Upwork ya se había
    # purgeado el 2026-09-13; faltaba Fiverr.
    enabled_platforms: list[str] = field(
        default_factory=lambda: [
            "indeed",
        ]
    )

    # Profile data (would be loaded from user config)
    profile_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplicationRecord:
    """Record of an auto-application."""

    id: str
    platform: str
    opportunity_id: str
    opportunity_title: str
    status: ApplyStatus
    submitted_at: str
    responded_at: str | None = None
    response_message: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "opportunity_id": self.opportunity_id,
            "opportunity_title": self.opportunity_title,
            "status": self.status.value,
            "submitted_at": self.submitted_at,
            "responded_at": self.responded_at,
            "response_message": self.response_message,
            "error_message": self.error_message,
        }


class AutoApplySystem:
    """System for automatic application to zero-barrier opportunities.

    Supports API-based application where possible.
    Rate limiting and anti-detection measures.
    """

    def __init__(self, config: AutoApplyConfig | None = None, state_file: Path = Path("data/auto_apply_state.json")):
        self.config = config or AutoApplyConfig()
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._applications: list[ApplicationRecord] = []
        self._last_application_time = datetime.now(UTC)
        self._alert_system = get_alert_system()
        self._load_state()

    def _load_state(self) -> None:
        """Load auto-apply state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    apps_data = data.get("applications", [])
                    self._applications = [
                        ApplicationRecord(
                            id=app["id"],
                            platform=app["platform"],
                            opportunity_id=app["opportunity_id"],
                            opportunity_title=app["opportunity_title"],
                            status=ApplyStatus(app["status"]),
                            submitted_at=app["submitted_at"],
                            responded_at=app.get("responded_at"),
                            response_message=app.get("response_message"),
                            error_message=app.get("error_message"),
                        )
                        for app in apps_data
                    ]
                logger.info(f"Loaded auto-apply state: {len(self._applications)} applications")
            except Exception as e:
                logger.warning(f"Failed to load auto-apply state: {e}")

    def _save_state(self) -> None:
        """Save auto-apply state to disk."""
        try:
            data = {
                "applications": [app.to_dict() for app in self._applications],
                "last_application_time": self._last_application_time.isoformat(),
                "last_updated": datetime.now(UTC).isoformat(),
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved auto-apply state")
        except Exception as e:
            logger.error(f"Failed to save auto-apply state: {e}")

    def auto_apply(self, opportunity: dict[str, Any]) -> ApplicationRecord:
        """Automatically apply to an opportunity if API-based application is available.

        Returns the application record.
        """
        platform = opportunity.get("source", "").lower()
        auto_apply_api = opportunity.get("auto_apply_api")

        if not auto_apply_api or platform not in self.config.enabled_platforms:
            logger.warning(f"Auto-apply not available for platform: {platform}")
            return self._create_manual_apply_record(opportunity)

        # Rate limiting check
        time_since_last = (datetime.now(UTC) - self._last_application_time).total_seconds()
        if time_since_last < self.config.min_delay_between_applications:
            delay = self.config.min_delay_between_applications - time_since_last
            logger.info(f"Rate limiting: waiting {delay:.1f}s before next application")
            time.sleep(delay)

        # Platform-specific auto-apply
        if platform == "indeed":
            record = self._apply_indeed(opportunity)
        elif platform == "fiverr":
            record = self._apply_fiverr(opportunity)
        else:
            record = self._create_manual_apply_record(opportunity)

        self._applications.append(record)
        self._last_application_time = datetime.now(UTC)
        self._save_state()

        return record

    def _apply_indeed(self, opportunity: dict[str, Any]) -> ApplicationRecord:
        """NO IMPLEMENTADO — devuelve un registro que dice que NO se envió.

        Antes simulaba la postulación: `time.sleep(...)` y devolvía
        `ApplyStatus.SUBMITTED` sin contactar a ninguna API. Es la misma
        clase de mentira que `infinite-sources` y que el pipeline de
        $5.810: un registro que afirma un envío que no ocurrió.

        Sin cliente real de indeed, el resultado honesto es
        `MANUAL_REQUIRED` con la instrucción de hacerlo a mano.
        """
        app_id = "indeed_manual_" + datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        logger.warning("auto-apply a indeed NO implementado: registro manual, sin enviar nada")
        return ApplicationRecord(
            id=app_id,
            platform="indeed",
            opportunity_id=opportunity.get("id", ""),
            opportunity_title=opportunity["title"],
            status=ApplyStatus.MANUAL_REQUIRED,
            submitted_at=None,
            responded_at=None,
            response_message=None,
            error_message=("Envío no implementado: sin cliente real de indeed. Postular a mano."),
        )

    def _apply_fiverr(self, opportunity: dict[str, Any]) -> ApplicationRecord:
        """NO IMPLEMENTADO — devuelve un registro que dice que NO se envió.

        Antes simulaba la postulación: `time.sleep(...)` y devolvía
        `ApplyStatus.SUBMITTED` sin contactar a ninguna API. Es la misma
        clase de mentira que `infinite-sources` y que el pipeline de
        $5.810: un registro que afirma un envío que no ocurrió.

        Sin cliente real de fiverr, el resultado honesto es
        `MANUAL_REQUIRED` con la instrucción de hacerlo a mano.
        """
        app_id = "fiverr_manual_" + datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        logger.warning("auto-apply a fiverr NO implementado: registro manual, sin enviar nada")
        return ApplicationRecord(
            id=app_id,
            platform="fiverr",
            opportunity_id=opportunity.get("id", ""),
            opportunity_title=opportunity["title"],
            status=ApplyStatus.MANUAL_REQUIRED,
            submitted_at=None,
            responded_at=None,
            response_message=None,
            error_message=("Envío no implementado: sin cliente real de fiverr. Postular a mano."),
        )

    def _create_manual_apply_record(self, opportunity: dict[str, Any]) -> ApplicationRecord:
        """Create a manual apply record for platforms without API."""
        app_id = f"manual_{opportunity.get('source', 'unknown')}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        return ApplicationRecord(
            id=app_id,
            platform=opportunity.get("source", "unknown"),
            opportunity_id=opportunity.get("id", ""),
            opportunity_title=opportunity["title"],
            status=ApplyStatus.PENDING,
            submitted_at=datetime.now(UTC).isoformat(),
            responded_at=None,
            response_message="Manual application required",
            error_message=None,
        )

    def get_status(self) -> dict[str, Any]:
        """Get current status of auto-apply system."""
        status_counts = {}
        for app in self._applications:
            status_counts[app.status.value] = status_counts.get(app.status.value, 0) + 1

        return {
            "total_applications": len(self._applications),
            "status_counts": status_counts,
            "last_application_time": self._last_application_time.isoformat(),
            "enabled_platforms": self.config.enabled_platforms,
            "config": {
                "max_applications_per_hour": self.config.max_applications_per_hour,
                "min_delay_between_applications": self.config.min_delay_between_applications,
            },
        }


# Singleton instance
_global_auto_apply: AutoApplySystem | None = None


def get_auto_apply_system() -> AutoApplySystem:
    """Get or create the global auto-apply system."""
    global _global_auto_apply
    if _global_auto_apply is None:
        _global_auto_apply = AutoApplySystem()
    return _global_auto_apply
