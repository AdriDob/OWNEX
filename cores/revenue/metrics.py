"""Revenue Metrics — continuous measurement of revenue performance.

Aggregates data from PayoutRecord, SubmissionRecord, RevenueEvent, and Finding
to provide real-time dashboards for ROI by program, vuln type, tool, reasoner,
acceptance rate, time-to-payout, and monthly revenue.

Usage::

    from core.revenue.metrics import RevenueMetrics
    metrics = RevenueMetrics()
    dashboard = metrics.full_dashboard()
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from database.db import SessionLocal
from database.models import Finding, SubmissionRecord
from database.models_economic import PayoutRecord

logger = logging.getLogger("orion.core.revenue.metrics")


class RevenueMetrics:
    """Aggregates revenue data for dashboards and analysis."""

    def monthly_revenue(self, months: int = 12) -> list[dict[str, Any]]:
        """Revenue breakdown by month."""
        session = SessionLocal()
        try:
            cutoff = datetime.now(UTC) - timedelta(days=months * 30)
            payouts = (
                session.query(PayoutRecord)
                .filter(PayoutRecord.paid_at >= cutoff, PayoutRecord.status == "confirmed")
                .all()
            )

            by_month: dict[str, dict[str, Any]] = {}
            for p in payouts:
                if not p.paid_at:
                    continue
                key = p.paid_at.strftime("%Y-%m")
                if key not in by_month:
                    by_month[key] = {"month": key, "total": 0.0, "count": 0, "by_platform": defaultdict(float)}
                by_month[key]["total"] += p.amount
                by_month[key]["count"] += 1
                by_month[key]["by_platform"][p.platform] += p.amount

            result = []
            for key in sorted(by_month.keys()):
                entry = by_month[key]
                entry["by_platform"] = dict(entry["by_platform"])
                result.append(entry)
            return result
        finally:
            session.close()

    def roi_by_program(self) -> list[dict[str, Any]]:
        """ROI breakdown by program/bounty target."""
        session = SessionLocal()
        try:
            payouts = session.query(PayoutRecord).filter(PayoutRecord.status == "confirmed").all()
            by_program: dict[str, dict[str, Any]] = {}
            for p in payouts:
                prog = p.program or "unknown"
                if prog not in by_program:
                    by_program[prog] = {
                        "program": prog,
                        "total_payout": 0.0,
                        "count": 0,
                        "platforms": set(),
                        "last_payout": None,
                    }
                by_program[prog]["total_payout"] += p.amount
                by_program[prog]["count"] += 1
                by_program[prog]["platforms"].add(p.platform)
                if p.paid_at and (not by_program[prog]["last_payout"] or p.paid_at > by_program[prog]["last_payout"]):
                    by_program[prog]["last_payout"] = p.paid_at.isoformat() if p.paid_at else None

            result = []
            for _prog, data in by_program.items():
                data["platforms"] = sorted(data["platforms"])
                result.append(data)

            return sorted(result, key=lambda x: x["total_payout"], reverse=True)
        finally:
            session.close()

    def roi_by_vuln_type(self) -> list[dict[str, Any]]:
        """ROI breakdown by vulnerability type."""
        session = SessionLocal()
        try:
            payouts = (
                session.query(PayoutRecord, Finding)
                .join(SubmissionRecord, PayoutRecord.submission_record_id == SubmissionRecord.id, isouter=True)
                .join(Finding, SubmissionRecord.report_id == Finding.id, isouter=True)
                .filter(PayoutRecord.status == "confirmed")
                .all()
            )

            by_type: dict[str, dict[str, Any]] = {}
            for payout, finding in payouts:
                vtype = (finding.vulnerability_type or "unknown") if finding else "unknown"
                if vtype not in by_type:
                    by_type[vtype] = {"vuln_type": vtype, "total_payout": 0.0, "count": 0, "total_programs": set()}
                by_type[vtype]["total_payout"] += payout.amount
                by_type[vtype]["count"] += 1
                if payout.program:
                    by_type[vtype]["total_programs"].add(payout.program)

            result = []
            for _vt, data in by_type.items():
                data["total_programs"] = len(data["total_programs"])
                data["avg_payout"] = round(data["total_payout"] / max(data["count"], 1), 2)
                result.append(data)

            return sorted(result, key=lambda x: x["total_payout"], reverse=True)
        finally:
            session.close()

    def acceptance_rate(self) -> dict[str, Any]:
        """Acceptance rate by platform with trend."""
        session = SessionLocal()
        try:
            submissions = session.query(SubmissionRecord).all()
            by_platform: dict[str, dict[str, int]] = defaultdict(
                lambda: {"total": 0, "accepted": 0, "rejected": 0, "pending": 0}
            )
            for s in submissions:
                by_platform[s.platform]["total"] += 1
                if s.status in ("accepted", "won"):
                    by_platform[s.platform]["accepted"] += 1
                elif s.status in ("rejected", "dismissed", "duplicate"):
                    by_platform[s.platform]["rejected"] += 1
                else:
                    by_platform[s.platform]["pending"] += 1

            result = {}
            for platform, data in by_platform.items():
                resolved = data["accepted"] + data["rejected"]
                result[platform] = {
                    "total": data["total"],
                    "accepted": data["accepted"],
                    "rejected": data["rejected"],
                    "pending": data["pending"],
                    "acceptance_rate": round(data["accepted"] / max(resolved, 1), 3),
                }
            return result
        finally:
            session.close()

    def time_metrics(self) -> dict[str, Any]:
        """Average time to acceptance and time to payout."""
        session = SessionLocal()
        try:
            submissions = (
                session.query(SubmissionRecord)
                .filter(
                    SubmissionRecord.status.in_(["accepted", "won", "rejected", "dismissed"]),
                    SubmissionRecord.submitted_at.isnot(None),
                )
                .all()
            )

            acceptance_times = []
            payout_times = []
            for s in submissions:
                if s.last_update and s.submitted_at:
                    delta = (s.last_update - s.submitted_at).total_seconds() / 86400
                    if s.status in ("accepted", "won"):
                        acceptance_times.append(delta)
                        payout_times.append(delta)

            payouts = (
                session.query(PayoutRecord)
                .filter(
                    PayoutRecord.status == "confirmed",
                    PayoutRecord.paid_at.isnot(None),
                )
                .all()
            )

            for p in payouts:
                if (
                    p.paid_at
                    and hasattr(p, "submission_record")
                    and p.submission_record
                    and p.submission_record.submitted_at
                ):
                    delta = (p.paid_at - p.submission_record.submitted_at).total_seconds() / 86400
                    payout_times.append(delta)

            return {
                "avg_days_to_acceptance": round(sum(acceptance_times) / max(len(acceptance_times), 1), 1),
                "acceptance_samples": len(acceptance_times),
                "avg_days_to_payout": round(sum(payout_times) / max(len(payout_times), 1), 1),
                "payout_samples": len(payout_times),
            }
        finally:
            session.close()

    def payout_summary(self) -> dict[str, Any]:
        """Aggregate payout statistics."""
        session = SessionLocal()
        try:
            payouts = session.query(PayoutRecord).filter(PayoutRecord.status == "confirmed").all()
            total = sum(p.amount for p in payouts)
            count = len(payouts)
            pending = session.query(PayoutRecord).filter(PayoutRecord.status == "pending").all()
            pending_total = sum(p.amount for p in pending)
            pending_count = len(pending)

            by_platform: dict[str, float] = defaultdict(float)
            for p in payouts:
                by_platform[p.platform] += p.amount

            by_currency: dict[str, float] = defaultdict(float)
            for p in payouts:
                by_currency[p.currency] += p.amount

            return {
                "total_payout": round(total, 2),
                "total_count": count,
                "avg_payout": round(total / max(count, 1), 2),
                "pending_total": round(pending_total, 2),
                "pending_count": pending_count,
                "by_platform": dict(sorted(by_platform.items(), key=lambda x: x[1], reverse=True)),
                "by_currency": dict(by_currency),
            }
        finally:
            session.close()

    def finding_pipeline(self) -> dict[str, Any]:
        """Pipeline metrics: findings created, confirmed, submitted."""
        session = SessionLocal()
        try:
            total = session.query(Finding).count()
            confirmed = session.query(Finding).filter(Finding.status == "confirmed").count()
            rejected = session.query(Finding).filter(Finding.status == "rejected").count()
            open_ = session.query(Finding).filter(Finding.status.in_(["open", "pending"])).count()

            submissions = session.query(SubmissionRecord).count()
            submitted_accepted = (
                session.query(SubmissionRecord)
                .filter(
                    SubmissionRecord.status.in_(["accepted", "won"]),
                )
                .count()
            )
            submitted_rejected = (
                session.query(SubmissionRecord)
                .filter(
                    SubmissionRecord.status.in_(["rejected", "dismissed"]),
                )
                .count()
            )

            return {
                "findings": {
                    "total": total,
                    "confirmed": confirmed,
                    "rejected": rejected,
                    "open": open_,
                    "confirmation_rate": round(confirmed / max(total, 1), 3),
                },
                "submissions": {
                    "total": submissions,
                    "accepted": submitted_accepted,
                    "rejected": submitted_rejected,
                    "pending": submissions - submitted_accepted - submitted_rejected,
                    "acceptance_rate": round(submitted_accepted / max(submitted_accepted + submitted_rejected, 1), 3),
                },
            }
        finally:
            session.close()

    def findings_by_type(self) -> list[dict[str, Any]]:
        """Findings count and confirmation rate by vulnerability type."""
        session = SessionLocal()
        try:
            findings = session.query(Finding).all()
            by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "confirmed": 0, "rejected": 0})
            for f in findings:
                vtype = f.vulnerability_type or "unknown"
                by_type[vtype]["total"] += 1
                if f.status == "confirmed":
                    by_type[vtype]["confirmed"] += 1
                elif f.status == "rejected":
                    by_type[vtype]["rejected"] += 1

            result = []
            for vtype, data in by_type.items():
                resolved = data["confirmed"] + data["rejected"]
                result.append(
                    {
                        "vuln_type": vtype,
                        "total": data["total"],
                        "confirmed": data["confirmed"],
                        "rejected": data["rejected"],
                        "confirmation_rate": round(data["confirmed"] / max(resolved, 1), 3),
                    }
                )
            return sorted(result, key=lambda x: x["total"], reverse=True)
        finally:
            session.close()

    def usd_per_hour(self, estimated_hours: float = 1.0) -> float:
        """Average USD earned per hour of work.

        Uses historical payout data divided by default effort estimate.
        When no payout data exists, returns 0.
        """
        summary = self.payout_summary()
        total = summary.get("total_payout", 0.0)
        count = summary.get("total_count", 0)
        if count == 0 or total <= 0:
            return 0.0
        avg_payout = total / count
        return round(avg_payout / max(estimated_hours, 0.5), 2)

    def platform_speed_days(self) -> dict[str, float]:
        """Dynamic platform payout speed from actual history.

        Returns dict of {platform: avg_days_to_payout}.
        Falls back to empty dict if no data.
        """
        payouts = self.payout_summary().get("by_platform", {})
        if not payouts:
            return {}
        speed: dict[str, float] = {}
        session = SessionLocal()
        try:
            for platform in payouts:
                plat_payouts = (
                    session.query(PayoutRecord)
                    .filter(
                        PayoutRecord.status == "confirmed",
                        PayoutRecord.platform == platform,
                        PayoutRecord.paid_at.isnot(None),
                    )
                    .all()
                )
                days = []
                for p in plat_payouts:
                    if p.submission_record and p.submission_record.submitted_at and p.paid_at:
                        delta = (p.paid_at - p.submission_record.submitted_at).total_seconds() / 86400
                        days.append(delta)
                if days:
                    speed[platform] = round(sum(days) / len(days), 1)
            return speed
        finally:
            session.close()

    def full_dashboard(self) -> dict[str, Any]:
        """Complete revenue dashboard with all metrics."""
        return {
            "payout_summary": self.payout_summary(),
            "monthly_revenue": self.monthly_revenue(),
            "roi_by_program": self.roi_by_program(),
            "roi_by_vuln_type": self.roi_by_vuln_type(),
            "acceptance_rate": self.acceptance_rate(),
            "time_metrics": self.time_metrics(),
            "finding_pipeline": self.finding_pipeline(),
            "findings_by_type": self.findings_by_type(),
            "usd_per_hour": self.usd_per_hour(),
            "platform_speed_days": self.platform_speed_days(),
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def capital_dashboard(self) -> dict[str, Any]:
        """Capital Dashboard — unified view of capital generated, potential, ROI, and pipeline."""
        base = self.full_dashboard()

        session = SessionLocal()
        try:
            recent_findings = (
                session.query(Finding)
                .filter(
                    Finding.created_at >= datetime.now(UTC) - timedelta(days=30),
                )
                .count()
            )
            critical_findings = (
                session.query(Finding)
                .filter(
                    Finding.severity == "critical",
                )
                .count()
            )
            high_findings = (
                session.query(Finding)
                .filter(
                    Finding.severity == "high",
                )
                .count()
            )
            total_findings = session.query(Finding).count()

            target_count = 0
            scanned_recently = 0
            try:
                from database.models import Target

                target_count = session.query(Target).count()
                scanned_recently = (
                    session.query(Target)
                    .filter(
                        Target.last_scanned >= datetime.now(UTC) - timedelta(days=7),
                    )
                    .count()
                )
            except Exception:
                pass
        finally:
            session.close()

        base["capital"] = {
            "total_findings": total_findings,
            "recent_30d_findings": recent_findings,
            "critical_count": critical_findings,
            "high_count": high_findings,
            "critical_rate": round(critical_findings / max(total_findings, 1), 3),
            "high_rate": round(high_findings / max(total_findings, 1), 3),
        }
        base["targets"] = {
            "total": target_count,
            "scanned_last_7d": scanned_recently,
        }

        try:
            from core.revenue.economic_memory import EconomicMemory

            econ = EconomicMemory()
            base["program_ranking"] = econ.rank_programs()[:10]
            summary = econ.get_summary()
            if summary:
                m = summary.get("metadata") or summary
                if isinstance(m, str):
                    import json

                    m = json.loads(m)
                base["economic_memory"] = {
                    "total_programs": m.get("total_programs", 0),
                    "total_accepted": m.get("total_accepted", 0),
                    "total_rejected": m.get("total_rejected", 0),
                    "total_duplicate": m.get("total_duplicate", 0),
                    "overall_usd_per_hour": m.get("overall_usd_per_hour", 0.0),
                    "overall_accepted_rate": m.get("overall_accepted_rate", 0.0),
                }
        except Exception:
            base["program_ranking"] = []
            base["economic_memory"] = {}

        try:
            from core.target_intelligence.prioritizer import TargetPrioritizer
            from database.models import Target

            session = SessionLocal()
            try:
                targets = session.query(Target).all()
                prioritizer = TargetPrioritizer()
                _, results = prioritizer.prioritize(targets, {})
                base["hot_targets"] = [r.to_dict() for r in results[:5] if r.expected_value > 0]
            finally:
                session.close()
        except Exception:
            base["hot_targets"] = []

        return base
