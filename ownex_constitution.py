"""
OWNEX Constitution Module - Python Import Compatible Version

This is the Python-compatible version of the OWNEX Constitution for import by self-update system.
"""

CONSTITUTION_VERSION = "1.0"
LAST_UPDATED = "2026-07-30"

CONSTITUTIONAL_VIOLATIONS = {
    "never_break_system_stability": {
        "description": "Stability is the #1 priority. Never compromise system stability for new features, performance changes, or architectural modifications."
    },
    "never_lose_user_data": {
        "description": "Every operation MUST have atomic rollback capability. No data changes without full backup and restore capability."
    },
    "only_evidence_based_changes": {
        "description": "Never assume. Never guess. No changes without measurable evidence of improvement OR rigorous testing proving no regression."
    },
    "zero_tolerance_security": {
        "description": "Security vulnerabilities cannot be accepted as trade-offs for new functionality or performance gains. Always secure first. Always secure completely."
    },
    "never_degrade_user_experience": {
        "description": "Every change must demonstrably improve user experience OR maintain current UX levels exactly. No deceptive improvements or hidden regressions."
    },
    "always_transparent_changes": {
        "description": "Every change must be fully disclosed with complete documentation. Nothing secret. Nothing undocumented. Nothing hidden from users."
    },
    "risk_management_mandatory": {
        "description": "Risk assessment required for EVERY change. No change without documented risk analysis and mitigation strategies."
    },
    "maintain_backward_compatibility": {
        "description": "New changes MUST preserve ALL existing functionality. Never break existing working systems, integrations, or user data."
    },
    "performance_integrity_enforced": {
        "description": "Performance metrics cannot degrade. Every change must show performance improvement OR be rejected."
    },
    "compliance_legal_priority": {
        "description": "Every change must pass all compliance requirements including legal, regulatory, security, privacy, and ethical standards. Compliance non-negotiable."
    },
}

# Foundational principles would go here...
FOUNDER_PRINCIPLES = [
    "OODA LOOP EVOLUTION",
    "EVIDENCE DRIVEN SYSTEM",
    "GRADUATED AUTONOMY",
    "MINIMUM INTERVENTION PRINCIPLE",
    "SINGLE SOURCE OF TRUTH",
    "DELETE BEFORE CREATE",
    "CAPABILITY REGISTRY",
    "EVENT BUS UNIFICATION",
    "REVENUE AMPLIFICATION",
    "PRODUCTION-FIRST DESIGN",
    "SELF-HEALING CAPABILITY",
    "AUDIT EVERYTHING",
    "TRACEABILITY FORWARD",
    "LOG EVERYTHING",
    "CURRENT_TECHNOLOGY_PRIORITY",
    "HARDWARE_ABSTRACTION",
    "SCALABILITY_NATURAL",
    "USER_DECISION_CONTROL",
    "ROLE_BASED_ACCESS",
    "NOTIFICATION_MANDATE",
    "COMPONENTS_SMALL",
    "FUNCTIONS_SINGLE_PURPOSE",
    "SIMPLICITY_IS_PRIORITY",
    "CAPABILITY_REGISTRY",
    "EVENT_BUS_UNIFICATION",
    "MODULE_DEPENDENCY_TREE",
]

INTEGRATION_REQUIREMENTS = {
    "technical": [
        "Constitutional engine loads on startup",
        "Every change request passes constitutional validation",
        "Runtime enforcement of ALL principles",
        "Constitutional audit logging",
        "Integration with existing EventBus",
        "Compatibility with 7 existing AI agents",
    ]
}

# Export public API
__all__ = [
    "CONSTITUTION_VERSION",
    "LAST_UPDATED",
    "CONSTITUTIONAL_VIOLATIONS",
    "FOUNDER_PRINCIPLES",
    "INTEGRATION_REQUIREMENTS",
]
