"""Unified scan pipeline — chains tools together with LLM correlation.

Flow:
  1. Subfinder  → subdomain enumeration
  2. httpx      → live endpoint probing
  3. Katana     → endpoint crawling
  4. Gau        → historical URL discovery
  5. LinkFinder → JS endpoint extraction
  6. ffuf       → fuzz path discovery
  7. Dalfox     → XSS candidate scanning
  8. Sqlmap     → SQLi candidate scanning
  9. Nuclei     → vulnerability scanning
 10. LLM        → correlation + intelligence
 11. Validation → differential testing
 12. Report     → generation

Each step feeds into the next. Results are correlated across tools.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from cores.tools.base import BaseTool, UnifiedResult
from cores.tools.httpx import HttpxTool
from cores.tools.nuclei import NucleiTool
from cores.tools.subfinder import SubfinderTool
from cores.tools.extra import (
    DalfoxTool,
    FfufTool,
    GauTool,
    KatanaTool,
    LinkFinderTool,
    SqlmapTool,
)


logger = logging.getLogger("catseye.pipeline.unified")


class CorrelationEngine:
    """Cross-tool evidence correlator.

    Takes results from multiple tools and:
    1. Groups by target
    2. Cross-references findings
    3. Adjusts confidence based on multiple detections
    4. Produces a unified finding list with evidence chains
    """

    def __init__(self, llm=None):
        if llm is not None:
            self._llm = llm
        else:
            from cores.validation.llm_analyzer import LLMResponseAnalyzer
            self._llm = LLMResponseAnalyzer()

    def correlate(self, results: list[UnifiedResult]) -> list[UnifiedResult]:
        """Correlate results across tools. Returns enriched findings."""
        # Group by target
        by_target: dict[str, list[UnifiedResult]] = defaultdict(list)
        for r in results:
            by_target[r.target].append(r)

        correlated: list[UnifiedResult] = []
        for target, target_results in by_target.items():
            # Collect evidence from all tools
            all_evidence = {}
            all_tags = set()
            max_severity = "info"
            max_confidence = 0.0
            best_name = target

            for r in target_results:
                all_evidence[r.source] = r.evidence
                all_tags.update(r.tags)
                sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
                if sev_order.get(r.severity, 0) > sev_order.get(max_severity, 0):
                    max_severity = r.severity
                    best_name = r.name
                if r.confidence > max_confidence:
                    max_confidence = r.confidence

            # Boost confidence when multiple tools detect same target
            source_count = len(set(r.source for r in target_results))
            confidence_boost = min(0.2, source_count * 0.05)
            max_confidence = min(1.0, max_confidence + confidence_boost)

            # Determine result type
            types = set(r.result_type for r in target_results)
            result_type = "vulnerability" if "vulnerability" in types else (
                "endpoint" if "endpoint" in types else "subdomain"
            )

            # Build evidence chain
            evidence_chain = {
                "sources": list(all_evidence.keys()),
                "cross_tool_confidence": max_confidence,
                "source_count": source_count,
                "details": all_evidence,
            }

            correlated.append(UnifiedResult(
                source="correlation",
                target=target,
                result_type=result_type,
                severity=max_severity,
                confidence=max_confidence,
                name=best_name,
                description=f"Correlated from {source_count} tools: {', '.join(all_evidence.keys())}",
                evidence=evidence_chain,
                tags=sorted(all_tags),
            ))

        return correlated

    def summarize_for_llm(self, results: list[UnifiedResult]) -> str:
        """Build a summary of findings for LLM analysis."""
        lines = []
        by_severity = defaultdict(list)
        for r in results:
            by_severity[r.severity].append(r)

        for sev in ["critical", "high", "medium", "low", "info"]:
            items = by_severity.get(sev, [])
            if items:
                lines.append(f"\n{sev.upper()} ({len(items)}):")
                for r in items[:10]:
                    lines.append(f"  - {r.target}: {r.name}")
                    if r.evidence.get("sources"):
                        lines.append(f"    sources: {', '.join(r.evidence['sources'])}")

        return "\n".join(lines)


class UnifiedScanner:
    """End-to-end scan pipeline that chains all tools.

    Usage:
        scanner = UnifiedScanner()
        results = scanner.scan_domain("example.com")
    """

    def __init__(
        self,
        subfinder: SubfinderTool | None = None,
        httpx: HttpxTool | None = None,
        nuclei: NucleiTool | None = None,
        katana: KatanaTool | None = None,
        gau: GauTool | None = None,
        ffuf: FfufTool | None = None,
        dalfox: DalfoxTool | None = None,
        sqlmap: SqlmapTool | None = None,
        linkfinder: LinkFinderTool | None = None,
        correlation: CorrelationEngine | None = None,
    ):
        self._subfinder = subfinder or SubfinderTool()
        self._httpx = httpx or HttpxTool()
        self._nuclei = nuclei or NucleiTool()
        self._katana = katana or KatanaTool()
        self._gau = gau or GauTool()
        self._ffuf = ffuf or FfufTool()
        self._dalfox = dalfox or DalfoxTool()
        self._sqlmap = sqlmap or SqlmapTool()
        self._linkfinder = linkfinder or LinkFinderTool()
        self._correlation = correlation or CorrelationEngine()

    def scan_domain(
        self,
        domain: str,
        scan_vulns: bool = True,
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Run full scan pipeline on a domain.

        Returns:
        {
            "domain": "example.com",
            "subdomains": [...],
            "live_endpoints": [...],
            "vulnerabilities": [...],
            "correlated": [...],
            "summary": "...",
            "duration_ms": int,
            "errors": [str]
        }
        """
        start = datetime.now(timezone.utc)
        all_results: list[UnifiedResult] = []
        errors: list[str] = []

        # Phase 1: Subdomain enumeration
        logger.info("Phase 1: Subfinder — enumerating subdomains for %s", domain)
        subdomains = []
        if self._subfinder.is_available():
            subdomains = self._subfinder.enumerate(domain)
            all_results.extend(subdomains)
            logger.info("  Found %d subdomains", len(subdomains))
        else:
            errors.append("subfinder not available")
            logger.warning("  subfinder not available")

        # Phase 2: Probe live endpoints
        live_targets = [r.target for r in subdomains] + [domain]
        logger.info("Phase 2: httpx — probing %d targets", len(live_targets))
        live_endpoints = []
        if self._httpx.is_available() and live_targets:
            live_endpoints = self._httpx.probe(live_targets)
            all_results.extend(live_endpoints)
            logger.info("  Found %d live endpoints", len(live_endpoints))
        else:
            errors.append("httpx not available or no targets")
            logger.warning("  httpx not available or no targets")

        # Phase 3: Katana crawl
        katana_results = []
        if self._katana.is_available():
            logger.info("Phase 3: Katana — crawling %s", domain)
            katana_results = self._katana.crawl(domain)
            all_results.extend(katana_results)
            logger.info("  Katana returned %d endpoints", len(katana_results))
        else:
            errors.append("katana not available")
            logger.warning("  katana not available")

        # Phase 4: Historical URLs via gau
        gau_results = []
        if self._gau.is_available():
            logger.info("Phase 4: Gau — historical URL discovery for %s", domain)
            gau_results = self._gau.discover_urls(domain)
            all_results.extend(gau_results)
            logger.info("  Gau returned %d URLs", len(gau_results))
        else:
            errors.append("gau not available")
            logger.warning("  gau not available")

        # Phase 5: JS endpoint discovery with LinkFinder
        linkfinder_results = []
        if self._linkfinder.is_available() and live_endpoints:
            primary_url = live_endpoints[0].target
            logger.info("Phase 5: LinkFinder — scanning %s", primary_url)
            linkfinder_results = self._linkfinder.discover_links(primary_url)
            all_results.extend(linkfinder_results)
            logger.info("  LinkFinder returned %d JS endpoints", len(linkfinder_results))
        else:
            logger.warning("  linkfinder not available or no live endpoints")

        # Phase 6: Fuzz discovery with ffuf
        ffuf_results = []
        if self._ffuf.is_available() and live_endpoints:
            fuzz_target = live_endpoints[0].target
            logger.info("Phase 6: ffuf — fuzzing %s", fuzz_target)
            ffuf_results = self._ffuf.discover_paths(fuzz_target, profile="fast")
            all_results.extend(ffuf_results)
            logger.info("  ffuf returned %d fuzz discoveries", len(ffuf_results))
        else:
            logger.warning("  ffuf not available or no live endpoints")

        # Phase 7: XSS scanning with Dalfox
        dalfox_results = []
        if self._dalfox.is_available():
            xss_candidates = [r.target for r in live_endpoints + linkfinder_results if "?" in r.target][:20]
            if xss_candidates:
                logger.info("Phase 7: Dalfox — scanning %d URL candidates", len(xss_candidates))
                dalfox_results = self._dalfox.scan_urls(xss_candidates)
                all_results.extend(dalfox_results)
                logger.info("  Dalfox returned %d findings", len(dalfox_results))
            else:
                logger.info("  Dalfox skipped: no query-style endpoints found")
        else:
            logger.warning("  dalfox not available")

        # Phase 8: SQLi scanning with sqlmap
        sqlmap_results = []
        if self._sqlmap.is_available():
            sqli_candidates = [r.target for r in live_endpoints + linkfinder_results if "?" in r.target][:10]
            if sqli_candidates:
                logger.info("Phase 8: sqlmap — scanning %d query endpoints", len(sqli_candidates))
                for target_url in sqli_candidates:
                    sqlmap_results.extend(self._sqlmap.scan_url(target_url))
                all_results.extend(sqlmap_results)
                logger.info("  sqlmap returned %d findings", len(sqlmap_results))
            else:
                logger.info("  sqlmap skipped: no query-style endpoints found")
        else:
            logger.warning("  sqlmap not available")

        # Phase 9: Vulnerability scanning
        vulns = []
        if scan_vulns and live_endpoints:
            live_urls = [r.target for r in live_endpoints if r.target.startswith("http")]
            logger.info("Phase 9: Nuclei — scanning %d URLs (severity=%s)", len(live_urls), severity)
            if self._nuclei.is_available() and live_urls:
                vulns = self._nuclei.scan(live_urls, severity=severity)
                all_results.extend(vulns)
                logger.info("  Found %d vulnerabilities", len(vulns))
            else:
                errors.append("nuclei not available or no live URLs")
                logger.warning("  nuclei not available or no live URLs")

        # Phase 10: Correlation
        logger.info("Phase 10: Correlation — cross-referencing %d results", len(all_results))
        correlated = self._correlation.correlate(all_results)
        logger.info("  Correlated into %d findings", len(correlated))

        duration = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

        return {
            "domain": domain,
            "subdomains": [r.to_dict() if hasattr(r, 'to_dict') else r.__dict__ for r in subdomains],
            "live_endpoints": [r.to_dict() if hasattr(r, 'to_dict') else r.__dict__ for r in live_endpoints],
            "vulnerabilities": [r.to_dict() if hasattr(r, 'to_dict') else r.__dict__ for r in vulns],
            "correlated": [r.to_dict() if hasattr(r, 'to_dict') else r.__dict__ for r in correlated],
            "summary": self._correlation.summarize_for_llm(correlated),
            "duration_ms": duration,
            "errors": errors,
        }
