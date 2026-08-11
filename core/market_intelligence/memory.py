"""Memoria de inteligencia — rastrea resultados de señales pasadas y aprende."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.intel.memory")

MEMORY_DIR = Path.home() / ".orion" / "intel_memory"


class IntelMemory:
    """Tracks signal outcomes and source reliability over time."""

    def __init__(self, storage_dir: Path = MEMORY_DIR) -> None:
        self._storage = storage_dir
        self._storage.mkdir(parents=True, exist_ok=True)
        self._outcomes: list[dict[str, Any]] = self._load("outcomes.json")
        self._source_reliability: dict[str, dict[str, Any]] = self._load("sources.json")
        self._predictions: list[dict[str, Any]] = self._load("predictions.json")

    # ── Persistence ──

    def _load(self, name: str) -> Any:
        path = self._storage / name
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return [] if name in ("outcomes.json", "predictions.json") else {}
        return [] if name in ("outcomes.json", "predictions.json") else {}

    def _save(self, name: str, data: Any) -> None:
        path = self._storage / name
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            logger.warning("[INTEL] Memory save error: %s", e)

    # ── Outcome tracking ──

    def record_outcome(
        self,
        signal_id: str,
        source_id: str,
        correct: bool,
        details: str = "",
        value_usd: float = 0.0,
    ) -> None:
        """Record whether a signal prediction was correct."""
        entry = {
            "signal_id": signal_id,
            "source_id": source_id,
            "correct": correct,
            "details": details,
            "value_usd": value_usd,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._outcomes.append(entry)
        self._save("outcomes.json", self._outcomes)

        # Update source reliability
        if source_id not in self._source_reliability:
            self._source_reliability[source_id] = {"total": 0, "correct": 0, "value_usd": 0.0}
        src = self._source_reliability[source_id]
        src["total"] += 1
        if correct:
            src["correct"] += 1
        src["value_usd"] += value_usd
        self._save("sources.json", self._source_reliability)

        logger.info(
            "[INTEL] Outcome: signal=%s, correct=%s, value=$%.0f",
            signal_id[:8],
            correct,
            value_usd,
        )

    def record_prediction(
        self,
        source_id: str,
        source_name: str,
        prediction: str,
        confidence: str = "medium",
    ) -> str:
        """Record a prediction made from a signal for later verification."""
        import uuid

        pred_id = str(uuid.uuid4())[:8]
        entry = {
            "id": pred_id,
            "source_id": source_id,
            "source_name": source_name,
            "prediction": prediction,
            "confidence": confidence,
            "verified": False,
            "correct": None,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._predictions.append(entry)
        self._save("predictions.json", self._predictions)
        return pred_id

    def verify_prediction(self, prediction_id: str, correct: bool) -> bool:
        """Mark a prediction as correct/incorrect."""
        for p in self._predictions:
            if p.get("id") == prediction_id:
                p["verified"] = True
                p["correct"] = correct
                p["verified_at"] = datetime.now(UTC).isoformat()
                self._save("predictions.json", self._predictions)
                self.record_outcome(
                    signal_id=prediction_id,
                    source_id=p.get("source_id", "unknown"),
                    correct=correct,
                    details=f"Prediction: {p.get('prediction', '')[:100]}",
                )
                return True
        return False

    # ── Analytics ──

    def source_accuracy(self, source_id: str) -> float:
        src = self._source_reliability.get(source_id)
        if not src or src["total"] == 0:
            return 0.0
        return src["correct"] / src["total"]

    def source_value(self, source_id: str) -> float:
        src = self._source_reliability.get(source_id)
        return src["value_usd"] if src else 0.0

    def top_sources(self, limit: int = 10) -> list[dict[str, Any]]:
        sorted_src = sorted(
            self._source_reliability.items(),
            key=lambda x: (x[1]["correct"] / max(x[1]["total"], 1), x[1]["value_usd"]),
            reverse=True,
        )
        return [{"source_id": sid, **stats} for sid, stats in sorted_src[:limit]]

    def pending_predictions(self) -> list[dict[str, Any]]:
        return [p for p in self._predictions if not p.get("verified")]

    def stats(self) -> dict[str, Any]:
        total_outcomes = len(self._outcomes)
        correct = sum(1 for o in self._outcomes if o.get("correct"))
        return {
            "total_outcomes": total_outcomes,
            "correct": correct,
            "accuracy": round(correct / max(total_outcomes, 1), 3),
            "total_value_tracked": sum(o.get("value_usd", 0) for o in self._outcomes),
            "sources_tracked": len(self._source_reliability),
            "pending_predictions": len(self.pending_predictions()),
            "total_predictions": len(self._predictions),
        }


_INTEL_MEMORY: IntelMemory | None = None


def get_intel_memory() -> IntelMemory:
    global _INTEL_MEMORY
    if _INTEL_MEMORY is None:
        _INTEL_MEMORY = IntelMemory()
    return _INTEL_MEMORY


def reset_intel_memory() -> None:
    global _INTEL_MEMORY
    _INTEL_MEMORY = None
