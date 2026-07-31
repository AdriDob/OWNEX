"""Administrative Navigator - Asistente de Trámites.

Guía al usuario en trámites administrativos explicando:
- Qué trámite hacer
- Por qué hacerlo
- Cuándo hacerlo
- Qué documentos preparar
- Qué errores evitar
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from cores.personal_infrastructure.models import AdministrativeProcess, AdministrativeStep

logger = logging.getLogger("ownex.personal_infrastructure.admin_navigator")

ADMIN_DATA_PATH = Path.home() / ".ownex" / "personal_infrastructure" / "admin"
PROCESSES_FILE = ADMIN_DATA_PATH / "processes.json"


class AdministrativeNavigator:
    """Navegador de trámites administrativos."""

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or ADMIN_DATA_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.processes: dict[str, AdministrativeProcess] = {}
        self._load_data()
        self._initialize_default_processes()

    def _load_data(self) -> None:
        """Cargar procesos administrativos."""
        try:
            if PROCESSES_FILE.exists():
                with open(PROCESSES_FILE) as f:
                    data = json.load(f)
                    for proc_id, proc_data in data.items():
                        if proc_data.get("started_at"):
                            proc_data["started_at"] = datetime.fromisoformat(proc_data["started_at"])
                        if proc_data.get("completed_at"):
                            proc_data["completed_at"] = datetime.fromisoformat(proc_data["completed_at"])
                        # Convertir steps
                        steps = []
                        for step_data in proc_data.get("steps", []):
                            if step_data.get("completed_at"):
                                step_data["completed_at"] = datetime.fromisoformat(step_data["completed_at"])
                            steps.append(AdministrativeStep(**step_data))
                        proc_data["steps"] = steps
                        self.processes[proc_id] = AdministrativeProcess(**proc_data)
        except Exception as exc:
            logger.error("Error loading administrative processes: %s", exc)

    def _save_data(self) -> None:
        """Guardar procesos administrativos."""
        try:
            with open(PROCESSES_FILE, "w") as f:
                data = {k: asdict(v) for k, v in self.processes.items()}
                json.dump(data, f, indent=2, default=str)
        except Exception as exc:
            logger.error("Error saving administrative processes: %s", exc)

    def _initialize_default_processes(self) -> None:
        """Inicializar procesos por defecto."""
        if not self.processes:
            self._create_payment_method_process()
            self._create_fiscal_setup_process()
            self._create_professional_profile_process()
            self._save_data()

    def _create_payment_method_process(self) -> None:
        """Crear proceso para configurar método de cobro."""
        steps = [
            AdministrativeStep(
                step_id="create_wise",
                title="Crear cuenta Wise",
                description="Regístrate en Wise para recibir pagos internacionales",
                why_do_it="Wise tiene las mejores tasas de cambio y comisiones bajas para transferencias internacionales",
                when_do_it="Antes de recibir tu primer pago internacional",
                documents_needed=["DNI/Pasaporte", "Comprobante de domicilio", "Email personal"],
                errors_to_avoid=["Usar email de trabajo (puedes perder acceso)", "No verificar identidad completa"],
            ),
            AdministrativeStep(
                step_id="connect_bank",
                title="Conectar cuenta bancaria",
                description="Vincula tu cuenta bancaria local a Wise para retirar fondos",
                why_do_it="Para convertir pagos internacionales a tu moneda local y retirarlos",
                when_do_it="Después de crear cuenta Wise y antes de recibir pagos",
                documents_needed=["CBU/CVU", "Alias", "Titularidad de cuenta"],
                errors_to_avoid=["Usar cuenta que no es tuya", "No verificar titularidad"],
            ),
            AdministrativeStep(
                step_id="test_transfer",
                title="Probar transferencia de prueba",
                description="Realiza una transferencia pequeña para verificar que todo funciona",
                why_do_it="Para asegurar que puedes recibir y retirar pagos sin problemas",
                when_do_it="Antes de recibir pagos reales",
                documents_needed=[],
                errors_to_avoid=["No verificar que el monto llegue correctamente"],
            ),
        ]

        self.processes["payment_method"] = AdministrativeProcess(
            process_id="payment_method",
            title="Configurar Método de Cobro",
            objective="Recibir pagos internacionales",
            steps=steps,
        )

    def _create_fiscal_setup_process(self) -> None:
        """Crear proceso para configuración fiscal (Argentina/ARCA)."""
        steps = [
            AdministrativeStep(
                step_id="determine_status",
                title="Determinar situación fiscal",
                description="Identifica si eres Monotributista, Autónomo o Responsable Inscripto",
                why_do_it="Para saber qué impuestos pagar y cómo declarar tus ingresos digitales",
                when_do_it="Antes de recibir ingresos significativos",
                documents_needed=["Constancia de AFIP", "Ingresos estimados"],
                errors_to_avoid=["No actualizar categoría cuando cambian tus ingresos"],
            ),
            AdministrativeStep(
                step_id="register_tax",
                title="Registrar como proveedor de servicios digitales",
                description="Regístrate correctamente para prestar servicios digitales si corresponde",
                why_do_it="Para estar cumpliendo con la normativa argentina sobre servicios digitales",
                when_do_it="Antes de ofrecer servicios a clientes internacionales",
                documents_needed=["Constancia de AFIP", "Datos de contacto"],
                errors_to_avoid=["No registrar actividad correctamente", "No emitir facturas"],
            ),
            AdministrativeStep(
                step_id="setup_bookkeeping",
                title="Configurar sistema de contabilidad",
                description="Organiza un sistema para registrar ingresos, gastos y retenciones",
                why_do_it="Para tener control fiscal y evitar problemas al momento de declarar",
                when_do_it="Desde el primer ingreso",
                documents_needed=["Planilla de seguimiento", "Sistema de facturación"],
                errors_to_avoid=["No registrar retenciones", "No guardar comprobantes"],
            ),
        ]

        self.processes["fiscal_setup"] = AdministrativeProcess(
            process_id="fiscal_setup",
            title="Configuración Fiscal Argentina",
            objective="Cumplir con obligaciones fiscales para ingresos digitales",
            steps=steps,
        )

    def _create_professional_profile_process(self) -> None:
        """Crear proceso para perfil profesional."""
        steps = [
            AdministrativeStep(
                step_id="create_github",
                title="Crear perfil GitHub profesional",
                description="Optimiza tu perfil de GitHub para mostrar tu trabajo",
                why_do_it="Los clientes y reclutadores revisan GitHub antes de contratar",
                when_do_it="Antes de aplicar a proyectos o freelance",
                documents_needed=["Foto profesional", "Bio clara", "Proyectos destacados"],
                errors_to_avoid=["Perfil vacío", "Sin README en repositorios", "Código desorganizado"],
            ),
            AdministrativeStep(
                step_id="create_portfolio",
                title="Crear portafolio personal",
                description="Crea un sitio o documento que muestre tus mejores proyectos",
                why_do_it="El portafolio es tu carta de presentación visual",
                when_do_it="Antes de buscar trabajo freelance",
                documents_needed=["Screenshots de proyectos", "Descripciones", "Links a repositorios"],
                errors_to_avoid=["Portafolio desorganizado", "Sin contexto de proyectos"],
            ),
            AdministrativeStep(
                step_id="optimize_linkedin",
                title="Optimizar perfil LinkedIn",
                description="Completa tu perfil de LinkedIn con información profesional",
                why_do_it="LinkedIn es una fuente importante de oportunidades de trabajo",
                when_do_it="En paralelo con GitHub y portafolio",
                documents_needed=["Experiencia", "Habilidades", "Proyectos"],
                errors_to_avoid=["Perfil incompleto", "Sin foto profesional", "Sin descripción"],
            ),
        ]

        self.processes["professional_profile"] = AdministrativeProcess(
            process_id="professional_profile",
            title="Perfil Profesional",
            objective="Crear presencia profesional visible para clientes y empleadores",
            steps=steps,
        )

    def get_process(self, process_id: str) -> AdministrativeProcess | None:
        """Obtener un proceso administrativo."""
        return self.processes.get(process_id)

    def get_all_processes(self) -> list[AdministrativeProcess]:
        """Obtener todos los procesos."""
        return list(self.processes.values())

    def start_process(self, process_id: str) -> AdministrativeProcess:
        """Iniciar un proceso administrativo."""
        if process_id not in self.processes:
            raise ValueError(f"Process {process_id} not found")

        process = self.processes[process_id]
        process.status = "in_progress"
        process.started_at = datetime.now()
        process.current_step_index = 0

        self._save_data()
        return process

    def advance_step(self, process_id: str, step_id: str) -> bool:
        """Avanzar un paso en el proceso."""
        if process_id not in self.processes:
            return False

        process = self.processes[process_id]
        step = next((s for s in process.steps if s.step_id == step_id), None)

        if not step:
            return False

        step.status = "completed"
        step.completed_at = datetime.now()

        # Avanzar al siguiente paso
        process.current_step_index += 1

        if process.current_step_index >= len(process.steps):
            process.status = "completed"
            process.completed_at = datetime.now()
        else:
            process.status = "in_progress"

        self._save_data()
        return True

    def get_process_status(self, process_id: str) -> dict[str, Any]:
        """Obtener estado detallado de un proceso."""
        process = self.processes.get(process_id)
        if not process:
            return {"error": "Process not found"}

        completed_steps = sum(1 for s in process.steps if s.status == "completed")
        total_steps = len(process.steps)
        progress = (completed_steps / total_steps * 100) if total_steps > 0 else 0

        current_step = process.steps[process.current_step_index] if process.current_step_index < len(process.steps) else None

        return {
            "process_id": process.process_id,
            "title": process.title,
            "objective": process.objective,
            "status": process.status,
            "progress": progress,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "current_step": current_step.to_dict() if current_step else None,
            "started_at": process.started_at.isoformat() if process.started_at else None,
            "completed_at": process.completed_at.isoformat() if process.completed_at else None,
        }

    def get_all_statuses(self) -> dict[str, dict[str, Any]]:
        """Obtener estado de todos los procesos."""
        return {proc_id: self.get_process_status(proc_id) for proc_id in self.processes.keys()}

    def get_next_action(self) -> str:
        """Obtener la próxima acción recomendada."""
        # Buscar proceso en progreso
        for process in self.processes.values():
            if process.status == "in_progress":
                if process.current_step_index < len(process.steps):
                    step = process.steps[process.current_step_index]
                    return f"Completar paso: {step.title} en proceso {process.title}"

        # Si no hay procesos en progreso, sugerir el primero pendiente
        for process in self.processes.values():
            if process.status == "pending":
                return f"Iniciar proceso: {process.title}"

        return "Todos los procesos administrativos están completados"


# Singleton instance
_admin_navigator: AdministrativeNavigator | None = None


def get_admin_navigator() -> AdministrativeNavigator:
    """Obtener instancia singleton del Administrative Navigator."""
    global _admin_navigator
    if _admin_navigator is None:
        _admin_navigator = AdministrativeNavigator()
    return _admin_navigator


def reset_admin_navigator() -> None:
    """Resetear instancia singleton."""
    global _admin_navigator
    _admin_navigator = None