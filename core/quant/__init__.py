"""
Quant Research & Performance Lab - OWENEX v10.1

Main entry point for the Quant Research module.
Provides unified access to quant capabilities, crypto intelligence,
and strategy research functions.
"""

from typing import Any

from .research import (
    CRYPTO_PROVIDER_REGISTRY,
    INTEGRATION_REGISTRY,
    QUANT_CAPABILITIES,
    check_argentina_compatibility,
    check_argentina_compatibility_crypto,
    check_argentina_compatibility_quant,
    check_prerequisites,
    check_provider_health,
    get_crypto_provider,
    get_quant_capability,
    list_crypto_providers,
    list_quant_capabilities,
    registry_status,
)

__all__ = [
    "get_quant_capability",
    "list_quant_capabilities",
    "check_prerequisites",
    "QUANT_CAPABILITIES",
    "check_argentina_compatibility",
    "check_argentina_compatibility_quant",
    "check_argentina_compatibility_crypto",
    "get_crypto_provider",
    "list_crypto_providers",
    "check_provider_health",
    "CRYPTO_PROVIDER_REGISTRY",
    "INTEGRATION_REGISTRY",
    "registry_status",
]


def init_quant_lab() -> dict[str, Any]:
    """Initialize the Quant Research Lab and return status."""
    # Mark as installed/available
    INTEGRATION_REGISTRY["quant_lab"]["installed"] = True
    INTEGRATION_REGISTRY["quant_lab"]["status"] = "available"

    # Mark crypto as available for research
    INTEGRATION_REGISTRY["crypto_intelligence"]["installed"] = True
    INTEGRATION_REGISTRY["crypto_intelligence"]["status"] = "research_available"

    return {
        "quant_lab_status": "available",
        "quant_capabilities": len(QUANT_CAPABILITIES),
        "crypto_providers": len(CRYPTO_PROVIDER_REGISTRY),
        "argentina_compatible_quant": sum(1 for c in QUANT_CAPABILITIES.values() if c.get(" argentina_compatible", False)),
        "argentina_compatible_crypto": sum(1 for c in CRYPTO_PROVIDER_REGISTRY.values() if c.get(" argentina_compatible", False)),
        "initialization_timestamp": __import__("datetime").datetime.now().isoformat(),
        "message": "Quant Research & Performance Lab initialized - all modules available for selective integration",
    }


def get_research_summary() -> dict[str, Any]:
    """Get a comprehensive research summary for the UI."""
    return {
        "quant_lab": {
            "status": "available",
            "capabilities": list_quant_capabilities(),
            "total": len(QUANT_CAPABILITIES),
            "argentina_compatible": check_argentina_compatibility_quant(next(iter(QUANT_CAPABILITIES), None)),
        },
        "crypto_intelligence": {
            "status": "research_available",
            "providers": list_crypto_providers(),
            "total": len(CRYPTO_PROVIDER_REGISTRY),
            "argentina_compatible": sum(1 for c in CRYPTO_PROVIDER_REGISTRY.values() if c.get(" argentina_compatible", False)),
        },
        "hummingbot": {
            "paper_trading": True,
            "real_trading": False,
            "status": "available_with_isolation",
        },
        "hola_optimizer": {
            "status": "optional",
            "category": "parameter_optimization",
        },
        "drex_finance": {
            "status": "optional",
            "category": "decision_signals",
        },
        "overall": registry_status(),
    }


def validate_integration(name: str, integration_type: str = "quant") -> dict[str, Any]:
    """Validate a specific integration before connecting."""
    if integration_type == "quant":
        cap = get_quant_capability(name)
        if not cap:
            return {"valid": False, "error": f"Quant capability '{name}' not found"}

        prereqs = check_prerequisites(name)
        argentina = check_argentina_compatibility_quant(name)

        return {
            "valid": prereqs.get("ready_to_use", False) and argentina["argentina_compatible"],
            "capability": name,
            "status": cap["status"],
            "requirements": cap.get("requirements", []),
            "argentina_compatible": argentina["argentina_compatible"],
            "auto_trading": cap.get("auto_trading", False),
            "credentials_required": cap.get("credentials_required", False),
        }

    elif integration_type == "crypto":
        provider = get_crypto_provider(name)
        if not provider:
            return {"valid": False, "error": f"Crypto provider '{name}' not found"}

        health = check_provider_health(name)
        argentina = check_argentina_compatibility_crypto(name)

        return {
            "valid": health["status"] in ["connected", "research"] and argentina["argentina_compatible"],
            "provider": name,
            "api_available": health["api_available"],
            "mcp_available": health["mcp_available"],
            "argentina_compatible": argentina["argentina_compatible"],
            "status": health["status"],
            "rate_limit": health["rate_limit"],
            "requires_api_key": health["requires_api_key"],
        }

    return {"valid": False, "error": f"Unknown integration type: {integration_type}"}
