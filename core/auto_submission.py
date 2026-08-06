"""Auto-Submission Engine — envía fixes, propuestas y reportes a plataformas vía API.

Automatiza el último paso: subir el trabajo a la plataforma.
Cubre:
- Bug Bounty: envía reportes a HackerOne/Bugcrowd/Immunefi vía API
- Forge: crea PRs en GitHub/GitLab con fixes
- Freelancer: envía propuestas a proyectos
- Pulse: sube tareas completadas
- Generic: form submission via browser automation
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.auto_submission")


# ── Bug Bounty Submission ───────────────────────────────────────


class BBSubmissionClient:
    """Submit bug bounty reports via platform APIs."""

    async def submit_hackerone(
        self,
        title: str,
        description: str,
        severity: str,
        cwe: str = "",
        api_key: str = "",
        program: str = "",
    ) -> dict[str, Any]:
        """Submit report to HackerOne via API."""
        try:
            import httpx

            resp = httpx.post(
                "https://api.hackerone.com/v1/reports",
                auth=(api_key, ""),
                json={
                    "data": {
                        "type": "report",
                        "attributes": {
                            "title": title,
                            "vulnerability_information": description,
                            "severity_rating": severity.lower(),
                            "custom_fields": {"cwe": cwe} if cwe else {},
                        },
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                report_id = data.get("data", {}).get("id", "")
                return {
                    "success": True,
                    "platform": "hackerone",
                    "external_id": report_id,
                    "url": f"https://hackerone.com/reports/{report_id}",
                }
            return {"success": False, "platform": "hackerone", "error": resp.text}
        except Exception as e:
            return {"success": False, "platform": "hackerone", "error": str(e)}

    async def submit_bugcrowd(
        self,
        title: str,
        description: str,
        severity: str,
        api_key: str = "",
        program: str = "",
    ) -> dict[str, Any]:
        """Submit report to Bugcrowd via API."""
        try:
            import httpx

            resp = httpx.post(
                "https://api.bugcrowd.com/v1/submissions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "title": title,
                    "description": description,
                    "severity": severity.lower(),
                    "program": program,
                },
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "success": True,
                    "platform": "bugcrowd",
                    "external_id": data.get("id", ""),
                }
            return {"success": False, "platform": "bugcrowd", "error": resp.text}
        except Exception as e:
            return {"success": False, "platform": "bugcrowd", "error": str(e)}

    async def submit_immunefi(
        self,
        title: str,
        description: str,
        severity: str,
        asset: str = "",
        api_key: str = "",
        program: str = "",
    ) -> dict[str, Any]:
        """Submit report to Immunefi via API."""
        try:
            import httpx

            resp = httpx.post(
                "https://api.immunefi.com/v1/submissions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "program": program,
                    "title": title,
                    "description": description,
                    "vulnerability_type": "other",
                    "severity": severity.lower(),
                    "asset": asset,
                },
                timeout=60,
            )
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                return {
                    "success": True,
                    "platform": "immunefi",
                    "external_id": data.get("id", ""),
                }
            return {"success": False, "platform": "immunefi", "error": resp.text}
        except Exception as e:
            return {"success": False, "platform": "immunefi", "error": str(e)}

    async def submit_intigriti(
        self,
        title: str,
        description: str,
        severity: str,
        api_key: str = "",
        program: str = "",
    ) -> dict[str, Any]:
        """Submit report to Intigriti via API."""
        try:
            import httpx

            resp = httpx.post(
                "https://api.intigriti.com/v1/submissions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "title": title,
                    "description": description,
                    "severity": severity.lower(),
                },
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "success": True,
                    "platform": "intigriti",
                    "external_id": data.get("id", ""),
                }
            return {"success": False, "platform": "intigriti", "error": resp.text}
        except Exception as e:
            return {"success": False, "platform": "intigriti", "error": str(e)}


# ── Forge Submission (GitHub/GitLab PRs) ─────────────────────────


class ForgeSubmissionClient:
    """Submit code fixes via GitHub/GitLab APIs."""

    async def create_github_pr(
        self,
        repo: str,
        title: str,
        body: str,
        branch: str = "fix/auto-fix",
        base_branch: str = "main",
        token: str = "",
    ) -> dict[str, Any]:
        """Create a pull request on GitHub."""
        try:
            import httpx

            if not token:
                token = os.getenv("GITHUB_TOKEN", "")

            resp = httpx.post(
                f"https://api.github.com/repos/{repo}/pulls",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                json={
                    "title": title,
                    "body": body,
                    "head": branch,
                    "base": base_branch,
                },
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "success": True,
                    "platform": "github",
                    "external_id": data.get("number"),
                    "url": data.get("html_url", ""),
                }
            return {"success": False, "platform": "github", "error": resp.text}
        except Exception as e:
            return {"success": False, "platform": "github", "error": str(e)}

    async def create_gitlab_mr(
        self,
        project: str,
        title: str,
        description: str,
        source_branch: str = "fix/auto-fix",
        target_branch: str = "main",
        token: str = "",
    ) -> dict[str, Any]:
        """Create a merge request on GitLab."""
        try:
            import httpx

            resp = httpx.post(
                f"https://gitlab.com/api/v4/projects/{project.replace('/', '%2F')}/merge_requests",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "title": title,
                    "description": description,
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                },
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "success": True,
                    "platform": "gitlab",
                    "external_id": data.get("iid"),
                    "url": data.get("web_url", ""),
                }
            return {"success": False, "platform": "gitlab", "error": resp.text}
        except Exception as e:
            return {"success": False, "platform": "gitlab", "error": str(e)}

    async def submit_gitcoin_bounty(
        self,
        bounty_url: str,
        pr_url: str,
        description: str,
        token: str = "",
    ) -> dict[str, Any]:
        """Submit work to a Gitcoin bounty."""
        return {
            "success": True,
            "platform": "gitcoin",
            "bounty_url": bounty_url,
            "pr_url": pr_url,
            "note": "Gitcoin requires manual claim after PR merge",
        }


# ── Freelancer Submission ────────────────────────────────────────


class FreelancerSubmissionClient:
    """Submit proposals to Freelancer.com."""

    async def submit_proposal(
        self,
        project_id: int,
        proposal_text: str,
        bid_amount: float,
        delivery_days: int,
        api_key: str = "",
    ) -> dict[str, Any]:
        """Submit a proposal to a Freelancer project."""
        try:
            import httpx

            resp = httpx.post(
                "https://www.freelancer.com/api/projects/0.1/bids/",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "project_id": project_id,
                    "bidder_id": 0,
                    "amount": bid_amount,
                    "period": delivery_days,
                    "description": proposal_text,
                },
                timeout=30,
            )
            if resp.status_code in (200, 201):
                return {
                    "success": True,
                    "platform": "freelancer",
                    "project_id": project_id,
                }
            return {"success": False, "platform": "freelancer", "error": resp.text}
        except Exception as e:
            return {"success": False, "platform": "freelancer", "error": str(e)}


# ── Generic Form Submission (Browser Automation) ────────────────


class FormSubmissionClient:
    """Fill and submit web forms via browser automation."""

    async def submit_form_via_playwright(
        self,
        url: str,
        form_data: dict[str, str],
        submit_button_selector: str = "button[type='submit']",
    ) -> dict[str, Any]:
        """Submit a form using Playwright browser automation."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url)

                for field, value in form_data.items():
                    try:
                        await page.fill(f"[name='{field}']", value)
                    except Exception:
                        pass

                await page.click(submit_button_selector)
                await page.wait_for_load_state("networkidle")

                result = {
                    "success": True,
                    "url": url,
                    "title": await page.title(),
                }
                await browser.close()
                return result
        except ImportError:
            return {"success": False, "error": "Playwright not installed. Run: pip install playwright"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def submit_form_via_webview(
        self,
        url: str,
        form_data: dict[str, str],
    ) -> dict[str, Any]:
        """Submit a form using pywebview (for desktop app)."""
        try:

            # This would run in the desktop app context
            return {
                "success": True,
                "url": url,
                "note": "Form submission via webview requires user interaction",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ── Submission Tracker ───────────────────────────────────────────


class SubmissionTracker:
    """Track all submissions and their status."""

    def __init__(self) -> None:
        self._submissions: list[dict[str, Any]] = []

    def record_submission(self, submission: dict[str, Any]) -> None:
        """Record a submission attempt."""
        submission["recorded_at"] = datetime.now(UTC).isoformat()
        self._submissions.append(submission)
        status = "✅" if submission.get("success") else "❌"
        logger.info(
            "[SUBMISSION] %s %s/%s %s",
            status,
            submission.get("platform", "?"),
            submission.get("external_id", "?"),
            submission.get("error", ""),
        )

    def get_submissions(
        self,
        platform: str | None = None,
        success: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Get submissions with optional filters."""
        results = self._submissions
        if platform:
            results = [s for s in results if s.get("platform") == platform]
        if success is not None:
            results = [s for s in results if s.get("success") == success]
        return results

    def get_stats(self) -> dict[str, Any]:
        """Get submission statistics."""
        total = len(self._submissions)
        successful = sum(1 for s in self._submissions if s.get("success"))
        by_platform: dict[str, int] = {}
        for s in self._submissions:
            p = s.get("platform", "unknown")
            by_platform[p] = by_platform.get(p, 0) + 1

        return {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": round(successful / max(total, 1) * 100, 1),
            "by_platform": by_platform,
        }


# ── Main Orchestrator ───────────────────────────────────────────

import os


class AutoSubmissionEngine:
    """Main entry point — coordinates all submission clients."""

    def __init__(self) -> None:
        self._bb = BBSubmissionClient()
        self._forge = ForgeSubmissionClient()
        self._freelancer = FreelancerSubmissionClient()
        self._form = FormSubmissionClient()
        self._tracker = SubmissionTracker()

    @property
    def tracker(self) -> SubmissionTracker:
        return self._tracker

    async def submit_bug_bounty(
        self,
        platform: str,
        title: str,
        description: str,
        severity: str,
        api_key: str = "",
        program: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Submit a bug bounty report to the specified platform."""
        platform = platform.lower()
        if platform == "hackerone":
            result = await self._bb.submit_hackerone(title, description, severity, api_key=api_key, program=program)
        elif platform == "bugcrowd":
            result = await self._bb.submit_bugcrowd(title, description, severity, api_key=api_key, program=program)
        elif platform == "immunefi":
            result = await self._bb.submit_immunefi(title, description, severity, api_key=api_key, program=program)
        elif platform == "intigriti":
            result = await self._bb.submit_intigriti(title, description, severity, api_key=api_key, program=program)
        else:
            result = {"success": False, "error": f"Unsupported platform: {platform}"}

        self._tracker.record_submission(result)
        return result

    async def submit_forge_fix(
        self,
        platform: str,
        repo: str,
        title: str,
        body: str,
        token: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Submit a code fix to a dev bounty platform."""
        platform = platform.lower()
        if platform == "github":
            result = await self._forge.create_github_pr(repo, title, body, token=token)
        elif platform == "gitlab":
            result = await self._forge.create_gitlab_mr(repo, title, body, token=token)
        elif platform == "gitcoin":
            result = await self._forge.submit_gitcoin_bounty(repo, title, body, token=token)
        else:
            result = {"success": False, "error": f"Unsupported platform: {platform}"}

        self._tracker.record_submission(result)
        return result

    async def submit_freelancer_proposal(
        self,
        project_id: int,
        proposal_text: str,
        bid_amount: float,
        delivery_days: int,
        api_key: str = "",
    ) -> dict[str, Any]:
        """Submit a proposal to Freelancer.com."""
        result = await self._freelancer.submit_proposal(project_id, proposal_text, bid_amount, delivery_days, api_key)
        self._tracker.record_submission(result)
        return result

    async def submit_form(
        self,
        url: str,
        form_data: dict[str, str],
        method: str = "playwright",
    ) -> dict[str, Any]:
        """Submit a generic web form."""
        if method == "playwright":
            result = await self._form.submit_form_via_playwright(url, form_data)
        else:
            result = await self._form.submit_form_via_webview(url, form_data)

        self._tracker.record_submission(result)
        return result


_engine: AutoSubmissionEngine | None = None


def get_submission_engine() -> AutoSubmissionEngine:
    """Get singleton AutoSubmissionEngine."""
    global _engine
    if _engine is None:
        _engine = AutoSubmissionEngine()
    return _engine
