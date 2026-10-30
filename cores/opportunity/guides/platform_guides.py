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
    "workana": PlatformGuide(
        platform="workana",
        name="Workana",
        url="https://www.workana.com",
        account_creation=[
            Step(
                title="Navegar a Workana",
                description="Ir a workana.com > 'Regístrate como Freelancer'",
                action="navigate",
                element="https://www.workana.com",
                url="https://www.workana.com",
            ),
            Step(
                title="Click en Regístrate",
                description="Botón 'Regístrate como Freelancer' en esquina superior derecha",
                action="click",
                element="button:contains('Regístrate')",
                screenshot_hint="Esquina superior derecha",
            ),
            Step(
                title="Seleccionar Freelancer",
                description="Click en 'Quiero trabajar como Freelancer'",
                action="click",
                element="button:contains('Freelancer')",
            ),
            Step(
                title="Ingresar email",
                description="Email para registro (usa tu email real)",
                action="type",
                element="input[type='email']",
                value="TU_EMAIL",
            ),
            Step(
                title="Crear contraseña",
                description="Mínimo 8 caracteres, usa gestor de contraseñas",
                action="type",
                element="input[type='password']",
                value="TU_CONTRASEÑA_SEGURA",
            ),
            Step(
                title="Completar perfil básico",
                description="Nombre, apellido, país (Argentina), habilidades principales",
                action="type",
                element="form[name='profile']",
                value="Tus datos...",
            ),
            Step(
                title="Verificar email",
                description="Click enlace en email de Workana",
                action="copy",
                element="email_verification_link",
                value="Check email for Workana verification",
            ),
            Step(
                title="Completar perfil profesional",
                description="Profile > Skills, Portfolio, Hourly rate, Disponibilidad. Agregar links a GitHub/LinkedIn",
                action="navigate",
                element="https://www.workana.com/freelancer/profile/edit",
                url="https://www.workana.com/freelancer/profile/edit",
            ),
            Step(
                title="Configurar pagos",
                description="Settings > Pagos. PayPal, Payoneer, Transferencia bancaria (Argentina: Payoneer/Banco local)",
                action="navigate",
                element="https://www.workana.com/settings/payments",
                url="https://www.workana.com/settings/payments",
            ),
        ],
        work_submission=[
            Step(
                title="Navegar a Proyectos",
                description="Dashboard > 'Proyectos' o workana.com/jobs",
                action="click",
                element="a:contains('Proyectos')",
                screenshot_hint="Menú lateral o superior",
            ),
            Step(
                title="Filtrar proyectos",
                description="Filtros: Categoría (Programación), Presupuesto, Tipo (Por hora/Fijo), Idioma (Español/Inglés)",
                action="click",
                element="button:contains('Filtros')",
            ),
            Step(
                title="Leer proyecto",
                description="Click proyecto > leer 'Descripción', 'Requisitos', 'Presupuesto', 'Plazo'",
                action="click",
                element=".project-card",
            ),
            Step(
                title="Enviar propuesta",
                description="Click 'Enviar propuesta' > Monto, Tiempo estimado, Carta de presentación, Preguntas al cliente",
                action="click",
                element="button:contains('Enviar propuesta')",
            ),
            Step(
                title="Completar propuesta",
                description="Monto (ARS/USD), Días de entrega, Cover letter personalizada, Preguntas de aclaración",
                action="type",
                element="form[name='proposal']",
                value="Propuesta personalizada...",
            ),
            Step(
                title="Enviar",
                description="Click 'Enviar propuesta'. Cliente revisa en 24-72h. Responder rápido a preguntas",
                action="click",
                element="button:contains('Enviar')",
            ),
            Step(
                title="Iniciar trabajo",
                description="Cliente acepta > Workana crea contrato > Iniciar > Entregar hitos > Cobrar",
                action="click",
                element="button:contains('Iniciar')",
            ),
        ],
        file_formats={
            "pdf": "Portafolio en PDF",
            "docx": "Documento Word",
            "zip": "Muestras de trabajo / código fuente + docs",
        },
        tips=[
            "Workana = mercado LATAM. Menos competencia global que Upwork/Freelancer",
            "Perfil completo + portfolio = 3x más probabilidades de ganar proyectos",
            "Pagos: Payoneer (USD) o Transferencia local (ARS). Configurar ANTES del primer proyecto",
            "Comisión Workana: 10-20% según plan. Incluir en tu precio",
            "Responder en <1h = mejor ranking. Notificaciones push/email activadas",
            "First 5 proyectos CRÍTICOS: over-deliver, 5 estrellas, response rápido = momentum",
        ],
        common_errors=[
            {"error": "Propuesta genérica", "solution": "Personaliza: menciona detalles del proyecto del cliente"},
            {"error": "Precio muy bajo", "solution": "Mínimo $15-25/hr para dev Argentina. No compitas por precio"},
            {"error": "Perfil incompleto", "solution": "Skills, portfolio, certificaciones, idiomas = confianza"},
            {"error": "Sin portfolio", "solution": "Crear 2-3 proyectos demo en GitHub y subir screenshots a Workana"},
            {"error": "Pago no configurado", "solution": "Settings > Pagos > Payoneer/Banco ANTES del primer proyecto"},
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
    "hackerone": PlatformGuide(
        platform="hackerone",
        name="HackerOne",
        url="https://hackerone.com",
        account_creation=[
            Step(
                title="Navegar a HackerOne",
                description="Ir a la página principal de HackerOne",
                action="navigate",
                element="https://hackerone.com",
                url="https://hackerone.com",
            ),
            Step(
                title="Click en Sign Up",
                description="Botón en la esquina superior derecha",
                action="click",
                element="a:contains('Sign Up')",
                screenshot_hint="Esquina superior derecha",
            ),
            Step(
                title="Seleccionar tipo de cuenta",
                description="Click en 'I want to hack' (quiero hackear/reportar bugs)",
                action="click",
                element="button:contains('I want to hack')",
            ),
            Step(
                title="Ingresar email",
                description="Email para registro (usa tu email real)",
                action="type",
                element="input[type='email']",
                value="TU_EMAIL",
            ),
            Step(
                title="Crear contraseña",
                description="Mínimo 12 caracteres, usa gestor de contraseñas",
                action="type",
                element="input[type='password']",
                value="TU_CONTRASEÑA_SEGURA",
            ),
            Step(
                title="Ingresar username",
                description="Nombre de usuario público único",
                action="type",
                element="input[name='username']",
                value="TU_USERNAME",
            ),
            Step(
                title="Click en Create Account",
                description="Botón de registro final",
                action="click",
                element="button:contains('Create Account')",
            ),
            Step(
                title="Verificar email",
                description="Revisar inbox y click en enlace de verificación de HackerOne",
                action="copy",
                element="email_verification_link",
                value="Check your email for HackerOne verification",
            ),
            Step(
                title="Completar perfil",
                description="Agregar bio, skills, foto. Importante para credibilidad",
                action="navigate",
                element="https://hackerone.com/settings/profile",
                url="https://hackerone.com/settings/profile",
            ),
            Step(
                title="Configurar 2FA",
                description="Settings > Security > Two-Factor Authentication. Obligatorio para pagos",
                action="navigate",
                element="https://hackerone.com/settings/security",
                url="https://hackerone.com/settings/security",
            ),
        ],
        work_submission=[
            Step(
                title="Navegar a Programs",
                description="Tab 'Programs' en menú superior o hackerone.com/programs",
                action="click",
                element="a:contains('Programs')",
                screenshot_hint="Menú superior",
            ),
            Step(
                title="Filtrar programas",
                description="Usar filtros: 'Offers bounties', 'Web', 'API', tu skill level",
                action="type",
                element="input[placeholder*='Search']",
                value="web bounty",
            ),
            Step(
                title="Leer scope y reglas",
                description="Click en programa > 'View Program' > leer 'Scope' y 'Rules' cuidadosamente",
                action="click",
                element="button:contains('View Program')",
                screenshot_hint="Botón verde en la tarjeta del programa",
            ),
            Step(
                title="Reconocimiento inicial",
                description="Usar herramientas: subfinder, httpx, katana. Guardar outputs en carpeta del target",
                action="copy",
                element="terminal",
                value="subfinder -d target.com -o recon/subdomains.txt && httpx -l recon/subdomains.txt -o recon/live.txt",
            ),
            Step(
                title="Buscar vulnerabilidades",
                description="Testing manual + automatizado. Documentar TODO con capturas, requests/responses, PoC",
                action="type",
                element="editor",
                value="Documentar hallazgos...",
            ),
            Step(
                title="Crear reporte",
                description="Report > Submit Report. Título claro, severity, PoC reproducible, impacto real",
                action="click",
                element="a:contains('Submit Report')",
                screenshot_hint="Botón 'Submit Report' en página del programa",
            ),
            Step(
                title="Completar formulario",
                description="Title, Vulnerability Type, Severity, Description, Steps to Reproduce, Impact, PoC, Remediation",
                action="type",
                element="form[name='report']",
                value="Detalles del reporte...",
            ),
            Step(
                title="Adjuntar evidencia",
                description="Subir: screenshots, video (Loom), curl commands, Burp request/response, PoC code",
                action="upload",
                element="input[type='file']",
                value="evidence.zip",
            ),
            Step(
                title="Submit report",
                description="Click 'Submit Report'. El triage revisará en 24-72h típicamente",
                action="click",
                element="button:contains('Submit Report')",
            ),
        ],
        file_formats={
            "zip": "Evidencia completa (screenshots + requests + PoC)",
            "txt": "Comandos curl / PoC code",
            "mp4": "Video walkthrough (Loom)",
            "md": "Reporte en Markdown",
        },
        tips=[
            "Siempre leer el SCOPE antes de testear - fuera de scope = ban risk",
            "Usa Hacker101 (hacker101.com) para práctica GRATIS antes de tocar programas reales",
            "Severity: usa CVSS 3.1 calculator. No inflar - los triagers lo detectan",
            "PoC debe ser REPRODUCIBLE paso a paso. Sin PoC = no pagan",
            "Respuesta a triage: responde en <24h. Profesional, técnico, sin ego",
            "Configura 2FA ANTES de tu primer reporte válido - sino no pagan",
            "Empieza con programas 'VDP' (no pagan) para ganar reputación y aprender",
        ],
        common_errors=[
            {
                "error": "Testing outside scope",
                "solution": "Leer scope línea por línea. Solo testear lo explícitamente permitido",
            },
            {
                "error": "PoC no reproducible",
                "solution": "Documentar pasos exactos: 1. Ir a URL 2. Click X 3. Observar Y",
            },
            {
                "error": "Severity inflado",
                "solution": "Usar CVSS calculator oficial. Critical solo si RCE/data breach real",
            },
            {"error": "Sin 2FA al pagar", "solution": "Habilitar 2FA en Settings > Security ANTES del primer payout"},
            {
                "error": "Reporte incompleto",
                "solution": "Usar template: Title, Type, Severity, Description, Steps, Impact, PoC, Remediation",
            },
        ],
    ),
    "bugcrowd": PlatformGuide(
        platform="bugcrowd",
        name="Bugcrowd",
        url="https://bugcrowd.com",
        account_creation=[
            Step(
                title="Navegar a Bugcrowd",
                description="Ir a bugcrowd.com > 'For Researchers' > 'Sign Up'",
                action="navigate",
                element="https://bugcrowd.com",
                url="https://bugcrowd.com",
            ),
            Step(
                title="Click en Sign Up",
                description="Botón 'Sign Up' en esquina superior derecha",
                action="click",
                element="a:contains('Sign Up')",
                screenshot_hint="Esquina superior derecha",
            ),
            Step(
                title="Seleccionar Researcher",
                description="Click en 'I'm a Researcher' (no Company)",
                action="click",
                element="button:contains('Researcher')",
            ),
            Step(
                title="Ingresar datos",
                description="Email real, username único, contraseña segura (12+ chars)",
                action="type",
                element="form[name='registration']",
                value="TU_EMAIL, TU_USERNAME, TU_CONTRASEÑA",
            ),
            Step(
                title="Verificar email",
                description="Click enlace en email de Bugcrowd",
                action="copy",
                element="email_verification_link",
                value="Check email for Bugcrowd verification",
            ),
            Step(
                title="Completar perfil",
                description="Profile > Skills, Bio, Location. Agregar links a GitHub/LinkedIn",
                action="navigate",
                element="https://bugcrowd.com/profile/edit",
                url="https://bugcrowd.com/profile/edit",
            ),
            Step(
                title="Configurar 2FA",
                description="Account Settings > Security > Enable 2FA. Requerido para pagos",
                action="navigate",
                element="https://bugcrowd.com/settings/security",
                url="https://bugcrowd.com/settings/security",
            ),
            Step(
                title="Configurar pagos",
                description="Account Settings > Payouts. PayPal, Payoneer, Bank Transfer. Argentina: Payoneer recomendado",
                action="navigate",
                element="https://bugcrowd.com/settings/payouts",
                url="https://bugcrowd.com/settings/payouts",
            ),
        ],
        work_submission=[
            Step(
                title="Navegar a Programs",
                description="Dashboard > 'Programs' o bugcrowd.com/programs",
                action="click",
                element="a:contains('Programs')",
                screenshot_hint="Menú lateral o superior",
            ),
            Step(
                title="Filtrar: Payout + Web",
                description="Filters: 'Offers Bounties'=Yes, 'Target Type'=Website/API, 'Payout'=tu rango",
                action="click",
                element="button:contains('Filters')",
            ),
            Step(
                title="Leer Program Brief",
                description="Click programa > leer 'Scope', 'Rewards', 'Safe Harbor', 'Exclusions'",
                action="click",
                element=".program-card",
            ),
            Step(
                title="Recon + Testing",
                description="Mismo flujo que HackerOne. Bugcrowd usa 'VRT' (Vulnerability Rating Taxonomy)",
                action="copy",
                element="terminal",
                value="subfinder -d target.com -o recon/subdomains.txt",
            ),
            Step(
                title="Submit Vulnerability",
                description="Program > 'Submit Vulnerability'. Seleccionar VRT category, severity",
                action="click",
                element="button:contains('Submit Vulnerability')",
            ),
            Step(
                title="Completar Submission Form",
                description="Title, VRT Category, Severity, Description, Steps, Impact, PoC, Remediation, Attachments",
                action="type",
                element="form[name='submission']",
                value="Detalles...",
            ),
            Step(
                title="Adjuntar PoC",
                description="Screenshots, video, Burp export, curl, code. ZIP recomendado",
                action="upload",
                element="input[type='file']",
                value="poc.zip",
            ),
            Step(
                title="Submit",
                description="Click 'Submit'. Triage típico: 48-96h. Responder rápido a preguntas",
                action="click",
                element="button:contains('Submit')",
            ),
        ],
        file_formats={
            "zip": "Evidencia completa",
            "txt": "PoC / curl commands",
            "mp4": "Video (opcional)",
            "md": "Reporte Markdown",
        },
        tips=[
            "Bugcrowd usa VRT (Vulnerability Rating Taxonomy) - aprender categorías",
            "University: bugcrowd.com/university - cursos GRATIS de metodología",
            "Payouts: Argentina usa Payoneer. Configurar ANTES del primer payout válido",
            "Responder a triage en <24h. Pedir aclaración si VRT category no clara",
            "Empieza con VDP programs para ganar reputation score",
        ],
        common_errors=[
            {
                "error": "VRT category incorrecta",
                "solution": "Leer taxonomy en docs.bugcrowd.com. Preguntar a triage si duda",
            },
            {
                "error": "Testing assets no en scope",
                "solution": "Solo testear URLs/dominios listados en 'Scope'. Wildcard = subdomains incluidos",
            },
            {
                "error": "Payout no configurado",
                "solution": "Settings > Payouts > agregar Payoneer/banco ANTES del primer accepted",
            },
            {
                "error": "Severity no coincide con VRT",
                "solution": "VRT define severity por categoría. No inventar - seguir la guía",
            },
        ],
    ),
    "intigriti": PlatformGuide(
        platform="intigriti",
        name="Intigriti",
        url="https://intigriti.com",
        account_creation=[
            Step(
                title="Navegar a Intigriti",
                description="Ir a intigriti.com > 'For Researchers' > 'Sign Up'",
                action="navigate",
                element="https://intigriti.com",
                url="https://intigriti.com",
            ),
            Step(
                title="Registrarse",
                description="Email, username, contraseña. Verificar email",
                action="type",
                element="form[name='registration']",
                value="TU_EMAIL, TU_USERNAME, TU_CONTRASEÑA",
            ),
            Step(
                title="Perfil + 2FA",
                description="Profile > completar bio, skills. Security > Enable 2FA (TOTP)",
                action="navigate",
                element="https://app.intigriti.com/profile",
                url="https://app.intigriti.com/profile",
            ),
            Step(
                title="Configurar pagos",
                description="Settings > Payout. Bank transfer (EUR), Payoneer. IBAN requerido para EU",
                action="navigate",
                element="https://app.intigriti.com/settings/payout",
                url="https://app.intigriti.com/settings/payout",
            ),
        ],
        work_submission=[
            Step(
                title="Navegar a Programs",
                description="Dashboard > Programs. Filtrar: 'Bug Bounty', 'Web', 'Hybrid'",
                action="click",
                element="a:contains('Programs')",
            ),
            Step(
                title="Leer Program Details",
                description="Click programa > 'Details' > Scope, Rewards, Rules, Safe Harbor",
                action="click",
                element=".program-card",
            ),
            Step(
                title="Testing + Documentar",
                description="Intigriti valora PoC técnico detallado. Burp Suite exports bienvenidos",
                action="copy",
                element="terminal",
                value="Documentar hallazgo...",
            ),
            Step(
                title="Create Submission",
                description="Program > 'New Submission'. Title, Category, Severity, Description, Steps, Impact, PoC",
                action="click",
                element="button:contains('New Submission')",
            ),
            Step(
                title="Adjuntar evidencia",
                description="Screenshots, video, HTTP requests, PoC code. Intigriti prefiere technical depth",
                action="upload",
                element="input[type='file']",
                value="evidence.zip",
            ),
            Step(
                title="Submit",
                description="Submit. Triage rápido (24-48h). Responder técnico y preciso",
                action="click",
                element="button:contains('Submit')",
            ),
        ],
        file_formats={
            "zip": "Evidencia técnica completa",
            "txt": "Requests/PoC",
            "mp4": "Video walkthrough",
            "har": "HAR file de Burp",
        },
        tips=[
            "Intigriti = programas calidad > cantidad. Menos programas, mejores rewards",
            "Challenge mensual (challenge.intigriti.io) = práctica real + writeups",
            "Payouts en EUR. Configurar IBAN/Payoneer ANTES del primer accepted",
            "Responder triage: técnico, conciso, sin rodeos",
        ],
        common_errors=[
            {
                "error": "Scope mal interpretado",
                "solution": "Intigriti usa 'In Scope' / 'Out of Scope' explícito. Leer literal",
            },
            {
                "error": "Payout EUR sin IBAN",
                "solution": "Configurar IBAN/Payoneer en Settings ANTES del primer accepted",
            },
        ],
    ),
    "yeswehack": PlatformGuide(
        platform="yeswehack",
        name="YesWeHack",
        url="https://yeswehack.com",
        account_creation=[
            Step(
                title="Navegar a YesWeHack",
                description="Ir a yeswehack.com > 'Hunters' > 'Sign Up'",
                action="navigate",
                element="https://yeswehack.com",
                url="https://yeswehack.com",
            ),
            Step(
                title="Registrarse",
                description="Email, password, username. Verificar email",
                action="type",
                element="form[name='registration']",
                value="TU_EMAIL, TU_CONTRASEÑA, TU_USERNAME",
            ),
            Step(
                title="Perfil + 2FA",
                description="Profile completar. Security > 2FA obligatorio para pagos",
                action="navigate",
                element="https://app.yeswehack.com/profile",
                url="https://app.yeswehack.com/profile",
            ),
            Step(
                title="Configurar pagos",
                description="Settings > Payment. PayPal, Bank Transfer. Argentina: PayPal o Payoneer",
                action="navigate",
                element="https://app.yeswehack.com/settings/payment",
                url="https://app.yeswehack.com/settings/payment",
            ),
        ],
        work_submission=[
            Step(
                title="Navegar a Programs",
                description="Dashboard > Programs. Filtrar: 'Bug Bounty', 'Web', 'API'",
                action="click",
                element="a:contains('Programs')",
            ),
            Step(
                title="Leer Program Rules",
                description="Click programa > 'Rules' > Scope, Rewards, Exclusions, Legal",
                action="click",
                element=".program-card",
            ),
            Step(
                title="Testing + Report",
                description="YesWeHack valora reportes técnicos claros. Formato: Title, Description, Steps, Impact, PoC",
                action="type",
                element="editor",
                value="Reporte...",
            ),
            Step(
                title="New Report",
                description="Program > 'Report a Vulnerability'. Completar formulario estructurado",
                action="click",
                element="button:contains('Report')",
            ),
            Step(
                title="Submit + Follow up",
                description="Submit. Triage 48-72h. Comunicación por platform messaging",
                action="click",
                element="button:contains('Submit')",
            ),
        ],
        file_formats={
            "zip": "Evidencia completa",
            "txt": "PoC / requests",
            "mp4": "Video opcional",
        },
        tips=[
            "YesWeHack = programas europeos + algunos globales. Buena cobertura GDPR",
            "Learning Center: yeswehack.com/learn - recursos gratuitos",
            "PayPal configurado ANTES del primer payout",
            "Messaging interno para comunicarse con triage - responder rápido",
        ],
        common_errors=[
            {"error": "PayPal no verificado", "solution": "Verificar cuenta PayPal ANTES de configurar en YesWeHack"},
        ],
    ),
    "fiverr": PlatformGuide(
        platform="fiverr",
        name="Fiverr",
        url="https://www.fiverr.com",
        account_creation=[
            Step(
                title="Navegar a Fiverr",
                description="Ir a fiverr.com > 'Become a Seller'",
                action="navigate",
                element="https://www.fiverr.com/start_selling",
                url="https://www.fiverr.com/start_selling",
            ),
            Step(
                title="Registrarse",
                description="Email, username, password. O Google/GitHub/Facebook login",
                action="type",
                element="form[name='registration']",
                value="TU_EMAIL, TU_USERNAME, TU_CONTRASEÑA",
            ),
            Step(
                title="Verificar email + teléfono",
                description="Fiverr requiere verificación de teléfono (SMS) para sellers",
                action="copy",
                element="phone_verification",
                value="Ingresar código SMS",
            ),
            Step(
                title="Completar perfil SELLER",
                description="Profile > Professional info: Occupation, Skills, Education, Certifications, Languages",
                action="navigate",
                element="https://www.fiverr.com/profile/edit",
                url="https://www.fiverr.com/profile/edit",
            ),
            Step(
                title="Configurar pagos",
                description="Settings > Billing > Payout method. Argentina: Payoneer (recomendado) o Direct Deposit (USD)",
                action="navigate",
                element="https://www.fiverr.com/settings/billing",
                url="https://www.fiverr.com/settings/billing",
            ),
            Step(
                title="Verificación de identidad",
                description="Fiverr puede pedir ID + selfie para verificación de seller. Tener DNI/pasaporte listo",
                action="upload",
                element="identity_verification",
                value="DNI + selfie",
            ),
        ],
        work_submission=[
            Step(
                title="Crear PRIMER GIG",
                description="Dashboard > 'Create a New Gig'. UNA sola servicio, UN problema específico",
                action="click",
                element="a:contains('Create a New Gig')",
                screenshot_hint="Botón verde 'Create a New Gig' en dashboard",
            ),
            Step(
                title="Título del Gig",
                description="Formato: 'I will [acción específica] for [resultado concreto]'. Ej: 'I will build a Python automation script for your repetitive tasks'",
                action="type",
                element="input[name='title']",
                value="I will build a Python automation script for your repetitive tasks",
            ),
            Step(
                title="Categoría + Tags",
                description="Category: Programming & Tech > Automation. Tags: python, automation, script, bot, workflow",
                action="click",
                element="select[name='category']",
            ),
            Step(
                title="Packages (3 tiers)",
                description="Basic: entrega mínima ($30-80). Standard: +features ($80-200). Premium: completo + soporte ($200-500+). Un solo precio por tier",
                action="type",
                element="form[name='packages']",
                value="Basic: $50 | Standard: $120 | Premium: $300",
            ),
            Step(
                title="Description + FAQ",
                description="Qué resuelves, cómo trabajas, qué necesita el cliente, qué entregas, timeline, revisions. FAQ: 3-5 preguntas frecuentes",
                action="type",
                element="textarea[name='description']",
                value="Descripción completa...",
            ),
            Step(
                title="Requirements",
                description="Qué necesitas del cliente para empezar: access, specs, credentials, files. Sé específico",
                action="type",
                element="textarea[name='requirements']",
                value="Necesito: 1) Access al repo/server 2) Especificaciones 3) Credenciales de test",
            ),
            Step(
                title="Gallery (Portfolio)",
                description="Subir 1-3 imágenes: screenshots de trabajos previos, diagramas, resultados. Video opcional",
                action="upload",
                element="input[type='file']",
                value="portfolio.png",
            ),
            Step(
                title="Publish Gig",
                description="Review > 'Publish Gig'. El gig entra en review (24-48h). Una vez aprobado, visible en marketplace",
                action="click",
                element="button:contains('Publish Gig')",
            ),
            Step(
                title="Gestionar Orders",
                description="Orders > 'Active'. Chat con cliente, entregar archivos, 'Deliver Work'. Rating 5 estrellas = visibilidad",
                action="click",
                element="a:contains('Orders')",
            ),
        ],
        file_formats={
            "zip": "Código fuente + docs",
            "py": "Python scripts",
            "js": "JavaScript/Node.js",
            "pdf": "Documentación",
            "mp4": "Video demo (opcional)",
        },
        tips=[
            "UNA sola gig por PROBLEMA ESPECÍFICO. No 'I will do Python work'",
            "Pricing: investiga competencia. Basic = entrada, Standard = valor real, Premium = premium",
            "Response time < 1h = mejor ranking. Configurar notificaciones push/email",
            "First 5 orders CRÍTICOS: over-deliver, 5 estrellas, response rápido = momentum",
            "FAQ reduce mensajes repetitivos. Incluye: timeline, revisions, qué NO incluye",
            "Argentina: Payoneer para recibir USD. Fiverr toma 20% fee. Net = 80% del precio",
        ],
        common_errors=[
            {
                "error": "Gig genérico 'I do coding'",
                "solution": "Título: 'I will [specific action] for [specific result]'",
            },
            {"error": "Precio muy bajo", "solution": "Basic mínimo $30. Valora tu tiempo. Competencia no es precio"},
            {
                "error": "Perfil incompleto",
                "solution": "Skills, certifications, education, languages = confianza del cliente",
            },
            {"error": "Sin portfolio", "solution": "Crear 2-3 proyectos demo en GitHub y screenshot en Gallery"},
            {"error": "Pago no configurado", "solution": "Settings > Billing > Payoneer ANTES del primer order"},
        ],
    ),
    "opire": PlatformGuide(
        platform="opire",
        name="Opire",
        url="https://opire.net",
        account_creation=[
            Step(
                title="Navegar a Opire",
                description="Ir a opire.net > 'Sign in with GitHub'",
                action="navigate",
                element="https://opire.net",
                url="https://opire.net",
            ),
            Step(
                title="Autorizar GitHub",
                description="Opire usa GitHub OAuth. Autorizar acceso a repos públicos/privados según config",
                action="click",
                element="button:contains('Sign in with GitHub')",
            ),
            Step(
                title="Configurar perfil",
                description="Settings > Profile. Bio, skills, timezone. Opire muestra tu GitHub activity",
                action="navigate",
                element="https://opire.net/settings/profile",
                url="https://opire.net/settings/profile",
            ),
            Step(
                title="Configurar pagos",
                description="Settings > Payouts. Stripe Connect (requiere cuenta Stripe o crear). Argentina: Stripe Atlas o Payoneer via Stripe",
                action="navigate",
                element="https://opire.net/settings/payouts",
                url="https://opire.net/settings/payouts",
            ),
        ],
        work_submission=[
            Step(
                title="Explorar Bounties",
                description="Dashboard > 'Bounties'. Filtrar: 'Good First Issue', 'Help Wanted', Language=Python/JS/TS, Reward > $50",
                action="click",
                element="a:contains('Bounties')",
            ),
            Step(
                title="Leer Issue + Repo",
                description="Click bounty > leer Issue en GitHub. Entender: qué hacer, acceptance criteria, labels",
                action="click",
                element=".bounty-card",
            ),
            Step(
                title="Claim Bounty",
                description="Click 'Claim' en Opire. Te asigna el issue en GitHub (si owner acepta)",
                action="click",
                element="button:contains('Claim')",
            ),
            Step(
                title="Fork + Clone + Branch",
                description="Fork repo > clone local > git checkout -b fix/issue-XXX",
                action="copy",
                element="terminal",
                value="git clone TU_FORK_URL && cd repo && git checkout -b fix/issue-123",
            ),
            Step(
                title="Implementar + Test",
                description="Código + tests + documentation. Seguir style guide del repo (lint, pre-commit)",
                action="type",
                element="editor",
                value="Implementación...",
            ),
            Step(
                title="Push + PR",
                description="git push origin fix/issue-123 > GitHub > 'Compare & pull request' > linkear issue (#123)",
                action="click",
                element="a:contains('Compare & pull request')",
            ),
            Step(
                title="Esperar Review + Merge",
                description="Owner review. Cambios si pide. Merge = bounty released a tu Opire balance",
                action="copy",
                element="terminal",
                value="Esperar review...",
            ),
            Step(
                title="Withdraw",
                description="Opire Dashboard > 'Withdraw' > Stripe payout. Tiempo: 7-14 días",
                action="click",
                element="a:contains('Withdraw')",
            ),
        ],
        file_formats={
            "patch": "Git patch file",
            "zip": "Repo completo si necesario",
            "md": "Documentación en PR",
        },
        tips=[
            "Opire = GitHub issues con bounty. Workflow nativo GitHub (fork/PR/merge)",
            "Good First Issue + bounty = mejor entry point para principiantes",
            "Stripe Connect para pagos. Argentina: evalúa Stripe Atlas o Payoneer",
            "Comunicación en PR comments. Profesional, técnico, responsive",
        ],
        common_errors=[
            {"error": "PR no pasa CI", "solution": "Correr lint/test LOCAL antes de push. Leer .github/workflows"},
            {
                "error": "Stripe no disponible en AR",
                "solution": "Evaluar Stripe Atlas (empresa US) o Payoneer via Stripe",
            },
        ],
    ),
    "issuehunt": PlatformGuide(
        platform="issuehunt",
        name="IssueHunt",
        url="https://issuehunt.io",
        account_creation=[
            Step(
                title="Navegar a IssueHunt",
                description="Ir a issuehunt.io > 'Sign in with GitHub'",
                action="navigate",
                element="https://issuehunt.io",
                url="https://issuehunt.io",
            ),
            Step(
                title="Autorizar GitHub",
                description="OAuth GitHub. IssueHunt lee issues de repos públicos",
                action="click",
                element="button:contains('Sign in with GitHub')",
            ),
            Step(
                title="Configurar pagos",
                description="Settings > Payment. PayPal o Bank Transfer. PayPal recomendado para AR",
                action="navigate",
                element="https://issuehunt.io/settings/payment",
                url="https://issuehunt.io/settings/payment",
            ),
        ],
        work_submission=[
            Step(
                title="Explorar Repos + Issues",
                description="Dashboard > 'Repositories' o 'Issues'. Filtrar: Language, Reward, 'Good First Issue'",
                action="click",
                element="a:contains('Issues')",
            ),
            Step(
                title="Seleccionar Issue",
                description="Click issue > leer: Description, Acceptance Criteria, Reward, Labels",
                action="click",
                element=".issue-card",
            ),
            Step(
                title="Start Work",
                description="Click 'Start Work'. Te asigna el issue, crea branch en tu fork automáticamente",
                action="click",
                element="button:contains('Start Work')",
            ),
            Step(
                title="Desarrollar + Commit",
                description="Trabajar en branch. Commits convencionales: 'fix: resolve #123 - description'",
                action="type",
                element="editor",
                value="fix: resolve #123 - add validation",
            ),
            Step(
                title="Submit Work",
                description="Click 'Submit Work' en IssueHunt. Crea PR automáticamente en repo original",
                action="click",
                element="button:contains('Submit Work')",
            ),
            Step(
                title="Review + Merge",
                description="Maintainer review. Aprobación = payout automático a tu balance",
                action="copy",
                element="terminal",
                value="Esperar review...",
            ),
            Step(
                title="Payout",
                description="Balance > 'Withdraw' > PayPal/Bank. Procesamiento 3-5 días",
                action="click",
                element="a:contains('Withdraw')",
            ),
        ],
        file_formats={
            "patch": "Git diff",
            "md": "PR description",
        },
        tips=[
            "IssueHunt = GitHub issues con bounty + workflow automatizado (branch/PR auto)",
            "Auto-crea branch + PR. Menos fricción git manual",
            "PayPal configurado = pagos rápidos a Argentina",
            "Filter: 'Good First Issue' + reward > $30 para empezar",
        ],
        common_errors=[
            {
                "error": "PR auto no se crea",
                "solution": "Verificar permisos GitHub en Settings > Applications > IssueHunt",
            },
        ],
    ),
    "mindrift": PlatformGuide(
        platform="mindrift",
        name="Mindrift",
        url="https://mindrift.com",
        account_creation=[
            Step(
                title="Navegar a Mindrift",
                description="Ir a mindrift.com > 'Join as Expert'",
                action="navigate",
                element="https://mindrift.com",
                url="https://mindrift.com",
            ),
            Step(
                title="Registrarse",
                description="Email, password. Verificar email",
                action="type",
                element="form[name='registration']",
                value="TU_EMAIL, TU_CONTRASEÑA",
            ),
            Step(
                title="Completar perfil",
                description="Idiomas, país (Argentina), educación, experiencia. Mindrift filtra por perfil",
                action="type",
                element="form[name='profile']",
                value="Argentina, Spanish native, University degree...",
            ),
            Step(
                title="Test de calificación",
                description="Test obligatorio: gramática, razonamiento, seguimiento de instrucciones. ~30-60 min",
                action="click",
                element="button:contains('Take Test')",
            ),
            Step(
                title="Esperar aprobación",
                description="Resultado en 24-72h. Si apruebas: acceso a proyectos. Si no: reintentar en 30 días",
                action="copy",
                element="terminal",
                value="Esperando aprobación...",
            ),
        ],
        work_submission=[
            Step(
                title="Dashboard > Available Projects",
                description="Proyectos disponibles según tu perfil/idioma. Cada proyecto = tipo de tarea + pay rate",
                action="click",
                element="a:contains('Projects')",
            ),
            Step(
                title="Leer Guidelines",
                description="Click proyecto > 'Guidelines'. LEER COMPLETO. Reglas estrictas de formato/calidad",
                action="click",
                element="button:contains('Guidelines')",
            ),
            Step(
                title="Start Task",
                description="Click 'Start' en task disponible. Timer empieza. Completar antes de deadline",
                action="click",
                element="button:contains('Start')",
            ),
            Step(
                title="Completar Task",
                description="Seguir guidelines EXACTO. Formato: JSON, CSV, texto, multiple choice. Quality > speed",
                action="type",
                element="task_interface",
                value="Respuestas según guidelines...",
            ),
            Step(
                title="Submit",
                description="Click 'Submit'. Quality review automático + manual. Aprobado = pago",
                action="click",
                element="button:contains('Submit')",
            ),
        ],
        file_formats={
            "json": "Respuestas estructuradas",
            "csv": "Datos tabulares",
            "txt": "Texto libre",
        },
        tips=[
            "Mindrift paga POR TAREA aprobada. Quality score determina acceso a mejores proyectos",
            "Argentina ACEPTADA directamente (no VPN). Idiomas: ES nativo = ventaja",
            "Guidelines son LEY. Un error de formato = reject. Leer 2x antes de submit",
            "Consistencia diaria > maratones. 1-2h/día sostenido mejor que 10h un día",
        ],
        common_errors=[
            {
                "error": "Guidelines no seguidas",
                "solution": "Leer guidelines ANTES de cada task. Tener abierto en segunda pantalla",
            },
            {
                "error": "Quality score bajo",
                "solution": "Hacer menos tasks pero perfectas. Re-leer guidelines de tareas rechazadas",
            },
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
