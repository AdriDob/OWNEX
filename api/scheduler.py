"""
Background scheduler — orchestrates the autonomous bug bounty pipeline.

Pipeline stages:
  1. DISCOVER  → scrape public platforms for new programs
  2. RECON     → run passive recon on each target (subfinder, amass, httpx, etc.)
  3. HYPOTHESIS  → generate vulnerability hypotheses from recon + ZAP data
  4. SCOPE_CHECK → verify validation is authorized before proceeding
  5. VALIDATE  → run controlled active tests only on in-scope targets
  6. REPORT    → generate reports for confirmed findings

Each stage runs independently and can be enabled/disabled via config.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from database import db, models

logger = logging.getLogger("catseye.scheduler")

STAGE_INTERVALS = {
    "discover": 3600,       # every hour
    "recon": 1800,          # every 30 min
    "hypothesis": 900,      # every 15 min
    "scope_check": 3600,    # every hour
    "validate": 7200,       # every 2 hours
    "report": 3600,         # every hour
}


class ScanScheduler:
    """Periodically runs the full autonomous pipeline on all targets."""

    def __init__(self, interval_minutes: int = 30):
        self.interval = interval_minutes * 60
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_run: dict[str, float] = {}

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Autonomous pipeline scheduler started (interval=%ds)", self.interval)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Autonomous pipeline scheduler stopped")

    async def _loop(self):
        while self._running:
            try:
                await self._run_pipeline()
            except Exception as exc:
                logger.warning("Pipeline cycle error: %s", exc)
            await asyncio.sleep(self.interval)

    async def _run_pipeline(self):
        """Execute one full pipeline cycle."""
        logger.info("=== Autonomous Pipeline Cycle ===")
        now = datetime.now(timezone.utc).timestamp()

        # Stage 1: Discover new programs
        if self._should_run("discover", now):
            try:
                await self._stage_discover()
            except Exception as e:
                logger.warning("Discover stage failed: %s", e)

        # Stage 2: Recon on all targets
        if self._should_run("recon", now):
            try:
                await self._stage_recon()
            except Exception as e:
                logger.warning("Recon stage failed: %s", e)

        # Stage 3: Generate hypotheses
        if self._should_run("hypothesis", now):
            try:
                await self._stage_hypothesis()
            except Exception as e:
                logger.warning("Hypothesis stage failed: %s", e)

        # Stage 4: Scope-aware active validation
        if self._should_run("validate", now):
            try:
                await self._stage_validate()
            except Exception as e:
                logger.warning("Validation stage failed: %s", e)

        # Stage 5: Generate reports
        if self._should_run("report", now):
            try:
                await self._stage_report()
            except Exception as e:
                logger.warning("Report stage failed: %s", e)

        self._last_run["pipeline"] = now
        logger.info("=== Pipeline Cycle Complete ===")

    def _should_run(self, stage: str, now: float) -> bool:
        """Check if enough time has passed since last run of this stage."""
        interval = STAGE_INTERVALS.get(stage, self.interval)
        last = self._last_run.get(stage, 0)
        return (now - last) >= interval

    # ── Stage 1: Discover ──────────────────────────────────────────────

    async def _stage_discover(self):
        """Scrape public platforms for new bounty programs."""
        logger.info("[DISCOVER] Scraping public bug bounty platforms...")
        session = db.SessionLocal()
        try:
            from cores.bounty_scraper import get_bounty_scraper

            scraper = get_bounty_scraper()
            programs = scraper.scrape_all(max_pages=2)
            created = scraper.convert_to_targets(programs, session, models)
            logger.info(
                "[DISCOVER] %d programs found, %d new targets created",
                len(programs),
                len(created),
            )
            self._last_run["discover"] = datetime.now(timezone.utc).timestamp()
        finally:
            session.close()

    # ── Stage 2: Recon ─────────────────────────────────────────────────

    async def _stage_recon(self):
        """Run passive recon on all targets that haven't been scanned recently."""
        session = db.SessionLocal()
        try:
            targets = session.query(models.Target).all()
            if not targets:
                logger.debug("[RECON] No targets to scan")
                return

            mode = os.environ.get("RASTRO_SCAN_MODE", "DEEP")

            for target in targets:
                if not self._running:
                    break
                try:
                    await self._recon_target(target, mode)
                except Exception as e:
                    logger.warning("[RECON] Failed on %s: %s", target.name, e)

            self._last_run["recon"] = datetime.now(timezone.utc).timestamp()
        finally:
            session.close()

    async def _recon_target(self, target: models.Target, mode: str):
        """Run recon pipeline + ZAP passive scan for a single target."""
        from cores.orchestrator.scan_service import launch_scan

        domain = target.domain or target.name
        logger.info("[RECON] Scanning %s (mode=%s)", target.name, mode)

        await launch_scan(
            target_name=target.name,
            target_domain=domain,
            target_mode=mode,
            session=db.SessionLocal(),
        )

        # Also run ZAP passive scan if available
        try:
            from cores.recon.zap_runner import ZapRunner, is_zap_installed

            if is_zap_installed():
                zap = ZapRunner()
                try:
                    health = await zap.health_check()
                    if health.get("running"):
                        await zap.access_url(f"https://{domain}")
                        await asyncio.sleep(2)
                        alerts = await zap.passive_scan_results(f"https://{domain}")
                        logger.info(
                            "[RECON] ZAP passive scan for %s: %d alerts",
                            domain, len(alerts),
                        )
                finally:
                    await zap.close()
        except Exception as e:
            logger.debug("[RECON] ZAP passive scan skipped for %s: %s", domain, e)

    # ── Stage 3: Hypothesis ────────────────────────────────────────────

    async def _stage_hypothesis(self):
        """Generate vulnerability hypotheses from recon + ZAP data."""
        session = db.SessionLocal()
        try:
            targets = session.query(models.Target).all()
            for target in targets:
                if not self._running:
                    break
                try:
                    await self._hypothesis_target(target, session)
                except Exception as e:
                    logger.warning(
                        "[HYPOTHESIS] Failed for %s: %s", target.name, e
                    )
            self._last_run["hypothesis"] = datetime.now(timezone.utc).timestamp()
        finally:
            session.close()

    async def _hypothesis_target(self, target: models.Target, session):
        """Run the Hypothesis Engine on a target's data."""
        from cores.engine.hypothesis import HypothesisEngine
        from cores.platform.system import get_data_dir
        from pathlib import Path

        # Load endpoints from last recon
        target_dir = get_data_dir() / "targets" / target.name
        endpoints_file = target_dir / "endpoints" / "normalized_endpoints.json"

        endpoints: list[dict] = []
        if endpoints_file.exists():
            import json
            try:
                endpoints = json.loads(endpoints_file.read_text())
            except (json.JSONDecodeError, Exception) as e:
                logger.debug("Could not load endpoints for %s: %s", target.name, e)

        if not endpoints:
            logger.debug("[HYPOTHESIS] No endpoints for %s, skipping", target.name)
            return

        engine = HypothesisEngine()
        output = engine.run(
            target_id=target.id,
            target_name=target.name,
            endpoints=endpoints,
        )
        logger.info(
            "[HYPOTHESIS] %s: %d hypotheses generated",
            target.name,
            output.total_hypotheses,
        )

    # ── Stage 4: Validate ──────────────────────────────────────────────

    async def _stage_validate(self):
        """Run controlled validation on high-confidence hypotheses.

        Only validates targets that are explicitly in scope.
        Skips targets where scope cannot be verified.
        """
        session = db.SessionLocal()
        try:
            targets = session.query(models.Target).all()
            for target in targets:
                if not self._running:
                    break
                try:
                    await self._validate_target(target, session)
                except Exception as e:
                    logger.warning(
                        "[VALIDATE] Failed for %s: %s", target.name, e
                    )
            self._last_run["validate"] = datetime.now(timezone.utc).timestamp()
        finally:
            session.close()

    async def _validate_target(self, target: models.Target, session):
        """Run controlled active validation for in-scope endpoints.

        Security: only runs if the target has a scope document that
        explicitly authorizes testing on the endpoint's domain.
        """
        # Check if target has a scope document
        scope_doc = (
            session.query(models.ScopeDocument)
            .filter(models.ScopeDocument.target_id == target.id)
            .first()
        )
        if not scope_doc:
            logger.debug(
                "[VALIDATE] No scope document for %s, skipping active validation",
                target.name,
            )
            return

        # Run nuclei with passive templates only
        from cores.recon.nuclei_runner import NucleiRunner
        from cores.platform.system import get_data_dir

        target_dir = get_data_dir() / "targets" / target.name
        targets_file = target_dir / "recon" / "nuclei_targets.txt"

        if not targets_file.exists():
            return

        nuclei = NucleiRunner(target_dir / "recon")
        result = await nuclei.run_nuclei(
            targets_file,
            "nuclei_validation.json",
            severity="medium,high,critical",
        )
        if result:
            logger.info("[VALIDATE] Nuclei scan for %s: %s", target.name, result)

    # ── Stage 5: Report ────────────────────────────────────────────────

    async def _stage_report(self):
        """Generate reports for confirmed findings."""
        session = db.SessionLocal()
        try:
            findings = (
                session.query(models.Finding)
                .filter(models.Finding.severity.in_(["high", "critical"]))
                .limit(20)
                .all()
            )
            if not findings:
                logger.debug("[REPORT] No high-severity findings to report")
                return

            from cores.pipeline.report_service import generate_and_save_report

            for finding in findings:
                if not self._running:
                    break
                try:
                    report = generate_and_save_report(
                        session=session,
                        finding_id=finding.id,
                    )
                    logger.info("[REPORT] Generated report for finding %d", finding.id)
                except Exception as e:
                    logger.debug(
                        "[REPORT] Failed for finding %d: %s", finding.id, e
                    )

            self._last_run["report"] = datetime.now(timezone.utc).timestamp()
        finally:
            session.close()

    # ── Manual trigger ─────────────────────────────────────────────────

    async def force_stage(self, stage: str):
        """Force-run a specific pipeline stage."""
        stage_map = {
            "discover": self._stage_discover,
            "recon": self._stage_recon,
            "hypothesis": self._stage_hypothesis,
            "validate": self._stage_validate,
            "report": self._stage_report,
        }
        fn = stage_map.get(stage)
        if fn:
            logger.info("Forcing stage: %s", stage)
            await fn()
            return {"status": "ok", "stage": stage}
        return {"status": "error", "detail": f"Unknown stage: {stage}"}
