"""Personal Infrastructure Manager - Integrations with Existing Systems.

Integra con MERLIN, Voice, Mission Control y Memory para proporcionar
una experiencia unificada.
"""

from __future__ import annotations

import logging
from typing import Any

from cores.personal_infrastructure.admin_navigator import get_admin_navigator
from cores.personal_infrastructure.health_center import get_integration_health_center
from cores.personal_infrastructure.manager import get_personal_infrastructure_manager
from cores.personal_infrastructure.wealth_assistant import get_wealth_assistant

logger = logging.getLogger("ownex.personal_infrastructure.integrations")


class PersonalInfrastructureIntegrations:
    """Integraciones del Personal Infrastructure Manager con sistemas existentes."""

    def __init__(self):
        self.manager = get_personal_infrastructure_manager()
        self.assistant = get_wealth_assistant()
        self.navigator = get_admin_navigator()
        self.health_center = get_integration_health_center()

    # ==================== MERLIN INTEGRATION ====================

    def get_merlin_response(self, query: str) -> dict[str, Any]:
        """Generar respuesta de MERLIN para consultas sobre infraestructura personal."""
        query_lower = query.lower()

        # Consultas sobre objetivos
        if "objetivo" in query_lower or "goal" in query_lower:
            return self._get_objectives_response(query_lower)

        # Consultas sobre finanzas
        if "finanza" in query_lower or "dinero" in query_lower or "ingreso" in query_lower:
            return self._get_finances_response(query_lower)

        # Consultas sobre trámites
        if "trámite" in query_lower or "administrativo" in query_lower or "papeleo" in query_lower:
            return self._get_admin_response(query_lower)

        # Consultas sobre integraciones
        if "integración" in query_lower or "cuenta" in query_lower or "conectar" in query_lower:
            return self._get_integrations_response(query_lower)

        # Consultas generales
        return self._get_general_response()

    def _get_objectives_response(self, query: str) -> dict[str, Any]:
        """Respuesta para consultas sobre objetivos."""
        snapshot = self.manager.get_infrastructure_snapshot()

        objectives = []
        for obj_id, progress in snapshot.objectives_progress.items():
            obj_def = self.manager.get_objective(obj_id)
            if obj_def:
                objectives.append(
                    {
                        "title": obj_def.title,
                        "category": obj_def.category.value,
                        "progress": progress.completion_percentage,
                        "status": "completed" if progress.completion_percentage >= 100 else "in_progress",
                    }
                )

        return {
            "type": "objectives",
            "message": f"Tienes {len(objectives)} objetivos configurados. {snapshot.next_recommended_action}",
            "data": {
                "objectives": objectives,
                "overall_completion": snapshot.overall_completion,
                "next_action": snapshot.next_recommended_action,
            },
        }

    def _get_finances_response(self, query: str) -> dict[str, Any]:
        """Respuesta para consultas financieras."""
        health = self.assistant.get_financial_health()

        if "mes" in query or "mensual" in query:
            current_date = __import__("datetime").datetime.now()
            summary = self.assistant.get_monthly_summary(current_date.year, current_date.month)
            return {
                "type": "finances_monthly",
                "message": f"Ingresos del mes: ${summary['total_income']:.2f}, Gastos: ${summary['total_expenses']:.2f}, Neto: ${summary['net_income']:.2f}",
                "data": summary,
            }

        return {
            "type": "finances_health",
            "message": f"Salud financiera: {health['health_score']}/100. Tasa de ahorro: {health['savings_rate']:.1%}",
            "data": health,
        }

    def _get_admin_response(self, query: str) -> dict[str, Any]:
        """Respuesta para consultas administrativas."""
        next_action = self.navigator.get_next_action()
        processes = self.navigator.get_all_processes()

        return {
            "type": "administrative",
            "message": f"Próxima acción administrativa: {next_action}",
            "data": {
                "next_action": next_action,
                "total_processes": len(processes),
                "processes": [
                    {
                        "id": proc.process_id,
                        "title": proc.title,
                        "status": proc.status,
                    }
                    for proc in processes
                ],
            },
        }

    def _get_integrations_response(self, query: str) -> dict[str, Any]:
        """Respuesta para consultas sobre integraciones."""
        health_check = self.health_center.run_health_check()

        return {
            "type": "integrations",
            "message": f"Salud de integraciones: {health_check['overall_status']}. {health_check['attention_count']} necesitan atención.",
            "data": health_check,
        }

    def _get_general_response(self) -> dict[str, Any]:
        """Respuesta general."""
        snapshot = self.manager.get_infrastructure_snapshot()

        return {
            "type": "general",
            "message": f"Infraestructura personal al {snapshot.overall_completion:.0f}%. {snapshot.next_recommended_action}",
            "data": {
                "overall_completion": snapshot.overall_completion,
                "next_action": snapshot.next_recommended_action,
                "objectives_count": len(snapshot.objectives_progress),
                "integrations_count": len(snapshot.integrations),
            },
        }

    # ==================== VOICE INTEGRATION ====================

    def get_voice_command_handler(self, command: str) -> dict[str, Any]:
        """Manejador de comandos de voz para infraestructura personal."""
        command_lower = command.lower()

        # Comandos de objetivos
        if "iniciar objetivo" in command_lower or "empezar objetivo" in command_lower:
            return self._handle_start_objective(command_lower)

        if "estado objetivo" in command_lower or "progreso objetivo" in command_lower:
            return self._handle_objective_progress(command_lower)

        # Comandos financieros
        if "agregar ingreso" in command_lower or "registrar ingreso" in command_lower:
            return self._handle_add_income(command_lower)

        if "agregar gasto" in command_lower or "registrar gasto" in command_lower:
            return self._handle_add_expense(command_lower)

        # Comandos administrativos
        if "iniciar trámite" in command_lower or "empezar trámite" in command_lower:
            return self._handle_start_process(command_lower)

        # Comandos de salud
        if "estado integraciones" in command_lower or "salud integraciones" in command_lower:
            return self._handle_health_check()

        return {
            "type": "error",
            "message": "Comando no reconocido. Intenta: 'iniciar objetivo', 'agregar ingreso', 'estado integraciones'",
        }

    def _handle_start_objective(self, command: str) -> dict[str, Any]:
        """Manejar comando para iniciar objetivo."""
        # Extraer tipo de objetivo del comando
        if "desarrollo" in command:
            objective_id = "development"
        elif "bug bounty" in command:
            objective_id = "bug_bounty"
        elif "dev bounty" in command:
            objective_id = "dev_bounty"
        elif "freelance" in command:
            objective_id = "freelance"
        elif "finanzas" in command or "wealth" in command:
            objective_id = "wealth"
        else:
            return {
                "type": "error",
                "message": "No especificaste qué objetivo iniciar. Opciones: desarrollo, bug bounty, dev bounty, freelance, finanzas",
            }

        try:
            progress = self.manager.start_objective(objective_id)
            return {
                "type": "success",
                "message": f"Objetivo {objective_id} iniciado. Progreso: {progress.completion_percentage:.0f}%",
                "data": {
                    "objective_id": objective_id,
                    "progress": progress.completion_percentage,
                    "pending_tasks": progress.pending_tasks,
                },
            }
        except Exception as exc:
            return {
                "type": "error",
                "message": f"Error al iniciar objetivo: {str(exc)}",
            }

    def _handle_objective_progress(self, command: str) -> dict[str, Any]:
        """Manejar comando para consultar progreso."""
        # Mostrar progreso de todos los objetivos
        snapshot = self.manager.get_infrastructure_snapshot()

        progress_list = []
        for obj_id, progress in snapshot.objectives_progress.items():
            obj_def = self.manager.get_objective(obj_id)
            if obj_def:
                progress_list.append(
                    f"{obj_def.title}: {progress.completion_percentage:.0f}% ({len(progress.completed_tasks)}/{len(progress.completed_tasks) + len(progress.pending_tasks)})"
                )

        return {
            "type": "success",
            "message": "Progreso de objetivos:\n" + "\n".join(progress_list),
            "data": snapshot.objectives_progress,
        }

    def _handle_add_income(self, command: str) -> dict[str, Any]:
        """Manejar comando para agregar ingreso (requiere más info)."""
        return {
            "type": "info",
            "message": "Para agregar un ingreso necesito: fuente, monto, moneda, plataforma, descripción. Usa la interfaz web para más detalles.",
        }

    def _handle_add_expense(self, command: str) -> dict[str, Any]:
        """Manejar comando para agregar gasto (requiere más info)."""
        return {
            "type": "info",
            "message": "Para agregar un gasto necesito: categoría, monto, moneda, descripción. Usa la interfaz web para más detalles.",
        }

    def _handle_start_process(self, command: str) -> dict[str, Any]:
        """Manejar comando para iniciar proceso administrativo."""
        if "pago" in command or "cobro" in command:
            process_id = "payment_method"
        elif "fiscal" in command or "impuesto" in command:
            process_id = "fiscal_setup"
        elif "perfil" in command or "profesional" in command:
            process_id = "professional_profile"
        else:
            return {
                "type": "error",
                "message": "No especificaste qué trámite iniciar. Opciones: método de pago, configuración fiscal, perfil profesional",
            }

        try:
            process = self.navigator.start_process(process_id)
            return {
                "type": "success",
                "message": f"Proceso {process.title} iniciado. Pasos: {len(process.steps)}",
                "data": {
                    "process_id": process.process_id,
                    "title": process.title,
                    "total_steps": len(process.steps),
                },
            }
        except Exception as exc:
            return {
                "type": "error",
                "message": f"Error al iniciar proceso: {str(exc)}",
            }

    def _handle_health_check(self) -> dict[str, Any]:
        """Manejar comando de check de salud."""
        health_check = self.health_center.run_health_check()

        return {
            "type": "success",
            "message": f"Salud de integraciones: {health_check['overall_status']}. Score: {health_check['health_overview']['health_score']:.0f}/100",
            "data": health_check,
        }

    # ==================== MISSION CONTROL INTEGRATION ====================

    def get_mission_control_widgets(self) -> list[dict[str, Any]]:
        """Obtener widgets para Mission Control."""
        snapshot = self.manager.get_infrastructure_snapshot()
        health_check = self.health_center.run_health_check()
        financial_health = self.assistant.get_financial_health()

        widgets = [
            {
                "id": "infrastructure_progress",
                "type": "progress",
                "title": "Infraestructura Personal",
                "value": snapshot.overall_completion,
                "max": 100,
                "unit": "%",
                "color": "green"
                if snapshot.overall_completion >= 80
                else "yellow"
                if snapshot.overall_completion >= 50
                else "red",
            },
            {
                "id": "integration_health",
                "type": "status",
                "title": "Salud de Integraciones",
                "value": health_check["overall_status"],
                "details": f"{health_check['attention_count']} necesitan atención",
                "color": "green" if health_check["overall_status"] == "healthy" else "yellow",
            },
            {
                "id": "financial_health",
                "type": "status",
                "title": "Salud Financiera",
                "value": f"{financial_health['health_score']}/100",
                "details": f"Tasa de ahorro: {financial_health['savings_rate']:.1%}",
                "color": "green"
                if financial_health["health_score"] >= 70
                else "yellow"
                if financial_health["health_score"] >= 50
                else "red",
            },
            {
                "id": "next_action",
                "type": "action",
                "title": "Próxima Acción",
                "value": snapshot.next_recommended_action,
                "action_type": "suggestion",
            },
        ]

        return widgets

    # ==================== MEMORY INTEGRATION ====================

    def get_memory_entries(self) -> list[dict[str, Any]]:
        """Obtener entradas para el sistema de memoria."""
        snapshot = self.manager.get_infrastructure_snapshot()

        entries = [
            {
                "namespace": "personal_infrastructure",
                "key": "infrastructure_snapshot",
                "value": snapshot,
                "tags": ["infrastructure", "progress", "objectives"],
            },
            {
                "namespace": "personal_infrastructure",
                "key": "integrations_health",
                "value": self.health_center.get_health_overview(),
                "tags": ["health", "integrations", "monitoring"],
            },
            {
                "namespace": "personal_infrastructure",
                "key": "financial_health",
                "value": self.assistant.get_financial_health(),
                "tags": ["finance", "wealth", "health"],
            },
        ]

        return entries


# Singleton instance
_personal_infrastructure_integrations: PersonalInfrastructureIntegrations | None = None


def get_personal_infrastructure_integrations() -> PersonalInfrastructureIntegrations:
    """Obtener instancia singleton de las integraciones."""
    global _personal_infrastructure_integrations
    if _personal_infrastructure_integrations is None:
        _personal_infrastructure_integrations = PersonalInfrastructureIntegrations()
    return _personal_infrastructure_integrations


def reset_personal_infrastructure_integrations() -> None:
    """Resetear instancia singleton."""
    global _personal_infrastructure_integrations
    _personal_infrastructure_integrations = None
