"""Scaffold generator: task → ordered, verifiable steps.

Was a bare stub (`class ScaffoldGenerator: pass`) while
`SelfImprovementEngine.run_once()` calls `.generate(task)` — so every
self-improvement run raised AttributeError.

The steps mirror `SandboxHarness._verification_command` (harness.py:118)
*exactly*: a scaffold that describes a different check than the one that will
actually run would be a guide that lies about its own success criterion.
"""

from __future__ import annotations

from typing import Any

from cores.self_improvement.models import Scaffold, ScaffoldStep

#: category -> (instruction, verification description, check_type).
#: Ordered to match the harness so the plan and the run agree.
_VERIFICATION_BY_CATEGORY: dict[str, tuple[str, str, str]] = {
    "code": ("Escribí la solución en solution.py", "Corre un verificador que importa la solución", "file"),
    "test": ("Escribí tests en test_solution.py", "Corre pytest sobre el workdir", "command"),
    "debug": ("Corregí el bug en solution.py", "Ejecuta la solución corregida", "command"),
    "documentation": ("Escribí la documentación", "Revisión manual del contenido", "assertion"),
    "analysis": ("Analizá la entrada y emití el veredicto", "Corre un verificador de análisis", "file"),
    "generation": ("Generá la salida estructurada", "Corre un verificador de generación", "file"),
    "security": ("Encontrá la vulnerabilidad en el sandbox", "Corre un verificador de seguridad", "file"),
    "reasoning": ("Respondé el razonamiento", "Corre un verificador de razonamiento", "file"),
}


class ScaffoldGenerator:
    """Deterministic scaffold builder — no LLM, no invented success criteria."""

    def generate(self, task: Any) -> Scaffold:
        category = getattr(getattr(task, "category", None), "value", "") or ""
        prompt = str(getattr(task, "prompt", "") or getattr(task, "description", "") or "")
        instruction, verification, check_type = _VERIFICATION_BY_CATEGORY.get(
            category, ("Resolvé la tarea", "Verificación no específica de categoría", "assertion")
        )
        steps = [
            ScaffoldStep(
                index=0,
                instruction=instruction,
                verification=verification,
                check_type=check_type,
            )
        ]
        if prompt:
            steps.append(
                ScaffoldStep(
                    index=1,
                    instruction="Releé el enunciado y asegurate de cubrir cada requisito",
                    verification="Contraste con el enunciado de la tarea",
                    check_type="assertion",
                )
            )
        return Scaffold(task_id=str(getattr(task, "id", "") or ""), steps=steps, hints=[])
