"""In-process timing metrics for OWNEX.

Migrated verbatim from the module `cores/observability.py`, which the package
`cores/observability/` shadowed: Python resolves the package first, so the
module was unreachable and `from cores.observability import get_metrics` /
`timer` raised ImportError (that broke `GET /api/system/status` with a 500).

Lives inside the package so there is exactly ONE observability SSOT.
"""

import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from threading import Lock
from typing import Any

LOG = logging.getLogger("ownex.observability")

_metrics: dict[str, list[float]] = defaultdict(list)
_metrics_lock = Lock()


@contextmanager
def timer(name: str):
    """Context manager that records execution duration for `name`."""
    t0 = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - t0
        with _metrics_lock:
            _metrics[name].append(elapsed)


def record(name: str, value: float) -> None:
    with _metrics_lock:
        _metrics[name].append(value)


def get_metrics() -> dict[str, Any]:
    """Return aggregated timing metrics."""
    result: dict[str, Any] = {}
    with _metrics_lock:
        for name, vals in dict(_metrics).items():
            if not vals:
                continue
            result[name] = {
                "count": len(vals),
                "total_ms": round(sum(vals) * 1000, 1),
                "avg_ms": round((sum(vals) / len(vals)) * 1000, 1),
                "min_ms": round(min(vals) * 1000, 1),
                "max_ms": round(max(vals) * 1000, 1),
            }
    return result


def reset_metrics() -> None:
    with _metrics_lock:
        _metrics.clear()
