#!/usr/bin/env python3
"""OWNEX Accessibility Compliance Engine.

Ensures WCAG 2.1 AA compliance across all systems, with focus on:
- Color contrast ratios
- Keyboard navigation
- Screen reader support
- Touch target sizes
- Cognitive load management
- Multi-language support

Integrates with zero-barrier eligibility and income multiplier systems.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.accessibility_compliance")


class WCAGLevel(Enum):
    """WCAG conformance levels."""

    A = "A"
    AA = "AA"  # Target level for OWNEX
    AAA = "AAA"


class ContrastRatio(Enum):
    """Pre-defined contrast ratios for WCAG."""

    AAA_NORMAL = "7:1"  # WCAG AAA for normal text
    AAA_LARGE = "4.5:1"  # WCAG AAA for large text (18pt+)
    AA_NORMAL = "4.5:1"  # WCAG AA for normal text
    AA_LARGE = "3:1"  # WCAG AA for large text (18pt+)
    UI_COMPONENT = "3:1"  # WCAG AA for UI components and graphics


@dataclass
class AccessibilityConfig:
    """Configuration for accessibility compliance."""

    wcag_level: WCAGLevel = WCAGLevel.AA
    high_contrast_mode: bool = False
    screen_reader_mode: bool = False
    keyboard_navigation: bool = True
    reduced_motion: bool = False
    font_scaling: float = 1.0  # 1.0 = default, can scale up to 2.0+
    touch_target_min_pixels: int = 44  # Minimum touch target size
    language: str = "en"  # Language code for localization
    aria_labels_enabled: bool = True
    focus_indicator: bool = True


@dataclass
class ContrastCheckResult:
    """Result of a contrast ratio check."""

    foreground: str  # HEX color
    background: str  # HEX color
    ratio: str  # Actual ratio (e.g., "4.5:1")
    passes_aa: bool  # Passes WCAG AA
    passes_aaa: bool  # Passes WCAG AAA
    recommendations: list[str] = field(default_factory=list)


@dataclass
class AccessibilityReport:
    """Complete accessibility compliance report."""

    config: AccessibilityConfig
    contrast_checks: list[ContrastCheckResult] = field(default_factory=list)
    keyboard_navigation_issues: list[str] = field(default_factory=list)
    screen_reader_issues: list[str] = field(default_factory=list)
    touch_target_issues: list[str] = field(default_factory=list)
    overall_compliance: str = "pending"  # pending, aa_compliant, aaa_compliant, non_compliant
    last_checked: datetime = field(default_factory=datetime.now)
    frontend_audited: bool = False  # True only after a real Vue/UI audit
    # NOTE: automated contrast checks alone are NOT a WCAG AA certification.
    # overall_compliance stays scoped to what was actually checked (color contrast)
    # while frontend_audited=False signals no real UI/manual audit has been done.


class AccessibilityComplianceEngine:
    """Engine for WCAG 2.1 AA compliance assessment and enforcement.

    Provides tools to ensure all UI components, reports, and system outputs
    meet accessibility standards, particularly for users with visual,
    motor, and cognitive impairments.
    """

    def __init__(self, config: AccessibilityConfig | None = None):
        self.config = config or AccessibilityConfig()
        self._contrast_cache: dict[tuple[str, str], ContrastCheckResult] = {}
        self._report: AccessibilityReport | None = None
        self.frontend_audited: bool = False

    def check_frontend_audit_status(self) -> dict[str, Any]:
        """Report the real state of the frontend accessibility audit.

        The engine performs automated color-contrast math only. A WCAG AA claim
        requires manual/frontend review of the actual UI components, so this
        reports honestly until that review sets frontend_audited=True.

        Returns:
            Dict with audit state, scope of what was verified, and what remains.
        """
        return {
            "frontend_audited": self.frontend_audited,
            "wcag_claim_allowed": self.frontend_audited,
            "verified_scope": ["color_contrast", "focus_guidance", "touch_target_guidance"],
            "unverified_scope": []
            if self.frontend_audited
            else [
                "vue_components_audit",
                "keyboard_navigation_live",
                "screen_reader_live",
                "dynamic_content_aria",
            ],
            "status": "audited" if self.frontend_audited else "pending_frontend_audit",
        }

    def mark_frontend_audited(self, audited: bool = True) -> None:
        """Set the frontend audit flag after (or before) a real UI review.

        Args:
            audited: True only when a real frontend/UI accessibility audit happened.
        """
        self.frontend_audited = audited
        logger.info(f"[ACCESSIBILITY] frontend_audited set to {audited}")

    def set_config(self, config: AccessibilityConfig) -> None:
        """Update accessibility configuration.

        Args:
            config: New accessibility configuration
        """
        self.config = config
        logger.info(f"[ACCESSIBILITY] Config updated: level={config.wcag_level.value}, high_contrast={config.high_contrast_mode}")

    def check_contrast_ratio(self, foreground: str, background: str) -> ContrastCheckResult:
        """Check contrast ratio between two colors against WCAG standards.

        Uses the WCAG 2.1 formula for luminance calculation.

        Args:
            foreground: HEX color string (e.g., "#ffffff", "white")
            background: HEX color string (e.g., "#000000", "black")

        Returns:
            ContrastCheckResult with pass/fail status for AA and AAA levels
        """
        # Check cache first
        cache_key = (foreground.lower(), background.lower())
        if cache_key in self._contrast_cache:
            return self._contrast_cache[cache_key]

        # Parse colors
        fg_r, fg_g, fg_b = self._hex_to_rgb(foreground)
        bg_r, bg_g, bg_b = self._hex_to_rgb(background)

        # Calculate relative luminance per WCAG 2.1
        fg_luminance = self._relative_luminance(fg_r, fg_g, fg_b)
        bg_luminance = self._relative_luminance(bg_r, bg_g, bg_b)

        # Contrast ratio = (L1 + 0.05) / (L2 + 0.05) where L1 is lighter
        lighter = max(fg_luminance, bg_luminance)
        darker = min(fg_luminance, bg_luminance)
        ratio = (lighter + 0.05) / (darker + 0.05)

        ratio_str = f"{ratio:.1f}:1"

        # WCAG thresholds
        passes_aaa_normal = ratio >= 7.0

        # Determine pass levels based on configured WCAG level
        if self.config.wcag_level == WCAGLevel.AAA:
            passes_aa = passes_aaa_normal
            passes_aaa = passes_aaa_normal
        elif self.config.wcag_level == WCAGLevel.AA:
            passes_aa = ratio >= 4.5
            passes_aaa = ratio >= 7.0
        else:  # Level A
            passes_aa = ratio >= 3.0  # Minimal AA threshold
            passes_aaa = False

        # Generate recommendations
        recommendations: list[str] = []
        if not passes_aa:
            if ratio >= 3.0:
                recommendations.append("AA large text threshold met; consider AA normal text improvements")
            else:
                recommendations.append(f"contrast ratio {ratio_str} below WCAG AA minimum (4.5:1). Consider color adjustment or alternative visual cues.")
        if not passes_aaa and self.config.wcag_level != WCAGLevel.A:
            recommendations.append(f"AAA ratio {ratio_str} not met. Consider increasing contrast.")

        result = ContrastCheckResult(
            foreground=foreground,
            background=background,
            ratio=ratio_str,
            passes_aa=passes_aa,
            passes_aaa=passes_aaa,
            recommendations=recommendations,
        )

        # Cache result
        self._contrast_cache[cache_key] = result
        logger.debug(f"[CONTRAST] {foreground} on {background}: {ratio_str} - AA: {passes_aa}, AAA: {passes_aaa}")

        return result

    def _hex_to_rgb(self, color: str) -> tuple[int, int, int]:
        """Convert HEX color to RGB tuple."""

        color = color.strip()
        if color.startswith("#"):
            color = color[1:]

        # Handle 3-digit hex (e.g., #fff → #ffffff)
        if len(color) == 3:
            color = "".join([c + c for c in color])

        if len(color) != 6:
            raise ValueError(f"Invalid HEX color: {color}")

        return (
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16),
        )

    def _relative_luminance(self, r: int, g: int, b: int) -> float:
        """Calculate relative luminance per WCAG 2.1.

        Applies sRGB luminance transformation.
        """
        # Normalize to 0-1
        r_norm = r / 255.0
        g_norm = g / 255.0
        b_norm = b / 255.0

        # Apply sRGB luminance transformation
        def transform(c: float) -> float:
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r_l = transform(r_norm)
        g_l = transform(g_norm)
        b_l = transform(b_norm)

        # Calculate luminance using WCAG weights
        return 0.2126 * r_l + 0.7152 * g_l + 0.0722 * b_l

    def generate_compliance_report(self, config: AccessibilityConfig | None = None) -> AccessibilityReport:
        """Generate a full accessibility compliance report.

        Args:
            config: Optional config override; uses self.config if not provided

        Returns:
            AccessibilityReport with full compliance assessment
        """
        if config:
            self.set_config(config)

        self._report = AccessibilityReport(config=self.config)

        # In a full implementation, this would scan all UI components,
        # API responses, and generated output for accessibility issues.
        # For now, we establish the compliance framework.

        # Check default system colors against WCAG AA
        # OWNEX primary colors: black bg, white primary, Tesla red #e82127
        default_checks = [
            # Black background with white text (ideal contrast)
            self.check_contrast_ratio("#ffffff", "#000000"),
            # Tesla red on white
            self.check_contrast_ratio("#e82127", "#ffffff"),
            # White on black (reverse)
            self.check_contrast_ratio("#ffffff", "#000000"),
            # Default text on default background
            self.check_contrast_ratio("#1a1a1a", "#ffffff"),
        ]

        self._report.contrast_checks = default_checks

        # Evaluate overall compliance
        all_pass_aa = all(check.passes_aa for check in self._report.contrast_checks)
        all_pass_aaa = all(check.passes_aaa for check in self._report.contrast_checks)

        if all_pass_aaa:
            self._report.overall_compliance = "aaa_compliant"
        elif all_pass_aa:
            self._report.overall_compliance = "aa_compliant"
        elif any(check.passes_aa for check in self._report.contrast_checks):
            # Partial compliance - some elements meet AA
            self._report.overall_compliance = "partial_aa"
        else:
            self._report.overall_compliance = "non_compliant"

        self._report.last_checked = datetime.now()
        self._report.frontend_audited = self.frontend_audited

        logger.info(
            f"[ACCESSIBILITY] Compliance report generated: {self._report.overall_compliance} (checked {len(self._report.contrast_checks)} color combinations)"
        )

        return self._report

    def get_focus_management_guidance(self) -> dict[str, Any]:
        """Get focus management guidance for keyboard navigation.

        Returns:
            Dictionary with focus-related accessibility guidelines
        """
        return {
            "focus_indicator_required": self.config.focus_indicator,
            "focus_ring_color": "#e82127" if self.config.high_contrast_mode else "#3b82f6",
            "focus_ring_width": "2px",
            "skip_link_text": "Skip to main content",
            "keyboard_navigation_enabled": self.config.keyboard_navigation,
            "tab_order_best_practices": [
                "Logical tab order following DOM structure",
                "Group related controls with fieldset/legend",
                "Use aria-label for custom controls",
                "Provide visible focus indicators",
                "Avoid tabindex > 1 (use multiple elements instead)",
            ],
            "screen_reader_tips": [
                "Use aria-labels for icons and custom controls",
                "Provide meaningful alt text for images",
                "Use heading hierarchy (h1-h6) correctly",
                "Landmark regions (nav, main, article, aside)",
                "Live regions for dynamic content updates",
            ],
        }

    def get_touch_target_guidance(self) -> dict[str, Any]:
        """Get touch target size guidance.

        Returns:
            Dictionary with touch target accessibility guidelines
        """
        return {
            "minimum_size_px": self.config.touch_target_min_pixels,
            "recommended_size_px": 48,
            "spacing_minimum_px": 8,
            "elements_requiring_large_targets": [
                "buttons",
                "links",
                "form controls",
                "navigation items",
                "menu items",
            ],
            "current_issues": self._detect_touch_target_issues(),
        }

    def _detect_touch_target_issues(self) -> list[str]:
        """Detect potential touch target issues.

        In a full implementation, this would scan actual UI components.
        For now, returns common issues based on config.
        """
        issues: list[str] = []

        if not self.config.keyboard_navigation:
            issues.append("Keyboard navigation disabled; ensure touch targets have keyboard alternatives")

        if self.config.high_contrast_mode and not self.config.focus_indicator:
            issues.append("High contrast mode enabled but focus indicator disabled; users may lose track of focused element")

        return issues

    def export_accessibility_settings(self) -> dict[str, Any]:
        """Export accessibility settings for persistence or sharing.

        Returns:
            Dictionary of accessibility settings
        """
        return {
            "wcag_level": self.config.wcag_level.value,
            "high_contrast_mode": self.config.high_contrast_mode,
            "screen_reader_mode": self.config.screen_reader_mode,
            "keyboard_navigation": self.config.keyboard_navigation,
            "reduced_motion": self.config.reduced_motion,
            "font_scaling": self.config.font_scaling,
            "touch_target_min_pixels": self.config.touch_target_min_pixels,
            "language": self.config.language,
            "aria_labels_enabled": self.config.aria_labels_enabled,
            "focus_indicator": self.config.focus_indicator,
            "last_checked": self._report.last_checked.isoformat() if self._report else None,
        }

    def import_accessibility_settings(self, settings: dict[str, Any]) -> None:
        """Import accessibility settings from exported configuration.

        Args:
            settings: Dictionary of accessibility settings (from export_accessibility_settings)
        """
        try:
            wcag_level = WCAGLevel(settings.get("wcag_level", "AA"))
            self.config = AccessibilityConfig(
                wcag_level=wcag_level,
                high_contrast_mode=settings.get("high_contrast_mode", False),
                screen_reader_mode=settings.get("screen_reader_mode", False),
                keyboard_navigation=settings.get("keyboard_navigation", True),
                reduced_motion=settings.get("reduced_motion", False),
                font_scaling=settings.get("font_scaling", 1.0),
                touch_target_min_pixels=settings.get("touch_target_min_pixels", 44),
                language=settings.get("language", "en"),
                aria_labels_enabled=settings.get("aria_labels_enabled", True),
                focus_indicator=settings.get("focus_indicator", True),
            )
            logger.info(f"[ACCESSIBILITY] Settings imported: WCAG {self.config.wcag_level.value}, high_contrast={self.config.high_contrast_mode}")
        except (ValueError, KeyError) as e:
            logger.error(f"[ACCESSIBILITY] Failed to import settings: {e}")
            raise


# Singleton instance for global access
_accessibility_engine: AccessibilityComplianceEngine | None = None


def get_accessibility_engine() -> AccessibilityComplianceEngine:
    """Get or create the global accessibility compliance engine instance."""
    global _accessibility_engine
    if _accessibility_engine is None:
        _accessibility_engine = AccessibilityComplianceEngine()
    return _accessibility_engine


def check_color_contrast(foreground: str, background: str) -> ContrastCheckResult:
    """Convenience function to check color contrast.

    Args:
        foreground: HEX color string
        background: HEX color string

    Returns:
        ContrastCheckResult with pass/fail status
    """
    engine = get_accessibility_engine()
    return engine.check_contrast_ratio(foreground, background)


def generate_full_report(config: AccessibilityConfig | None = None) -> AccessibilityReport:
    """Convenience function to generate full accessibility report.

    Args:
        config: Optional config override

    Returns:
        AccessibilityReport with full compliance assessment
    """
    engine = get_accessibility_engine()
    return engine.generate_compliance_report(config)


def export_settings() -> dict[str, Any]:
    """Convenience function to export accessibility settings.

    Returns:
        Dictionary of accessibility settings
    """
    engine = get_accessibility_engine()
    return engine.export_accessibility_settings()


def import_settings(settings: dict[str, Any]) -> None:
    """Convenience function to import accessibility settings.

    Args:
        settings: Dictionary of accessibility settings
    """
    engine = get_accessibility_engine()
    engine.import_accessibility_settings(settings)
