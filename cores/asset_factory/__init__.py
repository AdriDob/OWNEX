"""ASSET_FACTORY — construir activos digitales que generan ingreso recurrente.

Pipeline: BUILD → PUBLISH → ACQUIRE USERS → MONETIZE → SUPPORT → IMPROVE
Filosofía: construir 1 vez → vender N veces, cada trabajo sigue produciendo valor.

9 criterios de gate (todos deben pasar antes de BUILD):
  demanda_observable, costo≈0, capacidad_técnica, distribucion_gratuita,
  margen_alto, potencial_recurrente, automatizable, tiempo_razonable, riesgo_aceptable.
"""

from cores.asset_factory.engine import AssetFactoryEngine, get_asset_factory
from cores.asset_factory.models import Asset, AssetStatus, AssetType

__all__ = ["Asset", "AssetStatus", "AssetType", "AssetFactoryEngine", "get_asset_factory"]
