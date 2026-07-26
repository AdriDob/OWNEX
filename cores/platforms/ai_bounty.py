"""AI Bounty platform connectors — Imbue, Anthropic, OpenAI, Google AI."""

from __future__ import annotations

import json
import logging
from typing import Any

from cores.platforms.base import BugBountyPlatform, SubmissionResult

logger = logging.getLogger("cateye.platforms.ai_bounty")


AI_BOUNTY_PROGRAMS: dict[str, dict[str, Any]] = {
    "imbue": {
        "name": "Imbue AI Bounty",
        "url": "https://imbue.com/bounty-program/",
        "submit_url": "https://imbue.com/bounty-program/submit",
    },
    "anthropic": {
        "name": "Anthropic Red Teaming",
        "url": "https://www.anthropic.com/red-teaming",
        "submit_url": "https://forms.anthropic.com/red-teaming",
    },
    "openai": {
        "name": "OpenAI Bug Bounty",
        "url": "https://openai.com/bug-bounty-program/",
        "submit_url": "https://openai.com/bug-bounty-program/submit",
    },
    "google_ai": {
        "name": "Google AI Red Team",
        "url": "https://bughunters.google.com/about/rules/ai-red-team",
        "submit_url": "https://bughunters.google.com/report",
    },
}


class ImbueBounty(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "imbue"

    @property
    def display_name(self) -> str:
        return "Imbue AI Bounty"

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        content = report_data.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {"summary": content[:500]}
        return {
            "program": "imbue-bounty",
            "title": report_data.get("vulnerability", content.get("title", "AI Security Finding")),
            "description": content.get("description", content.get("summary", "")),
            "severity": report_data.get("severity", "medium"),
            "category": content.get("category", "ai_safety"),
            "reproducibility": content.get("reproducibility", ""),
            "impact": content.get("impact", ""),
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return "https://imbue.com/bounty-program/submit"

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        return SubmissionResult(
            success=False,
            error="Imbue requires manual web submission — auto-submit not supported",
        )


class AnthropicBounty(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "anthropic"

    @property
    def display_name(self) -> str:
        return "Anthropic Red Teaming"

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        content = report_data.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {"summary": content[:500]}
        return {
            "program": "anthropic-red-teaming",
            "title": report_data.get("vulnerability", content.get("title", "AI Safety Finding")),
            "description": content.get("description", content.get("summary", "")),
            "severity": report_data.get("severity", "medium"),
            "category": content.get("category", "ai_safety"),
            "model": content.get("model", ""),
            "prompt": content.get("prompt", ""),
            "response": content.get("response", ""),
            "reproducibility": content.get("reproducibility", ""),
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return "https://forms.anthropic.com/red-teaming"

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        return SubmissionResult(
            success=False,
            error="Anthropic requires manual form submission — auto-submit not supported",
        )


class OpenAIBounty(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "openai"

    @property
    def display_name(self) -> str:
        return "OpenAI Bug Bounty"

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        content = report_data.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {"summary": content[:500]}
        return {
            "program": "openai-bug-bounty",
            "title": report_data.get("vulnerability", content.get("title", "Security Finding")),
            "description": content.get("description", content.get("summary", "")),
            "severity": report_data.get("severity", "medium"),
            "category": content.get("category", "security"),
            "impact": content.get("impact", ""),
            "reproducibility": content.get("reproducibility", ""),
            "affected_component": content.get("affected_component", ""),
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return "https://openai.com/bug-bounty-program/submit"

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        return SubmissionResult(
            success=False,
            error="OpenAI requires manual web submission — auto-submit not supported",
        )


class GoogleAIBounty(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "google_ai"

    @property
    def display_name(self) -> str:
        return "Google AI Red Team"

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        content = report_data.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {"summary": content[:500]}
        return {
            "program": "google-ai-red-team",
            "title": report_data.get("vulnerability", content.get("title", "AI Red Team Finding")),
            "description": content.get("description", content.get("summary", "")),
            "severity": report_data.get("severity", "medium"),
            "category": content.get("category", "ai_red_team"),
            "impact": content.get("impact", ""),
            "reproducibility": content.get("reproducibility", ""),
            "affected_product": content.get("affected_product", ""),
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return "https://bughunters.google.com/report"

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        return SubmissionResult(
            success=False,
            error="Google AI requires manual submission via bughunters.google.com",
        )


AI_BOUNTY_REGISTRY: dict[str, type[BugBountyPlatform]] = {
    "imbue": ImbueBounty,
    "anthropic": AnthropicBounty,
    "openai": OpenAIBounty,
    "google_ai": GoogleAIBounty,
}
