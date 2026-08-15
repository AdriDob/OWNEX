"""Guards de DB del hardening pass 2026-08-15.

Cubre tres protecciones contra contaminación/corrupción de la DB real:
1. `create_target` deduplica por nombre (FASE E) — no más targets duplicados.
2. `recover_stale_scans` marca como failed los scans colgados en "running" (FASE C).
3. `convert_to_targets` no inventa dominios `{slug}.com` (FASE A) — skip honesto.

Corren contra la DB temporal aislada (conftest.py setea DATABASE_URL antes de imports).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from api.services.data_service import create_target
from cores.bounty_scraper.scraper import BountyScraper, ScrapedProgram
from cores.orchestrator.scan_service import recover_stale_scans
from database import db, models


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}.example.com"


class TestCreateTargetDedupe:
    def test_returns_existing_on_duplicate_name(self):
        first = create_target("dedupe-target.example.com", "dedupe-target.example.com")
        second = create_target("dedupe-target.example.com", "other-domain.example.com")
        assert second["duplicate"] is True
        assert second["id"] == first["id"]

    def test_creates_when_name_is_unique(self):
        name = _unique_name("unique")
        created = create_target(name, "unique.example.com")
        assert "duplicate" not in created
        assert created["name"] == name
        assert created["id"] > 0


class TestRecoverStaleScans:
    def test_marks_stale_running_as_failed_keeps_fresh(self):
        db.init_db()
        session = db.SessionLocal()
        target = models.Target(name=_unique_name("rec"), domain="rec.example.com")
        session.add(target)
        session.commit()
        session.refresh(target)
        stale = models.ScanRun(
            target_id=target.id,
            mode="FAST",
            status="running",
            started_at=datetime.now(UTC) - timedelta(hours=7),
        )
        fresh = models.ScanRun(
            target_id=target.id,
            mode="FAST",
            status="running",
            started_at=datetime.now(UTC) - timedelta(hours=1),
        )
        session.add_all([stale, fresh])
        session.commit()
        stale_id, fresh_id = stale.id, fresh.id
        session.close()

        recovered = recover_stale_scans(session=db.SessionLocal())

        session = db.SessionLocal()
        assert stale_id in recovered
        assert session.query(models.ScanRun).get(stale_id).status == "failed"
        assert session.query(models.ScanRun).get(stale_id).finished_at is not None
        assert fresh_id not in recovered
        assert session.query(models.ScanRun).get(fresh_id).status == "running"
        session.close()

    def test_idempotent_no_stale_scans(self):
        db.init_db()
        recovered = recover_stale_scans(max_age_hours=9999.0, session=db.SessionLocal())
        assert recovered == []


class TestConvertToTargetsNoFakeDomains:
    def test_skips_programs_without_real_domain(self):
        db.init_db()
        session = db.SessionLocal()
        scraper = BountyScraper()
        no_domain = ScrapedProgram(name="No Domain Program", platform="hackerone", has_rewards=True)
        with_domain = ScrapedProgram(
            name="Real Scope Program",
            platform="hackerone",
            domains=["real.example.com"],
            has_rewards=True,
        )
        created = scraper.convert_to_targets([no_domain, with_domain], session, models)

        assert len(created) == 1
        assert created[0].name == "hackerone_real_scope_program"
        assert created[0].domain == "real.example.com"
        fake = session.query(models.Target).filter(models.Target.name == "hackerone_no_domain_program").first()
        assert fake is None
        session.close()
