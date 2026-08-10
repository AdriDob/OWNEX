#!/usr/bin/env python3
"""
Capture real screenshots of OWNEX application
Uses Playwright to capture actual UI surfaces
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def capture_screenshots():
    """Capture screenshots of main application surfaces"""
    screenshots_dir = Path("docs/assets/screenshots/desktop")
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    routes = [
        ("mission-control", "Mission Control"),
        ("intelligence", "Intelligence"),
        ("targets", "Targets"),
        ("capital", "Capital Dashboard"),
        ("merlin", "MERLIN"),
        ("agents", "Agent Center"),
        ("reports", "Reports"),
        ("settings", "Settings"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        # Wait for application to be ready
        time.sleep(2)

        for route, name in routes:
            try:
                url = f"http://localhost:5174/{route}"
                print(f"Capturing: {name} ({url})")

                page.goto(url, wait_until="networkidle")
                time.sleep(5)  # Wait for animations and data to load

                filename = f"{route}.png"
                filepath = screenshots_dir / filename
                page.screenshot(path=str(filepath), full_page=False)
                print(f"  ✓ Saved: {filepath}")

            except Exception as e:
                print(f"  ✗ Failed: {e}")

        browser.close()
        print("\nScreenshot capture complete")


if __name__ == "__main__":
    capture_screenshots()
