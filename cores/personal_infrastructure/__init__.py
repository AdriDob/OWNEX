"""Personal Infrastructure Manager - Core Module.

Este módulo gestiona la infraestructura personal del usuario de forma permanente,
no solo durante el setup inicial. Es el asistente experto que entiende objetivos
humanos y los traduce en configuraciones técnicas.

Core Philosophy:
- El usuario nunca debería preguntarse "¿qué cuenta necesito crear?"
- OWNEX responde antes: "Para este objetivo necesitamos estas cuentas, por estas razones"
- Guía paso a paso desde cero hasta infraestructura profesional completa
- Explica cada paso en lenguaje accesible
- Automatiza todo lo posible sin comprometer seguridad
"""

from cores.personal_infrastructure.manager import PersonalInfrastructureManager
from cores.personal_infrastructure.models import (
    AccountIntegration,
    ApprovalCategory,
    IntegrationHealth,
    LearningExplanation,
    ObjectiveCategory,
    ObjectiveDefinition,
    ObjectiveProgress,
)

__all__ = [
    "PersonalInfrastructureManager",
    "AccountIntegration",
    "ApprovalCategory",
    "IntegrationHealth",
    "LearningExplanation",
    "ObjectiveCategory",
    "ObjectiveDefinition",
    "ObjectiveProgress",
]