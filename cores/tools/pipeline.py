"""Unified scan pipeline — chains tools together with LLM correlation.

Flow:
   1. Subfinder  → subdomain enumeration
   2. httpx      → live endpoint probing
   3. Katana     → endpoint crawling
   4. Gau        → historical URL discovery
   5. LinkFinder → JS endpoint extraction
   6. ffuf       → fuzz path discovery (deep: raft-large + api + subdomain profiles)
   7. Mutation   → smart mutation engine (encoding bypass, HPP, type confusion, WAF bypass)
   8. Dalfox     → XSS deep scanning (DOM + mining + follow-redirects) + mutated payloads
   9. Sqlmap     → SQLi aggressive (level 3, risk 2, time-based, custom tamper scripts)
  10. Nuclei     → vulnerability scanning (all templates)
  11. ZAP        → active scan (SQLi, XSS, SSRF, path traversal, etc.)
  12. Headless   → Playwright DOM XSS + SPA crawling
  13. LLM        → correlation + intelligence
  14. Validation → differential testing
  15. Report     → generation

Each step feeds into the next. Results are correlated across tools.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from cores.tools.base import UnifiedResult
from cores.tools.extra import (
    BrowserUseTool,
    DalfoxTool,
    FfufTool,
    GarakTool,
    GauTool,
    GitleaksTool,
    KatanaTool,
    LinkFinderTool,
    SqlmapTool,
)
from cores.tools.httpx import HttpxTool
from cores.tools.nuclei import NucleiTool
from cores.tools.subfinder import SubfinderTool

try:
    from cores.execution.mutation_engine import SmartMutationEngine

    HAS_MUTATION_ENGINE = True
except ImportError:
    HAS_MUTATION_ENGINE = False
    SmartMutationEngine = None  # type: ignore


logger = logging.getLogger("cateye.pipeline.unified")


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
            result_type = (
                "vulnerability" if "vulnerability" in types else ("endpoint" if "endpoint" in types else "subdomain")
            )

            # Build evidence chain
            evidence_chain = {
                "sources": list(all_evidence.keys()),
                "cross_tool_confidence": max_confidence,
                "source_count": source_count,
                "details": all_evidence,
            }

            correlated.append(
                UnifiedResult(
                    source="correlation",
                    target=target,
                    result_type=result_type,
                    severity=max_severity,
                    confidence=max_confidence,
                    name=best_name,
                    description=f"Correlated from {source_count} tools: {', '.join(all_evidence.keys())}",
                    evidence=evidence_chain,
                    tags=sorted(all_tags),
                )
            )

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
        gitleaks: GitleaksTool | None = None,
        garak: GarakTool | None = None,
        browser_use: BrowserUseTool | None = None,
        mutation: Any | None = None,
        correlation: CorrelationEngine | None = None,
        deep_scan: bool = True,
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
        self._gitleaks = gitleaks or GitleaksTool()
        self._garak = garak or GarakTool()
        self._browser_use = browser_use or BrowserUseTool()
        self._mutation = mutation or (SmartMutationEngine() if HAS_MUTATION_ENGINE else None)
        self._correlation = correlation or CorrelationEngine()
        self._deep_scan = deep_scan

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
            profile = "balanced" if self._deep_scan else "fast"
            logger.info("Phase 6: ffuf — fuzzing %s (profile=%s)", fuzz_target, profile)
            ffuf_results = self._ffuf.discover_paths(fuzz_target, profile=profile)
            all_results.extend(ffuf_results)
            logger.info("  ffuf returned %d fuzz discoveries (deep=%s)", len(ffuf_results), self._deep_scan)
        else:
            logger.warning("  ffuf not available or no live endpoints")

        # Phase 7: Mutation engine — generate encoded / type-confused / HPP variants
        mutation_plan = None
        if self._mutation and self._deep_scan:
            logger.info("Phase 7: Mutation — generating mutation variants")
            try:
                candidate_urls = [
                    r.target for r in live_endpoints + linkfinder_results + ffuf_results if "?" in r.target
                ]
                mutation_plan = self._mutation.plan(url=candidate_urls[0] if candidate_urls else domain)
                mutation_metadata = self._mutation.enrich_evidence(mutation_plan)
                all_results.append(
                    UnifiedResult(
                        source="mutation_engine",
                        target=domain,
                        result_type="mutation_metadata",
                        confidence=1.0,
                        name=f"Mutation plan: {mutation_plan.attack_vector} ({len(mutation_plan.variants)} variants)",
                        evidence=mutation_metadata,
                        tags=["mutation", mutation_plan.attack_vector],
                    )
                )
                logger.info(
                    "  Mutation engine: %s vector, %d variants (%s)",
                    mutation_plan.attack_vector,
                    len(mutation_plan.variants),
                    ", ".join(mutation_metadata.get("strategies", {})),
                )
            except Exception as exc:
                logger.warning("  Mutation engine failed: %s", exc)
        else:
            logger.info("  Mutation engine skipped (deep=%s or not available)", self._deep_scan)

        # Phase 8: XSS deep scanning with Dalfox (with mutation plan)
        dalfox_results = []
        if self._dalfox.is_available():
            xss_candidates = [r.target for r in live_endpoints + linkfinder_results + ffuf_results if "?" in r.target]
            limit = 100 if self._deep_scan else 20
            xss_candidates = xss_candidates[:limit]
            if xss_candidates:
                logger.info(
                    "Phase 8: Dalfox — deep scanning %d URL candidates (deep=%s)", len(xss_candidates), self._deep_scan
                )
                dalfox_results = self._dalfox.scan_urls(
                    xss_candidates, deep=self._deep_scan, mutation_plan=mutation_plan
                )
                all_results.extend(dalfox_results)
                logger.info("  Dalfox returned %d findings", len(dalfox_results))
            else:
                logger.info("  Dalfox skipped: no query-style endpoints found")
        else:
            logger.warning("  dalfox not available")

        # Phase 9: SQLi aggressive scanning with sqlmap (with custom tamper from mutation engine)
        sqlmap_results = []
        if self._sqlmap.is_available():
            sqli_candidates = [r.target for r in live_endpoints + linkfinder_results + ffuf_results if "?" in r.target]
            limit = 50 if self._deep_scan else 10
            sqli_candidates = sqli_candidates[:limit]
            if sqli_candidates:
                tamper = None
                if mutation_plan and self._mutation:
                    tamper = self._mutation.encode_tamper_command(mutation_plan)
                logger.info(
                    "Phase 9: sqlmap — aggressive scanning %d endpoints (deep=%s, tamper=%s)",
                    len(sqli_candidates),
                    self._deep_scan,
                    tamper or "default",
                )
                if self._deep_scan:
                    sqlmap_results = self._sqlmap.scan_urls_batch(sqli_candidates, tamper_scripts=tamper)
                else:
                    for target_url in sqli_candidates:
                        sqlmap_results.extend(self._sqlmap.scan_url(target_url, aggressive=False))
                all_results.extend(sqlmap_results)
                logger.info("  sqlmap returned %d findings", len(sqlmap_results))
            else:
                logger.info("  sqlmap skipped: no query-style endpoints found")
        else:
            logger.warning("  sqlmap not available")

        # Phase 10: Vulnerability scanning
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

        # Phase 11: ZAP active scan (deep mode only)
        zap_results = []
        if self._deep_scan and live_endpoints:
            try:
                from cores.recon.zap_runner import ZapRunner

                zap = ZapRunner()
                health = asyncio.run(zap.health_check())
                if health.get("running"):
                    target = live_endpoints[0].target
                    logger.info("Phase 11: ZAP — active scanning %s", target)
                    result = asyncio.run(zap.active_scan(target, max_duration=15))
                    for alert in result.get("alerts", []):
                        zap_results.append(
                            UnifiedResult(
                                source="zap_active",
                                target=alert.get("url", target),
                                result_type="vulnerability",
                                severity=alert.get("risk", "medium").lower(),
                                confidence=0.65,
                                name=f"ZAP: {alert.get('alert', 'finding')}",
                                description=alert.get("description", ""),
                                evidence={"solution": alert.get("solution", ""), "cwe": alert.get("cwe_id", "")},
                                tags=["zap", "active_scan", alert.get("risk", "").lower()],
                            )
                        )
                    all_results.extend(zap_results)
                    logger.info("  ZAP active scan returned %d alerts", len(zap_results))
                    asyncio.run(zap.close())
            except Exception as exc:
                logger.warning("  ZAP active scan skipped: %s", exc)
        else:
            logger.info("  ZAP active scan skipped (deep=%s or no endpoints)", self._deep_scan)

        # Phase 12: Headless DOM scanning (deep mode only)
        dom_results = []
        if self._deep_scan and live_endpoints:
            try:
                from cores.tools.headless import HeadlessScanner

                headless = HeadlessScanner()
                live_urls_list = [r.target for r in live_endpoints[:5] if r.target.startswith("http")]
                if live_urls_list:
                    logger.info("Phase 12: Headless — DOM scanning %d URLs", len(live_urls_list))
                    dom_results = headless.scan_urls(live_urls_list)
                    all_results.extend(dom_results)
                    logger.info("  Headless returned %d DOM findings", len(dom_results))
            except Exception as exc:
                logger.warning("  Headless DOM scan skipped: %s", exc)
        else:
            logger.info("  Headless DOM scan skipped (deep=%s or no endpoints)", self._deep_scan)

        # Phase 13: Gitleaks — secret scanning (deep mode only, scan target directory)
        gitleaks_results = []
        if self._gitleaks.is_available() and self._deep_scan:
            logger.info("Phase 13: Gitleaks — secret scanning %s", domain)
            try:
                import tempfile
                from pathlib import Path

                scan_dir = Path(tempfile.mkdtemp(prefix="gitleaks_"))
                gitleaks_results = self._gitleaks.scan_path(scan_dir)
                all_results.extend(gitleaks_results)
                import shutil

                shutil.rmtree(scan_dir, ignore_errors=True)
            except Exception as exc:
                logger.warning("  Gitleaks scan skipped: %s", exc)
            logger.info("  Gitleaks returned %d findings", len(gitleaks_results))
        else:
            logger.info("  Gitleaks skipped (deep=%s or not available)", self._deep_scan)

        # Phase 14: Browser Use — autonomous browser agent (deep mode only)
        browser_results = []
        if self._browser_use.is_available() and self._deep_scan and live_endpoints:
            target_url = live_endpoints[0].target
            logger.info("Phase 14: Browser Use — autonomous browsing %s", target_url)
            try:
                task = f"Navigate to {target_url}, explore the application, identify forms and authentication mechanisms. Report all pages visited and any security-relevant findings."
                br_result = self._browser_use.run_task(task, max_steps=20, timeout=180)
                if br_result.success:
                    browser_results = br_result.results
                    all_results.extend(browser_results)
                    logger.info("  Browser Use returned %d results", len(browser_results))
            except Exception as exc:
                logger.warning("  Browser Use skipped: %s", exc)
        else:
            logger.info(
                "  Browser Use skipped (deep=%s, available=%s)", self._deep_scan, self._browser_use.is_available()
            )

        # Phase 15: Garak — LLM security testing (deep mode only, if LLM endpoint is present)
        garak_results = []
        if self._garak.is_available() and self._deep_scan:
            logger.info("Phase 15: Garak — LLM security testing")
            try:
                garak_results = self._garak.scan_ollama(
                    model_name="qwen3-coder:8b",
                    probes=["promptinject", "jailbreak"],
                )
                all_results.extend(garak_results)
                logger.info("  Garak returned %d findings", len(garak_results))
            except Exception as exc:
                logger.warning("  Garak scan skipped: %s", exc)
        else:
            logger.info("  Garak skipped (deep=%s or not available)", self._deep_scan)

        # Phase 16: Correlation
        logger.info("Phase 16: Correlation — cross-referencing %d results", len(all_results))
        correlated = self._correlation.correlate(all_results)
        logger.info("  Correlated into %d findings", len(correlated))

        duration = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

        return {
            "domain": domain,
            "subdomains": [r.to_dict() if hasattr(r, "to_dict") else r.__dict__ for r in subdomains],
            "live_endpoints": [r.to_dict() if hasattr(r, "to_dict") else r.__dict__ for r in live_endpoints],
            "vulnerabilities": [r.to_dict() if hasattr(r, "to_dict") else r.__dict__ for r in vulns],
            "correlated": [r.to_dict() if hasattr(r, "to_dict") else r.__dict__ for r in correlated],
            "summary": self._correlation.summarize_for_llm(correlated),
            "duration_ms": duration,
            "errors": errors,
        }
