"""ASSET_FACTORY models — activos digitales reutilizables."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class AssetType(StrEnum):
    MICRO_SAAS = "micro_saas"
    API = "api"
    DEV_TOOL = "dev_tool"
    PLUGIN = "plugin"
    EXTENSION = "extension"
    TEMPLATE = "template"
    AUTOMATION_KIT = "automation_kit"
    DIGITAL_PRODUCT = "digital_product"
    DATASET = "dataset"
    LICENSING = "licensing"


class AssetStatus(StrEnum):
    IDEA = "idea"  # problema→oportunidad detectada, sin validar
    VALIDATING = "validating"  # validando 9 criterios gate
    BUILDING = "building"  # BUILD
    PUBLISHED = "published"  # PUBLISH
    TRACTION = "traction"  # ACQUIRE USERS — usuarios reales
    MONETIZING = "monetizing"  # SUBSCRIBE/PAY — primer $ recurrente
    SCALING = "scaling"  # SUPPORT→IMPROVE — crece con cada iteración
    ARCHIVED = "archived"  # no pasó gate o sin tracción medible


# 9 criterios obligatorios antes de BUILD — si uno falla → ARCHIVED
GATE_CRITERIA = [
    "demanda_observable",  # evidencia de búsqueda/pago, no "parece buena idea"
    "costo_inicial_0",  # CPU local + tiers gratis
    "capacidad_tecnica",  # ya sabés construirlo
    "distribucion_gratuita",  # orgánica, sin ads pagos
    "margen_alto",  # >70% tras costos
    "potencial_recurrente",  # suscripción/licencia, no 1 pago
    "automatizable",  # soporte/entrega sin tu tiempo 1:1
    "tiempo_razonable",  # MVP en días/semanas, no meses
    "riesgo_aceptable",  # no requiere permisos críticos ni apuestas binarias
]


@dataclass(slots=True)
class Asset:
    """Un activo digital del factory: construir 1 vez → vender N veces."""

    asset_id: str
    title: str
    asset_type: AssetType
    description: str = ""
    status: AssetStatus = AssetStatus.IDEA
    problem: str = ""  # qué dolor resuelve (observable)
    evidence_url: str = ""  # link a demanda observable (search, issue, ranking)
    gate: dict[str, bool] = field(default_factory=dict)  # 9 criterios → bool
    gate_notes: dict[str, str] = field(default_factory=dict)
    distribution_channel: str = "organica_gratuita"
    revenue_model: str = "suscripcion"  # suscripcion | licencia | pago_unico | sponsorship | revenue_share
    human_hours_est: float = 8.0
    human_hours_actual: float = 0.0
    builds_on_ownex: bool = True  # reutiliza infra OWNEX
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    # Métricas post-publish (0 = aún no medido, nunca inventado)
    users: int = 0
    mrr_usd: float = 0.0  # monthly recurring revenue
    sales_count: int = 0
    revenue_total_usd: float = 0.0

    @property
    def gate_passed(self) -> bool:
        if not self.gate:
            return False
        return all(self.gate.get(c, False) for c in GATE_CRITERIA)

    @property
    def gate_score(self) -> float:
        if not self.gate:
            return 0.0
        return sum(1 for c in GATE_CRITERIA if self.gate.get(c, False)) / len(GATE_CRITERIA)

    @property
    def repeatability(self) -> float:
        """0-1: qué tan repetible es el ingreso. Solo >0 cuando hay ventas reales."""
        if self.sales_count <= 0 and self.mrr_usd <= 0:
            return 0.0
        # 1 venta = 0.3, 10 ventas o MRR>0 = 0.8, 100 ventas+MRR = 1.0
        if self.mrr_usd > 0 and self.sales_count >= 10:
            return 1.0
        if self.mrr_usd > 0 or self.sales_count >= 10:
            return 0.8
        return 0.3

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "title": self.title,
            "asset_type": self.asset_type.value,
            "description": self.description,
            "status": self.status.value,
            "problem": self.problem,
            "evidence_url": self.evidence_url,
            "gate": self.gate,
            "gate_notes": self.gate_notes,
            "gate_passed": self.gate_passed,
            "gate_score": round(self.gate_score, 2),
            "distribution_channel": self.distribution_channel,
            "revenue_model": self.revenue_model,
            "human_hours_est": self.human_hours_est,
            "human_hours_actual": self.human_hours_actual,
            "builds_on_ownex": self.builds_on_ownex,
            "users": self.users,
            "mrr_usd": self.mrr_usd,
            "sales_count": self.sales_count,
            "revenue_total_usd": self.revenue_total_usd,
            "repeatability": round(self.repeatability, 2),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
