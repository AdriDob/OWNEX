"""Content Factory Validation — Specialized validation for Content Factory strategies.

Validates content strategies using content-specific metrics:
- RPM (Revenue Per Mille) historical + current
- Retention rate (3s, 10s, 30s, 60s)
- CTR (Click-Through Rate)
- Anti-overfitting for content (algorithm changes, platform shifts)
- Platform-specific validation (YouTube, TikTok, Instagram, etc.)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from core.trading.contracts import (
    ContentPiece,
    Strategy,
    ValidationPhase,
)

logger = logging.getLogger("ownex.content_factory.validation")


@dataclass
class ContentValidationResult:
    """Result of content validation."""

    strategy_id: str
    phase: ValidationPhase
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class ContentMetrics:
    """Content-specific metrics for validation."""

    # RPM (Revenue Per Mille)
    rpm_historical: float = 0.0
    rpm_current: float = 0.0
    rpm_trend: float = 0.0  # percentage change

    # Retention rates
    retention_3s: float = 0.0
    retention_10s: float = 0.0
    retention_30s: float = 0.0
    retention_60s: float = 0.0

    # CTR
    ctr: float = 0.0
    ctr_historical: float = 0.0
    ctr_trend: float = 0.0

    # Views & Engagement
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_avg: float = 0.0  # seconds

    # Platform
    platform: str = "youtube"
    channel_subscribers: int = 0


@dataclass
class CheckResult:
    """Base class for check results."""

    passed: bool = False
    score: float = 0.0
    details: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class RPMCheckResult(CheckResult):
    pass


@dataclass
class RetentionCheckResult(CheckResult):
    checks: dict[str, bool] = field(default_factory=dict)


@dataclass
class CTRCheckResult(CheckResult):
    pass


@dataclass
class ViewsCheckResult(CheckResult):
    pass


@dataclass
class PlatformCheckResult(CheckResult):
    checks: dict[str, bool] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class TrendCheckResult(CheckResult):
    warnings: list[str] = field(default_factory=list)


@dataclass
class OverfitCheckResult(CheckResult):
    warnings: list[str] = field(default_factory=list)


class ContentFactoryValidator:
    """Validates Content Factory strategies using content-specific metrics."""

    # Minimum thresholds for validation
    MIN_RPM = 0.50  # $0.50 RPM minimum
    MIN_RETENTION_3S = 0.70  # 70% retention at 3 seconds
    MIN_RETENTION_30S = 0.40  # 40% retention at 30 seconds
    MIN_CTR = 0.02  # 2% CTR minimum
    MIN_VIEWS = 100  # Minimum views for statistical significance

    def __init__(self):
        self.logger = logging.getLogger("ownex.content_factory.validation")
        self._historical_data: dict[str, list] = {}

    def validate(
        self,
        strategy: Strategy,
        content_piece: ContentPiece,
        metrics: ContentMetrics,
        historical_data: dict | None = None,
    ) -> ContentValidationResult:
        """Run all validation checks for a content piece."""

        checks = {}
        scores = {}
        warnings = []
        errors = []
        details = {}

        # 1. RPM Validation
        rpm_check = self._check_rpm(content_piece, metrics)
        checks["rpm_minimum"] = rpm_check.passed
        scores["rpm_score"] = rpm_check.score
        if not rpm_check.passed:
            errors.append(f"RPM ${metrics.rpm_current:.2f} below minimum ${self.MIN_RPM:.2f}")
        elif rpm_check.score < 0.7:
            warnings.append(f"RPM ${metrics.rpm_current:.2f} is below optimal")

        # 2. Retention Validation
        retention_check = self._check_retention(metrics)
        checks["retention_3s"] = retention_check.checks.get("retention_3s", False)
        checks["retention_30s"] = retention_check.checks.get("retention_30s", False)
        scores["retention_score"] = retention_check.score
        if not retention_check.passed:
            errors.append("Retention below minimum thresholds")
        elif retention_check.score < 0.7:
            warnings.append("Retention below optimal")

        # 3. CTR Validation
        ctr_check = self._check_ctr(metrics)
        checks["ctr_minimum"] = ctr_check.passed
        scores["ctr_score"] = ctr_check.score
        if not ctr_check.passed:
            errors.append(f"CTR {metrics.ctr:.2%} below minimum {self.MIN_CTR:.0%}")
        elif ctr_check.score < 0.7:
            warnings.append(f"CTR {metrics.ctr:.2%} below optimal")

        # 4. Views Validation
        views_check = self._check_views(metrics)
        checks["views_minimum"] = views_check.passed
        scores["views_score"] = views_check.score
        if not views_check.passed:
            errors.append(f"Views {metrics.views} below minimum {self.MIN_VIEWS}")

        # 5. Platform-specific validation
        platform_check = self._check_platform_specific(metrics)
        checks["platform_requirements"] = platform_check.passed
        scores["platform_score"] = platform_check.score
        if not platform_check.passed:
            warnings.append(f"Platform {metrics.platform} requirements not fully met")
            warnings.extend(platform_check.warnings)

        # 6. Historical trend analysis (if historical data available)
        trend_check = self._check_trends(metrics, historical_data)
        scores["trend_score"] = trend_check.score
        if trend_check.warnings:
            warnings.extend(trend_check.warnings)

        # 6. Anti-overfitting checks (content-specific)
        overfit_check = self._check_overfitting(content_piece, metrics, historical_data)
        scores["overfit_score"] = overfit_check.score
        if not overfit_check.passed:
            warnings.extend(overfit_check.warnings)

        # Overall passed
        all_passed = all(checks.values())

        return ContentValidationResult(
            strategy_id=getattr(strategy, "id", "unknown"),
            phase=ValidationPhase.VALIDATION,
            passed=all_passed,
            checks=checks,
            scores=scores,
            warnings=warnings,
            errors=errors,
            details=details,
        )

    def _check_rpm(self, content_piece: ContentPiece, metrics: ContentMetrics) -> RPMCheckResult:
        """Check RPM against minimum threshold."""
        passed = metrics.rpm_current >= self.MIN_RPM
        score = min(1.0, metrics.rpm_current / self.MIN_RPM) if self.MIN_RPM > 0 else 1.0
        return RPMCheckResult(
            passed=passed,
            score=score,
            details={
                "current_rpm": metrics.rpm_current,
                "min_rpm": self.MIN_RPM,
                "trend": metrics.rpm_trend,
            },
        )

    def _check_retention(self, metrics: ContentMetrics) -> RetentionCheckResult:
        """Check retention rates at multiple timepoints."""
        checks = {
            "retention_3s": metrics.retention_3s >= self.MIN_RETENTION_3S,
            "retention_30s": metrics.retention_30s >= self.MIN_RETENTION_30S,
        }
        passed = all(checks.values())
        score = (float(metrics.retention_3s) + float(metrics.retention_30s)) / 2
        return RetentionCheckResult(
            passed=passed,
            score=score,
            checks=checks,
            details={
                "retention_3s": float(metrics.retention_3s),
                "retention_10s": float(metrics.retention_10s),
                "retention_30s": float(metrics.retention_30s),
                "retention_60s": float(metrics.retention_60s),
            },
        )

    def _check_ctr(self, metrics: ContentMetrics) -> CTRCheckResult:
        """Check CTR against minimum threshold."""
        passed = metrics.ctr >= self.MIN_CTR
        score = min(1.0, metrics.ctr / self.MIN_CTR) if self.MIN_CTR > 0 else 1.0
        return CTRCheckResult(
            passed=passed,
            score=score,
            details={
                "ctr": metrics.ctr,
                "min_ctr": self.MIN_CTR,
                "trend": metrics.ctr_trend,
            },
        )

    def _check_views(self, metrics: ContentMetrics) -> ViewsCheckResult:
        """Check minimum views for statistical significance."""
        passed = metrics.views >= self.MIN_VIEWS
        score = min(1.0, metrics.views / self.MIN_VIEWS)
        return ViewsCheckResult(
            passed=passed,
            score=score,
            details={"views": metrics.views, "min_views": self.MIN_VIEWS},
        )

    def _check_platform_specific(self, metrics: ContentMetrics) -> PlatformCheckResult:
        """Platform-specific validation."""
        warnings = []
        checks = {}

        if metrics.platform == "youtube":
            # YouTube specific: need subscribers for monetization
            if metrics.channel_subscribers < 1000:
                checks["youtube_subscribers"] = False
                warnings.append("Channel has < 1000 subscribers (YouTube Partner Program requirement)")
            else:
                checks["youtube_subscribers"] = True

        elif metrics.platform == "tiktok":
            # TikTok specific: need consistent posting
            pass  # Add TikTok specific checks

        elif metrics.platform == "instagram":
            # Instagram specific: Reels vs Posts
            pass

        passed = all(checks.values())
        return PlatformCheckResult(
            passed=passed,
            score=1.0 if passed else 0.7,
            checks=checks,
            warnings=warnings,
        )

    def _check_trends(self, metrics: ContentMetrics, historical_data: dict | None) -> TrendCheckResult:
        """Check performance trends."""
        warnings = []
        score = 1.0

        if historical_data:
            # RPM trend
            if metrics.rpm_trend < -0.20:
                warnings.append(f"RPM declining: {metrics.rpm_trend:.1%}")
                score *= 0.8

            # CTR trend
            if metrics.ctr_trend < -0.15:
                warnings.append(f"CTR declining: {metrics.ctr_trend:.1%}")
                score *= 0.9

        return TrendCheckResult(
            passed=len(warnings) == 0,
            score=score,
            warnings=warnings,
        )

    def _check_overfitting(
        self, content_piece: ContentPiece, metrics: ContentMetrics, historical_data: dict | None
    ) -> OverfitCheckResult:
        """Check for content overfitting (over-optimization for current algorithm)."""
        warnings = []
        score = 1.0

        # Check if metrics are too good to be true (potential overfitting)
        if metrics.retention_3s > 0.95 and metrics.ctr > 0.15:
            warnings.append("Unusually high retention + CTR - possible overfitting to current algorithm")
            score *= 0.7

        if metrics.views > 100000 and metrics.retention_30s < 0.20:
            warnings.append("High views but low retention - possible clickbait")
            score *= 0.6

        # Check for platform policy compliance
        if metrics.platform == "youtube" and metrics.rpm_current > 10:
            warnings.append("Unusually high RPM for YouTube - verify compliance")
            score *= 0.8

        return OverfitCheckResult(
            passed=len([w for w in warnings if "overfitting" in w or "clickbait" in w]) == 0,
            score=score,
            warnings=warnings,
        )


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# FACTORY
# ════════════════════════════════════════════════════════════════════════════════════════════════════════

_content_factory_validator: ContentFactoryValidator | None = None


def get_content_factory_validator() -> ContentFactoryValidator:
    """Get the global Content Factory validator singleton."""
    global _content_factory_validator
    if _content_factory_validator is None:
        _content_factory_validator = ContentFactoryValidator()
    return _content_factory_validator
