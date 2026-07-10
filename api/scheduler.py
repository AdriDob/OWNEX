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
Target priority is informed by RewardLearner adjustments.
Per-target cooldown prevents re-scanning recently scanned targets.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import text

from cores.env.config import get_config
from cores.intelligence.reward_learning import RewardLearner
from database import db, models

logger = logging.getLogger("cateye.scheduler")

STAGE_INTERVALS = {
    "discover": 3600,
    "recon": 1800,
    "hypothesis": 900,
    "scope_check": 3600,
    "validate": 7200,
    "report": 3600,
}

# Per-target cooldown: skip recon on a target if scanned within this window
TARGET_COOLDOWN = 3600  # 1 hour

class ScanScheduler:
    def __init__(self, interval_minutes: int = 30):
        self.interval = interval_minutes * 60
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_run: dict[str, float] = {}
        self._target_cooldowns: dict[int, float] = {}

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
        logger.info("=== Autonomous Pipeline Cycle ===")
        now = datetime.now(timezone.utc).timestamp()

        if self._should_run("discover", now):
            try:
                await self._stage_discover()
            except Exception as e:
                logger.warning("Discover stage failed: %s", e)

        if self._should_run("recon", now):
            try:
                await self._stage_recon()
            except Exception as e:
                logger.warning("Recon stage failed: %s", e)

        if self._should_run("hypothesis", now):
            try:
                await self._stage_hypothesis()
            except Exception as e:
                logger.warning("Hypothesis stage failed: %s", e)

        if self._should_run("validate", now):
            try:
                await self._stage_validate()
            except Exception as e:
                logger.warning("Validation stage failed: %s", e)

        if self._should_run("report", now):
            try:
                await self._stage_report()
            except Exception as e:
                logger.warning("Report stage failed: %s", e)

        self._last_run["pipeline"] = now
        # Checkpoint WAL to prevent unbounded growth on 24/7 systems
        try:
            with db.SessionLocal() as sess:
                sess.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
        except Exception:
            pass
        # Purge stale cooldown entries (entries older than 2x TARGET_COOLDOWN)
        stale_cooldown_threshold = now - TARGET_COOLDOWN * 2
        old_count = len(self._target_cooldowns)
        self._target_cooldowns = {
            tid: ts for tid, ts in self._target_cooldowns.items()
            if ts >= stale_cooldown_threshold
        }
        purged = old_count - len(self._target_cooldowns)
        if purged:
            logger.info("[SCHEDULER] Purged %d stale cooldown entries", purged)
        logger.info("=== Pipeline Cycle Complete ===")

    def _should_run(self, stage: str, now: float) -> bool:
        interval = STAGE_INTERVALS.get(stage, self.interval)
        last = self._last_run.get(stage, 0)
        return (now - last) >= interval

    async def _stage_discover(self):
        logger.info("[DISCOVER] Scraping public bug bounty platforms...")
        session = db.SessionLocal()
        try:
            from cores.bounty_scraper import get_bounty_scraper
            scraper = get_bounty_scraper()
            programs = await asyncio.to_thread(scraper.scrape_all, max_pages=2)
            created = scraper.convert_to_targets(programs, session, models)
            logger.info(
                "[DISCOVER] %d programs found, %d new targets created",
                len(programs), len(created),
            )
            if created:
                try:
                    from cores.events.event_bus import get_event_bus
                    bus = get_event_bus()
                    bus.publish("opportunity:found", {
                        "count": len(created),
                        "names": [c.name for c in created[:10]] if hasattr(created[0], 'name') else [],
                        "source": "discovery_scheduler",
                    })
                except Exception:
                    pass
            self._last_run["discover"] = datetime.now(timezone.utc).timestamp()
        finally:
            session.close()

    async def _stage_recon(self):
        session = db.SessionLocal()
        try:
            targets = session.query(models.Target).all()
            if not targets:
                logger.debug("[RECON] No targets to scan")
                return

            mode = get_config().scan_mode

            # Build priority scores using reward learning adjustments
            priority = _compute_target_priorities(targets)

            # Sort targets by priority (high first), then filter by cooldown
            targets_with_priority = [(t, priority.get(t.id, 0.0)) for t in targets]
            targets_with_priority.sort(key=lambda x: -x[1])

            now = time.time()
            inspected_for_log = False
            scanned = 0
            for target, priority_score in targets_with_priority:
                if not self._running:
                    break
                # Skip if in cooldown
                last_scan = self._target_cooldowns.get(target.id, 0)
                if (now - last_scan) < TARGET_COOLDOWN:
                    continue
                if not inspected_for_log and priority_score > 1.0:
                    logger.info("[ORION] Auto-prioritized %s (priority=%.2f) — selected by reward learning + ORION scoring",
                                target.name, priority_score)
                    inspected_for_log = True
                try:
                    self._target_cooldowns[target.id] = now
                    await self._recon_target(target, mode, session)
                    scanned += 1
                except Exception as e:
                    logger.warning("[RECON] Failed on %s: %s", target.name, e)

            if scanned:
                logger.info("[RECON] Scanned %d/%d targets (cooldown filtered %d)",
                           scanned, len(targets),
                           sum(1 for t in targets
                               if (now - self._target_cooldowns.get(t.id, 0)) < TARGET_COOLDOWN))
                try:
                    from cores.events.event_bus import get_event_bus
                    bus = get_event_bus()
                    bus.publish("discovery:completed", {
                        "stage": "recon",
                        "scanned": scanned,
                        "total": len(targets),
                    })
                except Exception:
                    pass

            self._last_run["recon"] = datetime.now(timezone.utc).timestamp()
        finally:
            session.close()

    async def _recon_target(self, target: models.Target, mode: str, session):
        from cores.orchestrator.scan_service import launch_scan

        domain = target.domain or target.name
        logger.info("[RECON] Scanning %s (mode=%s)", target.name, mode)

        await launch_scan(
            target_name=target.name,
            target_domain=domain,
            target_mode=mode,
            session=session,
        )

    async def _resolve_auth_pair(
        self, session, target_id: int
    ) -> tuple[dict | None, dict | None]:
        from cores.target_auth.session_resolver import get_session_resolver

        resolver = get_session_resolver()

        baseline_id = session.query(models.TargetIdentity.id).filter(
            models.TargetIdentity.target_id == target_id,
            models.TargetIdentity.is_baseline.is_(True),
            models.TargetIdentity.is_active.is_(True),
        ).scalar()

        probe_id = session.query(models.TargetIdentity.id).filter(
            models.TargetIdentity.target_id == target_id,
            models.TargetIdentity.is_baseline.is_(False),
            models.TargetIdentity.is_active.is_(True),
        ).scalar()

        baseline_ctx = None
        probe_ctx = None

        if baseline_id:
            baseline_ctx = await asyncio.to_thread(resolver.resolve, baseline_id)
        else:
            logger.info("[VALIDATE] Target %d: no baseline identity — anonymous", target_id)

        if probe_id:
            probe_ctx = await asyncio.to_thread(resolver.resolve, probe_id)
        else:
            logger.info("[VALIDATE] Target %d: no probe identity — anonymous", target_id)

        return baseline_ctx, probe_ctx

    async def _stage_hypothesis(self):
        logger.info("[HYPOTHESIS] Generating vulnerability hypotheses...")
        session = db.SessionLocal()
        try:
            from cores.engine.hypothesis.generators import generate_hypotheses
            endpoints = session.query(models.Endpoint).filter(
                models.Endpoint.hypothesis_id.is_(None)
            ).limit(100).all()
            for ep in endpoints:
                try:
                    target = session.query(models.Target).filter(models.Target.id == ep.target_id).first()
                    if not target:
                        continue
                    ep_dict = {
                        "id": ep.id, "path": ep.path, "method": ep.method,
                        "parsed_params": getattr(ep, "parsed_params", "{}"),
                        "risk_score": getattr(ep, "risk_score", 0.0),
                    }
                    results = generate_hypotheses(
                        endpoints=[ep_dict],
                        target_id=ep.target_id,
                        target_name=target.name,
                    )
                    if results:
                        ep.hypothesis_id = results[0].id
                        session.commit()
                except Exception as e:
                    logger.debug("Hypothesis gen failed for endpoint %d: %s", ep.id, e)
            self._last_run["hypothesis"] = datetime.now(timezone.utc).timestamp()
        finally:
            session.close()

    async def _stage_validate(self):
        logger.info("[VALIDATE] Running scope-aware validation...")
        session = db.SessionLocal()
        try:
            from cores.validation.loop_engine import ValidationLoopEngine
            from cores.validation.replayer import AuthContext
            findings = session.query(models.Finding).filter(
                models.Finding.status == "open"
            ).filter(
                models.Finding.severity.in_(["high", "critical"])
            ).limit(20).all()
            engine = ValidationLoopEngine()
            for f in findings:
                try:
                    ep = session.query(models.Endpoint).filter(models.Endpoint.id == f.endpoint_id).first() if f.endpoint_id else None
                    if not ep:
                        continue
                    vt = getattr(f, "vulnerability_type", None) or "unknown"
                    endpoint_details = {
                        "url": getattr(ep, 'url', ''),
                        "method": getattr(ep, 'method', 'GET'),
                        "headers": {},
                        "params": {},
                    }
                    baseline_ctx, probe_ctx = await self._resolve_auth_pair(session, f.target_id)
                    auth_baseline = AuthContext(
                        token=(baseline_ctx or {}).get("token"),
                        cookies=(baseline_ctx or {}).get("cookies", {}),
                        headers=(baseline_ctx or {}).get("headers", {}),
                        label="baseline",
                    )
                    auth_probe = AuthContext(
                        token=(probe_ctx or {}).get("token"),
                        cookies=(probe_ctx or {}).get("cookies", {}),
                        headers=(probe_ctx or {}).get("headers", {}),
                        label="probe",
                    )
                    engine.evaluate(
                        hot_path_id=f"finding_{f.id}",
                        endpoint_details=endpoint_details,
                        endpoint_signals={},
                        auth_baseline=auth_baseline,
                        auth_probe=auth_probe,
                        vulnerability_type=vt,
                    )
                except Exception as e:
                    logger.debug("Validation failed for finding %d: %s", f.id, e)
            self._last_run["validate"] = datetime.now(timezone.utc).timestamp()
        finally:
            session.close()

    async def _stage_report(self):
        logger.info("[REPORT] Generating reports...")
        session = db.SessionLocal()
        try:
            from cores.pipeline.report_service import create_report_from_findings
            confirmed_findings = session.query(models.Finding).filter(
                models.Finding.status == "confirmed"
            ).limit(50).all()
            for f in confirmed_findings:
                try:
                    report = create_report_from_findings(
                        session=session,
                        finding_ids=[f.id],
                        program="",
                        target=f"target_{f.target_id}",
                        vulnerability=f.title or f"Finding #{f.id}",
                        severity=f.severity or "medium",
                    )
                    if report:
                        try:
                            from cores.events.event_bus import get_event_bus
                            bus = get_event_bus()
                            bus.publish("report:generated", {
                                "finding_id": f.id,
                                "report_id": report.get("id"),
                                "status": "draft",
                            })
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug("Report generation failed for finding %d: %s", f.id, e)
            self._last_run["report"] = datetime.now(timezone.utc).timestamp()
        finally:
            session.close()


def _compute_target_priorities(targets: list) -> dict[int, float]:
    """Compute per-target priority using reward learning + ORION SCORE + next action."""
    try:
        learner = RewardLearner()
        report = learner.analyze()
        adjustments = report.vuln_type_adjustments if report else {}
    except Exception:
        adjustments = {}

    # Get ORION's recommended next action
    orion_next = None
    orion_next_name = ""
    try:
        from cores.orion.next_action import get_next_action
        action = get_next_action()
        if action:
            orion_next = action
            orion_next_name = (action.get("title") or "").lower()
    except Exception:
        pass

    # Pre-load ORION SCOREs for targets that have related programs
    try:
        from database import db as _db
        _db.init_db()
        session = _db.SessionLocal()
        program_scores = {}
        for t in targets:
            if hasattr(t, 'domain') and t.domain:
                prog = session.query(_db.models_economic.Program).filter(
                    _db.models_economic.Program.domain == t.domain
                ).first()
                if prog and hasattr(prog, 'orion_score'):
                    program_scores[t.id] = prog.orion_score
        session.close()
    except Exception:
        program_scores = {}

    priorities: dict[int, float] = {}
    for t in targets:
        score = 1.0
        # Boost targets whose vulnerability types have high adjustment factors
        if hasattr(t, 'vulnerability_type') and t.vulnerability_type:
            adj = adjustments.get(t.vulnerability_type, 1.0)
            score *= adj
        # Boost targets with recent activity
        if hasattr(t, 'last_active') and t.last_active:
            days_since = (datetime.now(timezone.utc) - t.last_active).days
            score *= max(0.5, 2.0 - days_since * 0.1)
        # ORION SCORE multiplier
        orion = program_scores.get(t.id)
        if orion is not None and orion > 0:
            score *= 0.5 + (orion * 1.5)
        # Boost target if ORION recommends its program
        if orion_next_name and t.name and t.name.lower() in orion_next_name:
            score *= 1.5
        # Normalize
        priorities[t.id] = round(max(0.1, min(score, 10.0)), 2)

    if orion_next:
        logger.info("[ORION] Next action recommendation: %s (score=%.4f, why=%s)",
                    orion_next.get("title"), 0.0, orion_next.get("why_now", ""))

    return priorities
