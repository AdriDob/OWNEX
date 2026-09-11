"""L2: workspace income policies — roles, mix eligibility, mission ranking."""

from __future__ import annotations

from cores.workspaces.policies import (
    IncomeRole,
    allowed_in_income_mix,
    explain,
    income_role,
    rank_for_mission,
)
from cores.workspaces.registry import WorkspaceType


class TestIncomeRoles:
    def test_primary_engines(self):
        assert income_role(WorkspaceType.BUG_BOUNTY) == IncomeRole.PRIMARY
        assert income_role(WorkspaceType.DEV_BOUNTY) == IncomeRole.PRIMARY
        assert income_role(WorkspaceType.AI_TRAINING) == IncomeRole.PRIMARY

    def test_trading_is_capital_only(self):
        assert income_role(WorkspaceType.TRADING) == IncomeRole.CAPITAL_ONLY

    def test_backup_is_last_resort(self):
        assert income_role(WorkspaceType.BACKUP_INCOME) == IncomeRole.LAST_RESORT

    def test_ownex_core_is_not_income(self):
        assert income_role(WorkspaceType.OWNEX) == IncomeRole.CORE

    def test_optional_commercial(self):
        for ws in (
            WorkspaceType.DROPPINGLABEL,
            WorkspaceType.MERCADO_LIBRE,
            WorkspaceType.ADRIEL_WEBS,
            WorkspaceType.CONTENT_FACTORY,
        ):
            assert income_role(ws) == IncomeRole.UPSIDE


class TestAllowedInMix:
    def test_primary_needs_active(self):
        assert allowed_in_income_mix(WorkspaceType.BUG_BOUNTY, active=True) is True
        assert allowed_in_income_mix(WorkspaceType.BUG_BOUNTY, active=False) is False

    def test_trading_never_in_mix(self):
        assert allowed_in_income_mix(WorkspaceType.TRADING) is False
        assert allowed_in_income_mix(WorkspaceType.TRADING, include_optional=True) is False

    def test_backup_only_on_explicit_request(self):
        assert allowed_in_income_mix(WorkspaceType.BACKUP_INCOME) is False
        assert allowed_in_income_mix(WorkspaceType.BACKUP_INCOME, allow_last_resort=True) is True

    def test_optional_needs_flag(self):
        assert allowed_in_income_mix(WorkspaceType.ADRIEL_WEBS) is False
        assert allowed_in_income_mix(WorkspaceType.ADRIEL_WEBS, include_optional=True) is True

    def test_core_never(self):
        assert allowed_in_income_mix(WorkspaceType.OWNEX, include_optional=True) is False


class TestRankForMission:
    def test_excludes_trading_and_backup_by_default(self):
        ranked = rank_for_mission(list(WorkspaceType))
        assert WorkspaceType.TRADING not in ranked
        assert WorkspaceType.BACKUP_INCOME not in ranked
        assert WorkspaceType.OWNEX not in ranked
        assert WorkspaceType.BUG_BOUNTY in ranked

    def test_respects_priority_order(self):
        ranked = rank_for_mission(
            [WorkspaceType.AI_TRAINING, WorkspaceType.BUG_BOUNTY],
            priorities={WorkspaceType.AI_TRAINING: 9, WorkspaceType.BUG_BOUNTY: 3},
        )
        assert ranked[0] == WorkspaceType.AI_TRAINING

    def test_explain_mentions_rule(self):
        assert "PAPER" in explain(WorkspaceType.TRADING) or "capital" in explain(WorkspaceType.TRADING).lower()
        assert explain(WorkspaceType.BACKUP_INCOME) != ""
