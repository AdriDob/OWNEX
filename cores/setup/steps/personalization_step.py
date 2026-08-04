"""Personalization Step — Ask user what they want to use OWNEX OMEGA for and adapt configuration."""

from __future__ import annotations

import logging
from typing import Any

from core.setup.steps import define_step

logger = logging.getLogger("ownex.core.setup.personalization")


@define_step(
    step_id="personalization",
    label="Personalización",
    description="Configura OWNEX OMEGA según tus necesidades específicas",
    icon="user",
    order=1,  # First step after identity
    required=True,
    schema={
        "type": "object",
        "properties": {
            "use_case": {
                "type": "string",
                "enum": [
                    "bug_bounty_researcher",
                    "bug_bounty_company",
                    "cybersecurity_consultant",
                    "penetration_tester",
                    "security_analyst",
                    "developer",
                    "researcher",
                    "hobbyist",
                    "other",
                ],
                "title": "Casos de uso",
            },
            "modules": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "forge",
                        "pulse",
                        "vault",
                        "atlas",
                        "security",
                        "copilot",
                        "analytics",
                        "reports",
                        "targets",
                        "integrations",
                    ],
                },
                "title": "Módulos a habilitar",
            },
            "custom_name": {"type": "string", "title": "Nombre personalizado (opcional)"},
            "expertise_level": {
                "type": "string",
                "enum": ["beginner", "intermediate", "advanced", "expert"],
                "title": "Nivel de experiencia",
            },
            "primary_platforms": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["hackerone", "bugcrowd", "intigriti", "yeswehack", "synack", "all"],
                },
                "title": "Plataformas principales",
            },
        },
    },
)
def personalization_step(data: dict[str, Any]) -> dict[str, Any]:
    """Personalize OWNEX OMEGA based on user's use case and preferences."""
    use_case = data.get("use_case", "bug_bounty_researcher")
    modules = data.get("modules", [])
    custom_name = data.get("custom_name", "")
    expertise_level = data.get("expertise_level", "intermediate")
    primary_platforms = data.get("primary_platforms", ["all"])

    logger.info(f"[PERSONALIZATION] Use case: {use_case}")
    logger.info(f"[PERSONALIZATION] Modules: {modules}")
    logger.info(f"[PERSONALIZATION] Expertise: {expertise_level}")
    logger.info(f"[PERSONALIZATION] Platforms: {primary_platforms}")

    # Default modules based on use case
    default_modules = _get_default_modules_for_use_case(use_case)
    final_modules = modules if modules else default_modules

    # Customize configuration based on use case
    config = _build_personalized_config(
        use_case=use_case,
        modules=final_modules,
        custom_name=custom_name,
        expertise_level=expertise_level,
        primary_platforms=primary_platforms,
    )

    return {
        "status": "ok",
        "message": "Personalización completada con éxito",
        "data": {
            "use_case": use_case,
            "modules": final_modules,
            "custom_name": custom_name,
            "expertise_level": expertise_level,
            "primary_platforms": primary_platforms,
            "config": config,
        },
    }


def _get_default_modules_for_use_case(use_case: str) -> list[str]:
    """Get default modules based on use case."""
    modules_map = {
        "bug_bounty_researcher": ["forge", "pulse", "vault", "security", "copilot", "analytics", "reports", "targets"],
        "bug_bounty_company": [
            "forge",
            "pulse",
            "vault",
            "atlas",
            "security",
            "copilot",
            "analytics",
            "reports",
            "integrations",
        ],
        "cybersecurity_consultant": [
            "forge",
            "pulse",
            "vault",
            "atlas",
            "security",
            "copilot",
            "analytics",
            "reports",
            "targets",
        ],
        "penetration_tester": ["forge", "pulse", "vault", "security", "copilot", "analytics", "reports", "targets"],
        "security_analyst": ["forge", "pulse", "atlas", "security", "copilot", "analytics", "reports"],
        "developer": ["forge", "security", "copilot", "analytics", "targets"],
        "researcher": ["forge", "pulse", "atlas", "copilot", "analytics", "reports"],
        "hobbyist": ["forge", "pulse", "copilot", "analytics"],
        "other": ["forge", "pulse", "copilot", "analytics"],
    }
    return modules_map.get(use_case, ["forge", "pulse", "copilot", "analytics"])


def _build_personalized_config(
    use_case: str, modules: list[str], custom_name: str, expertise_level: str, primary_platforms: list[str]
) -> dict[str, Any]:
    """Build personalized configuration based on user preferences."""
    config = {
        "use_case": use_case,
        "enabled_modules": modules,
        "expertise_level": expertise_level,
        "primary_platforms": primary_platforms,
        "ui_customization": _get_ui_customization(use_case, custom_name),
        "feature_flags": _get_feature_flags(expertise_level, modules),
        "platform_config": _get_platform_config(primary_platforms),
        "automation_level": _get_automation_level(expertise_level),
        "notification_settings": _get_notification_settings(use_case),
        "analytics_settings": _get_analytics_settings(use_case),
        "report_settings": _get_report_settings(use_case, expertise_level),
    }

    return config


def _get_ui_customization(use_case: str, custom_name: str) -> dict[str, Any]:
    """Get UI customization based on use case."""
    return {
        "app_name": custom_name if custom_name else "OWNEX OMEGA",
        "theme": "dark",
        "accent_color": _get_accent_color_for_use_case(use_case),
        "dashboard_layout": _get_dashboard_layout_for_use_case(use_case),
        "show_advanced_features": True,
    }


def _get_accent_color_for_use_case(use_case: str) -> str:
    """Get accent color based on use case."""
    colors = {
        "bug_bounty_researcher": "#60A5FA",  # Blue
        "bug_bounty_company": "#34D399",  # Green
        "cybersecurity_consultant": "#FBBF24",  # Gold
        "penetration_tester": "#F87171",  # Red
        "security_analyst": "#A78BFA",  # Purple
        "developer": "#2DD4BF",  # Teal
        "researcher": "#FB923C",  # Orange
        "hobbyist": "#F472B6",  # Pink
        "other": "#94A3B8",  # Gray
    }
    return colors.get(use_case, "#60A5FA")


def _get_dashboard_layout_for_use_case(use_case: str) -> str:
    """Get dashboard layout based on use case."""
    layouts = {
        "bug_bounty_researcher": "researcher",
        "bug_bounty_company": "manager",
        "cybersecurity_consultant": "consultant",
        "penetration_tester": "pentester",
        "security_analyst": "analyst",
        "developer": "developer",
        "researcher": "researcher",
        "hobbyist": "simple",
        "other": "default",
    }
    return layouts.get(use_case, "default")


def _get_feature_flags(expertise_level: str, modules: list[str]) -> dict[str, bool]:
    """Get feature flags based on expertise level and modules."""
    flags = {
        "advanced_analytics": expertise_level in ["advanced", "expert"],
        "automated_patching": expertise_level == "expert",
        "ai_recommendations": True,
        "batch_operations": expertise_level in ["intermediate", "advanced", "expert"],
        "custom_workflows": expertise_level in ["advanced", "expert"],
        "api_access": True,
        "export_reports": "reports" in modules,
        "target_management": "targets" in modules,
        "integration_hub": "integrations" in modules,
        "collaboration": "atlas" in modules,
        "financial_tracking": "vault" in modules,
        "pulse_automation": "pulse" in modules,
        "forge_automation": "forge" in modules,
    }
    return flags


def _get_platform_config(primary_platforms: list[str]) -> dict[str, Any]:
    """Get platform configuration based on primary platforms."""
    return {
        "enabled_platforms": primary_platforms
        if primary_platforms != ["all"]
        else ["hackerone", "bugcrowd", "intigriti", "yeswehack", "synack"],
        "auto_discovery": True,
        "notification_frequency": "realtime",
        "sync_interval": 300,  # 5 minutes
    }


def _get_automation_level(expertise_level: str) -> str:
    """Get automation level based on expertise."""
    levels = {
        "beginner": "manual",
        "intermediate": "assisted",
        "advanced": "semi_automated",
        "expert": "fully_automated",
    }
    return levels.get(expertise_level, "assisted")


def _get_notification_settings(use_case: str) -> dict[str, Any]:
    """Get notification settings based on use case."""
    return {
        "email_notifications": True,
        "push_notifications": True,
        "slack_notifications": use_case in ["bug_bounty_company", "cybersecurity_consultant"],
        "telegram_notifications": use_case in ["bug_bounty_researcher", "penetration_tester"],
        "notification_types": ["new_target", "finding_accepted", "payout", "vulnerability_report"],
    }


def _get_analytics_settings(use_case: str) -> dict[str, Any]:
    """Get analytics settings based on use case."""
    return {
        "enable_analytics": True,
        "track_conversions": use_case in ["bug_bounty_company", "cybersecurity_consultant"],
        "track_revenue": "vault" in _get_default_modules_for_use_case(use_case),
        "track_productivity": True,
        "track_success_rate": True,
        "retention_days": 90,
    }


def _get_report_settings(use_case: str, expertise_level: str) -> dict[str, Any]:
    """Get report settings based on use case and expertise."""
    return {
        "auto_generate_reports": expertise_level in ["advanced", "expert"],
        "report_format": "pdf",
        "include_screenshots": True,
        "include_proof": True,
        "custom_templates": expertise_level == "expert",
        "report_frequency": "weekly" if expertise_level in ["beginner", "intermediate"] else "daily",
    }
