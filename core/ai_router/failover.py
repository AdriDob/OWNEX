"""Auto Failover — automatic provider switching when a provider fails.

Architecture:
    ProviderMonitor detects failure
        -> FailoverEngine selects best alternative
            -> Updates model_router availability
                -> Notifies EventBus

Failover chain:
    OmniRoute (primary) -> FCC Proxy -> Ollama -> OpenCode (free)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.failover")

FAILOVER_LOG = os.path.expanduser("~/.orion/failover_history.jsonl")


@dataclass
class FailoverEvent:
    timestamp: str
    from_provider: str
    to_provider: str
    reason: str
    success: bool
    duration_ms: float = 0.0
    auto_recovered: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "from_provider": self.from_provider,
            "to_provider": self.to_provider,
            "reason": self.reason,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 1),
            "auto_recovered": self.auto_recovered,
        }


class FailoverEngine:
    def __init__(self) -> None:
        self._history: list[FailoverEvent] = []
        self._load_history()
        self._failover_chain = ["omniroute", "fcc_proxy", "ollama", "opencode"]

    @property
    def failover_chain(self) -> list[str]:
        return list(self._failover_chain)

    def set_chain(self, chain: list[str]) -> None:
        self._failover_chain = list(chain)
        logger.info("Failover chain updated: %s", chain)

    def select_fallback(self, failed_provider: str, available_providers: set[str]) -> str | None:
        failed_idx = -1
        for i, p in enumerate(self._failover_chain):
            if p == failed_provider:
                failed_idx = i
                break

        if failed_idx == -1:
            for p in self._failover_chain:
                if p in available_providers:
                    return p
            return None

        for p in self._failover_chain[failed_idx + 1 :]:
            if p in available_providers:
                return p

        for p in self._failover_chain:
            if p != failed_provider and p in available_providers:
                return p

        return None

    def record_failover(
        self,
        from_provider: str,
        to_provider: str,
        reason: str,
        success: bool = True,
        duration_ms: float = 0.0,
    ) -> FailoverEvent:
        event = FailoverEvent(
            timestamp=datetime.now(UTC).isoformat(),
            from_provider=from_provider,
            to_provider=to_provider,
            reason=reason,
            success=success,
            duration_ms=duration_ms,
        )
        self._history.append(event)
        self._save_history()
        logger.info(
            "Failover: %s -> %s (%s) [%s]",
            from_provider,
            to_provider,
            reason,
            "OK" if success else "FAILED",
        )
        return event

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._history[-limit:]]

    def _load_history(self) -> None:
        try:
            path = Path(FAILOVER_LOG)
            if path.exists():
                with open(path) as f:
                    for line in f:
                        if line.strip():
                            self._history.append(FailoverEvent(**json.loads(line)))
        except Exception as e:
            logger.debug("Cannot load failover history: %s", e)

    def _save_history(self) -> None:
        try:
            path = Path(FAILOVER_LOG)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                for event in self._history[-500:]:
                    f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.warning("Cannot save failover history: %s", e)


_engine: FailoverEngine | None = None


def get_failover_engine() -> FailoverEngine:
    global _engine
    if _engine is None:
        _engine = FailoverEngine()
    return _engine
