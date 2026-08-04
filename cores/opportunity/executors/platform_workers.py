"""Platform Browser Workers — Browser automation for platforms without write APIs.

Supports DataAnnotation, Outlier, Mindrift, Remotasks via Playwright.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from core.opportunity.executors import BaseExecutor, ExecutionResult

try:
    from cores.automation.browser_agent import BrowserAgent
except ImportError:
    BrowserAgent = None

logger = logging.getLogger(__name__)


class DataAnnotationWorker(BaseExecutor):
    """Worker for DataAnnotation.tech — real login, fetch projects, submit responses."""

    platform = "dataannotation"

    # Platform-specific configuration
    BASE_URL = "https://app.dataannotation.tech"
    LOGIN_URL = "https://app.dataannotation.tech/login"
    PROJECTS_URL = "https://app.dataannotation.tech/work-on"

    # Selectors (multiple variants for robustness)
    LOGIN_SELECTORS = {
        "email": [
            'input[name="email"]',
            'input[type="email"]',
            'input[placeholder*="email" i]',
            "#email",
        ],
        "password": [
            'input[name="password"]',
            'input[type="password"]',
            "#password",
        ],
        "submit": [
            'button[type="submit"]',
            'button:has-text("Log in")',
            'button:has-text("Sign in")',
            'button:has-text("Login")',
            'input[type="submit"]',
        ],
    }

    PROJECT_SELECTORS = {
        "project_card": [
            '[data-testid="project-card"]',
            ".project-card",
            '[class*="ProjectCard"]',
            ".task-card",
        ],
        "project_title": [
            '[data-testid="project-title"]',
            ".project-title",
            "h3",
            ".title",
        ],
        "project_link": [
            'a[href*="/work-on/"]',
            'a[href*="/project/"]',
            'button:has-text("Start")',
        ],
    }

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.email = self.config.get("email") or os.getenv("DATAANNOTATION_EMAIL")
        self.password = self.config.get("password") or os.getenv("DATAANNOTATION_PASSWORD")
        self.base_url = self.config.get("base_url", self.BASE_URL)
        self.timeout = self.config.get("timeout", 30000)
        self.headless = self.config.get("headless", True)

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        """Execute an action on DataAnnotation platform."""
        if BrowserAgent is None:
            return ExecutionResult(False, action, "", error="playwright not installed")

        try:
            if action == "login":
                return await self.login()
            if action == "fetch_projects":
                return await self.fetch_projects()
            if action == "submit_response":
                return await self.submit_response(kwargs.get("project_id", ""), kwargs.get("response", {}))
            if action == "health_check":
                return await self.health_check()
            return ExecutionResult(False, action, "", error=f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"DataAnnotation {action} error: {e}", exc_info=True)
            return ExecutionResult(False, action, "", error=str(e))

    async def login(self) -> ExecutionResult:
        """Real login to DataAnnotation with robust error handling."""
        if not self.email or not self.password:
            return ExecutionResult(False, "login", "", error="DATAANNOTATION_EMAIL/PASSWORD not configured")

        agent_config = {**self.config, "headless": self.headless}
        async with BrowserAgent(agent_config) as agent:
            # Navigate to login page
            result = await agent.goto(self.LOGIN_URL, wait_until="networkidle")
            if not result.success:
                return ExecutionResult(False, "login", self.LOGIN_URL, error=result.error)

            try:
                # Wait for page to load
                await asyncio.sleep(2)

                # Try multiple selectors for email field
                email_filled = False
                for selector in self.LOGIN_SELECTORS["email"]:
                    try:
                        await agent.wait_for_selector(selector, timeout=5000)
                        await agent.fill(selector, self.email)
                        email_filled = True
                        logger.info(f"Filled email using selector: {selector}")
                        break
                    except Exception:
                        continue

                if not email_filled:
                    return ExecutionResult(False, "login", self.LOGIN_URL, error="Could not find email input field")

                # Try multiple selectors for password field
                password_filled = False
                for selector in self.LOGIN_SELECTORS["password"]:
                    try:
                        await agent.wait_for_selector(selector, timeout=5000)
                        await agent.fill(selector, self.password)
                        password_filled = True
                        logger.info(f"Filled password using selector: {selector}")
                        break
                    except Exception:
                        continue

                if not password_filled:
                    return ExecutionResult(False, "login", self.LOGIN_URL, error="Could not find password input field")

                # Try multiple selectors for submit button
                submit_clicked = False
                for selector in self.LOGIN_SELECTORS["submit"]:
                    try:
                        await agent.wait_for_selector(selector, timeout=5000)
                        await agent.click(selector, wait_for_navigation=True)
                        submit_clicked = True
                        logger.info(f"Clicked submit using selector: {selector}")
                        break
                    except Exception:
                        continue

                if not submit_clicked:
                    return ExecutionResult(False, "login", self.LOGIN_URL, error="Could not find submit button")

                # Wait for navigation and check for success
                await asyncio.sleep(3)

                # Check if we're still on login page (login failed)
                current_url = agent._page.url if agent._page else ""
                if "login" in current_url.lower():
                    return ExecutionResult(False, "login", current_url, error="Login failed - still on login page")

                # Check for CAPTCHA or 2FA
                page_content = await agent._page.content() if agent._page else ""
                if "captcha" in page_content.lower() or "2fa" in page_content.lower():
                    return ExecutionResult(
                        False, "login", current_url, error="CAPTCHA or 2FA detected - manual intervention required"
                    )

                return ExecutionResult(True, "login", current_url, message="Successfully logged in to DataAnnotation")

            except TimeoutError:
                return ExecutionResult(False, "login", self.LOGIN_URL, error="Login timeout after 30 seconds")
            except Exception as e:
                return ExecutionResult(False, "login", self.LOGIN_URL, error=f"Login error: {str(e)}")

    async def fetch_projects(self) -> ExecutionResult:
        """Fetch available projects from DataAnnotation with real scraping."""
        agent_config = {**self.config, "headless": self.headless}
        async with BrowserAgent(agent_config) as agent:
            # Navigate to projects page
            result = await agent.goto(self.PROJECTS_URL, wait_until="networkidle")
            if not result.success:
                return ExecutionResult(False, "fetch_projects", self.PROJECTS_URL, error=result.error)

            try:
                # Wait for page to load
                await asyncio.sleep(3)

                projects = []

                # Try multiple selectors for project cards
                for card_selector in self.PROJECT_SELECTORS["project_card"]:
                    try:
                        await agent.wait_for_selector(card_selector, timeout=5000)
                        cards = await agent._page.query_selector_all(card_selector)

                        for idx, card in enumerate(cards):
                            try:
                                # Extract project title
                                title = "Unknown Project"
                                for title_selector in self.PROJECT_SELECTORS["project_title"]:
                                    try:
                                        title_elem = await card.query_selector(title_selector)
                                        if title_elem:
                                            title = await title_elem.text_content()
                                            if title and title.strip():
                                                break
                                    except Exception:
                                        continue

                                # Extract project link/ID
                                link_elem = await card.query_selector("a")
                                project_id = None
                                if link_elem:
                                    href = await link_elem.get_attribute("href")
                                    if href:
                                        # Extract ID from URL
                                        parts = href.split("/")
                                        project_id = parts[-1] if parts else str(idx)

                                # Extract other metadata if available
                                description = ""
                                desc_elem = await card.query_selector('[class*="description"], p')
                                if desc_elem:
                                    description = await desc_elem.text_content()

                                projects.append(
                                    {
                                        "id": project_id or f"project_{idx}",
                                        "title": title.strip() if title else f"Project {idx}",
                                        "description": description.strip() if description else "",
                                        "url": f"{self.base_url}{href}" if href else None,
                                    }
                                )
                            except Exception as e:
                                logger.warning(f"Error extracting project {idx}: {e}")
                                continue

                        if projects:
                            logger.info(f"Found {len(projects)} projects using selector: {card_selector}")
                            break
                    except Exception:
                        continue

                if not projects:
                    # Fallback: try to extract any clickable elements
                    logger.warning("No projects found with standard selectors, trying fallback")
                    try:
                        all_links = await agent._page.query_selector_all("a[href]")
                        for link in all_links:
                            href = await link.get_attribute("href")
                            text = await link.text_content()
                            if href and ("work-on" in href or "project" in href) and text:
                                projects.append(
                                    {
                                        "id": href.split("/")[-1],
                                        "title": text.strip(),
                                        "description": "",
                                        "url": f"{self.base_url}{href}" if href.startswith("/") else href,
                                    }
                                )
                    except Exception as e:
                        logger.warning(f"Fallback extraction failed: {e}")

                return ExecutionResult(
                    True,
                    "fetch_projects",
                    self.PROJECTS_URL,
                    data={"projects": projects, "count": len(projects)},
                    message=f"Found {len(projects)} projects",
                )

            except TimeoutError:
                return ExecutionResult(False, "fetch_projects", self.PROJECTS_URL, error="Fetch projects timeout")
            except Exception as e:
                return ExecutionResult(
                    False, "fetch_projects", self.PROJECTS_URL, error=f"Fetch projects error: {str(e)}"
                )

    async def submit_response(self, project_id: str, response: dict[str, Any]) -> ExecutionResult:
        """Submit a response to a DataAnnotation project."""
        if not project_id:
            return ExecutionResult(False, "submit_response", "", error="project_id is required")

        agent_config = {**self.config, "headless": self.headless}
        async with BrowserAgent(agent_config) as agent:
            # Navigate to project page
            project_url = f"{self.base_url}/work-on/{project_id}"
            result = await agent.goto(project_url, wait_until="networkidle")
            if not result.success:
                return ExecutionResult(False, "submit_response", project_url, error=result.error)

            try:
                # Wait for page to load
                await asyncio.sleep(2)

                # Try to find and click start button if needed
                start_selectors = [
                    'button:has-text("Start")',
                    'button:has-text("Begin")',
                    'button:has-text("Continue")',
                    '[data-testid="start-button"]',
                ]
                for selector in start_selectors:
                    try:
                        await agent.wait_for_selector(selector, timeout=3000)
                        await agent.click(selector, wait_for_navigation=True)
                        await asyncio.sleep(2)
                        break
                    except Exception:
                        continue

                # Fill form fields based on response data
                for field_name, field_value in response.items():
                    if not field_value:
                        continue

                    # Try different input selectors
                    input_selectors = [
                        f'input[name="{field_name}"]',
                        f'textarea[name="{field_name}"]',
                        f"#{field_name}",
                        f'[data-testid="{field_name}"]',
                        f'input[placeholder*="{field_name}" i]',
                    ]

                    filled = False
                    for selector in input_selectors:
                        try:
                            await agent.wait_for_selector(selector, timeout=2000)
                            await agent.fill(selector, str(field_value))
                            filled = True
                            logger.info(f"Filled field {field_name} using selector: {selector}")
                            break
                        except Exception:
                            continue

                    if not filled:
                        logger.warning(f"Could not fill field: {field_name}")

                # Try to find and click submit button
                submit_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("Save")',
                    'button:has-text("Continue")',
                    '[data-testid="submit-button"]',
                ]

                submitted = False
                for selector in submit_selectors:
                    try:
                        await agent.wait_for_selector(selector, timeout=3000)
                        await agent.click(selector, wait_for_navigation=True)
                        submitted = True
                        logger.info(f"Submitted using selector: {selector}")
                        break
                    except Exception:
                        continue

                if not submitted:
                    return ExecutionResult(False, "submit_response", project_url, error="Could not find submit button")

                # Wait for submission to complete
                await asyncio.sleep(2)

                return ExecutionResult(
                    True,
                    "submit_response",
                    project_url,
                    data={"project_id": project_id, "response": response},
                    message=f"Response submitted for project {project_id}",
                )

            except TimeoutError:
                return ExecutionResult(False, "submit_response", project_url, error="Submit response timeout")
            except Exception as e:
                return ExecutionResult(False, "submit_response", project_url, error=f"Submit response error: {str(e)}")

    async def health_check(self) -> ExecutionResult:
        """Check if DataAnnotation platform is accessible."""
        agent_config = {**self.config, "headless": self.headless}
        async with BrowserAgent(agent_config) as agent:
            try:
                result = await agent.goto(self.base_url, wait_until="domcontentloaded")
                if not result.success:
                    return ExecutionResult(
                        False, "health_check", self.base_url, error=f"Navigation failed: {result.error}"
                    )

                # Check if page loaded successfully
                page_content = await agent._page.content() if agent._page else ""
                if not page_content or len(page_content) < 100:
                    return ExecutionResult(
                        False, "health_check", self.base_url, error="Page content is empty or too short"
                    )

                # Check for common error indicators
                if "error" in page_content.lower() or "503" in page_content or "502" in page_content:
                    return ExecutionResult(False, "health_check", self.base_url, error="Platform returned error page")

                return ExecutionResult(
                    True, "health_check", self.base_url, message="DataAnnotation platform is accessible"
                )

            except Exception as e:
                return ExecutionResult(False, "health_check", self.base_url, error=f"Health check error: {str(e)}")


class OutlierWorker(BaseExecutor):
    """Worker for Outlier.org — real login, fetch projects, submit work."""

    platform = "outlier"

    # Platform-specific configuration
    BASE_URL = "https://outlier.org"
    LOGIN_URL = "https://outlier.org/login"
    PROJECTS_URL = "https://outlier.org/projects"
    DASHBOARD_URL = "https://outlier.org/dashboard"

    # Selectors (multiple variants for robustness)
    LOGIN_SELECTORS = {
        "email": [
            'input[name="email"]',
            'input[type="email"]',
            'input[placeholder*="email" i]',
            "#email",
            "#user_email",
        ],
        "password": [
            'input[name="password"]',
            'input[type="password"]',
            "#password",
            "#user_password",
        ],
        "submit": [
            'button[type="submit"]',
            'button:has-text("Log in")',
            'button:has-text("Sign in")',
            'button:has-text("Login")',
            'input[type="submit"]',
            '[value="Log in"]',
        ],
    }

    PROJECT_SELECTORS = {
        "project_card": [
            '[data-testid="project-card"]',
            ".project-card",
            '[class*="ProjectCard"]',
            ".job-card",
            '[class*="JobCard"]',
            ".task-card",
        ],
        "project_title": [
            '[data-testid="project-title"]',
            ".project-title",
            ".job-title",
            "h3",
            "h4",
            ".title",
        ],
        "project_link": [
            'a[href*="/projects/"]',
            'a[href*="/jobs/"]',
            'button:has-text("Start")',
            'button:has-text("Begin")',
        ],
    }

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.email = self.config.get("email") or os.getenv("OUTLIER_EMAIL")
        self.password = self.config.get("password") or os.getenv("OUTLIER_PASSWORD")
        self.base_url = self.config.get("base_url", self.BASE_URL)
        self.timeout = self.config.get("timeout", 30000)
        self.headless = self.config.get("headless", True)

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        """Execute an action on Outlier platform."""
        if BrowserAgent is None:
            return ExecutionResult(False, action, "", error="playwright not installed")

        try:
            if action == "login":
                return await self.login()
            if action == "fetch_projects":
                return await self.fetch_projects()
            if action == "submit_work":
                return await self.submit_work(kwargs.get("project_id", ""), kwargs.get("work", {}))
            if action == "health_check":
                return await self.health_check()
            return ExecutionResult(False, action, "", error=f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Outlier {action} error: {e}", exc_info=True)
            return ExecutionResult(False, action, "", error=str(e))

    async def login(self) -> ExecutionResult:
        """Real login to Outlier with robust error handling."""
        if not self.email or not self.password:
            return ExecutionResult(False, "login", "", error="OUTLIER_EMAIL/PASSWORD not configured")

        agent_config = {**self.config, "headless": self.headless}
        async with BrowserAgent(agent_config) as agent:
            # Navigate to login page
            result = await agent.goto(self.LOGIN_URL, wait_until="networkidle")
            if not result.success:
                return ExecutionResult(False, "login", self.LOGIN_URL, error=result.error)

            try:
                # Wait for page to load
                await asyncio.sleep(2)

                # Try multiple selectors for email field
                email_filled = False
                for selector in self.LOGIN_SELECTORS["email"]:
                    try:
                        await agent.wait_for_selector(selector, timeout=5000)
                        await agent.fill(selector, self.email)
                        email_filled = True
                        logger.info(f"Filled email using selector: {selector}")
                        break
                    except Exception:
                        continue

                if not email_filled:
                    return ExecutionResult(False, "login", self.LOGIN_URL, error="Could not find email input field")

                # Try multiple selectors for password field
                password_filled = False
                for selector in self.LOGIN_SELECTORS["password"]:
                    try:
                        await agent.wait_for_selector(selector, timeout=5000)
                        await agent.fill(selector, self.password)
                        password_filled = True
                        logger.info(f"Filled password using selector: {selector}")
                        break
                    except Exception:
                        continue

                if not password_filled:
                    return ExecutionResult(False, "login", self.LOGIN_URL, error="Could not find password input field")

                # Try multiple selectors for submit button
                submit_clicked = False
                for selector in self.LOGIN_SELECTORS["submit"]:
                    try:
                        await agent.wait_for_selector(selector, timeout=5000)
                        await agent.click(selector, wait_for_navigation=True)
                        submit_clicked = True
                        logger.info(f"Clicked submit using selector: {selector}")
                        break
                    except Exception:
                        continue

                if not submit_clicked:
                    return ExecutionResult(False, "login", self.LOGIN_URL, error="Could not find submit button")

                # Wait for navigation and check for success
                await asyncio.sleep(3)

                # Check if we're still on login page (login failed)
                current_url = agent._page.url if agent._page else ""
                if "login" in current_url.lower():
                    return ExecutionResult(False, "login", current_url, error="Login failed - still on login page")

                # Check for CAPTCHA or 2FA
                page_content = await agent._page.content() if agent._page else ""
                if (
                    "captcha" in page_content.lower()
                    or "2fa" in page_content.lower()
                    or "two-factor" in page_content.lower()
                ):
                    return ExecutionResult(
                        False, "login", current_url, error="CAPTCHA or 2FA detected - manual intervention required"
                    )

                return ExecutionResult(True, "login", current_url, message="Successfully logged in to Outlier")

            except TimeoutError:
                return ExecutionResult(False, "login", self.LOGIN_URL, error="Login timeout after 30 seconds")
            except Exception as e:
                return ExecutionResult(False, "login", self.LOGIN_URL, error=f"Login error: {str(e)}")

    async def fetch_projects(self) -> ExecutionResult:
        """Fetch available projects from Outlier with real scraping."""
        agent_config = {**self.config, "headless": self.headless}
        async with BrowserAgent(agent_config) as agent:
            # Try dashboard first, then projects page
            result = await agent.goto(self.DASHBOARD_URL, wait_until="networkidle")
            if not result.success:
                # Fallback to projects page
                result = await agent.goto(self.PROJECTS_URL, wait_until="networkidle")
                if not result.success:
                    return ExecutionResult(False, "fetch_projects", self.PROJECTS_URL, error=result.error)

            try:
                # Wait for page to load
                await asyncio.sleep(3)

                projects = []

                # Try multiple selectors for project cards
                for card_selector in self.PROJECT_SELECTORS["project_card"]:
                    try:
                        await agent.wait_for_selector(card_selector, timeout=5000)
                        cards = await agent._page.query_selector_all(card_selector)

                        for idx, card in enumerate(cards):
                            try:
                                # Extract project title
                                title = "Unknown Project"
                                for title_selector in self.PROJECT_SELECTORS["project_title"]:
                                    try:
                                        title_elem = await card.query_selector(title_selector)
                                        if title_elem:
                                            title = await title_elem.text_content()
                                            if title and title.strip():
                                                break
                                    except Exception:
                                        continue

                                # Extract project link/ID
                                link_elem = await card.query_selector("a")
                                project_id = None
                                href = None
                                if link_elem:
                                    href = await link_elem.get_attribute("href")
                                    if href:
                                        # Extract ID from URL
                                        parts = href.split("/")
                                        project_id = parts[-1] if parts else str(idx)

                                # Extract other metadata if available
                                description = ""
                                desc_elem = await card.query_selector('[class*="description"], p, .subtitle')
                                if desc_elem:
                                    description = await desc_elem.text_content()

                                # Extract pay rate if available
                                pay_rate = ""
                                pay_elem = await card.query_selector(
                                    '[class*="pay"], [class*="rate"], [class*="hourly"]'
                                )
                                if pay_elem:
                                    pay_rate = await pay_elem.text_content()

                                projects.append(
                                    {
                                        "id": project_id or f"project_{idx}",
                                        "title": title.strip() if title else f"Project {idx}",
                                        "description": description.strip() if description else "",
                                        "pay_rate": pay_rate.strip() if pay_rate else "",
                                        "url": f"{self.base_url}{href}" if href and href.startswith("/") else href,
                                    }
                                )
                            except Exception as e:
                                logger.warning(f"Error extracting project {idx}: {e}")
                                continue

                        if projects:
                            logger.info(f"Found {len(projects)} projects using selector: {card_selector}")
                            break
                    except Exception:
                        continue

                if not projects:
                    # Fallback: try to extract any clickable elements
                    logger.warning("No projects found with standard selectors, trying fallback")
                    try:
                        all_links = await agent._page.query_selector_all("a[href]")
                        for link in all_links:
                            href = await link.get_attribute("href")
                            text = await link.text_content()
                            if href and ("project" in href or "job" in href) and text:
                                projects.append(
                                    {
                                        "id": href.split("/")[-1],
                                        "title": text.strip(),
                                        "description": "",
                                        "pay_rate": "",
                                        "url": f"{self.base_url}{href}" if href.startswith("/") else href,
                                    }
                                )
                    except Exception as e:
                        logger.warning(f"Fallback extraction failed: {e}")

                return ExecutionResult(
                    True,
                    "fetch_projects",
                    self.DASHBOARD_URL,
                    data={"projects": projects, "count": len(projects)},
                    message=f"Found {len(projects)} projects",
                )

            except TimeoutError:
                return ExecutionResult(False, "fetch_projects", self.DASHBOARD_URL, error="Fetch projects timeout")
            except Exception as e:
                return ExecutionResult(
                    False, "fetch_projects", self.DASHBOARD_URL, error=f"Fetch projects error: {str(e)}"
                )

    async def submit_work(self, project_id: str, work: dict[str, Any]) -> ExecutionResult:
        """Submit work to an Outlier project."""
        if not project_id:
            return ExecutionResult(False, "submit_work", "", error="project_id is required")

        agent_config = {**self.config, "headless": self.headless}
        async with BrowserAgent(agent_config) as agent:
            # Navigate to project page
            project_url = f"{self.base_url}/projects/{project_id}"
            result = await agent.goto(project_url, wait_until="networkidle")
            if not result.success:
                return ExecutionResult(False, "submit_work", project_url, error=result.error)

            try:
                # Wait for page to load
                await asyncio.sleep(2)

                # Try to find and click start button if needed
                start_selectors = [
                    'button:has-text("Start")',
                    'button:has-text("Begin")',
                    'button:has-text("Continue")',
                    'button:has-text("Accept")',
                    '[data-testid="start-button"]',
                ]
                for selector in start_selectors:
                    try:
                        await agent.wait_for_selector(selector, timeout=3000)
                        await agent.click(selector, wait_for_navigation=True)
                        await asyncio.sleep(2)
                        break
                    except Exception:
                        continue

                # Fill form fields based on work data
                for field_name, field_value in work.items():
                    if not field_value:
                        continue

                    # Try different input selectors
                    input_selectors = [
                        f'input[name="{field_name}"]',
                        f'textarea[name="{field_name}"]',
                        f"#{field_name}",
                        f'[data-testid="{field_name}"]',
                        f'input[placeholder*="{field_name}" i]',
                        f'textarea[placeholder*="{field_name}" i]',
                    ]

                    filled = False
                    for selector in input_selectors:
                        try:
                            await agent.wait_for_selector(selector, timeout=2000)
                            await agent.fill(selector, str(field_value))
                            filled = True
                            logger.info(f"Filled field {field_name} using selector: {selector}")
                            break
                        except Exception:
                            continue

                    if not filled:
                        logger.warning(f"Could not fill field: {field_name}")

                # Try to find and click submit button
                submit_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("Save")',
                    'button:has-text("Continue")',
                    'button:has-text("Complete")',
                    '[data-testid="submit-button"]',
                ]

                submitted = False
                for selector in submit_selectors:
                    try:
                        await agent.wait_for_selector(selector, timeout=3000)
                        await agent.click(selector, wait_for_navigation=True)
                        submitted = True
                        logger.info(f"Submitted using selector: {selector}")
                        break
                    except Exception:
                        continue

                if not submitted:
                    return ExecutionResult(False, "submit_work", project_url, error="Could not find submit button")

                # Wait for submission to complete
                await asyncio.sleep(2)

                return ExecutionResult(
                    True,
                    "submit_work",
                    project_url,
                    data={"project_id": project_id, "work": work},
                    message=f"Work submitted for project {project_id}",
                )

            except TimeoutError:
                return ExecutionResult(False, "submit_work", project_url, error="Submit work timeout")
            except Exception as e:
                return ExecutionResult(False, "submit_work", project_url, error=f"Submit work error: {str(e)}")

    async def health_check(self) -> ExecutionResult:
        """Check if Outlier platform is accessible."""
        agent_config = {**self.config, "headless": self.headless}
        async with BrowserAgent(agent_config) as agent:
            try:
                result = await agent.goto(self.base_url, wait_until="domcontentloaded")
                if not result.success:
                    return ExecutionResult(
                        False, "health_check", self.base_url, error=f"Navigation failed: {result.error}"
                    )

                # Check if page loaded successfully
                page_content = await agent._page.content() if agent._page else ""
                if not page_content or len(page_content) < 100:
                    return ExecutionResult(
                        False, "health_check", self.base_url, error="Page content is empty or too short"
                    )

                # Check for common error indicators
                if "error" in page_content.lower() or "503" in page_content or "502" in page_content:
                    return ExecutionResult(False, "health_check", self.base_url, error="Platform returned error page")

                return ExecutionResult(True, "health_check", self.base_url, message="Outlier platform is accessible")

            except Exception as e:
                return ExecutionResult(False, "health_check", self.base_url, error=f"Health check error: {str(e)}")


class MindriftBrowserWorker(BaseExecutor):
    """Worker for Mindrift.com — login, fetch projects, submit responses (browser-based)."""

    platform = "mindrift_browser"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.email = self.config.get("email") or os.getenv("MINDRIFT_BROWSER_EMAIL")
        self.password = self.config.get("password") or os.getenv("MINDRIFT_BROWSER_PASSWORD")
        self.base_url = self.config.get("base_url", "https://mindrift.com")

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        if BrowserAgent is None:
            return ExecutionResult(False, action, "", error="playwright not installed")

        if action == "login":
            return await self.login()
        if action == "fetch_projects":
            return await self.fetch_projects()
        if action == "submit_response":
            return await self.submit_response(kwargs.get("project_id", ""), kwargs.get("response", {}))
        if action == "health_check":
            return await self.health_check()
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def login(self) -> ExecutionResult:
        if not self.email or not self.password:
            return ExecutionResult(False, "login", "", error="MINDRIFT_BROWSER_EMAIL/PASSWORD not configured")

        async with BrowserAgent(self.config) as agent:
            result = await agent.goto(f"{self.base_url}/login")
            if not result.success:
                return ExecutionResult(False, "login", "", error=result.error)

            await agent._page.fill('input[name="email"]', self.email)
            await agent._page.fill('input[name="password"]', self.password)
            await agent._page.click('button[type="submit"]')
            await agent._page.wait_for_load_state("networkidle")

            return ExecutionResult(True, "login", "", message="Logged in to Mindrift")

    async def fetch_projects(self) -> ExecutionResult:
        async with BrowserAgent(self.config) as agent:
            result = await agent.goto(f"{self.base_url}/projects")
            if not result.success:
                return ExecutionResult(False, "fetch_projects", "", error=result.error)

            projects = await agent._page.query_selector_all(".project-card")
            project_data = [{"id": i, "title": await project.text_content()} for i, project in enumerate(projects)]

            return ExecutionResult(
                True, "fetch_projects", "", data={"projects": project_data, "count": len(project_data)}
            )

    async def submit_response(self, project_id: str, response: dict[str, Any]) -> ExecutionResult:
        async with BrowserAgent(self.config) as agent:
            result = await agent.goto(f"{self.base_url}/projects/{project_id}")
            if not result.success:
                return ExecutionResult(False, "submit_response", project_id, error=result.error)

            await agent._page.click('button[type="submit"]')
            await agent._page.wait_for_load_state("networkidle")

            return ExecutionResult(True, "submit_response", project_id, data={"response": response})

    async def health_check(self) -> ExecutionResult:
        async with BrowserAgent(self.config) as agent:
            result = await agent.goto(self.base_url)
            return ExecutionResult(result.success, "health_check", self.base_url)


class RemotasksWorker(BaseExecutor):
    """Worker for Remotasks.com — login, fetch tasks, submit results."""

    platform = "remotasks"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.email = self.config.get("email") or os.getenv("REMOTASKS_EMAIL")
        self.password = self.config.get("password") or os.getenv("REMOTASKS_PASSWORD")
        self.base_url = self.config.get("base_url", "https://remotasks.com")

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        if BrowserAgent is None:
            return ExecutionResult(False, action, "", error="playwright not installed")

        if action == "login":
            return await self.login()
        if action == "fetch_tasks":
            return await self.fetch_tasks()
        if action == "submit_result":
            return await self.submit_result(kwargs.get("task_id", ""), kwargs.get("result", {}))
        if action == "health_check":
            return await self.health_check()
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def login(self) -> ExecutionResult:
        if not self.email or not self.password:
            return ExecutionResult(False, "login", "", error="REMOTASKS_EMAIL/PASSWORD not configured")

        async with BrowserAgent(self.config) as agent:
            result = await agent.goto(f"{self.base_url}/login")
            if not result.success:
                return ExecutionResult(False, "login", "", error=result.error)

            await agent._page.fill('input[name="email"]', self.email)
            await agent._page.fill('input[name="password"]', self.password)
            await agent._page.click('button[type="submit"]')
            await agent._page.wait_for_load_state("networkidle")

            return ExecutionResult(True, "login", "", message="Logged in to Remotasks")

    async def fetch_tasks(self) -> ExecutionResult:
        async with BrowserAgent(self.config) as agent:
            result = await agent.goto(f"{self.base_url}/tasks")
            if not result.success:
                return ExecutionResult(False, "fetch_tasks", "", error=result.error)

            tasks = await agent._page.query_selector_all(".task-card")
            task_data = [{"id": i, "title": await task.text_content()} for i, task in enumerate(tasks)]

            return ExecutionResult(True, "fetch_tasks", "", data={"tasks": task_data, "count": len(task_data)})

    async def submit_result(self, task_id: str, result_data: dict[str, Any]) -> ExecutionResult:
        async with BrowserAgent(self.config) as agent:
            nav_result = await agent.goto(f"{self.base_url}/tasks/{task_id}")
            if not nav_result.success:
                return ExecutionResult(False, "submit_result", task_id, error=nav_result.error)

            await agent._page.click('button[type="submit"]')
            await agent._page.wait_for_load_state("networkidle")

            return ExecutionResult(True, "submit_result", task_id, data={"result": result_data})

    async def health_check(self) -> ExecutionResult:
        async with BrowserAgent(self.config) as agent:
            result = await agent.goto(self.base_url)
            return ExecutionResult(result.success, "health_check", self.base_url)


__all__ = [
    "DataAnnotationWorker",
    "OutlierWorker",
    "MindriftBrowserWorker",
    "RemotasksWorker",
]
