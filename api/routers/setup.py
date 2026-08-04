"""API Router for Personalization Wizard."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.setup.steps.personalization_step import personalization_step

router = APIRouter(prefix="/api/setup", tags=["setup"])


class PersonalizationRequest(BaseModel):
    """Request model for personalization."""

    use_case: str
    modules: list[str] = []
    custom_name: str = ""
    expertise_level: str = "intermediate"
    primary_platforms: list[str] = ["all"]


@router.post("/personalization")
async def run_personalization(request: PersonalizationRequest):
    """Run the personalization step with user preferences."""
    try:
        result = personalization_step(
            {
                "use_case": request.use_case,
                "modules": request.modules,
                "custom_name": request.custom_name,
                "expertise_level": request.expertise_level,
                "primary_platforms": request.primary_platforms,
            }
        )

        if result["status"] == "ok":
            return {"success": True, "message": result["message"], "data": result["data"]}
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Personalization failed"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/personalization/default-modules/{use_case}")
async def get_default_modules(use_case: str):
    """Get default modules for a specific use case."""
    from cores.setup.steps.personalization_step import _get_default_modules_for_use_case

    modules = _get_default_modules_for_use_case(use_case)
    return {"use_case": use_case, "default_modules": modules}


@router.get("/personalization/use-cases")
async def get_use_cases():
    """Get all available use cases."""
    use_cases = [
        {"id": "bug_bounty_researcher", "title": "Bug Bounty Researcher", "description": "Investigación individual"},
        {"id": "bug_bounty_company", "title": "Bug Bounty Company", "description": "Gestión empresarial"},
        {
            "id": "cybersecurity_consultant",
            "title": "Cybersecurity Consultant",
            "description": "Consultoría de seguridad",
        },
        {"id": "penetration_tester", "title": "Penetration Tester", "description": "Testing profesional"},
        {"id": "security_analyst", "title": "Security Analyst", "description": "Análisis de seguridad"},
        {"id": "developer", "title": "Developer", "description": "Desarrollo seguro"},
        {"id": "researcher", "title": "Researcher", "description": "Investigación"},
        {"id": "hobbyist", "title": "Hobbyist", "description": "Aprendizaje personal"},
        {"id": "other", "title": "Otro", "description": "Uso personalizado"},
    ]
    return {"use_cases": use_cases}


@router.get("/personalization/modules")
async def get_available_modules():
    """Get all available modules."""
    modules = [
        {"id": "forge", "title": "Forge", "description": "Automatización de búsqueda"},
        {"id": "pulse", "title": "Pulse", "description": "Monitoreo de targets"},
        {"id": "vault", "title": "Vault", "description": "Gestión financiera"},
        {"id": "atlas", "title": "Atlas", "description": "Colaboración"},
        {"id": "security", "title": "Security", "description": "Herramientas de seguridad"},
        {"id": "copilot", "title": "Copilot", "description": "Asistente IA"},
        {"id": "analytics", "title": "Analytics", "description": "Análisis y métricas"},
        {"id": "reports", "title": "Reports", "description": "Generación de reportes"},
        {"id": "targets", "title": "Targets", "description": "Gestión de objetivos"},
        {"id": "integrations", "title": "Integrations", "description": "Integraciones externas"},
    ]
    return {"modules": modules}


@router.get("/personalization/platforms")
async def get_available_platforms():
    """Get all available platforms."""
    platforms = [
        {"id": "hackerone", "title": "HackerOne", "description": "Plataforma más grande"},
        {"id": "bugcrowd", "title": "Bugcrowd", "description": "Programas diversos"},
        {"id": "intigriti", "title": "Intigriti", "description": "Plataforma europea"},
        {"id": "yeswehack", "title": "YesWeHack", "description": "Plataforma francesa"},
        {"id": "synack", "title": "Synack", "description": "Crowdsec elite"},
    ]
    return {"platforms": platforms}
