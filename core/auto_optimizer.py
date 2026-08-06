"""Auto-Optimizer — aprende de resultados y mejora estrategias.

Analiza resultados pasados y ajusta:
- Qué plataformas generan más ROI
- Qué horarios son mejores para cada ciclo
- Qué tipos de findings tienen mayor tasa de aceptación
- Cuándo pausar/reanudar estrategias
- Optimización de allocation de capital
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.auto_optimizer")


class AutoOptimizer:
    """Learns from results and optimizes strategies."""

    def __init__(self) -> None:
        self._data_dir = os.path.expanduser("~/.config/ownex/optimizer/")
        os.makedirs(self._data_dir, exist_ok=True)
        self._insights: list[dict[str, Any]] = []

    def record_result(self, result: dict[str, Any]) -> None:
        """Record a result for analysis."""
        result["recorded_at"] = datetime.now(UTC).isoformat()
        self._insights.append(result)

        # Persist to file
        date_key = datetime.now(UTC).strftime("%Y-%m-%d")
        file_path = os.path.join(self._data_dir, f"{date_key}.json")

        existing = []
        if os.path.exists(file_path):
            with open(file_path) as f:
                existing = json.load(f)

        existing.append(result)
        with open(file_path, "w") as f:
            json.dump(existing, f, indent=2, default=str)

    def analyze_performance(self, days: int = 30) -> dict[str, Any]:
        """Analyze performance over the last N days."""
        results = self._load_recent_results(days)

        if not results:
            return {"message": "Not enough data for analysis", "days": days}

        # Calculate metrics
        by_platform: dict[str, dict[str, Any]] = {}
        by_source: dict[str, dict[str, Any]] = {}

        for r in results:
            platform = r.get("platform", "unknown")
            source = r.get("source", "unknown")

            if platform not in by_platform:
                by_platform[platform] = {"attempts": 0, "successes": 0, "revenue": 0.0}
            by_platform[platform]["attempts"] += 1
            if r.get("success"):
                by_platform[platform]["successes"] += 1
            by_platform[platform]["revenue"] += r.get("revenue", 0)

            if source not in by_source:
                by_source[source] = {"attempts": 0, "successes": 0, "revenue": 0.0}
            by_source[source]["attempts"] += 1
            if r.get("success"):
                by_source[source]["successes"] += 1
            by_source[source]["revenue"] += r.get("revenue", 0)

        # Calculate success rates
        for platform, data in by_platform.items():
            data["success_rate"] = round(data["successes"] / max(data["attempts"], 1) * 100, 1)

        for source, data in by_source.items():
            data["success_rate"] = round(data["successes"] / max(data["attempts"], 1) * 100, 1)

        # Find best performing
        best_platform = max(by_platform.items(), key=lambda x: x[1]["revenue"]) if by_platform else ("none", {})
        best_source = max(by_source.items(), key=lambda x: x[1]["revenue"]) if by_source else ("none", {})

        return {
            "period_days": days,
            "total_results": len(results),
            "by_platform": by_platform,
            "by_source": by_source,
            "best_platform": {"name": best_platform[0], **best_platform[1]} if best_platform[0] != "none" else {},
            "best_source": {"name": best_source[0], **best_source[1]} if best_source[0] != "none" else {},
            "recommendations": self._generate_recommendations(by_platform, by_source),
            "analyzed_at": datetime.now(UTC).isoformat(),
        }

    def _load_recent_results(self, days: int) -> list[dict[str, Any]]:
        """Load results from the last N days."""
        results = []
        for i in range(days):
            date = (datetime.now(UTC) - __import__("datetime").timedelta(days=i)).strftime("%Y-%m-%d")
            file_path = os.path.join(self._data_dir, f"{date}.json")
            if os.path.exists(file_path):
                with open(file_path) as f:
                    results.extend(json.load(f))
        return results

    def _generate_recommendations(
        self,
        by_platform: dict[str, Any],
        by_source: dict[str, Any],
    ) -> list[str]:
        """Generate actionable recommendations based on data."""
        recommendations = []

        # Find platforms with high success but low attempts
        for platform, data in by_platform.items():
            if data.get("success_rate", 0) > 70 and data["attempts"] < 10:
                recommendations.append(
                    f"🔍 {platform}: High success rate ({data['success_rate']}%) but low volume. "
                    f"Increase scanning frequency."
                )

        # Find sources with low success
        for source, data in by_source.items():
            if data.get("success_rate", 0) < 30 and data["attempts"] > 20:
                recommendations.append(
                    f"⚠️ {source}: Low success rate ({data.get('success_rate', 0)}%) with high volume. "
                    f"Review approach or reduce effort."
                )

        # Revenue concentration
        total_revenue = sum(d["revenue"] for d in by_platform.values())
        for platform, data in by_platform.items():
            pct = data["revenue"] / max(total_revenue, 1) * 100
            if pct > 50:
                recommendations.append(f"💰 {platform} generates {pct:.0f}% of revenue. Prioritize this platform.")

        if not recommendations:
            recommendations.append("✅ Performance is balanced. Continue current strategy.")

        return recommendations

    def get_optimal_allocation(self) -> dict[str, Any]:
        """Get optimal capital allocation based on performance."""
        analysis = self.analyze_performance(30)
        by_source = analysis.get("by_source", {})

        total_revenue = sum(d["revenue"] for d in by_source.values())
        if total_revenue == 0:
            return {"allocation": {}, "reason": "No revenue data available"}

        allocation = {}
        for source, data in by_source.items():
            weight = data["revenue"] / total_revenue
            allocation[source] = {
                "weight": round(weight, 3),
                "expected_monthly": round(data["revenue"] * weight, 2),
            }

        return {
            "allocation": allocation,
            "total_monthly_revenue": round(total_revenue, 2),
            "based_on_days": 30,
            "generated_at": datetime.now(UTC).isoformat(),
        }


_optimizer: AutoOptimizer | None = None


def get_optimizer() -> AutoOptimizer:
    """Get singleton AutoOptimizer."""
    global _optimizer
    if _optimizer is None:
        _optimizer = AutoOptimizer()
    return _optimizer
