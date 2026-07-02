"""Economic Intelligence API — Money Radar, Program Intelligence, ROI, Financial Dashboard."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func as sa_func
from sqlalchemy.orm import Session

from api.schemas.economic import (
    BountyTierCreate,
    BountyTierOut,
    FinancialSummaryOut,
    MemoryPatternCreate,
    MemoryPatternListOut,
    MemoryPatternOut,
    MoneyRadarOut,
    MoneyRadarProgramOut,
    OpportunityPlanOut,
    ProgramCreate,
    ProgramIntelOut,
    ProgramIntelUpdate,
    ProgramListOut,
    ProgramOut,
    ProgramUpdate,
    ReportPriorityListOut,
    ReportPriorityOut,
    ROISummaryOut,
    ScopeDocumentOut,
)
from cores.ai.provider import get_provider
from database.db import SessionLocal
from database.models_economic import BountyTier, MemoryPattern, Program, ProgramIntel, ReportPriority, ScopeDocument
from database.models import Report

logger = logging.getLogger("catseye.api.economic")

router = APIRouter(prefix="/api/economic", tags=["economic"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════
# PROGRAMS CRUD
# ═══════════════════════════════════════════════════════════════════


@router.get("/programs", response_model=ProgramListOut)
def list_programs(
    platform: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("orion_score"),
    sort_order: str = Query("desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Program)

    if platform:
        q = q.filter(Program.platform == platform)
    if status:
        q = q.filter(Program.status == status)
    if priority:
        q = q.filter(Program.priority == priority)
    if search:
        q = q.filter(Program.name.ilike(f"%{search}%"))

    total = q.count()

    sort_col = getattr(Program, sort_by, Program.orion_score)
    sort_fn = desc if sort_order == "desc" else asc
    items = q.order_by(sort_fn(sort_col)).offset(skip).limit(limit).all()

    out = []
    for p in items:
        tier_count = db.query(sa_func.count(BountyTier.id)).filter(BountyTier.program_id == p.id).scalar() or 0
        out.append(_program_to_out(p, tier_count))

    return ProgramListOut(items=out, total=total)


@router.get("/programs/{program_id}", response_model=ProgramOut)
def get_program(program_id: int, db: Session = Depends(get_db)):
    p = db.query(Program).filter(Program.id == program_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")
    tier_count = db.query(sa_func.count(BountyTier.id)).filter(BountyTier.program_id == p.id).scalar() or 0
    return _program_to_out(p, tier_count)


@router.post("/programs", response_model=ProgramOut, status_code=201)
def create_program(body: ProgramCreate, db: Session = Depends(get_db)):
    existing = db.query(Program).filter(
        Program.name == body.name,
        Program.platform == body.platform,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Program already exists for this platform")

    p = Program(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    logger.info("Created program: %s (%s)", p.name, p.platform)
    return _program_to_out(p, 0)


@router.put("/programs/{program_id}", response_model=ProgramOut)
def update_program(program_id: int, body: ProgramUpdate, db: Session = Depends(get_db)):
    p = db.query(Program).filter(Program.id == program_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")

    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(p, key, val)

    db.commit()
    db.refresh(p)
    tier_count = db.query(sa_func.count(BountyTier.id)).filter(BountyTier.program_id == p.id).scalar() or 0
    return _program_to_out(p, tier_count)


@router.delete("/programs/{program_id}", status_code=204)
def delete_program(program_id: int, db: Session = Depends(get_db)):
    p = db.query(Program).filter(Program.id == program_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")
    db.delete(p)
    db.commit()


# ═══════════════════════════════════════════════════════════════════
# BOUNTY TIERS
# ═══════════════════════════════════════════════════════════════════


@router.get("/programs/{program_id}/tiers", response_model=list[BountyTierOut])
def list_tiers(program_id: int, db: Session = Depends(get_db)):
    tiers = db.query(BountyTier).filter(BountyTier.program_id == program_id).all()
    return [_tier_to_out(t) for t in tiers]


@router.post("/programs/{program_id}/tiers", response_model=BountyTierOut, status_code=201)
def create_tier(program_id: int, body: BountyTierCreate, db: Session = Depends(get_db)):
    p = db.query(Program).filter(Program.id == program_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")
    t = BountyTier(program_id=program_id, **body.model_dump(exclude={"program_id"}))
    db.add(t)
    db.commit()
    db.refresh(t)
    return _tier_to_out(t)


# ═══════════════════════════════════════════════════════════════════
# SCOPE DOCUMENTS
# ═══════════════════════════════════════════════════════════════════


@router.get("/programs/{program_id}/scopes", response_model=list[ScopeDocumentOut])
def list_scopes(program_id: int, db: Session = Depends(get_db)):
    docs = db.query(ScopeDocument).filter(ScopeDocument.program_id == program_id).order_by(desc(ScopeDocument.fetched_at)).all()
    return [_scope_to_out(d) for d in docs]


# ═══════════════════════════════════════════════════════════════════
# PROGRAM INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════


@router.get("/programs/{program_id}/intel", response_model=ProgramIntelOut)
def get_program_intel(program_id: int, db: Session = Depends(get_db)):
    intel = db.query(ProgramIntel).filter(ProgramIntel.program_id == program_id).first()
    if not intel:
        raise HTTPException(status_code=404, detail="Program intelligence not found. Run analysis first.")
    return _intel_to_out(intel)


@router.put("/programs/{program_id}/intel", response_model=ProgramIntelOut)
def update_program_intel(program_id: int, body: ProgramIntelUpdate, db: Session = Depends(get_db)):
    intel = db.query(ProgramIntel).filter(ProgramIntel.program_id == program_id).first()
    if not intel:
        intel = ProgramIntel(program_id=program_id)
        db.add(intel)

    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(intel, key, val)

    intel.last_analyzed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(intel)
    return _intel_to_out(intel)


@router.post("/programs/{program_id}/analyze", response_model=ProgramIntelOut)
def analyze_program(program_id: int, db: Session = Depends(get_db)):
    """Generate AI analysis for a program and create/update its intelligence dossier."""
    p = db.query(Program).filter(Program.id == program_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")

    tiers = db.query(BountyTier).filter(BountyTier.program_id == p.id).all()

    # Build analysis prompt
    prompt = _build_analysis_prompt(p, tiers)
    try:
        provider = get_provider()
        ai_resp = provider.chat([
            {"role": "system", "content": "You are an elite bug bounty intelligence analyst. Be concise and actionable."},
            {"role": "user", "content": prompt},
        ], max_tokens=1024)
        analysis_text = ai_resp or f"Analysis pending. Program: {p.name}, Platform: {p.platform}"
    except Exception as exc:
        logger.warning("AI analysis failed for program %s: %s", p.name, exc)
        analysis_text = f"Analysis pending. Program: {p.name}, Platform: {p.platform}"

    intel = db.query(ProgramIntel).filter(ProgramIntel.program_id == p.id).first()
    if not intel:
        intel = ProgramIntel(program_id=p.id)
        db.add(intel)

    intel.ai_summary = analysis_text
    intel.last_analyzed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(intel)
    logger.info("Program analyzed: %s", p.name)
    return _intel_to_out(intel)


# ═══════════════════════════════════════════════════════════════════
# SCOPE READER — Download, index, summarise, detect changes
# ═══════════════════════════════════════════════════════════════════


@router.post("/programs/{program_id}/read-scope")
def read_program_scope(program_id: int, db: Session = Depends(get_db)):
    """Download and index the program's scope URL. Detect changes from last scan."""
    from cores.scope_reader import read_program_scope as _read_scope

    p = db.query(Program).filter(Program.id == program_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")
    if not p.program_url:
        raise HTTPException(status_code=400, detail="Program has no URL configured")

    # Get previous scope document for change detection
    prev_doc = db.query(ScopeDocument).filter(
        ScopeDocument.program_id == program_id,
    ).order_by(desc(ScopeDocument.fetched_at)).first()

    result = _read_scope(
        url=p.program_url,
        program_name=p.name,
        previous_hash=prev_doc.hash if prev_doc else None,
        previous_text=prev_doc.raw_text if prev_doc else None,
    )

    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])

    # Save to database
    doc = ScopeDocument(
        program_id=program_id,
        original_url=p.program_url,
        content_type=result.get("content_type"),
        raw_text=result["raw_text"],
        summary=result.get("summary", ""),
        hash=result.get("hash", ""),
        assets_extracted=result.get("assets_extracted", "[]"),
        changes_from_previous=result.get("changes_from_previous", "[]"),
    )
    db.add(doc)

    # Update program scope data
    p.last_scope_fetch = datetime.now(timezone.utc)
    p.last_scope_hash = result.get("hash", "")
    if result.get("summary"):
        p.scope_summary = result["summary"]

    # Also update assets from extracted results
    try:
        assets_data = json.loads(result.get("assets_extracted", "[]")) if isinstance(result.get("assets_extracted"), str) else result.get("assets_extracted", {})
        if isinstance(assets_data, dict):
            # Update technologies
            techs = assets_data.get("technologies", [])
            if techs:
                existing_techs = []
                if p.technologies:
                    try:
                        existing_techs = json.loads(p.technologies)
                    except (json.JSONDecodeError, TypeError):
                        existing_techs = []
                merged = list(set(existing_techs + techs))
                p.technologies = json.dumps(merged, ensure_ascii=False)

            # Update assets
            all_assets = []
            for key in ("domains", "wildcards", "urls", "ip_ranges"):
                all_assets.extend(assets_data.get(key, []))
            if all_assets:
                existing_assets = []
                if p.assets:
                    try:
                        existing_assets = json.loads(p.assets)
                    except (json.JSONDecodeError, TypeError):
                        existing_assets = []
                merged_assets = list(set(existing_assets + all_assets))
                p.assets = json.dumps(merged_assets, ensure_ascii=False)
    except Exception as exc:
        logger.warning("Failed to parse assets: %s", exc)

    db.commit()
    db.refresh(doc)

    changes = json.loads(result.get("changes_from_previous", "[]"))
    logger.info("Scope read for %s: %d changes detected", p.name, len(changes))

    return {
        "status": "ok",
        "document_id": doc.id,
        "summary": doc.summary,
        "hash": doc.hash,
        "changes": changes,
        "assets": json.loads(doc.assets_extracted) if doc.assets_extracted else {},
        "fetched_at": doc.fetched_at.isoformat() if doc.fetched_at else None,
    }


# ═══════════════════════════════════════════════════════════════════
# MONEY RADAR — Auto-rank all programs by ORION SCORE
# ═══════════════════════════════════════════════════════════════════


@router.get("/money-radar", response_model=MoneyRadarOut)
def money_radar(
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return all programs ranked by ORION SCORE descending, with EVH and reward data."""
    q = db.query(Program).filter(Program.orion_score >= min_score)

    if platform:
        q = q.filter(Program.platform == platform)
    if status:
        q = q.filter(Program.status == status)
    if search:
        q = q.filter(Program.name.ilike(f"%{search}%"))

    total = q.count()
    items = q.order_by(desc(Program.orion_score)).offset(skip).limit(limit).all()

    out = []
    for p in items:
        # Get best reward tier
        top_tier = db.query(BountyTier).filter(
            BountyTier.program_id == p.id,
            BountyTier.max_reward.isnot(None),
        ).order_by(desc(BountyTier.max_reward)).first()

        tiers = db.query(BountyTier).filter(BountyTier.program_id == p.id).all()

        max_reward = top_tier.max_reward if top_tier else None
        min_reward = top_tier.min_reward if top_tier else None
        reward_currency = top_tier.currency if top_tier else "USD"

        # Compute competition based on platform + program data
        competition = _estimate_competition(p.platform, tiers)

        # Estimate effort hours
        effort = _estimate_effort(p)

        # Compute EVH
        avg_reward = (max_reward or 0) * 0.6  # conservative: 60% of max
        evh_val = (avg_reward * p.orion_score * 0.7) / max(effort, 0.5) if avg_reward > 0 else 0.0

        # Tech summary
        tech_summary = ""
        if p.technologies:
            try:
                tech_list = json.loads(p.technologies)
                tech_summary = ", ".join(tech_list[:5])
            except (json.JSONDecodeError, TypeError):
                tech_summary = p.technologies[:100] if p.technologies else ""

        out.append(MoneyRadarProgramOut(
            id=p.id,
            name=p.name,
            platform=p.platform,
            program_url=p.program_url,
            private=p.private,
            status=p.status,
            orion_score=p.orion_score,
            priority=p.priority,
            max_reward=max_reward,
            min_reward=min_reward,
            reward_currency=reward_currency,
            total_reports=p.total_reports,
            confirmed_reports=p.confirmed_reports,
            total_earned=p.total_earned,
            competition=competition,
            effort_hours=effort,
            evh=round(evh_val, 2),
            technologies_summary=tech_summary,
        ))

    return MoneyRadarOut(
        items=out,
        total=total,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/money-radar/refresh")
def refresh_money_radar(db: Session = Depends(get_db)):
    """Recompute ORION SCORE for all programs."""
    programs = db.query(Program).all()
    updated = 0
    for p in programs:
        tiers = db.query(BountyTier).filter(BountyTier.program_id == p.id).all()
        score = _compute_orion_score(p, tiers)
        p.orion_score = round(score, 4)
        p.priority = _score_to_priority(score)
        updated += 1
    db.commit()
    return {"status": "ok", "programs_scored": updated, "generated_at": datetime.now(timezone.utc).isoformat()}


# ═══════════════════════════════════════════════════════════════════
# FINANCIAL SUMMARY
# ═══════════════════════════════════════════════════════════════════


@router.get("/financial-summary", response_model=FinancialSummaryOut)
def financial_summary(db: Session = Depends(get_db)):
    """Aggregate financial data from reports and programs."""
    from database.models import Report

    reports = db.query(Report).all()

    total_collected = sum(r.confirmed_reward or 0 for r in reports if r.status == "paid")
    total_pending = sum(r.estimated_reward or 0 for r in reports if r.status in ("submitted", "pending", "draft"))
    total_estimated = sum(r.estimated_reward or 0 for r in reports)

    total_hours = db.query(sa_func.sum(Program.total_hours_spent)).scalar() or 0.0
    usd_per_hour = round(total_collected / total_hours, 2) if total_hours > 0 else 0.0

    # Per-program earnings
    programs = db.query(Program).all()
    usd_per_program = {}
    for p in programs:
        if p.total_earned > 0:
            usd_per_program[p.name] = round(p.total_earned, 2)

    # Per-platform earnings
    platform_totals: dict[str, float] = {}
    for p in programs:
        platform_totals[p.platform] = platform_totals.get(p.platform, 0.0) + (p.total_earned or 0.0)
    usd_per_platform = {k: round(v, 2) for k, v in sorted(platform_totals.items(), key=lambda x: -x[1]) if v > 0}

    # Per-vuln-type earnings
    vuln_totals: dict[str, float] = {}
    for r in reports:
        if r.confirmed_reward and r.vulnerability:
            vuln_totals[r.vulnerability] = vuln_totals.get(r.vulnerability, 0.0) + r.confirmed_reward
    usd_per_vuln_type = {k: round(v, 2) for k, v in sorted(vuln_totals.items(), key=lambda x: -x[1]) if v > 0}

    # Best program
    best_prog = max(usd_per_program.items(), key=lambda x: x[1]) if usd_per_program else (None, 0.0)

    # Next action from Orion
    next_action = None
    try:
        from cores.orion import get_next_action
        action = get_next_action()
        if action:
            next_action = action.get("title", action.get("type", "Review opportunities"))
    except Exception:
        next_action = "Review Money Radar for best opportunity"

    return FinancialSummaryOut(
        total_collected=round(total_collected, 2),
        total_pending=round(total_pending, 2),
        total_estimated=round(total_estimated, 2),
        usd_per_hour=usd_per_hour,
        usd_per_program=usd_per_program,
        usd_per_platform=usd_per_platform,
        usd_per_vuln_type=usd_per_vuln_type,
        weekly_earnings=_period_earnings(reports, days=7),
        monthly_earnings=_period_earnings(reports, days=30),
        best_program=best_prog[0],
        next_action=next_action,
    )


# ═══════════════════════════════════════════════════════════════════
# ROI SUMMARY
# ═══════════════════════════════════════════════════════════════════


@router.get("/roi-summary", response_model=ROISummaryOut)
def roi_summary(db: Session = Depends(get_db)):
    """ROI metrics across all activity."""
    from database.models import Report

    reports = db.query(Report).all()
    programs = db.query(Program).all()

    total_earned = sum(r.confirmed_reward or 0 for r in reports if r.status == "paid")
    total_pending = sum(r.estimated_reward or 0 for r in reports if r.status in ("submitted", "pending", "draft"))
    total_spent_hours = db.query(sa_func.sum(Program.total_hours_spent)).scalar() or 0.0

    usd_per_hour = round(total_earned / total_spent_hours, 2) if total_spent_hours > 0 else 0.0
    if usd_per_hour >= 500:
        rating = "EXCELLENT"
    elif usd_per_hour >= 200:
        rating = "GOOD"
    elif usd_per_hour >= 100:
        rating = "FAIR"
    elif usd_per_hour > 0:
        rating = "POOR"
    else:
        rating = "N/A"

    # Best program
    best_prog = max(programs, key=lambda p: p.total_earned or 0) if programs else None
    # Best platform
    platform_earnings: dict[str, float] = {}
    for p in programs:
        platform_earnings[p.platform] = platform_earnings.get(p.platform, 0.0) + (p.total_earned or 0.0)
    best_plat = max(platform_earnings.items(), key=lambda x: x[1]) if platform_earnings else (None, 0.0)

    # Best vuln type
    vuln_earnings: dict[str, float] = {}
    for r in reports:
        if r.confirmed_reward and r.vulnerability:
            vuln_earnings[r.vulnerability] = vuln_earnings.get(r.vulnerability, 0.0) + r.confirmed_reward
    best_vuln = max(vuln_earnings.items(), key=lambda x: x[1]) if vuln_earnings else (None, 0.0)

    accepted = sum(1 for r in reports if r.status == "paid")
    total_report_count = len(reports)
    acceptance_rate = round(accepted / total_report_count, 3) if total_report_count > 0 else 0.0

    return ROISummaryOut(
        total_earned=round(total_earned, 2),
        total_pending=round(total_pending, 2),
        total_spent_hours=round(total_spent_hours, 2),
        usd_per_hour=usd_per_hour,
        usd_per_hour_rating=rating,
        weekly_earnings=_period_earnings(reports, days=7),
        monthly_earnings=_period_earnings(reports, days=30),
        best_program=best_prog.name if best_prog and best_prog.total_earned else None,
        best_program_earned=round(best_prog.total_earned, 2) if best_prog and best_prog.total_earned else 0.0,
        best_platform=best_plat[0],
        best_platform_earned=round(best_plat[1], 2),
        best_vuln_type=best_vuln[0],
        best_vuln_type_earned=round(best_vuln[1], 2),
        acceptance_rate=acceptance_rate,
        report_count=total_report_count,
    )


# ═══════════════════════════════════════════════════════════════════
# MEMORY & PATTERN ENGINE
# ═══════════════════════════════════════════════════════════════════


@router.get("/patterns", response_model=MemoryPatternListOut)
def list_patterns(
    category: str | None = Query(None),
    search: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(MemoryPattern)

    if category:
        q = q.filter(MemoryPattern.category == category)
    if search:
        q = q.filter(MemoryPattern.observation.ilike(f"%{search}%"))
    if min_confidence > 0:
        q = q.filter(MemoryPattern.confidence >= min_confidence)

    total = q.count()
    items = q.order_by(desc(MemoryPattern.confidence)).offset(skip).limit(limit).all()
    return MemoryPatternListOut(
        items=[MemoryPatternOut(
            id=m.id, category=m.category, observation=m.observation,
            context=m.context, confidence=m.confidence,
            evidence_count=m.evidence_count, tags=m.tags,
            source_program_id=m.source_program_id,
            created_at=m.created_at.isoformat() if m.created_at else None,
        ) for m in items],
        total=total,
    )


@router.post("/patterns", response_model=MemoryPatternOut, status_code=201)
def create_pattern(body: MemoryPatternCreate, db: Session = Depends(get_db)):
    existing = db.query(MemoryPattern).filter(
        MemoryPattern.observation == body.observation,
        MemoryPattern.category == body.category,
    ).first()
    if existing:
        existing.evidence_count += 1
        existing.confidence = min(1.0, existing.confidence + 0.05)
        db.commit()
        db.refresh(existing)
        return MemoryPatternOut(
            id=existing.id, category=existing.category,
            observation=existing.observation, context=existing.context,
            confidence=existing.confidence, evidence_count=existing.evidence_count,
            tags=existing.tags, source_program_id=existing.source_program_id,
            created_at=existing.created_at.isoformat() if existing.created_at else None,
        )

    m = MemoryPattern(**body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    logger.info("Memory pattern created: [%s] %s", m.category, m.observation[:60])
    return MemoryPatternOut(
        id=m.id, category=m.category, observation=m.observation,
        context=m.context, confidence=m.confidence, evidence_count=m.evidence_count,
        tags=m.tags, source_program_id=m.source_program_id,
        created_at=m.created_at.isoformat() if m.created_at else None,
    )


@router.delete("/patterns/{pattern_id}", status_code=204)
def delete_pattern(pattern_id: int, db: Session = Depends(get_db)):
    m = db.query(MemoryPattern).filter(MemoryPattern.id == pattern_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Pattern not found")
    db.delete(m)
    db.commit()


# ═══════════════════════════════════════════════════════════════════
# REPORT QUEUE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════


@router.get("/report-queue", response_model=ReportPriorityListOut)
def report_queue(
    min_expected: float = Query(0.0),
    status: str | None = Query(None),
    time_filter: str | None = Query(None),  # immediate, today, this_week, this_month
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Reports sorted by expected value descending — money first."""
    q = db.query(ReportPriority).join(Report, ReportPriority.report_id == Report.id)

    if min_expected > 0:
        q = q.filter(ReportPriority.expected_value >= min_expected)
    if status:
        q = q.filter(Report.status == status)
    if time_filter:
        q = q.filter(ReportPriority.time_to_submit == time_filter)

    total = q.count()
    items = q.order_by(desc(ReportPriority.priority_score)).offset(skip).limit(limit).all()

    out = []
    for rp in items:
        report = db.query(Report).filter(Report.id == rp.report_id).first()
        out.append(ReportPriorityOut(
            id=rp.id, report_id=rp.report_id,
            report_title=(report.summary or report.vulnerability or "Report")[:80] if report else "Unknown",
            report_status=report.status if report else "draft",
            program=report.program if report else "",
            vulnerability=report.vulnerability if report else "",
            estimated_reward=rp.estimated_reward,
            confidence_score=rp.confidence_score,
            acceptance_probability=rp.acceptance_probability,
            expected_value=rp.expected_value,
            priority_score=rp.priority_score,
            priority_rank=rp.priority_rank,
            time_to_submit=rp.time_to_submit,
            reasoning=rp.reasoning,
            last_evaluated=rp.last_evaluated.isoformat() if rp.last_evaluated else None,
        ))

    return ReportPriorityListOut(items=out, total=total)


@router.post("/report-queue/recompute")
def recompute_report_queue(db: Session = Depends(get_db)):
    """Recompute priority for all reports based on expected economic value."""
    reports = db.query(Report).filter(Report.status.in_(["draft", "pending"])).all()
    updated = 0

    for report in reports:
        reward = report.estimated_reward or 0

        # Confidence based on severity
        sev_conf = {"critical": 0.85, "high": 0.7, "medium": 0.5, "low": 0.3}
        confidence = sev_conf.get(report.severity or "medium", 0.5)

        # Acceptance probability based on platform + program history
        acceptance_prob = 0.5
        if report.program:
            prog = db.query(Program).filter(Program.name.ilike(f"%{report.program}%")).first()
            if prog and prog.total_reports > 0:
                acceptance_prob = min(0.95, prog.confirmed_reports / max(prog.total_reports, 1))

        expected_value = reward * acceptance_prob

        # Priority score: expected value normalized to 0-100
        max_expected = db.query(sa_func.max(ReportPriority.expected_value)).scalar() or 1
        priority_score = min(100, (expected_value / max(max_expected, 1)) * 100) if expected_value > 0 else 0

        # Time to submit
        if expected_value >= 1000 and confidence >= 0.7:
            time_to_submit = "immediate"
        elif expected_value >= 500:
            time_to_submit = "today"
        elif expected_value >= 100:
            time_to_submit = "this_week"
        else:
            time_to_submit = "this_month"

        reasoning = f"${reward:.0f} reward × {acceptance_prob:.0%} acceptance prob = ${expected_value:.0f} EV. Confidence: {confidence:.0%}."

        existing = db.query(ReportPriority).filter(ReportPriority.report_id == report.id).first()
        if existing:
            existing.estimated_reward = reward
            existing.confidence_score = confidence
            existing.acceptance_probability = acceptance_prob
            existing.expected_value = expected_value
            existing.priority_score = priority_score
            existing.time_to_submit = time_to_submit
            existing.reasoning = reasoning
            existing.last_evaluated = datetime.now(timezone.utc)
        else:
            rp = ReportPriority(
                report_id=report.id, estimated_reward=reward,
                confidence_score=confidence, acceptance_probability=acceptance_prob,
                expected_value=expected_value, priority_score=priority_score,
                time_to_submit=time_to_submit, reasoning=reasoning,
            )
            db.add(rp)

        updated += 1

    # Re-rank
    all_priorities = db.query(ReportPriority).order_by(desc(ReportPriority.priority_score)).all()
    for i, rp in enumerate(all_priorities):
        rp.priority_rank = i + 1

    db.commit()
    logger.info("Report queue recomputed: %d reports prioritized", updated)
    return {"status": "ok", "reports_prioritized": updated}


# ═══════════════════════════════════════════════════════════════════
# OPPORTUNITY PLANNER — Mission generator
# ═══════════════════════════════════════════════════════════════════


@router.get("/programs/{program_id}/plan", response_model=OpportunityPlanOut)
def generate_opportunity_plan(program_id: int, db: Session = Depends(get_db)):
    """Generate a mission plan for a program: where to start, what to hunt, expected ROI."""
    p = db.query(Program).filter(Program.id == program_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")

    intel = db.query(ProgramIntel).filter(ProgramIntel.program_id == program_id).first()
    tiers = db.query(BountyTier).filter(BountyTier.program_id == program_id).all()

    # Determine best vulnerability types
    techs = []
    if p.technologies:
        try:
            techs = json.loads(p.technologies)
        except (json.JSONDecodeError, TypeError):
            pass

    tech_vuln_map = {
        "graphql": ["IDOR", "Mass Assignment", "Info Disclosure"],
        "rest": ["IDOR", "Broken Access Control", "SQLi"],
        "aws": ["S3 Misconfiguration", "IAM Privilege Escalation"],
        "cloudflare": ["WAF Bypass", "Info Disclosure"],
        "react": ["XSS", "Prototype Pollution", "Client-Side Access Control"],
        "node": ["Prototype Pollution", "Command Injection", "SSRF"],
        "django": ["Mass Assignment", "SQLi", "XSS"],
        "rails": ["Mass Assignment", "SQLi", "Command Injection"],
        "wordpress": ["SQLi", "XSS", "File Upload"],
        "api": ["IDOR", "BOLA", "Rate Limiting", "Auth Bypass"],
    }

    best_vulns = set()
    for tech in techs:
        for key, vulns in tech_vuln_map.items():
            if key in tech.lower():
                best_vulns.update(vulns)

    if not best_vulns:
        best_vulns = {"IDOR", "Broken Access Control", "XSS"}

    # Estimate time
    effort = _estimate_effort(p)
    difficulty_mult = {"easy": 0.7, "medium": 1.0, "hard": 1.5, "expert": 2.0}
    diff = intel.difficulty if intel and intel.difficulty else "medium"
    total_hours = effort * difficulty_mult.get(diff, 1.0)

    # Expected return
    max_reward = max((t.max_reward or 0) for t in tiers) if tiers else 0
    avg_reward = max_reward * 0.5  # conservative
    success_prob = intel.probability_of_success if intel and intel.probability_of_success else 0.3
    exp_return_min = avg_reward * success_prob * 0.5
    exp_return_max = avg_reward * success_prob * 1.5
    ev_per_hour = (avg_reward * success_prob) / max(total_hours, 0.5)

    # Where to start
    start_points = []
    if "graphql" in str(techs).lower():
        start_points.append("Revisar endpoints GraphQL — introspection query, IDOR en mutations")
    if "api" in str(techs).lower() or "rest" in str(techs).lower():
        start_points.append("Probar IDOR en endpoints REST — especialmente los que usan IDs numéricos")
    if any("auth" in t.lower() or "oauth" in t.lower() for t in techs):
        start_points.append("Revisar flujos de autenticación — OAuth misconfiguration, weak JWT")
    if "cloud" in str(techs).lower() or "aws" in str(techs).lower():
        start_points.append("Buscar S3 buckets abiertos, subdominios olvidados")
    start_points.append("Endpoint discovery: buscar endpoints no documentados")
    start_points.append("Revisar cabeceras de seguridad faltantes")

    # Endpoints to review
    endpoints_to_review = []
    if p.assets:
        try:
            assets_data = json.loads(p.assets)
            if isinstance(assets_data, list):
                endpoints_to_review = assets_data[:5]
            elif isinstance(assets_data, dict):
                for key in ("urls", "domains", "wildcards"):
                    endpoints_to_review.extend(assets_data.get(key, [])[:3])
        except (json.JSONDecodeError, TypeError):
            endpoints_to_review = [p.program_url] if p.program_url else []

    if not endpoints_to_review:
        endpoints_to_review = [f"https://{p.name.lower().replace(' ', '')}.com"] if p.name else []

    # Techniques
    techniques = []
    if "idor" in str(best_vulns).lower():
        techniques.append("IDOR: probar IDs secuenciales, UUIDs en endpoints")
    if "xss" in str(best_vulns).lower():
        techniques.append("XSS: input fields, URL params, headers reflejados")
    if "ssrf" in str(best_vulns).lower():
        techniques.append("SSRF: feature que cargue URLs externas, webhooks")
    if not techniques:
        techniques = ["Reconocimiento inicial con katana + gau", "Probar IDOR en endpoints principales"]
    techniques.append("Analizar respuestas en busca de info disclosure")

    # Checklist
    checklist = [
        "Leer scope y exclusiones del programa",
        "Ejecutar reconocimiento pasivo (subfinder, amass, httpx)",
        "Identificar endpoints activos con katana + gau",
        "Probar IDOR en endpoints con IDs numéricos",
        "Revisar autenticación y autorización",
        "Buscar info disclosure en respuestas HTTP",
        f"Enfocar en vulnerabilidades con mayor EV: {', '.join(list(best_vulns)[:3])}",
        "Documentar hallazgos parciales para reportes rápidos",
    ]

    return OpportunityPlanOut(
        program_id=p.id,
        program_name=p.name,
        platform=p.platform,
        orion_score=p.orion_score or 0.0,
        where_to_start="\n".join(start_points),
        endpoints_to_review=endpoints_to_review,
        recommended_techniques=techniques,
        best_vuln_types=sorted(best_vulns),
        estimated_time_hours=round(total_hours, 1),
        expected_return_min=round(exp_return_min, 2),
        expected_return_max=round(exp_return_max, 2),
        expected_value_per_hour=round(ev_per_hour, 2),
        checklist=checklist,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════
# SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════


def _compute_orion_score(p: Program, tiers: list[BountyTier]) -> float:
    """Compute ORION SCORE (0.0–1.0) for a program based on real data.

    Factors:
      - Reward potential (0.30): from bounty tiers
      - Historical success (0.20): from reports/program history
      - Competition (0.15): from platform + program type
      - Time efficiency (0.15): from estimated effort
      - Experience (0.10): from previous earnings + reports
      - Technologies (0.10): from technology diversity
    """
    if not p:
        return 0.0

    # 1. Reward potential (0.30)
    max_reward = max((t.max_reward or 0) for t in tiers) if tiers else 0
    if max_reward >= 10000:
        reward_score = 1.0
    elif max_reward >= 5000:
        reward_score = 0.8
    elif max_reward >= 2000:
        reward_score = 0.6
    elif max_reward >= 1000:
        reward_score = 0.4
    elif max_reward >= 500:
        reward_score = 0.2
    elif max_reward > 0:
        reward_score = 0.1
    else:
        reward_score = 0.3  # unknown rewards = medium

    # 2. Historical success (0.20)
    if p.total_reports > 0 and p.confirmed_reports > 0:
        acceptance = p.confirmed_reports / max(p.total_reports, 1)
        hist_score = min(acceptance * 1.5, 1.0)  # boost good acceptance
    else:
        hist_score = 0.3  # no history = medium uncertainty

    # 3. Competition (0.15)
    competition = _estimate_competition(p.platform, tiers)
    comp_score = 1.0 - competition  # invert: less competition = higher score

    # 4. Time efficiency (0.15)
    effort = _estimate_effort(p)
    time_score = max(0.0, 1.0 - (effort - 1) / 20)  # 1h=1.0, 10h=0.55, 20h=0.05

    # 5. Experience (0.10)
    if p.total_earned and p.total_earned > 0:
        exp_score = min(p.total_earned / 10000, 1.0)  # $10k = 1.0
    else:
        exp_score = 0.2

    # 6. Technologies (0.10)
    tech_score = 0.5
    if p.technologies:
        try:
            techs = json.loads(p.technologies)
            if len(techs) >= 5:
                tech_score = 1.0
            elif len(techs) >= 3:
                tech_score = 0.8
            elif len(techs) >= 1:
                tech_score = 0.6
        except (json.JSONDecodeError, TypeError):
            pass

    score = (
        reward_score * 0.30 +
        hist_score * 0.20 +
        comp_score * 0.15 +
        time_score * 0.15 +
        exp_score * 0.10 +
        tech_score * 0.10
    )

    return max(0.0, min(1.0, score))


def _estimate_competition(platform: str, tiers: list[BountyTier]) -> float:
    """Estimate competition level (0.0 = none, 1.0 = extreme)."""
    platform_base = {
        "hackerone": 0.7,
        "bugcrowd": 0.65,
        "intigriti": 0.5,
        "yeswehack": 0.4,
        "immunefi": 0.6,
        "code4rena": 0.55,
        "synack": 0.5,
    }
    base = platform_base.get(platform.lower(), 0.5)

    # Reduce competition for higher-tier programs (fewer hunters)
    max_reward = max((t.max_reward or 0) for t in tiers) if tiers else 0
    if max_reward >= 10000:
        base *= 0.7  # less competition for high-bounty programs
    elif max_reward <= 500:
        base *= 1.3  # more competition for low-bounty (mass hunting)

    return min(1.0, base)


def _estimate_effort(p: Program) -> float:
    """Estimate effort hours for this program."""
    if p.total_hours_spent > 0 and p.total_reports > 0:
        return max(0.5, p.total_hours_spent / p.total_reports)

    # Default by platform
    defaults = {
        "hackerone": 4.0,
        "bugcrowd": 5.0,
        "intigriti": 6.0,
        "yeswehack": 5.0,
        "immunefi": 8.0,
        "code4rena": 10.0,
    }
    return defaults.get(p.platform.lower(), 5.0)


def _score_to_priority(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _period_earnings(reports, days: int) -> float:
    """Sum confirmed rewards from reports within the last N days."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    total = 0.0
    for r in reports:
        if r.confirmed_reward and r.created_at:
            if hasattr(r.created_at, 'tzinfo') and r.created_at.tzinfo is not None:
                r_created = r.created_at
            else:
                r_created = r.created_at.replace(tzinfo=timezone.utc) if r.created_at else None
            if r_created and r_created >= cutoff:
                total += r.confirmed_reward
    return round(total, 2)


def _build_analysis_prompt(p: Program, tiers: list[BountyTier]) -> str:
    """Build AI analysis prompt for a program."""
    tier_info = "\n".join(
        f"  - {t.tier_name}: ${t.min_reward} – ${t.max_reward or 'N/A'} ({t.currency})"
        for t in tiers
    ) if tiers else "  (no tier data)"

    tech_info = ""
    if p.technologies:
        try:
            techs = json.loads(p.technologies)
            tech_info = f"Technologies: {', '.join(techs)}"
        except (json.JSONDecodeError, TypeError):
            pass

    scope_text = p.scope_summary or "(not indexed)"
    exclude_text = p.exclusions_text or "(none listed)"

    return f"""You are an elite bug bounty intelligence analyst. Analyze this program and produce a concise intelligence summary.

Program: {p.name}
Platform: {p.platform}
Status: {p.status}
Private: {p.private}
URL: {p.program_url or 'N/A'}

{tech_info}

Scope:
{scope_text[:2000]}

Exclusions:
{exclude_text[:1000]}

Bounty Tiers:
{tier_info}

Reports submitted: {p.total_reports}
Confirmed: {p.confirmed_reports}
Total earned: ${p.total_earned:.2f}

Your analysis must cover:
1. Program overview and potential
2. Most promising attack surfaces
3. Technologies and their common vulnerabilities
4. Risk assessment (difficulty, competition, time investment)
5. Recommended approach (where to start, what to look for)
6. Estimated ROI potential

Keep it concise and actionable."""


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════


def _program_to_out(p: Program, tier_count: int = 0) -> ProgramOut:
    return ProgramOut(
        id=p.id,
        name=p.name,
        platform=p.platform,
        platform_program_id=p.platform_program_id,
        program_url=p.program_url,
        private=p.private or False,
        status=p.status or "active",
        scope_summary=p.scope_summary,
        rewards_text=p.rewards_text,
        exclusions_text=p.exclusions_text,
        policy_text=p.policy_text,
        technologies=p.technologies,
        assets=p.assets,
        orion_score=p.orion_score or 0.0,
        priority=p.priority or "medium",
        total_reports=p.total_reports or 0,
        confirmed_reports=p.confirmed_reports or 0,
        total_earned=p.total_earned or 0.0,
        total_hours_spent=p.total_hours_spent or 0.0,
        last_scope_fetch=p.last_scope_fetch.isoformat() if p.last_scope_fetch else None,
        created_at=p.created_at.isoformat() if p.created_at else None,
        updated_at=p.updated_at.isoformat() if p.updated_at else None,
        tier_count=tier_count,
    )


def _tier_to_out(t: BountyTier) -> BountyTierOut:
    return BountyTierOut(
        id=t.id,
        program_id=t.program_id,
        tier_name=t.tier_name,
        min_reward=t.min_reward,
        max_reward=t.max_reward,
        currency=t.currency or "USD",
        requirements=t.requirements,
        created_at=t.created_at.isoformat() if t.created_at else None,
    )


def _scope_to_out(d: ScopeDocument) -> ScopeDocumentOut:
    return ScopeDocumentOut(
        id=d.id,
        program_id=d.program_id,
        original_url=d.original_url,
        content_type=d.content_type,
        summary=d.summary,
        hash=d.hash,
        assets_extracted=d.assets_extracted,
        changes_from_previous=d.changes_from_previous,
        fetched_at=d.fetched_at.isoformat() if d.fetched_at else None,
        created_at=d.created_at.isoformat() if d.created_at else None,
    )


def _intel_to_out(i: ProgramIntel) -> ProgramIntelOut:
    return ProgramIntelOut(
        id=i.id,
        program_id=i.program_id,
        ai_summary=i.ai_summary,
        technologies_list=i.technologies_list,
        recent_changes=i.recent_changes,
        historical_bugs=i.historical_bugs,
        public_reports=i.public_reports,
        hypotheses=i.hypotheses,
        interesting_endpoints=i.interesting_endpoints,
        notes=i.notes,
        pending_ideas=i.pending_ideas,
        score=i.score or 0.0,
        priority=i.priority or "medium",
        last_analyzed_at=i.last_analyzed_at.isoformat() if i.last_analyzed_at else None,
        updated_at=i.updated_at.isoformat() if i.updated_at else None,
    )


# ═══════════════════════════════════════════════════════════════════
# BANK ACCOUNT — Payout/withdrawal account info
# ═══════════════════════════════════════════════════════════════════


@router.get("/bank-account")
def get_bank_account():
    """Get linked bank/payout account info."""
    from database.models import RastroConfig

    session = SessionLocal()
    try:
        row = session.query(RastroConfig).filter(RastroConfig.key == "connections.payout_accounts").first()
        accounts = json.loads(row.value) if row and row.value else []
        default = next((a for a in accounts if a.get("is_default")), None) or (accounts[0] if accounts else None)
        if default:
            return BankAccountOut(
                connected=True,
                bank_name=default.get("bank_name", default.get("label", "")),
                last_four=default.get("last_four", ""),
                currency=default.get("currency", "USD"),
                withdrawable=default.get("withdrawable", 0),
                pending=0,
            )
        return BankAccountOut(connected=False)
    except Exception:
        return BankAccountOut(connected=False)
    finally:
        session.close()


class BankAccountOut:
    def __init__(self, connected: bool = False, **kwargs):
        self.connected = connected
        self.bank_name = kwargs.get("bank_name", "")
        self.last_four = kwargs.get("last_four", "")
        self.currency = kwargs.get("currency", "USD")
        self.withdrawable = kwargs.get("withdrawable", 0)
        self.pending = kwargs.get("pending", 0)


@router.get("/monthly-revenue")
def get_monthly_revenue():
    """Return real monthly revenue data aggregated from report table."""
    from database.db import SessionLocal
    from database.models import Report
    from sqlalchemy import extract

    session = SessionLocal()
    try:
        rows = (
            session.query(
                extract("year", Report.created_at).label("year"),
                extract("month", Report.created_at).label("month"),
                sa_func.coalesce(sa_func.sum(Report.confirmed_reward), 0).label("paid"),
                sa_func.coalesce(sa_func.sum(Report.estimated_reward), 0).label("estimated"),
                sa_func.count(Report.id).label("count"),
            )
            .filter(Report.created_at.isnot(None))
            .group_by("year", "month")
            .order_by(extract("year", Report.created_at), extract("month", Report.created_at))
            .all()
        )

        months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        result = []
        for r in rows:
            label = f"{months[int(r.month) - 1]}" if r.month and 1 <= int(r.month) <= 12 else str(r.month)
            if r.year:
                label += f" {int(r.year)}"
            result.append({
                "month": label,
                "amount": float(r.estimated or 0),
                "paid": float(r.paid or 0),
                "count": int(r.count or 0),
                "year": int(r.year) if r.year else None,
            })

        return {"months": result, "total": len(result)}
    except Exception as exc:
        logger.warning("Failed to aggregate monthly revenue: %s", exc)
        return {"months": [], "total": 0}
    finally:
        session.close()
