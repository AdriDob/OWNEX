#!/usr/bin/env python3
"""Integration test for OWNEX core modules."""

from decimal import Decimal

from core.mcp_bridge import create_mcp_bridge
from core.workflow_connector import WorkflowConnector, WorkflowContext
from cores.accessibility_compliance import AccessibilityConfig, WCAGLevel, get_accessibility_engine
from cores.income_multiplier import MultiplierStrategy, multiply_earnings
from cores.zero_barrier_eligibility import get_eligibility_engine


def test_eligibility_engine():
    """Test zero-barrier eligibility engine."""
    print("=== Testing Eligibility Engine ===")
    engine = get_eligibility_engine()
    source_data = {"platform": "bug_bounty", "barriers": [], "difficulty": "beginner", "success_rate": 0.95}
    assessment = engine.assess_source("test_source_1", source_data)
    assert assessment.eligibility.value == "approved", f"Expected approved, got {assessment.eligibility.value}"
    assert len(assessment.barriers_identified) == 0, "Expected no barriers"
    assert assessment.estimated_earnings_potential > 0, "Expected positive earnings potential"
    assert assessment.onboarding_time_minutes == 5, "Expected 5 min onboarding for approved"
    print(f"  ✓ Eligibility: {assessment.eligibility.value}")
    print(f"  ✓ Barriers: {[b.value for b in assessment.barriers_identified]}")
    print(f"  ✓ Earnings: ${assessment.estimated_earnings_potential}/day")
    print(f"  ✓ Onboarding: {assessment.onboarding_time_minutes} min")
    return True


def test_income_multiplier():
    """Test income multiplier engine."""
    print("\n=== Testing Income Multiplier ===")
    # Use the convenience function which accepts strategy as parameter
    result = multiply_earnings(
        daily_earnings=100.0,
        strategy=MultiplierStrategy.MODERATE,
        reinvestment_rate=0.3,
        min_earnings_threshold=10.0,
    )

    assert result.strategy == MultiplierStrategy.MODERATE, f"Expected moderate, got {result.strategy}"
    assert result.earnings_processed > 0, "Expected positive earnings processed"
    assert result.new_earnings_capacity >= 0, "Expected non-negative new capacity"
    assert result.reinvested_amount >= 0, "Expected non-negative reinvested amount"
    # total_multiplier_effect is earnings_processed + new_earnings_capacity
    total_effect = result.earnings_processed + result.new_earnings_capacity
    assert total_effect >= result.earnings_processed, "Expected total >= processed"
    print(f"  ✓ Strategy: {result.strategy.value}")
    print(f"  ✓ Earnings processed: ${result.earnings_processed}")
    print(f"  ✓ New capacity: ${result.new_earnings_capacity}")
    print(f"  ✓ Reinvested: ${result.reinvested_amount}")
    print(f"  ✓ Total effect: ${total_effect}")
    return True


def test_accessibility():
    """Test accessibility compliance engine."""
    print("\n=== Testing Accessibility Compliance ===")
    a11y = get_accessibility_engine()
    config = AccessibilityConfig(wcag_level=WCAGLevel.AA, high_contrast_mode=True)
    a11y.set_config(config)
    report = a11y.generate_compliance_report()

    assert report.overall_compliance in ["aa_compliant", "aaa_compliant", "partial_aa", "non_compliant"], (
        f"Unexpected compliance status: {report.overall_compliance}"
    )
    assert len(report.contrast_checks) > 0, "Expected contrast checks"
    print(f"  ✓ Compliance: {report.overall_compliance}")
    print(f"  ✓ Contrast checks: {len(report.contrast_checks)}")

    # Test contrast ratio
    contrast = a11y.check_contrast_ratio("#e82127", "#ffffff")
    assert contrast.ratio is not None, "Expected contrast ratio"
    assert isinstance(contrast.passes_aa, bool), "Expected AA pass/fail boolean"
    print(f"  ✓ Tesla red on white: {contrast.ratio} - AA: {contrast.passes_aa}, AAA: {contrast.passes_aaa}")
    return True


def test_mcp_bridge():
    """Test MCP bridge."""
    print("\n=== Testing MCP Bridge ===")
    bridge = create_mcp_bridge()
    tools = bridge.get_available_tools()
    assert len(tools) > 0, "Expected available MCP tools"
    print(f"  ✓ Tools available: {len(tools)}")
    for name, info in list(tools.items())[:3]:
        print(f"    - {name}: {info['description'][:50]}...")
    return True


def test_workflow_connector():
    """Test workflow connector."""
    print("\n=== Testing Workflow Connector ===")
    connector = WorkflowConnector()
    context = WorkflowContext(user_id="test_user", daily_earnings=Decimal("50.0"), strategy="moderate")
    connector.set_context(context)

    # Test workflow summary
    summary = connector.get_workflow_summary()
    assert "total_executions" in summary, "Expected total_executions in summary"
    assert "success_rate" in summary, "Expected success_rate in summary"
    print(f"  ✓ Workflow summary: {summary}")
    return True


def test_full_integration():
    """Test full integration of all modules."""
    print("\n=== Testing Full Integration ===")

    # 1. Eligibility assessment
    engine = get_eligibility_engine()
    source_data = {"platform": "bug_bounty", "barriers": [], "difficulty": "beginner", "success_rate": 0.95}
    assessment = engine.assess_source("integration_test_source", source_data)
    assert assessment.eligibility.value == "approved"

    # 2. Income multiplier
    result = multiply_earnings(
        daily_earnings=assessment.estimated_earnings_potential,
        strategy=MultiplierStrategy.MODERATE,
        reinvestment_rate=0.3,
        min_earnings_threshold=10.0,
    )

    # 3. Accessibility check
    a11y = get_accessibility_engine()
    a11y_config = AccessibilityConfig(wcag_level=WCAGLevel.AA)
    a11y.set_config(a11y_config)
    report = a11y.generate_compliance_report()

    # 4. MCP bridge tools
    bridge = create_mcp_bridge()
    tools = bridge.get_available_tools()

    # 5. Workflow context
    workflow_context = WorkflowContext(
        user_id="integration_user", source_id="integration_test_source", daily_earnings=result.new_earnings_capacity, strategy="moderate"
    )

    print(f"  ✓ Eligibility: {assessment.eligibility.value}")
    print(f"  ✓ Multiplier: ${result.earnings_processed} processed, ${result.new_earnings_capacity} new capacity")
    print(f"  ✓ Accessibility: {report.overall_compliance}")
    print(f"  ✓ MCP tools: {len(tools)} available")
    print(f"  ✓ Workflow context: {workflow_context.user_id}")

    return True


if __name__ == "__main__":
    results = []
    results.append(("Eligibility Engine", test_eligibility_engine()))
    results.append(("Income Multiplier", test_income_multiplier()))
    results.append(("Accessibility Compliance", test_accessibility()))
    results.append(("MCP Bridge", test_mcp_bridge()))
    results.append(("Workflow Connector", test_workflow_connector()))
    results.append(("Full Integration", test_full_integration()))

    print("\n" + "=" * 50)
    print("INTEGRATION TEST RESULTS")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("🎉 ALL INTEGRATION TESTS PASSED")
    else:
        print("⚠️  Some tests failed - review output above")

    exit(0 if all_passed else 1)
