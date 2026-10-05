"""Algora.io Real Executor — Claim → PR → Merge → Auto-Payout.

Zero-barrier: GitHub login → claim issue → create PR → automatic payment on merge.
No interview, no portfolio, no CV required. Merge = payment.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("ownex.executors.algora")


@dataclass
class AlgoraConfig:
    """Algora executor configuration."""

    github_token: str
    algora_api_key: str | None = None
    base_url: str = "https://api.algora.io"
    work_dir: Path = Path("~/ownex/work/algora").expanduser()
    claim_timeout_seconds: int = 30
    pr_timeout_seconds: int = 300


@dataclass
class ClaimResult:
    """Result of claiming an issue."""

    success: bool
    claim_id: str | None = None
    issue_url: str | None = None
    repo_url: str | None = None
    error: str | None = None


@dataclass
class PRResult:
    """Result of creating a PR."""

    success: bool
    pr_url: str | None = None
    pr_number: int | None = None
    branch_name: str | None = None
    error: str | None = None


class AlgoraExecutor:
    """Executes Algora bounties end-to-end: claim → code → PR → merge → payout."""

    def __init__(self, config: AlgoraConfig):
        self.config = config
        self.config.work_dir.mkdir(parents=True, exist_ok=True)
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Authorization": f"Bearer {self.config.github_token}"}
            if self.config.algora_api_key:
                headers["X-Algora-Key"] = self.config.algora_api_key
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _notify(self, event_type: str, **payload: Any) -> None:
        """Publish a user-facing outcome. Never raises: bounty must survive."""
        try:
            from cores.notifications.emit import emit

            emit(event_type, **payload)
        except Exception as exc:
            logger.debug("emit(%s) skipped: %s", event_type, exc)

    async def claim_issue(self, issue_url: str) -> ClaimResult:
        """Claim an Algora issue via API."""
        try:
            # Extract owner/repo/issue from URL
            # https://algora.io/issues/owner/repo/123
            match = re.search(r"algora\.io/issues/([^/]+)/([^/]+)(?:/(\d+))?", issue_url)
            if not match:
                return ClaimResult(success=False, error="Invalid Algora issue URL format")

            owner, repo, issue_num = match.groups()
            issue_id = issue_num or "1"  # fallback

            # Call Algora API to claim
            resp = await self.client.post(
                f"/issues/{owner}/{repo}/{issue_id}/claim",
                json={"github_token": self.config.github_token},
                timeout=self.config.claim_timeout_seconds,
            )

            if resp.status_code == 200:
                data = resp.json()
                return ClaimResult(
                    success=True,
                    claim_id=data.get("claim_id"),
                    issue_url=issue_url,
                    repo_url=f"https://github.com/{owner}/{repo}",
                )
            elif resp.status_code == 409:
                return ClaimResult(success=False, error="Issue already claimed")
            else:
                return ClaimResult(success=False, error=f"Claim failed: {resp.status_code} - {resp.text}")

        except Exception as exc:
            logger.exception("Algora claim failed")
            return ClaimResult(success=False, error=str(exc))

    async def clone_repo(self, repo_url: str, branch_name: str) -> Path:
        """Clone repository and create working branch."""
        repo_path = self.config.work_dir / f"algora-{uuid.uuid4().hex[:8]}"
        repo_path.parent.mkdir(parents=True, exist_ok=True)

        # Clone with depth=1 for speed
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr}")

        # Create working branch
        result = subprocess.run(
            ["git", "-C", str(repo_path), "checkout", "-b", branch_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git checkout failed: {result.stderr}")

        # Configure git user
        subprocess.run(["git", "-C", str(repo_path), "config", "user.name", "OWNEX Bot"], check=False)
        subprocess.run(["git", "-C", str(repo_path), "config", "user.email", "ownex@bot.local"], check=False)

        return repo_path

    async def create_pr(
        self,
        repo_path: Path,
        issue_url: str,
        commit_message: str,
        approval_token: str | None = None,
        require_approval: bool = True,
    ) -> PRResult:
        """Create a PR for the claimed issue.

        Abrir un PR es una acción externa e irreversible bajo el nombre del
        usuario, así que exige un token de aprobación de un solo uso, igual que
        `PRBuilder.create_pr` (spec §23/§48/§79: NO HUMAN GATE -> NO IRREVERSIBLE
        EXTERNAL ACTION). Antes empujeaba la rama y creaba el PR sin gate.
        """
        if require_approval:
            from cores.automation.safety import consume_approval

            if not consume_approval(approval_token, "coder:create_pr", str(repo_path)):
                return PRResult(
                    success=False,
                    error=(
                        "Requires human approval: PR push/open. Emití un token de "
                        "aprobación después de revisar el diff."
                    ),
                )
        try:
            branch_res = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
            )
            branch_name = branch_res.stdout.strip() if branch_res.returncode == 0 else ""
            if not branch_name:
                return PRResult(success=False, error="Could not determine current branch")
            # Push branch
            result = subprocess.run(
                ["git", "-C", str(repo_path), "push", "-u", "origin", "HEAD"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return PRResult(success=False, error=f"Git push failed: {result.stderr}")

            # Create PR via GitHub API
            # Extract owner/repo from repo_path
            remote_result = subprocess.run(
                ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
            )
            if remote_result.returncode != 0:
                return PRResult(success=False, error="Could not get remote URL")

            remote_url = remote_result.stdout.strip()
            # Parse github.com/owner/repo.git
            match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", remote_url)
            if not match:
                return PRResult(success=False, error="Could not parse GitHub repo from remote")

            owner, repo = match.groups()

            pr_data = {
                "title": commit_message,
                "head": branch_name,
                "base": "main",  # default branch
                "body": f"Fixes issue: {issue_url}\n\nSubmitted via OWNEX Algora Executor.",
            }

            resp = await self.client.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                json=pr_data,
                headers={"Authorization": f"Bearer {self.config.github_token}"},
                timeout=30.0,
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                return PRResult(
                    success=True,
                    pr_url=data.get("html_url"),
                    pr_number=data.get("number"),
                    branch_name=branch_name,
                )
            else:
                return PRResult(success=False, error=f"PR creation failed: {resp.status_code} - {resp.text}")

        except Exception as exc:
            logger.exception("PR creation failed")
            return PRResult(success=False, error=str(exc))

    async def execute_bounty(
        self,
        issue_url: str,
        code_changes: dict[str, str],  # file_path -> new_content
        commit_message: str,
        approval_token: str | None = None,
        require_approval: bool = True,
    ) -> dict[str, Any]:
        """Execute full bounty: claim → apply changes → PR → await merge → payout.

        `approval_token`/`require_approval` se propagan al PR: sin token el
        bounty se detiene en la etapa `pr` SIN crear nada externo (fail-closed).
        """
        execution_id = f"algora-{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(UTC).isoformat()

        logger.info(f"[{execution_id}] Starting Algora bounty execution for {issue_url}")

        # 1. Claim the issue
        claim = await self.claim_issue(issue_url)
        if not claim.success:
            logger.error(f"[{execution_id}] Claim failed: {claim.error}")
            self._notify(
                "devbounty:claim_failed",
                id=execution_id,
                message=f"No se pudo reclamar {issue_url}: {claim.error}",
            )
            return {"success": False, "stage": "claim", "error": claim.error}

        logger.info(f"[{execution_id}] Issue claimed: {claim.claim_id}")
        self._notify(
            "devbounty:claimed",
            id=execution_id,
            message=f"Bounty reclamado: {issue_url} (claim {claim.claim_id})",
        )

        # 2. Clone repo
        repo_url = claim.repo_url or issue_url.replace("/issues/", "/")
        branch_name = f"ownex/algora-{claim.claim_id or uuid.uuid4().hex[:8]}"
        try:
            repo_path = await self.clone_repo(repo_url, branch_name)
        except Exception as exc:
            return {"success": False, "stage": "clone", "error": str(exc)}

        # 3. Apply code changes
        try:
            for file_path, content in code_changes.items():
                full_path = repo_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")

            # Commit changes
            subprocess.run(["git", "-C", str(repo_path), "add", "-A"], check=True)
            subprocess.run(
                ["git", "-C", str(repo_path), "commit", "-m", commit_message],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception as exc:
            return {"success": False, "stage": "code", "error": str(exc)}

        # 4. Create PR
        pr = await self.create_pr(
            repo_path, issue_url, commit_message, approval_token=approval_token, require_approval=require_approval
        )
        if not pr.success:
            return {"success": False, "stage": "pr", "error": pr.error}

        logger.info(f"[{execution_id}] PR created: {pr.pr_url}")
        self._notify(
            "devbounty:pr_created",
            id=execution_id,
            message=f"PR abierto para {issue_url}: {pr.pr_url}",
        )

        if not pr.pr_url:
            return {"success": False, "stage": "pr", "error": "PR created but no URL returned"}

        # 5. Poll for merge (Algora pays on merge)
        merged = await self._poll_for_merge(pr.pr_url)

        completed_at = datetime.now(UTC).isoformat()

        if merged:
            logger.info(f"[{execution_id}] PR merged! Payout triggered automatically.")
            self._notify(
                "devbounty:merged_paid",
                id=execution_id,
                message=f"Bounty mergeado y pagado: {issue_url} ({pr.pr_url})",
            )
            return {
                "success": True,
                "execution_id": execution_id,
                "claim_id": claim.claim_id,
                "issue_url": issue_url,
                "pr_url": pr.pr_url,
                "pr_number": pr.pr_number,
                "merged": True,
                "started_at": started_at,
                "completed_at": completed_at,
                "payout_expected": True,
                "payout_note": "Algora pays automatically on merge",
            }
        else:
            logger.warning(f"[{execution_id}] PR not merged within timeout")
            self._notify(
                "devbounty:merge_pending",
                id=execution_id,
                message=f"PR sin mergear (timeout): {pr.pr_url}",
            )
            return {
                "success": False,
                "execution_id": execution_id,
                "stage": "merge",
                "pr_url": pr.pr_url,
                "error": "PR not merged within timeout",
            }

    async def _poll_for_merge(self, pr_url: str, max_wait_seconds: int = 3600) -> bool:
        """Poll PR for merge status."""
        # Extract owner/repo/pr_number from URL
        match = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
        if not match:
            return False

        owner, repo, pr_number = match.groups()
        poll_interval = 30
        max_polls = max_wait_seconds // poll_interval

        for _ in range(max_polls):
            await asyncio.sleep(poll_interval)
            try:
                resp = await self.client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
                    headers={"Authorization": f"Bearer {self.config.github_token}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("merged"):
                        return True
                    if data.get("state") == "closed" and not data.get("merged"):
                        return False  # Closed without merge
            except Exception:
                pass

        return False


async def execute_algora_bounty(
    issue_url: str,
    code_changes: dict[str, str],
    commit_message: str,
    github_token: str,
    algora_api_key: str | None = None,
) -> dict[str, Any]:
    """Convenience function for single bounty execution."""
    config = AlgoraConfig(
        github_token=github_token,
        algora_api_key=algora_api_key,
    )
    executor = AlgoraExecutor(config)
    try:
        return await executor.execute_bounty(issue_url, code_changes, commit_message)
    finally:
        await executor.close()


# Backward compatibility with AutoSubmitEngine adapter interface
class AlgoraDweAdapter:
    """Adapter interface for AutoSubmitEngine."""

    def __init__(self, github_token: str | None = None, algora_api_key: str | None = None):
        self.config = AlgoraConfig(
            github_token=github_token or os.environ.get("GITHUB_TOKEN", ""),
            algora_api_key=algora_api_key,
        )
        self.executor = AlgoraExecutor(self.config)

    async def submit_work(self, prepared_work: Any, api_key: str) -> dict[str, Any]:
        """Submit work via Algora (claim → PR → merge)."""
        opportunity = prepared_work.metadata.get("opportunity", {})
        issue_url = opportunity.get("url") or opportunity.get("issue_url")
        if not issue_url:
            return {"success": False, "error": "No issue_url in opportunity"}

        code_changes = prepared_work.files or {}
        commit_message = prepared_work.metadata.get("commit_message", "Fix: resolve issue")

        result = await self.executor.execute_bounty(issue_url, code_changes, commit_message)
        await self.executor.close()
        return result


def build_algora_executor(
    github_token: str | None = None,
    algora_api_key: str | None = None,
) -> AlgoraExecutor:
    """Build Algora executor with credentials from vault or env.

    Resolution order (first hit wins):
    1. explicit ``github_token`` param
    2. ``GITHUB_TOKEN`` env var
    3. credentials vault (``~/.config/ownex/opportunity.env`` via ``get_credentials``)
    4. IdentityVault ``platform_algora`` token
    """
    github_token = github_token or os.environ.get("GITHUB_TOKEN")
    if not github_token:
        # Credentials vault (~/.config/ownex/opportunity.env) — same source
        # the setup checklist detector reads, so a configured token always works.
        try:
            from cores.credentials import vault as _creds_vault

            github_token = _creds_vault.get_credentials(force_refresh=True).github_token or None
        except Exception:
            pass
    if not github_token:
        # Try IdentityVault
        try:
            from cores.identity_vault import IdentityVault

            vault = IdentityVault()
            creds = vault.get_credentials("platform_algora")
            if creds and creds.get("token"):
                github_token = creds["token"]
        except Exception:
            pass

    if not github_token:
        raise ValueError("GitHub token required for Algora executor")

    return AlgoraExecutor(AlgoraConfig(github_token=github_token, algora_api_key=algora_api_key))
