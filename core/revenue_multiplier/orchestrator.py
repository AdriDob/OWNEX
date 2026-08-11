from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from core.revenue_multiplier.bugbounty_hunter import BugBountyHunter
from core.revenue_multiplier.config import RevenueMultiplierConfig
from core.revenue_multiplier.crypto_trader import CryptoTradingOrchestrator
from core.revenue_multiplier.metrics.metrics_tracker import MetricsTracker
from core.revenue_multiplier.models import Finding, RevenueCategory, RevenueEvent
from core.revenue_multiplier.publisher import RevenuePublisher
from core.revenue_multiplier.tool_registry import ToolRegistry, get_tool_registry

logger = logging.getLogger("orion.revenue.orchestrator")


class RevenueMultiplierOrchestrator:
    def __init__(self, config: RevenueMultiplierConfig | None = None) -> None:
        self._config = config or RevenueMultiplierConfig()
        self._registry = get_tool_registry()
        self._publisher = RevenuePublisher(self._config)
        self._metrics = MetricsTracker()
        self._bounty: BugBountyHunter | None = None
        self._crypto: CryptoTradingOrchestrator | None = None
        self._running = False
        self._session_id = ""

    @property
    def config(self) -> RevenueMultiplierConfig:
        return self._config

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    @property
    def publisher(self) -> RevenuePublisher:
        return self._publisher

    @property
    def metrics(self) -> MetricsTracker:
        return self._metrics

    @property
    def is_running(self) -> bool:
        return self._running

    def activate_max_revenue_mode(self) -> dict[str, Any]:
        self._session_id = uuid.uuid4().hex[:12]
        self._running = True
        logger.warning("=" * 60)
        logger.warning("  MAX REVENUE MODE ACTIVATED [%s]", self._session_id)
        logger.warning("  Mode: %s", self._config.mode.value.upper())
        logger.warning("=" * 60)

        results: dict[str, Any] = {
            "session_id": self._session_id,
            "mode": self._config.mode.value,
            "started_at": datetime.now(UTC).isoformat(),
            "bounty": {},
            "crypto": {},
            "tool_summary": self._registry.get_summary(),
        }

        if self._config.capital_allocation.bug_bounty_pct > 0:
            results["bounty"] = self._run_bounty_pipeline()

        if self._config.capital_allocation.crypto_trading_pct > 0:
            results["crypto"] = self._run_crypto_pipeline()

        self._running = False
        results["metrics"] = self._metrics.to_dict()
        results["finished_at"] = datetime.now(UTC).isoformat()

        logger.warning("=" * 60)
        logger.warning("  MAX REVENUE MODE COMPLETE [%s]", self._session_id)
        logger.warning("=" * 60)
        return results

    def _run_bounty_pipeline(self) -> dict[str, Any]:
        logger.info("── Bug Bounty Pipeline ──")
        self._bounty = BugBountyHunter(self._config, self._registry)
        targets = self._discover_targets()

        results: dict[str, Any] = {
            "targets": [],
            "total_findings": 0,
            "high_value_findings": 0,
        }

        for target in targets[: self._config.max_daily_bounty_targets]:
            logger.info("Scanning target: %s", target)
            start = time.monotonic()
            findings = self._bounty.run_full_pipeline(target)
            elapsed = time.monotonic() - start

            for f in findings:
                self._metrics.record_finding(
                    severity=f.severity or "info",
                    tool=f.tool,
                    cvss=f.cvss_score,
                )
                if f.severity in ("critical", "high"):
                    results["high_value_findings"] += 1

                self._publisher.publish_event(
                    RevenueEvent(
                        source=f"bounty:{f.tool}",
                        category=RevenueCategory.BUG_BOUNTY,
                        amount=Decimal("0"),
                        description=f"{f.severity}: {f.title[:100]} on {target}",
                        metadata={
                            "target": target,
                            "tool": f.tool,
                            "severity": f.severity or "info",
                            "endpoint": f.endpoint,
                        },
                    )
                )

            results["targets"].append(
                {
                    "domain": target,
                    "findings": len(findings),
                    "elapsed_s": round(elapsed, 1),
                }
            )
            results["total_findings"] += len(findings)

            if self._config.auto_report_enabled and findings:
                self._generate_report(target, findings)

        return results

    def _run_crypto_pipeline(self) -> dict[str, Any]:
        logger.info("── Crypto Trading Pipeline ──")
        self._crypto = CryptoTradingOrchestrator(self._config)

        signals = self._crypto.scan_opportunities()
        logger.info("Found %d trading signals", len(signals))

        results: dict[str, Any] = {
            "signals": len(signals),
            "trades_executed": 0,
            "errors": 0,
        }

        for signal in signals[: self._config.max_concurrent_trades]:
            if signal.confidence < 0.3:
                logger.info("Skipping low-confidence signal: %.2f — %s", signal.confidence, signal.pair)
                continue
            try:
                trade_result = self._crypto.execute_trade(signal)
                if trade_result.get("success"):
                    results["trades_executed"] += 1
                    self._metrics.record_trade(pnl=Decimal("0"), won=True)
                    self._publisher.publish_event(
                        RevenueEvent(
                            source="crypto:trader",
                            category=RevenueCategory.CRYPTO_TRADING,
                            amount=Decimal("0"),
                            description=f"Signal executed: {signal.pair} ({signal.reason[:50]})",
                            metadata={
                                "pair": signal.pair,
                                "strategy": signal.strategy,
                                "confidence": signal.confidence,
                            },
                        )
                    )
                else:
                    results["errors"] += 1
            except Exception as e:
                logger.error("Trade execution failed: %s", e)
                results["errors"] += 1

        return results

    def _discover_targets(self) -> list[str]:
        targets = []
        try:
            import httpx

            resp = httpx.get(
                "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/hackerone_data.json",
                timeout=15,
            )
            if resp.status_code == 200:
                for entry in (resp.json() or [])[:10]:
                    url = entry.get("url", "") or entry.get("target", {}).get("marketplace", {}).get("handle", "")
                    if url and "://" in url:
                        domain = url.split("://")[1].split("/")[0].split("?")[0]
                        if domain:
                            targets.append(domain)
        except Exception as e:
            logger.warning("Target discovery failed: %s", e)

        if not targets:
            targets = ["docs.hackerone.com", "httpforever.com", "example.com"]
        return targets

    def _generate_report(self, target: str, findings: list[Finding]) -> None:

        high_confidence = [f for f in findings if f.confidence >= self._config.min_confidence_for_report]
        if not high_confidence:
            return
        logger.info(
            "Auto-report: %d findings with confidence >= %.2f",
            len(high_confidence),
            self._config.min_confidence_for_report,
        )
        self._publisher.publish_event(
            RevenueEvent(
                source="bounty:auto_report",
                category=RevenueCategory.BUG_BOUNTY,
                amount=Decimal("0"),
                description=f"Report drafted for {target}: {len(high_confidence)} findings ready",
                metadata={"target": target, "findings_ready": len(high_confidence)},
            )
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "session": self._session_id,
            "mode": self._config.mode.value,
            "tool_summary": self._registry.get_summary(),
            "metrics": self._metrics.to_dict(),
            "config": {
                "max_concurrent_tools": self._config.max_concurrent_tools,
                "max_concurrent_trades": self._config.max_concurrent_trades,
                "auto_report": self._config.auto_report_enabled,
                "auto_trade": self._config.auto_trade_enabled,
                "allocation": self._config.capital_allocation.model_dump(),
            },
        }

    def get_tool_report(self) -> dict[str, Any]:
        available = self._registry.get_available()
        unavailable = self._registry.get_unavailable()
        return {
            "total": self._registry.count,
            "available": len(available),
            "unavailable": len(unavailable),
            "available_tools": [t.name for t in available],
            "unavailable_tools": [t.name for t in unavailable],
        }


_MAX_REVENUE: RevenueMultiplierOrchestrator | None = None


def get_revenue_multiplier() -> RevenueMultiplierOrchestrator:
    global _MAX_REVENUE
    if _MAX_REVENUE is None:
        _MAX_REVENUE = RevenueMultiplierOrchestrator()
    return _MAX_REVENUE
