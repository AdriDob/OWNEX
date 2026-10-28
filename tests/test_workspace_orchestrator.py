"""Orchestrator §14: expected_net arithmetic + repeatability honesty."""

from __future__ import annotations

from cores.workspaces.orchestrator import WorkspacePick, WorkspaceQuote, orchestrate


class TestWorkspacePickEconomics:
    def test_quote_expected_net_is_arithmetic(self):
        pick = WorkspacePick(
            workspace_id="x",
            title="t",
            ev_per_hour=30.0,
            time_hours=2.0,
        )
        assert pick.expected_net_usd is None  # constructor doesn't compute
        assert pick.repeatability == "UNKNOWN"

    def test_orchestrate_quote_path_computes_net_and_keeps_repeatability(self):
        out = orchestrate(
            quotes={
                "droppinglabel": WorkspaceQuote(
                    workspace_id="droppinglabel",
                    p_cash=0.6,
                    ev_per_hour=25.0,
                    time_hours=2.0,
                    repeatability="UNKNOWN",
                    note="test quote",
                )
            }
        )
        picks = {p["workspace_id"]: p for p in out["picks"]}
        assert picks["droppinglabel"]["expected_net_usd"] == 50.0
        assert picks["droppinglabel"]["repeatability"] == "UNKNOWN"

    def test_orchestrate_never_raises_without_inputs(self):
        out = orchestrate()
        assert out["picks"] == []
        assert out["next_action"] is None
