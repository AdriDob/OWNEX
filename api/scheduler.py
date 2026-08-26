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
import re
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from core.target_intelligence import TargetPrioritizer
from cores.agents.types import EventType  # AÑADIR PipelineState
from cores.env.config import get_config
from cores.events.event_bus import get_event_bus  # AÑADIR
from cores.intelligence.reward_learning import RewardLearner
from cores.targets.models import TargetIntel
from database import db, models

if TYPE_CHECKING:
    pass

# Lazy COPILOT import — agent is optional
_copilot_instance: Any = None


def _get_copilot():
    """Lazy-init singleton COPILOT instance."""
    global _copilot_instance
    if _copilot_instance is None:
        try:
            from core.copilot.agent import CopilotAgent
            from core.copilot.permissions import AuthorityLevel

            _copilot_instance = CopilotAgent(authority=AuthorityLevel.SENIOR_HUNTER)
            logger.info("[COPILOT] Scheduler COPILOT initialized")
        except Exception as exc:
            logger.debug("[COPILOT] Not available in scheduler: %s", exc)
    return _copilot_instance


logger = logging.getLogger("ownex.scheduler")

STAGE_INTERVALS = {
    "discover": 3600,
    "recon": 1800,
    "hypothesis": 900,
    "auto_validate": 1800,
    "promote": 600,
    "scope_check": 3600,
    "validate": 7200,
    "report": 3600,
    "ai_bounty": 7200,
}

# Per-target cooldown: skip recon on a target if scanned within this window
TARGET_COOLDOWN = 3600  # 1 hour


def _path_based_hypothesis(endpoint: Any, target: Any) -> str | None:
    """Generate a hypothesis ID from path patterns alone (fallback for bare endpoints)."""
    import hashlib

    path = (getattr(endpoint, "path", "") or "").lower()
    method = (getattr(endpoint, "method", "GET") or "GET").upper()

    numeric_segment = re.search(r"/(\d+)(/|$)", path)
    uuid_pattern = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", path)
    has_id_param = re.search(
        r"(user|account|order|id|profile|file|team|project|customer|subscription|device)_?id", path, re.I
    )
    is_admin = "admin" in path
    is_api = path.startswith("/api/") or "/api/" in path
    is_graphql = "graphql" in path
    is_login = "login" in path or "signin" in path or "auth" in path
    is_search = "search" in path or "query" in path
    is_upload = "upload" in path or "import" in path
    is_ssrf_like = "redirect" in path or "proxy" in path or "fetch" in path or "webhook" in path

    vuln_type = None
    if is_graphql:
        vuln_type = "graphql_injection"
    elif (numeric_segment and is_api) or (uuid_pattern and is_api) or (has_id_param and method in ("GET", "DELETE")):
        vuln_type = "idor"
    elif is_admin or is_login:
        vuln_type = "auth_bypass"
    elif is_upload:
        vuln_type = "file_upload"
    elif is_ssrf_like:
        vuln_type = "ssrf"
    elif is_search and method == "GET":
        vuln_type = "xss"
    elif method == "POST" and is_api:
        vuln_type = "sqli"

    if vuln_type:
        raw = f"{vuln_type}:{endpoint.id}:path"
        h_id = hashlib.sha256(raw.encode()).hexdigest()[:12]
        logger.info("[HYPOTHESIS] Path-based %s for %s %s (id=%s)", vuln_type, method, path, h_id)
        return h_id
    return None


# Module-level references for cross-module access
scheduler_instance: ScanScheduler | None = None


def get_scheduler_stats() -> dict:
    if scheduler_instance is None:
        return {"status": "not_started", "running": False, "last_run": None}
    return {
        "status": "running" if scheduler_instance._running else "stopped",
        "running": scheduler_instance._running,
        "last_run": scheduler_instance._last_run.get("pipeline"),
        "targets_in_cooldown": len(scheduler_instance._target_cooldowns),
        "stages": dict(scheduler_instance._last_run),
        "current_stage": scheduler_instance._current_stage_name,
        "stage_started_at": scheduler_instance._stage_started_at,
    }


def get_scheduler_status() -> dict:
    if scheduler_instance is None:
        return {"status": "not_started", "running": False}
    return {
        "status": "running" if scheduler_instance._running else "stopped",
        "running": scheduler_instance._running,
        "interval": scheduler_instance.interval,
    }


class ScanScheduler:
    def __init__(self, interval_minutes: int = 30):
        self.interval = interval_minutes * 60
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_run: dict[str, float] = {}
        self._target_cooldowns: dict[int, float] = {}
        self._target_pipelines: dict[int, str] = {}
        self._current_stage_name: str = "idle"
        self._stage_started_at: float = 0.0
        self._time_waster_ceiling: float = 0.0
        self._cycle_started: float = 0.0

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
                self._recover_stale_scans()
                await self._run_pipeline()
            except Exception as exc:
                logger.warning("Pipeline cycle error: %s", exc)
            await asyncio.sleep(self.interval)

    def _recover_stale_scans(self) -> None:
        """Mark scans stuck in 'running' as failed before each cycle."""
        try:
            from cores.orchestrator.scan_service import recover_stale_scans

            recover_stale_scans()
        except Exception as exc:
            logger.warning("Scan recovery skipped: %s", exc)

    async def _run_pipeline(self):
        logger.info("=== Autonomous Pipeline Cycle ===")
        now = datetime.now(UTC).timestamp()
        self._cycle_started = now

        if self._should_run("discover", now):
            self._set_stage("discover")
            try:
                await self._stage_discover()
                # No se emite hook de copilot para discover, ya que se maneja por target en recon
            except Exception as e:
                logger.warning("Discover stage failed: %s", e)

        if self._should_run("recon", now):
            self._set_stage("recon")
            try:
                # _stage_recon ahora manejará la emisión de eventos por target
                await self._stage_recon()
            except Exception as e:
                logger.warning("Recon stage failed: %s", e)

        if self._should_run("hypothesis", now):
            self._set_stage("hypothesis")
            try:
                await self._stage_hypothesis()
                self._copilot_hook("hypothesis", "completed")
            except Exception as e:
                logger.warning("Hypothesis stage failed: %s", e)
                self._copilot_hook("hypothesis", "failed")

        if self._should_run("auto_validate", now):
            self._set_stage("auto_validate")
            try:
                await self._stage_auto_validate()
                self._copilot_hook("auto_validate", "completed")
            except Exception as e:
                logger.warning("Auto-validate stage failed: %s", e)
                self._copilot_hook("auto_validate", "failed")

        if self._should_run("promote", now):
            self._set_stage("promote")
            try:
                await self._stage_promote()
                self._copilot_hook("promote", "completed")
            except Exception as e:
                logger.warning("Promote stage failed: %s", e)
                self._copilot_hook("promote", "failed")

        if self._should_run("validate", now):
            self._set_stage("validate")
            try:
                await self._stage_validate()
                self._copilot_hook("validate", "completed")
            except Exception as e:
                logger.warning("Validation stage failed: %s", e)
                self._copilot_hook("validate", "failed")

        if self._should_run("report", now):
            self._set_stage("report")
            try:
                await self._stage_report()
                self._copilot_hook("report", "completed")
            except Exception as e:
                logger.warning("Report stage failed: %s", e)
                self._copilot_hook("report", "failed")

        if self._should_run("ai_bounty", now):
            self._set_stage("ai_bounty")
            try:
                await self._stage_ai_bounty()
                self._copilot_hook("ai_bounty", "completed")
            except Exception as e:
                logger.warning("AI Bounty stage failed: %s", e)
                self._copilot_hook("ai_bounty", "failed")

        self._last_run["pipeline"] = now

        # Parallel recovery: learn from hacktivity, refresh economic memory, generate stale reports
        try:
            asyncio.ensure_future(self._parallel_recovery())
        except Exception:
            logger.debug("[RECOVERY] Could not schedule parallel recovery")

        # Checkpoint WAL to prevent unbounded growth on 24/7 systems
        try:
            with db.SessionLocal() as sess:
                sess.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
        except Exception:
            logger.exception("Failed to checkpoint WAL")
        # Purge stale cooldown entries (entries older than 2x TARGET_COOLDOWN)
        stale_cooldown_threshold = now - TARGET_COOLDOWN * 2
        old_count = len(self._target_cooldowns)
        self._target_cooldowns = {
            tid: ts for tid, ts in self._target_cooldowns.items() if ts >= stale_cooldown_threshold
        }
        purged = old_count - len(self._target_cooldowns)
        if purged:
            logger.info("[SCHEDULER] Purged %d stale cooldown entries", purged)

        elapsed = now - self._cycle_started
        if elapsed > 1800 and now - self._time_waster_ceiling > 3600:
            try:
                with db.SessionLocal() as sess:
                    recent = (
                        sess.query(models.Finding)
                        .filter(
                            models.Finding.created_at >= self._cycle_started,
                        )
                        .count()
                    )
                    medium_plus = (
                        sess.query(models.Finding)
                        .filter(
                            models.Finding.created_at >= self._cycle_started,
                            models.Finding.severity.in_(["medium", "high", "critical"]),
                        )
                        .count()
                    )
                if medium_plus == 0 and recent > 0:
                    logger.warning(
                        "[TIME_WASTER] %.0fmin sin findings medium+ (solo %d low/info). "
                        "Consider cambiar de target o revisar el scope activo.",
                        elapsed / 60,
                        recent - medium_plus,
                    )
                    self._time_waster_ceiling = now
                elif recent == 0:
                    logger.info(
                        "[TIME_WASTER] %.0fmin sin NINGUN finding. "
                        "El pipeline no esta produciendo. Sugerencia: revisar conectividad de herramientas o cambiar de programa.",
                        elapsed / 60,
                    )
                    self._time_waster_ceiling = now
            except Exception:
                logger.debug("[TIME_WASTER] DB query failed (expected in test mode)", exc_info=True)

        logger.info("=== Pipeline Cycle Complete ===")

    async def _parallel_recovery(self) -> None:
        try:
            goals_met = 0

            try:
                from core.reports.acceptance.scraper import feed_hacktivity_to_learner

                fed = feed_hacktivity_to_learner(max_pages=1, delay=0.3)
                if fed:
                    logger.info("[RECOVERY] Learned from %d hacktivity reports", fed)
                    goals_met += 1
            except Exception:
                logger.debug("[RECOVERY] Hacktivity learning skipped")

            try:
                from core.revenue.economic_memory import EconomicMemory

                EconomicMemory().refresh()
                goals_met += 1
            except Exception:
                logger.debug("[RECOVERY] Economic memory refresh skipped")

            try:
                from cores.pipeline.report_service import create_report_from_findings

                session = db.SessionLocal()
                try:
                    stale = session.query(models.Finding).filter(models.Finding.status == "confirmed").limit(20).all()
                    for f in stale:
                        existing = (
                            session.query(models.Report).filter(models.Report.finding_ids.like(f"%{f.id}%")).first()
                        )
                        if existing:
                            continue
                        create_report_from_findings(
                            session=session,
                            finding_ids=[f.id],
                            extra={
                                "program": "",
                                "target": f"target_{f.target_id}",
                                "vulnerability": f.title or f"Finding #{f.id}",
                                "severity": f.severity or "medium",
                            },
                        )
                        goals_met += 1
                finally:
                    session.close()
            except Exception:
                logger.debug("[RECOVERY] Stale report generation skipped")

            logger.debug("[RECOVERY] Parallel recovery idle tasks done (%d goals met)", goals_met)
        except Exception as exc:
            logger.warning("[RECOVERY] Parallel recovery error: %s", exc)

    def _copilot_hook(
        self, stage: str, stage_result: str = "completed", pipeline_id: str | None = None, error_message: str = ""
    ) -> None:
        """Emit pipeline stage event to EventBus + COPILOT hook.

        Best-effort: nunca propaga excepciones al pipeline (P0-1 audit 2026-08-25:
        el cuerpo estaba anidado en un def interno nunca invocado → eventos muertos).
        """
        from cores.agents.types import EventType
        from cores.events.event_bus import get_event_bus

        event_bus = get_event_bus()

        event_type = EventType.PIPELINE_STAGE_COMPLETED
        if error_message:
            event_type = EventType.PIPELINE_FAILED

        try:
            event_bus.publish(
                event_type.value,
                stage=stage,
                stage_result=stage_result,
                pipeline_id=pipeline_id,
            )
            if error_message:
                event_bus.publish(
                    EventType.PIPELINE_FAILED.value,
                    error=error_message,
                    pipeline_id=pipeline_id,
                )
            logger.info(
                "[SCHEDULER->EVENTBUS] Emitted %s for pipeline %s, stage %s: %s",
                event_type.value,
                (pipeline_id or "")[:8],
                stage,
                stage_result,
            )
        except Exception:
            logger.exception("Failed to publish pipeline stage event to EventBus")

        try:
            copilot = _get_copilot()
            if copilot is None:
                logger.debug("[COPILOT] Not available, skipping hook for %s", stage)
                return

            actions = copilot.recommend_for_system(
                extra_state={
                    "stage": stage,
                    "stage_result": stage_result,
                    "last_run": self._last_run.get(stage, 0),
                }
            )
            for a in actions[:3]:
                logger.info(
                    "[COPILOT] After %s: %s (prio=%d) — %s",
                    stage,
                    a["action"],
                    a.get("priority", 0),
                    a.get("reason", ""),
                )
        except Exception as exc:
            logger.debug("[COPILOT] Hook %s error: %s", stage, exc)

    def _set_stage(self, stage: str) -> None:
        """Track current pipeline stage for frontend progress display."""
        self._current_stage_name = stage
        self._stage_started_at = time.time()

    def _should_run(self, stage: str, now: float) -> bool:
        interval = STAGE_INTERVALS.get(stage, self.interval)
        last = self._last_run.get(stage, 0)
        return (now - last) >= interval

    async def _stage_discover(self):
        logger.info("[DISCOVER] Scraping public bug bounty platforms...")
        session = db.SessionLocal()
        try:
            from cores.bounty_scraper import get_bounty_scraper
            from cores.events.event_bus import get_event_bus

            bus = get_event_bus()
            scraper = get_bounty_scraper()
            programs, diff = await asyncio.to_thread(
                scraper.scrape_with_changes,
                max_pages=2,
            )
            created = scraper.convert_to_targets(programs, session, models)
            logger.info(
                "[DISCOVER] %d programs found, %d new targets created, %d new programs, %d removed, %d updated",
                len(programs),
                len(created),
                len(diff.new_programs),
                len(diff.removed_programs),
                len(diff.updated_programs),
            )

            if diff.new_programs:
                for prog in diff.new_programs[:10]:
                    bus.publish(
                        "discovery:program:new",
                        {
                            "name": prog.name,
                            "platform": prog.platform,
                            "payout": prog.estimated_payout,
                            "url": prog.program_url,
                            "source": "discovery_scheduler",
                        },
                    )

            if diff.updated_programs:
                for update in diff.updated_programs[:10]:
                    bus.publish(
                        "discovery:program:updated",
                        {
                            "program": update["program"],
                            "changes": update["changes"],
                            "source": "discovery_scheduler",
                        },
                    )

            if created:
                try:
                    bus.publish(
                        "opportunity:found",
                        {
                            "count": len(created),
                            "names": [c.name for c in created[:10]] if hasattr(created[0], "name") else [],
                            "source": "discovery_scheduler",
                        },
                    )
                except Exception:
                    logger.exception("Failed to publish opportunity:found event")

            bus.publish(
                "discovery:completed",
                {
                    "count": len(programs),
                    "new": len(diff.new_programs),
                    "updated": len(diff.updated_programs),
                    "removed": len(diff.removed_programs),
                    "created": len(created),
                    "source": "discovery_scheduler",
                },
            )
            self._last_run["discover"] = datetime.now(UTC).timestamp()
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

            # Use TargetPrioritizer for EV-based ranking + attack plans
            try:
                learner = RewardLearner()
                learner.analyze()
                adjustments = learner.get_adjustments()
            except Exception:
                adjustments = {}

            target_intel_map: dict[int, TargetIntel] = {}
            for t in targets:
                domain = (getattr(t, "domain", None) or "").strip()
                intel: TargetIntel | None = None
                if domain:
                    intel = session.query(TargetIntel).filter(TargetIntel.domain == domain).first()
                if intel is None:
                    intel = session.query(TargetIntel).filter(TargetIntel.name == t.name).first()
                if intel is not None:
                    target_intel_map[t.id] = intel

            prioritizer = TargetPrioritizer()
            priority, results = prioritizer.prioritize(targets, target_intel_map, adjustments)

            targets_with_priority = [(t, priority.get(t.id, 0.0)) for t in targets]
            targets_with_priority.sort(key=lambda x: -x[1])

            now = time.time()
            inspected_for_log = False
            scanned = 0
            for target, priority_score in targets_with_priority:
                if not self._running:
                    break
                last_scan = self._target_cooldowns.get(target.id, 0)
                if (now - last_scan) < TARGET_COOLDOWN:
                    continue

                if not inspected_for_log:
                    pr = next((r for r in results if r.target_id == target.id), None)
                    if pr:
                        logger.info(
                            "[ORION] Auto-prioritized %s (EV=$%.2f, priority=%.2f, "
                            "reward=$%.0f×%.0f%%×%.1fx, $%.2f/h, tech=%s, plan=%s, phases=%d)",
                            target.name,
                            pr.expected_value,
                            priority_score,
                            pr.estimated_reward,
                            pr.acceptance_probability * 100,
                            pr.speed_multiplier,
                            pr.usd_per_hour,
                            pr.attack_plan.strategies or "none",
                            pr.attack_plan.estimated_hours,
                            len(pr.attack_plan.phases_to_run),
                        )
                    inspected_for_log = True

                plan = next((r.attack_plan for r in results if r.target_id == target.id), None)
                if plan and priority_score < 0.5:
                    logger.debug(
                        "[RECON] Skipping %s (EV too low: priority=%.2f, budget=%.1fh)",
                        target.name,
                        priority_score,
                        plan.estimated_hours,
                    )
                    continue

                try:
                    self._target_cooldowns[target.id] = now
                    await self._recon_target(target, mode, session)
                    scanned += 1
                except Exception as e:
                    logger.warning("[RECON] Failed on %s: %s", target.name, e)
                    self._copilot_hook("recon", "failed", pipeline_id=target._pipeline_id, error_message=str(e))

            if scanned:
                logger.info(
                    "[RECON] Scanned %d/%d targets (cooldown filtered %d)",
                    scanned,
                    len(targets),
                    sum(1 for t in targets if (now - self._target_cooldowns.get(t.id, 0)) < TARGET_COOLDOWN),
                )

            self._last_run["recon"] = datetime.now(UTC).timestamp()
        finally:
            session.close()

    async def _recon_target(self, target: models.Target, mode: str, session):
        from cores.orchestrator.scan_service import launch_scan

        domain = target.domain or target.name
        pipeline_id = str(uuid.uuid4())  # Generar un pipeline_id único por target
        target._pipeline_id = pipeline_id  # Guardar para usar en hooks posteriores

        logger.info("[RECON] Starting pipeline %s for %s (mode=%s)", pipeline_id[:8], target.name, mode)

        # Asociar pipeline_id con target_id para futuras etapas
        self._target_pipelines[target.id] = pipeline_id

        # Emitir evento de inicio de pipeline para este target
        try:
            bus = get_event_bus()
            bus.publish(
                EventType.PIPELINE_START.value,
                pipeline_id=pipeline_id,
                target_id=target.id,
                target_name=target.name,
                timestamp=datetime.now(UTC).timestamp(),
                source="ScanScheduler",
            )
            logger.info(
                "[SCHEDULER->EVENTBUS] Emitted %s for pipeline %s (target %s)",
                EventType.PIPELINE_START.value,
                pipeline_id[:8],
                target.name,
            )
        except Exception:
            logger.exception("Failed to publish pipeline:start event for target %s", target.name)

        try:
            await launch_scan(
                target_name=target.name,
                target_domain=domain,
                target_mode=mode,
                session=session,
            )
            # Emitir evento de etapa completada para 'discover' (que el scraper ya hizo)
            self._copilot_hook("discover", "completed", pipeline_id=pipeline_id)
            self._copilot_hook("recon", "completed", pipeline_id=pipeline_id)
        except Exception as e:
            logger.warning("[RECON] launch_scan failed for %s: %s", target.name, e)
            self._copilot_hook("recon", "failed", pipeline_id=pipeline_id, error_message=str(e))

    async def _resolve_auth_pair(self, session, target_id: int) -> tuple[dict | None, dict | None]:
        from cores.target_auth.session_resolver import get_session_resolver

        resolver = get_session_resolver()

        baseline_id = (
            session.query(models.TargetIdentity.id)
            .filter(
                models.TargetIdentity.target_id == target_id,
                models.TargetIdentity.is_baseline.is_(True),
                models.TargetIdentity.is_active.is_(True),
            )
            .scalar()
        )

        probe_id = (
            session.query(models.TargetIdentity.id)
            .filter(
                models.TargetIdentity.target_id == target_id,
                models.TargetIdentity.is_baseline.is_(False),
                models.TargetIdentity.is_active.is_(True),
            )
            .scalar()
        )

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

    async def _stage_promote(self):
        logger.info("[PROMOTE] Testing hypotheses against real endpoints...")
        session = db.SessionLocal()
        try:
            from core.pipeline.hypothesis_bridge import run_promote

            stats = await asyncio.to_thread(run_promote, session)
            if stats["findings_created"] > 0:
                logger.info(
                    "[PROMOTE] %d new findings promoted from hypotheses",
                    stats["findings_created"],
                )
                # Emitir evento de etapa completada para cada pipeline activo
                for _target_id, pipeline_id in self._target_pipelines.items():
                    self._copilot_hook("promote", "completed", pipeline_id=pipeline_id)
            else:
                # Si no se crearon hallazgos, no emitimos un evento "completed" global para promote.
                # Se asume que no hay nada que promover para los pipelines activos.
                pass
            self._last_run["promote"] = datetime.now(UTC).timestamp()
        except Exception as e:
            logger.warning("[PROMOTE] Promote stage failed: %s", e)
            # Emitir evento de fallo para cada pipeline activo si la etapa falló globalmente
            for _target_id, pipeline_id in self._target_pipelines.items():
                self._copilot_hook("promote", "failed", pipeline_id=pipeline_id, error_message=str(e))
        finally:
            session.close()

    async def _stage_hypothesis(self):
        logger.info("[HYPOTHESIS] Generating vulnerability hypotheses...")
        session = db.SessionLocal()
        try:
            from cores.engine.hypothesis.generators import generate_hypotheses

            endpoints = session.query(models.Endpoint).filter(models.Endpoint.hypothesis_id.is_(None)).limit(100).all()
            for ep in endpoints:
                try:
                    target = session.query(models.Target).filter(models.Target.id == ep.target_id).first()
                    if not target:
                        continue

                    pipeline_id = self._target_pipelines.get(target.id)  # OBTENER pipeline_id
                    if not pipeline_id:
                        logger.warning(
                            "[HYPOTHESIS] No pipeline_id found for target %d, skipping hypothesis generation.",
                            target.id,
                        )
                        continue

                    ep_dict = {
                        "id": ep.id,
                        "path": ep.path,
                        "method": ep.method,
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
                        self._copilot_hook("hypothesis", "completed", pipeline_id=pipeline_id)  # Emitir evento
                    else:
                        # Fallback: path-based hypothesis for bare endpoints
                        path_h = _path_based_hypothesis(ep, target)
                        if path_h:
                            ep.hypothesis_id = path_h
                            session.commit()
                            self._copilot_hook("hypothesis", "completed", pipeline_id=pipeline_id)  # Emitir evento
                        else:
                            self._copilot_hook(
                                "hypothesis", "failed", pipeline_id=pipeline_id, error_message="No hypothesis generated"
                            )  # Emitir evento
                except Exception as e:
                    logger.debug("Hypothesis gen failed for endpoint %d: %s", ep.id, e)
                    pipeline_id = self._target_pipelines.get(target.id)
                    if pipeline_id:
                        self._copilot_hook(
                            "hypothesis", "failed", pipeline_id=pipeline_id, error_message=str(e)
                        )  # Emitir evento
            self._last_run["hypothesis"] = datetime.now(UTC).timestamp()
        finally:
            session.close()

    async def _stage_auto_validate(self):
        """Ejecuta el Validation Engine sobre hypotheses generadas.

        Corre después de _stage_hypothesis. Toma las hypotheses de la DB
        las convierte a AttackCandidates y ejecuta el Validation Engine.
        Las que pasan el filtro económico y confianza se promueven a Finding.
        """
        logger.info("[AUTO_VALIDATE] Running Validation Engine on hypotheses...")
        session = db.SessionLocal()
        try:
            from core.validation.bridge import ValidationBridge

            bridge = ValidationBridge()

            # Endpoints con hypothesis pero sin validation ejecutada
            endpoints = session.query(models.Endpoint).filter(models.Endpoint.hypothesis_id.isnot(None)).limit(50).all()
            if not endpoints:
                logger.info("[AUTO_VALIDATE] No endpoints with hypotheses to validate")
                return

            eps_by_target: dict[int, list[dict]] = {}
            for ep in endpoints:
                eps_by_target.setdefault(ep.target_id or 0, []).append(
                    {
                        "path": ep.path,
                        "method": ep.method or "GET",
                        "host": "",
                        "target_id": ep.target_id or 0,
                    }
                )

            for target_id, eps in eps_by_target.items():
                target = session.query(models.Target).filter(models.Target.id == target_id).first()
                host = target.domain if target else ""

                for ep in eps:
                    ep["host"] = host

                logger.info("[AUTO_VALIDATE] Target %d: %d endpoints → validating...", target_id, len(eps))
                results = bridge.validate_batch(eps, target_id=target_id, session=session, dry_run=False)

                promoted = sum(1 for r in results if r.promoted)
                for r in results:
                    if r.promoted and r.confidence:
                        logger.info(
                            "[AUTO_VALIDATE] ✅ %s %s → Finding creado (confianza=%.0f%%)",
                            r.candidate.method if r.candidate else "?",
                            r.candidate.endpoint_path if r.candidate else "?",
                            r.confidence.score * 100,
                        )

                logger.info(
                    "[AUTO_VALIDATE] Target %d: %d validated, %d promoted to Finding",
                    target_id,
                    len(results),
                    promoted,
                )

            self._last_run["auto_validate"] = datetime.now(UTC).timestamp()
        except Exception as exc:
            logger.exception("[AUTO_VALIDATE] Failed: %s", exc)
            raise
        finally:
            session.close()

    async def _stage_validate(self):
        logger.info("[VALIDATE] Running scope-aware validation...")
        session = db.SessionLocal()
        try:
            from cores.validation.loop_engine import ValidationLoopEngine
            from cores.validation.replayer import AuthContext
            from cores.validation.verdict_handler import VerdictHandler

            findings = (
                session.query(models.Finding)
                .filter(models.Finding.status == "open")
                .filter(models.Finding.severity.in_(["high", "critical"]))
                .limit(20)
                .all()
            )
            engine = ValidationLoopEngine()
            handler = VerdictHandler(session)
            for f in findings:
                pipeline_id = None  # Inicializar pipeline_id
                if f.target_id:
                    pipeline_id = self._target_pipelines.get(f.target_id)  # OBTENER pipeline_id

                if not pipeline_id:
                    logger.warning(
                        "[VALIDATE] No pipeline_id found for finding %d (target %d), skipping validation.",
                        f.id,
                        f.target_id,
                    )
                    continue

                try:
                    ep = (
                        session.query(models.Endpoint).filter(models.Endpoint.id == f.endpoint_id).first()
                        if f.endpoint_id
                        else None
                    )
                    if not ep:
                        self._copilot_hook(
                            "validate",
                            "failed",
                            pipeline_id=pipeline_id,
                            error_message=f"Endpoint not found for finding {f.id}",
                        )
                        continue
                    vt = getattr(f, "vulnerability_type", None) or "unknown"
                    endpoint_details = {
                        "url": getattr(ep, "url", ""),
                        "method": getattr(ep, "method", "GET"),
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
                    verdict = engine.evaluate(
                        hot_path_id=f"finding_{f.id}",
                        endpoint_details=endpoint_details,
                        endpoint_signals={},
                        auth_baseline=auth_baseline,
                        auth_probe=auth_probe,
                        vulnerability_type=vt,
                    )
                    handler.process_verdict(
                        verdict=verdict,
                        endpoint_id=ep.id,
                        target_id=f.target_id,
                        evidence_records=[],
                        comparison_summary={"vulnerability_type": vt},
                    )
                    # Si la validación fue exitosa (el handler procesó el veredicto sin error)
                    self._copilot_hook("validate", "completed", pipeline_id=pipeline_id)
                except Exception as e:
                    logger.debug("Validation failed for finding %d: %s", f.id, e)
                    self._copilot_hook("validate", "failed", pipeline_id=pipeline_id, error_message=str(e))
            self._last_run["validate"] = datetime.now(UTC).timestamp()
        finally:
            session.close()

    async def _stage_report(self):
        logger.info("[REPORT] Generating reports...")
        session = db.SessionLocal()
        try:
            from cores.pipeline.report_service import create_report_from_findings

            confirmed_findings = (
                session.query(models.Finding).filter(models.Finding.status == "confirmed").limit(50).all()
            )
            for f in confirmed_findings:
                pipeline_id = None  # Inicializar pipeline_id
                if f.target_id:
                    pipeline_id = self._target_pipelines.get(f.target_id)  # OBTENER pipeline_id

                if not pipeline_id:
                    logger.warning(
                        "[REPORT] No pipeline_id found for finding %d (target %d), skipping report generation.",
                        f.id,
                        f.target_id,
                    )
                    continue

                try:
                    report = create_report_from_findings(
                        session=session,
                        finding_ids=[f.id],
                        extra={
                            "program": "",
                            "target": f"target_{f.target_id}",
                            "vulnerability": f.title or f"Finding #{f.id}",
                            "severity": f.severity or "medium",
                        },
                    )
                    if report:
                        try:
                            from cores.events.event_bus import get_event_bus

                            bus = get_event_bus()
                            bus.publish(
                                "report:generated",
                                {
                                    "finding_id": f.id,
                                    "report_id": report.get("id"),
                                    "status": "draft",
                                },
                            )
                            self._copilot_hook("report", "completed", pipeline_id=pipeline_id)  # Emitir evento

                            # Acceptance prediction (no-op if no data yet)
                            try:
                                from core.reports.acceptance.learner import AcceptanceLearner
                                from core.reports.quality.scorer import QualityScorer

                                learner = AcceptanceLearner(load_persisted=True)
                                scorer = QualityScorer()
                                qs = scorer.score(f.id)
                                pred = learner.predict(
                                    platform="unknown",
                                    score=qs.score if qs else 0.0,
                                    dimensions=qs.dimensions if qs else {},
                                    evidence_count=qs.evidence_count if qs else 0,
                                )
                                logger.info(
                                    "[REPORT] Acceptance prediction for finding %d: %.0f%% (%s) — %s",
                                    f.id,
                                    pred.probability,
                                    pred.confidence,
                                    "; ".join(pred.recommendations[:2]) if pred.recommendations else "no data yet",
                                )
                            except Exception:
                                logger.debug("[REPORT] Acceptance prediction not available for finding %d", f.id)
                        except Exception:
                            logger.exception("Failed to publish report:generated event")
                            self._copilot_hook(
                                "report",
                                "failed",
                                pipeline_id=pipeline_id,
                                error_message="Failed to publish report:generated event",
                            )  # Emitir evento
                    else:
                        self._copilot_hook(
                            "report",
                            "failed",
                            pipeline_id=pipeline_id,
                            error_message="Report generation returned no report",
                        )  # Emitir evento
                except Exception as e:
                    logger.debug("Report generation failed for finding %d: %s", f.id, e)
                    self._copilot_hook(
                        "report", "failed", pipeline_id=pipeline_id, error_message=str(e)
                    )  # Emitir evento
            self._last_run["report"] = datetime.now(UTC).timestamp()
        finally:
            session.close()

    async def _stage_ai_bounty(self):
        logger.info("[AI_BOUNTY] Checking AI bounty programs...")
        try:
            from core.ai_bounty.engine import AIBountyEngine

            engine = AIBountyEngine()
            challenges = engine.discover_all()
            logger.info("[AI_BOUNTY] %d AI bounty programs tracked", len(challenges))

            total_findings = 0
            for c in challenges:
                if not c.targets:
                    logger.info("[AI_BOUNTY] %s/%s: no targets to scan", c.platform, c.challenge_id)
                    continue

                logger.info(
                    "[AI_BOUNTY] Scanning %s/%s: %d targets — %s",
                    c.platform,
                    c.challenge_id,
                    len(c.targets),
                    ", ".join(c.targets),
                )

                scan_result = engine.scan_challenge(
                    platform=c.platform,
                    challenge_id=c.challenge_id,
                )
                findings = scan_result.get("findings", [])
                errors = scan_result.get("errors", [])
                total_findings += len(findings)

                if findings:
                    logger.info(
                        "[AI_BOUNTY] %s/%s: %d findings (%.0fms)",
                        c.platform,
                        c.challenge_id,
                        len(findings),
                        scan_result.get("scan_duration_ms", 0),
                    )
                if errors:
                    for err in errors:
                        logger.warning("[AI_BOUNTY] %s/%s scan error: %s", c.platform, c.challenge_id, err)

                result = engine.assess_opportunity(c.platform, c.challenge_id)
                if result.get("recommended_action") in ("high_priority", "worth_pursuing"):
                    logger.info(
                        "[AI_BOUNTY] %s/%s: EV=$%s/h — %s",
                        c.platform,
                        c.challenge_id,
                        result.get("expected_value_per_hour", 0),
                        result.get("recommended_action"),
                    )

            stats = engine.get_stats()
            logger.info(
                "[AI_BOUNTY] Stats: %d scans, %d findings (%d new), %d reports queued",
                stats.get("total_scans", 0),
                stats.get("total_findings", 0),
                total_findings,
                stats.get("total_reports_queued", 0),
            )

            self._last_run["ai_bounty"] = datetime.now(UTC).timestamp()
        except ImportError as exc:
            logger.warning("[AI_BOUNTY] Module not available: %s", exc)
        except Exception as exc:
            logger.warning("[AI_BOUNTY] Stage failed: %s", exc)
            logger.debug("[AI_BOUNTY] Stage failure detail:", exc_info=True)


# Tech tag → vuln type mapping bridges technology fingerprinting with
# historical payout data from RewardLearner. When we detect a target
# uses "graphql", for example, we boost its priority if IDOR findings
# have historically paid well (via RewardLearner adjustment factors).
_TECH_TO_VULN: dict[str, list[str]] = {
    "api": ["idor", "auth_bypass"],
    "rest": ["idor", "auth_bypass"],
    "graphql": ["idor", "injection", "auth_bypass"],
    "aws": ["ssrf"],
    "gcp": ["ssrf"],
    "azure": ["ssrf"],
    "cloud": ["ssrf"],
    "react": ["xss"],
    "vue": ["xss"],
    "angular": ["xss"],
    "wordpress": ["xss", "sqli"],
    "drupal": ["xss", "sqli"],
    "cms": ["xss", "sqli"],
    "spring": ["idor", "auth_bypass", "sqli"],
    "java": ["idor", "sqli"],
    "django": ["idor", "sqli", "xss"],
    "python": ["idor", "sqli", "ssrf"],
    "rails": ["idor", "ssrf", "sqli"],
    "ruby": ["idor", "ssrf", "sqli"],
    "laravel": ["sqli", "xss", "idor"],
    "php": ["sqli", "xss", "idor"],
    "jwt": ["auth_bypass"],
    "oauth": ["auth_bypass"],
    "saml": ["auth_bypass"],
    "docker": ["ssrf"],
    "kubernetes": ["ssrf"],
    "mysql": ["sqli"],
    "postgres": ["sqli"],
    "mongo": ["sqli"],
    "mobile": ["idor", "auth_bypass"],
}


def _compute_tech_adjustment(tech_tags: str, adjustments: dict[str, float]) -> float:
    """Blend RewardLearner adjustment factors matched via technology tags.

    For each known technology detected in the target, looks up which
    vulnerability types are commonly associated with it, then applies
    the highest RewardLearner adjustment factor found. This means a
    target running GraphQL+Spring will get the IDOR boost if IDOR
    findings have historically paid well, even without a specific
    hypothesis yet.
    """
    if not tech_tags:
        return 1.0
    tags_lower = tech_tags.lower()
    best = 1.0
    for tag, vulns in _TECH_TO_VULN.items():
        if tag in tags_lower:
            for v in vulns:
                vadj = adjustments.get(v, 1.0)
                if vadj > best:
                    best = vadj
    return best


def _compute_target_priorities(targets: list) -> dict[int, float]:
    """Compute per-target priority using TargetIntel + RewardLearner + ORION.

    Priority formula for each target:
      1.0
      × TargetIntel.roi_score multiplier      (financial history)
      × TargetIntel.quality_score multiplier  (program quality)
      × TargetIntel.attack_surface multiplier (more endpoints = more surface)
      × Tech-tuned RewardLearner adjustment  (what vuln types pay)
      × Program.orion_score multiplier        (program-level signal)
      × ORION next_action boost              (strategic recommendation)

    Result clamped to [0.1, 10.0].
    """
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
        logger.exception("Failed to get ORION next action")

    # Pre-load Program orion_scores and TargetIntel in bulk
    program_scores: dict[int, float] = {}
    target_intel_map: dict[int, TargetIntel] = {}
    try:
        from database import db as _db

        _db.init_db()
        session = _db.SessionLocal()

        for t in targets:
            domain = (getattr(t, "domain", None) or "").strip()

            # Match TargetIntel by domain first, fallback to name
            intel: TargetIntel | None = None
            if domain:
                intel = session.query(TargetIntel).filter(TargetIntel.domain == domain).first()
            if intel is None:
                intel = session.query(TargetIntel).filter(TargetIntel.name == t.name).first()
            if intel is not None:
                target_intel_map[t.id] = intel

            # Load Program orion_score
            if domain:
                prog = (
                    session.query(_db.models_economic.Program)
                    .filter(_db.models_economic.Program.domain == domain)
                    .first()
                )
                if prog is not None and getattr(prog, "orion_score", 0):
                    program_scores[t.id] = prog.orion_score

        session.close()
    except Exception:
        program_scores = {}

    priorities: dict[int, float] = {}
    for t in targets:
        score = 1.0
        intel = target_intel_map.get(t.id)

        if intel is not None:
            if intel.roi_score is not None:
                score *= 0.5 + (intel.roi_score / 100) * 1.5
            if intel.quality_score is not None:
                score *= 0.5 + (intel.quality_score / 100) * 1.0
            if intel.attack_surface_score is not None:
                score *= 0.8 + intel.attack_surface_score * 0.2
            if intel.technology_tags:
                score *= _compute_tech_adjustment(intel.technology_tags, adjustments)

        orion = program_scores.get(t.id)
        if orion is not None and orion > 0:
            score *= 0.5 + (orion * 1.5)

        if orion_next_name and t.name and t.name.lower() in orion_next_name:
            score *= 1.5

        priorities[t.id] = round(max(0.1, min(score, 10.0)), 2)

    if orion_next:
        logger.info(
            "[ORION] Next action recommendation: %s (score=%.4f, why=%s)",
            orion_next.get("title"),
            0.0,
            orion_next.get("why_now", ""),
        )

    return priorities
