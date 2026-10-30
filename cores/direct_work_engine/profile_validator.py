"""Profile Completeness Validator — scores profile quality 0-100 for freelance platforms."""

from __future__ import annotations

from dataclasses import dataclass

from cores.direct_work_engine.models import UserProfile


@dataclass
class CompletenessCheck:
    """A single completeness check with weight and result."""

    name: str
    weight: float
    passed: bool
    message: str = ""


@dataclass
class CompletenessResult:
    """Result of profile completeness validation."""

    score: int  # 0-100
    passed: bool
    checks: list[CompletenessCheck]
    missing_critical: list[str]
    recommendations: list[str]

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def total_weight(self) -> float:
        return sum(c.weight for c in self.checks)


class ProfileCompletenessValidator:
    """Validates UserProfile completeness for freelance platforms.

    Scores 0-100 based on weighted checks. Platform-specific rules:
    - Fiverr: title, description, skills, portfolio, FAQ, pricing
    - Freelancer: headline, overview, skills, portfolio, experience, certifications
    - LinkedIn: headline, summary, experience, skills, projects, about
    - Bug Bounty: bio, specialty, languages, availability
    """

    def __init__(self) -> None:
        pass

    def validate(self, profile: UserProfile, platform: str = "fiverr") -> CompletenessResult:
        """Validate profile for a specific platform."""
        checks: list[CompletenessCheck] = []

        if platform in ("fiverr", "freelancer", "toptal"):
            checks.extend(self._check_freelance_core(profile, platform))
            checks.extend(self._check_freelance_platform_specific(profile, platform))
        elif platform == "linkedin":
            checks.extend(self._check_linkedin(profile))
        elif platform in ("hackerone", "bugcrowd", "intigriti", "yeswehack"):
            checks.extend(self._check_bug_bounty(profile))
        elif platform in ("outlier", "mindrift", "alignerr", "mercor"):
            checks.extend(self._check_ai_training(profile))
        else:
            checks.extend(self._check_freelance_core(profile, platform))

        # Calculate weighted score
        total_weight = sum(c.weight for c in checks)
        earned_weight = sum(c.weight for c in checks if c.passed)
        score = round((earned_weight / total_weight) * 100) if total_weight > 0 else 0

        # Critical missing items (weight >= 10)
        missing_critical = [c.name for c in checks if not c.passed and c.weight >= 10]

        # Recommendations
        recommendations = [c.message for c in checks if not c.passed and c.message]

        return CompletenessResult(
            score=score,
            passed=score >= 70,  # Minimum viable profile
            checks=checks,
            missing_critical=missing_critical,
            recommendations=recommendations,
        )

    def _check_freelance_core(self, profile: UserProfile, platform: str) -> list[CompletenessCheck]:
        """Core checks for all freelance platforms."""
        return [
            CompletenessCheck(
                name="name",
                weight=10,
                passed=bool(profile.name and profile.name.strip()),
                message="Agregá tu nombre completo",
            ),
            CompletenessCheck(
                name="country",
                weight=5,
                passed=bool(profile.country and profile.country.strip()),
                message="Agregá tu país de residencia",
            ),
            CompletenessCheck(
                name="skills",
                weight=20,
                passed=len(profile.skills) >= 5,
                message=f"Tenés {len(profile.skills)} skills — necesitás al menos 5 relevantes para tu nicho",
            ),
            CompletenessCheck(
                name="languages",
                weight=5,
                passed=len(profile.languages) >= 1,
                message="Agregá al menos un idioma (español nativo + inglés profesional ideal)",
            ),
            CompletenessCheck(
                name="availability_hours",
                weight=5,
                passed=profile.availability_hours > 0,
                message="Definí cuántas horas/semana podés trabajar",
            ),
            CompletenessCheck(
                name="experience_level",
                weight=10,
                passed=profile.experience_level is not None,
                message="Seleccioná tu nivel de experiencia (entrada/junior/mid/senior)",
            ),
        ]

    def _check_freelance_platform_specific(self, profile: UserProfile, platform: str) -> list[CompletenessCheck]:
        """Platform-specific checks."""
        checks = []

        if platform == "fiverr":
            checks.extend(
                [
                    CompletenessCheck(
                        name="fiverr_title",
                        weight=10,
                        passed=bool(profile.name),
                        message="El título del gig usa tu nombre + skill principal + país",
                    ),
                    CompletenessCheck(
                        name="fiverr_skills_detail",
                        weight=10,
                        passed=len(profile.skills) >= 3,
                        message="Describí 3+ skills principales en la descripción del gig",
                    ),
                    CompletenessCheck(
                        name="fiverr_pricing",
                        weight=10,
                        passed=True,  # Always passes - generated from profile
                        message="Los 3 paquetes (Starter/Standard/Premium) se generan automáticamente",
                    ),
                    CompletenessCheck(
                        name="fiverr_faq",
                        weight=5,
                        passed=True,
                        message="FAQ se genera automáticamente desde tu perfil",
                    ),
                ]
            )

        elif platform == "freelancer":
            checks.extend(
                [
                    CompletenessCheck(
                        name="freelancer_headline",
                        weight=15,
                        passed=bool(profile.name and profile.skills),
                        message="Headline = nombre + top 3 skills + nivel + país",
                    ),
                    CompletenessCheck(
                        name="freelancer_overview",
                        weight=15,
                        passed=bool(profile.skills),
                        message="Overview completo con stack, especialidad, disponibilidad, pago",
                    ),
                    CompletenessCheck(
                        name="freelancer_portfolio",
                        weight=15,
                        passed=len(profile.projects) >= 3,
                        message=f"Tenés {len(profile.projects)} proyectos — necesitás 3+ case studies",
                    ),
                    CompletenessCheck(
                        name="freelancer_experience",
                        weight=10,
                        passed=len(profile.projects) > 0 or profile.experience_level != "none",
                        message="Experiencia: agregá proyectos o experiencia real",
                    ),
                    CompletenessCheck(
                        name="freelancer_certifications",
                        weight=10,
                        passed=bool(profile.skills),
                        message="Certificaciones se generan desde tus skills (ej: Python, Go, Security)",
                    ),
                    CompletenessCheck(
                        name="freelancer_links",
                        weight=5,
                        passed=bool(profile.github_url or profile.linkedin_url or profile.portfolio_url),
                        message="Agregá GitHub, LinkedIn o portfolio URL",
                    ),
                ]
            )

        elif platform == "toptal":
            checks.extend(
                [
                    CompletenessCheck(
                        name="toptal_headline",
                        weight=15,
                        passed=bool(profile.name and profile.skills),
                        message="Headline = nombre + top 3 skills + nivel + país",
                    ),
                    CompletenessCheck(
                        name="toptal_overview",
                        weight=15,
                        passed=bool(profile.skills),
                        message="Overview completo con stack, especialidad, disponibilidad, pago",
                    ),
                    CompletenessCheck(
                        name="toptal_portfolio",
                        weight=20,
                        passed=len(profile.projects) >= 5,
                        message=f"Tenés {len(profile.projects)} proyectos — Toptal exige 5+ case studies de alta calidad",
                    ),
                    CompletenessCheck(
                        name="toptal_experience",
                        weight=15,
                        passed=profile.experience_level in ("mid", "senior"),
                        message="Toptal requiere nivel mid/senior (3+ años experiencia verificada)",
                    ),
                    CompletenessCheck(
                        name="toptal_skills",
                        weight=15,
                        passed=len(profile.skills) >= 8,
                        message="Toptal exige 8+ skills técnicos verificables",
                    ),
                    CompletenessCheck(
                        name="toptal_english",
                        weight=10,
                        passed="en" in profile.languages,
                        message="Inglés fluido obligatorio para Toptal (entrevista en inglés)",
                    ),
                    CompletenessCheck(
                        name="toptal_links",
                        weight=5,
                        passed=bool(profile.github_url or profile.linkedin_url or profile.portfolio_url),
                        message="Agregá GitHub, LinkedIn o portfolio URL",
                    ),
                ]
            )

        elif platform == "linkedin":
            checks.extend(
                [
                    CompletenessCheck(
                        name="linkedin_headline",
                        weight=15,
                        passed=bool(profile.name and profile.skills),
                        message="Headline = nombre + país + top 3 skills",
                    ),
                    CompletenessCheck(
                        name="linkedin_about",
                        weight=15,
                        passed=True,
                        message="About completo se genera desde perfil",
                    ),
                    CompletenessCheck(
                        name="linkedin_experience",
                        weight=15,
                        passed=len(profile.projects) > 0,
                        message="Agregá experiencia laboral con bullets",
                    ),
                    CompletenessCheck(
                        name="linkedin_skills",
                        weight=10,
                        passed=len(profile.skills) >= 5,
                        message="Al menos 5 skills listadas",
                    ),
                    CompletenessCheck(
                        name="linkedin_projects",
                        weight=10,
                        passed=len(profile.projects) >= 3,
                        message=f"Tenés {len(profile.projects)} proyectos — necesitás 3+ destacados",
                    ),
                    CompletenessCheck(
                        name="linkedin_featured",
                        weight=5,
                        passed=len(profile.projects) > 0 or bool(profile.github_url),
                        message="Sección Featured: proyectos + GitHub + portfolio",
                    ),
                ]
            )

        elif platform == "bug_bounty":
            checks.extend(
                [
                    CompletenessCheck(
                        name="bio",
                        weight=15,
                        passed=bool(profile.skills),
                        message="Bio técnico con skills principales",
                    ),
                    CompletenessCheck(
                        name="specialty",
                        weight=15,
                        passed=len(profile.skills) >= 3,
                        message="Especialidad: top 3-5 skills de seguridad",
                    ),
                    CompletenessCheck(
                        name="languages",
                        weight=10,
                        passed=len(profile.languages) >= 2,
                        message="Idiomas: español nativo + inglés profesional",
                    ),
                    CompletenessCheck(
                        name="availability",
                        weight=10,
                        passed=profile.availability_hours >= 20,
                        message="Disponibilidad realista (20+ h/sem para bug bounty serio)",
                    ),
                ]
            )

        elif platform == "ai_training":
            checks.extend(
                [
                    CompletenessCheck(
                        name="skills",
                        weight=20,
                        passed=any(
                            s in profile.skills
                            for s in ("python", "go", "typescript", "javascript", "rust", "c++", "java")
                        ),
                        message="Necesitás al menos un lenguaje de programación principal",
                    ),
                    CompletenessCheck(
                        name="languages",
                        weight=15,
                        passed="es" in profile.languages and "en" in profile.languages,
                        message="Español nativo + inglés profesional obligatorio",
                    ),
                    CompletenessCheck(
                        name="experience",
                        weight=10,
                        passed=profile.experience_level != "none",
                        message="Nivel de experiencia requerido para assessment",
                    ),
                ]
            )

        return checks

    def _check_linkedin(self, profile: UserProfile) -> list[CompletenessCheck]:
        """LinkedIn-specific completeness checks."""
        return self._check_freelance_platform_specific(profile, "linkedin")

    def _check_bug_bounty(self, profile: UserProfile) -> list[CompletenessCheck]:
        """Bug bounty platform checks."""
        return self._check_freelance_platform_specific(profile, "bug_bounty")

    def _check_ai_training(self, profile: UserProfile) -> list[CompletenessCheck]:
        """AI training platform checks."""
        return self._check_freelance_platform_specific(profile, "ai_training")


# Convenience function
_validator: ProfileCompletenessValidator | None = None


def get_profile_validator() -> ProfileCompletenessValidator:
    global _validator
    if _validator is None:
        _validator = ProfileCompletenessValidator()
    return _validator
