"""Auto-Submission Engine — Real delivery to platforms via API.

Closes the loop: WorkBank prepares → AutoSubmitEngine delivers → RevenueTracker records.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from core.opportunity.executors.assisted_mode import AssistedExecutor, PreparedWork
from cores.identity_vault import IdentityVault

logger = logging.getLogger("ownex.opportunity.auto_submit")


# Lazy imports to avoid circular deps
def _get_hackerone():
    from cores.platforms.hackerone import HackerOne

    return HackerOne()


def _get_bugcrowd():
    from cores.platforms.bugcrowd import Bugcrowd

    return Bugcrowd()


def _get_intigriti():
    from cores.platforms.intigriti import Intigriti

    return Intigriti()


def _get_yeswehack():
    from cores.platforms.yeswehack import YesWeHack

    return YesWeHack()


def _get_opire_adapter():
    from cores.opportunity.adapters.opire import OpireAdapter

    return OpireAdapter()


def _get_issuehunt_adapter():
    from cores.opportunity.adapters.issuehunt import IssueHuntAdapter

    return IssueHuntAdapter()


def _get_freelancer_adapter():
    from cores.opportunity.adapters.freelancer import FreelancerAdapter

    return FreelancerAdapter()


def _get_algora_adapter():
    from api.adapters.direct_work_algora import AlgoraDweAdapter

    return AlgoraDweAdapter()


class SubmissionStatus(StrEnum):
    PENDING = "pending"
    PREPARING = "preparing"
    READY = "ready"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DLQ = "dlq"  # Dead Letter Queue - requires manual intervention


@dataclass
class SubmissionRecord:
    """Single submission attempt with full traceability."""

    id: str
    platform: str
    opportunity_id: str
    opportunity_title: str
    idempotency_key: str
    status: SubmissionStatus
    prepared_work: PreparedWork | None = None
    submission_result: dict[str, Any] | None = None
    attempts: int = 0
    max_attempts: int = 3
    last_error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    submitted_at: str | None = None
    confirmed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "opportunity_id": self.opportunity_id,
            "opportunity_title": self.opportunity_title,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "submitted_at": self.submitted_at,
            "confirmed_at": self.confirmed_at,
            "metadata": self.metadata,
        }


class AutoSubmitEngine:
    """Orchestrates real API submissions to all supported platforms."""

    def __init__(
        self,
        vault: IdentityVault | None = None,
        dlq_path: str | Path | None = None,
        queue_path: str | Path | None = None,
    ):
        self.vault = vault or IdentityVault()
        data_base = Path(os.environ.get("OWNEX_DATA_DIR", Path.home() / "ownex"))
        self.dlq_path = Path(dlq_path).expanduser() if dlq_path else data_base / "submissions" / "dlq"
        self.dlq_path.mkdir(parents=True, exist_ok=True)
        self._queue_path: Path = (
            Path(queue_path).expanduser() if queue_path else data_base / "submissions" / "submission_queue.json"
        )

        # Platform instances (lazy-loaded with credentials)
        self._platforms: dict[str, Any] = {}
        self._adapters: dict[str, Any] = {}

        # Submission queue (persisted)
        self._submissions: dict[str, SubmissionRecord] = {}
        self._load_queue()

        # Retry config
        self.base_retry_delay = 30  # seconds
        self.max_retry_delay = 3600  # 1 hour

    def _get_platform(self, platform_key: str) -> Any:
        """Lazy-load platform instance with credentials from vault."""
        if platform_key in self._platforms:
            return self._platforms[platform_key]

        platform_map = {
            "hackerone": _get_hackerone(),
            "bugcrowd": _get_bugcrowd(),
            "intigriti": _get_intigriti(),
            "yeswehack": _get_yeswehack(),
        }

        if platform_key not in platform_map:
            raise ValueError(f"Unsupported platform for auto-submit: {platform_key}")

        platform = platform_map[platform_key]
        self._platforms[platform_key] = platform
        return platform

    def _get_adapter(self, platform_key: str) -> Any:
        """Lazy-load opportunity adapter for dev bounty platforms."""
        if platform_key in self._adapters:
            return self._adapters[platform_key]

        adapter_map = {
            "opire": _get_opire_adapter(),
            "issuehunt": _get_issuehunt_adapter(),
            "freelancer": _get_freelancer_adapter(),
            "algora": _get_algora_adapter(),
        }

        if platform_key not in adapter_map:
            raise ValueError(f"Unsupported adapter for auto-submit: {platform_key}")

        adapter = adapter_map[platform_key]
        self._adapters[platform_key] = adapter
        return adapter

    def _get_api_key(self, platform: str) -> str | None:
        """Retrieve API key from IdentityVault."""
        try:
            # Try platform-specific key first
            creds = self.vault.get_credentials(f"platform_{platform}")
            if creds and creds.get("token"):
                return creds["token"]
            # Fallback to generic platform name
            creds = self.vault.get_credentials(platform)
            if creds and creds.get("token"):
                return creds["token"]
            # Try common variations
            for prefix in ("", "platform_"):
                creds = self.vault.get_credentials(f"{prefix}{platform}_api_key")
                if creds and creds.get("token"):
                    return creds["token"]
                creds = self.vault.get_credentials(f"{prefix}{platform}_api")
                if creds and creds.get("token"):
                    return creds["token"]
        except Exception:
            return None
        return None

    async def submit_workbank_item(
        self, item_id: str, platform: str, opportunity: dict[str, Any], force: bool = False
    ) -> SubmissionRecord:
        """Submit a WorkBank item to its platform via API.

        Args:
            item_id: WorkBank item ID
            platform: Platform key (hackerone, bugcrowd, opire, etc.)
            opportunity: Full opportunity data
            force: Re-submit even if already submitted/confirmed

        Returns:
            SubmissionRecord with current status
        """
        # Generate idempotency key
        idempotency_key = f"{platform}:{item_id}:{uuid.uuid4().hex[:8]}"

        # Check for existing submission
        existing = self._find_submission(item_id, platform)
        if existing and existing.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.CONFIRMED) and not force:
            logger.info(f"Submission already exists for {item_id} on {platform}: {existing.id}")
            return existing

        # Create new submission record
        record = SubmissionRecord(
            id=idempotency_key,
            platform=platform,
            opportunity_id=item_id,
            opportunity_title=opportunity.get("title", "Unknown"),
            idempotency_key=idempotency_key,
            status=SubmissionStatus.PENDING,
            metadata={"opportunity": opportunity},
        )
        self._submissions[record.id] = record
        self._save_queue()

        # Execute submission with retries
        return await self._execute_submission(record, opportunity)

    async def _execute_submission(self, record: SubmissionRecord, opportunity: dict[str, Any]) -> SubmissionRecord:
        """Execute the submission with retry logic."""
        platform = record.platform

        while record.attempts < record.max_attempts:
            record.attempts += 1
            record.status = SubmissionStatus.SUBMITTING
            record.updated_at = datetime.now(UTC).isoformat()
            self._save_queue()

            try:
                logger.info(f"Submitting {record.opportunity_id} to {platform} (attempt {record.attempts})")

                # Prepare the work using AssistedExecutor
                assisted = AssistedExecutor(base_executor=None)
                prepared = await assisted.prepare_work(opportunity)
                record.prepared_work = prepared

                # Save to disk for user review
                work_dir = await assisted.save_work_to_disk(prepared)
                record.metadata["package_path"] = str(work_dir)

                # Get API key
                api_key = self._get_api_key(platform)
                if not api_key:
                    raise ValueError(f"No API key configured for {platform}")

                # Execute platform-specific submission
                result = await self._submit_to_platform(platform, prepared, api_key)

                # If API submission failed, try Computer Use fallback
                if not result.get("success") and self._should_try_computer_use(platform):
                    logger.info(f"API submission failed for {platform}, trying Computer Use fallback")
                    result = await self._submit_via_computer_use(platform, prepared, record)

                record.submission_result = result
                record.status = SubmissionStatus.SUBMITTED
                record.submitted_at = datetime.now(UTC).isoformat()
                record.updated_at = datetime.now(UTC).isoformat()
                self._save_queue()

                if result.get("success"):
                    # Poll for confirmation
                    external_id = result.get("external_id")
                    if external_id:
                        confirmed = await self._poll_confirmation(platform, external_id, api_key)
                    else:
                        confirmed = False
                    if confirmed:
                        record.status = SubmissionStatus.CONFIRMED
                        record.confirmed_at = datetime.now(UTC).isoformat()
                        logger.info(f"Submission confirmed: {record.id}")
                    else:
                        record.status = SubmissionStatus.SUBMITTED  # Submitted, awaiting review
                    self._save_queue()
                    return record
                else:
                    record.last_error = result.get("error", "Unknown error")
                    logger.warning(f"Submission failed (attempt {record.attempts}): {record.last_error}")

            except Exception as exc:
                record.last_error = str(exc)
                logger.exception(f"Submission error for {record.id}: {exc}")

            # Exponential backoff
            if record.attempts < record.max_attempts:
                delay = min(self.base_retry_delay * (2 ** (record.attempts - 1)), self.max_retry_delay)
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)

        # All attempts exhausted -> DLQ
        record.status = SubmissionStatus.DLQ
        record.updated_at = datetime.now(UTC).isoformat()
        self._move_to_dlq(record)
        self._save_queue()
        logger.error(f"Submission moved to DLQ after {record.max_attempts} attempts: {record.id}")
        return record

    async def _submit_to_platform(self, platform: str, prepared: PreparedWork, api_key: str) -> dict[str, Any]:
        """Submit prepared work to specific platform."""
        platform_impl = self._get_platform(platform)

        # Convert PreparedWork to platform report format
        report_data = {
            "title": prepared.title,
            "vulnerability": prepared.metadata.get("opportunity", {}).get("description", ""),
            "program": prepared.metadata.get("opportunity", {}).get("program", ""),
            "severity": prepared.metadata.get("opportunity", {}).get("severity", "medium"),
            "content": prepared.files,
            "url": prepared.submission_url,
        }

        # For bug bounty platforms, use their submit method
        if hasattr(platform_impl, "submit"):
            result = platform_impl.submit(report_data, api_key)
            return {
                "success": result.success,
                "external_id": result.external_id,
                "url": result.url,
                "error": result.error,
                "data": result.data,
            }

        # For dev bounty platforms, use adapter
        adapter = self._get_adapter(platform)
        if hasattr(adapter, "submit_work"):
            return await adapter.submit_work(prepared, api_key)

        return {"success": False, "error": f"Platform {platform} does not support auto-submission"}

    async def _poll_confirmation(self, platform: str, external_id: str, api_key: str, max_polls: int = 10) -> bool:
        """Poll platform for submission confirmation."""
        platform_impl = self._get_platform(platform)

        for _i in range(max_polls):
            await asyncio.sleep(30)  # Wait 30s between polls
            try:
                status = platform_impl.check_status(external_id, api_key)
                if status in ("triaged", "resolved", "paid", "confirmed"):
                    return True
                if status in ("rejected", "duplicate", "informative"):
                    return False  # Final negative state
            except Exception:
                pass

        return False  # Timeout - still pending review

    def _should_try_computer_use(self, platform: str) -> bool:
        """Check if Computer Use fallback should be attempted."""
        try:
            from cores.computer_use.submission_executor import should_use_computer_use

            return should_use_computer_use(platform, api_submission_failed=True)
        except ImportError:
            return False

    async def _submit_via_computer_use(
        self, platform: str, prepared: PreparedWork, record: SubmissionRecord
    ) -> dict[str, Any]:
        """Submit via Computer Use (desktop form filling) as fallback."""
        try:
            from cores.computer_use.submission_executor import get_computer_use_executor

            executor = get_computer_use_executor()
            if not executor.can_handle(platform):
                return {"success": False, "error": f"Computer Use cannot handle {platform}"}

            work_data = {
                "title": prepared.title,
                "description": prepared.metadata.get("opportunity", {}).get("description", ""),
                "severity": prepared.metadata.get("opportunity", {}).get("severity", "medium"),
                "program": prepared.metadata.get("opportunity", {}).get("program", ""),
            }

            result = await executor.submit(
                platform=platform,
                work_data=work_data,
                work_item_id=record.opportunity_id,
                opportunity_title=record.opportunity_title,
            )

            return {
                "success": result.success,
                "method": "computer_use",
                "error": result.error,
                "duration_ms": result.duration_ms,
                "screenshots": result.screenshots,
            }
        except Exception as exc:
            logger.warning(f"Computer Use fallback failed for {platform}: {exc}")
            return {"success": False, "error": f"Computer Use fallback failed: {exc}"}

    def _find_submission(self, opportunity_id: str, platform: str) -> SubmissionRecord | None:
        """Find existing submission for opportunity/platform."""
        for record in self._submissions.values():
            if record.opportunity_id == opportunity_id and record.platform == platform:
                return record
        return None

    def get_submission(self, submission_id: str) -> SubmissionRecord | None:
        """Get submission by ID."""
        return self._submissions.get(submission_id)

    def list_submissions(
        self, status: SubmissionStatus | None = None, platform: str | None = None
    ) -> list[SubmissionRecord]:
        """List submissions with optional filters."""
        results = list(self._submissions.values())
        if status:
            results = [r for r in results if r.status == status]
        if platform:
            results = [r for r in results if r.platform == platform]
        return sorted(results, key=lambda r: r.created_at, reverse=True)

    def get_dlq(self) -> list[SubmissionRecord]:
        """Get all dead-letter queue items."""
        return self.list_submissions(status=SubmissionStatus.DLQ)

    async def retry_dlq(self, submission_id: str) -> SubmissionRecord | None:
        """Retry a DLQ item."""
        record = self._submissions.get(submission_id)
        if not record or record.status != SubmissionStatus.DLQ:
            return None
        record.status = SubmissionStatus.PENDING
        record.attempts = 0
        record.last_error = None
        record.updated_at = datetime.now(UTC).isoformat()
        self._save_queue()
        return await self._execute_submission(record, record.metadata.get("opportunity", {}))

    # Persistence
    def _save_queue(self) -> None:
        """Persist submission queue to disk."""
        queue_file = self._queue_path
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "updated_at": datetime.now(UTC).isoformat(),
            "submissions": {k: v.to_dict() for k, v in self._submissions.items()},
        }
        queue_file.write_text(json.dumps(data, indent=2))

    def _load_queue(self) -> None:
        """Load submission queue from disk."""
        queue_file = self._queue_path
        if not queue_file.exists():
            return
        try:
            data = json.loads(queue_file.read_text())
            for k, v in data.get("submissions", {}).items():
                v["status"] = SubmissionStatus(v["status"])
                if v.get("prepared_work"):
                    # Reconstruct PreparedWork (simplified)
                    pass
                self._submissions[k] = SubmissionRecord(**v)
        except Exception as exc:
            logger.warning(f"Could not load submission queue: {exc}")

    def _move_to_dlq(self, record: SubmissionRecord) -> None:
        """Move failed submission to DLQ file."""
        dlq_file = self.dlq_path / f"{record.id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        dlq_file.write_text(json.dumps(record.to_dict(), indent=2))
        logger.warning(f"Submission moved to DLQ: {dlq_file}")


# Global instance
_auto_submit_engine: AutoSubmitEngine | None = None


def get_auto_submit_engine() -> AutoSubmitEngine:
    global _auto_submit_engine
    if _auto_submit_engine is None:
        _auto_submit_engine = AutoSubmitEngine()
    return _auto_submit_engine


# API entry point
async def auto_submit_workbank_item(
    item_id: str, platform: str, opportunity: dict[str, Any], force: bool = False
) -> dict[str, Any]:
    """Public API: submit a WorkBank item to its platform."""
    engine = get_auto_submit_engine()
    record = await engine.submit_workbank_item(item_id, platform, opportunity, force)
    return record.to_dict()
