"""Real-time Platform Webhooks — Instant earnings sync via webhooks.

Instead of polling every 30 minutes, platforms push events to OWNEX:
- Payout received
- Submission status changed (triaged, resolved, paid)
- New program published
- Bounty amount updated

Each platform has a dedicated webhook endpoint with signature verification.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response

from core.credentials.vault import OpportunityCredentials
from core.opportunity.executors.auto_submit import SubmissionStatus, get_auto_submit_engine
from cores.revenue_tracker.revenue_tracker import get_revenue_tracker

logger = logging.getLogger("ownex.platform_webhooks")

router = APIRouter(prefix="/webhook", tags=["platform-webhooks"])


@dataclass
class WebhookEvent:
    """Normalized webhook event from any platform."""

    platform: str
    event_type: str  # payout_received, submission_status, program_created, bounty_updated
    external_id: str
    timestamp: str
    payload: dict[str, Any]
    raw_headers: dict[str, str]


# Platform webhook configurations
PLATFORM_WEBHOOK_CONFIG = {
    "hackerone": {
        "secret_env": "HACKERONE_WEBHOOK_SECRET",
        "signature_header": "X-HackerOne-Signature",
        "events": {
            "bounty.awarded": "payout_received",
            "report.rewarded": "payout_received",
            "report.state_changed": "submission_status",
        },
    },
    "bugcrowd": {
        "secret_env": "BUGCROWD_WEBHOOK_SECRET",
        "signature_header": "X-Bugcrowd-Signature",
        "events": {
            "bounty.paid": "payout_received",
            "submission.state_changed": "submission_status",
        },
    },
    "intigriti": {
        "secret_env": "INTIGRITI_WEBHOOK_SECRET",
        "signature_header": "X-Intigriti-Signature",
        "events": {
            "bounty.paid": "payout_received",
            "submission.status_changed": "submission_status",
        },
    },
    "yeswehack": {
        "secret_env": "YESWEHACK_WEBHOOK_SECRET",
        "signature_header": "X-YesWeHack-Signature",
        "events": {
            "bounty.paid": "payout_received",
            "report.status_changed": "submission_status",
        },
    },
    "opire": {
        "secret_env": "OPIRE_WEBHOOK_SECRET",
        "signature_header": "X-Opire-Signature",
        "events": {
            "bounty.paid": "payout_received",
            "submission.closed": "submission_status",
        },
    },
    "issuehunt": {
        "secret_env": "ISSUEHUNT_WEBHOOK_SECRET",
        "signature_header": "X-IssueHunt-Signature",
        "events": {
            "bounty.paid": "payout_received",
            "submission.merged": "submission_status",
        },
    },
    "algora": {
        "secret_env": "ALGORA_WEBHOOK_SECRET",
        "signature_header": "X-Algora-Signature",
        "events": {
            "bounty.paid": "payout_received",
            "pr.merged": "submission_status",
        },
    },
}


def _verify_signature(platform: str, body: bytes, signature: str) -> bool:
    """Verify webhook signature using HMAC."""
    config = PLATFORM_WEBHOOK_CONFIG.get(platform)
    if not config:
        return False

    secret = config.get("secret_env")
    if not secret:
        return False

    # Get secret from credentials
    try:
        creds = OpportunityCredentials()
        secret_value = getattr(creds, secret, "")
    except Exception:
        return False

    if not secret_value:
        logger.warning(f"No webhook secret configured for {platform}")
        return False

    expected = hmac.new(
        secret_value.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    # Handle different signature formats
    if signature.startswith("sha256="):
        signature = signature[7:]

    return hmac.compare_digest(expected, signature)


def _parse_webhook_event(platform: str, body: dict[str, Any], headers: dict[str, str]) -> WebhookEvent | None:
    """Parse platform-specific webhook payload into normalized event."""
    config = PLATFORM_WEBHOOK_CONFIG.get(platform)
    if not config:
        return None

    platform_events = config.get("events", {})
    event_type = None

    # Platform-specific parsing
    if platform == "hackerone":
        action = body.get("action", "")
        event_type = platform_events.get(action)
        external_id = body.get("data", {}).get("id", "")

    elif (
        platform == "bugcrowd"
        or platform == "intigriti"
        or platform == "yeswehack"
        or platform == "opire"
        or platform == "issuehunt"
        or platform == "algora"
    ):
        event = body.get("event", "")
        event_type = platform_events.get(event)
        external_id = body.get("data", {}).get("id", "")

    else:
        return None

    if not event_type:
        return None

    return WebhookEvent(
        platform=platform,
        event_type=event_type,
        external_id=str(external_id),
        timestamp=datetime.now(UTC).isoformat(),
        payload=body,
        raw_headers=headers,
    )


async def _process_payout_event(event: WebhookEvent) -> dict[str, Any]:
    """Process a payout received event."""
    tracker = get_revenue_tracker()
    if not tracker:
        return {"success": False, "error": "Revenue tracker not available"}

    # Extract payout info from payload
    payload = event.payload
    amount = 0.0
    currency = "USD"
    program = ""

    if event.platform == "hackerone":
        amount = float(payload.get("data", {}).get("attributes", {}).get("amount", 0))
        currency = payload.get("data", {}).get("attributes", {}).get("currency", "USD")
        program = payload.get("data", {}).get("attributes", {}).get("team", {}).get("handle", "")

    elif event.platform == "bugcrowd":
        amount = float(payload.get("data", {}).get("attributes", {}).get("amount", 0))
        currency = payload.get("data", {}).get("attributes", {}).get("currency", "USD")
        program = payload.get("data", {}).get("attributes", {}).get("program_name", "")

    # Add to revenue tracker
    try:
        tracker.record_payout(
            platform=event.platform,
            external_id=event.external_id,
            amount=amount,
            currency=currency,
            program=program,
            timestamp=event.timestamp,
        )
        logger.info(f"Recorded payout: {event.platform} ${amount} for {event.external_id}")
        return {"success": True, "amount": amount, "currency": currency}
    except Exception as exc:
        logger.error(f"Failed to record payout: {exc}")
        return {"success": False, "error": str(exc)}


async def _process_submission_status_event(event: WebhookEvent) -> dict[str, Any]:
    """Process a submission status change event."""
    auto_submit = get_auto_submit_engine()

    # Find submission by external_id
    submission = None
    for s in auto_submit._submissions.values():
        if s.submission_result and s.submission_result.get("external_id") == event.external_id:
            submission = s
            break

    if not submission:
        logger.warning(f"No submission found for external_id: {event.external_id}")
        return {"success": False, "error": "Submission not found"}

    # Update submission status based on platform event
    payload = event.payload
    new_status = None

    if event.platform == "hackerone":
        state = payload.get("data", {}).get("attributes", {}).get("state", "")
        if state in ("triaged", "resolved"):
            new_status = SubmissionStatus.CONFIRMED
        elif state in ("rejected", "duplicate", "informative"):
            new_status = SubmissionStatus.FAILED

    elif event.platform == "bugcrowd":
        state = payload.get("data", {}).get("attributes", {}).get("state", "")
        if state in ("accepted", "resolved", "paid"):
            new_status = SubmissionStatus.CONFIRMED
        elif state in ("rejected", "duplicate"):
            new_status = SubmissionStatus.FAILED

    # Update submission record
    if new_status:
        submission.status = new_status
        submission.updated_at = datetime.now(UTC).isoformat()
        if new_status == SubmissionStatus.CONFIRMED:
            submission.confirmed_at = datetime.now(UTC).isoformat()
        auto_submit._save_queue()
        logger.info(f"Updated submission {submission.id} to {new_status.value}")

    return {"success": True, "status": new_status.value if new_status else "unchanged"}


# ─── Webhook Endpoints ───


@router.post("/{platform}")
async def platform_webhook(
    platform: str,
    request: Request,
    x_signature: str | None = Header(None, alias="X-Signature"),
) -> Response:
    """Generic webhook endpoint for all platforms."""
    platform = platform.lower()

    if platform not in PLATFORM_WEBHOOK_CONFIG:
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")

    # Read raw body for signature verification
    body = await request.body()

    # Verify signature
    config = PLATFORM_WEBHOOK_CONFIG[platform]
    signature_header = config.get("signature_header", "X-Signature")
    signature = request.headers.get(signature_header) or x_signature

    if not signature or not _verify_signature(platform, body, signature):
        logger.warning(f"Invalid webhook signature for {platform}")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse body
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None

    # Parse event
    headers = dict(request.headers)
    event = _parse_webhook_event(platform, payload, headers)
    if not event:
        return Response(content="Event not handled", status_code=200)

    logger.info(f"Received webhook: {platform} / {event.event_type} / {event.external_id}")

    # Process based on event type
    result = {"success": False, "message": "Unhandled event type"}

    if event.event_type == "payout_received":
        result = await _process_payout_event(event)
    elif event.event_type == "submission_status":
        result = await _process_submission_status_event(event)

    return Response(content=json.dumps(result), media_type="application/json", status_code=200)


@router.get("/health")
async def webhook_health() -> dict[str, Any]:
    """Health check for webhook system."""
    return {
        "status": "ok",
        "platforms_configured": list(PLATFORM_WEBHOOK_CONFIG.keys()),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/test/{platform}")
async def test_webhook(platform: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Test webhook processing without signature verification (dev only)."""
    platform = platform.lower()

    if platform not in PLATFORM_WEBHOOK_CONFIG:
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")

    event = _parse_webhook_event(platform, payload, {})
    if not event:
        return {"success": False, "error": "Event not recognized"}

    result = {"success": False, "message": "Unhandled event type"}

    if event.event_type == "payout_received":
        result = await _process_payout_event(event)
    elif event.event_type == "submission_status":
        result = await _process_submission_status_event(event)

    return result
