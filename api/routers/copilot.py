"""COPILOT API — reasoning, chat, execution, context."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.copilot.hermes_bridge import get_hermes_bridge
from core.copilot.opencode_bridge import get_opencode_bridge
from core.copilot.orion_context import get_orion_context
from core.copilot.providers.router import get_provider_router

logger = logging.getLogger("ownex.api.copilot")

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    task_type: str = "chat"


class ExecuteRequest(BaseModel):
    action: str
    params: dict[str, Any] = {}


class ComputerUseRequest(BaseModel):
    """Request for autonomous desktop control."""

    task: str
    max_steps: int = 20
    model: str = "moondream"
    vision_provider: str = "ollama"  # "ollama" | "openai_compatible"
    api_url: str = ""
    api_key: str = ""
    dry_run: bool = False


class IncomeGoalRequest(BaseModel):
    """Natural-language income goal ("quiero ganar 10k este mes") o valores explícitos."""

    message: str = ""
    target_usd: float | None = None
    period: str | None = None  # "weekly" | "monthly"


_copilot_instance: Any = None


def _set_copilot(instance: object) -> None:
    global _copilot_instance
    _copilot_instance = instance


@router.get("/status")
def copilot_status():
    if _copilot_instance is None:
        return {"status": "unavailable", "agent_id": None, "authority": None}
    try:
        d = _copilot_instance.to_dict()
        return {
            "status": "active",
            "agent_id": d.get("agent_id"),
            "authority": d.get("authority"),
            "config": d.get("config"),
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/recommendations")
def copilot_recommendations():
    if _copilot_instance is None:
        return {"status": "unavailable", "recommendations": []}
    try:
        from database import db

        actions = _copilot_instance.recommend_for_system(db_factory=db.SessionLocal)
        return {"status": "ok", "recommendations": actions}
    except Exception as exc:
        logger.warning("[COPILOT] Recommendations error: %s", exc)
        return {"status": "error", "recommendations": [], "detail": str(exc)}


@router.get("/context")
def get_orion_system_context():
    """Return aggregated ORION system context."""
    try:
        ctx = get_orion_context()
        return {"status": "ok", "context": ctx.get_context(force_refresh=True)}
    except Exception as exc:
        logger.warning("[COPILOT] Context error: %s", exc)
        return {"status": "error", "detail": str(exc)}


@router.get("/context/llm")
def get_orion_context_for_llm():
    """Return ORION context formatted as prompt-friendly text."""
    try:
        ctx = get_orion_context()
        return {"status": "ok", "context": ctx.format_for_llm(force_refresh=True)}
    except Exception as exc:
        logger.warning("[COPILOT] Context LLM error: %s", exc)
        return {"status": "error", "detail": str(exc)}


@router.post("/chat")
async def copilot_chat(body: ChatRequest):
    """Multi-provider chat. Routes by task_type: chat/Ollama, reason/FCC, code/OpenCode."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        router_prov = get_provider_router()
        history = [{"role": m.role, "content": m.content} for m in body.history]
        messages = history + [{"role": "user", "content": body.message}]

        result = await router_prov.route(task_type=body.task_type, messages=messages)
        return {
            "status": "ok" if not result.error else "error",
            "response": result.content,
            "provider": result.provider,
            "model": result.model,
            "duration_ms": result.duration_ms,
            "error": result.error,
        }
    except Exception as exc:
        logger.warning("[COPILOT] Chat error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/chat/stream")
async def copilot_chat_stream(body: ChatRequest):
    """SSE streaming chat via provider router."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    async def event_stream():
        router_prov = get_provider_router()
        history = [{"role": m.role, "content": m.content} for m in body.history]
        messages = history + [{"role": "user", "content": body.message}]
        try:
            async for token in router_prov.route_stream(task_type=body.task_type, messages=messages):
                yield f"data: {token}\n\n"
        except Exception as exc:
            yield f"data: [ERROR] {exc}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/income-goal")
def copilot_income_goal(body: IncomeGoalRequest):
    """Convert "quiero ganar 10k este mes" into an actionable income plan.

    Accepts natural language (parsed via parse_income_goal) or explicit
    target_usd/period. Returns required opportunities, hours, sources,
    probability of success and current progress toward the target.
    """
    from cores.direct_work_engine.income_target import (
        TargetTier,
        get_income_target_engine,
        parse_income_goal,
    )

    amount = body.target_usd
    period = body.period

    if amount is None or amount <= 0:
        parsed = parse_income_goal(body.message)
        if parsed is None:
            raise HTTPException(
                status_code=400,
                detail="No pude extraer un monto del mensaje. Probá: 'quiero ganar 10k este mes'.",
            )
        amount, parsed_period = parsed
        period = period or parsed_period

    period = period if period in ("weekly", "monthly") else "monthly"

    try:
        engine = get_income_target_engine()
        target = engine.create_target(
            TargetTier.CUSTOM,
            custom_amount=float(amount),
            custom_period=period,
        )
        plan = engine.build_plan(target)
        progress = engine.track_progress(target)
    except Exception as exc:
        logger.warning("[COPILOT] Income goal error: %s", exc)
        raise HTTPException(status_code=500, detail="No se pudo generar el plan de ingreso") from exc

    return {
        "status": "ok",
        "target": {"amount_usd": float(amount), "period": period},
        "required_opportunities": plan.required_opportunities,
        "required_hours_per_week": plan.required_hours_per_week,
        "required_hours_per_day": plan.required_hours_per_day,
        "recommended_sources": plan.recommended_sources,
        "probability_of_success": plan.probability_of_success,
        "risk_factors": plan.risk_factors,
        "fallback_plan": plan.fallback_plan,
        "weekly_plan": plan.weekly_plan,
        "progress": {
            "earned_this_period": progress.earned_this_period,
            "pending_amount": progress.pending_amount,
            "projected_total": progress.projected_total,
            "progress_pct": progress.progress_pct,
            "days_remaining": progress.days_remaining,
            "on_track": progress.on_track,
            "required_daily_rate": progress.required_daily_rate,
            "actual_daily_rate": progress.actual_daily_rate,
        },
    }


@router.post("/execute")
async def copilot_execute(body: ExecuteRequest):
    """Execute an action via Hermes or OpenCode."""
    if not body.action.strip():
        raise HTTPException(status_code=400, detail="Action cannot be empty")

    try:
        if body.action.startswith("hermes:"):
            cmd = body.action.replace("hermes:", "")
            bridge = get_hermes_bridge()
            result = await bridge.execute(cmd, body.params.get("args"))
            return {"status": "ok" if result.get("success") else "error", "action": body.action, "result": result}

        elif body.action.startswith("opencode:"):
            subtask = body.action.replace("opencode:", "")
            bridge = get_opencode_bridge()
            if subtask == "ask":
                result = await bridge.ask(body.params.get("question", ""))
            elif subtask == "implement":
                result = await bridge.implement(body.params.get("description", ""))
            elif subtask == "fix":
                result = await bridge.fix(body.params.get("bug", ""))
            else:
                result = await bridge.run(body.params.get("task", subtask))
            return {"status": "ok" if result.get("success") else "error", "action": body.action, "result": result}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action prefix: {body.action}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("[COPILOT] Execute error: %s", exc)
        return {"status": "error", "action": body.action, "detail": str(exc)}


@router.get("/connections/audit")
def audit_connections():
    """Audit frontend↔backend connection health.

    Returns:
      - API calls from frontend not found in backend
      - Backend routes never consumed by frontend
      - Components referencing data without fetch
    """
    try:
        from core.copilot.connections import run_connection_audit

        return {"status": "ok", "audit": run_connection_audit()}
    except Exception as exc:
        logger.warning("[COPILOT] Connection audit error: %s", exc)
        return {"status": "error", "detail": str(exc)}


@router.get("/connections/audit/frontend")
def audit_frontend_endpoints():
    """List all API endpoints called from frontend."""
    try:
        from core.copilot.connections import _scan_frontend_api_calls

        calls = _scan_frontend_api_calls()
        return {"status": "ok", "count": len(calls), "endpoints": sorted(calls)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/connections/audit/backend")
def audit_backend_routes():
    """List all backend API routes."""
    try:
        from core.copilot.connections import _scan_backend_routes

        routes = _scan_backend_routes()
        return {"status": "ok", "count": len(routes), "routes": sorted(routes)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/vision/analyze")
async def copilot_vision_analyze(path: str):
    """Analyze an image file: OCR, colors, dimensions, layout, vision model."""
    try:
        from core.copilot.vision import analyze_image, describe_for_prompt

        analysis = analyze_image(path)
        prompt_text = describe_for_prompt(path)
        return {"status": "ok", "analysis": analysis, "prompt_context": prompt_text}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/vision/clipboard")
async def copilot_vision_clipboard():
    """Grab image from clipboard and analyze it."""
    try:
        from core.copilot.vision import describe_for_prompt, save_clipboard_image

        saved = save_clipboard_image()
        if saved is None:
            return {"status": "error", "detail": "No image found in clipboard"}
        prompt_text = describe_for_prompt(saved)
        return {"status": "ok", "path": str(saved), "prompt_context": prompt_text}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/vision/status")
def copilot_vision_status():
    """Check available vision capabilities."""
    import subprocess

    caps: dict[str, Any] = {
        "open_cv": False,
        "tesseract_ocr": False,
        "ollama_vision": False,
        "clipboard_support": False,
    }
    try:
        import cv2 as _cv2_check  # noqa: F401

        caps["open_cv"] = True
    except ImportError:
        pass
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        caps["tesseract_ocr"] = True
    except Exception:
        pass
    try:
        import shutil

        for tool in ("wl-paste", "xclip", "osascript"):
            if shutil.which(tool):
                caps["clipboard_support"] = True
                break
    except Exception:
        pass
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        for m in ("moondream", "llava", "minicpm", "qwen2-vl", "bakllava"):
            if m in r.stdout:
                caps["ollama_vision"] = m
                break
    except Exception:
        pass
    return {"status": "ok", "capabilities": caps}


# ── Computer Use (Desktop Automation) ─────────────────────────────


@router.get("/computer-use/status")
def computer_use_status():
    """Check computer use capabilities."""
    try:
        from cores.tools.computer_use import get_computer_use_tool

        tool = get_computer_use_tool()
        return {"status": "ok", "tool": tool.to_dict()}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/computer-use/execute")
async def computer_use_execute(body: ComputerUseRequest):
    """Execute an autonomous desktop task via Computer Use.

    Captures screenshots, analyzes with vision LLM, and executes actions
    (click, type, scroll, etc.) in a perception-action loop.
    """
    try:
        from cores.tools.computer_use import ComputerUseAgent, ComputerUseConfig

        config = ComputerUseConfig(
            max_steps=min(body.max_steps, 50),  # hard cap at 50
            model=body.model,
            vision_provider=body.vision_provider,
            api_url=body.api_url,
            api_key=body.api_key,
            dry_run=body.dry_run,
        )
        agent = ComputerUseAgent(config)
        result = await agent.run(body.task)
        return {"status": "ok", "result": result.to_dict()}
    except Exception as exc:
        logger.warning("[COMPUTER_USE] Execute error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/computer-use/screenshot")
async def computer_use_screenshot():
    """Capture and analyze the current screen."""
    try:
        from core.copilot.vision import analyze_screenshot

        result = analyze_screenshot()
        return {"status": "ok" if "error" not in result else "error", "analysis": result}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


# ── Computer Use Learning ─────────────────────────────────────────


@router.get("/computer-use/learning/stats")
def computer_use_learning_stats():
    """Get learning stats for all platforms."""
    try:
        from cores.computer_use.learning import get_computer_use_learner

        learner = get_computer_use_learner()
        return {"status": "ok", "platforms": learner.get_all_stats()}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/computer-use/learning/{platform}")
def computer_use_learning_platform(platform: str):
    """Get learning stats and recommendation for a specific platform."""
    try:
        from cores.computer_use.learning import get_computer_use_learner

        learner = get_computer_use_learner()
        stats = learner.get_platform_stats(platform)
        recommendation = learner.get_recommendation(platform)
        positions = learner.get_best_positions(platform)
        return {
            "status": "ok",
            "stats": stats,
            "recommendation": recommendation,
            "cached_positions": {k: v.to_dict() for k, v in positions.items()},
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/computer-use/learning/{platform}/records")
def computer_use_learning_records(platform: str, limit: int = 20):
    """Get fill records for a platform."""
    try:
        from cores.computer_use.learning import get_computer_use_learner

        learner = get_computer_use_learner()
        records = learner.get_records(platform=platform, limit=limit)
        return {"status": "ok", "platform": platform, "records": records, "count": len(records)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


# ── Computer Use Screenshot History ──────────────────────────────


@router.get("/computer-use/history")
def computer_use_history(limit: int = 20, platform: str | None = None):
    """List recent Computer Use sessions."""
    try:
        from cores.computer_use.screenshot_history import get_screenshot_history

        history = get_screenshot_history()
        sessions = history.list_sessions(limit=limit, platform=platform)
        stats = history.get_stats()
        return {"status": "ok", "sessions": sessions, "stats": stats}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/computer-use/history/{session_id}")
def computer_use_session(session_id: str):
    """Get a specific session with all screenshots."""
    try:
        from cores.computer_use.screenshot_history import get_screenshot_history

        history = get_screenshot_history()
        session = history.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {"status": "ok", "session": session}
    except HTTPException:
        raise
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/computer-use/history/{session_id}/screenshots")
def computer_use_session_screenshots(session_id: str):
    """Get all screenshots for a session."""
    try:
        from cores.computer_use.screenshot_history import get_screenshot_history

        history = get_screenshot_history()
        screenshots = history.get_screenshots(session_id)
        return {"status": "ok", "session_id": session_id, "screenshots": screenshots, "count": len(screenshots)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/bayesian/summary")
def bayesian_posterior_summary():
    """Return Bayesian posterior distributions for all platforms."""
    try:
        from core.copilot.bayesian import BayesianLearner
        from core.reports.optimizer import get_acceptance_learner

        learner = get_acceptance_learner()
        bl = BayesianLearner()
        for obs in learner.get_observations():
            if isinstance(obs, dict):
                bl.observe(
                    str(obs.get("platform", "?")), str(obs.get("outcome", "")) == "accepted", obs.get("dimensions")
                )
            else:
                bl.observe(str(obs.platform), str(obs.outcome) == "accepted", obs.dimensions)  # type: ignore[union-attr]
        return {"status": "ok", "posteriors": bl.get_posterior_summary()}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/polymarket/strategies")
def polymarket_list_strategies():
    """List available Polymarket strategies."""
    from core.polymarket.manager import list_strategies

    return {"status": "ok", "strategies": list_strategies()}


@router.post("/polymarket/scan")
async def polymarket_scan_strategy(strategy: str = "all"):
    """Run a Polymarket strategy scan."""
    from core.polymarket.manager import PolymarketManager

    mgr = PolymarketManager()
    if strategy == "all":
        return {"status": "ok", "result": await mgr.full_diagnostic()}
    return {"status": "ok", "strategy": strategy, "result": await mgr.run_scan(strategy)}


@router.get("/frontend/component/{path:path}")
def locate_frontend_component(path: str):
    """Locate any frontend file by partial path or component name."""
    import glob as gmod
    from pathlib import Path as PPath

    fe_dir = PPath.home() / "projects" / "Rastro" / "frontend" / "src"

    results = []
    search_patterns = [
        fe_dir / "**" / path,
        fe_dir / "**" / f"{path}.vue",
        fe_dir / "**" / f"{path}.ts",
        fe_dir / "pages" / "**" / f"{path}.vue",
        fe_dir / "components" / "**" / f"{path}.vue",
    ]
    for pat in search_patterns:
        for match in gmod.glob(str(pat), recursive=True):
            p = PPath(match)
            rel = p.relative_to(fe_dir)
            results.append({"path": str(rel), "size": p.stat().st_size, "type": p.suffix})
    return {"status": "ok" if results else "not_found", "query": path, "results": results[:20]}
