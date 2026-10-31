"""Personal Infrastructure Manager - Main Manager.

Gestiona la infraestructura personal del usuario de forma permanente.
Es el asistente experto que entiende objetivos humanos y los traduce
en configuraciones técnicas.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from cores.personal_infrastructure.models import (
    AccountIntegration,
    AdministrativeProcess,
    AdministrativeStep,
    ApprovalCategory,
    InfrastructureSnapshot,
    IntegrationHealth,
    LearningExplanation,
    ObjectiveCategory,
    ObjectiveDefinition,
    ObjectiveProgress,
    WealthAccount,
)

logger = logging.getLogger("ownex.personal_infrastructure.manager")

STORAGE_PATH = Path.home() / ".ownex" / "personal_infrastructure"
OBJECTIVES_FILE = STORAGE_PATH / "objectives.json"
INTEGRATIONS_FILE = STORAGE_PATH / "integrations.json"
PROGRESS_FILE = STORAGE_PATH / "progress.json"
ADMIN_FILE = STORAGE_PATH / "administrative.json"
WEALTH_FILE = STORAGE_PATH / "wealth.json"


class PersonalInfrastructureManager:
    """Gestor principal de infraestructura personal."""

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or STORAGE_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.objectives: dict[str, ObjectiveDefinition] = {}
        self.integrations: dict[str, AccountIntegration] = {}
        self.progress: dict[str, ObjectiveProgress] = {}
        self.administrative_processes: dict[str, AdministrativeProcess] = {}
        self.wealth_accounts: dict[str, WealthAccount] = {}

        self._load_data()
        self._initialize_default_objectives()

    def _load_data(self) -> None:
        """Cargar datos persistidos."""
        try:
            if OBJECTIVES_FILE.exists():
                with open(OBJECTIVES_FILE) as f:
                    data = json.load(f)
                    for obj_id, obj_data in data.items():
                        # Convertir strings a enums
                        if "category" in obj_data:
                            obj_data["category"] = ObjectiveCategory(obj_data["category"])
                        self.objectives[obj_id] = ObjectiveDefinition(**obj_data)

            if INTEGRATIONS_FILE.exists():
                with open(INTEGRATIONS_FILE) as f:
                    data = json.load(f)
                    for int_id, int_data in data.items():
                        if "category" in int_data:
                            int_data["category"] = ObjectiveCategory(int_data["category"])
                        if "health" in int_data:
                            int_data["health"] = IntegrationHealth(int_data["health"])
                        if "explanation" in int_data and int_data["explanation"]:
                            int_data["explanation"] = LearningExplanation(**int_data["explanation"])
                        self.integrations[int_id] = AccountIntegration(**int_data)

            if PROGRESS_FILE.exists():
                with open(PROGRESS_FILE) as f:
                    data = json.load(f)
                    for prog_id, prog_data in data.items():
                        # Convertir datetime strings
                        if prog_data.get("started_at"):
                            prog_data["started_at"] = datetime.fromisoformat(prog_data["started_at"])
                        if prog_data.get("completed_at"):
                            prog_data["completed_at"] = datetime.fromisoformat(prog_data["completed_at"])
                        self.progress[prog_id] = ObjectiveProgress(**prog_data)

            if ADMIN_FILE.exists():
                with open(ADMIN_FILE) as f:
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
                        self.administrative_processes[proc_id] = AdministrativeProcess(**proc_data)

            if WEALTH_FILE.exists():
                with open(WEALTH_FILE) as f:
                    data = json.load(f)
                    for acc_id, acc_data in data.items():
                        if acc_data.get("last_sync"):
                            acc_data["last_sync"] = datetime.fromisoformat(acc_data["last_sync"])
                        self.wealth_accounts[acc_id] = WealthAccount(**acc_data)

        except Exception as exc:
            logger.error("Error loading personal infrastructure data: %s", exc)

    def _save_data(self) -> None:
        """Guardar datos a disco."""
        try:
            # Save objectives
            with open(OBJECTIVES_FILE, "w") as f:
                data = {k: asdict(v) for k, v in self.objectives.items()}
                json.dump(data, f, indent=2, default=str)

            # Save integrations
            with open(INTEGRATIONS_FILE, "w") as f:
                data = {k: asdict(v) for k, v in self.integrations.items()}
                json.dump(data, f, indent=2, default=str)

            # Save progress
            with open(PROGRESS_FILE, "w") as f:
                data = {k: asdict(v) for k, v in self.progress.items()}
                json.dump(data, f, indent=2, default=str)

            # Save administrative processes
            with open(ADMIN_FILE, "w") as f:
                data = {k: asdict(v) for k, v in self.administrative_processes.items()}
                json.dump(data, f, indent=2, default=str)

            # Save wealth accounts
            with open(WEALTH_FILE, "w") as f:
                data = {k: asdict(v) for k, v in self.wealth_accounts.items()}
                json.dump(data, f, indent=2, default=str)

        except Exception as exc:
            logger.error("Error saving personal infrastructure data: %s", exc)

    def _initialize_default_objectives(self) -> None:
        """Inicializar objetivos por defecto si no existen."""
        if not self.objectives:
            self._create_development_objective()
            self._create_bug_bounty_objective()
            self._create_dev_bounty_objective()
            self._create_freelance_objective()
            self._create_wealth_objective()
            self._save_data()

    def _create_development_objective(self) -> None:
        """Crear objetivo de desarrollo."""
        explanation = LearningExplanation(
            title="Desarrollo de Software",
            what_is="El desarrollo de software es el proceso de crear, mantener y mejorar aplicaciones.",
            what_for="Para crear productos digitales, servicios web, aplicaciones móviles y herramientas.",
            what_changes="Te permitirá trabajar con código, contribuir a proyectos open source y generar ingresos.",
            what_risk="Sin cuenta de GitHub, no podrás colaborar en proyectos ni recibir pagos por código.",
            what_if_not="Perderás oportunidades de trabajo freelance, colaboraciones y exposición profesional.",
            simple_version="GitHub es donde los desarrolladores guardan su código y colaboran. Es esencial.",
        )

        integrations = [
            AccountIntegration(
                integration_id="github",
                name="GitHub",
                category=ObjectiveCategory.DEVELOPMENT,
                purpose="Almacenar código, colaborar en proyectos, recibir pull requests",
                permissions=["read", "write", "fork"],
                connection_type="oauth",
                explanation=LearningExplanation(
                    title="GitHub",
                    what_is="GitHub es una plataforma de alojamiento de código y colaboración.",
                    what_for="Para guardar tu código, colaborar con otros desarrolladores y construir tu portafolio.",
                    what_changes="Tu código estará accesible desde cualquier lugar y podrás colaborar en proyectos.",
                    what_risk="Sin GitHub, tu código vive solo en tu computadora (riesgo de pérdida).",
                    what_if_not="No podrás colaborar en proyectos open source ni recibir contribuciones.",
                    simple_version="GitHub es donde los desarrolladores guardan su código. Es como Google Drive para código.",
                ),
            ),
            AccountIntegration(
                integration_id="gitlab",
                name="GitLab",
                category=ObjectiveCategory.DEVELOPMENT,
                purpose="CI/CD, proyectos privados, alternativas a GitHub",
                permissions=["read", "write"],
                connection_type="oauth",
            ),
        ]

        self.objectives["development"] = ObjectiveDefinition(
            objective_id="development",
            category=ObjectiveCategory.DEVELOPMENT,
            title="Desarrollo de Software",
            description="Configurar entorno de desarrollo profesional para colaborar en proyectos",
            required_integrations=integrations,
            explanation=explanation,
            estimated_duration_hours=2,
        )

    def _create_bug_bounty_objective(self) -> None:
        """Crear objetivo de bug bounty."""
        explanation = LearningExplanation(
            title="Bug Bounty - Caza de Vulnerabilidades",
            what_is="Bug bounty es un programa donde empresas pagan por encontrar vulnerabilidades en sus sistemas.",
            what_for="Para generar ingresos buscando fallos de seguridad en aplicaciones web y móviles.",
            what_changes="Podrás generar ingresos reportando vulnerabilidades a empresas y recibir pagos.",
            what_risk="Sin plataformas de bug bounty, no tendrás dónde enviar tus hallazgos ni recibir pagos.",
            what_if_not="Perderás oportunidades de ingresos pasivos y experiencia en seguridad.",
            simple_version="Bug bounty es como un juego de detective: encuentras fallos, los reportas, te pagan.",
        )

        integrations = [
            AccountIntegration(
                integration_id="hackerone",
                name="HackerOne",
                category=ObjectiveCategory.BUG_BOUNTY,
                purpose="Recibir oportunidades de bug bounty, enviar reportes, recibir pagos",
                permissions=["read", "write"],
                connection_type="oauth",
                explanation=LearningExplanation(
                    title="HackerOne",
                    what_is="HackerOne es la plataforma más grande de bug bounty del mundo.",
                    what_for="Para encontrar programas de bug bounty, enviar reportes y recibir pagos.",
                    what_changes="Tendrás acceso a miles de programas de bug bounty de empresas grandes.",
                    what_risk="Sin HackerOne, te limitas a plataformas más pequeñas con menos oportunidades.",
                    what_if_not="Perderás acceso a programas exclusivos de empresas como Google, Facebook, etc.",
                    simple_version="HackerOne es donde las empresas ponen sus programas de bug bounty. Es el mercado principal.",
                ),
            ),
            AccountIntegration(
                integration_id="bugcrowd",
                name="Bugcrowd",
                category=ObjectiveCategory.BUG_BOUNTY,
                purpose="Alternativa a HackerOne, programas exclusivos",
                permissions=["read", "write"],
                connection_type="oauth",
            ),
            AccountIntegration(
                integration_id="intigriti",
                name="Intigriti",
                category=ObjectiveCategory.BUG_BOUNTY,
                purpose="Plataforma europea enfocada en privacidad",
                permissions=["read", "write"],
                connection_type="oauth",
            ),
        ]

        self.objectives["bug_bounty"] = ObjectiveDefinition(
            objective_id="bug_bounty",
            category=ObjectiveCategory.BUG_BOUNTY,
            title="Bug Bounty Professional",
            description="Configurar cuentas en plataformas de bug bounty para recibir oportunidades",
            required_integrations=integrations,
            explanation=explanation,
            estimated_duration_hours=3,
            dependencies=["development"],
        )

    def _create_dev_bounty_objective(self) -> None:
        """Crear objetivo de dev bounty (freelance de código)."""
        explanation = LearningExplanation(
            title="Dev Bounty - Freelance de Código",
            what_is="Dev bounty es trabajar en issues reales de código y recibir pagos por soluciones.",
            what_for="Para generar ingresos resolviendo bugs, implementando features y mejorando código.",
            what_changes="Podrás monetizar tus habilidades de desarrollo en proyectos reales.",
            what_risk="Sin plataformas de dev bounty, te limitas a freelancing tradicional (más competencia).",
            what_if_not="Perderás oportunidades de ingresos automáticos y portafolio de contribuciones.",
            simple_version="Dev bounty es como bug bounty pero para código: arreglas bugs, te pagan.",
        )

        integrations = [
            AccountIntegration(
                integration_id="superteam",
                name="Superteam",
                category=ObjectiveCategory.DEV_BOUNTY,
                purpose="Plataforma de dev bounty más grande, issues de código real",
                permissions=["read", "write"],
                connection_type="oauth",
            ),
            AccountIntegration(
                integration_id="opire",
                name="Opire",
                category=ObjectiveCategory.DEV_BOUNTY,
                purpose="Bounties de código, proyectos open source",
                permissions=["read", "write"],
                connection_type="oauth",
            ),
        ]

        self.objectives["dev_bounty"] = ObjectiveDefinition(
            objective_id="dev_bounty",
            category=ObjectiveCategory.DEV_BOUNTY,
            title="Dev Bounty Professional",
            description="Configurar cuentas en plataformas de dev bounty para resolver issues de código",
            required_integrations=integrations,
            explanation=explanation,
            estimated_duration_hours=2,
            dependencies=["development"],
        )

    def _create_freelance_objective(self) -> None:
        """Crear objetivo de freelance."""
        explanation = LearningExplanation(
            title="Freelance Profesional",
            what_is="Freelance es trabajar de forma independiente para múltiples clientes.",
            what_for="Para generar ingresos diversos y construir una cartera de clientes.",
            what_changes="Podrás trabajar con múltiples clientes y generar ingresos variables.",
            what_risk="Sin plataformas de freelance, te limitas a networking manual (más lento).",
            what_if_not="Perderás acceso a oportunidades visibles y proceso de pagos estandarizado.",
            simple_version="Freelance es como tener varios jefes pero tú eliges cuándo y para quién trabajar.",
        )

        integrations = [
            AccountIntegration(
                integration_id="upwork",
                name="Upwork",
                category=ObjectiveCategory.FREELANCE,
                purpose="Plataforma más grande de freelance, proyectos variados",
                permissions=["read", "write"],
                connection_type="oauth",
            ),
            AccountIntegration(
                integration_id="freelancer",
                name="Freelancer",
                category=ObjectiveCategory.FREELANCE,
                purpose="Alternativa a Upwork, proyectos de código",
                permissions=["read", "write"],
                connection_type="oauth",
            ),
        ]

        self.objectives["freelance"] = ObjectiveDefinition(
            objective_id="freelance",
            category=ObjectiveCategory.FREELANCE,
            title="Freelance Profesional",
            description="Configurar perfil profesional en plataformas de freelance",
            required_integrations=integrations,
            explanation=explanation,
            estimated_duration_hours=4,
            dependencies=["development"],
        )

    def _create_wealth_objective(self) -> None:
        """Crear objetivo de wealth/finanzas."""
        explanation = LearningExplanation(
            title="Gestión de Ingresos Digitales",
            what_is="Gestión de ingresos digitales es organizar cómo recibes y gestionas pagos online.",
            what_for="Para recibir pagos internacionales, organizar tus ingresos y preparar impuestos.",
            what_changes="Podrás recibir pagos de cualquier país y tener control financiero completo.",
            what_risk="Sin configuración financiera, no podrás recibir pagos ni organizar tus ingresos.",
            what_if_not="Perderás ingresos por no tener métodos de pago configurados o problemas fiscales.",
            simple_version="Gestión de ingresos es tener una cuenta para recibir pagos y organizar tus ganancias.",
        )

        integrations = [
            AccountIntegration(
                integration_id="wise",
                name="Wise",
                category=ObjectiveCategory.WEALTH,
                purpose="Recibir pagos internacionales, conversión de divisas",
                permissions=["read", "write"],
                connection_type="oauth",
                explanation=LearningExplanation(
                    title="Wise (TransferWise)",
                    what_is="Wise es un servicio de transferencias de dinero internacionales con mejores tasas.",
                    what_for="Para recibir pagos de clientes internacionales y convertir divisas sin perder dinero.",
                    what_changes="Podrás recibir pagos en USD/EUR y convertir a tu moneda local con tasas justas.",
                    what_risk="Sin Wise, usas transferencias bancarias tradicionales (más caras y lentas).",
                    what_if_not="Perderás dinero en comisiones de conversión y tiempos de transferencia largos.",
                    simple_version="Wise es como un banco pero para transferencias internacionales sin comisiones abusivas.",
                ),
            ),
            AccountIntegration(
                integration_id="paypal",
                name="PayPal",
                category=ObjectiveCategory.WEALTH,
                purpose="Recibir pagos, alternativa estándar",
                permissions=["read", "write"],
                connection_type="oauth",
            ),
        ]

        self.objectives["wealth"] = ObjectiveDefinition(
            objective_id="wealth",
            category=ObjectiveCategory.WEALTH,
            title="Gestión de Ingresos Digitales",
            description="Configurar métodos de pago y organización financiera para ingresos digitales",
            required_integrations=integrations,
            explanation=explanation,
            estimated_duration_hours=3,
        )

    def get_objective(self, objective_id: str) -> ObjectiveDefinition | None:
        """Obtener definición de objetivo."""
        return self.objectives.get(objective_id)

    def get_all_objectives(self) -> list[ObjectiveDefinition]:
        """Obtener todos los objetivos."""
        return list(self.objectives.values())

    def get_objectives_by_category(self, category: ObjectiveCategory) -> list[ObjectiveDefinition]:
        """Obtener objetivos por categoría."""
        return [obj for obj in self.objectives.values() if obj.category == category]

    def start_objective(self, objective_id: str) -> ObjectiveProgress:
        """Iniciar un objetivo."""
        if objective_id not in self.objectives:
            raise ValueError(f"Objective {objective_id} not found")

        if objective_id in self.progress:
            return self.progress[objective_id]

        objective = self.objectives[objective_id]

        # Verificar dependencias
        for dep_id in objective.dependencies:
            if dep_id not in self.progress or self.progress[dep_id].completion_percentage < 100:
                logger.warning("Objective %s has unmet dependency: %s", objective_id, dep_id)

        progress = ObjectiveProgress(
            objective_id=objective_id,
            started_at=datetime.now(),
            pending_tasks=[integ.integration_id for integ in objective.required_integrations],
            current_step="Crear cuenta " + objective.required_integrations[0].name if objective.required_integrations else "",
        )

        self.progress[objective_id] = progress
        self._save_data()
        return progress

    def complete_integration_task(self, objective_id: str, integration_id: str) -> bool:
        """Marcar una integración como completada."""
        if objective_id not in self.progress:
            return False

        progress = self.progress[objective_id]

        if integration_id not in progress.pending_tasks:
            return False

        progress.pending_tasks.remove(integration_id)
        progress.completed_tasks.append(integration_id)

        # Actualizar integración
        if integration_id in self.integrations:
            self.integrations[integration_id].health = IntegrationHealth.CONNECTED
            self.integrations[integration_id].last_sync = datetime.now()

        # Calcular progreso
        objective = self.objectives.get(objective_id)
        if objective:
            total = len(objective.required_integrations)
            if total > 0:
                progress.completion_percentage = (len(progress.completed_tasks) / total) * 100

        if progress.completion_percentage >= 100:
            progress.completed_at = datetime.now()

        self._save_data()
        return True

    def get_infrastructure_snapshot(self) -> InfrastructureSnapshot:
        """Obtener snapshot completo de la infraestructura."""
        # Calcular overall completion
        total_objectives = len(self.objectives)
        completed_objectives = sum(1 for p in self.progress.values() if p.completion_percentage >= 100)
        overall_completion = (completed_objectives / total_objectives * 100) if total_objectives > 0 else 0.0

        # Encontrar próxima acción recomendada
        next_action = self._get_next_recommended_action()

        return InfrastructureSnapshot(
            objectives_progress=self.progress,
            integrations=self.integrations,
            administrative_processes=self.administrative_processes,
            wealth_accounts=self.wealth_accounts,
            overall_completion=overall_completion,
            next_recommended_action=next_action,
            last_updated=datetime.now(),
        )

    def _get_next_recommended_action(self) -> str:
        """Determinar la próxima acción recomendada."""
        # Buscar objetivo iniciado pero no completado
        for obj_id, progress in self.progress.items():
            if progress.completion_percentage < 100 and progress.pending_tasks:
                next_integration = progress.pending_tasks[0]
                integration = self.integrations.get(next_integration)
                if integration:
                    return f"Configurar cuenta {integration.name} para objetivo {obj_id}"

        # Si no hay objetivos iniciados, sugerir el primero
        if self.objectives and not self.progress:
            first_obj = list(self.objectives.values())[0]
            return f"Iniciar objetivo: {first_obj.title}"

        return "Todos los objetivos están completados"

    def get_integration_health(self) -> dict[str, Any]:
        """Obtener estado de salud de todas las integraciones."""
        return {
            integration_id: {
                "name": integ.name,
                "health": integ.health.value,
                "last_sync": integ.last_sync.isoformat() if integ.last_sync else None,
                "risks": integ.risks,
                "recommended_actions": integ.recommended_actions,
            }
            for integration_id, integ in self.integrations.items()
        }

    def explain_integration(self, integration_id: str) -> LearningExplanation | None:
        """Obtener explicación educativa de una integración."""
        integration = self.integrations.get(integration_id)
        return integration.explanation if integration else None

    def create_administrative_process(self, process_id: str, title: str, objective: str, steps: list[AdministrativeStep]) -> AdministrativeProcess:
        """Crear un proceso administrativo."""
        process = AdministrativeProcess(
            process_id=process_id,
            title=title,
            objective=objective,
            steps=steps,
        )
        self.administrative_processes[process_id] = process
        self._save_data()
        return process

    def advance_administrative_step(self, process_id: str, step_id: str) -> bool:
        """Avanzar un paso en un proceso administrativo."""
        if process_id not in self.administrative_processes:
            return False

        process = self.administrative_processes[process_id]
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

    def add_wealth_account(self, account: WealthAccount) -> None:
        """Agregar cuenta financiera (sin datos sensibles)."""
        self.wealth_accounts[account.account_id] = account
        self._save_data()

    def check_approval_category(self, action: str) -> ApprovalCategory:
        """Determinar categoría de aprobación para una acción."""
        # AUTO: Puede hacerlo solo
        auto_actions = ["organize_files", "update_docs", "run_tests", "generate_reports"]
        if action in auto_actions:
            return ApprovalCategory.AUTO

        # MANUAL: Nunca automático
        manual_actions = ["financial_movement", "investment", "payment", "legal_action"]
        if action in manual_actions:
            return ApprovalCategory.MANUAL

        # CONFIRM: Pregunta antes
        return ApprovalCategory.CONFIGURE


# Singleton instance
_personal_infrastructure_manager: PersonalInfrastructureManager | None = None


def get_personal_infrastructure_manager() -> PersonalInfrastructureManager:
    """Obtener instancia singleton del Personal Infrastructure Manager."""
    global _personal_infrastructure_manager
    if _personal_infrastructure_manager is None:
        _personal_infrastructure_manager = PersonalInfrastructureManager()
    return _personal_infrastructure_manager


def reset_personal_infrastructure_manager() -> None:
    """Resetear instancia singleton."""
    global _personal_infrastructure_manager
    _personal_infrastructure_manager = None
