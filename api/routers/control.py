"""API Router para el Control Panel: modos, obsidian, vpn, acciones, checks."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("api.control")

router = APIRouter(prefix="/api", tags=["control-panel"])


# ── Mega Fast Mode ───────────────────────────────────────────────


@router.get("/mega-fast/status")
async def mega_fast_status() -> dict[str, Any]:
    """Get Mega Fast Mode status."""
    try:
        from core.mega_fast_mode import get_mega_fast_mode

        return get_mega_fast_mode().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/mega-fast/activate")
async def mega_fast_activate() -> dict[str, Any]:
    """Activate Mega Fast Mode."""
    try:
        from core.mega_fast_mode import get_mega_fast_mode

        mode = get_mega_fast_mode()
        result = mode.activate()
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/mega-fast/deactivate")
async def mega_fast_deactivate() -> dict[str, Any]:
    """Deactivate Mega Fast Mode."""
    try:
        from core.mega_fast_mode import get_mega_fast_mode

        get_mega_fast_mode().deactivate()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── First-Time Mode ──────────────────────────────────────────────


@router.get("/first-time/status")
async def first_time_status() -> dict[str, Any]:
    """Get First-Time Mode status."""
    try:
        from core.first_time_mode import get_first_time_mode

        return get_first_time_mode().get_progress()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/first-time/activate")
async def first_time_activate() -> dict[str, Any]:
    """Activate First-Time Mode."""
    try:
        from core.first_time_mode import get_first_time_mode

        mode = get_first_time_mode()
        result = mode.activate()
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/first-time/deactivate")
async def first_time_deactivate() -> dict[str, Any]:
    """Deactivate First-Time Mode."""
    try:
        from core.first_time_mode import get_first_time_mode

        result = get_first_time_mode().deactivate()
        return {"success": True, **(result or {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── VPN / Argentina access ───────────────────────────────────────


@router.get("/vpn/info")
async def vpn_info() -> dict[str, Any]:
    """Estado VPN real: IP, país, compatibilidad + qué te falta instalar."""
    try:
        from core.vpn_assistant import get_vpn_assistant

        assistant = get_vpn_assistant()
        status = assistant.detect()
        report = assistant.readiness_report()
        return {
            "success": True,
            "os": assistant.os_name,
            "is_wsl": assistant.is_wsl,
            "status": status.to_dict(),
            "options": assistant.free_options(),
            "vpns": report["vpns"],
            "missing_count": report["missing_count"],
            "missing": report["missing"],
            "present": report["present"],
            "vpn_plan": report["plan"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/vpn/check-outlier")
async def vpn_check_outlier() -> dict[str, Any]:
    """Chequear si la IP actual permitiría entrar a Outlier/DataAnnotation."""
    try:
        from core.vpn_assistant import get_vpn_assistant

        return get_vpn_assistant().check_outlier()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/vpn/install-windscribe")
async def vpn_install_windscribe() -> dict[str, Any]:
    """Instalar Windscribe CLI en Linux/WSL (gratis)."""
    try:
        from core.vpn_assistant import get_vpn_assistant

        return get_vpn_assistant().install_windscribe_linux()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Obsidian ─────────────────────────────────────────────────────


@router.post("/obsidian/sync")
async def obsidian_sync() -> dict[str, Any]:
    """Sync memory / notes a Obsidian."""
    try:
        from core.obsidian_sync import ObsidianSync

        syncer = ObsidianSync()
        if not syncer.is_connected:
            return {"success": False, "error": "Vault de Obsidian no detectado"}
        notes = syncer.list_notes()
        return {"success": True, "synced": len(notes), "files": [n.get("title", "") for n in notes][:20]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/vpn/windscribe-connect")
async def vpn_windscribe_connect() -> dict[str, Any]:
    """Detectar/abrir Windscribe en Windows y guiar la conexión a US."""
    try:
        from core.vpn_assistant import get_vpn_assistant

        return get_vpn_assistant().windscribe_on_windows()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/guide/master")
async def master_guide() -> dict[str, Any]:
    """Guía maestra paso a paso con estado real de todas las categorías."""
    try:
        from core.master_guide import master_guide as build_guide

        return build_guide()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Plan de plata ────────────────────────────────────────────────


@router.get("/money-plan")
async def money_plan_get() -> dict[str, Any]:
    """Obtener el plan de plata configurado + proyección semanal."""
    try:
        from core.money_plan import get_money_plan

        plan = get_money_plan()
        return {"success": True, "plan": plan.get(), "projection": plan.project_weekly()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/money-plan/update")
async def money_plan_update(payload: dict[str, Any]) -> dict[str, Any]:
    """Actualizar el plan de plata (horas/día, metas, prioridades)."""
    try:
        from core.money_plan import get_money_plan

        plan = get_money_plan()
        updated = plan.update(payload)
        return {"success": True, "plan": updated, "projection": plan.project_weekly()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/task-assistant/analyze")
async def task_assistant_analyze(payload: dict[str, Any]) -> dict[str, Any]:
    """Analizar una tarea pegada y devolver material de referencia para trabajarla."""
    try:
        from core.task_assistant import analyze_task

        task = payload.get("task", "")
        return await analyze_task(task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Dev Bounty Autopilot ─────────────────────────────────────────


@router.get("/dev-bounty/status")
async def dev_bounty_status() -> dict[str, Any]:
    """Estado del autopiloto de dev bounts."""
    try:
        from core.dev_bounty_autopilot import get_dev_bounty_autopilot

        return get_dev_bounty_autopilot().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/dev-bounty/activate")
async def dev_bounty_activate() -> dict[str, Any]:
    """Activar auto-discovery + auto-proposal de dev bounts."""
    try:
        from core.dev_bounty_autopilot import get_dev_bounty_autopilot

        return get_dev_bounty_autopilot().activate()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/dev-bounty/deactivate")
async def dev_bounty_deactivate() -> dict[str, Any]:
    """Desactivar el autopilote de dev bounts."""
    try:
        from core.dev_bounty_autopilot import get_dev_bounty_autopilot

        return get_dev_bounty_autopilot().deactivate()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/dev-bounty/run")
async def dev_bounty_run() -> dict[str, Any]:
    """Correr un ciclo de descubrimiento + preparar propuestas."""
    try:
        from core.dev_bounty_autopilot import get_dev_bounty_autopilot

        return await get_dev_bounty_autopilot().run_discovery_cycle()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/dev-bounty/queue")
async def dev_bounty_queue() -> dict[str, Any]:
    """Propuestas listas para validar."""
    try:
        from core.dev_bounty_autopilot import get_dev_bounty_autopilot

        return get_dev_bounty_autopilot().get_validation_queue()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/dev-bounty/beginner-mode")
async def dev_bounty_beginner_mode(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Activa/desactiva el filtro de bounts aptos para principiantes."""
    try:
        from core.dev_bounty_autopilot import get_dev_bounty_autopilot

        if payload is None:
            payload = {}
        enabled = payload.get("enabled", True)
        return get_dev_bounty_autopilot().set_beginner_mode(bool(enabled))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/dev-bounty/validate/{proposal_id}")
async def dev_bounty_validate(proposal_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validar una propuesta (approved/rejected)."""
    try:
        from core.dev_bounty_autopilot import get_dev_bounty_autopilot
        from core.profile_builder import get_profile_builder

        if payload is None:
            payload = {}
        action = payload.get("action", "approved")
        result = get_dev_bounty_autopilot().validate_proposal(proposal_id, action)

        # Si aprobó, registra la contribución en el perfil (y auto-push si está activo)
        if action == "approved" and result.get("success"):
            try:
                proposals = get_dev_bounty_autopilot()._read_proposals()
                for p in proposals:
                    if p.get("id") == proposal_id:
                        solution = {
                            "files": p.get("solution_files", []),
                            "summary": p.get("solution_preview", ""),
                            "platform": p.get("platform", "dev_bounty"),
                        }
                        get_profile_builder().record_contribution(
                            kind="dev_bounty",
                            title=p.get("title", "Bounty"),
                            url=p.get("repo", ""),
                            solution=solution,
                        )
                        break
            except Exception:
                pass

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Profile Builder ───────────────────────────────────────────────


@router.get("/profile-builder/status")
async def profile_builder_status() -> dict[str, Any]:
    """Estado del perfil de GitHub vinculado a OWNEX."""
    try:
        from core.profile_builder import get_profile_builder

        return get_profile_builder().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/profile-builder/link")
async def profile_builder_link(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Vincular cuenta de GitHub (username)."""
    try:
        from core.profile_builder import get_profile_builder

        if payload is None:
            payload = {}
        username = payload.get("username", "")
        return get_profile_builder().link_github(username)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/profile-builder/audit")
async def profile_builder_audit() -> dict[str, Any]:
    """Re-auditar el perfil vinculado."""
    try:
        from core.profile_builder import get_profile_builder

        return get_profile_builder().audit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/profile-builder/portfolio-repo")
async def profile_builder_portfolio_repo(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Configurar repo portfolio (usuario/repo) para auto-push."""
    try:
        from core.profile_builder import get_profile_builder

        if payload is None:
            payload = {}
        return get_profile_builder().set_portfolio_repo(payload.get("repo", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/profile-builder/auto-push")
async def profile_builder_auto_push(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Activar/desactivar auto-push de bounties validados al repo portfolio."""
    try:
        from core.profile_builder import get_profile_builder

        if payload is None:
            payload = {}
        return get_profile_builder().set_auto_push(payload.get("enabled", False))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/profile-builder/recommendations")
async def profile_builder_recommendations() -> dict[str, Any]:
    """Acciones recomendadas para mejorar el perfil."""
    try:
        from core.profile_builder import get_profile_builder

        return {"success": True, "recommendations": get_profile_builder().recommendations()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/profile-builder/readme")
async def profile_builder_readme() -> dict[str, Any]:
    """Generar README.md del perfil."""
    try:
        from core.profile_builder import get_profile_builder

        return get_profile_builder().generate_readme()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/profile-builder/record-contribution")
async def profile_builder_record_contribution(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Registrar contribución manual (opcional)."""
    try:
        from core.profile_builder import get_profile_builder

        if payload is None:
            payload = {}
        kind = payload.get("kind", "manual")
        title = payload.get("title", "")
        url = payload.get("url", "")
        return get_profile_builder().record_contribution(kind, title, url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Daily Task Board ─────────────────────────────────────────────


@router.get("/daily-tasks")
async def daily_tasks_get(force_refresh: bool = False) -> dict[str, Any]:
    """Tareas del día propuestas por OWNEX."""
    try:
        from core.daily_tasks import get_daily_task_board

        return get_daily_task_board().get_tasks(force_refresh=force_refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/daily-tasks/{task_id}/status")
async def daily_tasks_set_status(task_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Actualizar el estado de una tarea (pending/doing/done)."""
    try:
        from core.daily_tasks import get_daily_task_board

        if payload is None:
            payload = {}
        return get_daily_task_board().update_task_status(task_id, payload.get("status", "done"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/daily-tasks/advance-day")
async def daily_tasks_advance() -> dict[str, Any]:
    """Avanzar al próximo día (demo/prueba)."""
    try:
        from core.daily_tasks import get_daily_task_board

        return get_daily_task_board().advance_day()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/daily-tasks/refresh")
async def daily_tasks_refresh() -> dict[str, Any]:
    """Forzar regeneración de tareas del día."""
    try:
        from core.daily_tasks import get_daily_task_board

        return get_daily_task_board().get_tasks(force_refresh=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/daily-tasks/complete-done")
async def daily_tasks_complete_done() -> dict[str, Any]:
    """Marca como done las tareas cuyo hito ya está resuelto en el sistema."""
    try:
        from core.daily_tasks import get_daily_task_board

        result = get_daily_task_board().complete_done_from_state()
        board = get_daily_task_board().get_tasks()
        return {**result, **board}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Skill Method ──────────────────────────────────────────────────


@router.get("/skill-method")
async def skill_method_status() -> dict[str, Any]:
    """Estado de la ruta de estudio Skill Method."""
    try:
        from core.skill_method import get_skill_method

        return get_skill_method().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/skill-method/track")
async def skill_method_set_track(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Cambiar el track activo (web/mobile/cloud/web3)."""
    try:
        from core.skill_method import get_skill_method

        if payload is None:
            payload = {}
        return get_skill_method().set_track(payload.get("track_id", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/skill-method/session")
async def skill_method_register_session(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Registrar una sesión de evidencia real y avanzar skills."""
    try:
        from core.skill_method import get_skill_method

        if payload is None:
            payload = {}
        return get_skill_method().register_session(
            track_id=payload.get("track_id", ""),
            session_type=payload.get("session_type", ""),
            title=payload.get("title", ""),
            notes=payload.get("notes", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Capital Bar ──────────────────────────────────────────────────


@router.get("/capital-bar")
async def capital_bar_get_status() -> dict[str, Any]:
    """Estado del pool de capital y umbrales pasivos."""
    try:
        from core.capital_bar import get_capital_bar

        return get_capital_bar().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/capital-bar/ratio")
async def capital_bar_set_ratio(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Configurar el % de cada ingreso que alimenta el pool."""
    try:
        from core.capital_bar import get_capital_bar

        if payload is None:
            payload = {}
        return get_capital_bar().set_feed_ratio(payload.get("ratio", 0.8))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/capital-bar/income")
async def capital_bar_record_income(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Registrar un ingreso percibido (lo alimenta el pool)."""
    try:
        from core.capital_bar import get_capital_bar

        if payload is None:
            payload = {}
        return get_capital_bar().record_income(
            amount=payload.get("amount", 0),
            source=payload.get("source", ""),
            note=payload.get("note", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/capital-bar/adjust")
async def capital_bar_adjust(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Ajuste manual del pool (aportes / retiros)."""
    try:
        from core.capital_bar import get_capital_bar

        if payload is None:
            payload = {}
        return get_capital_bar().adjust_pool(payload.get("amount", 0), payload.get("note", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Goal Evaluator ───────────────────────────────────────────────


@router.get("/goal-evaluator")
async def goal_evaluator_status() -> dict[str, Any]:
    """Estado del evaluador de metas (historial)."""
    try:
        from core.goal_evaluator import get_goal_evaluator

        return get_goal_evaluator().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/goal-evaluator/evaluate")
async def goal_evaluator_evaluate(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluar una meta: {goal_type: 'monthly'|'multiplier', amount, multiplier}."""
    try:
        from core.goal_evaluator import get_goal_evaluator

        if payload is None:
            payload = {}
        return get_goal_evaluator().evaluate(
            goal_type=payload.get("goal_type", "monthly"),
            amount=payload.get("amount", 0),
            multiplier=payload.get("multiplier", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Work Log ──────────────────────────────────────────────────────


@router.get("/work-log")
async def work_log_get() -> dict[str, Any]:
    """Sesiones de trabajo reales + acumulados."""
    try:
        from core.work_log import get_work_log

        return get_work_log().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/work-log/session")
async def work_log_register(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Registrar una sesión de trabajo (horas, foco, momentum)."""
    try:
        from core.work_log import get_work_log

        if payload is None:
            payload = {}
        return get_work_log().register_session(
            hours=payload.get("hours", 0),
            foco=payload.get("foco", "bounty"),
            detail=payload.get("detail", ""),
            momentum=payload.get("momentum", 5),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Post Mortem ───────────────────────────────────────────────────


@router.get("/postmortem")
async def postmortem_get() -> dict[str, Any]:
    """Episodios de aprendizaje registrados."""
    try:
        from core.postmortem import get_postmortem

        return get_postmortem().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/postmortem/register")
async def postmortem_register(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Registrar un episodio (outcome: approved/rejected/closed/paused)."""
    try:
        from core.postmortem import get_postmortem

        if payload is None:
            payload = {}
        return get_postmortem().register(
            item_type=payload.get("item_type", "bounty"),
            item_title=payload.get("item_title", ""),
            outcome=payload.get("outcome", ""),
            learned=payload.get("learned", ""),
            repeat=payload.get("repeat", ""),
            avoid=payload.get("avoid", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Account Health ────────────────────────────────────────────────


@router.get("/account-health")
async def account_health_get(platform: str = "") -> dict[str, Any]:
    """Salud de cuentas y alertas de riesgo/ban."""
    try:
        from core.account_health import get_account_health

        return get_account_health().get_status(platform=platform)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/account-health/register")
async def account_health_register(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Registrar una cuenta nueva por plataforma."""
    try:
        from core.account_health import get_account_health

        if payload is None:
            payload = {}
        return get_account_health().register_account(payload.get("platform", ""), payload.get("name", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/account-health/event")
async def account_health_event(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Reportar un evento de riesgo (qa_fail, warn, vpn_issue, suspend_risk)."""
    try:
        from core.account_health import get_account_health

        if payload is None:
            payload = {}
        return get_account_health().report_event(
            platform=payload.get("platform", ""),
            event_type=payload.get("event_type", ""),
            detail=payload.get("detail", ""),
            impact=payload.get("impact", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Payout Planner ────────────────────────────────────────────────


@router.get("/payout-planner")
async def payout_planner_get() -> dict[str, Any]:
    """Plan de cobro en AR por plataforma."""
    try:
        from core.payout_planner import get_payout_planner

        return get_payout_planner().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/payout-planner/configure")
async def payout_planner_configure(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Marcar una plataforma como configurada (ruta de cobro lista)."""
    try:
        from core.payout_planner import get_payout_planner

        if payload is None:
            payload = {}
        return get_payout_planner().set_configured(payload.get("platform_id", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Brand Writer ──────────────────────────────────────────────────


@router.get("/brand-writer")
async def brand_writer_get() -> dict[str, Any]:
    """Borradores de contenido público generados."""
    try:
        from core.brand_writer import get_brand_writer

        return get_brand_writer().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/brand-writer/generate")
async def brand_writer_generate(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generar borradores para X/LinkedIn desde una evidencia."""
    try:
        from core.brand_writer import get_brand_writer

        if payload is None:
            payload = {}
        return get_brand_writer().generate(
            topic=payload.get("topic", ""),
            detail=payload.get("detail", ""),
            channels=payload.get("channels"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/brand-writer/publish")
async def brand_writer_publish(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Marcar un borrador como publicado."""
    try:
        from core.brand_writer import get_brand_writer

        if payload is None:
            payload = {}
        return get_brand_writer().mark_published(payload.get("draft_id", ""), payload.get("channel", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Vault Lock ────────────────────────────────────────────────────


@router.get("/vault-lock")
async def vault_lock_get() -> dict[str, Any]:
    """Estado de protección del vault (secretos)."""
    try:
        from core.vault_lock import get_vault_lock

        return get_vault_lock().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/vault-lock/secure")
async def vault_lock_secure(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Qué le faló: activar passphrase y fingerprint."""
    try:
        from core.vault_lock import get_vault_lock

        if payload is None:
            payload = {}
        return get_vault_lock().set_passphrase(payload.get("passphrase", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/vault-lock/unlock")
async def vault_lock_unlock(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Desbloquear con passphrase (fingerprint match)."""
    try:
        from core.vault_lock import get_vault_lock

        if payload is None:
            payload = {}
        return get_vault_lock().unlock(payload.get("passphrase", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Emergency Mode ────────────────────────────────────────────────


@router.get("/emergency-mode")
async def emergency_mode_get() -> dict[str, Any]:
    """Estado/último análisis de emergencia."""
    try:
        from core.emergency_mode import get_emergency_mode

        return get_emergency_mode().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/emergency-mode/analyze")
async def emergency_mode_analyze(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Analizar el mes contra la meta y devolver plan de emergencia."""
    try:
        from core.emergency_mode import get_emergency_mode

        if payload is None:
            payload = {}
        return get_emergency_mode().analyze(
            target_monthly=payload.get("target_monthly", 0),
            goal_type=payload.get("goal_type", "monthly"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Payout Net ────────────────────────────────────────────────────


@router.get("/payout-net")
async def payout_net_catalog(cat: str = "") -> dict[str, Any]:
    """Catálogo de métodos de cobro (solo KYC) por categoría."""
    try:
        from core.payout_net import get_payout_net

        return get_payout_net().get_catalog(cat=cat)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/payout-net/status")
async def payout_net_status() -> dict[str, Any]:
    """Estado/incidentes registrados de la red de cobro."""
    try:
        from core.payout_net import get_payout_net

        return get_payout_net().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/payout-net/recommend")
async def payout_net_recommend(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Recomendar métodos por plataforma (forge/pulse/bounty/...)"""
    try:
        from core.payout_net import get_payout_net

        if payload is None:
            payload = {}
        return get_payout_net().recommend_for(payload.get("source", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/payout-net/resolve")
async def payout_net_resolve(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolver un problema con un método (fallback + fix)."""
    try:
        from core.payout_net import get_payout_net

        if payload is None:
            payload = {}
        return get_payout_net().resolve(payload.get("method_id", ""), payload.get("problem", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Finance Guru ──────────────────────────────────────────────────


@router.get("/finance-guru")
async def finance_guru_status() -> dict[str, Any]:
    """Estado del guru financiero (consultas + resoluciones)."""
    try:
        from core.finance_guru import get_finance_guru

        return get_finance_guru().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/finance-guru/accounts")
async def finance_guru_accounts() -> dict[str, Any]:
    """Catálogo de cuentas internacionales/USA abribles desde AR."""
    try:
        from core.finance_guru import get_finance_guru

        return get_finance_guru().get_accounts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/finance-guru/ask")
async def finance_guru_ask(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Preguntar en lenguaje natural (cobro, cuentas, KYC, retenciones, LLC)."""
    try:
        from core.finance_guru import get_finance_guru

        if payload is None:
            payload = {}
        return get_finance_guru().ask(payload.get("query", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/finance-guru/resolve")
async def finance_guru_resolve(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolver un problema concreto con una cuenta."""
    try:
        from core.finance_guru import get_finance_guru

        if payload is None:
            payload = {}
        return get_finance_guru().resolve_account(payload.get("account_id", ""), payload.get("problem", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/finance-guru/recommend")
async def finance_guru_recommend(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Recomendar cuentas según propósito (freelance/bounty/crypto/product/llc)."""
    try:
        from core.finance_guru import get_finance_guru

        if payload is None:
            payload = {}
        purpose = payload.get("purpose", "freelance")
        # simple filter
        g = get_finance_guru()
        recs = g.recommend_accounts(purpose)
        return {"success": True, "purpose": purpose, "recommended": recs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Tax AR ────────────────────────────────────────────────────────


@router.get("/tax-ar")
async def tax_ar_status() -> dict[str, Any]:
    """Estado monotributo, facturas, gastos, recategorización."""
    try:
        from core.tax_ar import get_tax_ar

        return get_tax_ar().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/tax-ar/cuil")
async def tax_ar_set_cuil(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.tax_ar import get_tax_ar

        return get_tax_ar().set_cuil(payload.get("cuil", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/tax-ar/categoria")
async def tax_ar_set_cat(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.tax_ar import get_tax_ar

        return get_tax_ar().set_categoria(payload.get("categoria", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/tax-ar/ingreso")
async def tax_ar_add_income(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.tax_ar import get_tax_ar

        return get_tax_ar().registrar_ingreso_usd(payload.get("usd", 0), payload.get("fecha", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/tax-ar/gastos")
async def tax_ar_calc_gastos(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.tax_ar import get_tax_ar

        return get_tax_ar().calcular_gastos_deducibles(payload.get("ingresos_usd", 0), payload.get("usd_ars", 1000))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/tax-ar/factura")
async def tax_ar_add_factura(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.tax_ar import get_tax_ar

        return get_tax_ar().registrar_factura_e(
            payload.get("cliente", ""), payload.get("usd", 0), payload.get("fecha", ""), payload.get("cae", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/tax-ar/csv")
async def tax_ar_export_csv(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.tax_ar import get_tax_ar

        return get_tax_ar().exportar_csv_contador(payload.get("path", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Invoicer AR ───────────────────────────────────────────────────


@router.get("/invoicer-ar")
async def invoicer_ar_status() -> dict[str, Any]:
    try:
        from core.invoicer_ar import get_invoicer_ar

        return get_invoicer_ar().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/invoicer-ar/config")
async def invoicer_ar_config(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.invoicer_ar import get_invoicer_ar

        return get_invoicer_ar().configurar(
            payload.get("cuit", ""),
            payload.get("cert_path", ""),
            payload.get("key_path", ""),
            payload.get("punto_venta", 1),
            payload.get("modo", "homologacion"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/invoicer-ar/emitir")
async def invoicer_ar_emitir(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.invoicer_ar import get_invoicer_ar

        return get_invoicer_ar().emitir_factura_e(
            payload.get("cliente_cuit", ""),
            payload.get("cliente_nombre", ""),
            payload.get("usd", 0),
            payload.get("descripcion", ""),
            payload.get("moneda", "USD"),
            payload.get("cotizacion", 1.0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/invoicer-ar/pdf")
async def invoicer_ar_pdf(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.invoicer_ar import get_invoicer_ar

        return get_invoicer_ar().generar_pdf(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Offramp Executor ──────────────────────────────────────────────


@router.get("/offramp")
async def offramp_status() -> dict[str, Any]:
    try:
        from core.offramp_executor import get_offramp_executor

        return get_offramp_executor().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/offramp/providers")
async def offramp_providers() -> dict[str, Any]:
    try:
        from core.offramp_executor import get_offramp_executor

        return get_offramp_executor().get_providers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/offramp/default")
async def offramp_set_default(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.offramp_executor import get_offramp_executor

        return get_offramp_executor().set_default(payload.get("provider", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/offramp/execute")
async def offramp_execute(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.offramp_executor import get_offramp_executor

        return get_offramp_executor().build_url(
            payload.get("provider", ""), payload.get("amount_usd", 0), payload.get("extra")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/offramp/done")
async def offramp_done(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.offramp_executor import get_offramp_executor

        return get_offramp_executor().mark_done(payload.get("execution_id", ""), payload.get("txid", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Platform Connectors ───────────────────────────────────────────


@router.get("/platforms")
async def platforms_status() -> dict[str, Any]:
    try:
        from core.platform_connectors import get_platform_manager

        return get_platform_manager().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/platforms/config")
async def platforms_config(payload: dict[str, Any] = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    try:
        from core.platform_connectors import get_platform_manager

        return get_platform_manager().set_config(
            payload.get("platform", ""),
            payload.get("enabled", True),
            payload.get("credentials", {}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/platforms/sync")
async def platforms_sync() -> dict[str, Any]:
    try:
        from core.platform_connectors import get_platform_manager

        return await get_platform_manager().sync_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Life cycle ───────────────────────────────────────────────────
@router.post("/life/cycle")
async def life_cycle() -> dict[str, Any]:
    """Run a quick life / personal cycle and return the daily summary."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        summary = assistant.get_daily_summary()
        return {"success": True, **summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/life/snapshot")
async def life_snapshot() -> dict[str, Any]:
    """Snapshot rápido de la vida / tareas del día."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        tasks = assistant.get_today_tasks()
        return {"success": True, "tasks": len(tasks), "pending_tasks": [t.title for t in tasks][:10]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Action Required ──────────────────────────────────────────────


@router.get("/investment/action-required")
async def action_required() -> dict[str, Any]:
    """Listar acciones que requieren al usuario."""
    try:
        from cores.notifications.action_required import get_pending_actions

        actions = get_pending_actions()
        items = [a.to_dict() for a in actions]
        return {"items": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/investment/action-required/{action_id}/resolve")
async def action_required_resolve(action_id: str) -> dict[str, Any]:
    """Resolver una acción requerida."""
    try:
        from cores.notifications.action_required import resolve_action

        resolved = resolve_action(action_id)
        return {"success": resolved is not None, "resolved": bool(resolved)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Startup checks ───────────────────────────────────────────────


@router.post("/investment/startup-checks")
async def startup_checks() -> dict[str, Any]:
    """Ejecutar todos los checks de arranque."""
    try:
        from cores.startup_checks import run_all_checks

        results = run_all_checks()
        checks = [
            {
                "title": k.replace("_", " ").capitalize(),
                "status": v.get("status", "unknown"),
                "detail": v.get("detail", ""),
            }
            for k, v in results.items()
        ]
        return {"success": True, "checks": checks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Full autonomous cycle ────────────────────────────────────────


@router.post("/automation/full-cycle")
async def run_full_cycle() -> dict[str, Any]:
    """Ejecutar un ciclo completo autónomo on-demand."""
    try:
        from core.full_auto import get_full_auto

        result = await get_full_auto().run_full_cycle()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/automation/modules")
async def automation_modules() -> dict[str, Any]:
    """Estado de los módulos de automatización disponibles."""

    def _safe(fn):
        try:
            return fn()
        except Exception:
            return {}

    modules = {}
    try:
        from core.auto_submission import get_submission_engine

        modules["submission"] = {
            "name": "Auto-Submission",
            "enabled": True,
            "stats": _safe(get_submission_engine().get_stats),
        }
    except Exception:
        modules["submission"] = {"name": "Auto-Submission", "enabled": False}

    try:
        from core.auto_tax import get_tax_tracker

        modules["tax"] = {
            "name": "Auto-Tax",
            "enabled": True,
            "monthly": _safe(lambda: get_tax_tracker().get_monthly_summary()),
        }
    except Exception:
        modules["tax"] = {"name": "Auto-Tax", "enabled": False}

    try:
        from core.auto_optimizer import get_optimizer

        modules["optimizer"] = {
            "name": "Auto-Optimizer",
            "enabled": True,
            "allocation": _safe(get_optimizer().get_optimal_allocation),
        }
    except Exception:
        modules["optimizer"] = {"name": "Auto-Optimizer", "enabled": False}

    try:
        from core.auto_account import get_account_setup

        modules["accounts"] = {
            "name": "Auto-Account",
            "enabled": True,
            "credentials": _safe(lambda: get_account_setup().get_credentials("hackerone")),
        }
    except Exception:
        modules["accounts"] = {"name": "Auto-Account", "enabled": False}

    try:
        from core.auto_communication import get_communication

        modules["communication"] = {
            "name": "Auto-Communication",
            "enabled": True,
            "template": _safe(lambda: get_communication().get_custom_template("default")),
        }
    except Exception:
        modules["communication"] = {"name": "Auto-Communication", "enabled": False}


# ── Payment Tracker ────────────────────────────────────────────────


@router.get("/payment-tracker")
async def payment_tracker_status() -> dict[str, Any]:
    """Estado del tracker de pagos."""
    try:
        from core.payment_tracker import get_payment_tracker

        return get_payment_tracker().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/payment-tracker/webhook")
async def payment_tracker_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Recibir webhook de pago desde una plataforma."""
    try:
        from core.payment_tracker import get_payment_tracker

        platform = payload.get("platform", "unknown")
        payment = get_payment_tracker().receive_webhook(platform, payload)
        return {"success": True, "payment": payment.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/payment-tracker/config")
async def payment_tracker_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Configurar webhook/polling para una plataforma."""
    try:
        from core.payment_tracker import get_payment_tracker

        tracker = get_payment_tracker()
        tracker.register_webhook_config(
            platform=payload.get("platform", ""),
            webhook_url=payload.get("webhook_url"),
            secret=payload.get("secret"),
            polling_enabled=payload.get("polling_enabled", False),
            polling_interval_hours=payload.get("polling_interval_hours", 24),
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/payment-tracker/confirm")
async def payment_tracker_confirm(payload: dict[str, Any]) -> dict[str, Any]:
    """Confirmar un pago (manual o auto-confirmado)."""
    try:
        from core.payment_tracker import get_payment_tracker

        payment = get_payment_tracker().confirm_payment(payload.get("payment_id", ""))
        return {"success": True, "payment": payment.to_dict() if payment else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/payment-tracker/pending")
async def payment_tracker_pending() -> dict[str, Any]:
    """Listar pagos pendientes de confirmación."""
    try:
        from core.payment_tracker import get_payment_tracker

        pending = get_payment_tracker().get_pending_payments()
        return {"pending": [p.to_dict() for p in pending], "total": len(pending)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Trust Engine ───────────────────────────────────────────────────


@router.get("/trust-engine")
async def trust_engine_status() -> dict[str, Any]:
    """Estado del motor de confianza."""
    try:
        from core.trust_engine import get_trust_engine

        return get_trust_engine().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/trust-engine/platform/{platform}")
async def trust_engine_platform(platform: str) -> dict[str, Any]:
    """Métricas de confianza para una plataforma específica."""
    try:
        from core.trust_engine import get_trust_engine

        metrics = get_trust_engine().get_platform_trust(platform)
        return metrics.to_dict() if metrics else {"error": "Platform not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/trust-engine/config")
async def trust_engine_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Actualizar configuración de auto-aprobación."""
    try:
        from core.trust_engine import get_trust_engine

        get_trust_engine().update_config(**payload)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/trust-engine/outcome")
async def trust_engine_outcome(payload: dict[str, Any]) -> dict[str, Any]:
    """Registrar resultado (aceptado/rechazado, pagado/no pagado)."""
    try:
        from core.trust_engine import get_trust_engine

        get_trust_engine().record_outcome(
            platform=payload.get("platform", ""),
            accepted=payload.get("accepted", False),
            paid=payload.get("paid", False),
            amount_usd=payload.get("amount_usd", 0),
            time_to_payment_days=payload.get("time_to_payment_days"),
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/trust-engine/can-auto-approve")
async def trust_engine_can_auto_approve(payload: dict[str, Any]) -> dict[str, Any]:
    """Verificar si una oportunidad puede ser auto-aprobada."""
    try:
        from core.trust_engine import get_trust_engine

        can_approve, reason = get_trust_engine().can_auto_approve(
            platform=payload.get("platform", ""),
            amount_usd=payload.get("amount_usd", 0),
        )
        return {"can_approve": can_approve, "reason": reason}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Closed Loop ─────────────────────────────────────────────────────


@router.get("/closed-loop")
async def closed_loop_status() -> dict[str, Any]:
    """Estado del sistema de closed-loop."""
    try:
        from core.closed_loop import get_closed_loop_manager

        return get_closed_loop_manager().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/closed-loop/process-payment")
async def closed_loop_process_payment(payload: dict[str, Any]) -> dict[str, Any]:
    """Procesar un pago confirmado y actualizar trust/perfil."""
    try:
        from core.closed_loop import get_closed_loop_manager

        result = get_closed_loop_manager().process_payment(payload.get("payment_id", ""))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/closed-loop/process-rejection")
async def closed_loop_process_rejection(payload: dict[str, Any]) -> dict[str, Any]:
    """Procesar un rechazo y actualizar trust."""
    try:
        from core.closed_loop import get_closed_loop_manager

        result = get_closed_loop_manager().process_rejection(
            platform=payload.get("platform", ""),
            opportunity_id=payload.get("opportunity_id", ""),
            reason=payload.get("reason", ""),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/closed-loop/config")
async def closed_loop_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Actualizar configuración del closed-loop."""
    try:
        from core.closed_loop import ClosedLoopConfig, get_closed_loop_manager

        config = ClosedLoopConfig(
            auto_learn_from_payments=payload.get("auto_learn_from_payments", True),
            auto_update_trust=payload.get("auto_update_trust", True),
            auto_update_profile=payload.get("auto_update_profile", True),
            min_payment_amount_usd=payload.get("min_payment_amount_usd", 1.0),
        )
        manager = get_closed_loop_manager()
        manager.config = config
        return {"success": True, "config": {
            "auto_learn_from_payments": config.auto_learn_from_payments,
            "auto_update_trust": config.auto_update_trust,
            "auto_update_profile": config.auto_update_profile,
        }}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Platform Webhooks ──────────────────────────────────────────────


@router.post("/webhook/{platform}")
async def platform_webhook(platform: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Recibir webhook desde plataforma (HackerOne, Opire, Freelancer)."""
    try:
        from core.platform_webhooks import handle_platform_webhook

        result = handle_platform_webhook(platform, payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
