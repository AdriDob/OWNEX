from __future__ import annotations

import logging

logger = logging.getLogger("ownex.playwright")

try:
    from playwright.async_api import async_playwright

    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False
    logger.warning("playwright not installed — plugin disabled")


class PlaywrightSensor:
    connector_id = "playwright_sensor"
    display_name = "Playwright Web Sensor"

    def __init__(self) -> None:
        if not _PLAYWRIGHT_AVAILABLE:
            raise ImportError("playwright-async not installed")

    async def visit(self, url: str) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            content = await page.content()
            title = await page.title()
            screenshots: list[bytes] = []
            screenshot = await page.screenshot(full_page=True)
            screenshots.append(screenshot)
            await browser.close()
        return {
            "url": url,
            "title": title,
            "content": content,
            "screenshots": screenshots,
            "status": "ok",
        }
