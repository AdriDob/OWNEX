"""ORION CORE — ROI Engine: live scoring of platforms/programs from DB data."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from core.orion.models import PlatformID, ROIScore

logger = logging.getLogger("ownex.orion.roi")

# Normalize platform names from various DB schemas into PlatformID
_PLATFORM_ALIASES: dict[str, PlatformID] = {
    "hackerone": PlatformID.HACKERONE,
    "hackerone.com": PlatformID.HACKERONE,
    "h1": PlatformID.HACKERONE,
    "bugcrowd": PlatformID.BUGGROWD,
    "bugcrowd.com": PlatformID.BUGGROWD,
    "bc": PlatformID.BUGGROWD,
    "intigriti": PlatformID.INTIGRITI,
    "intigriti.com": PlatformID.INTIGRITI,
    "algora": PlatformID.ALGORA,
    "algora.io": PlatformID.ALGORA,
    "issuehunt": PlatformID.ISSUEHUNT,
    "issuehunt.io": PlatformID.ISSUEHUNT,
    "github": PlatformID.GITHUB,
    "github.com": PlatformID.GITHUB,
    "freelancer": PlatformID.FREELANCER,
    "freelancer.com": PlatformID.FREELANCER,
    "superteam": PlatformID.SUPERTEAM,
    "superteam.fun": PlatformID.SUPERTEAM,
    "opencollective": PlatformID.OPENCOLLECTIVE,
    "opencollective.com": PlatformID.OPENCOLLECTIVE,
    "opire": PlatformID.OPIRE,
    "opire.dev": PlatformID.OPIRE,
}


def _normalize_platform(raw: str) -> PlatformID:
    return _PLATFORM_ALIASES.get(raw.strip().lower(), PlatformID.UNKNOWN)


def score_all(session: Any) -> dict[str, ROIScore]:
    """Compute ROI scores for all known platforms using live DB data.

    Queries three sources:
        1. ``revenue_payouts`` — confirmed + pending payout amounts
        2. ``findings`` — total & confirmed counts per platform (via target)
        3. ``submission_records`` — acceptance rate & response times

    Returns a dict of ``{platform_id: ROIScore}`` sorted by score descending.
    """
    scores: dict[str, ROIScore] = {}
    now = datetime.now(timezone.utc)
    cutoff_30d = now - timedelta(days=30)
    cutoff_7d = now - timedelta(days=7)

    # ── 1. Payout data ──────────────────────────────────────────
    try:
        payout_rows = session.execute(
            text("""
                SELECT
                    platform,
                    COALESCE(SUM(CASE WHEN status = 'confirmed' AND paid_at >= :cut30 THEN amount ELSE 0 END), 0) AS earnings_30d,
                    COALESCE(SUM(CASE WHEN status = 'confirmed' AND paid_at >= :cut7 THEN amount ELSE 0 END), 0) AS earnings_7d,
                    COALESCE(SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END), 0) AS pending_payout,
                    MAX(paid_at) AS last_paid
                FROM revenue_payouts
                GROUP BY platform
            """),
            {"cut30": cutoff_30d, "cut7": cutoff_7d},
        ).fetchall()
        for platform, e30, e7, pending, last_paid in payout_rows:
            pid = _normalize_platform(platform).value
            if pid not in scores:
                scores[pid] = ROIScore(platform=_normalize_platform(platform))
            s = scores[pid]
            s.earnings_30d = float(e30 or 0)
            s.earnings_7d = float(e7 or 0)
            s.pending_payout = float(pending or 0)
            s.last_active = str(last_paid or "")
    except Exception as exc:
        logger.debug("ROI: payout query failed (DB may be empty): %s", exc)

    # ── 2. Finding counts ───────────────────────────────────────
    try:

        def _findings_by_platform(table: str) -> list[Any]:
            return session.execute(
                text(f"""
                    SELECT
                        t.name AS target_name,
                        COUNT(f.id) AS total,
                        SUM(CASE WHEN f.status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed
                    FROM {table} f
                    JOIN targets t ON t.id = f.target_id
                    GROUP BY t.name
                """),
            ).fetchall()

        for row in _findings_by_platform("findings"):
            pid = _normalize_platform(row.target_name or "").value
            if pid not in scores:
                scores[pid] = ROIScore(platform=_normalize_platform(row.target_name or ""))
            scores[pid].finding_count = int(row.total or 0)
            scores[pid].confirmed_count = int(row.confirmed or 0)
    except Exception as exc:
        logger.debug("ROI: findings query failed: %s", exc)

    # ── 3. Acceptance rate via submission_records ───────────────
    try:
        sub_rows = session.execute(
            text("""
                SELECT
                    platform,
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) AS accepted,
                    AVG(CASE WHEN responded_at IS NOT NULL THEN
                        (julianday(responded_at) - julianday(created_at)) * 24
                        ELSE NULL END) AS avg_response_hours
                FROM submission_records
                GROUP BY platform
            """),
        ).fetchall()
        for platform, total, accepted, avg_hours in sub_rows:
            pid = _normalize_platform(platform).value
            if pid not in scores:
                scores[pid] = ROIScore(platform=_normalize_platform(platform))
            scores[pid].acceptance_rate = float(accepted or 0) / max(float(total or 1), 1)
            scores[pid].avg_response_time_hours = float(avg_hours or 0)
    except Exception as exc:
        logger.debug("ROI: submission query failed: %s", exc)

    # ── 4. Calculate final scores ──────────────────────────────
    _compute_scores(scores)

    # Sort by score descending
    sorted_scores: dict[str, ROIScore] = {}
    for rank, pid in enumerate(sorted(scores, key=lambda p: scores[p].score, reverse=True), start=1):
        s = scores[pid]
        s.rank = rank
        sorted_scores[pid] = s

    return sorted_scores


def _compute_scores(scores: dict[str, ROIScore]) -> None:
    """Compute the 0-100 score for each platform based on weighted signals.

    Weights (total = 100):
        - Earnings 30d:      40 pts (direct revenue is king)
        - Acceptance rate:   20 pts (platform that pays out = better)
        - Confirmed findings: 15 pts (track record)
        - Pending payout:    10 pts (money already earned, just not received)
        - Response speed:    10 pts (faster = better workflow)
        - Recent activity:    5 pts (recency bonus)
    """
    max_earnings = max((s.earnings_30d for s in scores.values()), default=0.0) or 1.0

    for s in scores.values():
        pts = 0.0

        # Earnings (40 pts) — normalized against best performer
        pts += 40.0 * min(s.earnings_30d / max_earnings, 1.0)

        # Acceptance rate (20 pts)
        pts += 20.0 * s.acceptance_rate

        # Confirmed findings (15 pts) — log scale, cap at 50
        pts += 15.0 * min(s.confirmed_count / 50.0, 1.0)

        # Pending payout (10 pts) — money on the way
        pts += 10.0 * min(s.pending_payout / 500.0, 1.0)

        # Response speed (10 pts) — faster = better
        if s.avg_response_time_hours > 0:
            speed = max(0.0, 1.0 - s.avg_response_time_hours / 168.0)  # 168h = 1 week
            pts += 10.0 * speed
        else:
            pts += 5.0  # neutral when unknown

        # Recent activity (5 pts)
        if s.last_active:
            try:
                last = datetime.fromisoformat(s.last_active.replace("Z", "+00:00"))
                days_since = (datetime.now(timezone.utc) - last).days
                pts += 5.0 * max(0.0, 1.0 - days_since / 30.0)
            except (ValueError, TypeError):
                pass

        s.score = round(min(pts, 100.0), 1)

        # Trend detection
        if s.earnings_7d > 0 and s.earnings_30d > 0:
            ratio = s.earnings_7d / max(s.earnings_30d / 4, 1.0)  # normalize to weekly
            if ratio > 1.5:
                s.trend = "rising"
            elif ratio < 0.5:
                s.trend = "falling"
            else:
                s.trend = "stable"
