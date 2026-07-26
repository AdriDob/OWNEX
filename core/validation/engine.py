"""Validation Engine — orquestador del ciclo completo de validación experimental.

Pipeline completo:

  1. Recibe un AttackCandidate (hipótesis + score económico)
  2. Genera un ValidationPlan (qué probar exactamente)
  3. Ejecuta las probes vía adaptador de protocolo
  4. Analiza resultados y calcula ConfidenceScore
  5. Promueve a Finding si confianza suficiente
  6. Retorna el ciclo completo: plan → resultado → decisión

Uso típico:

    engine = ValidationEngine()
    result = engine.run(candidate, session=db_session)
    if result.decision.promoted:
        print(f"Finding #{result.decision.finding_id} creado")
"""

from __future__ import annotations

import logging
import time
from typing import Any

from core.validation.adapters import HTTPAdapter
from core.validation.confidence import ConfidenceEngine
from core.validation.economic_scorer import EconomicScorer
from core.validation.models import (
    AttackCandidate,
    ConfidenceScore,
    EconomicScore,
    ProbeResult,
    ProbeType,
    PromoteDecision,
    ValidationPlan,
    ValidationResult,
)
from core.validation.planner import ValidationPlanner
from core.validation.promoter import ValidationPromoter

logger = logging.getLogger("orion.core.validation.engine")

# ── Timeouts ───────────────────────────────────────────────────

DEFAULT_CONNECT_TIMEOUT = 15
DEFAULT_READ_TIMEOUT = 30  # más largo para SQLi time-based


class ValidationEngine:
    """Motor de validación experimental de hipótesis.

    Orquesta: EconomicScorer → Planner → HTTP Adapter → Confidence → Promoter.
    """

    def __init__(self, probe_engine: Any = None) -> None:
        self._scorer = EconomicScorer()
        self._planner = ValidationPlanner()
        self._adapter: HTTPAdapter | None = None
        self._confidence = ConfidenceEngine()
        self._promoter = ValidationPromoter()
        self._probe_engine = probe_engine

    # ── Public API ─────────────────────────────────────────────

    def run(
        self,
        candidate: AttackCandidate,
        session: Any = None,
        dry_run: bool = False,
    ) -> ValidationEngineResult:
        """Ejecuta el ciclo completo de validación para un AttackCandidate.

        Args:
            candidate: El AttackCandidate a validar
            session: Sesión de DB para promover Findings (opcional)
            dry_run: Si True, no ejecuta requests reales

        Returns:
            ValidationEngineResult con todo el ciclo
        """
        start = time.monotonic()

        # 1. Economic Score (si no tiene)
        if candidate.economic_score.priority == 0:
            candidate.economic_score = self._scorer.score(candidate)

        # 2. Validation Plan
        plan = self._planner.plan(candidate)

        if dry_run:
            logger.info(
                "[ENGINE] Dry run: %s %s → plan con %d probes (costo %d requests)",
                candidate.method,
                candidate.endpoint_path,
                len(plan.probes),
                plan.estimated_cost,
            )
            return ValidationEngineResult(
                candidate=candidate,
                plan=plan,
                result=None,
                confidence=None,
                decision=PromoteDecision(
                    attack_candidate_id=candidate.id,
                    promoted=False,
                    rejected_reason="Dry run — no se ejecutaron probes",
                ),
                duration_ms=0.0,
                dry_run=True,
            )

        # 3. Ejecutar probes
        result = self._execute_plan(candidate, plan)

        # 4. Calcular confianza
        confidence = self._confidence.evaluate(result)

        # 5. Promover a Finding
        decision = self._promoter.promote(candidate, result, session=session)

        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "[ENGINE] %s %s → %s (confianza=%.1f%%, %d probes, %.0fms)%s",
            candidate.method,
            candidate.endpoint_path,
            "✅ PROMOTED" if decision.promoted else "❌ rejected",
            confidence.score * 100,
            len(result.probes),
            duration_ms,
            f" → Finding #{decision.finding_id}" if decision.finding_id else "",
        )

        return ValidationEngineResult(
            candidate=candidate,
            plan=plan,
            result=result,
            confidence=confidence,
            decision=decision,
            duration_ms=duration_ms,
        )

    def score(self, candidate: AttackCandidate) -> EconomicScore:
        """Solo calcula el Economic Score, sin ejecutar nada."""
        candidate.economic_score = self._scorer.score(candidate)
        return candidate.economic_score

    def plan_only(self, candidate: AttackCandidate) -> ValidationPlan:
        """Solo genera el plan, sin ejecutar nada."""
        return self._planner.plan(candidate)

    # ── Internal ───────────────────────────────────────────────

    def _get_adapter(self) -> HTTPAdapter:
        """Obtiene (o crea) el adaptador HTTP."""
        if self._adapter is None:
            self._adapter = HTTPAdapter(timeout=DEFAULT_READ_TIMEOUT)
        return self._adapter

    def _execute_plan(self, candidate: AttackCandidate, plan: ValidationPlan) -> ValidationResult:
        """Ejecuta un ValidationPlan y devuelve el ValidationResult."""
        self._get_adapter()

        all_probes: list[ProbeResult] = []
        baseline_result: ProbeResult | None = None
        total_signals: list[str] = []
        evidence_data: dict[str, Any] = {}

        # Ejecutar cada probe del plan
        use_probe_engine = self._probe_engine is not None and candidate.original_hypothesis_id

        if use_probe_engine:
            result = self._execute_with_probe_engine(candidate, plan)
            poc_curl = result.poc_curl
            poc_python = result.poc_python
        else:
            result = self._execute_with_adapter(candidate, plan)
            poc_curl = self._generate_poc_curl(candidate, plan)
            poc_python = self._generate_poc_python(candidate, plan)
            self._generate_poc_httpie(candidate, plan)
            self._generate_poc_javascript(candidate, plan)
            self._generate_poc_burp(candidate, plan)

        # Resumen de evidencia
        evidence_summary = self._build_evidence_summary(candidate, baseline_result, all_probes, total_signals)

        # Reproducibilidad
        reproducible = self._check_reproducible(baseline_result, all_probes)

        # Riesgo de falso positivo
        fp_risk = self._assess_fp_risk(total_signals, all_probes)

        return ValidationResult(
            attack_candidate_id=candidate.id,
            validation_plan_id=plan.id,
            baseline=baseline_result,
            probes=all_probes,
            total_signals=total_signals,
            evidence_summary=evidence_summary,
            reproducible=reproducible,
            false_positive_risk=fp_risk,
            poc_curl=poc_curl,
            poc_python=poc_python,
            poc_httpie="",
            evidence_data=evidence_data,
        )

    # ── Analysis helpers ───────────────────────────────────────

    def _contains_sql_error(self, body: str) -> bool:
        """Detecta mensajes de error SQL."""
        keywords = [
            "sql syntax",
            "mysql",
            "unclosed quotation",
            "ora-",
            "driver",
            "odbc",
            "syntax error",
            "postgresql",
        ]
        body_lower = body.lower()
        return any(kw in body_lower for kw in keywords)

    def _build_evidence_summary(
        self,
        candidate: AttackCandidate,
        baseline: ProbeResult | None,
        probes: list[ProbeResult],
        signals: list[str],
    ) -> str:
        """Construye resumen legible de la evidencia."""
        parts: list[str] = []
        parts.append(
            f"Validation of {candidate.vulnerability_type.value.upper()} on {candidate.method.upper()} {candidate.endpoint_path}"
        )
        parts.append("")

        if baseline:
            parts.append(
                f"Baseline: {baseline.status_code} ({baseline.response_time_ms:.0f}ms, {baseline.response_size} bytes)"
            )
        if probes:
            for i, p in enumerate(probes):
                parts.append(
                    f"Probe {i + 1} ({p.probe_type.value}): {p.status_code} "
                    f"({p.response_time_ms:.0f}ms, {p.response_size} bytes)"
                    f"{' ⚠ data leak' if p.data_leaked else ''}"
                    f"{' ⚠ auth bypass' if p.auth_bypassed else ''}"
                )
        parts.append("")
        if signals:
            parts.append("Signals detected:")
            for s in signals:
                parts.append(f"  ✓ {s}")
        parts.append("")
        return "\n".join(parts)

    def _check_reproducible(self, baseline: ProbeResult | None, probes: list[ProbeResult]) -> bool:
        """Verifica si la vulnerabilidad es reproducible."""
        if not probes or not baseline:
            return False
        # Al menos una probe con señal detectada
        signal_probes = [p for p in probes if p.data_leaked or p.auth_bypassed or p.timing_anomaly_ms > 2000]
        return len(signal_probes) >= 1

    def _assess_fp_risk(self, signals: list[str], probes: list[ProbeResult]) -> str:
        """Evalúa riesgo de falso positivo."""
        if len(signals) >= 3:
            return "low"
        if len(signals) >= 1:
            # Verificar consistencia
            data_signals = [s for s in probes if s.data_leaked]
            auth_signals = [s for s in probes if s.auth_bypassed]
            if data_signals and auth_signals:
                return "low"
            return "medium"
        return "high"

    def _generate_poc_curl(self, candidate: AttackCandidate, plan: ValidationPlan) -> str:
        """Genera comando curl de ejemplo para la prueba."""
        base_url = candidate.base_url
        path = candidate.endpoint_path
        method = candidate.method.upper()
        lines = [f"# PoC: {candidate.vulnerability_type.value.upper()} - {method} {path}"]

        # Primer probe no-baseline
        for p in plan.probes:
            if p.probe_type != ProbeType.BASELINE:
                url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
                curl = [f"curl -X {method} '{url}'"]

                for k, v in (p.headers or {}).items():
                    curl.append(f"  -H '{k}: {v}'")

                if p.body:
                    import json

                    curl.append("  -H 'Content-Type: application/json'")
                    curl.append(f"  -d '{json.dumps(p.body)}'")

                if p.params:
                    import urllib.parse

                    qs = urllib.parse.urlencode(p.params)
                    curl[0] = f"curl -X {method} '{url}?{qs}'"

                lines.append("")
                lines.append(f"# Test: {p.description}")
                lines.append(" \\\n".join(curl))
                break

        return "\n".join(lines)

    def _generate_poc_python(self, candidate: AttackCandidate, plan: ValidationPlan) -> str:
        """Genera script Python de ejemplo."""
        base_url = candidate.base_url
        path = candidate.endpoint_path
        method = candidate.method.upper()

        lines = [
            "import requests",
            "",
            f"# PoC: {candidate.vulnerability_type.value.upper()} - {method} {path}",
            "",
        ]

        for p in plan.probes:
            if p.probe_type == ProbeType.BASELINE:
                continue
            url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
            lines.append(f"# Test: {p.description}")
            lines.append(f"url = '{url}'")
            if p.params:
                lines.append(f"params = {p.params}")
                lines.append(f"response = requests.{method.lower()}(url, params=params)")
            else:
                lines.append(f"response = requests.{method.lower()}(url)")
            lines.append("print(f'Status: {response.status_code}')")
            lines.append("print(f'Body: {response.text[:1000]}')")
            lines.append("")
            break

        return "\n".join(lines)


# ── Result container ───────────────────────────────────────────


class ValidationEngineResult:
    """Contenedor del resultado completo del Validation Engine."""

    def __init__(
        self,
        candidate: AttackCandidate,
        plan: ValidationPlan,
        result: ValidationResult | None,
        confidence: ConfidenceScore | None,
        decision: PromoteDecision,
        duration_ms: float,
        dry_run: bool = False,
    ) -> None:
        self.candidate = candidate
        self.plan = plan
        self.result = result
        self.confidence = confidence
        self.decision = decision
        self.duration_ms = duration_ms
        self.dry_run = dry_run

    @property
    def promoted(self) -> bool:
        return self.decision.promoted

    @property
    def summary(self) -> str:
        parts = [
            f"[{self.candidate.vulnerability_type.value.upper()}] "
            f"{self.candidate.method} {self.candidate.endpoint_path}",
        ]
        if self.dry_run:
            parts.append(f"  Plan: {len(self.plan.probes)} probes, {self.plan.estimated_cost} requests")
            parts.append("  ⏭ Dry run — no se ejecutaron requests")
        elif self.decision.promoted:
            parts.append(
                f"  ✅ Promoted → Finding #{self.decision.finding_id}" if self.decision.finding_id else "✅ Promoted"
            )
            parts.append(f"  Confianza: {self.confidence.score:.1%}" if self.confidence else "")
        else:
            parts.append(f"  ❌ Rejected: {self.decision.rejected_reason}")
            parts.append(f"  Confianza: {self.confidence.score:.1%}" if self.confidence else "")
        parts.append(f"  Duración: {self.duration_ms:.0f}ms")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.to_dict(),
            "plan": self.plan.to_dict(),
            "result": self.result.to_dict() if self.result else None,
            "confidence": self.confidence.to_dict() if self.confidence else None,
            "decision": self.decision.to_dict(),
            "duration_ms": round(self.duration_ms, 1),
            "dry_run": self.dry_run,
            "promoted": self.promoted,
        }
