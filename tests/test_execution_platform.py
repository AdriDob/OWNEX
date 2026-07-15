from __future__ import annotations

from core.execution.contract import CapabilityContract, ContractEvent, ContractField, ContractPermission
from core.execution.intent import Intent, IntentStatus, IntentUrgency
from core.execution.models import (
    Approval,
    ApprovalStatus,
    Checkpoint,
    Edge,
    ExecutionContext,
    ExecutionResult,
    ExecutionState,
    Node,
    NodeResult,
    Workflow,
)
from core.execution.plan import ExecutionPlan, RollbackPlan, build_execution_plan
from core.execution.primitives import (
    ApprovalConfig,
    CapabilityConfig,
    CheckpointConfig,
    ConditionConfig,
    DecisionConfig,
    DelayConfig,
    LoopConfig,
    NotificationConfig,
    ParallelConfig,
    PrimitiveType,
    RetryConfig,
    RollbackConfig,
    StartConfig,
    TimeoutConfig,
    TriggerConfig,
    WaitConfig,
)
from core.execution.validation import (
    BaseValidator,
    ExecutionValidator,
    ValidationIssue,
    ValidationReport,
    ValidationResult,
)

# ── EP-1: Model tests ──────────────────────────────────────────────


class TestWorkflow:
    def test_create_empty(self) -> None:
        w = Workflow(name="test", description="desc")
        assert w.name == "test"
        assert w.description == "desc"
        assert len(w.id) == 24
        assert w.version == "0.1.0"

    def test_to_dict(self) -> None:
        w = Workflow(name="test")
        d = w.to_dict()
        assert d["name"] == "test"
        assert "nodes" in d
        assert "edges" in d
        assert "created_at" in d


class TestNode:
    def test_create(self) -> None:
        n = Node(id="n1", type=PrimitiveType.START.value, label="Start", config={"key": "val"})
        assert n.id == "n1"
        assert n.label == "Start"
        assert n.config["key"] == "val"

    def test_default_id(self) -> None:
        n = Node()
        assert len(n.id) == 12


class TestEdge:
    def test_create(self) -> None:
        e = Edge(id="e1", source_id="a", target_id="b", condition="x > 5")
        assert e.source_id == "a"
        assert e.target_id == "b"
        assert e.condition == "x > 5"


class TestExecutionContext:
    def test_create(self) -> None:
        ctx = ExecutionContext(workflow_id="wf1", execution_id="ex1", correlation_id="corr1")
        assert ctx.state == ExecutionState.PENDING

    def test_to_dict(self) -> None:
        ctx = ExecutionContext(workflow_id="wf1", execution_id="ex1", correlation_id="c1")
        ctx.variables["url"] = "https://example.com"
        d = ctx.to_dict()
        assert d["variables"]["url"] == "https://example.com"
        assert d["state"] == "pending"


class TestExecutionResult:
    def test_create(self) -> None:
        r = ExecutionResult(execution_id="ex1", workflow_id="wf1", status=ExecutionState.COMPLETED)
        assert r.status == ExecutionState.COMPLETED


class TestCheckpoint:
    def test_create(self) -> None:
        cp = Checkpoint(execution_id="ex1", node_id="n1", context_snapshot={"key": "val"})
        assert cp.execution_id == "ex1"
        assert len(cp.id) == 12


class TestApproval:
    def test_create(self) -> None:
        a = Approval(execution_id="ex1", node_id="n1", reason="Need approval")
        assert a.status == ApprovalStatus.PENDING

    def test_approve(self) -> None:
        a = Approval(execution_id="ex1", node_id="n1", status=ApprovalStatus.APPROVED, responded_by="admin")
        assert a.status == ApprovalStatus.APPROVED
        assert a.responded_by == "admin"


class TestNodeResult:
    def test_create(self) -> None:
        nr = NodeResult(node_id="n1", status=ExecutionState.COMPLETED, output={"data": "ok"})
        assert nr.node_id == "n1"
        assert nr.output["data"] == "ok"


# ── EP-2: Primitive config tests ─────────────────────────────────


class TestPrimitiveTypes:
    def test_all_types(self) -> None:
        types = [p.value for p in PrimitiveType]
        expected = [
            "start",
            "trigger",
            "condition",
            "decision",
            "capability",
            "wait",
            "delay",
            "retry",
            "timeout",
            "parallel",
            "loop",
            "persist",
            "approval",
            "notification",
            "checkpoint",
            "rollback",
            "end",
        ]
        assert types == expected

    def test_each_primitive_config(self) -> None:
        # Just verify each config dataclass instantiates without error
        assert StartConfig()
        assert TriggerConfig(event_type="test:event")
        assert ConditionConfig(expression="x > 5")
        assert DecisionConfig(model="copilot", prompt="Is this safe?")
        assert CapabilityConfig(capability="test:cap", timeout_ms=5000)
        assert WaitConfig(duration_ms=1000)
        assert DelayConfig(duration_ms=500)
        assert RetryConfig(max_retries=3, base_delay_ms=1000)
        assert TimeoutConfig(duration_ms=30000)
        assert ParallelConfig(branches=["a", "b"])
        assert LoopConfig(iteration_input="items", body_start="process")
        assert ApprovalConfig(required_level="operator")
        assert NotificationConfig(channel="email", title="Alert")
        assert CheckpointConfig(frequency="always")
        assert RollbackConfig(to_checkpoint="cp1")


# ── Intent tests ──────────────────────────────────────────────────


class TestIntent:
    def test_create(self) -> None:
        intent = Intent(text="Find IDOR vulnerabilities", urgency=IntentUrgency.HIGH)
        assert intent.status == IntentStatus.EXPRESSED
        assert intent.urgency == IntentUrgency.HIGH

    def test_status_transitions(self) -> None:
        intent = Intent(text="Test")
        intent.status = IntentStatus.ANALYZING
        assert intent.status == IntentStatus.ANALYZING
        intent.status = IntentStatus.DESIGNED
        assert intent.status == IntentStatus.DESIGNED

    def test_to_dict(self) -> None:
        intent = Intent(text="Scan target")
        d = intent.to_dict()
        assert d["text"] == "Scan target"


# ── Contract tests ────────────────────────────────────────────────


class TestCapabilityContract:
    def test_create(self) -> None:
        contract = CapabilityContract(
            name="Port Scanner",
            version="1.0.0",
            capability="capability:scan_port",
            description="Scans open ports on a target",
            inputs=[ContractField(name="target", type="string", description="Target host", required=True)],
            outputs=[ContractField(name="ports", type="array", description="Open ports")],
            events_published=[ContractEvent(event_type="scan:completed", direction="publishes")],
            permissions=[ContractPermission(resource="network", action="execute")],
        )
        assert contract.name == "Port Scanner"
        assert len(contract.inputs) == 1
        assert contract.inputs[0].name == "target"

    def test_to_dict(self) -> None:
        c = CapabilityContract(name="Test", capability="test:cap")
        d = c.to_dict()
        assert d["name"] == "Test"
        assert d["capability"] == "test:cap"


# ── Plan tests ────────────────────────────────────────────────────


class TestExecutionPlan:
    def test_create(self) -> None:
        w = Workflow(name="test")
        plan = build_execution_plan(workflow_id=w.id, workflow_name=w.name, node_ids=["start", "end"])
        assert plan.workflow_name == "test"
        assert plan.execution_order == ["start", "end"]
        assert plan.safe is True
        assert plan.validation_score == 100.0

    def test_rollback_plan(self) -> None:
        rp = RollbackPlan(available=True, strategy="restore", checkpoint_nodes=["cp1"])
        assert rp.available is True

    def test_to_dict(self) -> None:
        plan = ExecutionPlan(workflow_id="wf1", workflow_name="test", execution_order=["a", "b"])
        d = plan.to_dict()
        assert d["workflow_name"] == "test"
        assert "rollback" in d


# ── EP-3: Validation tests ───────────────────────────────────────


class TestValidationModels:
    def test_validation_issue(self) -> None:
        issue = ValidationIssue(type="error", code="TEST_ERR", message="Test error", node_id="n1")
        assert issue.type == "error"
        d = issue.to_dict()
        assert d["code"] == "TEST_ERR"

    def test_validation_result_score_penalties(self) -> None:
        # No issues → 100
        r = ValidationResult(validator_name="test")
        assert r.score == 100.0

        # 1 error → 85
        r.errors.append(ValidationIssue(type="error", code="E1", message="err"))
        assert r.score == 85.0

        # 1 error + 1 warning → 80
        r.warnings.append(ValidationIssue(type="warning", code="W1", message="warn"))
        assert r.score == 80.0

        # 1 error + 1 warning + 1 suggestion → 78
        r.suggestions.append(ValidationIssue(type="suggestion", code="S1", message="sug"))
        assert r.score == 78.0

    def test_validation_result_passed(self) -> None:
        r = ValidationResult(validator_name="test")
        assert r.passed is True
        r.errors.append(ValidationIssue(type="error", code="E1", message="err"))
        assert r.passed is True  # passed is a static field, not computed

    def test_validation_report_aggregation(self) -> None:
        r1 = ValidationResult(validator_name="v1")
        r2 = ValidationResult(validator_name="v2")
        r2.errors.append(ValidationIssue(type="error", code="E1", message="err"))
        report = ValidationReport(workflow_id="wf1", results=[r1, r2])
        assert report.error_count == 1
        assert report.warning_count == 0
        assert report.passed is False
        assert report.score < 100

    def test_validation_report_empty(self) -> None:
        report = ValidationReport(workflow_id="wf1")
        assert report.score == 100.0
        assert report.passed is True


class TestGraphValidator:
    def test_valid_workflow(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))
        report = ExecutionValidator.run(w)
        graph_result = [r for r in report.results if r.validator_name == "graph"][0]
        assert graph_result.score == 100.0
        assert len(graph_result.errors) == 0

    def test_no_start(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        report = ExecutionValidator.run(w)
        graph_result = [r for r in report.results if r.validator_name == "graph"][0]
        assert graph_result.score < 100
        assert any("GRAPH_NO_START" in e.code for e in graph_result.errors)

    def test_no_end(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        report = ExecutionValidator.run(w)
        graph_result = [r for r in report.results if r.validator_name == "graph"][0]
        assert any("GRAPH_NO_END" in e.code for e in graph_result.errors)

    def test_multiple_start(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="s1", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="s2", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="s1", target_id="end"))
        w.edges.append(Edge(id="e2", source_id="s2", target_id="end"))
        report = ExecutionValidator.run(w)
        graph_result = [r for r in report.results if r.validator_name == "graph"][0]
        assert any("GRAPH_MULTI_START" in e.code for e in graph_result.errors)

    def test_orphan_node(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.nodes.append(Node(id="orphan", type=PrimitiveType.CAPABILITY.value, config={"capability": "test"}))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))
        report = ExecutionValidator.run(w)
        graph_result = [r for r in report.results if r.validator_name == "graph"][0]
        assert any("GRAPH_ORPHAN" in w.code for w in graph_result.warnings)

    def test_cycle_detection(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="a", type=PrimitiveType.CAPABILITY.value, config={"capability": "test"}))
        w.nodes.append(Node(id="b", type=PrimitiveType.CAPABILITY.value, config={"capability": "test"}))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="a"))
        w.edges.append(Edge(id="e2", source_id="a", target_id="b"))
        w.edges.append(Edge(id="e3", source_id="b", target_id="a"))  # cycle!
        w.edges.append(Edge(id="e4", source_id="b", target_id="end"))
        report = ExecutionValidator.run(w)
        graph_result = [r for r in report.results if r.validator_name == "graph"][0]
        assert any("GRAPH_CYCLE" in e.code for e in graph_result.errors)


class TestTimeoutValidator:
    def test_excessive_node_timeout(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="cap", type=PrimitiveType.CAPABILITY.value, timeout_ms=9_999_999))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="cap"))
        w.edges.append(Edge(id="e2", source_id="cap", target_id="end"))
        report = ExecutionValidator.run(w)
        timeout_result = [r for r in report.results if r.validator_name == "timeout"][0]
        assert any("TIMEOUT_EXCEEDS_WORKFLOW_LIMIT" in e.code for e in timeout_result.errors)

    def test_non_positive_timeout(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="cap", type=PrimitiveType.CAPABILITY.value, timeout_ms=-1))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="cap"))
        w.edges.append(Edge(id="e2", source_id="cap", target_id="end"))
        report = ExecutionValidator.run(w)
        timeout_result = [r for r in report.results if r.validator_name == "timeout"][0]
        assert any("TIMEOUT_NON_POSITIVE" in e.code for e in timeout_result.errors)


class TestRetryValidator:
    def test_excessive_retries(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="retry", type=PrimitiveType.RETRY.value, config={"max_retries": 999}))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="retry"))
        w.edges.append(Edge(id="e2", source_id="retry", target_id="end"))
        report = ExecutionValidator.run(w)
        retry_result = [r for r in report.results if r.validator_name == "retry"][0]
        assert any("RETRY_EXCESSIVE_RETRIES" in e.code for e in retry_result.errors)

    def test_zero_retries(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="retry", type=PrimitiveType.RETRY.value, config={"max_retries": 0}))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="retry"))
        w.edges.append(Edge(id="e2", source_id="retry", target_id="end"))
        report = ExecutionValidator.run(w)
        retry_result = [r for r in report.results if r.validator_name == "retry"][0]
        assert any("RETRY_ZERO_RETRIES" in e.code for e in retry_result.errors)


class TestSecurityValidator:
    def test_plaintext_secret(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(
            Node(
                id="bad", type=PrimitiveType.CAPABILITY.value, config={"password": "supersecret", "capability": "test"}
            )
        )
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="bad"))
        w.edges.append(Edge(id="e2", source_id="bad", target_id="end"))
        report = ExecutionValidator.run(w)
        sec_result = [r for r in report.results if r.validator_name == "security"][0]
        assert any("SEC_PLAINTEXT_SECRET" in e.code for e in sec_result.errors)

    def test_trigger_no_event_filter(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="trig", type=PrimitiveType.TRIGGER.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="trig"))
        w.edges.append(Edge(id="e2", source_id="trig", target_id="end"))
        report = ExecutionValidator.run(w)
        sec_result = [r for r in report.results if r.validator_name == "security"][0]
        assert any("SEC_TRIGGER_NO_EVENT_FILTER" in w.code for w in sec_result.warnings)


class TestResourceValidator:
    def test_produces_estimate(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(
            Node(id="cap", type=PrimitiveType.CAPABILITY.value, config={"capability": "capability:llm_analyze"})
        )
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="cap"))
        w.edges.append(Edge(id="e2", source_id="cap", target_id="end"))
        report = ExecutionValidator.run(w)
        res_result = [r for r in report.results if r.validator_name == "resource"][0]
        # Should have at least the estimate suggestion
        assert any("RES_ESTIMATE" in s.code for s in res_result.suggestions)


class TestExecutionValidator:
    def test_run_convenience(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))
        report = ExecutionValidator.run(w)
        assert isinstance(report, ValidationReport)
        assert len(report.results) == 9  # all 9 validators

    def test_custom_validator(self) -> None:
        class CustomValidator(BaseValidator):
            name = "custom"

            def validate(self, workflow: Workflow) -> ValidationResult:
                r = ValidationResult(validator_name=self.name)
                if workflow.name == "bad":
                    r.errors.append(self._error("CUSTOM_ERR", "Bad name"))
                    r.passed = False
                return r

        w = Workflow(name="bad")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))

        ev = ExecutionValidator()
        ev.register(CustomValidator())
        report = ev.validate(w)
        custom_result = [r for r in report.results if r.validator_name == "custom"][0]
        assert any("CUSTOM_ERR" in e.code for e in custom_result.errors)


class TestBaseValidatorHelpers:
    def test_error_helper(self) -> None:
        class V(BaseValidator):
            name = "test"

            def validate(self, workflow: Workflow) -> ValidationResult:
                r = ValidationResult(validator_name=self.name)
                r.errors.append(self._error("ERR", "msg", node_id="n1"))
                return r

        w = Workflow(name="t")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))
        result = V().validate(w)
        assert result.errors[0].code == "ERR"
        assert result.errors[0].node_id == "n1"

    def test_warning_helper(self) -> None:
        class V(BaseValidator):
            name = "test"

            def validate(self, workflow: Workflow) -> ValidationResult:
                r = ValidationResult(validator_name=self.name)
                r.warnings.append(self._warning("WARN", "msg"))
                return r

        w = Workflow(name="t")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))
        result = V().validate(w)
        assert result.warnings[0].type == "warning"

    def test_suggestion_helper(self) -> None:
        class V(BaseValidator):
            name = "test"

            def validate(self, workflow: Workflow) -> ValidationResult:
                r = ValidationResult(validator_name=self.name)
                r.suggestions.append(self._suggestion("SUG", "msg"))
                return r

        w = Workflow(name="t")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))
        result = V().validate(w)
        assert result.suggestions[0].type == "suggestion"


class TestExecutionState:
    def test_all_states(self) -> None:
        states = [s.value for s in ExecutionState]
        assert "pending" in states
        assert "running" in states
        assert "completed" in states
        assert "failed" in states
        assert "cancelled" in states
        assert "rolling_back" in states
        assert "rolled_back" in states


class TestApprovalStatus:
    def test_all_statuses(self) -> None:
        statuses = [s.value for s in ApprovalStatus]
        assert "pending" in statuses
        assert "approved" in statuses
        assert "rejected" in statuses
        assert "expired" in statuses
