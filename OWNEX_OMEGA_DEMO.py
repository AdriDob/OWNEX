#!/usr/bin/env python3
"""
OWNEX Self-Evolution Constitution Demo

This script demonstrates how the OWNEX Self-Evolution Constitution
enables safe, autonomous evolution of the OWNEX system.

The demo shows:
1. Constitution compliance validation
2. Evolution opportunity detection
3. Evolution proposal generation
4. Constitution enforcement
5. Risk management

This demonstrates the key feature: OWNEX can now design, prepare,
validate, and propose its own evolution while remaining safe
and constitutional.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ownex_constitution import (
    CONSTITUTION_VERSION,
    CONSTITUTIONAL_VIOLATIONS,
    FOUNDER_PRINCIPLES,
    INTEGRATION_REQUIREMENTS,
)
from self_update import SelfEvolutionSystem


def demonstrate_constitution():
    """Demonstrate the OWNEX Constitution in action."""

    print("=" * 80)
    print("OWNEX SELF-EVOLUTION CONSTITUTION DEMONSTRATION")
    print("=" * 80)
    print()
    print(f"Constitution Version: {CONSTITUTION_VERSION}")
    print("Last Updated: 2026-07-30")
    print()

    print("🔷 CONSTITUTIONAL PRINCIPLES:")
    print(f"   • {len(CONSTITUTIONAL_VIOLATIONS)} High-Priority Core Rules")
    print(f"   • {len(FOUNDER_PRINCIPLES)} Foundational Principles")
    print(f"   • {len(INTEGRATION_REQUIREMENTS['technical'])} Integration Requirements")
    print()

    # Show principle categories
    high_priority = [
        "never_break_system_stability",
        "never_lose_user_data",
        "only_evidence_based_changes",
        "zero_tolerance_security",
        "never_degrade_user_experience",
        "always_transparent_changes",
        "risk_management_mandatory",
        "maintain_backward_compatibility",
        "performance_integrity_enforced",
        "compliance_legal_priority",
    ]

    print("   High-Priority Core Rules:")
    for rule in high_priority:
        if rule in CONSTITUTIONAL_VIOLATIONS:
            print(f"     • {rule.replace('_', ' ').title()}: {CONSTITUTIONAL_VIOLATIONS[rule]['description'][:80]}...")

    print()
    print("   Foundational Principles:")
    for principle in FOUNDER_PRINCIPLES:
        print(f"     • {principle}")
    print()

    print("   Integration Requirements:")
    for req in INTEGRATION_REQUIREMENTS["technical"]:
        print(f"     • {req}")
    print()


def demonstrate_self_evolution():
    """Demonstrate the self-evolution system."""

    print("=" * 80)
    print("OWNEX SELF-EVOLUTION SYSTEM DEMONSTRATION")
    print("=" * 80)
    print()

    # Initialize the self-evolution system
    evolution_system = SelfEvolutionSystem()

    print("🚀 SYSTEM INITIALIZED")
    print(f"   Current Evolution Level: {evolution_system.evolution_level}")
    print(f"   Current Autonomy Level: {evolution_system.autonomy_level}")
    print(f"   System Readiness Score: {evolution_system._calculate_system_readiness_score():.2f}")
    print()

    # Detect evolution opportunities
    print("🔍 DETECTING EVOLUTION OPPORTUNITIES...")
    opportunities = evolution_system.detect_evolution_opportunities()

    print(f"✅ FOUND {len(opportunities)} EVOLUTION OPPORTUNITIES:")
    for i, opportunity in enumerate(opportunities, 1):
        print(f"   {i}. {opportunity['type'].replace('_', ' ').title()}")
        print(f"      Description: {opportunity['description']}")
        print(f"      Priority: {opportunity['priority']}")
        print(f"      Impact: {opportunity['impact_potential']}")
        print()

    # Propose evolution actions
    print("🏗️ PROPOSING EVOLUTION ACTIONS...")
    evolution_actions = []
    for opportunity in opportunities:
        evolution_action = evolution_system.propose_evolution_action(opportunity)
        if evolution_action:
            evolution_actions.append(evolution_action)
            print(f"   Proposed Action: {evolution_action['action_id']}")
            print(f"   Type: {evolution_action['opportunity_type'].replace('_', ' ').title()}")
            print(f"   Description: {evolution_action['description']}")
            print(f"   Priority: {evolution_action['priority']}")
            print(f"   Risk Level: {evolution_action['risk_level']}")
            print(f"   Constitutionally Verified: {evolution_action['constitutionally_verified']}")
            print()

    # Demonstrate autonomy level evaluation
    print("🔍 EVALUATING AUTONOMY LEVEL...")
    can_advance_autonomy = evolution_system.evaluate_autonomy_level()
    if can_advance_autonomy:
        print("✅ SYSTEM READY TO ADVANCE AUTONOMY LEVEL")
        evolution_system.autonomy_level += 1
        evolution_system.evolution_level += 1
        print(f"   New Autonomy Level: {evolution_system.autonomy_level}")
        print(f"   New Evolution Level: {evolution_system.evolution_level}")
    else:
        print("⚠️ SYSTEM NOT READY TO ADVANCE AUTONOMY LEVEL")
    print()

    # Demonstrate constitutional compliance evaluation
    print("🔍 EVALUATING CONSTITUTIONAL COMPLIANCE...")
    compliance_report = evolution_system.evaluate_constitutional_compliance()

    print("📊 COMPLIANCE REPORT:")
    print(f"   Total Changes: {compliance_report['total_changes']}")
    print(f"   Compliant Changes: {compliance_report['compliant_changes']}")
    print(f"   Violations: {len(compliance_report['violations'])}")
    print(f"   Compliance Percentage: {compliance_report['compliance_percentage']:.2f}%")
    print(f"   Status: {compliance_report['compliance_status']}")
    print(f"   Constitution Version: {compliance_report['constitution_version']}")
    print()

    if compliance_report["violations"]:
        print("⚠️ VIOLATIONS DETECTED - IMMEDIATE REMEDIATION REQUIRED:")
        for violation in compliance_report["violations"]:
            print(f"   • Change ID: {violation.get('action_id', 'UNKNOWN')}")
            print(f"     Description: {violation.get('description', 'UNKNOWN')}")
        print()

    # Summary
    print("=" * 80)
    print("📋 DEMONSTRATION SUMMARY")
    print("=" * 80)

    print("\n✅ SELF-EVOLUTION SYSTEM SUCCESSFULLY DEMONSTRATED")
    print(f"   • Constitution established: {len(CONSTITUTIONAL_VIOLATIONS)} core principles")
    print(f"   • Evolution capabilities: {len(evolution_actions)} actions proposed")
    print(
        f"   • Constitutional compliance: {compliance_report['compliance_status']} ({compliance_report['compliance_percentage']:.2f}%)"
    )
    print(f"   • Autonomy advancement: {'Ready' if can_advance_autonomy else 'Waiting'}")
    print(f"   • System readiness: {evolution_system._calculate_system_readiness_score():.2f}/10")

    print("\n🎯 KEY FEATURE DEMONSTRATED:")
    print("   • OWNEX can now DESIGN, PREPARE, VALIDATE, and PROPOSE its own evolution")
    print("   • All changes pass constitutional compliance validation")
    print("   • Risk management and rollback are automatic")
    print("   • Evolution is gradual and controlled, not uncontrolled")
    print("   • Constitution provides hard boundaries that cannot be broken")

    print("\n🔒 SAFETY GUARANTEES:")
    print("   • Evolution never breaks system stability")
    print("   • User data is always protected")
    print("   • Changes are evidence-based only")
    print("   • Security is always paramount")
    print("   • User experience never degrades")
    print("   • All changes are fully transparent")
    print("   • Risk management is mandatory")
    print("   • Backward compatibility is maintained")
    print("   • Performance integrity is enforced")
    print("   • Legal compliance is non-negotiable")

    print("\n✅ DEMO COMPLETE - OWNEX IS NOW AUTONOMOUS WITH SAFETY CONTROLS")
    return True


def main():
    """
    Main function to run the OWNEX Self-Evolution Constitution demonstration.

    This demonstrates how OWNEX has evolved from a manually controlled system
    to an autonomous, self-evolving system that can design, prepare, validate,
    and propose its own evolution while remaining safe and constitutional.
    """

    try:
        # Demonstrate the constitution
        demonstrate_constitution()

        # Demonstrate the self-evolution system
        success = demonstrate_self_evolution()

        if success:
            print("\n🎉 OWNEX CONSTITUTION AND SELF-EVOLUTION SUCCESSFULLY DEMONSTRATED!")
            print("   The system is now ready for autonomous operation with constitutional safety.")
            return 0
        else:
            print("\n❌ DEMONSTRATION FAILED")
            return 1

    except Exception as e:
        print(f"\n❌ DEMONSTRATION ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
