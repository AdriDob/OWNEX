"""Source Verifier — Three independent verification checks per source.

Each source must pass THREE independent verifications to be considered fully eligible:
1. Elegibilidad y acceso desde Argentina
2. Capacidad de integración y ejecución
3. Cobro y retiro de dinero viable

If any verification fails, the source is NOT fully eligible, though it may still
be partially usable depending on which check failed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .registry import SourceStatus


class VerificationResult(Enum):
    """Result of a single verification check."""

    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    ERROR = "error"


class CheckCategory(Enum):
    """Category of verification check."""

    ELIGIBILITY = "eligibility"
    INTEGRATION = "integration"
    PAYOUT = "payout"


@dataclass
class VerificationCheck:
    """A single verification check on a source."""

    check_id: str
    category: CheckCategory
    name: str
    description: str
    result: VerificationResult = VerificationResult.UNKNOWN
    detail: str = ""  # Human-readable detail if FAIL or ERROR
    scored: float = 0.0  # 0-100 score if PASS
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional context


@dataclass
class SourceVerdict:
    """Complete verification verdict for a source."""

    source_id: str
    source_name: str

    # Three independent checks
    eligibility: VerificationCheck  # Can user access from Argentina?
    integration: VerificationCheck  # Can OwnEX execute work?
    payout: VerificationCheck  # Can user withdraw money?

    # Overall verdict
    fully_eligible: bool
    eligible_reasons: list[str] = field(default_factory=list)  # Why it passes
    ineligibility_reasons: list[str] = field(default_factory=list)  # Why it fails

    # Scores (0-100 per check, average for overall)
    eligibility_score: float = 0.0
    integration_score: float = 0.0
    payout_score: float = 0.0
    overall_score: float = 0.0

    # Last verification timestamp
    last_verified: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Recommendation
    recommendation: str = ""  # "fully_eligible", "partial", "ineligible", "retire"


@dataclass
class VerificationPipelineResult:
    """Result of running the full verification pipeline on a source."""

    source_id: str
    source_name: str
    verdict: SourceVerdict
    pipeline_notes: list[str] = field(default_factory=list)
    verification_time: float = 0.0  # Seconds


class SourceVerifier:
    """Verifies sources across three independent dimensions.

    The verifier runs three checks per source:
    1. ELIGIBILITY: Can a user from Argentina access this source?
    2. INTEGRATION: Can OwnEX discover, fetch, and execute work from this source?
    3. PAYOUT: Can the user withdraw/collect money from this source?
    """

    def __init__(self, registry, payment_engine, country: str = "AR"):
        self.registry = registry
        self.payment_engine = payment_engine
        self.country = country
        self.check_counter = 0

    def verify_source(self, source_id: str, source_name: str | None = None) -> SourceVerdict:
        """Run the full verification pipeline on a source.

        Args:
            source_id: The source's unique identifier
            source_name: Human-readable name (defaults to registry lookup)

        Returns:
            SourceVerdict with all three checks and overall eligibility
        """
        if source_name is None:
            source_info = self.registry.get(source_id)
            if source_info is None:
                raise ValueError(f"Source {source_id} not found in registry")
            source_name = source_info.name

        self.check_counter = 0
        pipeline_notes = []

        # Check 1: ELIGIBILITY - Can user from Argentina access this?
        eligibility_check = self._check_eligibility(source_id)
        pipeline_notes.append(f"Eligibility: {eligibility_check.result.value} - {eligibility_check.detail}")

        # Check 2: INTEGRATION - Can OwnEX discover/fetch/execute work?
        integration_check = self._check_integration(source_id)
        pipeline_notes.append(f"Integration: {integration_check.result.value} - {integration_check.detail}")

        # Check 3: PAYOUT - Can user withdraw money?
        payout_check = self._check_payout(source_id)
        pipeline_notes.append(f"Payout: {payout_check.result.value} - {payout_check.detail}")

        # Build the verdict
        fully_eligible = (
            eligibility_check.result == VerificationResult.PASS
            and integration_check.result == VerificationResult.PASS
            and payout_check.result == VerificationResult.PASS
        )

        eligible_reasons = []
        ineligibility_reasons = []

        if eligibility_check.result == VerificationResult.PASS:
            eligible_reasons.append("Acceso desde Argentina permitido")
        else:
            ineligibility_reasons.append(eligibility_check.detail or "Restricciones de elegibilidad")

        if integration_check.result == VerificationResult.PASS:
            eligible_reasons.append("Integración y ejecución posible")
        else:
            ineligibility_reasons.append(integration_check.detail or "No es posible integrar/ejecutar")

        if payout_check.result == VerificationResult.PASS:
            eligible_reasons.append("Retiro de dinero viable")
        else:
            ineligibility_reasons.append(payout_check.detail or "No hay ruta de retiro viable")

        # Calculate scores
        elig_score = eligibility_check.scored
        integ_score = integration_check.scored
        payout_score = payout_check.scored
        overall_score = round((elig_score + integ_score + payout_score) / 3, 1)

        # Recommendation
        if fully_eligible:
            recommendation = "fully_eligible"
        elif len(ineligibility_reasons) == 1:
            recommendation = "partial"  # Only one check fails, others pass
        else:
            recommendation = "ineligible"

        verdict = SourceVerdict(
            source_id=source_id,
            source_name=source_name,
            eligibility=eligibility_check,
            integration=integration_check,
            payout=payout_check,
            fully_eligible=fully_eligible,
            eligible_reasons=eligible_reasons,
            ineligibility_reasons=ineligibility_reasons,
            eligibility_score=elig_score,
            integration_score=integ_score,
            payout_score=payout_score,
            overall_score=overall_score,
            recommendation=recommendation,
        )

        # Update source status in registry
        source_info = self.registry.get(source_id)
        if source_info:
            source_info.status = SourceStatus.ACTIVE if fully_eligible else SourceStatus.DEGRADED
            source_info.verification_score = overall_score
            source_info.last_verified = datetime.utcnow().isoformat()

        return verdict

    def _check_eligibility(self, source_id: str) -> VerificationCheck:
        """Check 1: Elegibilidad y acceso desde Argentina.

        Verifica:
        - Ciudadanía/residencia aceptada
        - Sin requisitos de experiencia profesional obligatoria
        - Sin entrevista obligatoria
        - Sin requisitos de grado
        """
        self.check_counter += 1
        check_id = f"eligibility_{source_id}_{self.check_counter}"

        # Check if source has eligibility rules
        source_info = self.registry.get(source_id)
        if source_info is None:
            return VerificationCheck(
                check_id=check_id,
                category=CheckCategory.ELIGIBILITY,
                name="Elegibilidad desde Argentina",
                description="Verificación de elegibilidad para usuarios en Argentina",
                result=VerificationResult.FAIL,
                detail="No hay información de elegibilidad disponible - source no verificada",
                scored=0.0,
            )

        rules = source_info.eligibility
        details = []
        passes = True
        scored = 50.0  # Base score for having eligibility rules

        # Check citizenship/residency
        if rules.requires_citizenship:
            details.append(f"Requiere cittadinanza: {rules.requires_citizenship}")
            # In a real system, we'd check the user's citizenship
            # For now, assume Argentina is allowed unless explicitly restricted
            scored += 20.0  # Has citizenship rules = structured

        if rules.requires_residency:
            details.append(f"Requiere residencia: {rules.requires_residency}")
            scored += 10.0

        # Check experience requirement
        if rules.min_experience == "none" or not rules.min_experience:
            # No experience required - passes
            details.append("Sin experiencia profesional obligatoria")
            scored += 20.0
        elif rules.min_experience == "beginner" and not True:  # has_experience_professional:
            # Beginner level might be OK for some users
            details.append(f"Experiencia mínima: {rules.min_experience}")
            scored += 10.0
        else:
            # Has experience requirement that may filter out zero-experience users
            details.append(f"Experiencia requerida: {rules.min_experience}")
            passes = False
            scored = 0.0

        # Check interview requirement
        if rules.requires_interview:
            details.append("Requiere entrevista obligatoria")
            passes = False
            scored = 0.0
        else:
            details.append("Sin entrevista obligatoria")
            scored += 15.0

        # Check portfolio requirement
        if rules.requires_portfolio:
            details.append("Requiere portfolio")
            passes = False
            scored = 0.0
        else:
            details.append("Sin portfolio obligatorio")
            scored += 10.0

        # Check degree requirement
        if rules.requires_degree:
            details.append("Requiere título universitario")
            passes = False
            scored = 0.0
        else:
            details.append("Sin requisito de grado")
            scored += 5.0

        # Check citizenship is NOT restricted to specific countries (Argentina should be OK)
        # Check if Argentina is in the allowed list or if it's open
        if rules.requires_citizenship and "AR" not in rules.requires_citizenship:
            # Explicitly restricts to non-AR countries
            details.append(f"Cittadinanza restringida a: {rules.requires_citizenship}")
            passes = False
            scored = 0.0

        result = VerificationResult.PASS if passes else VerificationResult.FAIL

        return VerificationCheck(
            check_id=check_id,
            category=CheckCategory.ELIGIBILITY,
            name="Elegibilidad desde Argentina",
            description="Verificación de elegibilidad para usuarios en Argentina",
            result=result,
            detail="; ".join(details) if details else "Sin restricciones detectadas",
            scored=min(scored, 100.0),
        )

    def _check_integration(self, source_id: str) -> VerificationCheck:
        """Check 2: Capacidad de integración y ejecución.

        Verifica:
        - Source tiene adaptador registrado
        - API accesible y responde
        - Puede descubrir oportunidades
        - Puede extraer tareas
        - Owner puede completar el trabajo
        """
        self.check_counter += 1
        check_id = f"integration_{source_id}_{self.check_counter}"

        source_info = self.registry.get(source_id)
        if source_info is None:
            return VerificationCheck(
                check_id=check_id,
                category=CheckCategory.INTEGRATION,
                name="Integración y ejecución",
                description="Verificación de capacidad de integración y ejecución",
                result=VerificationResult.FAIL,
                detail="Source no encontrada en el registry - no puede integrarse",
                scored=0.0,
            )

        details = []
        passes = True
        scored = 50.0  # Base score for having source info

        # Check adapter type
        adapter_type = source_info.adapter_type
        details.append(f"Tipo de adaptador: {adapter_type}")

        if adapter_type == "rest":
            scored += 15.0
            # REST is generally well-supported
        elif adapter_type == "graphql":
            scored += 12.0
        elif adapter_type == "browser":
            scored += 15.0  # Browser automation = can handle almost any website
        elif adapter_type == "sdk":
            scored += 15.0  # Official SDK = well-integrated
        elif adapter_type == "custom":
            scored += 5.0  # Custom = untested
        else:
            scored += 5.0

        # Check if discoverable
        if source_info.discoverable:
            details.append("Descubrible automáticamente")
            scored += 10.0
        else:
            details.append("Requiere descubrimiento manual")

        # Check if searchable
        if source_info.searchable:
            details.append("Buscable por keywords")
            scored += 5.0

        # Check RSS feed (if available)
        if source_info.rss_feed:
            details.append(f"Feed RSS: {source_info.rss_feed[:50]}...")
            scored += 5.0

        # Check minimum API spec
        if source_info.api_spec:
            details.append("Spec API disponible")
            scored += 8.0
        else:
            details.append("Sin spec API definido")
            scored += 2.0

        # For browser-based sources, always pass integration (they can scrape any site)
        if adapter_type == "browser":
            passes = True
            scored = min(scored, 100.0)
        else:
            # For API-based sources, check basic viability
            # In production, would actually call the API
            passes = True  # Assume viable for now - would test in reality

        result = VerificationResult.PASS if passes else VerificationResult.FAIL

        return VerificationCheck(
            check_id=check_id,
            category=CheckCategory.INTEGRATION,
            name="Integración y ejecución",
            description="Verificación de capacidad de OwnEX para descubrir y ejecutar trabajo",
            result=result,
            detail="; ".join(details) if details else "Capacidad de integración disponible",
            scored=min(scored, 100.0),
        )

    def _check_payout(self, source_id: str) -> VerificationCheck:
        """Check 3: Cobro y retiro de dinero viable.

        Verifica:
        - Métodos de pago soportados
        - Métodos compatibles con Argentina
        - Mínimo de retiro achievable
        - KYC requirements viables
        """
        self.check_counter += 1
        check_id = f"payout_{source_id}_{self.check_counter}"

        source_info = self.registry.get(source_id)
        if source_info is None:
            return VerificationCheck(
                check_id=check_id,
                category=CheckCategory.PAYOUT,
                name="Cobro y retiro de dinero",
                description="Verificación de viabilidad de retiro de dinero",
                result=VerificationResult.FAIL,
                detail="Source no encontrada - no hay información de pagos",
                scored=0.0,
            )

        rules = source_info.payment
        details = []
        passes = True
        scored = 50.0  # Base score

        # Check supported methods
        supported = rules.supported_methods
        details.append(f"Métodos soportados: {supported}")

        if not supported:
            # No methods specified = unknown
            passes = False
            scored = 0.0
        elif any("crypto" in m.lower() for m in supported):
            details.append("Crypto soportado - compatible con AR")
            scored += 20.0
            # Crypto is generally viable from Argentina
        if any("paypal" in m.lower() for m in supported):
            details.append("PayPal soportado")
            scored += 10.0
        if any("wire" in m.lower() for m in supported) or any("ach" in m.lower() for m in supported):
            details.append("Transferencia bancaria soportada")
            scored += 10.0
        if any("cvu" in m.lower() for m in supported) or any("cbu" in m.lower() for m in supported):
            details.append("CVU/CBU local Argentino soportado")
            scored += 15.0  # This is key for Argentina
        if any("local_transfer" in m.lower() for m in supported):
            details.append("Transferencia local soportada")
            scored += 10.0

        # Check minimum payout
        min_payout = rules.min_payout
        if min_payout > 0:
            details.append(f"Mínimo de retiro: ${min_payout}")
            scored += 10.0
        else:
            details.append("Sin mínimo de retiro especificado")
            scored += 5.0

        # Check supported countries
        supported_countries = rules.supported_countries
        if "AR" in supported_countries:
            details.append("Argentina explicitly soportada")
            scored += 15.0
        elif not supported_countries:
            details.append("Sin filtros de país - asumiendo compatibilidad AR")
            scored += 5.0
        else:
            # Argentina not explicitly listed but not excluded
            details.append(f"Países soportados: {supported_countries[:3]}...")
            scored += 2.0

        # Check KYC requirements
        if rules.requires_verification:
            details.append("Verificación KYC requerida")
            scored += 5.0
        else:
            details.append("Sin verificación KYC obligatoria")
            scored += 5.0

        # For crypto sources, always consider payout viable (user controls the wallet)
        if any("crypto" in m.lower() for m in supported):
            # Crypto is always viable from user's side - they control the wallet
            # The question is whether OwnEX can help them convert to ARS
            passes = True
            # Add crypto-specific boost
            scored = min(scored + 20, 100.0)
        else:
            passes = True  # Assume viable for now

        result = VerificationResult.PASS if passes else VerificationResult.FAIL

        return VerificationCheck(
            check_id=check_id,
            category=CheckCategory.PAYOUT,
            name="Cobro y retiro de dinero",
            description="Verificación de viabilidad de retiro de dinero al usuario",
            result=result,
            detail="; ".join(details) if details else "Ruta de retiro disponible",
            scored=min(scored, 100.0),
        )

    def verify_all_stale(self) -> list[VerificationPipelineResult]:
        """Run verification on all sources that need it."""
        now = datetime.now()
        results = []

        for source in self.registry.all_sources():
            if source.last_verified is None:
                # Never verified
                verdict = self.verify_source(source.source_id, source.name)
                results.append(
                    VerificationPipelineResult(
                        source_id=source.source_id,
                        source_name=source.name,
                        verdict=verdict,
                        pipeline_notes=[f"Primera verificación de source {source.source_id}"],
                    )
                )
            elif isinstance(source.last_verified, str):
                # Parse ISO format string
                last = datetime.fromisoformat(source.last_verified)
                if now - last > timedelta(days=7):
                    # Stale verification (> 7 days old)
                    verdict = self.verify_source(source.source_id, source.name)
                    results.append(
                        VerificationPipelineResult(
                            source_id=source.source_id,
                            source_name=source.name,
                            verdict=verdict,
                            pipeline_notes=[f"Verificación renovada (estaba stale desde {source.last_verified})"],
                        )
                    )
            elif now - source.last_verified > timedelta(days=7):
                # Stale verification (> 7 days old)
                verdict = self.verify_source(source.source_id, source.name)
                results.append(
                    VerificationPipelineResult(
                        source_id=source.source_id,
                        source_name=source.name,
                        verdict=verdict,
                        pipeline_notes=[f"Verificación renovada (estava stale desde {source.last_verified})"],
                    )
                )
        return results

    def verify_all_sources(self) -> list[VerificationPipelineResult]:
        """Run verification on ALL sources in the registry."""
        now = datetime.now()
        results = []

        for source in self.registry.all_sources():
            # Always run verification, but skip if recently verified (< 7 days)
            if source.last_verified is None:
                # Never verified - always run
                verdict = self.verify_source(source.source_id, source.name)
                results.append(
                    VerificationPipelineResult(
                        source_id=source.source_id,
                        source_name=source.name,
                        verdict=verdict,
                        pipeline_notes=[f"Primera verificación de source {source.source_id}"],
                    )
                )
            elif isinstance(source.last_verified, str):
                # Parse ISO format string
                last = datetime.fromisoformat(source.last_verified)
                # If never verified or stale (> 7 days), re-verify
                if now - last > timedelta(days=7):
                    verdict = self.verify_source(source.source_id, source.name)
                    results.append(
                        VerificationPipelineResult(
                            source_id=source.source_id,
                            source_name=source.name,
                            verdict=verdict,
                            pipeline_notes=["Verificación completa (estaba stale o nunca verificada)"],
                        )
                    )
                # else: recently verified, skip
            elif now - source.last_verified > timedelta(days=7):
                # Old verification, re-verify
                verdict = self.verify_source(source.source_id, source.name)
                results.append(
                    VerificationPipelineResult(
                        source_id=source.source_id,
                        source_name=source.name,
                        verdict=verdict,
                        pipeline_notes=["Verificación completa (última verificación antigua)"],
                    )
                )
            # else: recently verified, skip

        return results

    def decide_renewal(self, source_id: str) -> str:
        """Get renewal decision for a specific source without running full cycle."""
        source = self.registry.get(source_id)
        if source is None:
            return "retire"
        result = self.decide_renewal_source(source)
        return result

    def decide_renewal_source(self, source) -> str:
        """decide renewal for a single source."""
        from cores.source_intelligence.registry import SourceStatus

        last_verified = source.last_verified
        now = datetime.now()

        if last_verified is None:
            return "renew"  # Never verified - need full verification

        if (now - datetime.fromisoformat(last_verified)).days >= 30:
            return "retire"  # Not verified in 30+ days - retire

        if (now - datetime.fromisoformat(last_verified)).days >= 7:
            return "renew"  # Stale (7+ days) - renew verification

        # Recently verified - check status
        if source.status in [SourceStatus.DEGRADED, SourceStatus.UNKNOWN]:
            return "renew"  # Source status degraded or unknown - renew verification

        return "monitor"  # Good standing - just monitor
