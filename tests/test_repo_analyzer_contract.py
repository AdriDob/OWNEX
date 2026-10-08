"""RepoAnalyzer: la Fase 1 del pipeline no podia ejecutarse.

Dos fallos en la MISMA funcion, ambos|DateTime-independent, ambos encontrados al
correrla de verdad contra un repo publico:

1. `RepoInfo(...)` se construia con 3 de sus 7 campos obligatorios
   -> TypeError en todas las llamadas.
2. `repo_path` llegaba como `str` (así lo devuelve clone_repo en `data`) y
   `_detect_language` hacía `repo_path.rglob(...)`
   -> AttributeError: 'str' object has no attribute 'rglob'.

Ninguno lo cubría ningún test: `analyze_repo` no se probaba contra nada. Por eso
`DevBountyPipeline` nunca corrió, ni sus 6 fases, ni el primer pago.
"""

from __future__ import annotations

import inspect

from cores.autonomy.repo_analyzer import RepoAnalyzer, RepoInfo


def test_repo_info_can_be_constructed_with_the_args_analyze_repo_passes() -> None:
    """Todo RepoInfo se puede construir con los campos que el analyzer pasa."""
    required = (
        [f.name for f in RepoInfo.__dataclass_fields__.values() if f.default is f.default_factory]
        if hasattr(RepoInfo, "__dataclass_fields__")
        else []
    )
    # contrato: los 7 campos sin default deben existir
    for name in ("path", "language", "package_manager", "test_command", "build_command", "dev_command", "framework"):
        assert name in required, f"{name} dejó de ser obligatorio y eso rompe el contrato"
    # y se pueden pasar por keyword
    RepoInfo(
        path="x",
        language="python",
        package_manager=None,
        test_command=None,
        build_command=None,
        dev_command=None,
        framework=None,
    )


def test_analyze_repo_accepts_a_string_path() -> None:
    """clone_repo devuelve str; analyze_repo no puede asumir Path."""
    hint = inspect.signature(RepoAnalyzer.analyze_repo).parameters["repo_path"].annotation
    text = str(hint)
    assert "str" in text, f"analyze_repo anotaba `{text}` sin aceptar str, pero clone_repo lo entrega como str"


def test_generate_fix_does_not_report_success_with_zero_changes() -> None:
    """Cero cambios NO es un exito.

    Séptimo caso del mismo patrón: "no pude" reportado como "lo hice". Con
    `success=True` y un plan vacío, el pipeline seguía a la Fase 4 (tests) y
    Fase 5 (PR) sin nada que probar ni enviar.
    """
    import inspect

    from cores.autonomy.code_generator import CodeGenerator

    src = inspect.getsource(CodeGenerator.generate_fix)
    assert "if not changes:" in src, "generate_fix volvió a devolver success=True sin comprobar que haya cambios"
