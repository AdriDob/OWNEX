from __future__ import annotations

import logging

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.crawl4ai.connector")

try:
    import crawl4ai

    _CRAWL4AI_AVAILABLE = True
except ImportError:
    _CRAWL4AI_AVAILABLE = False


class Crawl4AIConnector(IConnector):
    """LLM-friendly web crawler connector.

    Extracts clean, structured content from web pages formatted
    for AI consumption — markdown, metadata, and structured data.
    """

    connector_id = "crawl4ai_crawler"
    app_id = "ownex"
    display_name = "Crawl4AI Web Crawler"

    def __init__(self) -> None:
        self._connected = False

    async def connect(self) -> bool:
        if not _CRAWL4AI_AVAILABLE:
            logger.warning("crawl4ai package not installed")
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._connected)

    def get_config_fields(self) -> list[dict]:
        return [
            {
                "key": "crawl_timeout",
                "label": "Crawl timeout (seconds)",
                "type": "number",
                "default": "30",
            },
        ]

    async def crawl(self, url: str, max_pages: int = 1) -> dict:
        """Crawl a URL and return LLM-ready content."""
        if not _CRAWL4AI_AVAILABLE:
            return {"error": "crawl4ai not installed"}
        try:
            import crawl4ai

            result = await crawl4ai.arun(url=url, max_pages=max_pages)
            return {
                "url": url,
                "markdown": getattr(result, "markdown", ""),
                "metadata": getattr(result, "metadata", {}),
            }
        except Exception as exc:
            logger.error("crawl4ai failed: %s", exc)
            return {"error": str(exc)}

    async def crawl_many(self, urls: list[str]) -> list[dict]:
        """Crawl multiple URLs in batch."""
        results = []
        for url in urls:
            result = await self.crawl(url)
            results.append(result)
        return results


async def on_sensor_fetch(event: object) -> None:
    if not _CRAWL4AI_AVAILABLE:
        return
    from extensions.crawl4ai.connector import Crawl4AIConnector

    url = getattr(event, "url", "") or getattr(event, "target", "")
    if url:
        connector = Crawl4AIConnector()
        await connector.connect()
        result = await connector.crawl(url)
        if result and hasattr(event, "set_result"):
            event.set_result(result)


async def on_documentation_scrape(event: object) -> None:
    if not _CRAWL4AI_AVAILABLE:
        return
    from extensions.crawl4ai.connector import Crawl4AIConnector

    url = getattr(event, "url", "") or getattr(event, "data", "")
    if url:
        connector = Crawl4AIConnector()
        await connector.connect()
        result = await connector.crawl(url)
        if result and hasattr(event, "set_result"):
            event.set_result(result.get("markdown", ""))
