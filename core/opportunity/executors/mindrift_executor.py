"""Mindrift Executor — Claim tasks, solve, and submit work on Mindrift.io.

Semi-autonomous features:
- Automatic preparation checklist generation
- Submission formatting optimization
- Task metadata enrichment for better scoring
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class MindriftExecutor(BaseExecutor):
    """Executor for Mindrift.io — claim AI data tasks and submit solutions.

    Semi-autonomous features:
    - Automatic preparation checklist generation
    - Submission formatting optimization
    - Task metadata enrichment for better scoring
    """

    platform = "mindrift"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("MINDRIFT_EMAIL")
        self.base_url = self.config.get("base_url", "https://api.mindrift.io/v1")

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        if action == "claim_task":
            return await self.claim_task(kwargs.get("task_id", ""))
        if action == "submit_task":
            return await self.submit_task(
                kwargs.get("task_id", ""),
                kwargs.get("solution_url", ""),
                kwargs.get("description", ""),
            )
        if action == "get_tasks":
            return await self.get_tasks(kwargs.get("status", "open"))
        if action == "health_check":
            return await self.health_check()
        if action == "prepare_task":
            return await self.prepare_task(kwargs.get("task_id", ""))
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def claim_task(self, task_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "claim_task", task_id, error="MINDRIFT_EMAIL not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/tasks/{task_id}/claim",
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "claim_task", task_id, data={"response": data})
                return ExecutionResult(False, "claim_task", task_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                return ExecutionResult(False, "claim_task", task_id, error=str(e))

    async def submit_task(self, task_id: str, solution_url: str, description: str = "") -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "submit_task", task_id, error="MINDRIFT_EMAIL not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/tasks/{task_id}/submit",
                    headers=await self._headers(),
                    json={
                        "solution_url": solution_url,
                        "description": description or self._format_description(task_id),
                    },
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "submit_task", task_id, data={"response": data})
                return ExecutionResult(False, "submit_task", task_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                return ExecutionResult(False, "submit_task", task_id, error=str(e))

    async def prepare_task(self, task_id: str) -> ExecutionResult:
        """Semi-autonomous: Generate preparation checklist and guidance for a task.

        Does NOT solve the task automatically - provides structured guidance
        for the user to follow while working in Mindrift.
        """
        if not self.token:
            return ExecutionResult(False, "prepare_task", task_id, error="MINDRIFT_EMAIL not configured")

        async with httpx.AsyncClient() as client:
            try:
                # Fetch task details
                resp = await client.get(
                    f"{self.base_url}/tasks/{task_id}",
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code != 200:
                    return ExecutionResult(False, "prepare_task", task_id, error=f"HTTP {resp.status_code}: Cannot fetch task")

                task_data = resp.json()

                # Generate structured preparation guide
                preparation = self._generate_preparation_guide(task_data)

                return ExecutionResult(True, "prepare_task", task_id, data={"preparation": preparation})

            except Exception as e:
                return ExecutionResult(False, "prepare_task", task_id, error=str(e))

    def _generate_preparation_guide(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """Generate a structured preparation guide for the task.

        This is SEMI-AUTONOMOUS: it provides structured guidance based on
        task metadata, but the actual solution creation is done by the user.
        """
        categories = task_data.get("categories", ["ai_training", "evaluation"])
        task_title = task_data.get("title", "Tarea Mindrift")
        task_description = task_data.get("description", "")
        estimated_time = task_data.get("estimated_time", "1.5")
        reward = task_data.get("reward", "$0.05")

        # Determine task type based on categories and description
        task_type = self._classify_task_type(categories, task_description)

        # Generate appropriate checklist based on task type
        checklist = self._generate_checklist(task_type, categories)

        return {
            "task_id": task_data.get("id"),
            "task_title": task_title,
            "task_type": task_type,
            "estimated_hours": float(estimated_time) if estimated_time else 1.5,
            "reward": reward,
            "categories": categories,
            "preparation_guide": {
                "objective": self._extract_objective(task_description),
                "key_deliverables": self._extract_deliverables(task_description),
                "checklist": checklist,
                "technical_guidelines": self._get_guidelines(task_type),
                "quality_criteria": self._get_quality_criteria(task_type),
                "estimated_time_hours": float(estimated_time) if estimated_time else 1.5,
                "expected_output_format": self._get_output_format(task_type),
            },
            "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
        }

    def _classify_task_type(self, categories: list[str], description: str) -> str:
        """Classify the task type for appropriate guidance."""
        desc_lower = (description or "").lower()
        cats_lower = [c.lower() for c in categories]

        if any(kw in desc_lower or kw in cats_lower for kw in ["code review", "review", "diff", "pull request"]):
            return "code_review"
        if any(kw in desc_lower or kw in cats_lower for kw in ["data annotation", "label", "classification", "tagging"]):
            return "data_annotation"
        if any(kw in desc_lower or kw in cats_lower for kw in ["essay", "writing", "content", "article"]):
            return "writing"
        if any(kw in desc_lower or kw in cats_lower for kw in ["translation", "language", "multilingual"]):
            return "translation"
        if any(kw in desc_lower or kw in cats_lower for kw in ["analysis", "research", "survey"]):
            return "analysis"
        if any(kw in desc_lower or kw in cats_lower for kw in ["comparison", "benchmark", "evaluation"]):
            return "evaluation"
        return "general"

    def _generate_checklist(self, task_type: str, categories: list[str]) -> list[dict[str, str]]:
        """Generate task-type-specific checklist.

        Semi-autonomous: provides appropriate checklist, user follows it.
        """
        base_checklist = [
            {"step": "READ", "description": "Lee cuidadosamente todas las instrucciones del task"},
            {"step": "UNDERSTAND", "description": "Asegúrate de entender el objetivo y entregables"},
        ]

        type_specific = {
            "code_review": [
                {"step": "FORK/CLONE", "description": "Fork del repo o clona el proyecto"},
                {"step": "RUN TESTS", "description": "Ejecutá tests existentes para baseline"},
                {"step": "ANALYZE DIFF", "description": "Analizá el diff/cambios solicitados"},
                {"step": "IDENTIFY ISSUES", "description": "Identificá bugs, improvements, refactoring"},
                {"step": "WRITE REVIEW", "description": "Escribí review con rationale y suggestions"},
                {"step": "TEST FIXES", "description": "Probá tus suggestions si es posible"},
            ],
            "data_annotation": [
                {"step": "REVIEW SCHEMA", "description": "Entendé el esquema de etiquetado"},
                {"step": "SAMPLE REVIEW", "description": "Revisá 2-3 ejemplos para entender el estándar"},
                {"step": "ANNOTATE SAMPLE", "description": "Etiquetá 5-10 ejemplos de práctica"},
                {"step": "VALIDATE CONSISTENCY", "description": "Verificá consistencia en tus etiquetas"},
                {"step": "FULL ANNOTATION", "description": "Etiquetá el resto del dataset"},
            ],
            "evaluation": [
                {"step": "DEFINE METRICS", "description": "Identificá las métricas a evaluar"},
                {"step": "RUN BASELINE", "description": "Ejecutá baseline con modelo simple"},
                {"step": "COMPARE RESULTS", "description": "Compará con y sin improvements"},
                {"step": "DOCUMENT FINDINGS", "description": "Documentá hallazgos y conclusiones"},
            ],
            "general": [
                {"step": "INVESTIGATE", "description": "Investigá el context y requisitos del task"},
                {"step": "PLAN APPROACH", "description": "Planificá tu enfoque antes de empezar"},
                {"step": "EXECUTE", "description": "Ejecutá el trabajo principal"},
                {"step": "VALIDATE", "description": "Validá que cumpla los requisitos"},
                {"step": "DOCUMENT", "description": "Documentá tus resultados y proceso"},
            ],
        }

        return type_specific.get(task_type, base_checklist)

    def _extract_objective(self, description: str) -> str:
        """Extract the main objective from task description."""
        if not description:
            return "Completar las instrucciones de la task de AI training"
        # Simple extraction: first meaningful sentence
        sentences = [s.strip() for s in description.split(". ") if s.strip()]
        return sentences[0] if sentences else description[:100] + "..."

    def _extract_deliverables(self, description: str) -> list[str]:
        """Extract expected deliverables from task description."""
        if not description:
            return ["Solución completada según especificaciones"]
        # Look for deliverable indicators
        deliverables = []
        lower = description.lower()
        if "code" in lower or "repository" in lower:
            deliverables.append("Código completado y probado")
        if "report" in lower or "document" in lower:
            deliverables.append("Informe o documentación")
        if "analysis" in lower:
            deliverables.append("Análisis de resultados")
        if not deliverables:
            deliverables.append("Task completado según requisitos")
        return deliverables

    def _get_guidelines(self, task_type: str) -> list[str]:
        """Get technical guidelines for the task type."""
        guidelines_map = {
            "code_review": [
                "Usá PEP 8 o style guide del proyecto",
                "Comentá tus decisiones de review",
                "Sé constructivo y específico",
                "Priorizá fixes por impacto",
            ],
            "data_annotation": [
                "Sé consistente con el esquema de etiquetado",
                "Revisá inter-rater reliability si es posible",
                "Documenta casos borderline",
                "Mantené la calidad sobre la velocidad",
            ],
            "evaluation": [
                "Usá datasets de test separados",
                "Reportá métricas tanto de éxito como de fallo",
                "Compará resultados de forma justa",
                "Documentá limitaciones del experimento",
            ],
            "general": [
                "Seguí las instrucciones del task exactamente",
                "Documentá tu proceso para reproducibilidad",
                "Contactá al admin si tenés dudas",
                "Entregá en el formato solicitado",
            ],
        }
        return guidelines_map.get(task_type, guidelines_map["general"])

    def _get_quality_criteria(self, task_type: str) -> list[str]:
        """Get quality criteria validation points."""
        quality_map = {
            "code_review": [
                "Code follows project style guidelines",
                "Identified issues are valid and reproducible",
                "Suggestions improve code quality or security",
                "Review is complete and well-structured",
            ],
            "data_annotation": [
                "Etiquetado consistente a través de dataset",
                "Casos borderline bien documentados",
                "Consistencia con esquema de referencia",
                "Cantidad mínima de items etiquetados cumplida",
            ],
            "evaluation": [
                "Resultados reportados con métricas claras",
                "Comparación justa con baseline",
                "Hallazgos documentados y analizados",
                "Conclusiones respaldadas por datos",
            ],
            "general": [
                "Task completado según instrucciones",
                "Entregables cumplen requisitos especificados",
                "Documentación adecuada del proceso",
                "Cualquier problema debidamente reportado",
            ],
        }
        return quality_map.get(task_type, quality_map["general"])

    def _get_output_format(self, task_type: str) -> str:
        """Get expected output format for submission."""
        format_map = {
            "code_review": "URL fork/repo con review en formato Markdown",
            "data_annotation": "URL dataset con etiquetas en formato JSON/CSV",
            "evaluation": "URL reporte o logs de experimento",
            "general": "URL o contenido según instrucciones del task",
        }
        return format_map.get(task_type, format_map["general"])

    def _format_description(self, task_id: str) -> str:
        """Format description automatically for submission.

        Semi-autonomous: OWNEX genera una description optimizada
        basada en el task, pero el user puede editarla.
        """
        # In a real implementation, this would fetch task details
        # and format a description based on task type and requirements
        return f"Submission via OWNEX semi-autonomous workflow for task {task_id}"

    async def get_tasks(self, status: str = "open") -> ExecutionResult:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/tasks",
                    params={"status": status},
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_tasks", status, data={"tasks": data})
                return ExecutionResult(False, "get_tasks", status, error=f"HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                return ExecutionResult(False, "get_tasks", status, error=str(e))


async def claim(task_id: str | None = None) -> ExecutionResult:
    """Top-level claim function for scheduler handler.

    References: ``core.opportunity.executors.mindrift_executor:claim``
    """
    executor = MindriftExecutor()
    if task_id:
        return await executor.claim_task(task_id)
    # Find first available task and claim it
    tasks_result = await executor.get_tasks("open")
    if not tasks_result.success or not tasks_result.data:
        return ExecutionResult(False, "claim", task_id, error="No open tasks available")
    tasks = tasks_result.data.get("tasks", [])
    if not tasks:
        return ExecutionResult(False, "claim", task_id, error="No open tasks available")
    first_task_id = tasks[0].get("id") if isinstance(tasks[0], dict) and "id" in tasks[0] else str(tasks[0])
    return await executor.claim_task(first_task_id)
