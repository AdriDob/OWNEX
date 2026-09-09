"""Promoter — promueve un AttackCandidate validado a Finding en la DB.

Pipeline:
  ValidationResult → ConfidenceScore → Confidence >= 0.7 + reproducible
    → create Finding in DB
    → publish event to EventBus
    → attach evidence bundle
    → return PromoteDecision

Si confidence < 0.7, registra el intento y las razones de rechazo.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.validation.confidence import ConfidenceEngine
from core.validation.models import (
    AttackCandidate,
    ConfidenceScore,
    PromoteDecision,
    Severity,
    ValidationResult,
)

logger = logging.getLogger("orion.core.validation.promoter")

# ── Thresholds ─────────────────────────────────────────────────

PROMOTE_CONFIDENCE_THRESHOLD = 0.7
AUTO_PROMOTE_MIN_CONFIDENCE = 0.85  # Sin revisión humana


class ValidationPromoter:
    """Promueve hallazgos validados a Findings en la base de datos.

    Flujo:
      1. Recibe ValidationResult + AttackCandidate
      2. Calcula ConfidenceScore
      3. Si confianza >= threshold, crea Finding en DB
      4. Publica evento en EventBus
      5. Retorna PromoteDecision
    """

    def __init__(self) -> None:
        self._confidence = ConfidenceEngine()

    def promote(
        self,
        candidate: AttackCandidate,
        result: ValidationResult,
        session: Any = None,
    ) -> PromoteDecision:
        """Intenta promover un AttackCandidate a Finding en la DB.

        Args:
            candidate: AttackCandidate original
            result: ValidationResult con la evidencia
            session: Sesión de DB opcional (si no se pasa, no persiste)

        Returns:
            PromoteDecision con el resultado
        """
        confidence = self._confidence.evaluate(result)
        severity = self._map_severity(candidate, confidence)

        poc_data = {
            "curl": result.poc_curl,
            "python": result.poc_python[:500],
            "httpie": result.poc_httpie,
            "evidence": result.evidence_data,
            "signals": result.total_signals,
            "reproducible": result.reproducible,
        }

        # Decidir si promover
        if confidence.should_promote:
            title = self._build_title(candidate, severity)
            description = self._build_description(candidate, result, confidence)

            finding_id = None
            if session is not None:
                finding_id = self._create_finding_in_db(
                    session=session,
                    candidate=candidate,
                    title=title,
                    severity=severity,
                    description=description,
                    poc_data=poc_data,
                )
                self._publish_event(candidate, result, confidence, finding_id)
                logger.info(
                    "[PROMOTER] ✅ Finding creado: #%d — %s (confianza=%.1f%%)",
                    finding_id,
                    title,
                    confidence.score * 100,
                )
            else:
                logger.info(
                    "[PROMOTER] ✅ Finding listo (sin DB): %s (confianza=%.1f%%)",
                    title,
                    confidence.score * 100,
                )

            return PromoteDecision(
                attack_candidate_id=candidate.id,
                validation_result_id=result.id,
                confidence=confidence,
                promoted=True,
                finding_id=finding_id,
                target_id=candidate.target_id,
                title=title,
                severity=severity,
                description=description,
                poc_data=poc_data,
            )

        # No promover
        rejected_reason = self._build_rejection_reason(confidence)
        logger.info(
            "[PROMOTER] ❌ No promovido: %s %s (confianza=%.1f%%) — %s",
            candidate.vulnerability_type.value,
            candidate.endpoint_path,
            confidence.score * 100,
            rejected_reason,
        )

        return PromoteDecision(
            attack_candidate_id=candidate.id,
            validation_result_id=result.id,
            confidence=confidence,
            promoted=False,
            target_id=candidate.target_id,
            title=self._build_title(candidate, severity),
            severity=severity,
            rejected_reason=rejected_reason,
        )

    # ── Helpers ────────────────────────────────────────────────

    def _build_title(self, candidate: AttackCandidate, severity: Severity) -> str:
        """Construye título descriptivo para el Finding."""
        vuln_label = candidate.vulnerability_type.value.upper()
        method = candidate.method.upper()
        path = candidate.endpoint_path
        return f"[{vuln_label}] {method} {path} — Confirmed by Validation Engine"

    def _build_description(
        self,
        candidate: AttackCandidate,
        result: ValidationResult,
        confidence: ConfidenceScore,
    ) -> str:
        """Construye descripción estructurada del hallazgo."""
        parts: list[str] = []
        parts.append(f"## Vulnerability: {candidate.vulnerability_type.value.upper()}")
        parts.append(f"**Endpoint:** {candidate.method.upper()} {candidate.endpoint_path}")
        if candidate.host:
            parts.append(f"**Host:** {candidate.host}")
        parts.append(f"**Confidence:** {confidence.score:.1%}")
        parts.append("")

        if result.total_signals:
            parts.append("### Signals Detected")
            for s in result.total_signals:
                parts.append(f"- {s}")
            parts.append("")

        if result.evidence_summary:
            parts.append("### Evidence")
            parts.append(result.evidence_summary)
            parts.append("")

        if confidence.reasoning:
            parts.append("### Confidence Reasoning")
            for r in confidence.reasoning:
                parts.append(f"- {r}")
            parts.append("")

        if confidence.gaps:
            parts.append("### Gaps / Risks")
            for g in confidence.gaps:
                parts.append(f"- {g}")

        return "\n".join(parts)

    def _map_severity(self, candidate: AttackCandidate, confidence: ConfidenceScore) -> Severity:
        """Mapea severidad basada en tipo de vulnerabilidad + confianza."""
        if confidence.score >= 0.9:
            if candidate.vulnerability_type.value in ("sqli", "cmdi"):
                return Severity.CRITICAL
            return Severity.HIGH
        if confidence.score >= 0.7:
            if candidate.vulnerability_type.value in ("idor", "auth_bypass"):
                return Severity.HIGH
            return Severity.MEDIUM
        if confidence.score >= 0.4:
            return Severity.MEDIUM
        return Severity.LOW

    def _create_finding_in_db(
        self,
        session: Any,
        candidate: AttackCandidate,
        title: str,
        severity: Severity,
        description: str,
        poc_data: dict[str, Any],
    ) -> int:
        """Crea un Finding en la base de datos.

        Usa el modelo Finding existente en database/models.py
        """
        from database import models

        finding = models.Finding(
            target_id=candidate.target_id,
            title=title,
            severity=severity.value,
            description=description,
            status="open",
            vulnerability_type=candidate.vulnerability_type.value,
            notes=json.dumps(
                {
                    "validation_id": candidate.id,
                    "poc_data": poc_data,
                    "signals": candidate.signals,
                    "attack_candidate_id": candidate.id,
                },
                indent=2,
            ),
        )
        session.add(finding)
        session.flush()  # Obtener el ID sin commit
        return finding.id  # type: ignore[return-value]

    def _publish_event(
        self,
        candidate: AttackCandidate,
        result: ValidationResult,
        confidence: ConfidenceScore,
        finding_id: int,
    ) -> None:
        """Publica evento de finding confirmado en EventBus."""
        try:
            from cores.events.event_bus import get_event_bus

            bus = get_event_bus()
            bus.publish(
                "finding:created",
                payload={
                    "finding_id": finding_id,
                    "target_id": candidate.target_id,
                    "vulnerability_type": candidate.vulnerability_type.value,
                    "endpoint": candidate.endpoint_path,
                    "method": candidate.method,
                    "confidence": confidence.score,
                    "evidence_summary": result.evidence_summary,
                    "source": "validation_engine",
                    "attack_candidate_id": candidate.id,
                },
            )
        except Exception as exc:
            logger.warning("[PROMOTER] No se pudo publicar evento: %s", exc)

    def _build_rejection_reason(self, confidence: ConfidenceScore) -> str:
        """Construye razón de rechazo para no promover."""
        parts: list[str] = []
        if confidence.score < PROMOTE_CONFIDENCE_THRESHOLD:
            parts.append(f"Confianza ({confidence.score:.1%}) bajo umbral ({PROMOTE_CONFIDENCE_THRESHOLD:.0%})")
        if not confidence.reproducible:
            parts.append("No reproducible")
        if confidence.gaps:
            parts.extend(confidence.gaps[:3])
        return "; ".join(parts) if parts else "Confianza insuficiente"
