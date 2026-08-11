from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from database import db
from database.models import Finding, MetricEvent, Verdict

logger = logging.getLogger("orion.core.evolution.analyze")

# ── Config ──────────────────────────────────────────────

_BOTTLENECK_MIN_EVENTS = 5
_BOTTLENECK_MIN_TOTAL_MS = 60_000  # 1 minute minimum to be a bottleneck
_ASSET_MIN_OBSERVATIONS = 3
_RECENT_DAYS = 14

_BOTTLENECK_THRESHOLD_MS_PER_FINDING = 30_000  # 30s per finding = warning


class AnalyzeEngine:
    """Analyze ORION metrics and generate knowledge assets.

    Four levels, each building on the previous:
      1. descriptive_stats  — distributions, rates, percentiles
      2. detect_bottlenecks — modules/tools with poor output/time ratio
      3. mine_patterns      — vuln-type × tech correlations from findings
      4. propose_assets     — evidence check → write KnowledgeAssets (draft)
    """

    def __init__(self) -> None:
        self.results: dict[str, Any] = {}

    def run_full_cycle(self) -> dict[str, Any]:
        """Execute all four analysis levels in sequence."""
        self.results = {}
        self.results["run_at"] = datetime.now(UTC).isoformat()
        self.results["window_days"] = _RECENT_DAYS

        cutoff = datetime.now(UTC) - timedelta(days=_RECENT_DAYS)
        self._cutoff = cutoff

        self.results["level_1"] = self._level_1_descriptive_stats(cutoff)
        self.results["level_2"] = self._level_2_bottlenecks(cutoff)
        self.results["level_3"] = self._level_3_patterns(cutoff)
        self.results["level_4"] = self._level_4_propose_assets(cutoff)

        logger.info(
            "[ANALYZE] Cycle complete: %d metrics, %d bottlenecks, %d patterns, %d assets proposed",
            self.results["level_1"].get("event_count", 0),
            len(self.results["level_2"].get("bottlenecks", [])),
            len(self.results["level_3"].get("patterns", [])),
            len(self.results["level_4"].get("assets_created", [])),
        )
        return self.results

    # ── Level 1: Descriptive Statistics ─────────────────

    def _level_1_descriptive_stats(self, cutoff: datetime) -> dict[str, Any]:
        """Compute counts, averages, percentiles across all metric events."""
        session = db.SessionLocal()
        try:
            events = session.query(MetricEvent).filter(MetricEvent.timestamp >= cutoff).all()
        finally:
            session.close()

        if not events:
            return {"event_count": 0, "message": "No recent events"}

        durations = [e.duration_ms for e in events if e.duration_ms is not None]
        by_module: dict[str, list[float]] = defaultdict(list)
        by_tool: dict[str, list[float]] = defaultdict(list)
        by_status: Counter[str] = Counter()
        by_type: Counter[str] = Counter()

        for e in events:
            if e.duration_ms is not None:
                by_module[e.module].append(e.duration_ms)
                if e.tool:
                    by_tool[e.tool].append(e.duration_ms)
            by_status[e.status or "unknown"] += 1
            by_type[e.event_type] += 1

        stats: dict[str, Any] = {
            "event_count": len(events),
            "duration": self._summarize_durations(durations),
            "by_module": {m: self._summarize_durations(ds) for m, ds in sorted(by_module.items())},
            "by_tool": {t: self._summarize_durations(ds) for t, ds in sorted(by_tool.items())},
            "by_status": dict(by_status.most_common()),
            "by_type": dict(by_type.most_common()),
        }
        return stats

    @staticmethod
    def _summarize_durations(values: list[float]) -> dict[str, float | None]:
        if not values:
            return {"count": 0}
        return {
            "count": len(values),
            "avg_ms": round(sum(values) / len(values), 1),
            "p50_ms": round(sorted(values)[len(values) // 2], 1),
            "p95_ms": round(sorted(values)[int(len(values) * 0.95)], 1),
            "min_ms": round(min(values), 1),
            "max_ms": round(max(values), 1),
            "total_ms": round(sum(values), 1),
        }

    # ── Level 2: Bottleneck Detection ───────────────────

    def _level_2_bottlenecks(self, cutoff: datetime) -> dict[str, Any]:
        """Find modules and tools with low output relative to time invested."""
        session = db.SessionLocal()
        try:
            events = session.query(MetricEvent).filter(MetricEvent.timestamp >= cutoff).all()
        finally:
            session.close()

        bottlenecks: list[dict[str, Any]] = []
        tool_groups: dict[str, list[MetricEvent]] = defaultdict(list)
        module_groups: dict[str, list[MetricEvent]] = defaultdict(list)

        for e in events:
            if e.tool:
                tool_groups[e.tool].append(e)
            module_groups[e.module].append(e)

        finding_ids = self._recent_finding_ids(cutoff)
        finding_count = len(finding_ids)

        for tool, group in sorted(tool_groups.items()):
            if len(group) < _BOTTLENECK_MIN_EVENTS:
                continue
            durations = [g.duration_ms for g in group if g.duration_ms is not None]
            total_ms = sum(durations)
            if total_ms < _BOTTLENECK_MIN_TOTAL_MS:
                continue
            avg_ms = total_ms / len(group) if group else 0
            tool_findings = self._count_findings_for_tool(tool, cutoff)
            ms_per_finding = total_ms / tool_findings if tool_findings > 0 else total_ms

            bottlenecks.append(
                {
                    "type": "tool",
                    "name": tool,
                    "runs": len(group),
                    "total_ms": round(total_ms, 1),
                    "total_hours": round(total_ms / 3_600_000, 2),
                    "avg_ms": round(avg_ms, 1),
                    "findings_produced": tool_findings,
                    "ms_per_finding": round(ms_per_finding, 1),
                    "status": "warning" if ms_per_finding > _BOTTLENECK_THRESHOLD_MS_PER_FINDING else "ok",
                }
            )

        # Module-level summary
        for module, group in sorted(module_groups.items()):
            durations = [g.duration_ms for g in group if g.duration_ms is not None]
            total_ms = sum(durations)
            total_findings = sum(1 for e in group if e.event_type == "finding:created")
            bottlenecks.append(
                {
                    "type": "module",
                    "name": module,
                    "runs": len(group),
                    "total_ms": round(total_ms, 1),
                    "total_hours": round(total_ms / 3_600_000, 2),
                    "findings_produced": total_findings,
                    "ms_per_finding": round(total_ms / total_findings, 1) if total_findings else None,
                }
            )

        bottlenecks.sort(key=lambda b: b.get("total_ms", 0), reverse=True)

        for b in bottlenecks:
            if b.get("ms_per_finding", 0) and b["ms_per_finding"] > _BOTTLENECK_THRESHOLD_MS_PER_FINDING:
                opp_cost_hours = (
                    b["ms_per_finding"] * b.get("runs", 1) - _BOTTLENECK_THRESHOLD_MS_PER_FINDING * b.get("runs", 1)
                ) / 3_600_000
                b["opportunity_cost_hours"] = round(opp_cost_hours, 2)

        return {
            "bottlenecks": bottlenecks,
            "bottleneck_count": len(bottlenecks),
            "total_findings_in_window": finding_count,
        }

    @staticmethod
    def _recent_finding_ids(cutoff: datetime) -> set[int]:
        session = db.SessionLocal()
        try:
            rows = session.query(Finding.id).filter(Finding.created_at >= cutoff).all()
            return {r[0] for r in rows}
        finally:
            session.close()

    @staticmethod
    def _count_findings_for_tool(tool: str, cutoff: datetime) -> int:
        """Estimate findings associated with a tool via metric events."""
        session = db.SessionLocal()
        try:
            tool_events = (
                session.query(MetricEvent)
                .filter(MetricEvent.tool == tool)
                .filter(MetricEvent.timestamp >= cutoff)
                .filter(MetricEvent.finding_id.isnot(None))
                .count()
            )
            return tool_events
        finally:
            session.close()

    # ── Level 3: Pattern Mining ─────────────────────────

    def _level_3_patterns(self, cutoff: datetime) -> dict[str, Any]:
        """Find correlations between vulnerability types and technologies."""
        session = db.SessionLocal()
        try:
            verdicts = session.query(Verdict).filter(Verdict.created_at >= cutoff).all()
            findings = session.query(Finding).filter(Finding.created_at >= cutoff).all()
        finally:
            session.close()

        patterns: list[dict[str, Any]] = []

        vuln_type_counts: Counter[str] = Counter()
        for f in findings:
            vt = f.vulnerability_type or "unknown"
            vuln_type_counts[vt] += 1

        total = sum(vuln_type_counts.values())
        if total > 0:
            patterns.append(
                {
                    "type": "vulnerability_distribution",
                    "title": "Distribución de tipos de vulnerabilidad",
                    "data": {k: round(v / total * 100, 1) for k, v in vuln_type_counts.most_common()},
                    "observations": total,
                }
            )

        status_counts: Counter[str] = Counter()
        for v in verdicts:
            status_counts[v.status] += 1
        v_total = sum(status_counts.values())
        if v_total > 0:
            patterns.append(
                {
                    "type": "verdict_distribution",
                    "title": "Distribución de veredictos",
                    "data": dict(status_counts.most_common()),
                    "observations": v_total,
                }
            )

        acceptance_rate = status_counts.get("confirmed", 0) / v_total if v_total > 0 else 0
        patterns.append(
            {
                "type": "acceptance_rate",
                "title": "Tasa de aceptación global",
                "data": {
                    "confirmed": status_counts.get("confirmed", 0),
                    "total": v_total,
                    "rate": round(acceptance_rate, 3),
                },
                "observations": v_total,
            }
        )

        return {"patterns": patterns, "pattern_count": len(patterns)}

    # ── Level 4: Asset Proposal ─────────────────────────

    def _level_4_propose_assets(self, cutoff: datetime) -> dict[str, Any]:
        """Generate KnowledgeAssets from bottlenecks and patterns.

        Evidence check — only writes assets that meet minimum quality bar:
          - Bottleneck assets: require >= _BOTTLENECK_MIN_EVENTS observations
          - Pattern assets: require >= _ASSET_MIN_OBSERVATIONS data points
        """
        created: list[dict[str, Any]] = []
        engine = get_evolution_engine()

        bottlenecks = self.results.get("level_2", {}).get("bottlenecks", [])
        patterns = self.results.get("level_3", {}).get("patterns", [])

        for b in bottlenecks:
            if b.get("runs", 0) < _BOTTLENECK_MIN_EVENTS:
                continue
            if b.get("status") != "warning":
                continue
            if b["type"] != "tool":
                continue

            op_cost = b.get("opportunity_cost_hours", 0)
            evidence = {
                "runs": b["runs"],
                "total_hours": b["total_hours"],
                "findings_produced": b["findings_produced"],
                "ms_per_finding": b["ms_per_finding"],
                "period_days": _RECENT_DAYS,
            }
            title = f"{b['name']}: {b['total_hours']}h sin findings proporcionados (op. cost ~{op_cost:.1f}h)"
            description = (
                f"{b['name']} ejecutó {b['runs']} veces en {_RECENT_DAYS} días "
                f"({b['total_hours']}h totales) y produjo {b['findings_produced']} findings. "
                f"Cada finding costó ~{b['ms_per_finding'] / 1000:.0f}s. "
            )
            if op_cost > 0:
                description += f"Oportunidad perdida estimada: {op_cost:.1f}h."

            asset_id = engine.create_asset(
                asset_type="optimization",
                domain="cateye",
                title=title,
                description=description,
                source="evolution_analyze",
                source_confidence=0.7,
                content={
                    "recommendation": f"Limitar {b['name']} a targets con score > 80",
                    "expected_savings_hours": round(b["total_hours"] * 0.6, 1),
                    "risk": "low",
                },
                evidence=evidence,
                tags=["bottleneck", "automation", b["name"]],
            )
            if asset_id > 0:
                engine.update_asset_status(
                    asset_id,
                    "draft",
                    impact_score=0.0,
                    observation_count=b["runs"],
                    opportunity_cost_hours=op_cost,
                )
                created.append({"id": asset_id, "type": "bottleneck", "title": title})

        for p in patterns:
            if p.get("observations", 0) < _ASSET_MIN_OBSERVATIONS:
                continue
            if p["type"] == "vulnerability_distribution":
                title = f"Distribución de vulnerabilidades ({_RECENT_DAYS}d): {p['data']}"
                asset_id = engine.create_asset(
                    asset_type="statistic",
                    domain="cateye",
                    title=title,
                    description=f"Basado en {p['observations']} findings de los últimos {_RECENT_DAYS} días.",
                    source="evolution_analyze",
                    source_confidence=0.8,
                    content={"distribution": p["data"], "total": p["observations"]},
                    tags=["statistic", "vulnerability", "distribution"],
                )
                if asset_id > 0:
                    engine.update_asset_status(
                        asset_id,
                        "draft",
                        observation_count=p["observations"],
                    )
                    created.append({"id": asset_id, "type": "statistic", "title": title})

            elif p["type"] == "acceptance_rate" and p["observations"] > 10:
                rate = p["data"]["rate"]
                title = f"Tasa de aceptación global: {rate:.1%} ({p['observations']} reportes)"
                asset_id = engine.create_asset(
                    asset_type="statistic",
                    domain="cateye",
                    title=title,
                    description=f"Confirmados: {p['data']['confirmed']} de {p['observations']}.",
                    source="evolution_analyze",
                    source_confidence=0.85 if rate > 0.3 else 0.6,
                    content={"acceptance_rate": rate, "confirmed": p["data"]["confirmed"], "total": p["observations"]},
                    tags=["statistic", "acceptance", "quality"],
                )
                if asset_id > 0:
                    engine.update_asset_status(
                        asset_id,
                        "draft",
                        observation_count=p["observations"],
                    )
                    created.append({"id": asset_id, "type": "statistic", "title": title})

        return {"assets_created": created, "count": len(created)}


# ── Singleton ───────────────────────────────────────────

_analyzer: AnalyzeEngine | None = None


def get_analyze_engine() -> AnalyzeEngine:
    global _analyzer
    if _analyzer is None:
        _analyzer = AnalyzeEngine()
    return _analyzer


# Late import to avoid circular dep
from core.evolution.engine import get_evolution_engine  # noqa: E402
