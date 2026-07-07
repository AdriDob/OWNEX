from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.execution.request_mutator import RequestMutator

logger = logging.getLogger("cateye.api.validation")

router = APIRouter(prefix="/api/validation", tags=["validation"])


class AuthContextModel(BaseModel):
    token: str | None = None
    label: str = "baseline"


class ValidateHotPathRequest(BaseModel):
    hot_path_id: str
    endpoint_id: int
    target_id: int
    url: str
    method: str = "GET"
    headers: dict[str, str] | None = None
    params: dict[str, Any] | None = None
    body: str | None = None
    # Legacy: raw token strings
    auth_baseline_token: str | None = None
    auth_baseline_label: str = "baseline"
    auth_probe_token: str | None = None
    auth_probe_label: str = "probe"
    # Phase 2: identity-based auth (preferred)
    identity_baseline_id: int | None = None
    identity_probe_id: int | None = None
    mutations: dict[str, Any] | None = None
    min_attempts: int = 3


def _resolve_auth(
    identity_id: int | None,
    raw_token: str | None,
    fallback_label: str,
) -> dict | None:
    """Resolve auth context from identity_id or raw token.

    Returns AuthContext-compatible dict or None.
    """
    if identity_id is not None:
        from cores.target_auth.session_resolver import get_session_resolver
        ctx = get_session_resolver().resolve(identity_id)
        if ctx:
            ctx["label"] = fallback_label
            return ctx
    if raw_token:
        return {"token": raw_token, "cookies": {}, "headers": {}, "label": fallback_label}
    return None


@router.post("/validate")
def validate_and_report(request: ValidateHotPathRequest):
    from cores.pipeline.report_service import generate_and_save_report
    from cores.validation.evidence_builder import EvidenceBuilder
    from cores.validation.loop_engine import ValidationLoopEngine
    from cores.validation.replayer import AuthContext
    from cores.validation.verdict_handler import VerdictHandler
    from database import db, models

    session = db.SessionLocal()
    try:
        endpoint = (
            session.query(models.Endpoint)
            .filter(models.Endpoint.id == request.endpoint_id)
            .first()
        )
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")

        # Use LLM to plan contextual mutations when none provided
        mutations = request.mutations or {}
        if not mutations:
            try:
                mutator = RequestMutator()
                attack_vector, llm_mutations = mutator.plan_mutations(
                    url=request.url,
                    method=request.method,
                    params=request.params or {},
                    headers=request.headers or {},
                )
                if llm_mutations:
                    mutations = llm_mutations
                    logger.info(
                        "LLM mutation plan: %s -> %s",
                        attack_vector, json.dumps(mutations)[:200],
                    )
            except Exception as e:
                logger.warning("LLM mutation planning failed, using defaults: %s", e)

        validation_engine = ValidationLoopEngine()

        baseline = _resolve_auth(
            request.identity_baseline_id,
            request.auth_baseline_token,
            request.auth_baseline_label,
        )
        probe = _resolve_auth(
            request.identity_probe_id,
            request.auth_probe_token,
            request.auth_probe_label,
        )

        if baseline is None and probe is None:
            raise HTTPException(
                status_code=400,
                detail="At least one auth context required: provide identity_baseline_id, auth_baseline_token, or both",
            )

        auth_baseline = AuthContext(
            token=baseline.get("token") if baseline else None,
            cookies=baseline.get("cookies", {}) if baseline else {},
            headers=baseline.get("headers", {}) if baseline else {},
            label=(baseline or {}).get("label", "anonymous"),
        )
        auth_probe = AuthContext(
            token=probe.get("token") if probe else None,
            cookies=probe.get("cookies", {}) if probe else {},
            headers=probe.get("headers", {}) if probe else {},
            label=(probe or {}).get("label", "anonymous"),
        )

        logger.info(
            f"Running validation loop: {request.method} {request.url} "
            f"with {request.min_attempts} attempts "
            f"(baseline={auth_baseline.label}, probe={auth_probe.label})"
        )

        verdict = validation_engine.evaluate(
            hot_path_id=request.hot_path_id,
            endpoint_details={
                "url": request.url,
                "method": request.method,
                "headers": request.headers or {},
                "params": request.params or {},
                "body": request.body,
            },
            endpoint_signals=endpoint.parsed_params,
            auth_baseline=auth_baseline,
            auth_probe=auth_probe,
            mutations=request.mutations or {},
            min_attempts=request.min_attempts,
        )

        evidence_builder = EvidenceBuilder()
        comparison_summary = evidence_builder.build_comparison_summary([])

        handler = VerdictHandler(session=session)
        finding = handler.process_verdict(
            verdict=verdict,
            endpoint_id=request.endpoint_id,
            target_id=request.target_id,
            evidence_records=[],
            comparison_summary=comparison_summary,
        )

        db_verdict = (
            session.query(models.Verdict)
            .filter(models.Verdict.hot_path_id == verdict.hot_path_id)
            .order_by(models.Verdict.id.desc())
            .first()
        )
        verdict_id = db_verdict.id if db_verdict else None

        response = {
            "verdict": {
                "id": verdict_id,
                "status": verdict.status,
                "confidence": verdict.confidence,
                "reason": verdict.reason,
            },
            "evidence": [],
            "validated": True,
        }

        report_id = None
        if verdict.status == "confirmed" and verdict.confidence >= 0.6:
            from cores.pipeline.stages import PipelineContext
            ctx = PipelineContext(
                hot_path_id=request.hot_path_id,
                endpoint_id=request.endpoint_id,
                target_id=request.target_id,
            )
            ctx.finding_id = finding.id if finding else None
            try:
                ctx = generate_and_save_report(
                    session=session,
                    ctx=ctx,
                    verdict=verdict,
                    endpoint=endpoint,
                    findings_data={
                        "verdict": verdict.status,
                        "confidence": verdict.confidence,
                    },
                )
                report_id = ctx.report_id
                response["report_id"] = report_id
            except Exception as e:
                logger.warning(f"Report generation failed: {e}")
                response["report_error"] = str(e)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}") from e
    finally:
        session.close()


class BatchValidateRequest(BaseModel):
    target_id: int
    identity_baseline_id: int
    identity_probe_id: int | None = None
    limit: int = 10
    min_risk_score: float = 25.0


@router.post("/batch")
def batch_validate(request: BatchValidateRequest):
    """Validate all actionable endpoints for a target in batch.

    Uses the identity-based auth (Phase 2). Falls back to anonymous for probe.
    Only processes endpoints with risk_score >= min_risk_score.
    """
    import logging

    from cores.engine.unified_scoring import score as unified_score
    from cores.target_auth.session_resolver import get_session_resolver
    from cores.validation.loop_engine import ValidationLoopEngine
    from cores.validation.replayer import AuthContext
    from cores.validation.verdict_handler import VerdictHandler
    from database import db, models
    logger = logging.getLogger("cateye.api.validation.batch")
    session_db = db.SessionLocal()

    try:
        # Resolve baseline auth once
        resolver = get_session_resolver()
        baseline_ctx = resolver.resolve(request.identity_baseline_id)
        if not baseline_ctx:
            raise HTTPException(status_code=400, detail="Baseline identity has no valid session")

        probe_ctx = resolver.resolve(request.identity_probe_id) if request.identity_probe_id else None

        auth_baseline = AuthContext(
            token=baseline_ctx.get("token"),
            cookies=baseline_ctx.get("cookies", {}),
            headers=baseline_ctx.get("headers", {}),
            label=baseline_ctx.get("label", "baseline"),
        )
        auth_probe = AuthContext(
            token=probe_ctx.get("token") if probe_ctx else None,
            cookies=probe_ctx.get("cookies", {}) if probe_ctx else {},
            headers=probe_ctx.get("headers", {}) if probe_ctx else {},
            label=(probe_ctx or {}).get("label", "anonymous"),
        )

        # Fetch candidate endpoints
        endpoints = (
            session_db.query(models.Endpoint)
            .filter(models.Endpoint.target_id == request.target_id)
            .limit(request.limit)
            .all()
        )

        engine = ValidationLoopEngine()
        results = []

        for ep in endpoints:
            signals = ep.parsed_params
            score_result = unified_score(ep.path, ep.method, signals.get("params", {}))
            risk_score = score_result.get("risk_score", 0)

            if risk_score < request.min_risk_score:
                continue

            hot_path_id = f"batch-{ep.id}"

            verdict = engine.evaluate(
                hot_path_id=hot_path_id,
                endpoint_details={
                    "url": f"https://{ep.path}" if not ep.path.startswith("http") else ep.path,
                    "method": ep.method,
                    "headers": {},
                    "params": signals.get("params", {}),
                    "body": None,
                },
                endpoint_signals=signals,
                auth_baseline=auth_baseline,
                auth_probe=auth_probe,
                mutations={},
                min_attempts=2,
            )

            verdict_handler = VerdictHandler(session=session_db)
            saved_verdict = verdict_handler.process_verdict(verdict, endpoint_id=ep.id, target_id=0, evidence_records=[])

            results.append({
                "endpoint_id": ep.id,
                "path": ep.path,
                "method": ep.method,
                "risk_score": risk_score,
                "verdict": saved_verdict,
            })

        return {"results": results, "total": len(results)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch validation failed: {str(e)}") from e
    finally:
        session_db.close()


class RecordVerificationRequest(BaseModel):
    hypothesis_id: str
    result: str  # confirmed | rejected | inconclusive
    notes: str = ""
    step_statuses: dict[str, str] = {}


@router.post("/record")
def record_verification(request: RecordVerificationRequest):
    """Record the result of a manual verification session.

    Stores the outcome so the learning loop can improve future
    hypothesis scoring based on what was confirmed/rejected.
    """
    import logging

    from cores.intelligence.learning_loop import FeedbackEvent, get_learning_loop
    from cores.validation.llm_analyzer import FeedbackLearner
    logger = logging.getLogger("cateye.api.validation.record")

    valid_results = {"confirmed", "rejected", "inconclusive"}
    if request.result not in valid_results:
        raise HTTPException(status_code=400, detail=f"Invalid result: {request.result}. Must be one of {valid_results}")

    try:
        loop = get_learning_loop()
        event = FeedbackEvent(
            action_id=request.hypothesis_id,
            action_type=f"verification_{request.result}",
            outcome=request.result,
            metadata={
                "hypothesis_id": request.hypothesis_id,
                "notes": request.notes,
                "step_statuses": request.step_statuses,
            },
        )
        loop.record_feedback(event)

        # Run LLM feedback analysis periodically (every 10 events)
        total_events = len(loop._feedback_history)
        if total_events > 0 and total_events % 10 == 0:
            try:
                learner = FeedbackLearner()
                recent = [
                    {
                        "hypothesis_id": e.action_id,
                        "pipeline_verdict": e.action_type.replace("verification_", ""),
                        "human_verdict": e.outcome,
                        "notes": e.metadata.get("notes", ""),
                    }
                    for e in loop._feedback_history[-20:]
                ]
                insights = learner.analyze_verdict_patterns(recent)
                if insights:
                    for ins in insights:
                        logger.info(
                            "Feedback insight: %s (conf_adj=%.2f, sources=%d)",
                            ins.pattern[:80], ins.confidence_adjustment, ins.source_count,
                        )
            except Exception as e:
                logger.warning("Feedback analysis failed: %s", e)

        logger.info("Verification recorded: hypothesis=%s result=%s", request.hypothesis_id, request.result)

        return {
            "success": True,
            "message": f"Verificación registrada como '{request.result}'. El sistema usará este resultado para mejorar futuras hipótesis.",
        }
    except Exception as e:
        logger.error(f"Failed to record verification: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record verification: {str(e)}") from e
