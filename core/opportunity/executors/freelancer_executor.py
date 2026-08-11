"""Freelancer Executor — Autonomous bid, deliver, and manage projects on Freelancer.com."""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class FreelancerExecutor(BaseExecutor):
    """Executor for Freelancer.com — bid on projects, submit deliverables, manage milestones."""

    platform = "freelancer"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.api_token = self.config.get("api_token") or os.getenv("FREELANCER_API_TOKEN")
        self.user_id = self.config.get("user_id") or os.getenv("FREELANCER_USER_ID")
        self.base_url = "https://www.freelancer.com/api"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "freelancer-oauth-v1": self.api_token or "",
        }

    async def execute(self, action: str, **kwargs) -> ExecutionResult:
        if action == "bid_on_project":
            return await self.bid_on_project(
                kwargs.get("project_id"),
                kwargs.get("bid_amount"),
                kwargs.get("period"),
                kwargs.get("description"),
                kwargs.get("milestone_percentage"),
            )
        if action == "submit_deliverable":
            return await self.submit_deliverable(
                kwargs.get("project_id"),
                kwargs.get("files"),
                kwargs.get("message"),
            )
        if action == "request_milestone_release":
            return await self.request_milestone_release(
                kwargs.get("project_id"),
                kwargs.get("milestone_id"),
            )
        if action == "get_project":
            return await self.get_project(kwargs.get("project_id"))
        if action == "list_my_bids":
            return await self.list_my_bids(kwargs.get("status"))
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def bid_on_project(
        self,
        project_id: int | str,
        bid_amount: float,
        period: int,
        description: str,
        milestone_percentage: float = 100.0,
    ) -> ExecutionResult:
        """Place a bid on a project."""
        if not self.api_token:
            return ExecutionResult(
                False, "bid_on_project", str(project_id), error="FREELANCER_API_TOKEN not configured"
            )

        project_id_str = str(project_id)
        payload = {
            "project_id": project_id_str,
            "bidder_id": self.user_id,
            "amount": bid_amount,
            "period": period,
            "description": description,
            "milestone_percentage": milestone_percentage,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/projects/{project_id_str}/bids",
                    headers=self._headers(),
                    json=payload,
                    timeout=30,
                )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(
                        True,
                        "bid_on_project",
                        project_id_str,
                        f"Bid ${bid_amount} placed on project {project_id_str}",
                        data={"bid_id": data.get("bid_id"), "status": data.get("status")},
                    )
                else:
                    return ExecutionResult(
                        False, "bid_on_project", project_id_str, error=f"API {resp.status_code}: {resp.text}"
                    )
        except Exception as e:
            return ExecutionResult(False, "bid_on_project", project_id_str, error=str(e))

    async def submit_deliverable(
        self,
        project_id: int | str,
        files: list[dict[str, str]] | None = None,
        message: str = "Deliverable submitted for review.",
    ) -> ExecutionResult:
        """Submit deliverable files for a project."""
        if not self.api_token:
            return ExecutionResult(
                False, "submit_deliverable", str(project_id), error="FREELANCER_API_TOKEN not configured"
            )

        project_id_str = str(project_id)
        payload = {"project_id": project_id_str, "message": message, "files": files or []}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/projects/{project_id_str}/deliverables",
                    headers=self._headers(),
                    json=payload,
                    timeout=60,
                )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(
                        True,
                        "submit_deliverable",
                        project_id_str,
                        f"Deliverable submitted for project {project_id_str}",
                        data={"deliverable_id": data.get("deliverable_id")},
                    )
                else:
                    return ExecutionResult(
                        False, "submit_deliverable", project_id_str, error=f"API {resp.status_code}: {resp.text}"
                    )
        except Exception as e:
            return ExecutionResult(False, "submit_deliverable", project_id_str, error=str(e))

    async def request_milestone_release(
        self,
        project_id: int | str,
        milestone_id: int | str,
    ) -> ExecutionResult:
        """Request release of a milestone payment."""
        if not self.api_token:
            return ExecutionResult(
                False, "request_milestone_release", str(project_id), error="FREELANCER_API_TOKEN not configured"
            )

        project_id_str = str(project_id)
        milestone_id_str = str(milestone_id)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/projects/{project_id_str}/milestones/{milestone_id_str}/release",
                    headers=self._headers(),
                    json={},
                    timeout=30,
                )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(
                        True,
                        "request_milestone_release",
                        project_id_str,
                        f"Milestone {milestone_id_str} release requested",
                        data=data,
                    )
                else:
                    return ExecutionResult(
                        False, "request_milestone_release", project_id_str, error=f"API {resp.status_code}: {resp.text}"
                    )
        except Exception as e:
            return ExecutionResult(False, "request_milestone_release", project_id_str, error=str(e))

    async def get_project(self, project_id: int | str) -> ExecutionResult:
        """Get project details."""
        if not self.api_token:
            return ExecutionResult(False, "get_project", str(project_id), error="FREELANCER_API_TOKEN not configured")

        project_id_str = str(project_id)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/projects/{project_id_str}",
                    headers=self._headers(),
                    timeout=15,
                )

                if resp.status_code == 200:
                    return ExecutionResult(True, "get_project", project_id_str, "Project fetched", data=resp.json())
                else:
                    return ExecutionResult(
                        False, "get_project", project_id_str, error=f"API {resp.status_code}: {resp.text}"
                    )
        except Exception as e:
            return ExecutionResult(False, "get_project", project_id_str, error=str(e))

    async def list_my_bids(self, status: str | None = None) -> ExecutionResult:
        """List my bids with optional status filter."""
        if not self.api_token:
            return ExecutionResult(False, "list_my_bids", "self", error="FREELANCER_API_TOKEN not configured")

        params = {}
        if status:
            params["status"] = status

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/users/self/bids",
                    headers=self._headers(),
                    params=params,
                    timeout=15,
                )

                if resp.status_code == 200:
                    return ExecutionResult(True, "list_my_bids", "self", "Bids fetched", data=resp.json())
                else:
                    return ExecutionResult(False, "list_my_bids", "self", error=f"API {resp.status_code}: {resp.text}")
        except Exception as e:
            return ExecutionResult(False, "list_my_bids", "self", error=str(e))
