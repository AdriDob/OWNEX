"""
DevinTool — Tool para ejecutar comandos de Devin CLI desde OWNEX OMEGA

Devin CLI es una herramienta gratuita de desarrollo de Cognition que:
- Ejecuta tareas de desarrollo autónomas
- Usa modelos de IA (Claude, etc.) detrás de escena
- Se ejecuta en la terminal con comandos como `opencode run "tarea"`

Este tool permite que OWNEX OMEGA use Devin CLI para:
- Refactor de código
- Implementación de features
- Debugging
- Análisis de código
- Generación de tests
- Optimización de rendimiento
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.devin_tool")


class DevinCommandType(Enum):
    """Tipo de comando de Devin."""
    RUN = "run"  # Ejecutar tarea de desarrollo
    PLAN = "plan"  # Planificar tarea
    EDIT = "edit"  # Editar archivos
    REFACTOR = "refactor"  # Refactor código
    DEBUG = "debug"  # Debugging
    TEST = "test"  # Generar tests
    OPTIMIZE = "optimize"  # Optimizar rendimiento
    REVIEW = "review"  # Code review


class DevinModel(Enum):
    """Modelos disponibles en Devin."""
    CLAUDE_SONNET_4_5 = "anthropic/claude-sonnet-4-5"
    CLAUDE_HAIKU = "anthropic/claude-haiku"
    DEEPSEEK_V4 = "opencode/deepseek-v4-flash-free"
    NEMOTRON = "opencode/nemotron-4-free"
    MIMO = "opencode/mimo-free"


@dataclass
class DevinTask:
    """Tarea de desarrollo para Devin."""
    task_id: str
    command_type: DevinCommandType
    prompt: str
    model: DevinModel
    files: list[str]
    context: dict[str, Any]
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "pending"  # pending, running, completed, failed
    output: str = ""
    error: str = ""
    duration_seconds: int = 0


class DevinTool:
    """Tool para ejecutar comandos de Devin CLI."""

    def __init__(self, devin_path: str = "opencode"):
        """Inicializar DevinTool."""
        self.devin_path = devin_path
        self.tasks: dict[str, DevinTask] = {}
        self.default_model = DevinModel.DEEPSEEK_V4  # Usar modelo gratuito por defecto

    def _execute_command(
        self,
        command: str,
        working_dir: str | None = None,
        timeout: int = 300,
    ) -> tuple[str, str, int]:
        """Ejecutar comando de shell."""
        try:
            logger.info(f"[DEVIN] Ejecutando comando: {command}")

            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            stdout = result.stdout
            stderr = result.stderr
            returncode = result.returncode

            logger.info(f"[DEVIN] Comando completado con código: {returncode}")

            return stdout, stderr, returncode

        except subprocess.TimeoutExpired:
            logger.error(f"[DEVIN] Comando timeout después de {timeout}s")
            return "", "Command timeout", -1
        except Exception as e:
            logger.error(f"[DEVIN] Error ejecutando comando: {e}")
            return "", str(e), -1

    def run_task(
        self,
        prompt: str,
        command_type: DevinCommandType = DevinCommandType.RUN,
        model: DevinModel | None = None,
        files: list[str] | None = None,
        context: dict[str, Any] | None = None,
        working_dir: str | None = None,
        timeout: int = 300,
    ) -> DevinTask:
        """Ejecutar tarea de desarrollo con Devin CLI."""
        task_id = f"devin_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        model = model or self.default_model
        files = files or []
        context = context or {}

        # Crear tarea
        task = DevinTask(
            task_id=task_id,
            command_type=command_type,
            prompt=prompt,
            model=model,
            files=files,
            context=context,
            created_at=datetime.now(),
        )

        self.tasks[task_id] = task

        # Construir comando
        command = self._build_command(task)

        # Ejecutar comando
        task.status = "running"
        task.started_at = datetime.now()

        stdout, stderr, returncode = self._execute_command(
            command,
            working_dir=working_dir,
            timeout=timeout,
        )

        task.completed_at = datetime.now()
        task.duration_seconds = int((task.completed_at - task.started_at).total_seconds())

        if returncode == 0:
            task.status = "completed"
            task.output = stdout
        else:
            task.status = "failed"
            task.error = stderr if stderr else stdout

        logger.info(f"[DEVIN] Tarea {task_id} completada: {task.status}")

        return task

    def _build_command(self, task: DevinTask) -> str:
        """Construir comando de Devin CLI."""
        base_command = f"{self.devin_path} run"

        # Agregar modelo
        model_arg = f"--model {task.model.value}"

        # Agregar archivos si hay
        files_arg = ""
        if task.files:
            files_arg = " ".join([f'"{f}"' for f in task.files])

        # Construir comando completo
        command = f"{base_command} {model_arg} {files_arg} \"{task.prompt}\""

        return command

    def get_task(self, task_id: str) -> DevinTask | None:
        """Obtener tarea por ID."""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: str) -> list[DevinTask]:
        """Obtener tareas por estado."""
        return [task for task in self.tasks.values() if task.status == status]

    def get_recent_tasks(self, limit: int = 10) -> list[DevinTask]:
        """Obtener tareas recientes."""
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.created_at,
            reverse=True,
        )
        return sorted_tasks[:limit]

    def refactor_code(
        self,
        file_path: str,
        refactor_prompt: str,
        model: DevinModel | None = None,
        working_dir: str | None = None,
    ) -> DevinTask:
        """Refactor código usando Devin."""
        return self.run_task(
            prompt=f"Refactor el archivo {file_path}: {refactor_prompt}",
            command_type=DevinCommandType.REFACTOR,
            model=model,
            files=[file_path],
            working_dir=working_dir,
        )

    def implement_feature(
        self,
        feature_description: str,
        files: list[str] | None = None,
        model: DevinModel | None = None,
        working_dir: str | None = None,
    ) -> DevinTask:
        """Implementar feature usando Devin."""
        return self.run_task(
            prompt=f"Implementar feature: {feature_description}",
            command_type=DevinCommandType.RUN,
            model=model,
            files=files,
            working_dir=working_dir,
        )

    def debug_code(
        self,
        error_description: str,
        files: list[str] | None = None,
        model: DevinModel | None = None,
        working_dir: str | None = None,
    ) -> DevinTask:
        """Debug código usando Devin."""
        return self.run_task(
            prompt=f"Debug este código: {error_description}",
            command_type=DevinCommandType.DEBUG,
            model=model,
            files=files,
            working_dir=working_dir,
        )

    def generate_tests(
        self,
        file_path: str,
        test_framework: str = "pytest",
        model: DevinModel | None = None,
        working_dir: str | None = None,
    ) -> DevinTask:
        """Generar tests usando Devin."""
        return self.run_task(
            prompt=f"Generar tests para {file_path} usando {test_framework}",
            command_type=DevinCommandType.TEST,
            model=model,
            files=[file_path],
            working_dir=working_dir,
        )

    def optimize_code(
        self,
        file_path: str,
        optimization_goal: str = "performance",
        model: DevinModel | None = None,
        working_dir: str | None = None,
    ) -> DevinTask:
        """Optimizar código usando Devin."""
        return self.run_task(
            prompt=f"Optimizar {file_path} para {optimization_goal}",
            command_type=DevinCommandType.OPTIMIZE,
            model=model,
            files=[file_path],
            working_dir=working_dir,
        )

    def code_review(
        self,
        file_path: str,
        review_focus: str = "security",
        model: DevinModel | None = None,
        working_dir: str | None = None,
    ) -> DevinTask:
        """Code review usando Devin."""
        return self.run_task(
            prompt=f"Code review de {file_path} enfocado en {review_focus}",
            command_type=DevinCommandType.REVIEW,
            model=model,
            files=[file_path],
            working_dir=working_dir,
        )

    def plan_feature(
        self,
        feature_description: str,
        model: DevinModel | None = None,
        working_dir: str | None = None,
    ) -> DevinTask:
        """Planificar feature usando Devin."""
        return self.run_task(
            prompt=f"Planificar implementación de: {feature_description}",
            command_type=DevinCommandType.PLAN,
            model=model,
            working_dir=working_dir,
        )

    def check_devin_available(self) -> bool:
        """Verificar si Devin CLI está disponible."""
        stdout, stderr, returncode = self._execute_command("opencode --version", timeout=10)
        return returncode == 0

    def get_devin_version(self) -> str | None:
        """Obtener versión de Devin CLI."""
        stdout, stderr, returncode = self._execute_command("opencode --version", timeout=10)
        if returncode == 0:
            return stdout.strip()
        return None


# Singleton instance
_devin_tool: DevinTool | None = None


def get_devin_tool(devin_path: str = "opencode") -> DevinTool:
    """Obtener instancia singleton de DevinTool."""
    global _devin_tool

    if _devin_tool is None:
        _devin_tool = DevinTool(devin_path)

    return _devin_tool
