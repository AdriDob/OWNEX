"""Application Assistant — plan asistido de postulación a plataformas de ingreso.

Guía paso a paso para postular a plataformas AI-training y freelance desde
Argentina (Outlier, Mercor, Alignerr, Mindrift, Fiverr). Cada paso trae qué
poner en cada campo, pre-rellenado desde el Profile Kit real del usuario.
Progreso persistido en ``data/applications.json`` (sobrevive restarts).

Nota 2026: Argentina está aceptado directamente en Outlier/Mercor/Alignerr/
Mindrift — la postulación es honesta (ID + móvil del país real, sin VPN).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("cores.application_assistant")

STORE_FILENAME = "applications.json"

STATUS_PENDING = "pending"
STATUS_APPLIED = "applied"
STATUS_IN_REVIEW = "in_review"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"
STATUS_PAUSED = "paused"

VALID_STATUSES = {
    STATUS_PENDING,
    STATUS_APPLIED,
    STATUS_IN_REVIEW,
    STATUS_ACCEPTED,
    STATUS_REJECTED,
    STATUS_PAUSED,
}


def _default_store_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / STORE_FILENAME


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _platform_catalog() -> list[dict[str, Any]]:
    """Catálogo curado de plataformas, ordenado por prioridad de caja."""
    return [
        {
            "key": "outlier",
            "name": "Outlier (Scale AI)",
            "url": "https://outlier.ai",
            "category": "ai_training_coding",
            "pay_range": "$8–18/h coding tier LatAm; $35–60/h specialist",
            "payout": "semanal (PayPal/Payoneer/Airtm)",
            "time_to_first_income": "1–3 semanas desde aprobación",
            "why": "Acepta Argentina directo; tu track natural es coding evaluation.",
        },
        {
            "key": "mercor",
            "name": "Mercor",
            "url": "https://work.mercor.com/explore",
            "category": "ai_training_specialist",
            "pay_range": "$25–53/h skilled; más para domain experts",
            "payout": "por proyecto",
            "time_to_first_income": "2–4 semanas (screening riguroso)",
            "why": "Techo salarial más alto para devs verificados.",
        },
        {
            "key": "alignerr",
            "name": "Alignerr (Labelbox)",
            "url": "https://www.alignerr.com/jobs",
            "category": "ai_training_coding",
            "pay_range": "$8–30/h según expertise",
            "payout": "semanal (PayPal/Payoneer, mínimo $20)",
            "time_to_first_income": "1–3 semanas",
            "why": "100+ países, onboarding simple, buena como segunda cola.",
        },
        {
            "key": "mindrift",
            "name": "Mindrift (Toloka)",
            "url": "https://mindrift.ai",
            "category": "ai_training_writing",
            "pay_range": "$15–40/h; tareas de español nativo pagan mejor",
            "payout": "bi-semanal",
            "time_to_first_income": "2–4 semanas",
            "why": "El español nativo + inglés técnico es un activo real acá.",
        },
        {
            "key": "fiverr",
            "name": "Fiverr",
            "url": "https://www.fiverr.com",
            "category": "freelance_services",
            "pay_range": "$20–150 por orden según gig",
            "payout": "14 días post-entrega",
            "time_to_first_income": "1–3 semanas hasta primera orden",
            "why": "Setup único; los textos ya los genera tu Profile Kit.",
        },
    ]


def _steps_catalog() -> dict[str, list[dict[str, Any]]]:
    """Pasos por plataforma con guía de qué poner en cada campo."""
    return {
        "outlier": [
            {
                "id": "create_account",
                "title": "Crear cuenta en outlier.ai",
                "detail": "Registrarte con tu email principal. Argentina aceptado — sin VPN, la IP debe ser tu residencia real.",
                "est_minutes": 5,
                "fields": {
                    "email": "Tu email principal (el mismo de LinkedIn idealmente)",
                    "country": "Argentina — siempre honesto",
                },
            },
            {
                "id": "expertise_profile",
                "title": "Completar áreas de expertise",
                "detail": "Elegí Software Development/Coding como dominio principal. Los tracks generales pagan menos.",
                "est_minutes": 10,
                "fields": {
                    "domain": "Software Development / Coding",
                    "skills": "Python, JavaScript/TypeScript, Git, Security (del Profile Kit)",
                    "languages": "Español (nativo), Inglés (profesional)",
                },
            },
            {
                "id": "identity_verification",
                "title": "Verificación de identidad",
                "detail": "DNI argentino + número de móvil argentino. Deben coincidir con tu país de residencia — vas a trabajar solo desde ahí.",
                "est_minutes": 10,
                "fields": {},
            },
            {
                "id": "resume_linkedin",
                "title": "Subir CV + LinkedIn",
                "detail": "El CV debe mostrar años de experiencia dev y educación. LinkedIn actualizado con lo mismo.",
                "est_minutes": 15,
                "requires": "cv",
                "fields": {
                    "resume": "CV enfocado en desarrollo (no seguridad): proyectos, stack, años",
                    "linkedin": "URL de tu LinkedIn actualizado",
                },
            },
            {
                "id": "coding_assessment",
                "title": "Skills assessment de coding (cronometrado)",
                "detail": "Problemas estilo LeetCode + evaluar outputs de código. Bloqueá 60 min sin distracciones; leé cada consigna completa antes de responder.",
                "est_minutes": 60,
                "fields": {},
            },
            {
                "id": "project_onboarding",
                "title": "Onboarding por proyecto (cuando aprueben)",
                "detail": "Leé las guidelines COMPLETAS antes del practice task. Las primeras semanas puede haber trabajo rechazado sin pago mientras agarrás el estilo del proyecto — es normal, no te frustres.",
                "est_minutes": 30,
                "fields": {},
            },
        ],
        "mercor": [
            {
                "id": "create_account",
                "title": "Crear cuenta y subir CV",
                "detail": "work.mercor.com — parsea tu CV automáticamente. Revisá que extraiga bien tus skills.",
                "est_minutes": 15,
                "requires": "cv",
                "fields": {"cv": "El mismo CV de Outlier", "domain": "Software Engineering"},
            },
            {
                "id": "ai_interview",
                "title": "Entrevista IA por video (~20 min)",
                "detail": "En inglés, cámara prendida. Respuestas claras y estructuradas: situación → acción → resultado.",
                "est_minutes": 25,
                "requires": "interview",
                "fields": {},
            },
            {
                "id": "technical_screening",
                "title": "Screening técnico del dominio",
                "detail": "Evaluación de coding según tu especialidad declarada.",
                "est_minutes": 45,
                "fields": {},
            },
            {
                "id": "project_matching",
                "title": "Esperar match de proyecto",
                "detail": "Mercor te asigna tareas según credenciales verificadas. Puede tardar semanas — no bloquea las otras plataformas.",
                "est_minutes": 5,
                "fields": {},
            },
        ],
        "alignerr": [
            {
                "id": "create_account",
                "title": "Crear cuenta en alignerr.com/jobs",
                "detail": "Perfil orientado a dominio software/coding. Aplicar a los listings activos para tu región.",
                "est_minutes": 15,
                "requires": "cv",
                "fields": {"profile": "Mismo CV + skills del kit"},
            },
            {
                "id": "domain_assessment",
                "title": "Assessment por proyecto activo",
                "detail": "Cada proyecto tiene su propio test. Postulate a varios; son independientes.",
                "est_minutes": 40,
                "fields": {},
            },
            {
                "id": "payment_setup",
                "title": "Configurar cobro PayPal/Payoneer",
                "detail": "Pago semanal, mínimo $20. Payoneer funciona bien para Argentina.",
                "est_minutes": 15,
                "fields": {},
            },
        ],
        "mindrift": [
            {
                "id": "create_account",
                "title": "Crear cuenta en mindrift.ai (vía All-access)",
                "detail": "Cargá dominios técnicos + ambos idiomas. La vía All-access (anotación, clasificación, comparación, transcripción) no pide experiencia, título, CV, entrevista ni assessment. El español nativo abre tareas específicas mejor pagas.",
                "est_minutes": 10,
                "fields": {
                    "domains": "Software development, security",
                    "languages": "Spanish (native), English (professional)",
                },
            },
            {
                "id": "writing_tests",
                "title": "Evaluaciones ES + EN (solo vía Specialized)",
                "detail": "Solo si vas por proyectos Specialized (coding/STEM/etc.): evalúan calidad y rubrics + piden CV y verificación de identidad. Pagan más, pero NO son sin experiencia.",
                "est_minutes": 35,
                "fields": {},
            },
            {
                "id": "project_wait",
                "title": "Esperar match de proyecto",
                "detail": "Por proyecto, pago bi-semanal. Complementa, no reemplaza Outlier.",
                "est_minutes": 5,
                "fields": {},
            },
        ],
        "fiverr": [
            {
                "id": "generate_gigs",
                "title": "Generar textos de gigs con el Profile Kit",
                "detail": "POST /api/profile-kit/generate devuelve los campos bilingües listos para copiar.",
                "est_minutes": 10,
                "fields": {"endpoint": "POST /api/profile-kit/generate (sin payload usa tu perfil guardado)"},
            },
            {
                "id": "publish_3_gigs",
                "title": "Publicar 3 gigs",
                "detail": "Bug fixing, Python automation, API integration — capacidades demostrables con el portfolio propio.",
                "est_minutes": 45,
                "fields": {},
            },
            {
                "id": "first_response_sprint",
                "title": "Sprint de respuesta rápida",
                "detail": "Los primeros días respondé consultas en <1 h: el algoritmo premia la responsiveness inicial.",
                "est_minutes": 0,
                "fields": {},
            },
        ],
        "hackerone": [
            {
                "id": "create_account",
                "title": "Crear cuenta en HackerOne",
                "detail": "hackerone.com — registrarte con email real. Sin restricciones de país para hunters.",
                "est_minutes": 5,
                "fields": {"email": "Tu email principal", "username": "Handle profesional"},
            },
            {
                "id": "configure_payment",
                "title": "Configurar método de payout",
                "detail": "Settings → Payouts. PayPal o Payoneer funcionan desde Argentina. Mínimo $300 USD para PayPal.",
                "est_minutes": 10,
                "fields": {},
            },
            {
                "id": "api_key",
                "title": "Generar API key",
                "detail": "Settings → API token → crear token de solo lectura para sync de earnings.",
                "est_minutes": 5,
                "fields": {},
            },
            {
                "id": "first_program",
                "title": "Seleccionar primer programa público",
                "detail": "Filtrar por: public + bounty + reports > 50. Evitar programas VDP (sin pago). Empezar con scope amplio.",
                "est_minutes": 15,
                "fields": {},
            },
        ],
        "issuehunt": [
            {
                "id": "create_account",
                "title": "Crear cuenta en IssueHunt",
                "detail": "issuehunt.io — login con GitHub. Vincula tus repos automáticamente.",
                "est_minutes": 3,
                "fields": {},
            },
            {
                "id": "connect_github",
                "title": "Vincular cuenta GitHub",
                "detail": "Autorizar OAuth. Tu historial de contribuciones es tu reputación acá.",
                "est_minutes": 2,
                "fields": {},
            },
            {
                "id": "configure_payout",
                "title": "Configurar payout",
                "detail": "PayPal o crypto (USDC). Sin mínimo aparente.",
                "est_minutes": 5,
                "fields": {},
            },
        ],
        "freelancer": [
            {
                "id": "create_account",
                "title": "Crear perfil en Freelancer.com",
                "detail": "freelancer.com — completar perfil con skills del Profile Kit. Los primeros proyectos conviene hacerlos a bajo precio por reviews.",
                "est_minutes": 20,
                "fields": {"skills": "Python, Web Scraping, Automation (del Profile Kit)"},
            },
            {
                "id": "verify_identity",
                "title": "Verificar identidad",
                "detail": "DNI + selfie. Necesario para retirar fondos.",
                "est_minutes": 15,
                "fields": {},
            },
            {
                "id": "configure_payment",
                "title": "Configurar método de retiro",
                "detail": "Payoneer o PayPal funcionan desde Argentina. Verificar fees de conversión USD→ARS.",
                "est_minutes": 10,
                "fields": {},
            },
            {
                "id": "first_bid",
                "title": "Primer bid",
                "detail": "Buscar proyectos pequeños ($30-100) con pocos bids. El Profile Kit genera la propuesta — copiar y ajustar.",
                "est_minutes": 20,
                "fields": {},
            },
        ],
    }


class ApplicationAssistant:
    """Plan asistido + tracking persistente de postulaciones."""

    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = Path(store_path) if store_path else _default_store_path()

    # ── Persistencia ──

    def _load_state(self) -> dict[str, Any]:
        try:
            if self.store_path.exists():
                return json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("applications store corrupto, se reinicia: %s", exc)
        return {}

    def _save_state(self, state: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def _platform_state(self, state: dict[str, Any], key: str) -> dict[str, Any]:
        entry = state.get(key)
        if not isinstance(entry, dict):
            entry = {"status": STATUS_PENDING, "completed_steps": [], "updated_at": None}
            state[key] = entry
        entry.setdefault("status", STATUS_PENDING)
        completed = entry.setdefault("completed_steps", [])
        if not isinstance(completed, list):
            entry["completed_steps"] = []
        return entry

    # ── Perfil (respuestas sugeridas) ──

    def _seed_answers(self) -> dict[str, str]:
        """Respuestas pre-rellenadas desde el Profile Kit real (defensivo)."""
        try:
            from cores.direct_work_engine.profile_kit import ProfileKitEngine

            kit = ProfileKitEngine()
            raw = kit.get() or {}
            if not raw:
                raw = kit.default_profile()
            profile = ProfileKitEngine.profile_from_dict(raw)
            skills = sorted(profile.skills)[:6]
            languages = sorted(profile.languages)
            parts = [p for p in [profile.name, profile.country] if p]
            return {
                "name": " ".join(parts) or "",
                "skills_list": ", ".join(skills),
                "languages_list": ", ".join(languages),
                "github_url": profile.github_url,
                "linkedin_url": profile.linkedin_url,
                "availability_hours": f"{profile.availability_hours:g} h/semana",
            }
        except Exception as exc:  # pragma: no cover - defensivo
            logger.warning("Profile Kit no disponible para seeds: %s", exc)
            return {}

    # ── Plan ──

    def get_plan(self, allow_interview_paths: bool = False) -> dict[str, Any]:
        state = self._load_state()
        seeds = self._seed_answers()
        platforms: list[dict[str, Any]] = []
        for meta in _platform_catalog():
            key = meta["key"]
            entry = self._platform_state(state, key)
            done = set(entry.get("completed_steps") or [])
            steps = []
            gated = 0
            for step in _steps_catalog().get(key, []):
                if not allow_interview_paths and step.get("requires") in ("cv", "interview"):
                    gated += 1
                    continue
                steps.append({**step, "done": step["id"] in done})
            total = len(steps)
            completed = sum(1 for s in steps if s["done"])
            platforms.append(
                {
                    **meta,
                    "status": entry["status"],
                    "steps": steps,
                    "completed_steps": completed,
                    "total_steps": total,
                    "progress_pct": round(completed / total * 100) if total else 0,
                    "gated_steps": gated,
                }
            )
        return {
            "generated_at": _now_iso(),
            "suggested_answers": seeds,
            "note": "Postulación honesta desde Argentina: ID + móvil reales, sin VPN.",
            "zero_barrier": not allow_interview_paths,
            "zero_barrier_note": (
                "Pasos con CV/entrevista ocultos; solo registro y assessments. "
                "Pasá allow_interview_paths=True para verlos."
                if not allow_interview_paths
                else "Mostrando todos los pasos, incluidos CV/entrevista."
            ),
            "platforms": platforms,
        }

    # ── Mutaciones ──

    def complete_step(self, platform_key: str, step_id: str) -> dict[str, Any]:
        if platform_key not in {m["key"] for m in _platform_catalog()}:
            raise KeyError(f"plataforma desconocida: {platform_key}")
        known = {s["id"] for s in _steps_catalog().get(platform_key, [])}
        if step_id not in known:
            raise KeyError(f"paso desconocido: {step_id}")
        state = self._load_state()
        entry = self._platform_state(state, platform_key)
        if step_id not in entry["completed_steps"]:
            entry["completed_steps"].append(step_id)
        entry["updated_at"] = _now_iso()
        self._save_state(state)
        return {"success": True, "platform": platform_key, "step": step_id}

    def set_status(self, platform_key: str, status: str) -> dict[str, Any]:
        if platform_key not in {m["key"] for m in _platform_catalog()}:
            raise KeyError(f"plataforma desconocida: {platform_key}")
        if status not in VALID_STATUSES:
            raise ValueError(f"estado inválido: {status}")
        state = self._load_state()
        entry = self._platform_state(state, platform_key)
        entry["status"] = status
        entry["updated_at"] = _now_iso()
        self._save_state(state)
        return {"success": True, "platform": platform_key, "status": status}

    # ── Platform Onboarding (Platform Operations Engine) ──

    ONBOARDING_STATES = (
        "NOT_STARTED",
        "REGISTERED",
        "EMAIL_VERIFIED",
        "PROFILE_COMPLETE",
        "PAYMENT_READY",
        "QUALIFICATION_PENDING",
        "QUALIFIED",
        "ACTIVE",
        "BLOCKED",
        "SUSPENDED",
        "UNKNOWN",
    )

    # §4/§9 facet checklist: facet -> step-id keywords. A facet is done when any
    # completed step id contains a keyword; unknown when no step covers it
    # (never invented). FIRST_PAYMENT stays unknown without revenue evidence
    # (accepted != paid, Rule §39).
    PLATFORM_FACETS: dict[str, tuple[str, ...]] = {
        "account": ("create_account",),
        "email": ("email_verify", "verify_email"),
        "profile": ("expertise_profile", "resume_linkedin", "generate_gigs"),
        "identity": ("identity_verification", "verify_identity"),
        "kyc": ("kyc",),
        "payment": ("payment_setup", "configure_payment", "configure_payout"),
        "wallet": ("wallet",),
        "api": ("api_key",),
        "oauth": ("connect_github", "oauth"),
        "skills": ("coding_assessment", "domain_assessment", "writing_tests", "ai_interview", "technical_screening"),
        "reputation": ("reputation",),
        "first_opportunity": (
            "project_onboarding",
            "project_matching",
            "project_wait",
            "publish_3_gigs",
            "first_program",
            "first_bid",
        ),
        "first_submission": ("first_submission", "submit_work"),
        "first_acceptance": ("first_acceptance",),
        "first_payment": (),
    }

    GLOBAL_STATES = (
        "NOT_CONNECTED",
        "ONBOARDING",
        "CONFIGURING",
        "BLOCKED",
        "READY",
        "OPERATIONAL",
        "EARNING",
        "OPTIMIZING",
    )

    def get_platform_status(self, platform_key: str, allow_interview_paths: bool = False) -> dict[str, Any]:
        """§4/§9 facet checklist + global state for one platform (derived, never invented)."""
        ob = self.get_onboarding(platform_key, allow_interview_paths=allow_interview_paths)
        done_ids = {c["id"] for c in ob["checklist"] if c["done"]}
        all_ids = {c["id"] for c in ob["checklist"]}

        facets: dict[str, str] = {}
        for facet, keywords in self.PLATFORM_FACETS.items():
            if not keywords or not any(k in " ".join(all_ids) for k in keywords):
                facets[facet] = "unknown"
            elif any(any(k in sid for k in keywords) for sid in done_ids):
                facets[facet] = "done"
            else:
                facets[facet] = "pending"

        status = ob["status"]
        readiness = ob["readiness_pct"]
        if status in (STATUS_REJECTED,):
            global_state = "BLOCKED"
        elif status == STATUS_ACCEPTED and facets["first_opportunity"] == "done":
            global_state = "EARNING"
        elif readiness >= 80:
            global_state = "OPERATIONAL"
        elif facets["payment"] == "done" or readiness >= 50:
            global_state = "READY"
        elif status in (STATUS_APPLIED, STATUS_IN_REVIEW):
            global_state = "ONBOARDING"
        elif done_ids:
            global_state = "CONFIGURING"
        else:
            global_state = "NOT_CONNECTED"

        missing = [f for f, v in facets.items() if v == "pending"]
        nxt = ob["next_action"]
        return {
            "platform": platform_key,
            "facets": facets,
            "global_state": global_state,
            "missing": missing,
            "unknown_facets": [f for f, v in facets.items() if v == "unknown"],
            "next_action": nxt,
            "what_unlocks": (
                f"Completar '{nxt['title']}' (~{nxt['est_minutes']} min) desbloquea el siguiente facet."
                if nxt
                else "Onboarding completo en lo medible; el cobro se confirma con revenue real."
            ),
        }

    def get_onboarding(self, platform_key: str, allow_interview_paths: bool = False) -> dict[str, Any]:
        """Onboarding state for a platform: what's done, what's missing, readiness %."""
        if platform_key not in {m["key"] for m in _platform_catalog()}:
            raise KeyError(f"plataforma desconocida: {platform_key}")
        state = self._load_state()
        entry = self._platform_state(state, platform_key)
        steps = [
            s
            for s in _steps_catalog().get(platform_key, [])
            if allow_interview_paths or s.get("requires") not in ("cv", "interview")
        ]
        done_ids = set(entry.get("completed_steps") or [])

        checklist = []
        for step in steps:
            checklist.append(
                {
                    "id": step["id"],
                    "title": step["title"],
                    "detail": step.get("detail", ""),
                    "done": step["id"] in done_ids,
                    "est_minutes": step.get("est_minutes", 0),
                    "human_required": True,
                }
            )

        total = len(checklist)
        completed = sum(1 for c in checklist if c["done"])
        readiness = round(completed / total * 100) if total else 0

        pending = [c for c in checklist if not c["done"]]
        next_step = pending[0] if pending else None

        meta = next((m for m in _platform_catalog() if m["key"] == platform_key), {})

        return {
            "platform": platform_key,
            "name": meta.get("name", platform_key),
            "url": meta.get("url", ""),
            "status": entry["status"],
            "readiness_pct": readiness,
            "total_steps": total,
            "completed_steps": completed,
            "checklist": checklist,
            "next_action": {
                "step_id": next_step["id"],
                "title": next_step["title"],
                "detail": next_step["detail"],
                "est_minutes": next_step["est_minutes"],
                "url": meta.get("url", ""),
            }
            if next_step
            else None,
            "payment_ready": any(c["id"] == "payment_setup" and c["done"] for c in checklist)
            or entry["status"] in ("ACTIVE", "QUALIFIED"),
            "pay_range": meta.get("pay_range", ""),
            "payout": meta.get("payout", ""),
            "why": meta.get("why", ""),
        }

    def get_all_onboarding(self, allow_interview_paths: bool = False) -> list[dict[str, Any]]:
        """Onboarding summary for all platforms."""
        results = []
        for meta in _platform_catalog():
            with contextlib.suppress(Exception):
                results.append(self.get_onboarding(meta["key"], allow_interview_paths=allow_interview_paths))
        return results

    # ── All-access entry (vía segura sin experiencia profesional) ──

    # Mercor fuera: su única vía curada exige entrevista IA por video
    # (ai_interview) + CV. Sin path sin-entrevista en datos → no entra acá.
    # Sigue en el catálogo general con opt-in (allow_interview_paths=True).
    ALL_ACCESS_PLATFORMS: tuple[str, ...] = ("outlier", "alignerr", "mindrift")

    @staticmethod
    def _entry_verdict(all_steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Veredicto de entrada derivado de los steps (nunca inventado).

        ALL_ACCESS_OK: ningún step exige CV/entrevista (solo registro +
        assessments de habilidad). NEEDS_CV / NEEDS_INTERVIEW en caso contrario.
        """
        requires = {str(s.get("requires") or "") for s in all_steps}
        if "interview" in requires:
            return {
                "verdict": "NEEDS_INTERVIEW",
                "experience_required": True,
                "note": "Pide entrevista (opt-in). No es entrada 100% segura sin proceso.",
            }
        if "cv" in requires:
            return {
                "verdict": "NEEDS_CV",
                "experience_required": False,
                "note": "Pide CV pero sin entrevista: assessments de habilidad deciden. Entrada segura con CV listo.",
            }
        return {
            "verdict": "ALL_ACCESS_OK",
            "experience_required": False,
            "note": "Sin experiencia profesional, sin CV, sin entrevista. Solo registro + assessments de habilidad.",
        }

    def get_all_access_entry(self) -> dict[str, Any]:
        """Vía all-access ordenada por seguridad: qué hacer en cada web para entrar 100% seguro.

        Solo AI sin entrevista (outlier/alignerr/mindrift). Mercor queda fuera:
        su única vía curada exige entrevista IA por video + CV. Orden:
        ALL_ACCESS_OK primero, luego NEEDS_CV; desempate por minutos totales
        visibles. Los minutos y pasos salen del catálogo real.
        """
        entries = []
        for meta in _platform_catalog():
            key = meta["key"]
            if key not in self.ALL_ACCESS_PLATFORMS:
                continue
            verdict = self._entry_verdict(_steps_catalog().get(key, []))
            ob = self.get_onboarding(key)  # vista default: pasos CV/entrevista ocultos
            total_minutes = sum(int(s.get("est_minutes") or 0) for s in ob["checklist"])
            entries.append(
                {
                    "platform": key,
                    "name": meta.get("name", key),
                    "url": meta.get("url", ""),
                    "verdict": verdict["verdict"],
                    "experience_required": verdict["experience_required"],
                    "verdict_note": verdict["note"],
                    "pay_range": meta.get("pay_range", ""),
                    "payout": meta.get("payout", ""),
                    "why": meta.get("why", ""),
                    "status": ob["status"],
                    "readiness_pct": ob["readiness_pct"],
                    "total_minutes": total_minutes,
                    "steps": ob["checklist"],
                    "next_action": ob["next_action"],
                }
            )
        rank = {"ALL_ACCESS_OK": 0, "NEEDS_CV": 1, "NEEDS_INTERVIEW": 2}
        entries.sort(key=lambda e: (rank.get(e["verdict"], 9), e["total_minutes"]))
        return {
            "generated_at": _now_iso(),
            "note": "Entrada segura = sin experiencia profesional. Assessments de habilidad sí (son la puerta, no la barrera).",
            "safest_first": entries[0]["platform"] if entries else None,
            "total_minutes_all": sum(e["total_minutes"] for e in entries),
            "entries": entries,
        }

    def get_platform_ranking(self) -> list[dict[str, Any]]:
        """Rank platforms by readiness × pay — where should the user work NOW?"""
        ranked = []
        for ob in self.get_all_onboarding():
            try:
                from cores.opportunity.global_sources import find_curated_entry_model

                facts = find_curated_entry_model(ob["platform"])
                rate = float(facts["hourly_rate_usd"]) if facts and facts.get("hourly_rate_usd") else None
            except Exception:
                rate = None

            readiness = ob["readiness_pct"] / 100.0
            effective_rate = round(rate * readiness, 2) if rate else None

            ranked.append(
                {
                    "platform": ob["platform"],
                    "name": ob["name"],
                    "readiness_pct": ob["readiness_pct"],
                    "documented_rate_usd_h": rate,
                    "effective_rate_usd_h": effective_rate,
                    "status": ob["status"],
                    "next_action": ob["next_action"],
                    "recommendation": (
                        "WORK_HERE"
                        if readiness >= 0.8 and effective_rate
                        else "FINISH_SETUP"
                        if readiness >= 0.3
                        else "START_ONBOARDING"
                        if ob["status"] != "accepted"
                        else "ACTIVE_STREAM"
                    ),
                }
            )
        ranked.sort(key=lambda r: r.get("effective_rate_usd_h") or 0, reverse=True)
        return ranked

    # ── Assessment prep-packs (P1 vNext) ──
    # Qué evalúa cada assessment + checklist de preparación + intentos.
    # Contenido HONESTO y genérico: áreas de habilidad y método, jamás
    # respuestas filtradas ni atajos. Rendirlo sigue siendo 100% humano.

    _PREP_PACKS: dict[str, dict[str, Any]] = {
        "coding_assessment": {
            "evaluates": [
                "lectura de consignas",
                "código Python/JS",
                "evaluación de outputs",
                "criterio bajo presión de tiempo",
            ],
            "checklist": [
                "repasar Python base 45 min",
                "practicar explicar código en voz alta",
                "leer CADA consigna completa antes de responder",
                "bloquear 60 min sin distracciones",
            ],
            "est_minutes": 45,
        },
        "domain_assessment": {
            "evaluates": ["conocimiento del dominio elegido", "criterio con rubrics", "idioma técnico ES+EN"],
            "checklist": [
                "elegir 1 dominio donde ya sabés",
                "repasar vocabulario técnico en inglés",
                "practicar seguir una rubric al pie de la letra",
            ],
            "est_minutes": 30,
        },
        "writing_tests": {
            "evaluates": ["calidad de escritura", "seguimiento de rubrics", "comparación de respuestas"],
            "checklist": [
                "escribir 1 párrafo técnico de muestra",
                "practicar puntuar 2 respuestas con criterios",
                "revisar gramática ES e inglesa",
            ],
            "est_minutes": 30,
        },
        "ai_interview": {
            "evaluates": ["experiencia verificable", "comunicación", "encaje de dominio"],
            "checklist": [
                "CV y LinkedIn consistentes",
                "2 proyectos contables en 60 segundos",
                "ambiente con cámara/mic probados",
            ],
            "est_minutes": 30,
        },
        "technical_screening": {
            "evaluates": ["screening técnico general", "disponibilidad y encaje"],
            "checklist": ["stack y seniority declarados con honestidad", "horarios disponibles claros"],
            "est_minutes": 15,
        },
    }

    def get_prep_pack(self, platform_key: str, step_id: str) -> dict[str, Any]:
        """Pack de preparación + seeds del perfil + intentos previos. {} si el paso no es assessment."""
        if platform_key not in {m["key"] for m in _platform_catalog()}:
            raise KeyError(f"plataforma desconocida: {platform_key}")
        pack = self._PREP_PACKS.get(step_id)
        if pack is None:
            return {}
        state = self._load_state()
        attempts = [a for a in state.get(platform_key, {}).get("attempts", []) if a.get("step_id") == step_id]
        return {
            "platform": platform_key,
            "step_id": step_id,
            "evaluates": list(pack["evaluates"]),
            "checklist": list(pack["checklist"]),
            "est_minutes": pack["est_minutes"],
            "suggested_answers": self._seed_answers(),
            "prior_attempts": attempts,
        }

    def record_attempt(self, platform_key: str, step_id: str, passed: bool | None, notes: str = "") -> dict[str, Any]:
        """Registra un intento de assessment (pasado=True/False, None=sin resultado aún)."""
        if platform_key not in {m["key"] for m in _platform_catalog()}:
            raise KeyError(f"plataforma desconocida: {platform_key}")
        if step_id not in self._PREP_PACKS:
            raise KeyError(f"paso sin prep-pack (no es assessment): {step_id}")
        if passed is not None and not isinstance(passed, bool):
            raise ValueError("passed debe ser True, False o None")
        state = self._load_state()
        entry = self._platform_state(state, platform_key)
        attempts = entry.setdefault("attempts", [])
        attempts.append({"step_id": step_id, "passed": passed, "notes": notes[:500], "at": _now_iso()})
        entry["updated_at"] = _now_iso()
        self._save_state(state)
        return {"success": True, "platform": platform_key, "step": step_id, "attempts": len(attempts)}

    def attempt_summary(self, platform_key: str | None = None) -> dict[str, Any]:
        """Resumen de intentos por assessment: {step_id: {attempts, passed}}. Sin datos → {}."""
        state = self._load_state()
        keys = [platform_key] if platform_key else [m["key"] for m in _platform_catalog()]
        out: dict[str, Any] = {}
        for key in keys:
            per_step: dict[str, dict[str, int]] = {}
            for a in state.get(key, {}).get("attempts", []):
                slot = per_step.setdefault(a.get("step_id", "?"), {"attempts": 0, "passed": 0})
                slot["attempts"] += 1
                if a.get("passed") is True:
                    slot["passed"] += 1
            if per_step:
                out[key] = per_step
        return out

    # ── Resumen ──

    def overview(self, allow_interview_paths: bool = False) -> dict[str, Any]:
        plan = self.get_plan(allow_interview_paths=allow_interview_paths)
        by_status: dict[str, int] = {}
        next_action: dict[str, Any] | None = None
        for platform in plan["platforms"]:
            by_status[platform["status"]] = by_status.get(platform["status"], 0) + 1
            if next_action is None and platform["status"] not in {
                STATUS_ACCEPTED,
                STATUS_REJECTED,
                STATUS_PAUSED,
            }:
                pending = [s for s in platform["steps"] if not s["done"]]
                if pending:
                    step = pending[0]
                    next_action = {
                        "platform": platform["key"],
                        "platform_name": platform["name"],
                        "url": platform["url"],
                        "step": step["title"],
                        "detail": step["detail"],
                        "fields": step["fields"],
                        "est_minutes": step["est_minutes"],
                    }
        total_steps = sum(p["total_steps"] for p in plan["platforms"])
        done_steps = sum(p["completed_steps"] for p in plan["platforms"])
        return {
            "generated_at": _now_iso(),
            "by_status": by_status,
            "progress_pct": round(done_steps / total_steps * 100) if total_steps else 0,
            "next_action": next_action,
        }


def get_study_tracks() -> dict[str, Any]:
    """Tracks de estudio web3/cybersec/AI — 100% gratis, $0. Feed del sistema de empleo+estudio."""
    return {
        "tracks": [
            {
                "key": "web3_solidity",
                "name": "Web3 / Solidity",
                "goal": "Leer y auditar contratos básicos; base para Sherlock/Cantina/Code4rena",
                "resources": [
                    {"title": "CryptoZombies (gratis, interactivo)", "url": "https://cryptozombies.io"},
                    {"title": "Solidity docs + Foundry book (gratis)", "url": "https://book.getfoundry.sh"},
                    {"title": "Solodit checklist auditoría (gratis)", "url": "https://solodit.xyz"},
                ],
                "milestone": "Completar CryptoZombies + deploy local con Foundry",
                "est_hours": 20,
            },
            {
                "key": "cybersec_web",
                "name": "Ciberseguridad Web",
                "goal": "IDOR/XSS/SQLi/SSRF practicados; base para huntr + bug bounty",
                "resources": [
                    {
                        "title": "PortSwigger Web Security Academy (gratis)",
                        "url": "https://portswigger.net/web-security",
                    },
                    {
                        "title": "OWASP Juice Shop (open source, local)",
                        "url": "https://owasp.org/www-project-juice-shop",
                    },
                    {"title": "HackTricks (gratis)", "url": "https://book.hacktricks.xyz"},
                ],
                "milestone": "Completar labs SQLi + XSS + IDOR de PortSwigger",
                "est_hours": 30,
            },
            {
                "key": "ai_engineering",
                "name": "AI Engineering",
                "goal": "RAG/agents/evals; base para Outlier/Alignerr specialist + gigs API/AI",
                "resources": [
                    {"title": "Hugging Face NLP course (gratis)", "url": "https://huggingface.co/learn/nlp-course"},
                    {"title": "LangChain docs + Cookbook (gratis)", "url": "https://python.langchain.com"},
                    {"title": "Ollama local + qwen2.5 (gratis, offline)", "url": "https://ollama.com"},
                ],
                "milestone": "RAG local funcionando con Ollama + 1 eval propio",
                "est_hours": 25,
            },
        ],
        "routine": "30-45 min/día, 1 track a la vez; milestone antes de cambiar. Job search: /api/local-jobs/search + /api/applications/plan en paralelo.",
        "job_search": {
            "local": "GET /api/local-jobs/search?query=junior&zone=Zona+Sur (Zonajobs/Bumeran/Computrabajo read-only)",
            "platforms": "GET /api/applications/plan (Outlier/Mercor/Alignerr/Mindrift/Fiverr)",
            "rule": "30 min búsqueda + 30 min estudio/día; registrar todo en Project OS",
        },
    }


_singleton: ApplicationAssistant | None = None


def get_application_assistant() -> ApplicationAssistant:
    global _singleton
    if _singleton is None:
        _singleton = ApplicationAssistant()
    return _singleton
