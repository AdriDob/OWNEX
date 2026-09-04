"""Tests for Approval Gate."""

from __future__ import annotations

import pytest

from core.approval.gate import (
    POLICY_PRESETS,
    ActionType,
    ApprovalDecision,
    ApprovalGate,
    AutonomyPolicy,
    RiskLevel,
)


@pytest.fixture()
def gate():
    """Fresh ApprovalGate instance for each test."""
    return ApprovalGate()


class TestApprovalGatePolicies:
    """Tests for different autonomy policies."""

    def test_lite_policy_blocks_all(self, gate):
        """LITE policy should block all actions."""
        gate.set_policy(AutonomyPolicy.LITE)

        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 100, "HIGH", "MEDIUM")
        assert decision.approved is False
        assert "LITE policy" in decision.reason
        assert decision.requires_human_review is True
        assert decision.auto_approval_allowed is False

    def test_full_policy_allows_low_risk_bounty(self, gate):
        """FULL policy allows low-risk bounty with high trust."""
        gate.set_policy(AutonomyPolicy.FULL)

        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 50, "HIGH", "MEDIUM")
        assert decision.approved is True
        assert decision.auto_approval_allowed is True

    def test_full_policy_blocks_high_amount(self, gate):
        """FULL policy blocks amounts over limit."""
        gate.set_policy(AutonomyPolicy.FULL)

        decision = gate.request_approval(ActionType.ACCEPT_WORK, "opire", 200, "HIGH", "LOW")
        assert decision.approved is False
        assert "exceeds auto-approval limit" in decision.reason

    def test_full_policy_blocks_disallowed_platform(self, gate):
        """FULL policy blocks platforms not in allowed list."""
        gate.set_policy(AutonomyPolicy.FULL)

        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "unknown_platform", 50, "HIGH", "MEDIUM")
        assert decision.approved is False
        assert "not in allowed list" in decision.reason

    def test_full_policy_allows_accepted_platform(self, gate):
        """FULL policy allows platforms in allowed list."""
        gate.set_policy(AutonomyPolicy.FULL)

        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 50, "HIGH", "MEDIUM")
        assert decision.approved is True

    def test_full_policy_blocks_insufficient_trust(self, gate):
        """FULL policy blocks when trust level is insufficient."""
        gate.set_policy(AutonomyPolicy.FULL)

        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 50, "LOW", "MEDIUM")
        assert decision.approved is False
        assert "Trust level" in decision.reason

    def test_capital_policy_blocks_high_risk(self, gate):
        """CAPITAL policy blocks high-risk actions."""
        gate.set_policy(AutonomyPolicy.CAPITAL)

        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 100, "HIGH", "HIGH")
        assert decision.approved is False
        assert "Risk level" in decision.reason

    def test_capital_policy_blocks_financial(self, gate):
        """CAPITAL policy always requires human review for financial actions."""
        gate.set_policy(AutonomyPolicy.CAPITAL)
        # Add platform to allowed list for testing
        gate.update_config(allowed_platforms=["hackerone", "binance"])

        decision = gate.request_approval(ActionType.FINANCIAL_TRANSACTION, "binance", 100, "CRITICAL", "MEDIUM")
        assert decision.approved is False
        assert "human review" in decision.reason.lower()

    def test_capital_policy_allows_low_risk_pr(self, gate):
        """CAPITAL policy allows low-risk PR creation with medium trust."""
        gate.set_policy(AutonomyPolicy.CAPITAL)
        # CAPITAL has empty allowed_platforms by default, add github for testing
        gate._config.allowed_platforms = ["github"]

        decision = gate.request_approval(ActionType.CREATE_PR, "github", 0, "MEDIUM", "LOW")
        # CAPITAL requires human review for CREATE_PR
        assert decision.approved is False
        assert "human review" in decision.reason.lower()

    def test_platform_blocking(self, gate):
        """Platforms in blocked list are denied."""
        gate.set_policy(AutonomyPolicy.FULL)
        gate.update_config(blocked_platforms=["evil_platform"])

        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "evil_platform", 50, "HIGH", "MEDIUM")
        assert decision.approved is False
        assert "blocked" in decision.reason.lower()


class TestPolicyPresets:
    """Test that policy presets are correctly configured."""

    def test_lite_preset_exists(self):
        assert AutonomyPolicy.LITE in POLICY_PRESETS
        preset = POLICY_PRESETS[AutonomyPolicy.LITE]
        assert preset.policy == AutonomyPolicy.LITE
        assert preset.global_requires_human_review is True
        assert preset.default_max_auto_amount_usd == 0.0

    def test_full_preset_exists(self):
        assert AutonomyPolicy.FULL in POLICY_PRESETS
        preset = POLICY_PRESETS[AutonomyPolicy.FULL]
        assert preset.policy == AutonomyPolicy.FULL
        assert preset.global_requires_human_review is False
        assert preset.default_max_auto_amount_usd == 100.0

    def test_capital_preset_exists(self):
        assert AutonomyPolicy.CAPITAL in POLICY_PRESETS
        preset = POLICY_PRESETS[AutonomyPolicy.CAPITAL]
        assert preset.policy == AutonomyPolicy.CAPITAL
        assert preset.global_requires_human_review is True
        assert preset.default_max_auto_amount_usd == 50.0

    def test_preset_rules_exist(self):
        """Each preset should have rules for common action types."""
        for policy in [AutonomyPolicy.LITE, AutonomyPolicy.FULL, AutonomyPolicy.CAPITAL]:
            preset = POLICY_PRESETS[policy]
            assert ActionType.SUBMIT_BOUNTY in preset.rules
            assert ActionType.CREATE_PR in preset.rules
            assert ActionType.ACCEPT_WORK in preset.rules


class TestApprovalGateIntegration:
    """Integration tests for the ApprovalGate."""

    def test_switch_policy(self, gate):
        """Can switch between policies at runtime."""
        gate.set_policy(AutonomyPolicy.LITE)
        assert gate.get_policy() == AutonomyPolicy.LITE

        gate.set_policy(AutonomyPolicy.FULL)
        assert gate.get_policy() == AutonomyPolicy.FULL

        gate.set_policy(AutonomyPolicy.CAPITAL)
        assert gate.get_policy() == AutonomyPolicy.CAPITAL

    def test_update_config(self, gate):
        """Can update config parameters."""
        gate.set_policy(AutonomyPolicy.FULL)
        gate.update_config(default_max_auto_amount_usd=200.0)
        assert gate._config.default_max_auto_amount_usd == 200.0

    def test_blocked_platforms(self, gate):
        """Blocked platforms are respected."""
        gate.set_policy(AutonomyPolicy.FULL)
        gate.update_config(blocked_platforms=["bad_platform"])

        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "bad_platform", 50, "HIGH", "MEDIUM")
        assert decision.approved is False
        assert "blocked" in decision.reason.lower()

    def test_allowed_platforms_filter(self, gate):
        """Only allowed platforms are permitted when list is set."""
        gate.set_policy(AutonomyPolicy.FULL)
        gate.update_config(allowed_platforms=["hackerone", "bugcrowd"])

        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 50, "HIGH", "MEDIUM")
        assert decision.approved is True

        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "intigriti", 50, "HIGH", "MEDIUM")
        assert decision.approved is False
        assert "not in allowed list" in decision.reason

    def test_trust_level_check(self, gate):
        """Trust level must meet minimum requirement."""
        gate.set_policy(AutonomyPolicy.FULL)

        # High trust required, but only MEDIUM provided
        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 50, "MEDIUM", "MEDIUM")
        assert decision.approved is False
        assert "Trust level" in decision.reason

        # HIGH trust meets requirement
        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 50, "HIGH", "MEDIUM")
        assert decision.approved is True

    def test_amount_limit_check(self, gate):
        """Amount must not exceed limit."""
        gate.set_policy(AutonomyPolicy.FULL)

        # $50 under $200 limit (SUBMIT_BOUNTY rule) - should pass
        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 50, "HIGH", "MEDIUM")
        assert decision.approved is True

        # $300 over $200 limit (SUBMIT_BOUNTY rule) - should fail
        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 300, "HIGH", "MEDIUM")
        assert decision.approved is False
        assert "exceeds auto-approval limit" in decision.reason

    def test_risk_level_check(self, gate):
        """High risk actions are blocked."""
        gate.set_policy(AutonomyPolicy.FULL)

        decision = gate.request_approval(ActionType.FINANCIAL_TRANSACTION, "hackerone", 50, "HIGH", "HIGH")
        assert decision.approved is False
        assert "Risk level" in decision.reason

    def test_human_review_required(self, gate):
        """Actions marked as requiring human review are blocked from auto-approval."""
        gate.set_policy(AutonomyPolicy.FULL)

        # FINANCIAL_TRANSACTION requires human review in FULL policy
        decision = gate.request_approval(ActionType.FINANCIAL_TRANSACTION, "binance", 50, "HIGH", "HIGH")
        assert decision.approved is False
        assert decision.requires_human_review is True


class TestApprovalDecision:
    """Test the ApprovalDecision dataclass."""

    def test_decision_structure(self, gate):
        """Decision should have all required fields."""
        gate.set_policy(AutonomyPolicy.FULL)
        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 50, "HIGH", "MEDIUM")

        assert isinstance(decision, ApprovalDecision)
        assert hasattr(decision, "approved")
        assert hasattr(decision, "reason")
        assert hasattr(decision, "policy")
        assert hasattr(decision, "action_type")
        assert hasattr(decision, "platform")
        assert hasattr(decision, "amount_usd")
        assert hasattr(decision, "risk_level")
        assert hasattr(decision, "trust_level")
        assert hasattr(decision, "requires_human_review")
        assert hasattr(decision, "auto_approval_allowed")
        assert hasattr(decision, "timestamp")

    def test_decision_contains_context(self, gate):
        """Decision should contain context for debugging."""
        gate.set_policy(AutonomyPolicy.FULL)
        decision = gate.request_approval(ActionType.SUBMIT_BOUNTY, "hackerone", 50, "HIGH", "MEDIUM")

        assert decision.action_type == ActionType.SUBMIT_BOUNTY
        assert decision.platform == "hackerone"
        assert decision.amount_usd == 50
        assert decision.trust_level == "HIGH"
        assert decision.risk_level == RiskLevel.MEDIUM
