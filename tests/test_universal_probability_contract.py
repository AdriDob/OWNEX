"""Tests for Universal Probability Contract."""

from __future__ import annotations

import pytest

from cores.direct_work_engine.probability_contract import (
    CategoryFunnel,
    EvidenceLabel,
    ProbabilityEstimate,
    ProbabilityType,
    get_all_funnels,
    get_categories_with_funnels,
    get_funnel,
    get_probability_types_for_category,
    get_stages_for_category,
    register_funnel,
)


class TestProbabilityType:
    def test_bug_bounty_types_exist(self):
        assert ProbabilityType.P_VALID == "p_valid"
        assert ProbabilityType.P_UNIQUE == "p_unique"
        assert ProbabilityType.P_ACCEPT == "p_accept"
        assert ProbabilityType.P_REWARD == "p_reward"
        assert ProbabilityType.P_PAYMENT == "p_payment"

    def test_dev_bounty_types_exist(self):
        assert ProbabilityType.P_ELIGIBLE == "p_eligible"
        assert ProbabilityType.P_QUALIFIED == "p_qualified"
        assert ProbabilityType.P_SELECTED == "p_selected"
        assert ProbabilityType.P_COMPLETION == "p_completion"
        assert ProbabilityType.P_ACCEPT == "p_accept"
        assert ProbabilityType.P_PAYMENT == "p_payment"

    def test_ai_training_types_exist(self):
        assert ProbabilityType.P_TASK_ASSIGNED == "p_task_assigned"

    def test_client_work_types_exist(self):
        assert ProbabilityType.P_LEAD == "p_lead"
        assert ProbabilityType.P_REPLY == "p_reply"
        assert ProbabilityType.P_PROPOSAL == "p_proposal"
        assert ProbabilityType.P_DELIVERY == "p_delivery"

    def test_employment_types_exist(self):
        assert ProbabilityType.P_APPLICATION == "p_application"
        assert ProbabilityType.P_RESPONSE == "p_response"
        assert ProbabilityType.P_INTERVIEW == "p_interview"
        assert ProbabilityType.P_OFFER == "p_offer"
        assert ProbabilityType.P_RETENTION == "p_retention"

    def test_investment_types_exist(self):
        assert ProbabilityType.P_THESIS == "p_thesis"
        assert ProbabilityType.P_EXECUTION == "p_execution"
        assert ProbabilityType.P_RETURN == "p_return"
        assert ProbabilityType.P_RISK == "p_risk"
        assert ProbabilityType.P_DRAWDOWN == "p_drawdown"

    def test_cross_category_reuse(self):
        # Same type used across categories
        assert ProbabilityType.P_ACCEPT == "p_accept"
        assert ProbabilityType.P_PAYMENT == "p_payment"
        assert ProbabilityType.P_COMPLETION == "p_completion"

    def test_category_agnostic(self):
        assert ProbabilityType.P_SUCCESS == "p_success"
        assert ProbabilityType.P_FAILURE == "p_failure"


class TestProbabilityTypeEnum:
    def test_all_types_are_strings(self):
        for pt in ProbabilityType:
            assert isinstance(pt.value, str)
            assert len(pt.value) > 0
