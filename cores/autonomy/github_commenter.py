"""GitHub Issue Commenter — bounty claim mechanics via slash-commands.

Algora and Opire award bounties through GitHub comments, not REST claims:
  - Algora: ``/attempt`` comment on the bounty issue.
  - Opire:  ``/try`` comment on the bounty issue; ``/claim #N`` in the PR body.

This module posts those comments with the user's GITHUB_TOKEN. Without a
token every method returns a failed result (never raises).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("ownex.autonomy.github_commenter")

_GITHUB_API = "https://api.github.com"

# Slash-command de reclamo por plataforma (Zero Magic: tabla explícita).
_CLAIM_COMMANDS: dict[str, str] = {
    "algora": "/attempt",
    "opire": "/try",
}


@dataclass
class CommentResult:
    success: bool
    comment_url: str | None = None
    error: str | None = None


class GitHubCommenter:
    """Posts bounty-claim comments to GitHub issues."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.token = os.environ.get("GITHUB_TOKEN") or self.config.get("github_token", "")
        self._timeout = self.config.get("timeout_s", 20)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def post_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> CommentResult:
        """POST /repos/{owner}/{repo}/issues/{issue_number}/comments."""
        if not self.token:
            return CommentResult(success=False, error="GITHUB_TOKEN not configured")
        if not body.strip():
            return CommentResult(success=False, error="Comment body cannot be empty")

        try:
            url = f"{_GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/comments"
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json={"body": body}, headers=self._headers())
            if resp.status_code in (200, 201):
                data = resp.json()
                return CommentResult(success=True, comment_url=data.get("html_url"))
            return CommentResult(
                success=False,
                error=f"GitHub API {resp.status_code}: {resp.text[:200]}",
            )
        except Exception as exc:
            logger.warning("[GitHubCommenter] post error: %s", exc)
            return CommentResult(success=False, error=str(exc))

    async def claim_bounty(
        self,
        platform: str,
        owner: str,
        repo: str,
        issue_number: int,
    ) -> CommentResult:
        """Post the platform-specific slash-command that claims a bounty.

        Returns a failed result for platforms without a known claim command.
        """
        command = _CLAIM_COMMANDS.get(platform.lower())
        if command is None:
            supported = ", ".join(sorted(_CLAIM_COMMANDS))
            return CommentResult(
                success=False,
                error=f"Unknown claim command for '{platform}'. Supported: {supported}",
            )
        return await self.post_issue_comment(owner, repo, issue_number, command)

    @staticmethod
    def pr_body_with_claim(pr_body: str, issue_number: int) -> str:
        """Append the Opire-style ``/claim #N`` reference to a PR body."""
        line = f"/claim #{issue_number}"
        if line in pr_body:
            return pr_body
        sep = "" if pr_body.endswith("\n") else "\n"
        return f"{pr_body}{sep}\n{line}"
