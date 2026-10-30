"""Platform Guides API router.

Exposes structured onboarding guides for each supported platform.
Zero-to-Earning: guides the owner from "never used this platform" to "first earning".
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from cores.opportunity.guides.platform_guides import (
    format_guide_for_user,
    get_platform_guide,
    list_all_platforms,
)

router = APIRouter(prefix="/platform-guides", tags=["platform-guides"])


@router.get("/")
async def list_platform_guides() -> dict[str, Any]:
    """List all platforms with onboarding guides."""
    platforms = list_all_platforms()
    return {
        "platforms": platforms,
        "count": len(platforms),
    }


@router.get("/{platform}")
async def get_platform_guide_endpoint(
    platform: str,
    guide_type: str = Query("account", pattern="^(account|work)$"),
) -> dict[str, Any]:
    """Get full onboarding guide for a platform.

    Args:
        platform: Platform key (e.g., hackerone, fiverr, outlier)
        guide_type: "account" for account creation, "work" for work submission
    """
    guide = get_platform_guide(platform)
    if not guide:
        raise HTTPException(
            status_code=404,
            detail=f"Guide for platform '{platform}' not found. Available: {list_all_platforms()}",
        )

    formatted = format_guide_for_user(guide, guide_type)

    return {
        "platform": guide.platform,
        "name": guide.name,
        "url": guide.url,
        "guide_type": guide_type,
        "formatted": formatted,
        "steps_count": len(guide.account_creation if guide_type == "account" else guide.work_submission),
        "file_formats": guide.file_formats,
        "tips": guide.tips,
        "common_errors": guide.common_errors,
    }


@router.get("/{platform}/steps")
async def get_platform_guide_steps(
    platform: str,
    guide_type: str = Query("account", pattern="^(account|work)$"),
) -> dict[str, Any]:
    """Get structured steps for a platform guide (for UI rendering)."""
    guide = get_platform_guide(platform)
    if not guide:
        raise HTTPException(
            status_code=404,
            detail=f"Guide for platform '{platform}' not found.",
        )

    steps = guide.account_creation if guide_type == "account" else guide.work_submission

    return {
        "platform": guide.platform,
        "name": guide.name,
        "url": guide.url,
        "guide_type": guide_type,
        "steps": [
            {
                "index": i + 1,
                "title": step.title,
                "description": step.description,
                "action": step.action,
                "element": step.element,
                "value": step.value,
                "url": step.url,
                "screenshot_hint": step.screenshot_hint,
            }
            for i, step in enumerate(steps)
        ],
        "file_formats": guide.file_formats,
        "tips": guide.tips,
        "common_errors": guide.common_errors,
    }


@router.get("/{platform}/first-opportunity")
async def get_platform_first_opportunity(platform: str) -> dict[str, Any]:
    """Get recommended first opportunity for a beginner on this platform.

    Returns a beginner-friendly opportunity with full context.
    """
    guide = get_platform_guide(platform)
    if not guide:
        raise HTTPException(
            status_code=404,
            detail=f"Guide for platform '{platform}' not found.",
        )

    # Platform-specific first opportunity recommendations
    first_opp = {
        "hackerone": {
            "title": "Hacker101 Practice CTF",
            "description": "Free guided practice from HackerOne to learn bug bounty basics",
            "url": "https://hacker101.com",
            "why": "Official HackerOne learning platform, completely free, teaches real vulnerability classes",
            "difficulty": "beginner",
            "estimated_time": "2-4 hours",
            "skills_practiced": ["recon", "xss", "sqli", "idor", "auth_bypass"],
            "next_action": "Complete the first CTF level and document findings",
        },
        "bugcrowd": {
            "title": "Bugcrowd University",
            "description": "Free educational content from Bugcrowd for learning bug bounty",
            "url": "https://www.bugcrowd.com/resources/bugcrowd-university",
            "why": "Official Bugcrowd education, covers methodology and common vulnerability classes",
            "difficulty": "beginner",
            "estimated_time": "3-5 hours",
            "skills_practiced": ["methodology", "report_writing", "scope_understanding"],
            "next_action": "Watch the 'Bug Bounty Methodology' module",
        },
        "intigriti": {
            "title": "Intigriti 0x Challenge Archive",
            "description": "Past monthly challenges for practice",
            "url": "https://challenge.intigriti.io",
            "why": "Real past challenges with writeups, teaches practical exploitation",
            "difficulty": "beginner",
            "estimated_time": "4-8 hours",
            "skills_practiced": ["web_vulns", "client_side", "logic_bugs"],
            "next_action": "Start with the earliest challenge and read the writeup",
        },
        "yeswehack": {
            "title": "YesWeHack Learning Center",
            "description": "Educational resources from YesWeHack",
            "url": "https://www.yeswehack.com/learn",
            "why": "Official learning resources from the platform",
            "difficulty": "beginner",
            "estimated_time": "2-3 hours",
            "skills_practiced": ["platform_usage", "report_quality", "communication"],
            "next_action": "Review the 'Getting Started' guide",
        },
        "fiverr": {
            "title": "Create Your First Gig",
            "description": "Set up a service listing for a specific technical problem you solve",
            "url": "https://www.fiverr.com/start_selling",
            "why": "Fiverr rewards specialization - one clear service beats generic 'I do coding'",
            "difficulty": "beginner",
            "estimated_time": "1-2 hours",
            "skills_practiced": ["service_design", "pricing", "portfolio_presentation"],
            "next_action": "Pick ONE service (e.g., 'Python automation script') and create the gig",
        },
        "opire": {
            "title": "First Open Source Bounty",
            "description": "Find a labeled 'good first issue' on a project using Opire",
            "url": "https://opire.net",
            "why": "Opire aggregates GitHub issues with bounties, good for beginners",
            "difficulty": "beginner",
            "estimated_time": "4-8 hours",
            "skills_practiced": ["git", "github_workflow", "code_review", "testing"],
            "next_action": "Filter for 'good first issue' + bounty > $50",
        },
        "issuehunt": {
            "title": "First IssueHunt Bounty",
            "description": "Claim and solve a labeled issue on IssueHunt",
            "url": "https://issuehunt.io",
            "why": "Direct GitHub integration, clear requirements",
            "difficulty": "beginner",
            "estimated_time": "4-8 hours",
            "skills_practiced": ["issue_analysis", "implementation", "pr_process"],
            "next_action": "Browse repos with 'good first issue' label",
        },
        "outlier": {
            "title": "First Outlier Job",
            "description": "Complete qualification and first paid task on Outlier",
            "url": "https://platform.outlier.ai",
            "why": "AI training pays per task, zero portfolio needed, immediate start",
            "difficulty": "beginner",
            "estimated_time": "1-2 hours (qualification + first task)",
            "skills_practiced": ["following_instructions", "quality_consistency", "time_management"],
            "next_action": "Complete the qualification assessment for your language",
        },
        "mindrift": {
            "title": "Mindrift Qualification",
            "description": "Pass the qualification test for AI training projects",
            "url": "https://mindrift.com",
            "why": "Mindrift pays for AI data tasks, open to Argentina directly",
            "difficulty": "beginner",
            "estimated_time": "30-60 min qualification",
            "skills_practiced": ["attention_to_detail", "instruction_following", "consistency"],
            "next_action": "Sign up and take the qualification test",
        },
        "workana": {
            "title": "First Workana proposal",
            "description": "Send one tailored proposal for a Python/API/automation project with clear scope",
            "url": "https://www.workana.com/jobs",
            "why": "LATAM marketplace with less global competition than Upwork; Spanish/English projects",
            "difficulty": "beginner",
            "estimated_time": "1-2 hours (profile + first proposal)",
            "skills_practiced": ["proposal_writing", "scoping", "client_communication"],
            "next_action": "Complete profile, set Payoneer payout, send first tailored proposal",
        },
    }

    recommendation = first_opp.get(
        platform.lower(),
        {
            "title": f"First opportunity on {guide.name}",
            "description": "Explore the platform and find a beginner-friendly task",
            "url": guide.url,
            "why": "Start with low-risk, well-documented opportunities",
            "difficulty": "beginner",
            "estimated_time": "varies",
            "skills_practiced": ["platform_navigation", "requirement_following"],
            "next_action": "Browse available opportunities and read requirements carefully",
        },
    )

    return {
        "platform": guide.platform,
        "name": guide.name,
        "recommendation": recommendation,
        "guide_available": True,
    }


@router.get("/workplatform/mapping")
async def get_workplatform_mapping() -> dict[str, Any]:
    """Map WorkPlatform enum to guide availability."""
    from cores.direct_work_engine.models import WorkPlatform

    platforms_with_guides = list_all_platforms()
    mapping = {}

    for wp in WorkPlatform:
        has_guide = wp.value in platforms_with_guides
        mapping[wp.value] = {
            "has_guide": has_guide,
            "guide_url": f"/api/platform-guides/{wp.value}" if has_guide else None,
        }

    return {
        "total_platforms": len(WorkPlatform),
        "platforms_with_guides": len(platforms_with_guides),
        "mapping": mapping,
    }
