"""OWNEX MAXIMUM POTENTIAL ENGINE — Daily Optimization Report.

Filosofía del spec "OWNEX MAXIMUM POTENTIAL ENGINE": extraer el máximo valor
real del sistema sin romper estabilidad ni inventar resultados. El reporte
diario consolida señales de motores EXISTENTES (Regla de Oro: no duplica
análisis, los referencia):

- `core.capabilities.registry` → capabilities activas / rotas (mejoras y
  problemas).
- `core.health.engine` → score de salud + servicios caídos (problemas).
- `cores.direct_work_engine.feedback` + `evolution.PerformanceAnalyzer` →
  ganancias de performance (conversión, ROI USD/h, revenue real).
- `cores.direct_work_engine.workbank` + `execution_planner` → ganancias de
  automatización (automation_pct promedio de lo preparado).
- `cores.direct_work_engine.evolution` → lecciones de oportunidades perdidas
  y propuestas de capacidades (próximas acciones).
- `cores.direct_work_engine.income_projection` → impacto esperado (proyección
  honesta; sin ingreso real no inventa números).
- `git log` → mejoras realmente completadas en el repositorio.

Genera el formato exacto del spec:

    OWNEX EVOLUTION REPORT
    Completed improvements / Performance gains / Automation gains /
    New capabilities / Problems discovered / Recommended next actions /
    Expected impact.

Toda sección es defensiva: un motor caído no rompe el reporte.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")

# Reportes diarios persistidos (el sistema se audita a sí mismo cada día).
_REPORTS_SUBDIR: str = "evolution_reports"
REPORTS_HISTORY_LIMIT: int = 30

# Cuántas entradas por sección expone el reporte.
MAX_IMPROVEMENTS: int = 8
MAX_CAPABILITIES: int = 10
MAX_PROBLEMS: int = 8
MAX_NEXT_ACTIONS: int = 5
MAX_GIT_COMMITS: int = 10

# Score de salud bajo el cual se reporta un problema de estabilidad.
HEALTH_PROBLEM_THRESHOLD: float = 0.9

_REPORT_SECTIONS: tuple[str, ...] = (
    "completed_improvements",
    "performance_gains",
    "automation_gains",
    "new_capabilities",
    "problems_discovered",
    "recommended_next_actions",
    "expected_impact",
)


def _safe(fn: Callable[[], T], default: T) -> T:
    """Degradación defensiva: un motor caído nunca rompe el reporte."""
    try:
        return fn()
    except Exception:
        return default


@dataclass
class MaxPotentialReport:
    generated_at: str
    completed_improvements: list[str] = field(default_factory=list)
    performance_gains: dict[str, Any] = field(default_factory=dict)
    automation_gains: dict[str, Any] = field(default_factory=dict)
    new_capabilities: list[str] = field(default_factory=list)
    problems_discovered: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    expected_impact: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "completed_improvements": self.completed_improvements,
            "performance_gains": self.performance_gains,
            "automation_gains": self.automation_gains,
            "new_capabilities": self.new_capabilities,
            "problems_discovered": self.problems_discovered,
            "recommended_next_actions": self.recommended_next_actions,
            "expected_impact": self.expected_impact,
        }


class MaxPotentialEngine:
    """Consolida las señales de evolución del sistema en un reporte diario."""

    def report(self) -> dict[str, Any]:
        report = MaxPotentialReport(generated_at=datetime.now(UTC).isoformat())
        report.completed_improvements = self._completed_improvements()
        report.performance_gains = self._performance_gains()
        report.automation_gains = self._automation_gains()
        report.new_capabilities = self._new_capabilities()
        report.problems_discovered = self._problems_discovered()
        report.recommended_next_actions = self._next_actions()
        report.expected_impact = self._expected_impact()
        return report.to_dict()

    # ── secciones ────────────────────────────────────────────

    @staticmethod
    def _completed_improvements() -> list[str]:
        commits = _safe(_recent_commits, [])
        capabilities = _safe(_active_capabilities, [])
        items = [f"commit: {c}" for c in commits]
        items.extend(f"capability activa: {c}" for c in capabilities)
        return items[:MAX_IMPROVEMENTS]

    @staticmethod
    def _performance_gains() -> dict[str, Any]:
        from cores.direct_work_engine.evolution import PerformanceAnalyzer
        from cores.direct_work_engine.feedback import build_history_from_revenue_tracker
        from cores.revenue_tracker import get_revenue_tracker

        records = _safe(lambda: build_history_from_revenue_tracker(get_revenue_tracker()), [])
        analysis = _safe(lambda: PerformanceAnalyzer().analyze(records), None)
        if analysis is None:
            return {"note": "sin historial de outcomes verificados aún"}
        return {
            "total_outcomes": analysis.total,
            "accepted": analysis.accepted,
            "rejected": analysis.rejected,
            "revenue_usd": analysis.revenue,
            "roi_usd_per_hour": analysis.roi_usd_per_hour,
            "conversion_rate": analysis.conversion_rate,
            "top_platform_by_revenue": analysis.top_platform_by_revenue,
            "top_category_by_revenue": analysis.top_category_by_revenue,
        }

    @staticmethod
    def _automation_gains() -> dict[str, Any]:
        from cores.direct_work_engine.execution_planner import plan_execution
        from cores.direct_work_engine.workbank import get_workbank

        bank = _safe(get_workbank, None)
        if bank is None:
            return {"note": "WorkBank no disponible"}
        items = _safe(lambda: bank.best_ready(limit=100), [])
        if not items:
            return {"prepared_jobs": 0, "avg_automation_pct": 0, "estimated_hours_saved": 0.0}
        automation = 0
        for item in items:
            try:
                plan = plan_execution(item.to_dict())
                plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else plan
                automation += int(plan_dict.get("automation_pct", 0) or 0)
            except Exception:
                pass
        avg = automation / len(items)
        hours_saved = round(
            sum(_to_float(i.to_dict().get("reward")) for i in items) * avg / 100 / max(1, len(items)), 1
        )
        return {
            "prepared_jobs": len(items),
            "avg_automation_pct": round(avg, 0),
            "estimated_hours_saved_today": hours_saved,
        }

    @staticmethod
    def _new_capabilities() -> list[str]:
        from cores.direct_work_engine.evolution import CapabilityExpansionDetector

        detector = CapabilityExpansionDetector()
        proposals = _safe(lambda: detector.detect(opportunities=[]), [])
        names = [p.name for p in proposals]
        names.extend(_safe(_active_capabilities, []))
        return names[:MAX_CAPABILITIES]

    @staticmethod
    def _problems_discovered() -> list[str]:
        problems: list[str] = []
        snapshot = _safe(_health_snapshot, None)
        if snapshot is not None:
            score = float(getattr(snapshot, "score", 1.0) or 1.0)
            if score < HEALTH_PROBLEM_THRESHOLD:
                status = str(getattr(snapshot, "status", "degraded"))
                problems.append(f"salud del sistema {status} (score {round(score, 2)})")
        broken = _safe(_broken_capabilities, [])
        problems.extend(f"capability rota: {c}" for c in broken)
        needs_access = _safe(_needs_access_jobs, [])
        if needs_access:
            problems.append(f"{len(needs_access)} trabajos preparados bloqueados por acceso")
        return problems[:MAX_PROBLEMS]

    @staticmethod
    def _next_actions() -> list[str]:
        actions: list[str] = []
        actions.extend(_safe(_access_actions, []))
        actions.extend(_safe(_evolution_actions, []))
        return actions[:MAX_NEXT_ACTIONS]

    @staticmethod
    def _expected_impact() -> dict[str, Any]:
        from cores.direct_work_engine.income_projection import project_income

        work_income = _safe(_monthly_work_income, 0.0)
        projection = None
        if work_income > 0:
            projection = _safe(
                lambda: project_income(
                    work_income_usd_per_month=work_income,
                    savings_usd_per_month=0.0,
                ).to_dict(),
                None,
            )
        automation = _safe(lambda: MaxPotentialEngine._automation_gains(), {})
        return {
            "monthly_work_income_usd": round(work_income, 2),
            "projection": projection or {"note": "configurá ingreso mensual en RevenueTracker para ver proyección"},
            "automation_score": automation.get("avg_automation_pct", 0),
        }

    @staticmethod
    def digest(report: dict[str, Any]) -> dict[str, str]:
        lines = ["OWNEX EVOLUTION REPORT", ""]
        lines.append(f"Completed improvements: {len(report['completed_improvements'])}")
        perf = report["performance_gains"]
        if "conversion_rate" in perf:
            lines.append(
                f"Performance gains: conversion {perf['conversion_rate']}, "
                f"ROI ${perf['roi_usd_per_hour']}/h, revenue ${perf['revenue_usd']}"
            )
        else:
            lines.append(f"Performance gains: {perf.get('note', 'n/a')}")
        aut = report["automation_gains"]
        if "prepared_jobs" in aut:
            lines.append(
                f"Automation gains: {aut['prepared_jobs']} trabajos preparados, "
                f"{aut['avg_automation_pct']}% automatización promedio"
            )
        else:
            lines.append(f"Automation gains: {aut.get('note', 'n/a')}")
        lines.append(f"New capabilities: {', '.join(report['new_capabilities'][:3]) or 'n/a'}")
        problems = report["problems_discovered"]
        lines.append(f"Problems discovered: {', '.join(problems) or 'none'}")
        actions = report["recommended_next_actions"]
        lines.append(f"Recommended next actions: {', '.join(actions) or 'n/a'}")
        impact = report["expected_impact"]
        projection = impact.get("projection", {})
        if "months_to_target" in projection and projection["months_to_target"]:
            lines.append(
                f"Expected impact: objetivo en {projection['months_to_target']} meses "
                f"con capital ${projection.get('capital_at_target_usd', 0)}"
            )
        else:
            lines.append(f"Expected impact: {projection.get('note', 'n/a')}")
        return {"text": "\n".join(lines)}


# ── helpers de datos reales (nunca inventan) ──────────────────


def _recent_commits() -> list[str]:
    import subprocess

    out = subprocess.run(
        ["git", "log", "--oneline", "-n", str(MAX_GIT_COMMITS)],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if out.returncode != 0:
        return []
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def _active_capabilities() -> list[str]:
    from core.capabilities.registry import get_capability_registry

    registry = get_capability_registry()
    return list(registry.list_capabilities())


def _broken_capabilities() -> list[str]:
    from core.capabilities.registry import get_capability_registry

    registry = get_capability_registry()
    entries = getattr(registry, "capabilities", {})
    return [str(k) for k, v in entries.items() if getattr(v, "status", "active") not in ("active",)]


def _health_snapshot():
    from core.health.engine import get_health_center

    return get_health_center().get_snapshot()


def _needs_access_jobs() -> list[Any]:
    from cores.direct_work_engine.workbank import get_workbank

    return get_workbank().needs_access()


def _access_actions() -> list[str]:
    jobs = _safe(_needs_access_jobs, [])
    return [f"configurar acceso para {j.platform} ({j.title})" for j in jobs[:3]]


def _evolution_actions() -> list[str]:
    from cores.direct_work_engine.evolution import CapabilityExpansionDetector

    detector = CapabilityExpansionDetector()
    proposals = _safe(lambda: detector.detect(opportunities=[]), [])
    return [f"adquirir capacidad {p.name} (evidencia: {p.evidence})" for p in proposals[:2]]


def _monthly_work_income() -> float:
    from cores.revenue_tracker import get_revenue_tracker

    metrics = get_revenue_tracker().metrics
    per_platform = getattr(metrics, "per_platform", None)
    if per_platform:
        return sum(_to_float(p.get("completed_amount")) for p in per_platform)
    return 0.0


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def get_evolution_report() -> dict[str, Any]:
    """Public entry point: OWNEX EVOLUTION REPORT (data + digest + trend)."""
    engine = MaxPotentialEngine()
    report = engine.report()
    report["digest"] = engine.digest(report)
    previous = _latest_report(exclude_today=True)
    if previous is not None:
        report["trend"] = _compare_reports(previous, report)
    return report


# ── persistencia diaria (historial + tendencias) ──────────────


def _reports_dir(report_dir: str | Path | None = None) -> Path:
    if report_dir is not None:
        return Path(report_dir)
    return Path(__file__).resolve().parents[3] / "data" / _REPORTS_SUBDIR


def _report_path(day: str, report_dir: str | Path | None = None) -> Path:
    return _reports_dir(report_dir) / f"evolution_{day}.json"


def save_daily_report(report: dict[str, Any], report_dir: str | Path | None = None) -> str | None:
    """Persist the report for today (idempotent: overwrites same-day file)."""
    try:
        today = datetime.now(UTC).date().isoformat()
        path = _report_path(today, report_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, default=str))
        return str(path)
    except Exception:
        return None


def _latest_report(exclude_today: bool = False, report_dir: str | Path | None = None) -> dict[str, Any] | None:
    try:
        root = _reports_dir(report_dir)
        if not root.exists():
            return None
        today = date.today().isoformat()
        files = sorted(
            (p for p in root.glob("evolution_*.json") if p.name.endswith(".json")),
            key=lambda p: p.name,
            reverse=True,
        )
        for path in files:
            day = path.name.removeprefix("evolution_").removesuffix(".json")
            if exclude_today and day >= today:
                continue
            return json.loads(path.read_text())
    except Exception:
        return None
    return None


def report_history(limit: int = REPORTS_HISTORY_LIMIT, report_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """Snapshots diarios con métricas clave, del más reciente al más antiguo."""
    history: list[dict[str, Any]] = []
    try:
        root = _reports_dir(report_dir)
        if not root.exists():
            return history
        files = sorted(
            (p for p in root.glob("evolution_*.json") if p.name.endswith(".json")),
            key=lambda p: p.name,
            reverse=True,
        )
        for path in files[:limit]:
            try:
                data = json.loads(path.read_text())
            except Exception:
                continue
            perf = data.get("performance_gains", {})
            aut = data.get("automation_gains", {})
            history.append(
                {
                    "date": path.name.removeprefix("evolution_").removesuffix(".json"),
                    "generated_at": data.get("generated_at"),
                    "prepared_jobs": aut.get("prepared_jobs", 0),
                    "avg_automation_pct": aut.get("avg_automation_pct", 0),
                    "revenue_usd": perf.get("revenue_usd", 0),
                    "problems": len(data.get("problems_discovered", [])),
                    "next_actions": len(data.get("recommended_next_actions", [])),
                }
            )
    except Exception:
        return []
    return history


def _compare_reports(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Tendencia vs. el reporte anterior: delta de métricas clave (honesto, sin inventar)."""
    trend: dict[str, Any] = {}
    for key in ("prepared_jobs", "avg_automation_pct"):
        prev_val = _to_float(previous.get("automation_gains", {}).get(key))
        curr_val = _to_float(current.get("automation_gains", {}).get(key))
        if prev_val or curr_val:
            trend[key] = round(curr_val - prev_val, 1)
    prev_problems = len(previous.get("problems_discovered", []))
    curr_problems = len(current.get("problems_discovered", []))
    if prev_problems or curr_problems:
        trend["problems_delta"] = curr_problems - prev_problems
    prev_revenue = _to_float(previous.get("performance_gains", {}).get("revenue_usd"))
    curr_revenue = _to_float(current.get("performance_gains", {}).get("revenue_usd"))
    if prev_revenue or curr_revenue:
        trend["revenue_usd_delta"] = round(curr_revenue - prev_revenue, 2)
    if not trend:
        trend = {"note": "sin reporte previo comparable"}
    return trend
