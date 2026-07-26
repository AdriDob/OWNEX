"""Confidence Engine — calcula confianza basada en evidencia experimental recolectada.

No dice "hay IDOR" o "no hay IDOR".
Dice: "Confianza: 94% — señal encontrada, reproducible, datos filtrados".

Factores:
  - Diferencia baseline vs probe (status code, body, size)
  - Señales específicas detectadas (data leak, auth bypass, timing anomaly)
  - Reproducibilidad (misma señal en probes diferentes)
  - Riesgo de falso positivo
"""

from __future__ import annotations

import logging

from core.validation.models import ConfidenceScore, ProbeResult, ValidationResult

logger = logging.getLogger("orion.core.validation.confidence")

# ── Pesos de cada señal ────────────────────────────────────────

SIGNAL_WEIGHTS: dict[str, float] = {
    "data_leaked": 0.35,
    "auth_bypassed": 0.30,
    "timing_anomaly": 0.20,
    "reflected_payload": 0.35,
    "status_code_change": 0.10,
    "body_size_change": 0.10,
    "error_message_sql": 0.25,
    "error_message_detailed": 0.15,
}


class ConfidenceEngine:
    """Evalúa la confianza de un ValidationResult.

    El engine analiza las diferencias entre baseline y probes,
    extrae señales, y calcula un score de confianza 0.0-1.0.
    """

    def evaluate(self, result: ValidationResult) -> ConfidenceScore:
        """Calcula el ConfidenceScore para un ValidationResult completo."""
        signals_found = 0
        signals_possible = len(result.total_signals)
        reasoning: list[str] = []
        gaps: list[str] = []

        if not result.baseline:
            return ConfidenceScore(
                score=0.0,
                reasoning=["No hay baseline — no se puede calcular confianza"],
                gaps=["Baseline missing"],
                rejection_risk="high",
            )

        if not result.probes:
            return ConfidenceScore(
                score=0.0,
                reasoning=["No hay probes ejecutadas"],
                gaps=["No probes executed"],
                rejection_risk="high",
            )

        baseline = result.baseline

        # ── Data leak detection ────────────────────────────────────
        data_leak = self._detect_data_leak(result)
        if data_leak:
            signals_found += 1
            reasoning.append("Data leak detectado: respuesta contiene datos de otro usuario")

        # ── Auth bypass detection ──────────────────────────────────
        auth_bypass = self._detect_auth_bypass(result)
        if auth_bypass:
            signals_found += 1
            reasoning.append("Auth bypass: endpoint responde igual sin autenticación")

        # ── Timing anomaly ─────────────────────────────────────────
        for probe in result.probes:
            if probe.timing_anomaly_ms > 2000:
                signals_found += 1
                reasoning.append(
                    f"Timing anomaly: {probe.timing_anomaly_ms:.0f}ms vs baseline "
                    f"(sugiere SQLi time-based)"
                )
                break

        # ── Payload reflection ─────────────────────────────────────
        reflected = any(p.reflected_payload for p in result.probes)
        if reflected:
            signals_found += 1
            reasoning.append("Payload reflejado en response (sugiere XSS)")

        # ── Status code changes ────────────────────────────────────
        status_changes = sum(
            1 for p in result.probes if p.status_code != baseline.status_code and p.status_code > 0
        )
        if status_changes > 0:
            signals_found += 1
            reasoning.append(f"{status_changes} probe(s) con status code diferente al baseline")

        # ── Response size changes ──────────────────────────────────
        size_changes = sum(
            1
            for p in result.probes
            if p.response_size > 0
            and abs(p.response_size - baseline.response_size) > max(baseline.response_size * 0.3, 100)
        )
        if size_changes > 0:
            signals_found += 1
            reasoning.append(f"{size_changes} probe(s) con tamaño de respuesta significativamente diferente")
            if data_leak:
                reasoning.append("Data leak consistente: tamaño mayor + contenido diferente = evidencia fuerte")

        # ── Error analysis ─────────────────────────────────────────
        sql_error = self._detect_sql_error(result)
        if sql_error:
            signals_found += 1
            reasoning.append("Mensaje de error SQL revelado en la respuesta")

        # ── Calcular score ─────────────────────────────────────────
        total_signals = len(result.total_signals) if result.total_signals else 1
        score = min(1.0, signals_found / max(total_signals, 1))

        # Ajustes finos
        if data_leak and auth_bypass:
            score = min(1.0, score + 0.15)  # Bonus por señal combinada
            reasoning.append("Combo data leak + auth bypass = señal muy fuerte")

        if result.reproducible:
            score = min(1.0, score + 0.10)
            reasoning.append("Vulnerabilidad reproducible (múltiples probes confirman)")
        else:
            gaps.append("No se pudo reproducir consistentemente")

        if result.false_positive_risk == "low":
            score = min(1.0, score + 0.05)
        elif result.false_positive_risk == "high":
            score = max(0.0, score - 0.20)
            gaps.append("Alto riesgo de falso positivo")

        # Detectar gaps
        if not data_leak and auth_bypass:
            gaps.append("Data leak no confirmado — puede ser solo falta de auth, no IDOR")
        if not result.reproducible:
            gaps.append("Necesita verificación manual — no reproducible automáticamente")

        # Riesgo de rechazo
        if score >= 0.8 and data_leak:
            rejection_risk = "low"
        elif score >= 0.6:
            rejection_risk = "medium"
        else:
            rejection_risk = "high"

        return ConfidenceScore(
            score=round(score, 3),
            signals_found=signals_found,
            signals_possible=signals_possible,
            data_leak_confirmed=data_leak,
            auth_bypass_confirmed=auth_bypass,
            reproducible=result.reproducible,
            baseline_diff_ratio=self._baseline_diff_ratio(baseline, result.probes),
            rejection_risk=rejection_risk,
            reasoning=reasoning,
            gaps=gaps,
        )

    # ── Detection helpers ──────────────────────────────────────

    def _detect_data_leak(self, result: ValidationResult) -> bool:
        return any(p.data_leaked for p in result.probes)

    def _detect_auth_bypass(self, result: ValidationResult) -> bool:
        return any(p.auth_bypassed for p in result.probes)

    def _detect_sql_error(self, result: ValidationResult) -> bool:
        """Detecta mensajes de error SQL en responses."""
        sql_keywords = [
            "sql", "mysql", "postgresql", "sqlite",
            "you have an error in your sql syntax",
            "unclosed quotation mark",
            "odbc", "driver", "db2",
            "ora-", "oracle",
            "syntax error",
        ]
        for probe in result.probes:
            preview = probe.response_preview.lower()
            if any(kw in preview for kw in sql_keywords):
                return True
        return False

    def _baseline_diff_ratio(self, baseline: ProbeResult, probes: list[ProbeResult]) -> float:
        """Calcula qué tan diferentes son las probes del baseline (0.0-1.0)."""
        if not probes:
            return 0.0
        diffs = 0
        for p in probes:
            if p.status_code != baseline.status_code:
                diffs += 1
            if abs(p.response_size - baseline.response_size) > max(baseline.response_size * 0.3, 100):
                diffs += 1
            if p.data_leaked:
                diffs += 2
            if p.auth_bypassed:
                diffs += 2
        max_diffs = len(probes) * 5
        return min(1.0, diffs / max_diffs) if max_diffs > 0 else 0.0
