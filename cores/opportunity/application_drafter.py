"""Application drafter — template-based drafts from REAL profile data only.

Produces draft artifacts (profile summary, cover letter, gap notes) for a
tracked job. NEVER invents experience, skills, or achievements: every sentence
is built strictly from fields present in the user profile. Output is always a
DRAFT requiring human approval before any submission.
"""

from __future__ import annotations

from typing import Any

from cores.opportunity.job_tracker import gap_analysis


def draft_application(job: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Build draft artifacts. Returns {drafts, gaps, requires_approval: True}."""
    gaps = gap_analysis(job, profile)
    name = profile.get("name") or profile.get("full_name") or "[TU NOMBRE]"
    headline = profile.get("headline") or profile.get("title") or ""
    skills = [str(s) for s in (profile.get("skills") or [])]
    exp_years = profile.get("experience_years") or 0
    summary_bits = [b for b in [headline, f"{exp_years} años de experiencia" if exp_years else "", ", ".join(skills[:6])] if b]

    cover = (
        f"Estimado/a equipo de {job.get('company') or '[EMPRESA]'}:\n\n"
        f"Me postulo para {job.get('title') or '[CARGO]'}. "
        + (f"{summary_bits[0]}. " if summary_bits else "")
        + (f"Mi perfil incluye: {', '.join(skills[:5])}. " if skills else "")
        + "Adjunto mi CV para más detalle. Quedo atento/a a cualquier prueba o entrevista.\n\n"
        "Saludos,\n" + name
    )

    return {
        "requires_approval": True,
        "disclaimer": "Borrador generado solo con datos reales del perfil. Revisar y completar antes de enviar.",
        "cover_letter": cover,
        "profile_summary": {
            "name": name,
            "headline": headline,
            "skills": skills,
            "experience_years": exp_years,
            "matched_skills": gaps["matched_skills"],
        },
        "gaps_to_address": gaps["gaps"],
        "job": {"title": job.get("title"), "company": job.get("company"), "url": job.get("url")},
    }
