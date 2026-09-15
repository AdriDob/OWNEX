"""L2: registry with 15 canonical $0 workspaces incl. AFFILIATE + LEAD_SERVICES + KNOWLEDGE_ASSETS."""

from __future__ import annotations

from cores.workspaces.registry import AutomationPolicy, WorkspaceRegistry, WorkspaceType


def _reg() -> WorkspaceRegistry:
    return WorkspaceRegistry()


class TestRegistryContents:
    def test_ten_canonical_types(self):
        reg = _reg()
        assert len(reg.list_all()) == 15
        assert reg.get_by_type(WorkspaceType.ASSET_FACTORY) is not None
        assert reg.get_by_type(WorkspaceType.PARTNERSHIP) is not None
        assert reg.get_by_type(WorkspaceType.AFFILIATE) is not None
        assert reg.get_by_type(WorkspaceType.LEAD_SERVICES) is not None
        assert reg.get_by_type(WorkspaceType.KNOWLEDGE_ASSETS) is not None
        assert reg.get_by_type(WorkspaceType.TRADING) is not None
        assert reg.get_by_type(WorkspaceType.BACKUP_INCOME) is not None

    def test_asset_factory_is_upside(self):
        ctx = _reg().get("asset_factory")
        assert ctx is not None
        assert ctx.automation_policy == AutomationPolicy.DRAFT_ONLY
        assert "construir 1 vez" in ctx.description
        assert ctx.priority == 6
        assert "micro_saas" in ctx.settings.get("tipos", [])

    def test_partnership_is_future_upside(self):
        ctx = _reg().get("partnership")
        assert ctx is not None
        assert ctx.automation_policy == AutomationPolicy.DRAFT_ONLY
        assert "Revenue share" in ctx.description or "revenue share" in ctx.description.lower()
        assert ctx.active is False
        assert "revenue_share" in ctx.settings.get("tipos", [])

    def test_zero_invest_trio_is_upside(self):
        reg = _reg()
        for ws_id in ("affiliate", "lead_services", "knowledge_assets"):
            ctx = reg.get(ws_id)
            assert ctx is not None
            assert ctx.automation_policy == AutomationPolicy.DRAFT_ONLY
            assert ctx.active is True
            assert ctx.settings.get("costo", 0) == 0

    def test_trading_is_paper_and_gated(self):
        ctx = _reg().get("trading")
        assert ctx is not None
        assert ctx.automation_policy == AutomationPolicy.DRAFT_ONLY
        assert ctx.settings.get("mode") == "paper"
        assert ctx.settings.get("leverage") is False
        assert ctx.settings.get("activation") == "explicit_human_arm_only"

    def test_backup_is_safety_net(self):
        ctx = _reg().get("backup_income")
        assert ctx is not None
        assert ctx.automation_policy == AutomationPolicy.DRAFT_ONLY
        assert "Zona Sur" in ctx.settings.get("zonas", [])
        bug_bounty = _reg().get("bug_bounty")
        assert bug_bounty is not None
        assert ctx.priority < bug_bounty.priority


class TestLinkage:
    def test_link_unlink_roundtrip(self):
        reg = _reg()
        assert reg.link_task("trading", "t-1") is True
        assert reg.link_opportunity("trading", "o-1") is True
        assert reg.link_revenue("trading", "r-1") is True
        assert reg.get_linked_tasks("trading") == {"t-1"}
        assert reg.unlink_task("trading", "t-1") is True
        assert reg.get_linked_tasks("trading") == set()

    def test_activate_deactivate(self):
        reg = _reg()
        assert reg.deactivate("content_factory") is True
        assert all(w.workspace_id != "content_factory" for w in reg.list_active())
        assert reg.activate("content_factory") is True
