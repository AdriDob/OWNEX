from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from core.memory.store import UnifiedMemoryStore
from database import db, models

logger = logging.getLogger("ownex.revenue.economic_memory")

NS = "economic"


def _econ_models():
    from database import models_economic

    return models_economic


def _init_program() -> dict[str, Any]:
    return {
        "total_payout": 0.0,
        "count": 0,
        "platforms": set(),
        "last_payout": None,
        "submissions": 0,
        "accepted": 0,
        "rejected": 0,
        "duplicate": 0,
        "na": 0,
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
        "findings_total": 0,
        "avg_resolution_days": 0.0,
        "resolution_days_sum": 0.0,
        "resolution_count": 0,
    }


class EconomicMemory:
    def __init__(self) -> None:
        self._store = UnifiedMemoryStore()

    def refresh(self, estimated_hours: float = 0.0) -> dict[str, list[str]]:
        programs: dict[str, dict[str, Any]] = {}
        vulns: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"total_payout": 0.0, "count": 0, "accepted": 0, "rejected": 0, "duplicate": 0}
        )
        total_payout = 0.0
        total_accepted = 0
        total_rejected = 0
        total_duplicate = 0

        session = db.SessionLocal()
        try:
            econ = _econ_models()
            payouts = session.query(econ.PayoutRecord).filter(econ.PayoutRecord.status == "confirmed").all()
            for p in payouts:
                prog = p.program or "unknown"
                if prog not in programs:
                    programs[prog] = _init_program()
                programs[prog]["total_payout"] += p.amount
                programs[prog]["count"] += 1
                programs[prog]["platforms"].add(p.platform)
                if p.paid_at and (programs[prog]["last_payout"] is None or p.paid_at > programs[prog]["last_payout"]):
                    programs[prog]["last_payout"] = p.paid_at
                total_payout += p.amount

            subs = session.query(models.SubmissionRecord).all()
            for s in subs:
                report = session.query(models.Report).filter(models.Report.id == s.report_id).first()
                if not report:
                    continue
                prog = report.program or "unknown"
                if prog not in programs:
                    programs[prog] = _init_program()

                programs[prog]["submissions"] += 1
                if s.status in ("bounty_paid", "resolved", "accepted"):
                    programs[prog]["accepted"] += 1
                    total_accepted += 1
                elif s.status in ("rejected", "informative"):
                    programs[prog]["rejected"] += 1
                    total_rejected += 1
                elif s.status in ("duplicate", "closed"):
                    programs[prog]["duplicate"] += 1
                    total_duplicate += 1
                programs[prog]["platforms"].add(s.platform)

                if s.submitted_at and s.last_update:
                    delta = (s.last_update - s.submitted_at).total_seconds()
                    if delta > 0:
                        programs[prog]["resolution_days_sum"] += delta / 86400
                        programs[prog]["resolution_count"] += 1

                programs[prog]["severity"] = report.severity or "medium"

                vt = report.vulnerability or "unknown"
                vulns[vt]["total_payout"] += report.confirmed_reward or 0.0
                vulns[vt]["count"] += 1
                if s.status in ("bounty_paid", "resolved", "accepted"):
                    vulns[vt]["accepted"] += 1
                elif s.status in ("rejected", "informative"):
                    vulns[vt]["rejected"] += 1
                elif s.status in ("duplicate", "closed"):
                    vulns[vt]["duplicate"] += 1

            reports_for_findings = (
                session.query(models.Report)
                .filter(
                    models.Report.finding_ids.isnot(None),
                    models.Report.finding_ids != "",
                    models.Report.finding_ids != "[]",
                )
                .all()
            )
            for report in reports_for_findings:
                prog = report.program or "unknown"
                if prog not in programs:
                    programs[prog] = _init_program()
                    programs[prog]["platforms"].add("unknown")
                sev = (report.severity or "medium").lower()
                if sev in ("critical", "high", "medium", "low", "info"):
                    programs[prog][sev] += 1
                programs[prog]["findings_total"] += 1
        finally:
            session.close()

        updated_keys: list[str] = []
        for prog_name, data in sorted(programs.items()):
            key = f"program:{prog_name}"
            data["platforms"] = sorted(data["platforms"])
            data["last_payout"] = data["last_payout"].isoformat() if data["last_payout"] else None
            total_f = max(data.get("findings_total", 0), 1)
            data["critical_rate"] = round(data["critical"] / total_f, 3)
            data["duplicate_rate"] = round(data["duplicate"] / max(data["submissions"], 1), 3)
            total_subs = max(data["submissions"], 1)
            data["accepted_rate"] = round(data["accepted"] / total_subs, 3)
            data["rejected_rate"] = round(data["rejected"] / total_subs, 3)
            data["avg_payout_per_accepted"] = round(data["total_payout"] / max(data["accepted"], 1), 2)
            data["avg_resolution_days"] = round(data["resolution_days_sum"] / max(data["resolution_count"], 1), 1)
            data["usd_per_hour"] = round(data["total_payout"] / max(estimated_hours or data["count"] * 2, 1), 2)
            score = (
                data["accepted_rate"] * 25
                + min(data["total_payout"] / 50, 25)
                + (1 - data["duplicate_rate"]) * 20
                + data["critical_rate"] * 20
                + max(0, 10 - data["avg_resolution_days"])
            )
            data["roi_score"] = round(score, 1)

            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._store.store(NS, key, content=prog_name, metadata=data, tags=["program"])
            updated_keys.append(key)

        vuln_keys: list[str] = []
        for vt, data in sorted(vulns.items()):
            key = f"vuln:{vt}"
            data["avg_payout"] = round(data["total_payout"] / max(data["count"], 1), 2)
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._store.store(NS, key, content=vt, metadata=data, tags=["vuln"])
            vuln_keys.append(key)

        best = ""
        if programs:
            best = max(programs, key=lambda p: programs[p]["roi_score"])
        summary = {
            "total_programs": len(programs),
            "total_payout": total_payout,
            "total_accepted": total_accepted,
            "total_rejected": total_rejected,
            "total_duplicate": total_duplicate,
            "total_hours": estimated_hours,
            "overall_usd_per_hour": round(total_payout / max(estimated_hours or 1, 1), 2),
            "best_program": best,
            "overall_accepted_rate": round(
                total_accepted / max(total_accepted + total_rejected + total_duplicate, 1), 3
            ),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        self._store.store(NS, "summary:overall", content="economic_summary", metadata=summary, tags=["summary"])
        logger.info(
            "[ECONOMIC_MEMORY] Stored %d programs, %d vuln types, total payout $%.2f",
            len(programs),
            len(vulns),
            total_payout,
        )
        return {"programs": updated_keys, "vulns": vuln_keys}

    def get_program(self, name: str) -> dict[str, Any] | None:
        return self._store.get(NS, f"program:{name}")

    def get_summary(self) -> dict[str, Any] | None:
        return self._store.get(NS, "summary:overall")

    def list_programs(self) -> list[dict[str, Any]]:
        entries = self._store.query(namespace=NS, tags=["program"])
        out = []
        for e in entries:
            meta = e.get("metadata") or e.get("metadata_json") or {}
            if isinstance(meta, str):
                meta = json.loads(meta)
            out.append(
                {
                    "program": meta.get("program") or e.get("content", ""),
                    "total_payout": meta.get("total_payout", 0.0),
                    "usd_per_hour": meta.get("usd_per_hour", 0.0),
                    "roi_score": meta.get("roi_score", 0.0),
                    "count": meta.get("count", 0),
                    "platforms": meta.get("platforms", []),
                    "accepted": meta.get("accepted", 0),
                    "rejected": meta.get("rejected", 0),
                    "duplicate": meta.get("duplicate", 0),
                    "critical": meta.get("critical", 0),
                    "high": meta.get("high", 0),
                    "medium": meta.get("medium", 0),
                    "low": meta.get("low", 0),
                    "critical_rate": meta.get("critical_rate", 0.0),
                    "duplicate_rate": meta.get("duplicate_rate", 0.0),
                    "accepted_rate": meta.get("accepted_rate", 0.0),
                    "avg_payout_per_accepted": meta.get("avg_payout_per_accepted", 0.0),
                    "avg_resolution_days": meta.get("avg_resolution_days", 0.0),
                }
            )
        out.sort(key=lambda x: -x.get("roi_score", x.get("usd_per_hour", 0)))
        return out

    def rank_programs(self) -> list[dict[str, Any]]:
        return self.list_programs()
