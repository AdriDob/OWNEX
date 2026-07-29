"""Bridge module — re-exports the most useful OLA types for import convenience.

Lo más utilizado por los adaptadores de Forge:
  - OpportunityAdapter (Base disponible para crear adaptadores)
  - RawOpportunity (Puedes crear este tipo de datos)
"""

from .forge_legacy import OpportunityAdapter, RawOpportunity

__all__ = ["OpportunityAdapter", "RawOpportunity"]
