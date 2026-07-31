"""Integration Health Center - Centro de Salud de Integraciones.

Monitorea el estado de todas las integraciones del usuario y proporciona
acciones recomendadas para mantener la infraestructura saludable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from cores.personal_infrastructure.manager import get_personal_infrastructure_manager
from cores.personal_infrastructure.models import IntegrationHealth

logger = logging.getLogger("ownex.personal_infrastructure.health_center")


class IntegrationHealthCenter:
    """Centro de salud de integraciones."""

    def __init__(self):
        self.manager = get_personal_infrastructure_manager()

    def get_health_overview(self) -> dict[str, Any]:
        """Obtener visión general de salud de integraciones."""
        integrations = self.manager.integrations

        health_summary = {
            "total": len(integrations),
            "connected": 0,
            "pending_auth": 0,
            "not_configured": 0,
            "error": 0,
            "deprecated": 0,
        }

        for integ in integrations.values():
            health_summary[integ.health.value] += 1

        # Calcular score de salud (0-100)
        connected_count = health_summary["connected"]
        total_count = health_summary["total"]
        health_score = (connected_count / total_count * 100) if total_count > 0 else 0

        return {
            "health_score": health_score,
            "summary": health_summary,
            "integrations": self._get_detailed_health(),
            "last_updated": datetime.now().isoformat(),
        }

    def _get_detailed_health(self) -> dict[str, dict[str, Any]]:
        """Obtener detalles de salud de cada integración."""
        detailed = {}

        for int_id, integ in self.manager.integrations.items():
            detailed[int_id] = {
                "name": integ.name,
                "category": integ.category.value,
                "purpose": integ.purpose,
                "health": integ.health.value,
                "last_sync": integ.last_sync.isoformat() if integ.last_sync else None,
                "connection_type": integ.connection_type,
                "risks": integ.risks,
                "recommended_actions": integ.recommended_actions,
                "needs_attention": self._needs_attention(integ),
            }

        return detailed

    def _needs_attention(self, integ) -> bool:
        """Determinar si una integración necesita atención."""
        if integ.health in [IntegrationHealth.ERROR, IntegrationHealth.DEPRECATED]:
            return True

        if integ.health == IntegrationHealth.PENDING_AUTH:
            return True

        # Si no se sincronizó en los últimos 30 días
        if integ.last_sync:
            days_since_sync = (datetime.now() - integ.last_sync).days
            if days_since_sync > 30:
                return True

        return False

    def get_integrations_needing_attention(self) -> list[dict[str, Any]]:
        """Obtener integraciones que necesitan atención."""
        needing_attention = []

        for int_id, integ in self.manager.integrations.items():
            if self._needs_attention(integ):
                needing_attention.append({
                    "integration_id": int_id,
                    "name": integ.name,
                    "health": integ.health.value,
                    "reason": self._get_attention_reason(integ),
                    "recommended_action": self._get_recommended_action(integ),
                })

        return needing_attention

    def _get_attention_reason(self, integ) -> str:
        """Obtener razón por la que necesita atención."""
        if integ.health == IntegrationHealth.ERROR:
            return "La integración tiene errores de conexión"
        if integ.health == IntegrationHealth.DEPRECATED:
            return "La integración está deprecada y debe actualizarse"
        if integ.health == IntegrationHealth.PENDING_AUTH:
            return "La integración requiere autorización del usuario"
        if integ.last_sync:
            days_since_sync = (datetime.now() - integ.last_sync).days
            if days_since_sync > 30:
                return f"No se sincroniza hace {days_since_sync} días"
        return "Requiere revisión"

    def _get_recommended_action(self, integ) -> str:
        """Obtener acción recomendada."""
        if integ.health == IntegrationHealth.ERROR:
            return "Reautenticar la integración"
        if integ.health == IntegrationHealth.DEPRECATED:
            return "Migrar a versión actualizada"
        if integ.health == IntegrationHealth.PENDING_AUTH:
            return "Completar proceso de autorización"
        if integ.last_sync:
            days_since_sync = (datetime.now() - integ.last_sync).days
            if days_since_sync > 30:
                return "Sincronizar manualmente"
        return "Revisar configuración"

    def update_integration_health(self, integration_id: str, health: IntegrationHealth, last_sync: datetime | None = None) -> bool:
        """Actualizar estado de salud de una integración."""
        if integration_id not in self.manager.integrations:
            return False

        self.manager.integrations[integration_id].health = health
        if last_sync:
            self.manager.integrations[integration_id].last_sync = last_sync

        self.manager._save_data()
        return True

    def run_health_check(self) -> dict[str, Any]:
        """Ejecutar check de salud completo."""
        health_overview = self.get_health_overview()
        needing_attention = self.get_integrations_needing_attention()

        return {
            "health_overview": health_overview,
            "needing_attention": needing_attention,
            "attention_count": len(needing_attention),
            "overall_status": "healthy" if len(needing_attention) == 0 else "needs_attention",
            "checked_at": datetime.now().isoformat(),
        }

    def get_health_score_by_category(self) -> dict[str, float]:
        """Obtener score de salud por categoría."""
        categories = {}

        for integ in self.manager.integrations.values():
            category = integ.category.value
            if category not in categories:
                categories[category] = {"total": 0, "connected": 0}

            categories[category]["total"] += 1
            if integ.health == IntegrationHealth.CONNECTED:
                categories[category]["connected"] += 1

        scores = {}
        for category, data in categories.items():
            score = (data["connected"] / data["total"] * 100) if data["total"] > 0 else 0
            scores[category] = score

        return scores


# Singleton instance
_integration_health_center: IntegrationHealthCenter | None = None


def get_integration_health_center() -> IntegrationHealthCenter:
    """Obtener instancia singleton del Integration Health Center."""
    global _integration_health_center
    if _integration_health_center is None:
        _integration_health_center = IntegrationHealthCenter()
    return _integration_health_center


def reset_integration_health_center() -> None:
    """Resetear instancia singleton."""
    global _integration_health_center
    _integration_health_center = None