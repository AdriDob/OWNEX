from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="crawl4ai",
    name="Crawl4AI Web Scraper",
    version="1.0.0",
    description="LLM-friendly web crawling. Extracts clean markdown from "
    "any URL, supports batch crawling with structured output, "
    "and monitors pages for content changes.",
    author="OWNEX",
    icon="Search",
    capabilities=[
        Capability(
            domain="web_crawl",
            name="Web Crawl",
            description="Crawl any URL and extract LLM-ready markdown content",
        ),
        Capability(
            domain="batch_crawl",
            name="Batch Crawl",
            description="Crawl multiple URLs with structured output",
        ),
        Capability(
            domain="content_monitor",
            name="Content Monitor",
            description="Monitor pages for content changes and new information",
        ),
    ],
    hooks={
        "sensor_fetch": "crawl4ai.hooks.on_sensor_fetch",
        "documentation_scrape": "crawl4ai.hooks.on_documentation_scrape",
    },
    providers=["crawl4ai_scraper"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
