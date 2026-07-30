"""Platform Guides — Detailed step-by-step assistance for account creation and work submission.

Each platform has:
- Account creation guide
- Work submission guide
- Exact UI navigation (tab/button/field)
- Direct links
- File format requirements
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Step:
    """A single step in a platform guide."""
    title: str
    description: str
    action: str  # "click", "type", "upload", "navigate", "copy"
    element: str  # CSS selector or UI description
    value: str | None = None
    url: str | None = None
    screenshot_hint: str | None = None


@dataclass
class PlatformGuide:
    """Complete guide for a platform."""
    platform: str
    name: str
    url: str
    account_creation: list[Step]
    work_submission: list[Step]
    file_formats: dict[str, str]  # key: file type, value: description
    tips: list[str]
    common_errors: list[dict[str, str]]


# ── Platform Guides Registry ──

PLATFORM_GUIDES: dict[str, PlatformGuide] = {
    "algora": PlatformGuide(
        platform="algora",
        name="Algora",
        url="https://algora.io",
        account_creation=[
            Step(
                title="Navegar a Algora",
                description="Ir a la página principal de Algora",
                action="navigate",
                element="https://algora.io",
                url="https://algora.io",
            ),
            Step(
                title="Click en Sign Up",
                description="Botón en la esquina superior derecha",
                action="click",
                element="button:contains('Sign Up')",
                screenshot_hint="Esquina superior derecha",
            ),
            Step(
                title="Ingresar email",
                description="Email para registro",
                action="type",
                element="input[type='email']",
                value="TU_EMAIL",
            ),
            Step(
                title="Crear contraseña",
                description="Mínimo 8 caracteres",
                action="type",
                element="input[type='password']",
                value="TU_CONTRASEÑA",
            ),
            Step(
                title="Click en Create Account",
                description="Botón de registro",
                action="click",
                element="button:contains('Create Account')",
            ),
            Step(
                title="Verificar email",
                description="Revisar inbox y click en enlace de verificación",
                action="copy",
                element="email_verification_link",
                value="Check your email",
            ),
        ],
        work_submission=[
            Step(
                title="Navegar a Bounties",
                description="Tab 'Bounties' en el menú superior",
                action="click",
                element="a:contains('Bounties')",
                screenshot_hint="Menú superior, tab Bounties",
            ),
            Step(
                title="Seleccionar bounty",
                description="Click en un bounty de interés",
                action="click",
                element=".bounty-card",
                screenshot_hint="Tarjeta del bounty",
            ),
            Step(
                title="Click en Submit Work",
                description="Botón para subir trabajo",
                action="click",
                element="button:contains('Submit Work')",
                screenshot_hint="Lado derecho del bounty",
            ),
            Step(
                title="Subir archivo",
                description="Seleccionar archivo ZIP o PDF",
                action="upload",
                element="input[type='file']",
                value="work.zip",
            ),
            Step(
                title="Agregar descripción",
                description="Descripción breve del trabajo",
                action="type",
                element="textarea[name='description']",
                value="Descripción...",
            ),
            Step(
                title="Click en Submit",
                description="Botón para enviar",
                action="click",
                element="button:contains('Submit')",
            ),
        ],
        file_formats={
            "zip": "Archivo ZIP con código completo",
            "pdf": "Informe en PDF",
            "md": "README en Markdown",
        },
        tips=[
            "Los bounties de Algora suelen ser issues de GitHub",
            "El archivo ZIP debe incluir instrucciones de instalación",
            "Verifica que el bounty aún esté abierto antes de enviar",
        ],
        common_errors=[
            {"error": "Archivo muy grande", "solution": "Comprimir el ZIP o usar git repo"},
            {"error": "Descripción vacía", "solution": "Agrega una descripción clara"},
        ],
    ),
    "freelancer": PlatformGuide(
        platform="freelancer",
        name="Freelancer",
        url="https://www.freelancer.com",
        account_creation=[
            Step(
                title="Navegar a Freelancer",
                description="Ir a la página principal",
                action="navigate",
                element="https://www.freelancer.com",
                url="https://www.freelancer.com",
            ),
            Step(
                title="Click en Sign Up",
                description="Botón en esquina superior derecha",
                action="click",
                element="button:contains('Sign Up')",
                screenshot_hint="Esquina superior derecha",
            ),
            Step(
                title="Seleccionar tipo de cuenta",
                description="Click en 'I want to work'",
                action="click",
                element="button:contains('I want to work')",
            ),
            Step(
                title="Ingresar email",
                description="Email para registro",
                action="type",
                element="input[type='email']",
                value="TU_EMAIL",
            ),
            Step(
                title="Ingresar contraseña",
                description="Mínimo 8 caracteres",
                action="type",
                element="input[type='password']",
                value="TU_CONTRASEÑA",
            ),
            Step(
                title="Click en Join",
                description="Botón de registro",
                action="click",
                element="button:contains('Join')",
            ),
        ],
        work_submission=[
            Step(
                title="Navegar a Projects",
                description="Tab 'Projects' en menú superior",
                action="click",
                element="a:contains('Projects')",
                screenshot_hint="Menú superior",
            ),
            Step(
                title="Buscar proyecto",
                description="Usar barra de búsqueda",
                action="type",
                element="input[type='search']",
                value="palabras clave",
            ),
            Step(
                title="Seleccionar proyecto",
                description="Click en proyecto de interés",
                action="click",
                element=".project-card",
            ),
            Step(
                title="Click en Bid on Project",
                description="Botón para ofertar",
                action="click",
                element="button:contains('Bid on Project')",
                screenshot_hint="Lado derecho del proyecto",
            ),
            Step(
                title="Ingresar monto",
                description="Oferta en USD",
                action="type",
                element="input[name='bid_amount']",
                value="100",
            ),
            Step(
                title="Agregar propuesta",
                description="Descripción de tu experiencia",
                action="type",
                element="textarea[name='proposal']",
                value="Propuesta...",
            ),
            Step(
                title="Click en Place Bid",
                description="Botón para enviar oferta",
                action="click",
                element="button:contains('Place Bid')",
            ),
        ],
        file_formats={
            "pdf": "Portafolio en PDF",
            "docx": "Documento Word",
            "zip": "Muestras de trabajo",
        },
        tips=[
            "Freelancer cobra comisión del 10%",
            "Completa tu perfil antes de ofertar",
            "Verifica el tiempo estimado del proyecto",
        ],
        common_errors=[
            {"error": "Oferta fuera de rango", "solution": "Revisa el presupuesto del cliente"},
            {"error": "Perfil incompleto", "solution": "Completa skills y portafolio"},
        ],
    ),
    "github": PlatformGuide(
        platform="github",
        name="GitHub",
        url="https://github.com",
        account_creation=[
            Step(
                title="Navegar a GitHub",
                description="Ir a github.com",
                action="navigate",
                element="https://github.com",
                url="https://github.com",
            ),
            Step(
                title="Click en Sign up",
                description="Botón en esquina superior derecha",
                action="click",
                element="a:contains('Sign up')",
                screenshot_hint="Esquina superior derecha",
            ),
            Step(
                title="Ingresar email",
                description="Email para registro",
                action="type",
                element="input[type='email']",
                value="TU_EMAIL",
            ),
            Step(
                title="Ingresar contraseña",
                description="Mínimo 15 caracteres o 8 con números",
                action="type",
                element="input[type='password']",
                value="TU_CONTRASEÑA",
            ),
            Step(
                title="Continuar con username",
                description="Nombre de usuario único",
                action="type",
                element="input[name='login']",
                value="TU_USERNAME",
            ),
            Step(
                title="Click en Continue",
                description="Botón para continuar",
                action="click",
                element="button:contains('Continue')",
            ),
        ],
        work_submission=[
            Step(
                title="Navegar al repo",
                description="Ir al repositorio del proyecto",
                action="navigate",
                element="REPO_URL",
                url="https://github.com/ORG/REPO",
            ),
            Step(
                title="Navegar a Issues",
                description="Tab 'Issues' en el repo",
                action="click",
                element="a:contains('Issues')",
                screenshot_hint="Tab Issues en el repo",
            ),
            Step(
                title="Seleccionar issue",
                description="Click en issue abierto",
                action="click",
                element=".issue-item",
            ),
            Step(
                title="Fork del repo",
                description="Click en Fork en esquina superior derecha",
                action="click",
                element="button:contains('Fork')",
                screenshot_hint="Esquina superior derecha del repo",
            ),
            Step(
                title="Clonar repo forkeado",
                description="Usar git clone",
                action="copy",
                element="git_clone_url",
                value="git clone URL",
            ),
            Step(
                title="Crear branch",
                description="git checkout -b fix/issue-123",
                action="copy",
                element="terminal",
                value="git checkout -b fix/issue-123",
            ),
            Step(
                title="Hacer cambios",
                description="Editar archivos según el issue",
                action="type",
                element="editor",
                value="cambios...",
            ),
            Step(
                title="Commit cambios",
                description="git commit -am 'Fix issue #123'",
                action="copy",
                element="terminal",
                value="git commit -am 'Fix issue #123'",
            ),
            Step(
                title="Push branch",
                description="git push origin fix/issue-123",
                action="copy",
                element="terminal",
                value="git push origin fix/issue-123",
            ),
            Step(
                title="Crear Pull Request",
                description="Click en 'Compare & pull request'",
                action="click",
                element="a:contains('Compare & pull request')",
                screenshot_hint="Banner verde en GitHub",
            ),
            Step(
                title="Completar PR",
                description="Agregar descripción y click en 'Create pull request'",
                action="click",
                element="button:contains('Create pull request')",
            ),
        ],
        file_formats={
            "zip": "No aplicable (usa git)",
            "patch": "Patch file para fixes pequeños",
            "md": "Documentación en Markdown",
        },
        tips=[
            "Usa git convencional commits",
            "Verifica CI/CD antes de hacer PR",
            "Lee el CONTRIBUTING.md del repo",
        ],
        common_errors=[
            {"error": "PR no pasa tests", "solution": "Corrige los errores de CI/CD"},
            {"error": "Conflicto de merge", "solution": "Haz rebase con branch main"},
        ],
    ),
    "outlier": PlatformGuide(
        platform="outlier",
        name="Outlier",
        url="https://platform.outlier.ai",
        account_creation=[
            Step(
                title="Navegar a Outlier",
                description="Ir a platform.outlier.ai",
                action="navigate",
                element="https://platform.outlier.ai",
                url="https://platform.outlier.ai",
            ),
            Step(
                title="Click en Get Started",
                description="Botón en página principal",
                action="click",
                element="button:contains('Get Started')",
                screenshot_hint="Centro de la página",
            ),
            Step(
                title="Ingresar email",
                description="Email para registro",
                action="type",
                element="input[type='email']",
                value="TU_EMAIL",
            ),
            Step(
                title="Crear contraseña",
                description="Mínimo 8 caracteres",
                action="type",
                element="input[type='password']",
                value="TU_CONTRASEÑA",
            ),
            Step(
                title="Click en Sign Up",
                description="Botón de registro",
                action="click",
                element="button:contains('Sign Up')",
            ),
        ],
        work_submission=[
            Step(
                title="Navegar a Jobs",
                description="Tab 'Jobs' en menú lateral",
                action="click",
                element="a:contains('Jobs')",
                screenshot_hint="Menú lateral izquierdo",
            ),
            Step(
                title="Seleccionar job",
                description="Click en job disponible",
                action="click",
                element=".job-card",
            ),
            Step(
                title="Click en Start Job",
                description="Botón para comenzar trabajo",
                action="click",
                element="button:contains('Start Job')",
                screenshot_hint="Lado derecho del job",
            ),
            Step(
                title="Seguir instrucciones",
                description="Leer instrucciones específicas del job",
                action="copy",
                element="instructions",
                value="Leer guía...",
            ),
            Step(
                title="Completar tareas",
                description="Seguir los pasos del job",
                action="type",
                element="task_form",
                value="respuestas...",
            ),
            Step(
                title="Click en Submit",
                description="Botón para enviar respuestas",
                action="click",
                element="button:contains('Submit')",
            ),
        ],
        file_formats={
            "csv": "Archivos CSV para tareas de data",
            "json": "JSON para respuestas estructuradas",
            "txt": "Texto plano para respuestas simples",
        },
        tips=[
            "Outlier paga por tarea completada",
            "Lee las instrucciones cuidadosamente",
            "Verifica el pago antes de aceptar el job",
        ],
        common_errors=[
            {"error": "Formato incorrecto", "solution": "Verifica el formato requerido (CSV/JSON)"},
            {"error": "Job expirado", "solution": "Busca jobs activos"},
        ],
    ),
}


def get_platform_guide(platform: str) -> PlatformGuide | None:
    """Get guide for a specific platform."""
    return PLATFORM_GUIDES.get(platform.lower())


def list_all_platforms() -> list[str]:
    """List all platforms with guides."""
    return sorted(PLATFORM_GUIDES.keys())


def format_guide_for_user(guide: PlatformGuide, guide_type: str = "account") -> str:
    """Format a guide for user display (markdown or plain text)."""
    steps = guide.account_creation if guide_type == "account" else guide.work_submission

    lines = [
        f"# Guía para {guide.name} ({guide_type})",
        f"URL: {guide.url}",
        "",
        "## Pasos:",
        "",
    ]

    for i, step in enumerate(steps, 1):
        lines.append(f"### {i}. {step.title}")
        lines.append(f"{step.description}")
        lines.append(f"- Acción: {step.action}")
        lines.append(f"- Elemento: {step.element}")
        if step.value:
            lines.append(f"- Valor: {step.value}")
        if step.url:
            lines.append(f"- URL: {step.url}")
        if step.screenshot_hint:
            lines.append(f"- Hint: {step.screenshot_hint}")
        lines.append("")

    lines.append("## Formatos de archivo aceptados:")
    for fmt, desc in guide.file_formats.items():
        lines.append(f"- **.{fmt}**: {desc}")

    lines.append("")
    lines.append("## Tips:")
    for tip in guide.tips:
        lines.append(f"- {tip}")

    lines.append("")
    lines.append("## Errores comunes:")
    for error in guide.common_errors:
        lines.append(f"- **{error['error']}**: {error['solution']}")

    return "\n".join(lines)
