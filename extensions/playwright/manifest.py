from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="playwright",
    name="Playwright Web Sensor",
    version="1.0.0",
    description="Web navigation and browser automation sensor for OWNEX. "
    "Enables visiting pages, extracting content, taking screenshots, "
    "and understanding web interfaces for task detection.",
    author="OWNEX",
    icon="Web",
    capabilities=[
        Capability(
            domain="web_sensor",
            name="Web Sensor",
            description="Visit URLs and extract page content",
        ),
        Capability(
            domain="web_screenshot",
            name="Web Screenshot",
            description="Capture screenshots of web pages",
        ),
        Capability(
            domain="web_task_detection",
            name="Task Detection",
            description="Understand web pages and detect actionable tasks",
        ),
    ],
    hooks={
        "before_scan": "playwright.hooks.before_scan",
        "after_scan": "playwright.hooks.after_scan",
    },
    dependencies=["core/event_bus", "core/storage"],
    providers=["playwright_sensor"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
