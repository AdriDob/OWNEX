"""Opportunity Analyzer — generates internal analysis reports for opportunities.

Takes an opportunity ID and produces a step-by-step guide with
estimated reward, effort, and learning resources.
"""

from __future__ import annotations

import logging
from typing import Any

from cores.opportunity import get_engine as get_opp_engine
from cores.opportunity.models import Opportunity

logger = logging.getLogger("catseye.orion.analyzer")


def _category_guide(cat: str) -> list[dict[str, str]]:
    """Return learning resources based on category."""
    guides = {
        "web": [
            {"title": "OWASP Top 10", "url": "https://owasp.org/www-project-top-ten/"},
            {"title": "Web Security Academy", "url": "https://portswigger.net/web-security"},
        ],
        "api": [
            {"title": "API Security Checklist", "url": "https://github.com/shieldfy/API-Security-Checklist"},
            {"title": "REST API Security", "url": "https://roadmap.sh/api-security"},
        ],
        "mobile": [
            {"title": "Mobile Security Guide", "url": "https://mobilesecuritywiki.com/"},
        ],
        "web3": [
            {"title": "Smart Contract Security", "url": "https://swcregistry.io/"},
        ],
        "cloud": [
            {"title": "Cloud Security Checklist", "url": "https://cloudsecurityalliance.org/"},
        ],
    }
    return guides.get(cat, [
        {"title": "Security Fundamentals", "url": "https://portswigger.net/web-security"},
    ])


def _generate_analysis(opp: Opportunity) -> dict[str, Any]:
    """Generate a full analysis report for a single opportunity."""
    score = opp.score
    cat = opp.category.value if opp.category else "general"

    max_r = score.reward_range_max if score else None
    min_r = score.reward_range_min if score else None
    if max_r and min_r:
        reward_str = f"${min_r} - ${max_r}"
    elif max_r:
        reward_str = f"Up to ${max_r}"
    else:
        reward_str = "Variable"

    exec_s = getattr(score, "execution_score", 0.5) if score else 0.5
    if exec_s > 0.7:
        effort_str = "Low — suitable for beginners"
    elif exec_s > 0.4:
        effort_str = "Medium — some prior knowledge helpful"
    else:
        effort_str = "High — advanced techniques may be needed"

    evh_val = score.evh.value if score and score.evh else None

    return {
        "opportunity_id": opp.id,
        "title": opp.title or opp.name,
        "source_url": opp.source.url if opp.source else "",
        "category": cat,
        "priority": opp.priority or "medium",
        "reward_estimate": reward_str,
        "effort": effort_str,
        "evh": round(evh_val, 2) if evh_val else None,
        "summary": f"{opp.title or opp.name} — a {cat} opportunity from {opp.source.name if opp.source else 'unknown source'}.",
        "why_it_matters": _generate_why_matters(opp),
        "steps": _generate_steps(opp, cat),
        "learning_resources": _category_guide(cat),
        "risk_opportunity_summary": _risk_opportunity_summary(opp),
    }


def _generate_why_matters(opp: Opportunity) -> str:
    """Explain why this opportunity matters in plain language."""
    score = opp.score
    parts = []
    if score and score.reward_range_max:
        parts.append(f"Potential reward up to ${score.reward_range_max}.")
    cat = opp.category.value if opp.category else "general"
    parts.append(f"This is a {cat}-based opportunity.")
    if score and getattr(score, "competition_score", 0) > 0.6:
        parts.append("Competition is low, increasing your chances.")
    elif score and getattr(score, "competition_score", 0) < 0.3:
        parts.append("Competition is high, but the reward may still justify the effort.")
    parts.append("Review the scope carefully before starting.")
    return " ".join(parts)


def _generate_steps(opp: Opportunity, cat: str) -> list[dict[str, str]]:
    """Generate actionable steps for this opportunity."""
    steps = [
        {"step": 1, "title": "Review opportunity scope", "description": f"Read the full scope and rules for {opp.title or opp.name}. Understand what is in and out of scope."},
        {"step": 2, "title": "Set up your environment", "description": "Prepare your tools: browser, proxies, and any required accounts."},
    ]
    if cat in ("web", "api"):
        steps.append({"step": 3, "title": "Reconnaissance", "description": "Map the target: endpoints, parameters, authentication mechanisms."})
        steps.append({"step": 4, "title": "Test for common issues", "description": "Check for OWASP Top 10 vulnerabilities relevant to this target."})
    elif cat == "web3":
        steps.append({"step": 3, "title": "Review smart contract", "description": "Read the contract code if available. Look for common patterns."})
        steps.append({"step": 4, "title": "Test for vulnerabilities", "description": "Check for reentrancy, access control, and oracle issues."})
    else:
        steps.append({"step": 3, "title": "Explore the target", "description": "Understand the attack surface and identify potential issues."})
        steps.append({"step": 4, "title": "Document findings", "description": "Record any issues found with clear steps to reproduce."})
    steps.append({"step": 5, "title": "Generate report", "description": "Create a structured report of your findings and analysis."})
    return steps


def _risk_opportunity_summary(opp: Opportunity) -> str:
    """Return a balanced risk/opportunity summary."""
    score = opp.score
    if not score:
        return "Review this opportunity to assess risk and potential."
    evh = score.evh.value if score.evh else 0
    if evh and evh > 50:
        return f"High opportunity with strong EVH (${evh}/hr). Low risk: well-defined scope."
    elif evh and evh > 20:
        return f"Moderate opportunity (${evh}/hr). Standard risk level."
    else:
        return "Lower immediate value, but may have strategic importance or learning value."


def analyze_opportunity(opportunity_id: str) -> dict[str, Any] | None:
    """Generate a full analysis for the given opportunity ID.

    Returns a dict with analysis report, or None if not found.
    """
    logger.info("[Orion] analyze_opportunity: %s", opportunity_id)
    try:
        engine = get_opp_engine()
        opp = engine.get_by_id(opportunity_id)
    except Exception as exc:
        logger.warning("[Orion] failed to get opportunity %s: %s", opportunity_id, exc)
        return None

    if not opp:
        logger.warning("[Orion] opportunity not found: %s", opportunity_id)
        return None

    analysis = _generate_analysis(opp)
    logger.info("[Orion] analysis generated for %s", opportunity_id)
    return analysis
