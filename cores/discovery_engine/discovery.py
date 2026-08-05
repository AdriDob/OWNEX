"""
Discovery Engine - Core crawler for discovering new platforms.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from cores.memory.system import MemoryNamespace, MemoryTier, get_memory_store

logger = logging.getLogger("ownex.discovery")


@dataclass
class DiscoveryConfig:
    """Configuration for discovery engine."""

    max_concurrent_requests: int = 10
    request_timeout: int = 30
    user_agent: str = "OWNEX-Discovery/1.0 (+https://ownex.ai/bot)"
    respect_robots_txt: bool = True
    max_depth: int = 3
    allowed_domains: list[str] = field(default_factory=list)
    blocked_domains: list[str] = field(default_factory=list)
    min_content_length: int = 500
    languages: list[str] = field(default_factory=lambda: ["en", "es"])


@dataclass
class DiscoveredPlatform:
    """A discovered platform candidate."""

    url: str
    title: str
    description: str
    domain: str
    content_hash: str
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_url: str = ""
    raw_html: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class DiscoveryEngine:
    """Main discovery engine for crawling and finding new platforms."""

    def __init__(self, config: DiscoveryConfig | None = None):
        self.config = config or DiscoveryConfig()
        self.memory = get_memory_store()
        self._session: aiohttp.ClientSession | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._visited_urls: set[str] = set()
        self._discovered_platforms: list[DiscoveredPlatform] = []

    async def __aenter__(self):
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
        self._session = aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": self.config.user_agent})
        await self._load_visited_urls()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def _load_visited_urls(self):
        """Load previously visited URLs from memory."""
        data = self.memory.get(MemoryNamespace.OPPORTUNITIES, "discovery_visited_urls")
        if data and isinstance(data, list):
            self._visited_urls = set(data)
        logger.info(f"Loaded {len(self._visited_urls)} previously visited URLs")

    async def _save_visited_urls(self):
        """Save visited URLs to memory."""
        self.memory.set(
            MemoryNamespace.OPPORTUNITIES,
            "discovery_visited_urls",
            list(self._visited_urls),
            tier=MemoryTier.PERMANENT,
            tags=["discovery", "visited_urls"],
        )

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        parsed = urlparse(url.lower())
        # Remove fragment and query parameters for base URL
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        # Remove trailing slash
        normalized = normalized.rstrip("/")
        return normalized

    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _is_allowed_domain(self, url: str) -> bool:
        """Check if domain is allowed."""
        domain = urlparse(url).netloc.lower()
        if self.config.blocked_domains and any(b in domain for b in self.config.blocked_domains):
            return False
        if self.config.allowed_domains and not any(a in domain for a in self.config.allowed_domains):
            return False
        return True

    async def _fetch(self, url: str) -> tuple[str, int] | None:
        """Fetch URL content."""
        if not self._is_allowed_domain(url):
            return None

        normalized = self._normalize_url(url)
        if normalized in self._visited_urls:
            return None

        self._visited_urls.add(normalized)

        async with self._semaphore:
            try:
                async with self._session.get(url) as response:
                    if response.status != 200:
                        return None
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" not in content_type:
                        return None
                    text = await response.text()
                    if len(text) < self.config.min_content_length:
                        return None
                    return text, response.status
            except Exception as e:
                logger.debug(f"Fetch failed for {url}: {e}")
                return None

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract all links from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.scheme in ("http", "https"):
                links.append(full_url)
        return links

    def _extract_platform_info(self, html: str, url: str) -> DiscoveredPlatform | None:
        """Extract platform information from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Get title
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else ""

        # Get description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if not desc_tag:
            desc_tag = soup.find("meta", attrs={"property": "og:description"})
        description = desc_tag.get("content", "").strip() if desc_tag else ""

        # Fallback to first paragraph
        if not description:
            p_tag = soup.find("p")
            if p_tag:
                description = p_tag.get_text().strip()[:500]

        if not title or len(title) < 3:
            return None

        domain = urlparse(url).netloc
        content_hash = self._get_content_hash(html)

        return DiscoveredPlatform(
            url=url,
            title=title,
            description=description,
            domain=domain,
            content_hash=content_hash,
            source_url=url,
            raw_html=html[:10000],  # Store first 10k chars
        )

    async def discover_from_seed(self, seed_urls: list[str]) -> list[DiscoveredPlatform]:
        """Discover platforms starting from seed URLs."""
        self._discovered_platforms = []

        # BFS crawl
        queue = [(url, 0) for url in seed_urls]

        while queue:
            url, depth = queue.pop(0)
            if depth > self.config.max_depth:
                continue

            result = await self._fetch(url)
            if not result:
                continue

            html, status = result
            platform = self._extract_platform_info(html, url)
            if platform:
                self._discovered_platforms.append(platform)
                logger.info(f"Discovered: {platform.title} ({platform.domain})")

            # Extract links for next depth
            if depth < self.config.max_depth:
                links = self._extract_links(html, url)
                for link in links[:20]:  # Limit links per page
                    queue.append((link, depth + 1))

            # Rate limiting
            await asyncio.sleep(0.5)

        await self._save_visited_urls()
        return self._discovered_platforms

    async def discover_from_search(self, queries: list[str], max_results: int = 50) -> list[DiscoveredPlatform]:
        """Discover platforms using search queries (placeholder for search API integration)."""
        # This would integrate with search APIs (Google, Bing, DuckDuckGo, etc.)
        # For now, return empty - to be implemented with search API keys
        logger.warning("Search-based discovery not yet implemented - requires search API")
        return []


async def run_discovery(seed_urls: list[str] | None = None) -> list[DiscoveredPlatform]:
    """Run discovery engine with default configuration."""
    default_seeds = [
        "https://github.com/topics/bug-bounty",
        "https://github.com/topics/hacktoberfest",
        "https://www.reddit.com/r/bugbounty/",
        "https://www.reddit.com/r/freelance/",
        "https://news.ycombinator.com/",
        "https://www.producthunt.com/",
        "https://www.indiehackers.com/",
    ]

    seeds = seed_urls or default_seeds

    config = DiscoveryConfig()
    async with DiscoveryEngine(config) as engine:
        return await engine.discover_from_seed(seeds)
