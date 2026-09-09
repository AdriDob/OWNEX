"""QA Testing Cycle — Automated QA testing work cycle for OWNEX.

Coordinates: Test Plan → Test Execution → Evidence → Report → Follow-up
Integrates with KnowledgeCapture for iterative learning from test outcomes.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from core.cycles.knowledge_capture import KnowledgeCapture, LearningType
from core.cycles.models import Cycle, Task, TaskStatus

logger = logging.getLogger("ownex.cycles.qa")


def _get_cycle_service():
    from core.cycles.service import get_cycle_service

    return get_cycle_service()


# ── Test Case Data Structures ─────────────────────────────────────────


class TestCase:
    """A single QA test case — generated, structured, executable."""

    def __init__(
        self,
        title: str,
        description: str,
        target_type: str,
        target_id: int | None = None,
        endpoint: str | None = None,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        expected_status: int | None = None,
        expected_patterns: list[str] | None = None,
        severity: str = "medium",
        tags: list[str] | None = None,
        source_finding_id: int | None = None,
    ) -> None:
        self.title = title
        self.description = description
        self.target_type = target_type
        self.target_id = target_id
        self.endpoint = endpoint
        self.method = method.upper()
        self.params = params or {}
        self.headers = headers or {}
        self.body = body or {}
        self.expected_status = expected_status
        self.expected_patterns = expected_patterns or []
        self.severity = severity
        self.tags = tags or []
        self.source_finding_id = source_finding_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "params": self.params,
            "headers": self.headers,
            "body": self.body,
            "expected_status": self.expected_status,
            "expected_patterns": self.expected_patterns,
            "severity": self.severity,
            "tags": self.tags,
            "source_finding_id": self.source_finding_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestCase:
        return cls(
            title=data["title"],
            description=data.get("description", ""),
            target_type=data.get("target_type", "generic"),
            target_id=data.get("target_id"),
            endpoint=data.get("endpoint"),
            method=data.get("method", "GET"),
            params=data.get("params"),
            headers=data.get("headers"),
            body=data.get("body"),
            expected_status=data.get("expected_status"),
            expected_patterns=data.get("expected_patterns"),
            severity=data.get("severity", "medium"),
            tags=data.get("tags"),
            source_finding_id=data.get("source_finding_id"),
        )


class TestResult:
    """Result of executing a single QA test case."""

    def __init__(
        self,
        test_case: TestCase,
        passed: bool,
        actual_status: int | None = None,
        response_body: str | None = None,
        response_headers: dict[str, str] | None = None,
        error_message: str | None = None,
        duration_ms: float = 0.0,
        evidence_paths: list[str] | None = None,
        executed_at: str | None = None,
    ) -> None:
        self.test_case = test_case
        self.passed = passed
        self.actual_status = actual_status
        self.response_body = response_body
        self.response_headers = response_headers or {}
        self.error_message = error_message
        self.duration_ms = duration_ms
        self.evidence_paths = evidence_paths or []
        self.executed_at = executed_at or datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_case": self.test_case.to_dict(),
            "passed": self.passed,
            "actual_status": self.actual_status,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "evidence_paths": self.evidence_paths,
            "executed_at": self.executed_at,
        }


class QATestSuite:
    """A collection of related test cases forming a suite."""

    def __init__(
        self,
        name: str,
        description: str = "",
        test_cases: list[TestCase] | None = None,
        tags: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.test_cases = test_cases or []
        self.tags = tags or []
        self.config = config or {}

    def add_case(self, test_case: TestCase) -> None:
        self.test_cases.append(test_case)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "test_cases": [tc.to_dict() for tc in self.test_cases],
            "tags": self.tags,
            "config": self.config,
            "total_cases": len(self.test_cases),
        }


class QAReport:
    """Consolidated QA report — summary, metrics, per-suite breakdown."""

    def __init__(
        self,
        cycle_id: int,
        total_tests: int = 0,
        passed: int = 0,
        failed: int = 0,
        skipped: int = 0,
        duration_ms: float = 0.0,
        suites: list[dict[str, Any]] | None = None,
        failures: list[dict[str, Any]] | None = None,
        evidence_count: int = 0,
        summary: str = "",
        generated_at: str | None = None,
    ) -> None:
        self.cycle_id = cycle_id
        self.total_tests = total_tests
        self.passed = passed
        self.failed = failed
        self.skipped = skipped
        self.duration_ms = duration_ms
        self.suites = suites or []
        self.failures = failures or []
        self.evidence_count = evidence_count
        self.summary = summary
        self.generated_at = generated_at or datetime.now(UTC).isoformat()

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 1.0
        return self.passed / self.total_tests

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "pass_rate": self.pass_rate,
            "duration_ms": self.duration_ms,
            "suites": self.suites,
            "failures": self.failures,
            "evidence_count": self.evidence_count,
            "summary": self.summary,
            "generated_at": self.generated_at,
        }


# ── QA Cycle Service ──────────────────────────────────────────────────


class QATestCycle:
    """QA Testing Cycle — wraps automated QA testing as an OWNEX Work Cycle.

    Stages:
    1. TEST_PLAN — generate test cases from targets, endpoints, findings
    2. TEST_EXECUTION — execute test suites against live endpoints
    3. EVIDENCE — collect screenshots, logs, traces from test run
    4. REPORT — generate QA report with pass/fail metrics
    5. FOLLOW_UP — track retest after fixes, learn from outcomes
    """

    STAGE_ORDER = [
        "test_plan",
        "test_execution",
        "evidence",
        "report",
        "follow_up",
    ]

    def __init__(self) -> None:
        self._cycle_service = _get_cycle_service()
        self._knowledge = KnowledgeCapture()

    def ensure_cycle(self) -> Cycle:
        """Ensure the QA Testing cycle exists in DB."""
        cycle = self._cycle_service.get_by_slug("qa")
        if not cycle:
            cycle = self._cycle_service.create(
                {
                    "name": "QA Testing",
                    "slug": "qa",
                    "description": "Automated QA testing, regression, integration testing",
                    "category": "qa",
                    "enabled": True,
                    "priority": 90,
                    "status": "idle",
                    "config": {
                        "browser_agent_enabled": True,
                        "http_probe_enabled": True,
                        "auto_generate_cases": True,
                        "max_retest_attempts": 3,
                        "evidence_dir": "data/qa_evidence",
                        "screenshot_enabled": True,
                        "response_capture_enabled": True,
                        "follow_up_enabled": True,
                    },
                }
            )
            logger.info("Created QA Testing cycle")
        return cycle

    def start_cycle(self) -> Cycle:
        """Start the QA Testing cycle."""
        cycle = self.ensure_cycle()
        if cycle.status in ("running", "completed"):
            logger.warning("QA cycle already running or completed")
            return cycle

        self._create_stage_tasks(cycle.id)
        activated = self._cycle_service.activate(cycle.id, next_action="test_plan")
        logger.info("QA Testing cycle started")
        return activated

    def _create_stage_tasks(self, cycle_id: int) -> list[Task]:
        """Create tasks for each QA pipeline stage."""
        from core.database.manager import get_db_manager

        mgr = get_db_manager()
        db_session = mgr.get_session("cycles")

        tasks = []
        for i, stage in enumerate(self.STAGE_ORDER):
            task = Task(
                cycle_id=cycle_id,
                name=stage.replace("_", " ").title(),
                description=f"QA pipeline stage: {stage}",
                status=TaskStatus.PENDING.value,
                priority=100 - i,
                order=i,
                estimated_hours=self._estimate_hours(stage),
            )
            db_session.add(task)
            tasks.append(task)

        db_session.commit()
        for t in tasks:
            db_session.refresh(t)
        return tasks

    def _estimate_hours(self, stage: str) -> float:
        estimates = {
            "test_plan": 1.0,
            "test_execution": 3.0,
            "evidence": 1.0,
            "report": 1.0,
            "follow_up": 0.5,
        }
        return estimates.get(stage, 1.0)

    def advance_stage(self, cycle_id: int, stage: str, result: dict[str, Any] | None = None) -> Task | None:
        """Mark a stage complete and advance to next."""
        from core.database.manager import get_db_manager

        mgr = get_db_manager()
        db_session = mgr.get_session("cycles")

        try:
            tasks = db_session.query(Task).filter(Task.cycle_id == cycle_id).order_by(Task.order).all()
            current_task = None
            next_task = None

            for i, t in enumerate(tasks):
                if t.name.lower().replace(" ", "_") == stage:
                    current_task = t
                    if i + 1 < len(tasks):
                        next_task = tasks[i + 1]
                    break

            if not current_task:
                logger.warning("Stage %s not found in cycle %d", stage, cycle_id)
                return None

            current_task.status = TaskStatus.COMPLETED.value
            current_task.result = json.dumps(result or {})
            current_task.completed_at = datetime.now(UTC)

            if next_task:
                next_task.status = TaskStatus.RUNNING.value
                next_task.started_at = datetime.now(UTC)
                cycle = self._cycle_service.get(cycle_id)
                if cycle:
                    cycle.config_dict.update({"next_action": next_task.name.lower().replace(" ", "_")})
                    cycle.config = json.dumps(cycle.config_dict)

            db_session.commit()
            if current_task:
                db_session.refresh(current_task)
            logger.info("Advanced from %s to %s", stage, next_task.name if next_task else "COMPLETED")
            return current_task

        except Exception as e:
            db_session.rollback()
            logger.error("Failed to advance stage: %s", e)
            raise
        finally:
            db_session.close()

    # ── Stage 1: Test Plan / Test Case Generation ─────────────────────

    def generate_test_cases(
        self,
        target_ids: list[int] | None = None,
        endpoint_ids: list[int] | None = None,
        finding_ids: list[int] | None = None,
        include_regression: bool = True,
    ) -> QATestSuite:
        """Generate QA test cases from existing targets, endpoints, and findings.

        Scans the Rastro database for registered targets and endpoints,
        then produces structured TestCase objects for each.
        """
        suite = QATestSuite(
            name=f"QA Auto-Suite {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}",
            description="Auto-generated test suite from targets, endpoints, and findings",
            tags=["auto-generated", "regression"],
        )

        from database import db as db_mod

        session = db_mod.SessionLocal()
        try:
            from database.models import Endpoint, Finding, Target

            # ── Generate from targets ──
            target_query = session.query(Target)
            if target_ids:
                target_query = target_query.filter(Target.id.in_(target_ids))
            for target in target_query.all():
                suite.add_case(
                    TestCase(
                        title=f"Target reachability: {target.name}",
                        description=f"Verify target {target.name} ({target.domain or 'N/A'}) is reachable",
                        target_type="target",
                        target_id=target.id,
                        endpoint=target.domain or target.name,
                        method="GET",
                        expected_status=200,
                        severity="critical",
                        tags=["target", "reachability"],
                    )
                )

            # ── Generate from endpoints ──
            endpoint_query = session.query(Endpoint)
            if endpoint_ids:
                endpoint_query = endpoint_query.filter(Endpoint.id.in_(endpoint_ids))
            if target_ids:
                endpoint_query = endpoint_query.filter(Endpoint.target_id.in_(target_ids))
            for ep in endpoint_query.all():
                params_dict = ep.parsed_params
                suite.add_case(
                    TestCase(
                        title=f"Endpoint: {ep.method} {ep.path}",
                        description=f"QA test for endpoint {ep.method} {ep.path} (target {ep.target_id})",
                        target_type="endpoint",
                        target_id=ep.target_id,
                        endpoint=ep.path,
                        method=ep.method or "GET",
                        params=params_dict,
                        expected_status=200,
                        severity="high",
                        tags=["endpoint", "smoke"],
                    )
                )

            # ── Generate from findings ──
            finding_query = session.query(Finding)
            if finding_ids:
                finding_query = finding_query.filter(Finding.id.in_(finding_ids))
            for finding in finding_query.all():
                suite.add_case(
                    TestCase(
                        title=f"Finding regression: {finding.title}",
                        description=f"Regression test for finding '{finding.title}' (severity: {finding.severity})",
                        target_type="finding",
                        target_id=finding.target_id,
                        endpoint=finding.endpoint_id,
                        method="GET",
                        severity=finding.severity or "medium",
                        tags=["finding", "regression"],
                        source_finding_id=finding.id,
                    )
                )

            logger.info(
                "Generated %d test cases from %d targets, %d endpoints, %d findings",
                len(suite.test_cases),
                target_query.count() if not target_ids else len(target_ids),
                endpoint_query.count() if not endpoint_ids else len(endpoint_ids),
                finding_query.count() if not finding_ids else len(finding_ids),
            )
            return suite

        except Exception as e:
            logger.error("Failed to generate test cases: %s", e)
            raise
        finally:
            session.close()

    def _build_execution_config(self, test_suite: QATestSuite) -> dict[str, Any]:
        """Build run configuration from a test suite."""
        return {
            "suite_name": test_suite.name,
            "total_cases": len(test_suite.test_cases),
            "tags": test_suite.tags,
            "config": test_suite.config,
            "screenshot_enabled": True,
            "response_capture_enabled": True,
            "timeout_ms": 30000,
            "retry_on_failure": True,
            "max_retries": 2,
        }

    # ── Stage 2: Test Execution ───────────────────────────────────────

    def execute_test_suite(
        self,
        suite: QATestSuite,
        execution_config: dict[str, Any] | None = None,
    ) -> list[TestResult]:
        """Execute a test suite against endpoints.

        Runs each TestCase via HTTP probe, capturing responses, status codes,
        and timing. Results are returned as a list of TestResult objects.
        """
        import http.client
        import json as json_mod
        import urllib.error
        import urllib.parse
        import urllib.request
        import uuid
        from time import time

        results: list[TestResult] = []
        run_id = str(uuid.uuid4())[:8]
        start_time = time()

        logger.info("Executing suite '%s' (run-%s) with %d cases", suite.name, run_id, len(suite.test_cases))

        for tc in suite.test_cases:
            case_start = time()
            try:
                # Build URL
                base_url = tc.endpoint or "http://localhost"
                if tc.params:
                    query_string = urllib.parse.urlencode(tc.params)
                    url = f"{base_url}?{query_string}"
                else:
                    url = base_url

                req = urllib.request.Request(
                    url,
                    data=json_mod.dumps(tc.body).encode()
                    if tc.body and tc.method in ("POST", "PUT", "PATCH")
                    else None,
                    headers={
                        "User-Agent": "OWNEX-QA-Cycle/1.0",
                        "Accept": "application/json",
                        **tc.headers,
                    },
                    method=tc.method,
                )

                try:
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        resp_body = resp.read().decode("utf-8", errors="replace")
                        actual_status = resp.status
                        resp_headers = dict(resp.headers)
                        error_msg = None
                except urllib.error.HTTPError as e:
                    resp_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
                    actual_status = e.code
                    resp_headers = dict(e.headers)
                    error_msg = str(e)
                except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
                    resp_body = ""
                    actual_status = 0
                    resp_headers = {}
                    error_msg = str(e)

                duration = (time() - case_start) * 1000  # ms

                # Determine pass/fail
                passed = True
                if tc.expected_status is not None and actual_status != tc.expected_status:
                    passed = False
                if tc.expected_patterns:
                    for pattern in tc.expected_patterns:
                        if pattern not in resp_body:
                            passed = False
                            break

                result = TestResult(
                    test_case=tc,
                    passed=passed,
                    actual_status=actual_status,
                    response_body=resp_body[:2000],  # Truncate large bodies
                    response_headers=resp_headers,
                    error_message=error_msg,
                    duration_ms=round(duration, 2),
                    executed_at=datetime.now(UTC).isoformat(),
                )
                results.append(result)

                level = "PASS" if passed else "FAIL"
                logger.debug("  [%s] %s %s (%dms)", level, tc.method, tc.endpoint, round(duration))

            except Exception as e:
                duration = (time() - case_start) * 1000
                logger.error("  [ERROR] %s %s: %s", tc.method, tc.endpoint, e)
                results.append(
                    TestResult(
                        test_case=tc,
                        passed=False,
                        actual_status=None,
                        error_message=f"Unhandled execution error: {e}",
                        duration_ms=round(duration, 2),
                        executed_at=datetime.now(UTC).isoformat(),
                    )
                )

        total_duration = (time() - start_time) * 1000
        passed_count = sum(1 for r in results if r.passed)
        logger.info(
            "Suite '%s' complete: %d/%d passed (%.1f%%) in %.0fms",
            suite.name,
            passed_count,
            len(results),
            (passed_count / len(results) * 100) if results else 0,
            total_duration,
        )

        return results

    # ── Stage 3: Evidence Collection ──────────────────────────────────

    def collect_evidence(
        self,
        results: list[TestResult],
        cycle_id: int,
        evidence_dir: str | None = None,
    ) -> dict[str, Any]:
        """Collect evidence from test execution results.

        Captures response payloads, headers, error traces, and timing data.
        Stores evidence artifacts and returns a manifest of collected items.
        """
        import uuid
        from pathlib import Path

        from core.cycles.events import publish_cycle_event

        config = self._get_cycle_config(cycle_id)
        base_dir = evidence_dir or config.get("evidence_dir", "data/qa_evidence")
        run_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        run_dir = Path(base_dir) / f"run_{timestamp}_{run_id}"

        if not run_dir.exists():
            run_dir.mkdir(parents=True, exist_ok=True)

        evidence_manifest: dict[str, Any] = {
            "run_id": run_id,
            "timestamp": timestamp,
            "cycle_id": cycle_id,
            "artifacts": [],
            "total_evidence": 0,
            "path": str(run_dir),
        }

        for i, result in enumerate(results):
            tc = result.test_case
            artifact_dir = run_dir / f"case_{i:04d}"
            artifact_dir.mkdir(exist_ok=True)

            artifacts = []

            # Capture response body
            if result.response_body and config.get("response_capture_enabled", True):
                body_path = artifact_dir / "response_body.json"
                body_path.write_text(result.response_body, encoding="utf-8")
                artifacts.append(str(body_path))

            # Capture response headers
            if result.response_headers and config.get("response_capture_enabled", True):
                headers_path = artifact_dir / "response_headers.json"
                headers_path.write_text(json.dumps(result.response_headers, indent=2), encoding="utf-8")
                artifacts.append(str(headers_path))

            # Capture error trace
            if result.error_message:
                error_path = artifact_dir / "error.txt"
                error_path.write_text(result.error_message, encoding="utf-8")
                artifacts.append(str(error_path))

            # Capture result summary
            result_path = artifact_dir / "result.json"
            result_path.write_text(json.dumps(result.to_dict(), indent=2, default=str), encoding="utf-8")
            artifacts.append(str(result_path))

            # Log captured evidence
            result.evidence_paths = artifacts
            evidence_manifest["artifacts"].append(
                {
                    "case_index": i,
                    "test_title": tc.title,
                    "passed": result.passed,
                    "artifacts": artifacts,
                }
            )

        evidence_manifest["total_evidence"] = len(evidence_manifest["artifacts"])

        # Write manifest
        manifest_path = run_dir / "evidence_manifest.json"
        manifest_path.write_text(json.dumps(evidence_manifest, indent=2, default=str), encoding="utf-8")

        logger.info(
            "Collected evidence for %d test cases in %s",
            len(results),
            str(run_dir),
        )

        # Publish event
        publish_cycle_event(
            cycle_id=cycle_id,
            event_type="qa.evidence_collected",
            data={"run_id": run_id, "evidence_count": len(results), "path": str(run_dir)},
        )

        return evidence_manifest

    def _take_screenshot(
        self,
        url: str,
        output_path: str,
        timeout: int = 15,
    ) -> str | None:
        """Take a screenshot of a URL using browser automation (placeholder).

        In production, this integrates with Playwright/Selenium for real
        browser screenshots. Returns the path to the screenshot file.
        """
        logger.debug("Screenshot request for %s -> %s (simulated)", url, output_path)
        # NOTE: In production, replace with Playwright/Selenium driver:
        #   from playwright.sync_api import sync_playwright
        #   with sync_playwright() as p:
        #       browser = p.chromium.launch()
        #       page = browser.new_page()
        #       page.goto(url, timeout=timeout*1000)
        #       page.screenshot(path=output_path, full_page=True)
        #
        # For now we record the intent so evidence collection is aware.
        from pathlib import Path

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # Placeholder: write a metadata stub
        stub = {"url": url, "timestamp": datetime.now(UTC).isoformat(), "simulated": True}
        with open(output_path + ".json", "w") as f:
            json.dump(stub, f)
        return output_path

    # ── Stage 4: Report Generation ────────────────────────────────────

    def generate_report(
        self,
        results: list[TestResult],
        cycle_id: int,
        suite_name: str = "QA Test Suite",
    ) -> QAReport:
        """Generate a consolidated QA report from test execution results.

        Produces pass/fail metrics, per-suite breakdown, failure details,
        and a textual summary.
        """
        from pathlib import Path

        from core.cycles.events import publish_cycle_event

        total_duration = sum(r.duration_ms for r in results)
        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]

        # Build suite breakdown
        suites_map: dict[str, dict[str, Any]] = {}
        for r in results:
            tags_key = ",".join(sorted(r.test_case.tags)) if r.test_case.tags else "untagged"
            if tags_key not in suites_map:
                suites_map[tags_key] = {
                    "tags": r.test_case.tags or [],
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "duration_ms": 0.0,
                }
            suites_map[tags_key]["total"] += 1
            suites_map[tags_key]["duration_ms"] += r.duration_ms
            if r.passed:
                suites_map[tags_key]["passed"] += 1
            else:
                suites_map[tags_key]["failed"] += 1

        # Build failure details
        failure_details: list[dict[str, Any]] = []
        for r in failed:
            failure_details.append(
                {
                    "title": r.test_case.title,
                    "method": r.test_case.method,
                    "endpoint": r.test_case.endpoint,
                    "expected_status": r.test_case.expected_status,
                    "actual_status": r.actual_status,
                    "error_message": r.error_message,
                    "duration_ms": r.duration_ms,
                    "severity": r.test_case.severity,
                    "tags": r.test_case.tags,
                }
            )

        # Evidence count
        evidence_count = sum(len(r.evidence_paths) for r in results)

        # Summary text
        pass_rate = (len(passed) / len(results) * 100) if results else 0
        summary_lines = [
            f"QA Report for '{suite_name}'",
            f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            f"Results: {len(passed)} passed / {len(failed)} failed / {len(results)} total",
            f"Pass rate: {pass_rate:.1f}%",
            f"Total duration: {total_duration:.0f}ms",
            f"Evidence artifacts: {evidence_count}",
            "",
        ]
        if failed:
            summary_lines.append("Failed cases:")
            for f_ in failed:
                summary_lines.append(
                    f"  - [{f_.test_case.severity.upper()}] {f_.test_case.title}: "
                    f"{f_.error_message or f'Expected {f_.test_case.expected_status}, got {f_.actual_status}'}"
                )

        report = QAReport(
            cycle_id=cycle_id,
            total_tests=len(results),
            passed=len(passed),
            failed=len(failed),
            skipped=0,
            duration_ms=round(total_duration, 2),
            suites=list(suites_map.values()),
            failures=failure_details,
            evidence_count=evidence_count,
            summary="\n".join(summary_lines),
        )

        # Write report to file
        report_dir = Path("data/qa_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"qa_report_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(report.to_dict(), indent=2, default=str), encoding="utf-8")

        logger.info(
            "Generated QA report: %d/%d passed (%.1f%%) -> %s",
            len(passed),
            len(results),
            pass_rate,
            str(report_path),
        )

        # Publish event
        publish_cycle_event(
            cycle_id=cycle_id,
            event_type="qa.report_generated",
            data={
                "total_tests": len(results),
                "passed": len(passed),
                "failed": len(failed),
                "pass_rate": pass_rate,
                "report_path": str(report_path),
            },
        )

        return report

    # ── Stage 5: Follow-Up / Retest Tracking ──────────────────────────

    def track_follow_up(
        self,
        results: list[TestResult],
        cycle_id: int,
        max_attempts: int | None = None,
    ) -> dict[str, Any]:
        """Track retest after fixes for failed test cases.

        Records follow-up entries for each failed test, captures retest
        attempts, and integrates with KnowledgeCapture to learn from outcomes.
        """
        from core.cycles.events import publish_cycle_event

        config = self._get_cycle_config(cycle_id)
        max_attempts = max_attempts or config.get("max_retest_attempts", 3)

        failed_cases = [r for r in results if not r.passed]
        follow_ups: list[dict[str, Any]] = []

        for result in failed_cases:
            follow_up_entry = {
                "test_title": result.test_case.title,
                "target_type": result.test_case.target_type,
                "target_id": result.test_case.target_id,
                "endpoint": result.test_case.endpoint,
                "method": result.test_case.method,
                "severity": result.test_case.severity,
                "failure_reason": result.error_message or f"Status {result.actual_status}",
                "retest_attempts": 0,
                "max_attempts": max_attempts,
                "resolved": False,
                "created_at": datetime.now(UTC).isoformat(),
                "last_retest_at": None,
            }
            follow_ups.append(follow_up_entry)

            # Capture learning from failure
            self._capture_qa_learning(
                cycle_id=cycle_id,
                test_title=result.test_case.title,
                outcome="failed",
                details=result.error_message
                or f"Expected {result.test_case.expected_status}, got {result.actual_status}",
            )

        # Update cycle config with follow-up tracking
        cycle = self._cycle_service.get(cycle_id)
        if cycle:
            existing = cycle.config_dict
            existing["follow_ups"] = existing.get("follow_ups", []) + follow_ups
            cycle.config = json.dumps(existing)
            self._cycle_service.update(cycle_id, {"config": cycle.config})

        logger.info("Tracked %d follow-up items for cycle %d", len(follow_ups), cycle_id)

        publish_cycle_event(
            cycle_id=cycle_id,
            event_type="qa.follow_ups_tracked",
            data={"follow_up_count": len(follow_ups), "cycle_id": cycle_id},
        )

        return {
            "cycle_id": cycle_id,
            "follow_ups": follow_ups,
            "total_failed": len(failed_cases),
            "max_attempts": max_attempts,
        }

    def retest(
        self,
        follow_up: dict[str, Any],
        cycle_id: int,
    ) -> TestResult | None:
        """Retest a single follow-up item.

        Re-executes the test case for a previously failed item and
        returns the new result. Updates the follow-up tracking state.
        """
        test_case = TestCase.from_dict(
            {
                "title": follow_up["test_title"],
                "target_type": follow_up["target_type"],
                "target_id": follow_up.get("target_id"),
                "endpoint": follow_up.get("endpoint"),
                "method": follow_up.get("method", "GET"),
                "severity": follow_up.get("severity", "medium"),
                "tags": ["retest"],
            }
        )

        suite = QATestSuite(name="Retest Suite", test_cases=[test_case])
        results = self.execute_test_suite(suite)

        if not results:
            return None

        result = results[0]

        # Update follow-up record
        follow_up["retest_attempts"] = follow_up.get("retest_attempts", 0) + 1
        follow_up["last_retest_at"] = datetime.now(UTC).isoformat()
        if result.passed:
            follow_up["resolved"] = True
            self._capture_qa_learning(
                cycle_id=cycle_id,
                test_title=test_case.title,
                outcome="resolved",
                details="Retest passed after fix",
            )

        # Persist updated follow-ups
        cycle = self._cycle_service.get(cycle_id)
        if cycle:
            existing = cycle.config_dict
            follow_ups = existing.get("follow_ups", [])
            for fu in follow_ups:
                if fu["test_title"] == follow_up["test_title"]:
                    fu.update(follow_up)
                    break
            cycle.config = json.dumps(existing)
            self._cycle_service.update(cycle_id, {"config": cycle.config})

        return result

    def run_full_qa_cycle(
        self,
        target_ids: list[int] | None = None,
        endpoint_ids: list[int] | None = None,
        finding_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Run a complete QA cycle end-to-end.

        Convenience method that chains all stages:
          1. Generate test cases
          2. Execute tests
          3. Collect evidence
          4. Generate report
          5. Track follow-ups

        Returns a dict with all stage results.
        """
        cycle = self.start_cycle()
        cycle_id = cycle.id

        # Stage 1: Test Plan
        suite = self.generate_test_cases(
            target_ids=target_ids,
            endpoint_ids=endpoint_ids,
            finding_ids=finding_ids,
        )
        self.advance_stage(cycle_id, "test_plan", {"test_count": len(suite.test_cases)})

        # Stage 2: Test Execution
        results = self.execute_test_suite(suite)
        self.advance_stage(
            cycle_id,
            "test_execution",
            {
                "total": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
            },
        )

        # Stage 3: Evidence
        evidence = self.collect_evidence(results, cycle_id)
        self.advance_stage(cycle_id, "evidence", {"evidence_count": evidence["total_evidence"]})

        # Stage 4: Report
        report = self.generate_report(results, cycle_id, suite.name)
        self.advance_stage(
            cycle_id,
            "report",
            {
                "pass_rate": report.pass_rate,
                "total": report.total_tests,
                "report_generated_at": report.generated_at,
            },
        )

        # Stage 5: Follow-up
        follow_up = self.track_follow_up(results, cycle_id)
        self.advance_stage(cycle_id, "follow_up", {"follow_ups": len(follow_up["follow_ups"])})

        # Complete the cycle
        self._cycle_service.complete(cycle_id)

        logger.info("Full QA cycle %d completed", cycle_id)
        return {
            "cycle_id": cycle_id,
            "suite": suite.to_dict(),
            "results": [r.to_dict() for r in results],
            "evidence": evidence,
            "report": report.to_dict(),
            "follow_up": follow_up,
        }

    # ── Learning Integration ──────────────────────────────────────────

    def _capture_qa_learning(
        self,
        cycle_id: int,
        test_title: str,
        outcome: str,
        details: str,
    ) -> Any:
        """Capture QA test outcome as a learning entry.

        Integrates with KnowledgeCapture to persist testing knowledge
        for future cycle improvements.
        """
        entry = self._knowledge.create_entry(
            type_=LearningType.PATTERN,
            source_finding_id=None,
            source_target_id=None,
            platform="ownex_qa",
            program=None,
            vuln_type="qa_test",
            lesson=f"[QA] {test_title}: {outcome} — {details}",
            confidence=0.8 if outcome == "resolved" else 0.5,
            metadata={
                "cycle_id": cycle_id,
                "test_title": test_title,
                "outcome": outcome,
                "details": details,
                "source": "qa_cycle",
            },
        )
        logger.debug("Captured QA learning: %s -> %s", test_title, outcome)
        return entry

    def get_cycle_status(self) -> dict[str, Any]:
        """Get current QA cycle status with tasks."""
        cycle = self.ensure_cycle()
        tasks = self._cycle_service.get_metrics(cycle.id)
        return {
            "cycle": {"id": cycle.id, "name": cycle.name, "status": cycle.status},
            "stages": self.STAGE_ORDER,
            "metrics": tasks,
        }

    def _get_cycle_config(self, cycle_id: int) -> dict[str, Any]:
        """Get the JSON config dict for a cycle."""
        cycle = self._cycle_service.get(cycle_id)
        if not cycle:
            return {}
        return cycle.config_dict


# ── Singleton Instance ────────────────────────────────────────────────


_QA_CYCLE: QATestCycle | None = None


def get_qa_cycle() -> QATestCycle:
    """Get the global QATestCycle instance."""
    global _QA_CYCLE
    if _QA_CYCLE is None:
        _QA_CYCLE = QATestCycle()
    return _QA_CYCLE


# ── Registry Integration ──────────────────────────────────────────────


def register_qa_cycle(registry) -> None:
    """Register QA Testing cycle definition."""
    import contextlib

    from core.cycles.registry import CycleDefinition

    with contextlib.suppress(ValueError):
        registry.register(
            CycleDefinition(
                slug="qa",
                name="QA Testing",
                description="Automated QA testing, regression, integration testing",
                category="quality_assurance",
                priority=9,
                config={
                    "stages": ["test_plan", "test_execution", "evidence", "report", "follow_up"],
                    "browser_agent_enabled": True,
                    "http_probe_enabled": True,
                    "auto_generate_cases": True,
                    "screenshot_enabled": True,
                    "response_capture_enabled": True,
                    "follow_up_enabled": True,
                },
            )
        )
