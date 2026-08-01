"""Personal Infrastructure Manager - API Router.

Expone endpoints para gestionar la infraestructura personal del usuario.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from cores.personal_infrastructure.admin_navigator import get_admin_navigator
from cores.personal_infrastructure.argentina_support import (
    AFIPCategory,
    get_argentina_support,
)
from cores.personal_infrastructure.health_center import get_integration_health_center
from cores.personal_infrastructure.manager import get_personal_infrastructure_manager
from cores.personal_infrastructure.wealth_assistant import (
    ExpenseCategory,
    IncomeSource,
    get_wealth_assistant,
)

logger = logging.getLogger("ownex.api.personal_infrastructure")

router = APIRouter(prefix="/api/personal-infrastructure", tags=["personal-infrastructure"])

# ==================== ENDPOINTS DE OBJETIVOS ====================


@router.get("/objectives")
async def get_all_objectives():
    """Obtener todos los objetivos disponibles."""
    manager = get_personal_infrastructure_manager()
    objectives = manager.get_all_objectives()
    return {
        "objectives": [
            {
                "id": obj.objective_id,
                "category": obj.category.value,
                "title": obj.title,
                "description": obj.description,
                "estimated_duration_hours": obj.estimated_duration_hours,
                "dependencies": obj.dependencies,
                "required_integrations_count": len(obj.required_integrations),
            }
            for obj in objectives
        ]
    }


@router.get("/objectives/{objective_id}")
async def get_objective(objective_id: str):
    """Obtener detalles de un objetivo específico."""
    manager = get_personal_infrastructure_manager()
    objective = manager.get_objective(objective_id)

    if not objective:
        raise HTTPException(status_code=404, detail=f"Objective {objective_id} not found") from None

    return {
        "id": objective.objective_id,
        "category": objective.category.value,
        "title": objective.title,
        "description": objective.description,
        "explanation": {
            "title": objective.explanation.title,
            "what_is": objective.explanation.what_is,
            "what_for": objective.explanation.what_for,
            "what_changes": objective.explanation.what_changes,
            "what_risk": objective.explanation.what_risk,
            "what_if_not": objective.explanation.what_if_not,
            "simple_version": objective.explanation.simple_version,
        },
        "required_integrations": [
            {
                "id": integ.integration_id,
                "name": integ.name,
                "purpose": integ.purpose,
                "permissions": integ.permissions,
                "connection_type": integ.connection_type,
            }
            for integ in objective.required_integrations
        ],
        "estimated_duration_hours": objective.estimated_duration_hours,
        "dependencies": objective.dependencies,
    }


@router.post("/objectives/{objective_id}/start")
async def start_objective(objective_id: str):
    """Iniciar un objetivo."""
    manager = get_personal_infrastructure_manager()
    try:
        progress = manager.start_objective(objective_id)
        return {
            "objective_id": progress.objective_id,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completion_percentage": progress.completion_percentage,
            "pending_tasks": progress.pending_tasks,
            "current_step": progress.current_step,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/objectives/{objective_id}/progress")
async def get_objective_progress(objective_id: str):
    """Obtener progreso de un objetivo."""
    manager = get_personal_infrastructure_manager()
    progress = manager.progress.get(objective_id)

    if not progress:
        raise HTTPException(status_code=404, detail=f"Objective {objective_id} not started") from None

    return {
        "objective_id": progress.objective_id,
        "started_at": progress.started_at.isoformat() if progress.started_at else None,
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "completion_percentage": progress.completion_percentage,
        "completed_tasks": progress.completed_tasks,
        "pending_tasks": progress.pending_tasks,
        "current_step": progress.current_step,
        "notes": progress.notes,
    }


@router.post("/objectives/{objective_id}/complete-task")
async def complete_integration_task(objective_id: str, integration_id: str):
    """Marcar una integración como completada."""
    manager = get_personal_infrastructure_manager()
    success = manager.complete_integration_task(objective_id, integration_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete task") from None

    progress = manager.progress.get(objective_id)
    return {
        "objective_id": objective_id,
        "integration_id": integration_id,
        "completion_percentage": progress.completion_percentage if progress else 0,
    }


# ==================== ENDPOINTS DE INFRAESTRUCTURA ====================


@router.get("/snapshot")
async def get_infrastructure_snapshot():
    """Obtener snapshot completo de la infraestructura."""
    manager = get_personal_infrastructure_manager()
    snapshot = manager.get_infrastructure_snapshot()

    return {
        "overall_completion": snapshot.overall_completion,
        "next_recommended_action": snapshot.next_recommended_action,
        "last_updated": snapshot.last_updated.isoformat(),
        "objectives_progress": {
            obj_id: {
                "completion_percentage": prog.completion_percentage,
                "completed_tasks": prog.completed_tasks,
                "pending_tasks": prog.pending_tasks,
            }
            for obj_id, prog in snapshot.objectives_progress.items()
        },
        "integrations_count": len(snapshot.integrations),
        "active_processes": len(snapshot.administrative_processes),
        "wealth_accounts_count": len(snapshot.wealth_accounts),
    }


@router.get("/integrations/health")
async def get_integration_health():
    """Obtener estado de salud de integraciones."""
    manager = get_personal_infrastructure_manager()
    return manager.get_integration_health()


@router.get("/integrations/{integration_id}/explanation")
async def get_integration_explanation(integration_id: str):
    """Obtener explicación educativa de una integración."""
    manager = get_personal_infrastructure_manager()
    explanation = manager.explain_integration(integration_id)

    if not explanation:
        raise HTTPException(status_code=404, detail=f"Integration {integration_id} not found") from None

    return {
        "title": explanation.title,
        "what_is": explanation.what_is,
        "what_for": explanation.what_for,
        "what_changes": explanation.what_changes,
        "what_risk": explanation.what_risk,
        "what_if_not": explanation.what_if_not,
        "simple_version": explanation.simple_version,
    }


# ==================== ENDPOINTS DE WEALTH ====================


@router.post("/wealth/income")
async def add_income(
    source: str,
    amount: float,
    currency: str,
    platform: str,
    description: str,
    account_id: str,
):
    """Agregar ingreso."""
    assistant = get_wealth_assistant()

    try:
        income = assistant.add_income(
            source=IncomeSource(source),
            amount=Decimal(str(amount)),
            currency=currency,
            platform=platform,
            description=description,
            account_id=account_id,
        )
        return {
            "entry_id": income.entry_id,
            "source": income.source.value,
            "amount": float(income.amount),
            "currency": income.currency,
            "date": income.date.isoformat(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/wealth/expenses")
async def add_expense(
    category: str,
    amount: float,
    currency: str,
    description: str,
    is_deductible: bool = False,
):
    """Agregar gasto."""
    assistant = get_wealth_assistant()

    try:
        expense = assistant.add_expense(
            category=ExpenseCategory(category),
            amount=Decimal(str(amount)),
            currency=currency,
            description=description,
            is_deductible=is_deductible,
        )
        return {
            "entry_id": expense.entry_id,
            "category": expense.category.value,
            "amount": float(expense.amount),
            "currency": expense.currency,
            "date": expense.date.isoformat(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/wealth/summary/{year}/{month}")
async def get_monthly_summary(year: int, month: int):
    """Obtener resumen mensual."""
    assistant = get_wealth_assistant()
    return assistant.get_monthly_summary(year, month)


@router.get("/wealth/summary/{year}")
async def get_annual_summary(year: int):
    """Obtener resumen anual."""
    assistant = get_wealth_assistant()
    return assistant.get_annual_summary(year)


@router.get("/wealth/tax/{year}")
async def get_tax_prep_summary(year: int):
    """Obtener resumen para preparación fiscal."""
    assistant = get_wealth_assistant()
    return assistant.get_tax_prep_summary(year)


@router.get("/wealth/health")
async def get_financial_health():
    """Obtener salud financiera."""
    assistant = get_wealth_assistant()
    return assistant.get_financial_health()


# ==================== ENDPOINTS DE ADMINISTRACIÓN ====================


@router.get("/admin/processes")
async def get_admin_processes():
    """Obtener todos los procesos administrativos."""
    navigator = get_admin_navigator()
    processes = navigator.get_all_processes()
    return {
        "processes": [
            {
                "id": proc.process_id,
                "title": proc.title,
                "objective": proc.objective,
                "status": proc.status,
                "total_steps": len(proc.steps),
            }
            for proc in processes
        ]
    }


@router.get("/admin/processes/{process_id}")
async def get_admin_process(process_id: str):
    """Obtener detalles de un proceso administrativo."""
    navigator = get_admin_navigator()
    status = navigator.get_process_status(process_id)

    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"]) from None

    return status


@router.post("/admin/processes/{process_id}/start")
async def start_admin_process(process_id: str):
    """Iniciar un proceso administrativo."""
    navigator = get_admin_navigator()
    try:
        process = navigator.start_process(process_id)
        return {
            "process_id": process.process_id,
            "status": process.status,
            "started_at": process.started_at.isoformat() if process.started_at else None,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post("/admin/processes/{process_id}/advance")
async def advance_admin_step(process_id: str, step_id: str):
    """Avanzar un paso en un proceso administrativo."""
    navigator = get_admin_navigator()
    success = navigator.advance_step(process_id, step_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to advance step") from None

    status = navigator.get_process_status(process_id)
    return status


@router.get("/admin/next-action")
async def get_next_admin_action():
    """Obtener próxima acción administrativa recomendada."""
    navigator = get_admin_navigator()
    return {"next_action": navigator.get_next_action()}


# ==================== ENDPOINTS DE HEALTH CENTER ====================


@router.get("/health/overview")
async def get_health_overview():
    """Obtener visión general de salud de integraciones."""
    health_center = get_integration_health_center()
    return health_center.get_health_overview()


@router.get("/health/check")
async def run_health_check():
    """Ejecutar check de salud completo."""
    health_center = get_integration_health_center()
    return health_center.run_health_check()


@router.get("/health/score-by-category")
async def get_health_score_by_category():
    """Obtener score de salud por categoría."""
    health_center = get_integration_health_center()
    return health_center.get_health_score_by_category()


# ==================== ENDPOINTS DE APROBACIONES ====================


@router.get("/approval/check")
async def check_approval_category(action: str):
    """Determinar categoría de aprobación para una acción."""
    manager = get_personal_infrastructure_manager()
    category = manager.check_approval_category(action)
    return {"action": action, "category": category.value}


# ==================== ENDPOINTS DE ARGENTINA/ARCA ====================


@router.get("/argentina/tax-category/{category}")
async def get_tax_category_explanation(category: str):
    """Obtener explicación de categoría fiscal argentina."""
    support = get_argentina_support()
    try:
        afip_category = AFIPCategory(category)
        return support.get_tax_category_explanation(afip_category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}") from None


@router.get("/argentina/recommendation/{annual_income_usd}")
async def get_recommendation_for_income(annual_income_usd: float):
    """Obtener recomendación fiscal basada en ingresos anuales."""
    support = get_argentina_support()
    recommendation = support.get_recommendation_for_income(annual_income_usd)
    return {
        "title": recommendation.title,
        "description": recommendation.description,
        "category": recommendation.category,
        "priority": recommendation.priority,
        "action_required": recommendation.action_required,
        "afip_related": recommendation.afip_related,
    }


@router.get("/argentina/services-digital-guide")
async def get_services_digital_tax_guide():
    """Obtener guía fiscal para servicios digitales en Argentina."""
    support = get_argentina_support()
    return support.get_services_digital_tax_guide()


@router.get("/argentina/processes")
async def get_argentina_specific_processes():
    """Obtener procesos administrativos específicos para Argentina."""
    support = get_argentina_support()
    return {"processes": support.get_argentina_specific_processes()}


@router.get("/argentina/tax-calendar/{year}")
async def get_tax_calendar(year: int):
    """Obtener calendario fiscal para Argentina."""
    support = get_argentina_support()
    return {"year": year, "calendar": support.get_tax_calendar(year)}


@router.get("/argentina/bug-bounty-warning")
async def get_bug_bounty_warning():
    """Obtener advertencia fiscal para bug bounty en Argentina."""
    support = get_argentina_support()
    return support.get_warning_for_bug_bounty()
