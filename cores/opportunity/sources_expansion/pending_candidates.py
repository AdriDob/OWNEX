"""Pending source registrations for OWNEX expansion.

These 10 candidates are PRELIMINARY registrations — they must be validated
for identity, eligibility, payout mechanics, and duplicates before being
promoted to active catalog entry. Until then, they remain pending and are
NOT included in BUG_BOUNTY_SOURCES, DEV_BOUNTY_SOURCES, or DATA_ENTRY_SOURCES.

Key policy: argentina_ok defaults to None (UNKNOWN), NOT True. Unknown
must NOT transform to eligible by metadata omission.
"""

from __future__ import annotations


from cores.opportunity.sources_expansion._common import src
from cores.opportunity.global_sources import OpportunityCategory


# ---------------------------------------------------------------------------
# 1. OpenSats — open_source_grant
# ---------------------------------------------------------------------------
OPENSATS = src(
    name="OpenSats",
    url="https://opensats.org",
    category=OpportunityCategory.dev_bounty,  # financia dev/educador; cross-category
    description="Financia desarrolladores y educadores de Bitcoin, Nostr y software libre. Convocatoria Q4 2026 cierra 30/11.",
    type="open_source_grant",
    apply_method="profile_only",
    quality=0.7,
    portfolio=False,
    interview=False,
    experience=False,
    assessment=False,
    rate=None,
    first_work_h=None,
    payout_range="varies",
    language="en",
    argentina_ok=None,  # UNKNOWN — sin evidencia oficial de admisión Argentina
    tags=["bitcoin", "nostr", "software-libre", "grant"],
    priority=10,
    account=True,
    verified="2026-11-20",
)

# ---------------------------------------------------------------------------
# 2. Tari Build Contest — coding_competition
# ---------------------------------------------------------------------------
TARI_CONTEST = src(
    name="Tari Build Contest",
    url="https://tari.build/contest",  # placeholder — verificar URL oficial
    category=OpportunityCategory.dev_bounty,
    description="Concurso de desarrollo con premios en XTM. Convocatoria de noviembre: cierre informado el 30 de noviembre de 2026. Participación mundial con excepciones para miembros del organizador y empleados de Tari Labs. El premio depende de la posición y reglas del concurso.",
    type="coding_competition",
    apply_method="profile_only",
    quality=0.65,
    portfolio=False,
    interview=False,
    experience=False,
    assessment=False,
    rate=None,
    first_work_h=None,
    payout_range="varies (position-dependent)",
    language="en",
    argentina_ok=None,  # UNKNOWN — concurso con excepciones regionales
    tags=["competition", "xtm", "development", " Tari"],
    priority=8,
    account=True,
    verified="2026-11-20",
)

# ---------------------------------------------------------------------------
# 3. Deltakit Community Fund — specialized_open_source_grant
# ---------------------------------------------------------------------------
DELTATK_FUND = src(
    name="Deltakit Community Fund",
    url="https://riverlane.com/deltakit",  # placeholder — verificar fuente oficial
    category=OpportunityCategory.dev_bounty,
    description="Hasta USD 4.000 de financiación y mentoría. Cierre informado: 2 de diciembre de 2026. Orientado a desarrolladores e investigadores de software de corrección de errores cuánticos. Muy especializado; no es una fuente generalista.",
    type="specialized_open_source_grant",
    apply_method="profile_only",
    quality=0.55,
    portfolio=False,
    interview=False,
    experience=False,
    assessment=False,
    rate=None,
    first_work_h=None,
    payout_range="up to USD 4,000",
    language="en",
    argentina_ok=None,  # UNKNOWN — convocatoria técnica especializada
    tags=["quantum", "error-correction", "QEC", "mentoria"],
    priority=9,
    account=True,
    verified="2026-11-20",
)

# ---------------------------------------------------------------------------
# 4. Mozilla Foundation Fellowship — technology_fellowship
# ---------------------------------------------------------------------------
MOZ_FELLOWSHIP = src(
    name="Mozilla Foundation Fellowship",
    url="https://foundation.mozilla.org/fellowship",  # placeholder — verificar URL oficial
    category=OpportunityCategory.dev_bounty,
    description="Convocatoria 2027. Hasta USD 125.000 según directorio de convocatorias. Cierre informado: 17 de diciembre de 2026. Requiere una propuesta de impacto tecnológico, no simplemente completar tickets. Alta prioridad para proyectos propios liberables.",
    type="technology_fellowship",
    apply_method="profile_only",
    quality=0.8,
    portfolio=True,  # fellowship typical requiere portafolio de proyecto
    interview=True,  # selección por propuesta/entrevista
    experience=False,
    assessment=True,  # evaluación de impacto tecnológico
    rate=None,
    first_work_h=None,
    payout_range="up to USD 125,000",
    language="en",
    argentina_ok=None,  # UNKNOWN — verificar condiciones oficiales para Argentina
    tags=["fellowship", "technology", "impact", "Mozilla"],
    priority=9,
    account=True,
    verified="2026-11-20",
)

# ---------------------------------------------------------------------------
# 5. Research Software Catalyst Fund — research_software_grant
# ---------------------------------------------------------------------------
RESEARCH_CATALYST = src(
    name="Research Software Catalyst Fund",
    url="https://digital science/catalyst",  # placeholder — verificar fuente oficial
    category=OpportunityCategory.dev_bounty,
    description="Interesante para proyectos técnicos. Hasta USD 50.000 por subvención exploratoria. Cierre informado: 31 de diciembre de 2026. Se informa disponibilidad mundial para individuos, equipos informales e instituciones. Orientado a software de investigación, no a microtareas.",
    type="research_software_grant",
    apply_method="profile_only",
    quality=0.7,
    portfolio=True,  # typical de grants de software de investigación
    interview=False,
    experience=False,
    assessment=True,  # evaluación de propuesta de investigación
    rate=None,
    first_work_h=None,
    payout_range="up to USD 50,000",
    language="en",
    argentina_ok=None,  # UNKNOWN — verificar disponibilidad mundial
    tags=["research", "software", "grant", "exploratory"],
    priority=7,
    account=True,
    verified="2026-11-20",
)

# ---------------------------------------------------------------------------
# 6. micro1 — conditional technical tasks
# ---------------------------------------------------------------------------
MICRO1_TASKS = src(
    name="micro1",
    url="https://micro1.co/jobs",  # placeholder — verificar oferta activa
    category=OpportunityCategory.dev_bounty,
    description="Oferta de Software Engineer Backend que acepta Argentina. Publicada como remota y sin experiencia obligatoria en el listado. Compensación anunciada de USD 50–100 por tarea aprobada. Pide conocimientos técnicos profundos y una entrevista con IA. No cumple nuestro ideal de ingreso sin entrevistas, pero merece entrar al catálogo como fuente de tareas técnicas.",
    type="coding_competition",  # trata-se de tareas técnicas con evaluación
    apply_method="profile_only",
    quality=0.5,
    portfolio=False,
    interview=True,  # entrevista con IA requerida
    experience=True,  # "conocimientos técnicos profundos"
    assessment=False,
    rate=None,
    first_work_h=None,
    payout_range="USD 50–100 por tarea aprobada",
    language="en",
    argentina_ok=None,  # UNKNOWN — oferta confirmada para Argentina pero con entrevista IA
    tags=["backend", "remote", "task", "AI-interview", "Argentina-conditional"],
    priority=6,
    account=True,
    verified="2026-11-20",
)

# ---------------------------------------------------------------------------
# 7. Igalia Coding Experience — verify apertura
# ---------------------------------------------------------------------------
IGALIA_EXPERIENCE = src(
    name="Igalia Coding Experience",
    url="https://igalia.com/coding-experience",  # placeholder — verificar directorio oficial
    category=OpportunityCategory.dev_bounty,
    description="Programa de experiencia en desarrollo de software libre. El directorio consultado indica una remuneración de hasta USD 7.000. Aperturas periódicas. No asumir que hay plazas disponibles ahora ni que el importe aplica a cualquier participante.",
    type="open_source_grant",
    apply_method="profile_only",
    quality=0.6,
    portfolio=False,
    interview=False,
    experience=False,
    assessment=False,
    rate=None,
    first_work_h=None,
    payout_range="up to USD 7,000",
    language="en",
    argentina_ok=None,  # UNKNOWN — verificar si plazas disponibles y importe aplica
    tags=["igalia", "experience", "software-libre", "development"],
    priority=5,
    account=True,
    verified="2026-11-20",
)

# ---------------------------------------------------------------------------
# 8. European Summer of Code — conditional
# ---------------------------------------------------------------------------
EU_SOC = src(
    name="European Summer of Code",
    url="https://open-source-mv.vercel.app/ESoC",  # placeholder — verificar dominio oficial
    category=OpportunityCategory.dev_bounty,
    description="Programa de contribución a proyectos open source. El directorio indica participación mundial y posibles estipendios. Conviene verificar cada proyecto, financiación y elegibilidad antes de postular.",
    type="open_source_grant",
    apply_method="profile_only",
    quality=0.55,
    portfolio=False,
    interview=False,
    experience=False,
    assessment=False,
    rate=None,
    first_work_h=None,
    payout_range="varies",
    language="en",
    argentina_ok=None,  # UNKNOWN — verificar elegibilidad por región
    tags=["open-source", "contribution", "ESoC", "stipend"],
    priority=5,
    account=True,
    verified="2026-11-20",
)

# ---------------------------------------------------------------------------
# 9. ZeroDay.Cloud 2026 — security_competition (alto riesgo/dificultad)
# ---------------------------------------------------------------------------
ZERODAY_CLOUD = src(
    name="ZeroDay.Cloud 2026",
    url="https://wiz.com/zerodaycloud",  # placeholder — verificar reglas oficiales
    category=OpportunityCategory.dev_bounty,
    description="Concurso de hacking de Wiz con un pozo de premios anunciado de USD 6,5 millones. Cierre informado: 1 de diciembre de 2026. Cobertura mundial según el directorio. No es una oportunidad de USD 6,5 millones por participante: es un premio total competitivo. Incorporar como security_competition, con riesgo y dificultad altos.",
    type="security_competition",
    apply_method="profile_only",
    quality=0.4,  # alto riesgo, baja tasa de éxito por participante
    portfolio=False,
    interview=False,
    experience=True,  # se asume capacidad de seguridad avanzada
    assessment=True,  # evaluación de skills para concurso
    rate=None,
    first_work_h=None,
    payout_range="competitive pool USD 6.5M (not per participant)",
    language="en",
    argentina_ok=None,  # UNKNOWN — cobertura mundial pero alto umbral de participación
    tags=["security", "hacking", "competition", "WD", "high-risk"],
    priority=4,  # alta prioridad de incorporación pero alto riesgo/dificultad
    account=True,
    verified="2026-11-20",
)

# ---------------------------------------------------------------------------
# 10. Terac — DESCARTADA (no incluida en pending active)
# ---------------------------------------------------------------------------
# Terac was evaluated and discarded per audit recommendation:
# "exige experiencia profesional y evaluación técnica. La descarto de las
# recomendaciones prioritarias porque no respeta tus condiciones actuales."
# It is referenced here only for audit trail — NOT promoted.
#
# Terac would have been:
# src(name="Terac", url="...", type="...", argentina_ok=None, ...)
# But it is EXCLUDED from the pending list per auditoría Phase 0 instruction.

# ---------------------------------------------------------------------------
# Pending catalog — do NOT promote to active until Phase 0-2 resolved:
#   • Git reconciliado (core/ vs cores/ vs core/cores/)
#   • Build frontend exitoso (PR #70 aislado)
#   • SQLite persistencia validada en ejecución local
#   • Aplicación web levanta, guarda datos y sobrevive reinicio
# ---------------------------------------------------------------------------

__all__ = [
    "OPENSATS",
    "TARI_CONTEST",
    "DELTATK_FUND",
    "MOZ_FELLOWSHIP",
    "RESEARCH_CATALYST",
    "MICRO1_TASKS",
    "IGALIA_EXPERIENCE",
    "EU_SOC",
    "ZERODAY_CLOUD",
]
