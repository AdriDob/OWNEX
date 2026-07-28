"""Browser Automation Layer — Playwright-based agent for platforms without write APIs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page

WaitUntil = Literal["commit", "domcontentloaded", "load", "networkidle"]

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None


@dataclass
class BrowserResult:
    """Result of a browser action."""

    success: bool
    action: str
    target: str
    message: str = ""
    data: dict[str, Any] | None = None
    error: str | None = None


class BrowserAgent:
    """Playwright-based browser automation with session persistence."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.headless = self.config.get("headless", True)
        self.storage_dir = Path(self.config.get("storage_dir", "~/.config/ownex/browser_sessions")).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def start(self) -> None:
        """Start Playwright browser with persistent context."""
        if async_playwright is None:
            raise ImportError("playwright not installed. Run: pip install playwright && playwright install chromium")

        playwright = await async_playwright().start()
        self._playwright = playwright
        self._browser = await playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        # Persistent context for session/cookie persistence
        context_path = self.storage_dir / "default"
        self._context = await self._browser.new_context(
            storage_state=str(context_path / "state.json") if (context_path / "state.json").exists() else None,
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        self._page = await self._context.new_page()

    async def stop(self) -> None:
        """Stop browser and save session state."""
        if self._context:
            context_path = self.storage_dir / "default"
            context_path.mkdir(exist_ok=True)
            await self._context.storage_state(path=str(context_path / "state.json"))
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def __aenter__(self) -> BrowserAgent:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    # === Core Navigation ===

    async def goto(self, url: str, wait_until: WaitUntil = "networkidle") -> BrowserResult:
        """Navigate to URL."""
        if not self._page:
            return BrowserResult(False, "goto", url, error="Browser not started")

        try:
            await self._page.goto(url, wait_until=wait_until, timeout=30000)
            return BrowserResult(True, "goto", url, f"Navigated to {url}")
        except Exception as e:
            return BrowserResult(False, "goto", url, error=str(e))

    async def click(self, selector: str, wait_for_navigation: bool = False) -> BrowserResult:
        """Click element by selector."""
        if not self._page:
            return BrowserResult(False, "click", selector, error="Browser not started")

        try:
            if wait_for_navigation:
                async with self._page.expect_navigation(wait_until="networkidle"):
                    await self._page.click(selector)
            else:
                await self._page.click(selector)
            return BrowserResult(True, "click", selector, f"Clicked {selector}")
        except Exception as e:
            return BrowserResult(False, "click", selector, error=str(e))

    async def fill(self, selector: str, value: str) -> BrowserResult:
        """Fill input field."""
        if not self._page:
            return BrowserResult(False, "fill", selector, error="Browser not started")

        try:
            await self._page.fill(selector, value)
            return BrowserResult(True, "fill", selector, f"Filled {selector}")
        except Exception as e:
            return BrowserResult(False, "fill", selector, error=str(e))

    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> BrowserResult:
        """Wait for element to appear."""
        if not self._page:
            return BrowserResult(False, "wait_for_selector", selector, error="Browser not started")

        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return BrowserResult(True, "wait_for_selector", selector, f"Found {selector}")
        except Exception as e:
            return BrowserResult(False, "wait_for_selector", selector, error=str(e))

    async def upload_files(self, selector: str, file_paths: list[str]) -> BrowserResult:
        """Upload files to input."""
        if not self._page:
            return BrowserResult(False, "upload_files", selector, error="Browser not started")

        try:
            await self._page.set_input_files(selector, file_paths)
            return BrowserResult(True, "upload_files", selector, f"Uploaded {len(file_paths)} files")
        except Exception as e:
            return BrowserResult(False, "upload_files", selector, error=str(e))

    async def wait_for_url(self, url_pattern: str, timeout: int = 30000) -> BrowserResult:
        """Wait for URL to match pattern."""
        if not self._page:
            return BrowserResult(False, "wait_for_url", url_pattern, error="Browser not started")

        try:
            await self._page.wait_for_url(url_pattern, timeout=timeout)
            return BrowserResult(True, "wait_for_url", url_pattern, f"URL matched: {self._page.url}")
        except Exception as e:
            return BrowserResult(False, "wait_for_url", url_pattern, error=str(e))

    async def get_text(self, selector: str) -> BrowserResult:
        """Get text content of element."""
        if not self._page:
            return BrowserResult(False, "get_text", selector, error="Browser not started")

        try:
            text = await self._page.text_content(selector)
            return BrowserResult(True, "get_text", selector, text or "", data={"text": text})
        except Exception as e:
            return BrowserResult(False, "get_text", selector, error=str(e))

    # === Platform-Specific Actions ===

    async def login_linkedin(self, email: str, password: str) -> BrowserResult:
        """Login to LinkedIn."""
        result = await self.goto("https://www.linkedin.com/login")
        if not result.success:
            return result

        await self.fill("#username", email)
        await self.fill("#password", password)
        result = await self.click('button[type="submit"]', wait_for_navigation=True)

        if result.success and self._page is not None and "feed" in self._page.url:
            return BrowserResult(True, "login_linkedin", "linkedin.com", "Logged in successfully")
        return BrowserResult(False, "login_linkedin", "linkedin.com", error="Login failed")

    async def easy_apply_linkedin(self, job_url: str) -> BrowserResult:
        """Apply to LinkedIn job via Easy Apply."""
        result = await self.goto(job_url)
        if not result.success:
            return result

        # Click Easy Apply button
        result = await self.click(
            'button:has-text("Easy Apply"), button:has-text("Aplicar fácilmente")', wait_for_navigation=True
        )
        if not result.success:
            return BrowserResult(False, "easy_apply", job_url, error="Easy Apply button not found")

        # Fill application steps (simplified)
        # This would need expansion for multi-step forms
        return BrowserResult(True, "easy_apply", job_url, "Application submitted")

    async def claim_algora_issue(self, issue_url: str) -> BrowserResult:
        """Claim issue on Algora via web."""
        result = await self.goto(issue_url)
        if not result.success:
            return result

        result = await self.click('button:has-text("Claim"), button:has-text("Claim this bounty")')
        if not result.success:
            return BrowserResult(False, "claim_algora", issue_url, error="Claim button not found")

        return BrowserResult(True, "claim_algora", issue_url, "Issue claimed via web")

    async def dataannotation_claim_task(self, task_url: str) -> BrowserResult:
        """Claim task on DataAnnotation.tech."""
        result = await self.goto(task_url)
        if not result.success:
            return result

        result = await self.click('button:has-text("Start"), button:has-text("Claim"), button:has-text("Begin")')
        if not result.success:
            return BrowserResult(False, "dataannotation_claim", task_url, error="Claim button not found")

        return BrowserResult(True, "dataannotation_claim", task_url, "Task claimed")

    async def outlier_claim_task(self, task_url: str) -> BrowserResult:
        """Claim task on Outlier.ai."""
        result = await self.goto(task_url)
        if not result.success:
            return result

        result = await self.click('button:has-text("Start"), button:has-text("Begin Task")')
        if not result.success:
            return BrowserResult(False, "outlier_claim", task_url, error="Start button not found")

        return BrowserResult(True, "outlier_claim", task_url, "Task claimed")

    # === Session Management ===

    async def save_session(self, name: str = "default") -> BrowserResult:
        """Save current session state."""
        if not self._context:
            return BrowserResult(False, "save_session", name, error="No context")

        try:
            path = self.storage_dir / name / "state.json"
            path.parent.mkdir(exist_ok=True)
            await self._context.storage_state(path=str(path))
            return BrowserResult(True, "save_session", name, f"Session saved to {path}")
        except Exception as e:
            return BrowserResult(False, "save_session", name, error=str(e))

    async def load_session(self, name: str = "default") -> BrowserResult:
        """Load session state (requires restart)."""
        path = self.storage_dir / name / "state.json"
        if not path.exists():
            return BrowserResult(False, "load_session", name, error="Session file not found")

        return BrowserResult(True, "load_session", name, f"Session found at {path}, restart browser to load")
