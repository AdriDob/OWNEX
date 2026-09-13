"""PlatformBrowserWorkers — Playwright-based workers for AI task platforms."""

from cores.automation.workers.dataannotation_worker import DataAnnotationWorker
from cores.automation.workers.mindrift_browser_worker import MindriftBrowserWorker
from cores.automation.workers.outlier_worker import OutlierWorker

__all__ = [
    "DataAnnotationWorker",
    "OutlierWorker",
    "MindriftBrowserWorker",
]


def get_browser_workers() -> dict[str, object]:
    # Remotasks removed per owner (purge 2026-09-13).
    return {
        "dataannotation": DataAnnotationWorker(),
        "outlier": OutlierWorker(),
        "mindrift_browser": MindriftBrowserWorker(),
    }
