"""Profile Kit — pre-prepared professional copy for each platform.

Generates ready-to-copy text for profile sections (bio, skills, FAQ, headline, etc.)
per platform, with bilingual support (ES default, EN fallback).

Zero invented data. Every field is derived from the real profile or defaults.

Pattern: data_dir = Path(__file__).resolve().parents[3] / "data" / "profile_kit.json"
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from cores.direct_work_engine.models import ExperienceLevel, UserProfile

logger = logging.getLogger("ownex.profile_kit")

_DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data" / "profile_kit.json"
_DEFAULT_PROFILE: dict[str, Any] = {
    "name": "",
    "tagline": "",
    "city": "",
    "country": "Argentina",
    "languages": [],
    "skills": [],
    "experience_level": "none",
    "github_url": "",
    "linkedin_url": "",
    "portfolio_url": "",
    "focus_bullets": [],
    "current_focus": "bug bounty",
    "availability_hours": 40.0,
    "credentials": [],
    "platforms_ready": [],
}


_BB_PLATFORMS = ("hackerone", "bugcrowd", "intigriti", "yeswehack")

_BB_METHODS: dict[str, dict[str, str]] = {
    "hackerone": {
        "bio": "_hackerone_bio",
        "specialty": "_hackerone_specialty",
        "languages": "_hackerone_languages",
        "availability": "_hackerone_availability",
    },
    "bugcrowd": {
        "bio": "_bugcrowd_bio",
        "specialty": "_bugcrowd_specialty",
        "languages": "_bugcrowd_languages",
        "availability": "_bugcrowd_availability",
    },
    "intigriti": {
        "bio": "_intigriti_bio",
        "specialty": "_intigriti_specialty",
        "languages": "_intigriti_languages",
        "availability": "_intigriti_availability",
    },
    "yeswehack": {
        "bio": "_yeswehack_bio",
        "specialty": "_yeswehack_specialty",
        "languages": "_yeswehack_languages",
        "availability": "_yeswehack_availability",
    },
}


class ProfileKitEngine:
    """Generates and persists platform-ready profile copy."""

    def __init__(self) -> None:
        self.data_dir = _DATA_DIR.parent
        self.data_path = _DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self._loaded: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.data_path, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _save_data(data: dict[str, Any], path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save(self, profile: dict[str, Any]) -> dict[str, Any]:
        self._loaded = profile
        self._save_data(profile, self.data_path)
        return profile

    def load(self) -> dict[str, Any]:
        if self._loaded is None:
            self._loaded = self._load()
        return self._loaded

    def has_profile(self) -> bool:
        return bool(self.load())

    def get(self) -> dict[str, Any]:
        return self.load()

    def platforms(self) -> list[str]:
        return list(self._platform_templates().keys())

    def default_profile(self) -> dict[str, Any]:
        return dict(_DEFAULT_PROFILE)

    @staticmethod
    def profile_from_dict(data: dict[str, Any]) -> UserProfile:
        """Convert a dict profile into a typed UserProfile (safe for partial payloads)."""
        skills = set(data.get("skills") or [])
        languages = set(data.get("languages") or [])
        experience = data.get("experience_level") or ExperienceLevel.NONE.value
        try:
            experience_level = ExperienceLevel(experience)
        except ValueError:
            experience_level = ExperienceLevel.NONE
        return UserProfile(
            name=str(data.get("name", "")),
            country=str(data.get("country", "Argentina")),
            languages=languages,
            skills=skills,
            experience_level=experience_level,
            availability_hours=float(data.get("availability_hours", 40.0)),
            github_url=str(data.get("github_url", "")),
            linkedin_url=str(data.get("linkedin_url", "")),
            portfolio_url=str(data.get("portfolio_url", "")),
            projects=list(data.get("projects") or []),
        )

    # ── Generación ──

    def generate(self, profile: UserProfile) -> dict[str, dict[str, list[dict[str, str]]]]:
        """Generates platform copy for every language (es / en).

        Returns: {lang: {platform: [Field{key, label, text}]}}.
        """
        result: dict[str, dict[str, list[dict[str, str]]]] = {}
        for lang in ["es", "en"]:
            result[lang] = {}
            for platform, template in self._platform_templates().items():
                result[lang][platform] = self._generate_fields(profile, platform, lang, template)
        return result

    def _platform_templates(self) -> dict[str, dict[str, Any]]:
        return {
            "fiverr": {
                "label_keys": ["title", "description", "ask", "faq"],
                "field_keys": ["title", "description", "ask", "faq"],
            },
            "github": {
                "label_keys": ["bio", "skills", "projects", "links"],
                "field_keys": ["bio", "skills", "projects", "links"],
            },
            "hackerone": {
                "label_keys": ["bio", "specialty", "languages", "availability"],
                "field_keys": ["bio", "specialty", "languages", "availability"],
            },
            "bugcrowd": {
                "label_keys": ["bio", "specialty", "languages", "availability"],
                "field_keys": ["bio", "specialty", "languages", "availability"],
            },
            "intigriti": {
                "label_keys": ["bio", "specialty", "languages", "availability"],
                "field_keys": ["bio", "specialty", "languages", "availability"],
            },
            "yeswehack": {
                "label_keys": ["bio", "specialty", "languages", "availability"],
                "field_keys": ["bio", "specialty", "languages", "availability"],
            },
            "opire": {
                "label_keys": ["bio", "skills", "projects", "links"],
                "field_keys": ["bio", "skills", "projects", "links"],
            },
            "issuehunt": {
                "label_keys": ["bio", "skills", "projects", "links"],
                "field_keys": ["bio", "skills", "projects", "links"],
            },
            "algora": {
                "label_keys": ["bio", "skills", "projects", "links"],
                "field_keys": ["bio", "skills", "projects", "links"],
            },
            "outlier": {
                "label_keys": ["bio", "skills", "availability"],
                "field_keys": ["bio", "skills", "availability"],
            },
            "mindrift": {
                "label_keys": ["bio", "skills", "availability"],
                "field_keys": ["bio", "skills", "availability"],
            },
            "linkedin": {
                "label_keys": ["headline", "summary", "skills", "projects"],
                "field_keys": ["headline", "summary", "skills", "projects"],
            },
        }

    def _generate_fields(
        self,
        profile: UserProfile,
        platform: str,
        lang: str,
        template: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Generate field list for a platform/language."""
        fields: list[dict[str, str]] = []

        if not platform:
            return fields

        lang_label = "ES" if lang == "es" else "EN"

        # ── Header ──
        name = profile.name or "Desarrollador"
        top_skill = next(iter(profile.skills)) if profile.skills else "Full-stack"
        fields.append(
            {
                "key": "header",
                "label": f"Perfil {lang_label}",
                "text": self._header(name, profile.country, top_skill),
            }
        )

        # ── Descripción ──
        if platform == "fiverr":
            fields.append({"key": "fiverr_title", "label": "Título del gig", "text": self._fiverr_title(profile)})
            fields.append(
                {"key": "fiverr_description", "label": "Descripción", "text": self._fiverr_description(profile, lang)}
            )
            fields.append(
                {"key": "fiverr_ask", "label": "Preguntas frecuentes", "text": self._fiverr_ask(profile, lang)}
            )
            fields.append({"key": "fiverr_faq", "label": "FAQ", "text": self._fiverr_faq(profile, lang)})
        elif platform == "github":
            fields.append({"key": "github_bio", "label": "Bio", "text": self._github_bio(profile)})
            fields.append({"key": "github_skills", "label": "Stack técnico", "text": self._github_skills(profile)})
            fields.append(
                {"key": "github_projects", "label": "Proyectos destacados", "text": self._github_projects(profile)}
            )
            fields.append({"key": "github_links", "label": "Enlaces", "text": self._github_links(profile)})
        elif platform in _BB_PLATFORMS:
            field_types = (
                ("bio", "Bio profesional"),
                ("specialty", "Especialidad técnica"),
                ("languages", "Idiomas"),
                ("availability", "Disponibilidad"),
            )
            for key, label in field_types:
                method = _BB_METHODS[platform][key]
                fields.append({"key": f"{platform}_{key}", "label": label, "text": getattr(self, method)(profile)})
        elif platform == "opire":
            fields.append({"key": "opire_bio", "label": "Bio del operador", "text": self._opire_bio(profile)})
            fields.append({"key": "opire_skills", "label": "Stack técnico", "text": self._opire_skills(profile)})
            fields.append(
                {"key": "opire_projects", "label": "Proyectos destacados", "text": self._opire_projects(profile)}
            )
            fields.append({"key": "opire_links", "label": "Enlaces", "text": self._opire_links(profile)})
        elif platform == "issuehunt":
            fields.append({"key": "issuehunt_bio", "label": "Bio del operador", "text": self._issuehunt_bio(profile)})
            fields.append(
                {"key": "issuehunt_skills", "label": "Stack técnico", "text": self._issuehunt_skills(profile)}
            )
            fields.append(
                {
                    "key": "issuehunt_projects",
                    "label": "Proyectos destacados",
                    "text": self._issuehunt_projects(profile),
                }
            )
            fields.append({"key": "issuehunt_links", "label": "Enlaces", "text": self._issuehunt_links(profile)})
        elif platform == "algora":
            fields.append({"key": "algora_bio", "label": "Bio del operador", "text": self._algora_bio(profile)})
            fields.append({"key": "algora_skills", "label": "Stack técnico", "text": self._algora_skills(profile)})
            fields.append(
                {"key": "algora_projects", "label": "Proyectos destacados", "text": self._algora_projects(profile)}
            )
            fields.append({"key": "algora_links", "label": "Enlaces", "text": self._algora_links(profile)})
        elif platform == "outlier":
            fields.append({"key": "outlier_bio", "label": "Bio del operador", "text": self._outlier_bio(profile)})
            fields.append({"key": "outlier_skills", "label": "Stack técnico", "text": self._outlier_skills(profile)})
            fields.append(
                {"key": "outlier_availability", "label": "Disponibilidad", "text": self._outlier_availability(profile)}
            )
        elif platform == "mindrift":
            fields.append({"key": "mindrift_bio", "label": "Bio del operador", "text": self._mindrift_bio(profile)})
            fields.append({"key": "mindrift_skills", "label": "Stack técnico", "text": self._mindrift_skills(profile)})
            fields.append(
                {
                    "key": "mindrift_availability",
                    "label": "Disponibilidad",
                    "text": self._mindrift_availability(profile),
                }
            )
        elif platform == "linkedin":
            fields.append(
                {"key": "linkedin_headline", "label": "Headline del perfil", "text": self._linkedin_headline(profile)}
            )
            fields.append(
                {"key": "linkedin_summary", "label": "Resumen del perfil", "text": self._linkedin_summary(profile)}
            )
            fields.append({"key": "linkedin_skills", "label": "Stack técnico", "text": self._linkedin_skills(profile)})
            fields.append(
                {"key": "linkedin_projects", "label": "Proyectos destacados", "text": self._linkedin_projects(profile)}
            )

        return fields

    # ── Generadores por plataforma ──

    def _header(self, name: str, country: str, top_skill: str) -> str:
        return f"{name} — {country} — Remote — {top_skill}"

    def _fiverr_title(self, profile: UserProfile) -> str:
        if profile.skills:
            return f"{profile.name or 'Desarrollador'} — {next(iter(profile.skills))} — {profile.country}"
        return f"{profile.name or 'Desarrollador'} — Full-stack — {profile.country}"

    def _fiverr_description(self, profile: UserProfile, lang: str) -> str:
        return (
            f"Resuelvo problemas técnicos con stack {', '.join(sorted(profile.skills)[:5]) if profile.skills else 'Full-stack'} "
            f"para {profile.country}. "
            f"Experto en {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'programación y automatización'} "
            f"Con {profile.availability_hours}h/semana de disponibilidad. "
            f"Pago: transferencia bancaria (USD). "
            f"En {lang}."
        )

    @staticmethod
    def _exp_label(profile: UserProfile) -> str:
        """Label honesto del nivel: el enum no declara años, así que el copy no los inventa."""
        return {
            ExperienceLevel.NONE: "nivel entrada",
            ExperienceLevel.JUNIOR: "nivel junior",
            ExperienceLevel.MID: "nivel mid",
            ExperienceLevel.SENIOR: "nivel senior",
        }[profile.experience_level]

    def _fiverr_ask(self, profile: UserProfile, lang: str) -> str:
        return (
            f"¿Cómo iniciar?: enviá un mensaje con tu descripción y stack. "
            f"¿Qué incluye la entrega?: trabajo definido y completado. "
            f"¿Cuál es tu nivel de experiencia? {self._exp_label(profile)}. "
            f"¿Te interesa el plan Starter o Standard? (pago por el plan). "
            f"¿Recibís el resultado? → Sí, aceptamos el trabajo y lo entregamos. "
            f"¿Puede darte soporte post-entrega? → Sí. "
            f"En {lang}."
        )

    def _fiverr_faq(self, profile: UserProfile, lang: str) -> str:
        return (
            f"¿Cuánto tiempo toma un gig? → 2-4 horas. "
            f"¿Qué necesitas para empezar? → Solo describí tu proyecto y tu stack. "
            f"¿Cuál es tu nivel de experiencia? → {self._exp_label(profile)}. "
            f"¿Puede enviarte el resultado? → Sí. "
            f"¿Puede darte soporte post-entrega? → Sí. "
            f"En {lang}."
        )

    def _github_bio(self, profile: UserProfile) -> str:
        return f"{profile.name or 'Desarrollador'} — {profile.country} — {', '.join(sorted(profile.skills)[:5]) if profile.skills else 'Full-stack'} — {self._exp_label(profile)} de experiencia"

    def _github_skills(self, profile: UserProfile) -> str:
        skills = ", ".join(sorted(profile.skills)[:10]) if profile.skills else "full-stack, backend, frontend"
        return f"Stack: {skills} — {self._exp_label(profile)} de experiencia en {profile.country}"

    def _github_projects(self, profile: UserProfile) -> str:
        if profile.projects:
            return "\n".join(f"- {p}" for p in profile.projects[:5])
        return "- Sin proyectos publicados aún (creá algunos y subí el README)"

    def _github_links(self, profile: UserProfile) -> str:
        links = []
        if profile.github_url:
            links.append(f"GitHub: {profile.github_url}")
        if profile.portfolio_url:
            links.append(f"Portfolio: {profile.portfolio_url}")
        if profile.linkedin_url:
            links.append(f"LinkedIn: {profile.linkedin_url}")
        return "\n".join(links) if links else "- Sin links configurados"

    def _hackerone_bio(self, profile: UserProfile) -> str:
        return f"Desarrollador {profile.country} con expertise en {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'ciencia de datos'} — {self._exp_label(profile)} de experiencia en bug bounty."

    def _hackerone_specialty(self, profile: UserProfile) -> str:
        return f"Especialidad técnica: {', '.join(sorted(profile.skills)[:5]) if profile.skills else 'programación, APIs, seguridad'}"

    def _hackerone_languages(self, profile: UserProfile) -> str:
        return f"Idiomas: {', '.join(sorted(profile.languages))}"

    def _hackerone_availability(self, profile: UserProfile) -> str:
        return f"Disponibilidad: {profile.availability_hours}h/semana, bug bounty"

    def _bugcrowd_bio(self, profile: UserProfile) -> str:
        return f"Operador {profile.country} con expertise en {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'programación'} — {self._exp_label(profile)} en bug bounty."

    def _bugcrowd_specialty(self, profile: UserProfile) -> str:
        return f"Stack: {', '.join(sorted(profile.skills)[:5]) if profile.skills else 'Python, Go, TypeScript'}"

    def _bugcrowd_languages(self, profile: UserProfile) -> str:
        return f"Idiomas: {', '.join(sorted(profile.languages))}"

    def _bugcrowd_availability(self, profile: UserProfile) -> str:
        return f"Disponibilidad: {profile.availability_hours}h/semana"

    def _intigriti_bio(self, profile: UserProfile) -> str:
        return f"Operador {profile.country} especializado en {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'seguridad'} — {self._exp_label(profile)}."

    def _intigriti_specialty(self, profile: UserProfile) -> str:
        return (
            f"Especialidad: {', '.join(sorted(profile.skills)[:5]) if profile.skills else 'bug bounty, API, backend'}"
        )

    def _intigriti_languages(self, profile: UserProfile) -> str:
        return f"Idiomas: {', '.join(sorted(profile.languages))}"

    def _intigriti_availability(self, profile: UserProfile) -> str:
        return f"Disponibilidad: {profile.availability_hours}h/semana, bug bounty"

    def _yeswehack_bio(self, profile: UserProfile) -> str:
        return f"Operador {profile.country} con expertise en {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'seguridad'} — {self._exp_label(profile)} en bug bounty."

    def _yeswehack_specialty(self, profile: UserProfile) -> str:
        return f"Stack: {', '.join(sorted(profile.skills)[:5]) if profile.skills else 'Python, Go, TypeScript'}"

    def _yeswehack_languages(self, profile: UserProfile) -> str:
        return f"Idiomas: {', '.join(sorted(profile.languages))}"

    def _yeswehack_availability(self, profile: UserProfile) -> str:
        return f"Disponibilidad: {profile.availability_hours}h/semana"

    def _opire_bio(self, profile: UserProfile) -> str:
        return f"{profile.name or 'Desarrollador'} — {profile.country} — {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'Desarrollo de software'} — {self._exp_label(profile)}"

    def _opire_skills(self, profile: UserProfile) -> str:
        skills = ", ".join(sorted(profile.skills)[:10]) if profile.skills else "full-stack, backend, frontend"
        return f"Stack: {skills} — Disponible para bug bounty"

    def _opire_projects(self, profile: UserProfile) -> str:
        if profile.projects:
            return "\n".join(f"- {p}" for p in profile.projects[:5])
        return "- Sin proyectos publicados aún"

    def _opire_links(self, profile: UserProfile) -> str:
        links = []
        if profile.github_url:
            links.append(f"GitHub: {profile.github_url}")
        if profile.portfolio_url:
            links.append(f"Portfolio: {profile.portfolio_url}")
        if profile.linkedin_url:
            links.append(f"LinkedIn: {profile.linkedin_url}")
        return "\n".join(links) if links else "- Sin links configurados"

    def _issuehunt_bio(self, profile: UserProfile) -> str:
        return f"Operador {profile.country} en {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'programación'} — {self._exp_label(profile)} de experiencia en bug bounty."

    def _issuehunt_skills(self, profile: UserProfile) -> str:
        skills = ", ".join(sorted(profile.skills)[:10]) if profile.skills else "Python, Go, TypeScript"
        return f"Stack: {skills} — {self._exp_label(profile)} de experiencia"

    def _issuehunt_projects(self, profile: UserProfile) -> str:
        if profile.projects:
            return "\n".join(f"- {p}" for p in profile.projects[:5])
        return "- Sin proyectos publicados aún"

    def _issuehunt_links(self, profile: UserProfile) -> str:
        links = []
        if profile.github_url:
            links.append(f"GitHub: {profile.github_url}")
        if profile.linkedin_url:
            links.append(f"LinkedIn: {profile.linkedin_url}")
        return "\n".join(links) if links else "- Sin links configurados"

    def _algora_bio(self, profile: UserProfile) -> str:
        return f"{profile.name or 'Desarrollador'} — {profile.country} — {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'Backend'} — {self._exp_label(profile)}"

    def _algora_skills(self, profile: UserProfile) -> str:
        skills = ", ".join(sorted(profile.skills)[:10]) if profile.skills else "backend, APIs, Python"
        return f"Stack: {skills} — {self._exp_label(profile)} de experiencia"

    def _algora_projects(self, profile: UserProfile) -> str:
        if profile.projects:
            return "\n".join(f"- {p}" for p in profile.projects[:5])
        return "- Sin proyectos publicados aún"

    def _algora_links(self, profile: UserProfile) -> str:
        links = []
        if profile.github_url:
            links.append(f"GitHub: {profile.github_url}")
        if profile.portfolio_url:
            links.append(f"Portfolio: {profile.portfolio_url}")
        if profile.linkedin_url:
            links.append(f"LinkedIn: {profile.linkedin_url}")
        return "\n".join(links) if links else "- Sin links configurados"

    def _outlier_bio(self, profile: UserProfile) -> str:
        return f"{profile.name or 'Desarrollador'} — {profile.country} — {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'Seguridad'} — {self._exp_label(profile)}"

    def _outlier_skills(self, profile: UserProfile) -> str:
        skills = ", ".join(sorted(profile.skills)[:10]) if profile.skills else "Python, Go, Seguridad"
        return f"Stack: {skills} — {self._exp_label(profile)} de experiencia"

    def _outlier_availability(self, profile: UserProfile) -> str:
        return f"Disponibilidad: {profile.availability_hours}h/semana — bug bounty"

    def _mindrift_bio(self, profile: UserProfile) -> str:
        return f"{profile.name or 'Desarrollador'} — {profile.country} — {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'API, Backend'} — {self._exp_label(profile)}"

    def _mindrift_skills(self, profile: UserProfile) -> str:
        skills = ", ".join(sorted(profile.skills)[:10]) if profile.skills else "Python, Go, APIs"
        return f"Stack: {skills} — {self._exp_label(profile)} de experiencia"

    def _mindrift_availability(self, profile: UserProfile) -> str:
        return f"Disponibilidad: {profile.availability_hours}h/semana — bug bounty"

    def _linkedin_headline(self, profile: UserProfile) -> str:
        return f"{profile.name or 'Desarrollador'} — {profile.country} — {', '.join(sorted(profile.skills)[:3]) if profile.skills else 'Full-stack'}"

    def _linkedin_summary(self, profile: UserProfile) -> str:
        return (
            f"Profesional {profile.country} con {self._exp_label(profile)} de experiencia en "
            f"{', '.join(sorted(profile.skills)[:5]) if profile.skills else 'desarrollo full-stack'}. "
            f"Especializado en bug bounty. "
            f"Disponible para {profile.availability_hours}h/semana."
        )

    def _linkedin_skills(self, profile: UserProfile) -> str:
        skills = ", ".join(sorted(profile.skills)[:10]) if profile.skills else "Python, Go, TypeScript"
        return f"Stack: {skills} — {self._exp_label(profile)} de experiencia"

    def _linkedin_projects(self, profile: UserProfile) -> str:
        if profile.projects:
            return "\n".join(f"- {p}" for p in profile.projects[:5])
        return "- Sin proyectos publicados aún"
