from __future__ import annotations

import logging
import uuid
from typing import Any

from core.revenue_multiplier.config import RevenueMultiplierConfig
from core.revenue_multiplier.models import Finding
from core.revenue_multiplier.tool_registry import ToolRegistry, get_tool_registry

logger = logging.getLogger("orion.revenue.bugbounty")


class BugBountyHunter:
    def __init__(self, config: RevenueMultiplierConfig, tool_registry: ToolRegistry | None = None) -> None:
        self._config = config
        self._registry = tool_registry or get_tool_registry()
        self._findings: list[Finding] = []
        self._pipeline: dict[str, Any] = {}

    @property
    def findings(self) -> list[Finding]:
        return list(self._findings)

    def run_full_pipeline(self, domain: str) -> list[Finding]:
        logger.info("Bug bounty pipeline starting for %s", domain)
        session_id = uuid.uuid4().hex[:12]
        self._findings.clear()

        try:
            self._stage_subdomains(domain)
            self._stage_urls(domain)
            self._stage_crawl(domain)
            self._stage_scan(domain)
            self._stage_fuzz(domain)
            self._stage_exploit(domain)
            self._stage_secrets(domain)
            self._deduplicate()
        except Exception as e:
            logger.exception("Pipeline failed for %s: %s", domain, e)

        self._log_summary(domain, session_id)
        return self._findings

    def _stage_subdomains(self, domain: str) -> None:
        logger.info("Stage 1/7: Subdomain discovery — %s", domain)
        for tool_name in ("subfinder", "assetfinder"):
            adapter = self._get_adapter(tool_name)
            if not adapter:
                continue
            try:
                results = adapter.run(domain)
                self._findings.extend(results)
                logger.info("  %s: %d results", tool_name, len(results))
            except Exception as e:
                logger.warning("  %s failed: %s", tool_name, e)

    def _stage_urls(self, domain: str) -> None:
        logger.info("Stage 2/7: URL gathering — %s", domain)
        for tool_name in ("gau",):
            adapter = self._get_adapter(tool_name)
            if not adapter:
                continue
            try:
                results = adapter.run(domain)
                self._findings.extend(results)
                logger.info("  %s: %d URLs", tool_name, len(results))
            except Exception as e:
                logger.warning("  %s failed: %s", tool_name, e)

    def _stage_crawl(self, domain: str) -> None:
        logger.info("Stage 3/7: Crawling — %s", domain)
        for tool_name in ("katana",):
            adapter = self._get_adapter(tool_name)
            if not adapter:
                continue
            try:
                results = adapter.run(domain, depth=2, rate_limit=30)
                self._findings.extend(results)
                logger.info("  %s: %d endpoints", tool_name, len(results))
            except Exception as e:
                logger.warning("  %s failed: %s", tool_name, e)

    def _stage_scan(self, domain: str) -> None:
        logger.info("Stage 4/7: Vulnerability scanning — %s", domain)
        adapter = self._get_adapter("nuclei")
        if adapter:
            try:
                results = adapter.run(domain, severity="critical,high,medium", rate_limit=50)
                self._findings.extend(results)
                logger.info("  nuclei: %d findings", len(results))
            except Exception as e:
                logger.warning("  nuclei failed: %s", e)

    def _stage_fuzz(self, domain: str) -> None:
        logger.info("Stage 5/7: Fuzzing — %s", domain)
        endpoints = [
            f"https://{domain}/FUZZ",
            f"https://www.{domain}/FUZZ",
        ]
        for endpoint in endpoints:
            adapter = self._get_adapter("ffuf")
            if not adapter:
                continue
            try:
                results = adapter.run(endpoint, rate_limit=50)
                self._findings.extend(results)
                logger.info("  ffuf: %d endpoints on %s", len(results), endpoint)
            except Exception as e:
                logger.warning("  ffuf failed for %s: %s", endpoint, e)

    def _stage_exploit(self, domain: str) -> None:
        logger.info("Stage 6/7: Exploit testing — %s", domain)
        live_endpoints = [
            f"https://{domain}/",
            f"https://www.{domain}/",
        ]
        for endpoint in live_endpoints:
            for tool_name in ("sqlmap",):
                adapter = self._get_adapter(tool_name)
                if not adapter:
                    continue
                try:
                    results = adapter.run(endpoint, level=3, risk=2)
                    self._findings.extend(results)
                    if results:
                        logger.warning("  %s: %d findings!", tool_name, len(results))
                except Exception as e:
                    logger.warning("  %s failed: %s", tool_name, e)

    def _stage_secrets(self, domain: str) -> None:
        logger.info("Stage 7/7: Secret scanning — %s", domain)
        adapter = self._get_adapter("gitleaks")
        if adapter:
            try:
                results = adapter.run(domain, repo_path=f"https://github.com/{domain}")
                if results:
                    self._findings.extend(results)
                    logger.warning("  gitleaks: %d secrets found!", len(results))
            except Exception as e:
                logger.warning("  gitleaks failed: %s", e)

    def _deduplicate(self) -> None:
        seen: set[str] = set()
        unique: list[Finding] = []
        for f in self._findings:
            key = f"{f.tool}:{f.endpoint}:{f.title}"
            if key not in seen:
                seen.add(key)
                unique.append(f)
        self._findings = unique

    def _get_adapter(self, name: str) -> Any:
        if name == "nuclei":
            from core.revenue_multiplier.adapters.base import NucleiAdapter

            return NucleiAdapter(binary=self._config.nuclei_binary)
        if name == "katana":
            from core.revenue_multiplier.adapters.base import KatanaAdapter

            return KatanaAdapter(binary=self._config.katana_binary)
        if name == "ffuf":
            from core.revenue_multiplier.adapters.base import FfufAdapter

            return FfufAdapter(binary=self._config.ffuf_binary)
        if name == "subfinder":
            from core.revenue_multiplier.adapters.base import SubfinderAdapter

            return SubfinderAdapter(binary=self._config.subfinder_binary)
        if name == "assetfinder":
            from core.revenue_multiplier.adapters.base import SubfinderAdapter

            return SubfinderAdapter(binary="assetfinder")
        if name == "gau":
            from core.revenue_multiplier.adapters.base import GauAdapter

            return GauAdapter()
        if name == "sqlmap":
            from core.revenue_multiplier.adapters.base import SqlmapAdapter

            return SqlmapAdapter()
        if name == "xsstrike":
            from core.revenue_multiplier.adapters.base import XSStrikeAdapter

            return XSStrikeAdapter()
        if name == "gitleaks":
            from core.revenue_multiplier.adapters.base import GitleaksAdapter

            return GitleaksAdapter()
        return None

    def _log_summary(self, domain: str, session_id: str) -> None:
        by_severity: dict[str, int] = {}
        for f in self._findings:
            s = f.severity or "unknown"
            by_severity[s] = by_severity.get(s, 0) + 1
        logger.info("=" * 50)
        logger.info("Pipeline complete — %s [%s]", domain, session_id)
        logger.info("  Total findings: %d", len(self._findings))
        for sev, count in sorted(by_severity.items()):
            logger.info("    %s: %d", sev, count)
        logger.info("=" * 50)
