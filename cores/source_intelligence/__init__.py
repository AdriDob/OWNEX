"""Source Intelligence — Automatic discovery, verification, scoring, and renewal of work sources.

This module implements the "Universal Source Adapter" and "Source Intelligence" layers
defined in the product specification. It enables OwnEX to discover, evaluate, and
maintain up to 300+ work sources with automatic renewal and priority ranking.

Three independent verifications per source:
1. Elegibilidad y acceso desde Argentina
2. Capacidad de integración y ejecución
3. Cobro y retiro de dinero viable

Architecture:
- Source Registry: Catálogo canonical de fuentes con metadatos
- Verification Engine: Three independent checks per source
- Intelligence Engine: Scoring, prioritization, renewal decisions
- Renewal Agent: Automatic health checks and retirement
- Intelligence Report: Priority rankings and recommendations
"""

from __future__ import annotations

from .intelligence import IntelligenceReport, PriorityRanking, SourceIntelligence
from .registry import SourceCategory, SourceInfo, SourceRegistry, SourceStatus
from .renewal import RenewalAgent, RenewalSchedule
from .verifier import CheckCategory, SourceVerifier, VerificationCheck, VerificationResult

__all__ = [
    "SourceRegistry",
    "SourceInfo",
    "SourceStatus",
    "SourceCategory",
    "SourceVerifier",
    "VerificationCheck",
    "VerificationResult",
    "CheckCategory",
    "SourceIntelligence",
    "IntelligenceReport",
    "PriorityRanking",
    "RenewalAgent",
    "RenewalSchedule",
]
