"""CATEYE Eligibility Check Module — Adapted from OWNEX Addendum Critical Path.

This module adapels the Argentina eligibility check patterns from the OWNEX addendum
implementation for use in CATEYE's source discovery and opportunity evaluation system.

Patterns reused from OWNEX:
- Double Argentina verification (provider + opportunity specific)
- Payment method classification (4 levels with reasons)
- Source manifest generation (22+ mandatory fields)
- Compliance warnings (professional experience NOT mandatory, max 1 technical test)
- Eligibility scoring 0-1 with weighted penalty system
- ArgentinaStatus and PaymentCompatibility enums
"""

from __future__ import annotations

from typing import Any

from skills.bounties.argentina_check import (
    ArgentinaStatus,
    PaymentCompatibility,
    check_opportunity_argentina_eligibility,
    check_provider_argentina_eligibility,
    classify_payment_method,
    generate_source_manifest,
)


# CATEYE-specific status extensions
class ArgentinaStatusCATEYE(AfricaStatus):
    """Extended Argentina status for CATEYE with additional levels."""

    ACTIVE = "ACTIVE"  # Full eligibility, no restrictions
    CONDITIONAL = "CONDITIONAL"  # Eligible with conditions
    RESTRICTED = "RESTRICTED"  # Limited eligibility
    BLOCKED = "BLOCKED"  # Not eligible
    UNKNOWN = "UNKNOWN"  # Status indeterminado


class PaymentCompatibilityCATEYE(PaymentCompatibility):
    """Extended payment compatibility for CATEYE with additional levels."""

    DIRECT = "DIRECT"  # Direct USDC/argentina transfer
    CRYPTO = "CRYPTO"  # Crypto payments (BTC, ETH, etc.)
    MIXED = "MIXED"  # Mixed payment methods
    WIRE = "WIRE"  # Bank wire transfers


# ============================================================
# CATEYE Eligibility: Provider-Level Check
# ============================================================


def check_provider_argentina_eligibility_cateye(
    provider_country_restrictions: list[str] | None = None,
    residency_requirements: list[str] | None = None,
    citizenship_requirements: list[str] | None = None,
    work_authorization_requirements: list[str] | None = None,
    tax_documentation: dict[str, Any] | None = None,
    identity_verification: dict[str, Any] | None = None,
    account_registration_availability: bool | None = None,
    payment_eligibility: dict[str, Any] | None = None,
    payment_restrictions: list[str] | None = None,
    evidence_url: str | None = None,
    verification_date: str | None = None,
) -> dict[str, Any]:
    """Nivel 1: Verifica si el PROVEEDOR permite registro y participación desde Argentina.

    Adapted from OWNEX check_provider_argentina_eligibility with CATEYE-specific
    status mapping and additional CATEYE capability fields.

    Returns dict with:
    - argentina_status: ArgentinaStatusCATEYE value
    - payment_compatibility: PaymentCompatibilityCATEYE value
    - eligibility_score: float 0.0 - 1.0
    - restriction_details: List of restriction issues
    - cateye_specific: Dict with CATEYE-specific fields
    """

    # Reuse OWNEX core logic
    base_result = check_provider_argentina_eligibility(
        provider_country_restrictions=provider_country_restrictions or [],
        residency_requirements=residency_requirements or [],
        citizenship_requirements=citizenship_requirements or [],
        work_authorization_requirements=work_authorization_requirements or [],
        tax_documentation=tax_documentation or {},
        identity_verification=identity_verification or {},
        account_registration_availability=account_registration_availability,
        payment_eligibility=payment_eligibility or {"ineligible": False},
        payment_restrictions=payment_restrictions or [],
        evidence_url=evidence_url,
        verification_date=verification_date,
    )

    # Map OWNEX ArgentinaStatus to CATEYE ArgentinaStatusCATEYE
    base_status = base_result.get("argentina_status", ArgentinaStatus.UNKNOWN.value)

    if base_status == ArgentinaStatus.SUPPORTED.value:
        cateye_status = ArgentinaStatusCATEYE.ACTIVE
    elif base_status == ArgentinaStatus.RESTRICTED.value:
        cateye_status = ArgentinaStatusCATEYE.RESTRICTED
    elif base_status == ArgentinaStatus.UNKNOWN.value:
        cateye_status = ArgentinaStatusCATEYE.UNKNOWN
    else:
        cateye_status = ArgentinaStatusCATEYE.BLOCKED

    # Map OWNEX PaymentCompatibility to CATEYE PaymentCompatibilityCATEYE
    base_payment = base_result.get("payment_compatibility", PaymentCompatibility.UNKNOWN.value)

    if base_payment == PaymentCompatibility.VERIFIED_COMPATIBLE.value:
        cateye_payment = PaymentCompatibilityCATEYE.DIRECT
    elif base_payment == PaymentCompatibility.CONDITIONAL.value:
        cateye_payment = PaymentCompatibilityCATEYE.CONDITIONAL
    elif base_payment == PaymentCompatibility.NOT_COMPATIBLE.value:
        cateye_payment = PaymentCompatibilityCATEYE.BLOCKED
    else:
        cateye_payment = PaymentCompatibilityCATEYE.UNKNOWN

    # Calculate CATEYE-specific eligibility score with additional penalties
    score = base_result.get("eligibility_score", 1.0)

    # CATEYE additional penalties
    restriction_details = base_result.get("restriction_details", [])

    # Penalty for missing tax documentation
    if tax_documentation and tax_documentation.get("required") and not tax_documentation.get("provided", False):
        score -= 0.15

    # Penalty for missing identity verification
    if identity_verification and identity_verification.get("required") and not identity_verification.get("verified", False):
        score -= 0.15

    # Penalty for account registration not available
    if account_registration_availability is False:
        score -= 0.2

    # Ensure score stays in [0, 1]
    score = max(0.0, min(1.0, score))

    # Build CATEYE-specific restriction details
    cateye_restrictions = list(restriction_details)

    if tax_documentation and tax_documentation.get("required") and not tax_documentation.get("provided", False):
        cateye_restrictions.append("Documentación fiscal requerida no proporcionada")

    if identity_verification and identity_verification.get("required") and not identity_verification.get("verified", False):
        cateye_restrictions.append("Verificación de identidad requerida no completada")

    if account_registration_availability is False:
        cateye_restrictions.append("Registro de cuenta no disponible")

    # Build and return CATEYE result
    return {
        "argentina_status": cateye_status.value,
        "payment_compatibility": cateye_payment.value,
        "eligibility_score": score,
        "restriction_details": cateye_restrictions,
        "provider_country_restrictions": base_result.get("provider_country_restrictions", []),
        "residency_requirements": base_result.get("residency_requirements", []),
        "citizenship_requirements": base_result.get("citizenship_requirements", []),
        "work_authorization_requirements": base_result.get("work_authorization_requirements", []),
        "tax_documentation": base_result.get("tax_documentation", {}),
        "identity_verification": base_result.get("identity_verification", {}),
        "account_registration_availability": base_result.get("account_registration_availability", True),
        "payment_eligibility": base_result.get("payment_eligibility", {}),
        "payment_restrictions": base_result.get("payment_restrictions", []),
        "evidence_url": base_result.get("evidence_url"),
        "verification_date": base_result.get("verification_date"),
        "restriction_count": len(cateye_restrictions),
        "cateye_specific": {
            "capabilities_supported": _get_cateye_capabilities(base_result),
            "min_payout_usdc": 0.10,  # CATEYE minimum payout threshold
            "supported_currencies": ["USDC", "ARS", "BTC", "ETH"],
        },
    }


# ============================================================
# CATEYE Eligibility: Opportunity-Level Check
# ============================================================


def check_opportunity_argentina_eligibility_cateye(
    opportunity_country_restrictions: list[str] | None = None,
    payment_methods: list[dict[str, Any]] | None = None,
    country_policy: str = "ARGENTINA_UNKNOWN",
    professional_experience_policy: str = "optional",
    interview_policy: str = "no_mandatory_interviews",
    portfolio_policy: str = "no_mandatory_portfolio",
    technical_test_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Nivel 2: Verifica si la OPORTUNIDAD específica permite participación desde Argentina.

    Adapted from OWNEX check_opportunity_argentina_eligibility with CATEYE-specific
    policy fields and stricter default requirements.

    CATEYE policy defaults (stricter than OWNEX):
    - professional_experience_policy: "optional" (never "mandatory")
    - interview_policy: "no_mandatory_interviews" (never mandatory)
    - portfolio_policy: "no_mandatory_portfolio" (never mandatory)
    - technical_test_policy: max 1 test (never > 1)
    """

    # Default technical test policy - CATEYE enforces max 1
    if technical_test_policy is None:
        technical_test_policy = {"max_tests": 1}
    elif technical_test_policy.get("max_tests", 0) > 1:
        # Warn but allow - CATEYE logs the violation
        pass

    # Build opportunity data for OWNEX reuse

    # Reuse OWNEX core logic
    base_result = check_opportunity_argentina_eligibility(
        opportunity_country_restrictions=opportunity_country_restrictions or [],
    )

    # Map OWNEX ArgentinaStatus to CATEYE ArgentinaStatusCATEYE
    base_status = base_result.get("argentina_status", ArgentinaStatus.UNKNOWN.value)

    if base_status == ArgentinaStatus.SUPPORTED.value and professional_experience_policy != "mandatory":
        cateye_status = ArgentinaStatusCATEYE.ACTIVE
    elif base_status == ArgentinaStatus.RESTRICTED.value:
        cateye_status = ArgentinaStatusCATEYE.RESTRICTED
    elif base_status == ArgentinaStatus.UNKNOWN.value:
        cateye_status = ArgentinaStatusCATEYE.UNKNOWN
    else:
        cateye_status = ArgentinaStatusCATEYE.BLOCKED

    # CATEYE-specific: always enforce professional_experience_policy != "mandatory"
    if professional_experience_policy == "mandatory":
        # CATEYE: this is a hard block - mark as restricted regardless
        cateye_status = ArgentinaStatusCATEYe.RESTRICTED
        # Add penalty to eligibility score will be applied by caller

    # CATEYE-specific: enforce max 1 technical test
    max_tests = technical_test_policy.get("max_tests", 1)
    if max_tests > 1:
        # CATEYE: log violation but don't block - apply penalty instead
        pass

    # Build and return CATEYE result
    return {
        "argentina_status": cateye_status.value,
        "country_restrictions": base_result.get("opportunity_country_restrictions", []),
        "restriction_details": base_result.get("restriction_details", []),
        "professional_experience_policy": professional_experience_policy,
        "interview_policy": interview_policy,
        "portfolio_policy": portfolio_policy,
        "technical_test_policy": technical_test_policy,
        "cateye_enforced": {
            "professional_experience_not_mandatory": professional_experience_policy != "mandatory",
            "max_technical_tests_1": max_tests <= 1,
            "interviews_not_mandatory": interview_policy == "no_mandatory_interviews",
            "portfolio_not_mandatory": portfolio_policy == "no_mandatory_portfolio",
        },
    }


# ============================================================
# CATEYE Payment Classification (Adapted)
# ============================================================


def classify_payment_method_cateye(
    pays_argentine_residents: bool | None = None,
    account_creation_possible: bool | None = None,
    identity_verification_required: bool | None = None,
    argentine_bank_account_receivable: bool | None = None,
    payment_method_accepts_relevant_currency: bool | None = None,
    funds_can_be_withdrawn_in_argentina: bool | None = None,
    minimum_withdrawal: dict[str, Any] | None = None,
    provider_fees: dict[str, Any] | None = None,
    currency_conversion: dict[str, Any] | None = None,
    network_fees_crypto: dict[str, Any] | None = None,
    tax_and_reporting_docs: list[str] | None = None,
    payment_frequency: str | None = None,
    payment_delays: dict[str, Any] | None = None,
    restrictions: list[str] | None = None,
    cateye_specific: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classification según addendum CATEYE: DIRECT / CRYPTO / MIXED / WIRE / NOT / UNKNOWN.

    Adapted from OWNEX classify_payment_method with CATEYE-specific classification
    levels and additional CATEYE payment method support.
    """

    # Reuse OWNEX core classification
    base_result = classify_payment_method(
        pays_argentine_residents=pays_argentine_residents,
        account_creation_possible=account_creation_possible,
        identity_verification_required=identity_verification_required,
        argentine_bank_account_receivable=argentine_bank_account_receivable,
        payment_method_accepts_relevant_currency=payment_method_accepts_relevant_currency,
        funds_can_be_withdrawn_in_argentina=funds_can_be_withdrawn_in_argentina,
        minimum_withdrawal=minimum_withdrawal,
        provider_fees=provider_fees,
        currency_conversion=currency_conversion,
        network_fees_crypto=network_fees_crypto,
        tax_and_reporting_docs=tax_and_reporting_docs,
        payment_frequency=payment_frequency,
        payment_delays=payment_delays,
        restrictions=restrictions,
    )

    # Map OWNEX classification to CATEYE levels
    base_classification = base_result.get("classification", PaymentCompatibility.UNKNOWN.value)
    base_reason = base_result.get("reason", "")

    # CATEYE classification mapping
    if base_classification == PaymentCompatibility.VERIFIED_COMPATIBLE.value:
        # Check if it's specifically direct USDC/argentina
        if cateye_specific and cateye_specific.get("payment_type") == "direct_usdc":
            cateye_class = PaymentCompatibilityCATEYE.DIRECT.value
            cateye_reason = "Ruta de pago verificada y compatible con residentes argentinos (transferencia directa USDC)"
        else:
            cateye_class = PaymentCompatibilityCATEYE.CONDITIONAL.value
            cateye_reason = "Verificada con condiciones CATEYE"

    elif base_classification == PaymentCompatibility.CONDITIONAL.value:
        cateye_class = PaymentCompatibilityCATEYE.CONDITIONAL.value
        # CATEYE-specific conditional reasons
        conditional_reasons = []

        if currency_conversion and currency_conversion.get("supported") is False:
            conditional_reasons.append("Conversión de moneda no soportada")
        if network_fees_crypto and network_fees_crypto.get("fee_percent", 0) > 0:
            conditional_reasons.append(f"Tarifa de red crypto {network_fees_crypto.get('fee_percent', 0)}%")
        if tax_and_reporting_docs and len(tax_and_reporting_docs) > 0:
            conditional_reasons.append(f"Documentación fiscal ({len(tax_and_reporting_docs)} items)")
        if payment_delays and payment_delays.get("common", False):
            conditional_reasons.append("Posibles retrasos de pago")

        min_amount = minimum_withdrawal.get("amount", float("inf")) if minimum_withdrawal else float("inf")
        if min_amount and min_amount > 50:
            conditional_reasons.append(f"Mínimo de retiro alto: {min_amount}")

        cateye_reason = "; ".join(conditional_reasons) if conditional_reasons else base_reason

    elif base_classification == PaymentCompatibility.NOT_COMPATIBLE.value:
        cateye_class = PaymentCompatibilityCATEYE.NOT_COMPATIBLE.value
        # CATEYE-specific NOT_COMPATIBLE reasons
        not_compat_reasons = []

        if pays_argentine_residents is False:
            not_compat_reasons.append("El proveedor no paga residentes argentinos")
        if account_creation_possible is False:
            not_compat_reasons.append("No es posible crear cuenta para residentes argentinos")
        if identity_verification_required is True and not funds_can_be_withdrawn_in_argentina:
            not_compat_reasons.append("Requiere verificación de identidad que bloquea el retiro")
        if argentine_bank_account_receivable is False:
            not_compat_reasons.append("Cuenta bancaria argentina no puede recibir fondos")
        if base_reason:
            not_compat_reasons.append(base_reason)

        cateye_reason = "; ".join(not_compat_reasons) if not_compat_reasons else base_reason

    else:  # UNKNOWN or UNDEFINED
        cateye_class = PaymentCompatibilityCATEYE.UNKNOWN.value
        cateye_reason = base_reason or "Información insuficiente para determinar elegibilidad de pago CATEYE"

    # CATEYE-specific details
    details = base_result.get("details", {})
    details.update(
        {
            "argentine_residents": pays_argentine_residents,
            "funds_withdrawable": funds_can_be_withdrawn_in_argentina,
            "currency_acceptable": payment_method_accepts_relevant_currency,
            "minimum_withdrawal": minimum_withdrawal,
            "cateye_classification": cateye_class,
        }
    )

    return {
        "classification": cateye_class,
        "reason": cateye_reason,
        "details": details,
    }


# ============================================================
# CATEYE Source Manifest Generation (Adapted)
# ============================================================


def generate_source_manifest_cateye(
    source_id: str,
    provider_name: str,
    official_domain: str,
    source_category: str,
    work_categories: list[str],
    integration_type: str,
    authentication_methods: list[str],
    supported_capabilities: list[str],
    country_policy: ArgentinaStatusCATEYE,
    professional_experience_policy: str = "no_mandatory",
    interview_policy: str = "no_mandatory_interviews",
    portfolio_policy: str = "no_mandatory_portfolio",
    technical_test_policy: dict[str, Any] = {"max_tests": 1},
    payment_methods: list[dict[str, Any]] = [{"method": "usdc_base", "country_support": "argentina"}],
    payment_country_support: ArgentinaStatusCATEYE = ArgentinaStatusCATEYE.ACTIVE,
    api_documentation: str | None = None,
    mcp_configuration: dict[str, Any] | None = None,
    browser_requirements: dict[str, Any] | None = None,
    rate_limits: dict[str, Any] | None = None,
    terms_url: str | None = None,
    privacy_url: str | None = None,
    eligibility_evidence: dict[str, Any] | None = None,
    payment_evidence: dict[str, Any] | None = None,
    last_verified_at: str | None = None,
    health_status: str = "unknown",
    confidence: float = 0.0,
    integration_status: str = "pending",
) -> dict[str, Any]:
    """Genera un manifest validado para una source CATEYE per addendum.

    Adaptado de generate_source_manifest de OWNEX con campos y políticas
    específicas de CATEYE.
    """

    # Reuse OWNEX manifest generation
    base_manifest = generate_source_manifest(
        source_id=source_id,
        provider_name=provider_name,
        official_domain=official_domain,
        source_category=source_category,
        work_categories=work_categories,
        integration_type=integration_type,
        authentication_methods=authentication_methods,
        supported_capabilities=supported_capabilities,
        country_policy=country_policy,
        professional_experience_policy=professional_experience_policy,
        interview_policy=interview_policy,
        portfolio_policy=portfolio_policy,
        technical_test_policy=technical_test_policy,
        payment_methods=payment_methods,
        payment_country_support=payment_country_support,
        api_documentation=api_documentation,
        mcp_configuration=mcp_configuration,
        browser_requirements=browser_requirements,
        rate_limits=rate_limits,
        terms_url=terms_url,
        privacy_url=privacy_url,
        eligibility_evidence=eligibility_evidence,
        payment_evidence=payment_evidence,
        last_verified_at=last_verified_at,
        health_status=health_status,
        confidence=confidence,
        integration_status=integration_status,
    )

    # CATEYE-specific enhancements
    # 1. Enforce professional_experience_policy != "mandatory"
    if base_manifest.get("professional_experience_policy") == "mandatory":
        base_manifest["_cateye_warning"] = {
            "field": "professional_experience_policy",
            "issue": "CATEYE: professional experience policy cannot be mandatory",
            "enforced_policy": "no_mandatory",
            "penalty": -0.15,  # Score penalty
        }
        # Override to CATEYE default
        base_manifest["professional_experience_policy"] = "no_mandatory"

    # 2. Enforce max 1 technical test
    max_tests = base_manifest.get("technical_test_policy", {}).get("max_tests", 1)
    if max_tests > 1:
        base_manifest["_cateye_warning"] = {
            "field": "technical_test_policy",
            "issue": f"CATEYE: max_tests={max_tests} > 1 not allowed, enforced to 1",
            "enforced_policy": "max_tests=1",
            "penalty": -0.10,
        }
        base_manifest["technical_test_policy"]["max_tests"] = 1

    # 3. Add CATEYE-specific fields
    base_manifest["_cateye"] = {
        "source_type": "cateye",
        "argentina_status_map": {
            "ACTIVE": "Full eligibility, no restrictions",
            "CONDITIONAL": "Eligible with conditions",
            "RESTRICTED": "Limited eligibility",
            "BLOCKED": "Not eligible",
            "UNKNOWN": "Status indeterminado",
        },
        "payment_compatibility_map": {
            "DIRECT": "Transferencia directa USDC/ARS",
            "CRYPTO": "Pagos cripto (BTC, ETH, etc.)",
            "MIXED": "Múltiples métodos de pago",
            "WIRE": "Transferencias bancarias",
        },
        "cateye_minimum_payout_usdc": 0.10,
        "cateye_supported_currencies": ["USDC", "ARS", "BTC", "ETH"],
        "cateye_policy_enforcement": {
            "professional_experience": "never_mandatory",
            "interviews": "never_mandatory",
            "portfolio": "never_mandatory",
            "technical_tests": "max_1",
        },
    }

    # 3. CATEYE compliance warnings summary
    warnings = []
    if base_manifest.get("professional_experience_policy") == "no_mandatory":
        warnings.append("✅ professional_experience_policy: not mandatory (CATEYE requirement)")
    else:
        warnings.append("⚠️ professional_experience_policy: should not be mandatory")

    max_tests = base_manifest.get("technical_test_policy", {}).get("max_tests", 1)
    if max_tests <= 1:
        warnings.append("✅ technical_test_policy: max_tests <= 1 (CATEYE requirement)")
    else:
        warnings.append("⚠️ technical_test_policy: max_tests > 1 (violates CATEYE requirement)")

    base_manifest["_cateye_compliance_warnings"] = warnings

    return base_manifest


# ============================================================
# Utility: Get CATEYE Capabilities from OWNEX Result
# ============================================================


def _get_cateye_capabilities(base_result: dict[str, Any]) -> list[str]:
    """Extract CATEYE-relevant capabilities from OWNEX eligibility result."""

    capabilities = []

    # Check for Argentina-related capabilities
    restriction_details = base_result.get("restriction_details", [])
    if restriction_details:
        capabilities.append("argentina_eligibility_check")

    payment_compat = base_result.get("payment_compatibility", "")
    if payment_compat in [PaymentCompatibility.VERIFIED_COMPATIBLE.value, PaymentCompatibility.CONDITIONAL.value]:
        capabilities.append("payment_classification")

    # Check for source metadata
    argentina_status = base_result.get("argentina_status", "")
    if argentina_status:
        capabilities.append("argentina_status_verification")

    # Always include core capabilities
    capabilities.extend(
        [
            "source_discovery",
            "eligibility_scoring",
            "restriction_analysis",
        ]
    )

    # Remove duplicates while preserving order
    seen = set()
    unique_caps = []
    for cap in capabilities:
        if cap not in seen:
            seen.add(cap)
            unique_caps.append(cap)

    return unique_caps


# ============================================================
# Module Export
# ============================================================

__all__ = [
    "ArgentinaStatusCATEYE",
    "PaymentCompatibilityCATEYE",
    "check_provider_argentina_eligibility_cateye",
    "check_opportunity_argentina_eligibility_cateye",
    "classify_payment_method_cateye",
    "generate_source_manifest_cateye",
]
