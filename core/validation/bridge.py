"""Bridge — conecta el Offensive Intelligence existente con el Validation Engine.

Transforma las Hypothesis del sistema de razonamiento en AttackCandidate
listos para validación experimental.

Pipeline:
  OffensiveEngine.analyze_endpoint() → ReasonerResult.hypotheses[]
    → bridge.to_candidates() → AttackCandidate[]
    → EconomicScorer.filter_candidates() → AttackCandidate[] priorizados
    → ValidationEngine.run() → PromoteDecision
"""

from __future__ import annotations

import logging
from typing import Any

from core.offensive.engine import OffensiveEngine
from core.offensive.models import Hypothesis
from core.validation.economic_scorer import EconomicScorer
from core.validation.engine import ValidationEngine
from core.validation.models import (
    AttackCandidate,
    VulnType,
)

logger = logging.getLogger("orion.core.validation.bridge")

# ── Mapeo de tipos de vulnerabilidad ──────────────────────────

VULN_MAP: dict[str, VulnType] = {
    "idor": VulnType.IDOR,
    "ssrf": VulnType.SSRF,
    "xss": VulnType.XSS,
    "sqli": VulnType.SQLI,
    "auth_bypass": VulnType.AUTH_BYPASS,
    "csrf": VulnType.CSRF,
    "lfi": VulnType.LFI,
    "cmdi": VulnType.CMDI,
    "graphql": VulnType.GRAPHQL,
    "race_condition": VulnType.RACE_CONDITION,
    "cors": VulnType.CORS,
    "open_redirect": VulnType.OPEN_REDIRECT,
    "business_logic": VulnType.BUSINESS_LOGIC,
}

# ── Mapeo de severidad → prioridad económica base ────────────

SEVERITY_PAYOUT_BASE: dict[str, float] = {
    "critical": 5000.0,
    "high": 1500.0,
    "medium": 400.0,
    "low": 100.0,
    "info": 0.0,
}


class ValidationBridge:
    """Puente entre OffensiveEngine y ValidationEngine.

    Uso:
        bridge = ValidationBridge()
        candidates = bridge.from_endpoint(endpoint_data, target_id=1)
        # candidates son AttackCandidate listos para engine.run()
    """

    def __init__(self) -> None:
        self._offensive = OffensiveEngine()
        self._scorer = EconomicScorer()
        self._validator = ValidationEngine()

    # ── Conversion ─────────────────────────────────────────────

    def from_hypothesis(self, hypothesis: Hypothesis, target_id: int = 0) -> AttackCandidate | None:
        """Convierte una Hypothesis del Offensive Intelligence en AttackCandidate.

        Returns None si el tipo de vulnerabilidad no está mapeado.
        """
        vuln_type = VULN_MAP.get(hypothesis.vulnerability_type)
        if vuln_type is None:
            logger.debug("[BRIDGE] Tipo no mapeado: %s — ignorando", hypothesis.vulnerability_type)
            return None

        endpoint = hypothesis.endpoint
        method = hypothesis.method or "GET"

        # Extraer headers del relationship context si existen
        headers_template: dict[str, str] = {}
        if hypothesis.relationship_context:
            pass  # No tenemos headers del relationship context actualmente

        # Extraer params de test_instructions si es posible
        param_values: dict[str, str] = {}
        for p in hypothesis.parameters_of_interest:
            param_values[p] = "FUZZ"

        # Determinar si requiere auth
        requires_auth = bool(
            hypothesis.why_triager_might_reject
            and any(kw in hypothesis.why_triager_might_reject.lower() for kw in ["auth", "authentication", "login", "session"])
        )

        candidate = AttackCandidate(
            vulnerability_type=vuln_type,
            method=method,
            endpoint_path=endpoint,
            host="",
            base_url="",
            parameters_of_interest=list(hypothesis.parameters_of_interest),
            param_values=param_values,
            headers_template=headers_template,
            requires_auth=requires_auth,
            original_hypothesis_id=hypothesis.id,
            reasoner_confidence=hypothesis.confidence,
            signals=list(hypothesis.signals),
            contradictions=[c.label for c in hypothesis.contradictions] if hypothesis.contradictions else [],
            target_id=target_id,
        )

        # Calcular economic score inmediatamente
        candidate.economic_score = self._scorer.score(candidate)

        return candidate

    def from_reasoner_result(
        self, result: Any, target_id: int = 0, min_priority: int = 3, max_candidates: int = 10
    ) -> list[AttackCandidate]:
        """Convierte un ReasonerResult completo en AttackCandidates priorizados.

        Args:
            result: ReasonerResult de OffensiveEngine.analyze_endpoint()
            target_id: ID del target en DB
            min_priority: Prioridad mínima (1-10) para filtrar
            max_candidates: Máximo de candidates a retornar

        Returns:
            Lista de AttackCandidates ordenados por prioridad
        """
        candidates: list[AttackCandidate] = []

        for hyp in getattr(result, "hypotheses", []):
            candidate = self.from_hypothesis(hyp, target_id=target_id)
            if candidate is not None:
                candidates.append(candidate)

        # Filtrar y ordenar por prioridad económica
        return self._scorer.filter_candidates(candidates, min_priority=min_priority, max_candidates=max_candidates)

    def from_endpoint(
        self,
        endpoint_data: dict[str, Any],
        target_id: int = 0,
        min_priority: int = 3,
        max_candidates: int = 5,
    ) -> list[AttackCandidate]:
        """Analiza un endpoint y devuelve AttackCandidates priorizados.

        Un solo paso: analyze + convert + score + filter.
        """
        result = self._offensive.analyze_endpoint(endpoint_data)
        return self.from_reasoner_result(result, target_id=target_id, min_priority=min_priority, max_candidates=max_candidates)

    # ── Full pipeline ──────────────────────────────────────────

    def validate_endpoint(
        self,
        endpoint_data: dict[str, Any],
        target_id: int = 0,
        session: Any = None,
        dry_run: bool = False,
        min_priority: int = 3,
    ) -> list[Any]:
        """Ciclo completo: analyze → convert → score → validate → promote.

        Args:
            endpoint_data: Dict con path, method, params, etc.
            target_id: ID del target en DB
            session: Sesión de DB para persistir Findings
            dry_run: Si True, no ejecuta requests reales
            min_priority: Prioridad mínima económica

        Returns:
            Lista de ValidationEngineResult
        """
        # 1. Generar hipótesis
        result = self._offensive.analyze_endpoint(endpoint_data)

        # 2. Convertir a candidates
        candidates = self.from_reasoner_result(result, target_id=target_id, min_priority=min_priority)

        if not candidates:
            logger.info("[BRIDGE] Ningún candidate superó el filtro económico para %s %s",
                       endpoint_data.get("method", "GET"), endpoint_data.get("path", ""))
            return []

        # 3. Completar datos de red para cada candidate
        for c in candidates:
            if not c.host and "host" in endpoint_data:
                c.host = endpoint_data["host"]
            if not c.base_url:
                scheme = "https"
                host = c.host or endpoint_data.get("host", "")
                if host:
                    c.base_url = f"{scheme}://{host}"
            if not c.param_values and "params" in endpoint_data:
                c.param_values = dict(endpoint_data.get("params", {}))

        # 4. Validar cada candidate
        results = []
        for candidate in candidates:
            logger.info(
                "[BRIDGE] Validando candidate #%d: %s %s (prioridad=%d, EV=$%.0f)",
                candidate.economic_score.priority,
                candidate.method,
                candidate.endpoint_path,
                candidate.economic_score.priority,
                candidate.economic_score.expected_value,
            )
            vresult = self._validator.run(candidate, session=session, dry_run=dry_run)
            results.append(vresult)

            # Feedback: si el reasoner acertó/falló
            if not dry_run and vresult.confidence is not None:
                was_confirmed = vresult.confidence.should_promote
                self._offensive.record_outcome(
                    candidate.vulnerability_type.value,
                    candidate.original_hypothesis_id,
                    was_confirmed=was_confirmed,
                )

        return results

    def validate_batch(
        self,
        endpoints: list[dict[str, Any]],
        target_id: int = 0,
        session: Any = None,
        dry_run: bool = False,
        min_priority: int = 3,
    ) -> list[Any]:
        """Valida múltiples endpoints en paralelo.

        Args:
            endpoints: Lista de dicts con path, method, params, host
            target_id: ID del target en DB
            session: Sesión de DB
            dry_run: Si True, no ejecuta requests
            min_priority: Prioridad mínima

        Returns:
            Lista de ValidationEngineResult (batch)
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # 1. Batch analyze
        self._offensive.set_context(endpoints)
        results: list[Any] = []

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(self.validate_endpoint, ep, target_id, session, dry_run, min_priority): ep
                for ep in endpoints
            }
            for future in as_completed(futures, timeout=120):
                try:
                    ep_results = future.result()
                    results.extend(ep_results)
                except Exception as exc:
                    ep = futures[future]
                    logger.warning("[BRIDGE] Batch validation failed for %s %s: %s",
                                 ep.get("method", "GET"), ep.get("path", ""), exc)

        results.sort(key=lambda r: r.candidate.economic_score.priority if r.candidate else 0, reverse=True)
        return results

    def record_outcome(self, engine_result: Any, target_id: int = 0) -> None:
        """Registra feedback del Validation Engine en el Learning Loop.

        Args:
            engine_result: ValidationEngineResult de engine.run()
            target_id: ID del target (opcional, extraído del candidate si existe)
        """
        from core.validation.learning import ValidationOutcome, record_outcome  # fmt: skip

        candidate = engine_result.candidate
        if not candidate:
            return

        outcome = ValidationOutcome(
            target_id=target_id or candidate.target_id or 0,
            target_name="",
            vulnerability_type=candidate.vulnerability_type.value
            if hasattr(candidate.vulnerability_type, "value")
            else str(candidate.vulnerability_type),
            confidence=engine_result.confidence.score if engine_result.confidence else 0.0,
            promoted=engine_result.promoted or False,
            severity="medium",
            endpoint_path=candidate.endpoint_path,
            method=candidate.method,
            duration_ms=engine_result.duration_ms,
            signals_count=len(engine_result.result.total_signals)
            if engine_result.result
            else 0,
            reproducible=engine_result.result.reproducible if engine_result.result else False,
        )
        record_outcome(outcome)
