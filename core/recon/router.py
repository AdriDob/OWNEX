from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.recon.fingerprint import Fingerprinter, FingerprintResult
from core.recon.strategies import ReconStrategy, select_strategies

logger = logging.getLogger("cateye.recon.router")


@dataclass
class RoutedReconResult:
    domain: str
    fingerprint: FingerprintResult = field(default_factory=lambda: FingerprintResult())
    strategies_used: list[str] = field(default_factory=list)
    probes_attempted: int = 0
    endpoints_found: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    tech_summary: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "domain": self.domain,
                "tech_summary": self.tech_summary,
                "strategies_used": self.strategies_used,
                "endpoints_found": len(self.endpoints_found),
                "sources": self.sources,
            },
            indent=2,
        )


class ReconRouter:
    def __init__(self, timeout: float = 10.0):
        self._fingerprinter = Fingerprinter(timeout=timeout)

    def route(self, domain: str, output_dir: Path | None = None) -> RoutedReconResult:
        result = RoutedReconResult(domain=domain)

        logger.info("[ROUTER] Fingerprinting %s...", domain)
        fingerprint = self._fingerprinter.fingerprint(domain)
        result.fingerprint = fingerprint
        result.tech_summary = fingerprint.tech_summary
        logger.info("[ROUTER] Detected: %s", fingerprint.tech_summary if fingerprint.technologies else "unknown")

        strategies = select_strategies(fingerprint)
        if not strategies:
            logger.info("[ROUTER] No strategy matched for %s", domain)
            return result

        result.strategies_used = [s.name for s in strategies]

        for strategy in strategies:
            self._run_strategy(domain, strategy, result)

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_path = output_dir / f"{domain}_router.json"
            out_path.write_text(result.to_json())
            logger.info("[ROUTER] Results written to %s", out_path)

        logger.info(
            "[ROUTER] %s: %d probes, %d endpoints", domain, result.probes_attempted, len(result.endpoints_found)
        )
        return result

    def _run_strategy(self, domain: str, strategy: ReconStrategy, result: RoutedReconResult) -> None:
        logger.info("[ROUTER] Strategy '%s' — %d probes", strategy.name, len(strategy.probes))

        for probe in strategy.probes:
            path = probe.get("path", "/")
            method = probe.get("method", "GET")
            body = probe.get("body")
            reason = probe.get("reason", "")

            url = f"https://{domain}{path}"
            result.probes_attempted += 1

            try:
                import httpx

                kwargs: dict[str, Any] = {
                    "method": method,
                    "url": url,
                    "timeout": self._fingerprinter._timeout,
                    "verify": False,
                    "follow_redirects": True,
                }
                if body:
                    kwargs["content"] = body
                    kwargs["headers"] = {"Content-Type": "application/json"}

                resp = httpx.request(**kwargs)

                if resp.status_code < 500:
                    entry: dict[str, Any] = {
                        "url": url,
                        "method": method,
                        "status": resp.status_code,
                        "reason": reason,
                        "strategy": strategy.name,
                        "body_preview": resp.text[:300] if resp.text else "",
                        "content_type": resp.headers.get("content-type", ""),
                    }

                    if body and '"data"' in resp.text:
                        entry["has_graphql_response"] = True

                    result.endpoints_found.append(entry)
                    result.sources.append(strategy.name)

                    if resp.status_code < 400:
                        logger.debug("[ROUTER]  %s %s → %d (%s)", method, url, resp.status_code, reason)
            except Exception:
                continue

    def route_and_enrich_existing(
        self,
        domain: str,
        existing_endpoints: list[dict[str, Any]],
    ) -> RoutedReconResult:
        result = self.route(domain)

        existing_paths = {ep.get("path", "") for ep in existing_endpoints}

        for ep in result.endpoints_found:
            path = ep.get("url", "").replace(f"https://{domain}", "")
            if path not in existing_paths:
                existing_endpoints.append(
                    {
                        "path": path,
                        "method": ep.get("method", "GET"),
                        "labels": [ep.get("strategy", "router"), ep.get("reason", "")],
                        "score": _endpoint_score(ep.get("status", 0)),
                        "raw": ep.get("url", ""),
                        "auth_smells": _detect_auth_smells(ep),
                    }
                )
                existing_paths.add(path)

        return result


def _endpoint_score(status: int) -> float:
    if status == 200:
        return 0.9
    if status == 401:
        return 0.7
    if status == 403:
        return 0.6
    if status in (301, 302, 307, 308):
        return 0.3
    if status == 404:
        return 0.1
    return 0.5


def _detect_auth_smells(entry: dict[str, Any]) -> list[str]:
    smells: list[str] = []
    body = entry.get("body_preview", "")
    if "login" in body.lower():
        smells.append("login_page")
    if "token" in body.lower():
        smells.append("token_reference")
    if "csrf" in body.lower():
        smells.append("csrf_protected")
    if "graphql" in entry.get("content_type", "").lower():
        smells.append("graphql_endpoint")
    if entry.get("status") == 401:
        smells.append("requires_authentication")
    if entry.get("status") == 403:
        smells.append("forbidden")
    return smells
