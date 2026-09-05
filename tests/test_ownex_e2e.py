"""End-to-end test for OWNEX pipeline.

Tests the complete circuit:
  DISCOVER → RANK → TELL USER WHAT TO DO → HELP DO IT → RECORD PAID → LEARN → IMPROVE
"""

from __future__ import annotations


class TestOwnexE2EPipeline:
    """Test the complete OWNEX pipeline end-to-end."""

    def test_discovery_to_ranking(self):
        """Test that discovery produces ranked opportunities."""
        from cores.opportunity import get_engine

        engine = get_engine()
        opps = engine.get_all()

        # Even if empty, the engine should work
        assert isinstance(opps, list)

    def test_ranking_to_next_action(self):
        """Test that ranking produces a next best action."""
        from cores.modes.engine import OwnexMode, get_mode_engine

        engine = get_mode_engine()
        engine.set_mode(OwnexMode.LITE)

        config = engine.get_config()
        assert config.name == "LITE"
        assert config.show_next_action is True
        assert config.prioritize_ev is True

    def test_next_action_to_approval(self):
        """Test that next action can require approval."""
        from cores.approval.gates import ActionType, get_approval_gate

        gate = get_approval_gate()
        req = gate.request_approval(
            ActionType.SUBMIT_REPORT,
            "Submit report for finding #1",
            "IDOR vulnerability in API",
            risk_level="medium",
        )

        assert req is not None
        assert req.status == "pending"
        assert req.level.value == "confirmation"

    def test_approval_to_record(self):
        """Test that approval leads to recording."""
        from cores.approval.gates import ActionType, get_approval_gate
        from cores.learning.revenue_loop import get_revenue_loop

        gate = get_approval_gate()
        loop = get_revenue_loop()

        # Request approval
        req = gate.request_approval(
            ActionType.SUBMIT_REPORT,
            "Submit report for finding #2",
            "SQL injection in login",
            risk_level="high",
        )

        # Record the action
        action = loop.record_action(
            opportunity_id="finding_2",
            action_type="submit",
            title="Submit report for SQL injection",
            description="Login endpoint vulnerable to SQLi",
            human_minutes=15,
            expected_value=1000,
        )

        # Approve
        gate.approve(req.id, notes="Approved for submission")

        # Record result
        loop.record_result(action.id, actual_revenue=0, status="submitted")

        assert req.status == "approved"
        assert action.status == "submitted"

    def test_record_to_learn(self):
        """Test that recording leads to learning."""
        from cores.learning.revenue_loop import get_revenue_loop

        loop = get_revenue_loop()

        # Record action
        action = loop.record_action(
            opportunity_id="finding_3",
            action_type="investigate",
            title="Investigate XSS in search",
            description="Reflected XSS in search parameter",
            human_minutes=45,
            expected_value=300,
        )

        # Record result (accepted)
        loop.record_result(
            action.id,
            actual_revenue=500,
            status="paid",
            learning_tags=["xss", "search", "high_value"],
        )

        # Check learning
        assert len(loop.learnings) > 0
        last_learning = loop.learnings[-1]
        assert "insight" in last_learning

    def test_capital_engine_goals(self):
        """Test that capital engine tracks goals."""
        from cores.capital.engine import get_capital_engine

        engine = get_capital_engine()
        engine.update_state(
            net_worth=10000,
            cash=5000,
            monthly_income=4000,
            monthly_expenses=2000,
        )

        dashboard = engine.get_dashboard()

        assert dashboard["state"]["net_worth"] == 10000
        assert dashboard["state"]["monthly_savings"] == 2000
        assert dashboard["state"]["savings_rate"] == 50.0  # to_dict returns percentage
        assert len(dashboard["goals"]) >= 4
        assert dashboard["gap_to_million"] == 990000

    def test_mode_switching(self):
        """Test that modes actually change behavior."""
        from cores.modes.engine import OwnexMode, get_mode_engine

        engine = get_mode_engine()

        # Switch to LITE
        engine.set_mode(OwnexMode.LITE)
        config = engine.get_config()
        assert config.ui_density == "minimal"
        assert config.show_agents is False
        assert config.show_finance is False

        # Switch to FULL
        engine.set_mode(OwnexMode.FULL)
        config = engine.get_config()
        assert config.ui_density == "detailed"
        assert config.show_agents is True
        assert config.show_finance is True

        # Switch to CAPITAL
        engine.set_mode(OwnexMode.CAPITAL)
        config = engine.get_config()
        assert config.ui_density == "standard"
        assert config.show_capital is True
        assert config.prioritize_capital is True

    def test_adaptive_mode_recommendation(self):
        """Test that mode recommendation adapts to state."""
        from cores.modes.engine import get_mode_engine

        engine = get_mode_engine()

        # Low income → recommend LITE
        rec = engine.recommend_mode(monthly_income=500, monthly_target=5000)
        assert rec.recommended_mode.value == "lite"

        # Good income, low capital → recommend CAPITAL
        rec = engine.recommend_mode(
            monthly_income=5000,
            monthly_target=5000,
            capital=10000,
            capital_target=1000000,
        )
        assert rec.recommended_mode.value == "capital"

    def test_state_machine_lifecycle(self):
        """Test complete task lifecycle through state machine."""
        from cores.orchestrator.state_machine import TaskPriority, get_state_machine

        sm = get_state_machine()

        # Create task
        task = sm.create_task(
            "Investigate IDOR",
            "investigation",
            TaskPriority.HIGH,
        )
        assert task.state.value == "pending"

        # Plan (required before assign)
        from cores.orchestrator.state_machine import TaskState

        task.transition(TaskState.PLANNING, reason="Planned")

        # Assign
        sm.assign(task.id, "agent_researcher")
        assert task.state.value == "assigned"

        # Start
        sm.start(task.id)
        assert task.state.value == "executing"

        # Complete
        sm.complete(task.id, result={"findings": 1})
        assert task.state.value == "reviewing"

        # Approve
        sm.approve(task.id)
        assert task.state.value == "completed"

    def test_command_center_today(self):
        """Test that command center provides today view."""
        from cores.capital.engine import get_capital_engine
        from cores.learning.revenue_loop import get_revenue_loop
        from cores.modes.engine import get_mode_engine

        # Setup state
        ce = get_capital_engine()
        ce.update_state(net_worth=5000, monthly_income=3000, monthly_expenses=1500)

        me = get_mode_engine()
        me.set_mode("lite")

        loop = get_revenue_loop()
        loop.record_action(
            opportunity_id="test",
            action_type="investigate",
            title="Test action",
            description="Test",
            human_minutes=30,
            expected_value=200,
        )

        # All engines should work together
        cap = ce.get_dashboard()
        mode = me.get_config()
        metrics = loop.get_totals()

        assert cap["state"]["net_worth"] == 5000
        assert mode.name == "LITE"
        assert metrics["total_actions"] >= 1

    def test_full_circuit(self):
        """Test the complete circuit: discover → rank → next action → approve → record → learn."""
        from cores.approval.gates import ActionType, get_approval_gate
        from cores.capital.engine import get_capital_engine
        from cores.learning.revenue_loop import get_revenue_loop
        from cores.modes.engine import get_mode_engine

        # 1. Setup
        ce = get_capital_engine()
        ce.update_state(net_worth=0, monthly_income=0, monthly_expenses=1000)

        me = get_mode_engine()
        me.set_mode("lite")

        loop = get_revenue_loop()
        gate = get_approval_gate()

        # 2. Discover (simulated)
        # In real usage, this comes from OpportunityEngine

        # 3. Rank (simulated)
        # In real usage, this comes from PriorityEngine

        # 4. Next action
        config = me.get_config()
        assert config.show_next_action is True

        # 5. Approval
        req = gate.request_approval(
            ActionType.SUBMIT_REPORT,
            "Submit first report",
            "Found IDOR in user API",
            risk_level="medium",
        )
        assert req is not None

        # 6. Record action
        action = loop.record_action(
            opportunity_id="first_finding",
            action_type="submit",
            title="Submit IDOR report",
            description="IDOR in /api/users/{id}",
            human_minutes=20,
            expected_value=500,
        )

        # 7. Approve
        gate.approve(req.id, notes="First submission!")

        # 8. Record result
        loop.record_result(action.id, actual_revenue=0, status="submitted")

        # 9. Learn
        assert len(loop.learnings) > 0

        # 10. Verify state
        totals = loop.get_totals()
        assert totals["total_actions"] >= 1
        assert totals["total_human_minutes"] >= 20

        # 11. Check dashboard
        dashboard = loop.get_dashboard()
        assert dashboard["today"]["actions_taken"] >= 1
