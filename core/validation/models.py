"""Validation Engine — modelos de datos para el ciclo de validación experimental.

Jerarquía:

  AttackCandidate       → Hipótesis + Score Económico
       ↓
  ValidationPlan        → Qué probar exactamente
       ↓
  ValidationResult      → Resultado de la prueba mínima
       ↓
  ProbeEvidence         → Evidencia cruda recolectada
       ↓
  ConfidenceScore       → Confianza calculada
       ↓
  PromoteDecision       → ¿Crear Finding en DB?
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ── Vulnerability types ────────────────────────────────────────


class VulnType(str, Enum):
    IDOR = "idor"
    SSRF = "ssrf"
    XSS = "xss"
    SQLI = "sqli"
    AUTH_BYPASS = "auth_bypass"
    CSRF = "csrf"
    LFI = "lfi"
    CMDI = "cmdi"
    GRAPHQL = "graphql"
    RACE_CONDITION = "race_condition"
    CORS = "cors"
    OPEN_REDIRECT = "open_redirect"
    BUSINESS_LOGIC = "business_logic"
    GENERIC = "generic"


# ── Protocol types ─────────────────────────────────────────────


class ProtocolType(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    GRAPHQL = "graphql"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    S3 = "s3"
    FIREBASE = "firebase"
    JWT = "jwt"
    OAUTH = "oauth"


# ── Severity ───────────────────────────────────────────────────


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ── AttackCandidate ────────────────────────────────────────────


@dataclass
class EconomicScore:
    """¿Cuánto vale económicamente validar esta hipótesis?"""

    expected_payout_low: float = 0.0
    expected_payout_high: float = 0.0
    expected_payout_avg: float = 0.0
    probability_acceptance: float = 0.0  # 0.0-1.0 basado en histórico
    effort_minutes: float = 5.0  # Tiempo estimado de validación
    usd_per_hour: float = 0.0
    priority: int = 0  # 1-10, 10 = máxima prioridad
    reasoning: list[str] = field(default_factory=list)

    @property
    def expected_value(self) -> float:
        """Valor esperado = payout_avg * acceptance_prob."""
        return self.expected_payout_avg * self.probability_acceptance

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_payout_low": round(self.expected_payout_low, 2),
            "expected_payout_high": round(self.expected_payout_high, 2),
            "expected_payout_avg": round(self.expected_payout_avg, 2),
            "probability_acceptance": round(self.probability_acceptance, 2),
            "effort_minutes": self.effort_minutes,
            "usd_per_hour": round(self.usd_per_hour, 2),
            "expected_value": round(self.expected_value, 2),
            "priority": self.priority,
            "reasoning": self.reasoning,
        }


@dataclass
class AttackCandidate:
    """Una hipótesis que pasó el filtro económico y merece ser validada.

    Envuelve una hypothesis existente del sistema Offensive Intelligence
    y le agrega el score económico y metadata de validación.
    """

    id: str = field(default_factory=lambda: f"ac-{uuid.uuid4().hex[:12]}")
    vulnerability_type: VulnType = VulnType.GENERIC
    protocol: ProtocolType = ProtocolType.HTTP

    # Endpoint objetivo
    target_id: int = 0
    endpoint_path: str = ""
    method: str = "GET"
    host: str = ""
    base_url: str = ""  # ej: https://api.target.com

    # Parámetros de interés
    parameters_of_interest: list[str] = field(default_factory=list)
    param_values: dict[str, str] = field(default_factory=dict)  # valores reales del endpoint
    headers_template: dict[str, str] = field(default_factory=dict)
    body_template: dict[str, Any] | None = None

    # Auth
    requires_auth: bool = False
    auth_type: str = ""  # "bearer", "cookie", "basic", "none"
    auth_token_hint: str = ""  # cómo obtener el token

    # Metadata de la hipótesis original
    original_hypothesis_id: str = ""
    reasoner_confidence: float = 0.0  # confianza del reasoner (0-1)
    signals: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)

    # Score económico
    economic_score: EconomicScore = field(default_factory=EconomicScore)

    # Estado de validación
    status: str = "pending"  # pending, planned, validated, confirmed, rejected, error

    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "vulnerability_type": self.vulnerability_type.value,
            "protocol": self.protocol.value,
            "target_id": self.target_id,
            "endpoint_path": self.endpoint_path,
            "method": self.method,
            "host": self.host,
            "base_url": self.base_url,
            "parameters_of_interest": self.parameters_of_interest,
            "param_values": self.param_values,
            "requires_auth": self.requires_auth,
            "auth_type": self.auth_type,
            "original_hypothesis_id": self.original_hypothesis_id,
            "reasoner_confidence": round(self.reasoner_confidence, 2),
            "signals": self.signals,
            "economic_score": self.economic_score.to_dict(),
            "status": self.status,
            "created_at": self.created_at,
        }


# ── ValidationPlan ─────────────────────────────────────────────


class ProbeType(str, Enum):
    """Tipo de prueba a ejecutar."""

    BASELINE = "baseline"  # Request normal para tener línea de base
    AUTH_BYPASS = "auth_bypass"  # Probar sin auth
    ID_SWAP = "id_swap"  # Cambiar ID por otro
    ID_SEQUENTIAL = "id_sequential"  # Probar IDs secuenciales
    UUID_SWAP = "uuid_swap"  # Cambiar UUID por otro conocido
    PARAM_INJECTION = "param_injection"  # Inyectar payload en parámetro
    HEADER_INJECTION = "header_injection"  # Inyectar en header
    BODY_INJECTION = "body_injection"  # Inyectar en body
    SLEEP_DETECT = "sleep_detect"  # Time-based detection
    ERROR_ANALYSIS = "error_analysis"  # Analizar mensajes de error
    CUSTOM = "custom"  # Personalizado


@dataclass
class ProbeInstruction:
    """Una instrucción atómica de prueba."""

    probe_type: ProbeType = ProbeType.BASELINE
    description: str = ""
    method: str = "GET"
    path: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    expected_signal: str = ""  # qué buscar en la respuesta
    comparison_with: str = ""  # ID de la probe baseline para comparar

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_type": self.probe_type.value,
            "description": self.description,
            "method": self.method,
            "path": self.path,
            "headers": self.headers,
            "params": self.params,
            "body": self.body,
            "expected_signal": self.expected_signal,
            "comparison_with": self.comparison_with,
        }


@dataclass
class ValidationPlan:
    """Plan estratégico de validación para un AttackCandidate.

    No incluye TODAS las pruebas posibles — solo las mínimas
    que dan la máxima señal con el menor costo.
    """

    id: str = field(default_factory=lambda: f"vp-{uuid.uuid4().hex[:12]}")
    attack_candidate_id: str = ""
    vulnerability_type: VulnType = VulnType.GENERIC

    # Pruebas a ejecutar (ordenadas por señal/costo)
    probes: list[ProbeInstruction] = field(default_factory=list)

    # Estrategia
    strategy_summary: str = ""
    max_probes: int = 3
    requires_baseline: bool = True

    # Señales a buscar en las respuestas
    signals_to_check: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def estimated_cost(self) -> int:
        """Costo estimado en número de requests."""
        return len(self.probes) + (1 if self.requires_baseline else 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "attack_candidate_id": self.attack_candidate_id,
            "vulnerability_type": self.vulnerability_type.value,
            "probes": [p.to_dict() for p in self.probes],
            "strategy_summary": self.strategy_summary,
            "max_probes": self.max_probes,
            "requires_baseline": self.requires_baseline,
            "estimated_cost": self.estimated_cost,
            "signals_to_check": self.signals_to_check,
        }


# ── ValidationResult ───────────────────────────────────────────


@dataclass
class ProbeResult:
    """Resultado de una probe individual."""

    probe_type: ProbeType = ProbeType.BASELINE
    success: bool = False
    status_code: int = 0
    response_time_ms: float = 0.0
    response_size: int = 0
    response_preview: str = ""  # primeros 500 chars
    headers: dict[str, str] = field(default_factory=dict)
    error: str = ""

    # Señales detectadas
    signals_detected: list[str] = field(default_factory=list)
    data_leaked: bool = False
    auth_bypassed: bool = False
    timing_anomaly_ms: float = 0.0
    reflected_payload: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_type": self.probe_type.value,
            "success": self.success,
            "status_code": self.status_code,
            "response_time_ms": round(self.response_time_ms, 1),
            "response_size": self.response_size,
            "response_preview": self.response_preview[:200],
            "signals_detected": self.signals_detected,
            "data_leaked": self.data_leaked,
            "auth_bypassed": self.auth_bypassed,
            "timing_anomaly_ms": round(self.timing_anomaly_ms, 1),
            "reflected_payload": self.reflected_payload,
            "error": self.error[:200] if self.error else "",
        }


@dataclass
class ValidationResult:
    """Resultado completo de la validación experimental."""

    id: str = field(default_factory=lambda: f"vr-{uuid.uuid4().hex[:12]}")
    attack_candidate_id: str = ""
    validation_plan_id: str = ""

    # Resultados
    baseline: ProbeResult | None = None
    probes: list[ProbeResult] = field(default_factory=list)

    # Señales globales
    total_signals: list[str] = field(default_factory=list)
    evidence_summary: str = ""
    reproducible: bool = False
    false_positive_risk: str = ""  # "low", "medium", "high"

    # Datos crudos para PoC
    poc_curl: str = ""
    poc_python: str = ""
    poc_httpie: str = ""
    evidence_data: dict[str, Any] = field(default_factory=dict)

    executed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "attack_candidate_id": self.attack_candidate_id,
            "validation_plan_id": self.validation_plan_id,
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "probes": [p.to_dict() for p in self.probes],
            "total_signals": self.total_signals,
            "evidence_summary": self.evidence_summary,
            "reproducible": self.reproducible,
            "false_positive_risk": self.false_positive_risk,
            "poc_curl": self.poc_curl,
            "poc_python": self.poc_python[:300],
            "duration_ms": round(self.duration_ms, 1),
        }


# ── ConfidenceScore ────────────────────────────────────────────


@dataclass
class ConfidenceScore:
    """Confianza calculada basada en la evidencia recolectada."""

    score: float = 0.0  # 0.0-1.0
    signals_found: int = 0
    signals_possible: int = 0
    data_leak_confirmed: bool = False
    auth_bypass_confirmed: bool = False
    reproducible: bool = False
    baseline_diff_ratio: float = 0.0  # qué tan diferente fue la respuesta
    rejection_risk: str = "high"  # "low", "medium", "high"
    reasoning: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.score >= 0.9:
            return "confirmed"
        elif self.score >= 0.7:
            return "highly_probable"
        elif self.score >= 0.4:
            return "probable"
        elif self.score >= 0.2:
            return "unlikely"
        return "negative"

    @property
    def should_promote(self) -> bool:
        """¿Merece promoverse a Finding en la DB?"""
        return self.score >= 0.7 and self.reproducible

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "label": self.label,
            "signals_found": self.signals_found,
            "signals_possible": self.signals_possible,
            "data_leak_confirmed": self.data_leak_confirmed,
            "auth_bypass_confirmed": self.auth_bypass_confirmed,
            "reproducible": self.reproducible,
            "baseline_diff_ratio": round(self.baseline_diff_ratio, 3),
            "rejection_risk": self.rejection_risk,
            "should_promote": self.should_promote,
            "reasoning": self.reasoning,
            "gaps": self.gaps,
        }


# ── PromoteDecision ────────────────────────────────────────────


@dataclass
class PromoteDecision:
    """Decisión de promoción: Hypothesis → Finding."""

    attack_candidate_id: str = ""
    validation_result_id: str = ""
    confidence: ConfidenceScore = field(default_factory=ConfidenceScore)
    promoted: bool = False
    finding_id: int | None = None  # DB id after creation
    target_id: int = 0
    endpoint_id: int | None = None
    title: str = ""
    severity: Severity = Severity.MEDIUM
    description: str = ""
    poc_data: dict[str, Any] = field(default_factory=dict)
    rejected_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_candidate_id": self.attack_candidate_id,
            "validation_result_id": self.validation_result_id,
            "confidence": self.confidence.to_dict(),
            "promoted": self.promoted,
            "finding_id": self.finding_id,
            "target_id": self.target_id,
            "title": self.title,
            "severity": self.severity.value,
            "rejected_reason": self.rejected_reason,
        }
