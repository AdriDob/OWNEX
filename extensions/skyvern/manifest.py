from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="skyvern",
    name="Skyvern Browser Agent",
    version="1.0.0",
    description="AI-powered browser automation for visual web navigation. "
    "Navigates websites, fills forms, extracts structured data, and "
    "monitors visual changes — no DOM-dependent selectors needed.",
    author="OWNEX",
    icon="ScanEye",
    capabilities=[
        Capability(
            domain="web_navigation",
            name="Web Navigation",
            description="Navigate any website with AI-powered understanding",
        ),
        Capability(
            domain="form_filling",
            name="Form Filling",
            description="Complete web forms automatically with AI",
        ),
        Capability(
            domain="data_extraction",
            name="Structured Data Extraction",
            description="Extract structured data from any web page",
        ),
        Capability(
            domain="visual_monitoring",
            name="Visual Monitoring",
            description="Monitor web pages for visual changes",
        ),
    ],
    hooks={
        "sensor_fetch": "skyvern.hooks.on_sensor_fetch",
        "web_observe": "skyvern.hooks.on_web_observe",
    },
    providers=["skyvern_browser"],
    hot_reloadable=False,
    requires_core="5.0.0",
)
