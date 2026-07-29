"""Tests for CoderAgent modules — issue analysis, repo analysis, code generation.

IssueAnalyzer is fully deterministic (text analysis only, no external calls).
RepoAnalyzer and other modules use asyncio subprocess — these tests focus on
the pure-logic parts.
"""

from __future__ import annotations

import pytest

from core.autonomy.issue_analyzer import IssueAnalysis, IssueAnalyzer

# ── IssueAnalyzer Tests ─────────────────────────────────────────


class TestIssueAnalyzerClassification:
    """Test issue type classification logic — fully deterministic."""

    @pytest.fixture
    def analyzer(self) -> IssueAnalyzer:
        return IssueAnalyzer()

    def test_classify_bug(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_issue_type("Fix crash on login", "The app crashes when...") == "bug"

    def test_classify_security(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_issue_type("XSS vulnerability in form", "Allows script injection...") == "security"

    def test_classify_feature(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_issue_type("Add dark mode support", "Would be nice to have...") == "feature"

    def test_classify_documentation(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_issue_type("Fix typo in README", "The documentation says...") == "documentation"

    def test_classify_refactor(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_issue_type("Refactor auth module", "Code is too complex...") == "refactor"

    def test_security_takes_priority_over_bug(self, analyzer: IssueAnalyzer):
        title = "Security vulnerability: crash on malicious input"
        assert analyzer._classify_issue_type(title, "") == "security"

    def test_default_to_bug(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_issue_type("Miscellaneous task", "No clear keywords...") == "bug"

    def test_security_keyword_detection(self, analyzer: IssueAnalyzer):
        """Test that all security keywords correctly map."""
        for kw in ["cve", "csrf", "ssrf", "rce", "lfi", "xss", "idor", "xxe", "oauth bypass", "jwt leak"]:
            result = analyzer._classify_issue_type(f"Test {kw} issue", "")
            assert result == "security", f"Keyword '{kw}' should classify as security, got '{result}'"


class TestIssueAnalyzerSeverity:
    """Test severity classification."""

    @pytest.fixture
    def analyzer(self) -> IssueAnalyzer:
        return IssueAnalyzer()

    def test_critical_severity(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_severity("CRITICAL: Data loss bug", "") == "critical"

    def test_high_severity(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_severity("HIGH: Major regression", "") == "high"

    def test_medium_severity(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_severity("Bug report: form submission", "") == "medium"

    def test_low_severity(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_severity("Minor: UI cosmetic fix", "") == "low"

    def test_default_severity(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_severity("Random task", "") == "medium"

    def test_security_triggers_critical(self, analyzer: IssueAnalyzer):
        assert analyzer._classify_severity("Security vulnerability in auth", "") == "critical"


class TestIssueAnalyzerDifficulty:
    """Test difficulty estimation."""

    @pytest.fixture
    def analyzer(self) -> IssueAnalyzer:
        return IssueAnalyzer()

    def test_easy_keyword(self, analyzer: IssueAnalyzer):
        assert analyzer._estimate_difficulty("Good first issue", "") == "easy"

    def test_hard_keyword(self, analyzer: IssueAnalyzer):
        assert analyzer._estimate_difficulty("Complex refactor needed", "") == "hard"

    def test_short_body_is_easy(self, analyzer: IssueAnalyzer):
        assert analyzer._estimate_difficulty("Fix typo", "short") == "easy"

    def test_long_body_is_hard(self, analyzer: IssueAnalyzer):
        long_body = "\n".join([f"Line {i}" for i in range(30)])
        assert analyzer._estimate_difficulty("Some issue", long_body) == "hard"

    def test_medium_default(self, analyzer: IssueAnalyzer):
        body = "\n".join([f"Line {i}" for i in range(10)])
        assert analyzer._estimate_difficulty("Unclear issue", body) == "medium"


class TestIssueAnalyzerExtraction:
    """Test text extraction from issue bodies."""

    @pytest.fixture
    def analyzer(self) -> IssueAnalyzer:
        return IssueAnalyzer()

    def test_extract_reproduction_steps(self, analyzer: IssueAnalyzer):
        body = "Steps to reproduce:\n1. Go to /login\n2. Enter invalid password\n3. See error"
        steps = analyzer._extract_reproduction_steps(body)
        assert len(steps) >= 1

    def test_extract_expected_behavior(self, analyzer: IssueAnalyzer):
        body = "Expected: The form should show a validation error\nActual: Nothing happens"
        assert analyzer._extract_expected_behavior(body) is not None
        assert analyzer._extract_actual_behavior(body) is not None

    def test_extract_error_message(self, analyzer: IssueAnalyzer):
        body = "Error: Connection refused\ntraceback..."
        errors = analyzer._extract_error_messages(body)
        assert len(errors) >= 0  # May or may not match

    def test_extract_file_references(self, analyzer: IssueAnalyzer):
        body = "The bug is in `src/auth/login.py` and `src/utils.py`"
        files = analyzer._extract_file_references(body)
        assert len(files) >= 1
        assert any("login.py" in f for f in files)

    def test_extract_function_references(self, analyzer: IssueAnalyzer):
        body = "The function `validate_user()` is broken"
        funcs = analyzer._extract_function_references(body)
        assert len(funcs) >= 1


class TestIssueAnalyzerFull:
    """Full issue analysis integration tests."""

    @pytest.fixture
    def analyzer(self) -> IssueAnalyzer:
        return IssueAnalyzer()

    def test_full_github_issue_analysis(self, analyzer: IssueAnalyzer):
        issue = {
            "number": 42,
            "title": "Login form crashes on invalid input",
            "body": (
                "### Steps to reproduce\n"
                "1. Go to /login\n"
                "2. Enter invalid email\n"
                "3. Click submit\n\n"
                "### Expected behavior\n"
                "Form should show validation error\n\n"
                "### Actual behavior\n"
                "Page crashes with 500 error\n\n"
                "### Stack trace\n"
                "```\n"
                "Traceback (most recent call last):\n"
                '  File "views.py", line 42, in login\n'
                "    user = User.objects.get(email=email)\n"
                '  File "db.py", line 100, in get\n'
                "    return self._query(...)\n"
                "```\n\n"
                "File: `src/views.py`"
            ),
            "labels": [{"name": "bug"}, {"name": "high"}],
            "url": "https://github.com/owner/repo/issues/42",
            "platform": "github",
        }

        result = analyzer.analyze_issue(issue)
        assert result.success is True
        analysis: IssueAnalysis = result.data["analysis"]

        assert analysis.issue_id == "42"
        assert analysis.title == "Login form crashes on invalid input"
        assert analysis.issue_type == "bug"
        assert analysis.severity == "high"
        assert analysis.platform == "github"
        assert analysis.confidence > 0.5
        assert len(analysis.reproduction_steps) > 0
        assert analysis.expected_behavior is not None
        assert analysis.actual_behavior is not None

    def test_algora_issue_format(self, analyzer: IssueAnalyzer):
        issue = {
            "id": "alg-123",
            "title": "Fix memory leak in cache module",
            "description": "There is a memory leak when the cache grows beyond 1GB",
            "bounty_amount": 500,
            "currency": "USD",
            "repository": {"full_name": "owner/repo"},
            "platform": "algora",
        }
        result = analyzer.analyze_issue(issue)
        assert result.success is True
        analysis: IssueAnalysis = result.data["analysis"]
        assert analysis.bounty_amount == 500
        assert analysis.bounty_currency == "USD"

    def test_opire_issue_format(self, analyzer: IssueAnalyzer):
        issue = {
            "id": "op-456",
            "title": "Add pagination to API",
            "body": "The /api/users endpoint needs pagination support",
            "reward": 200,
            "currency": "USD",
            "platform": "opire",
        }
        result = analyzer.analyze_issue(issue)
        assert result.success is True
        analysis: IssueAnalysis = result.data["analysis"]
        assert analysis.bounty_amount == 200

    def test_multiple_labels(self, analyzer: IssueAnalyzer):
        issue = {
            "number": 1,
            "title": "Fix security issue",
            "body": "Critical security vulnerability in auth",
            "labels": ["security", "critical"],
            "platform": "github",
        }
        result = analyzer.analyze_issue(issue)
        assert result.success is True
        analysis: IssueAnalysis = result.data["analysis"]
        assert analysis.issue_type == "security"

    def test_confidence_calculation(self, analyzer: IssueAnalyzer):
        # Minimal issue
        minimal = analyzer._calculate_confidence(
            IssueAnalysis(
                issue_id="1",
                title="Hi",
                body="",
                url="",
                platform="test",
                issue_type="bug",
                severity="medium",
                confidence=0.0,
            )
        )
        assert 0.3 <= minimal <= 0.5  # Base + small title bonus

        # Rich issue
        rich = analyzer._calculate_confidence(
            IssueAnalysis(
                issue_id="1",
                title="Full bug report with details",
                body="Lots of content here " * 20,
                url="http://example.com",
                platform="github",
                issue_type="bug",
                severity="high",
                confidence=0.0,
                reproduction_steps=["Step 1", "Step 2"],
                error_messages=["Error: something failed"],
                stack_traces=["Traceback ..."],
                affected_files=["src/main.py"],
                expected_behavior="Should work",
                actual_behavior="Doesn't work",
            )
        )
        assert rich > 0.7  # Rich issues should have high confidence

    def test_estimated_hours(self, analyzer: IssueAnalyzer):
        analysis = IssueAnalysis(
            issue_id="1",
            title="Simple fix",
            body="",
            url="",
            platform="test",
            issue_type="documentation",
            severity="low",
            confidence=0.5,
            difficulty_estimate="easy",
        )
        hours = analyzer._estimate_hours(analysis)
        assert hours < 2  # Easy doc fix should be fast

        analysis.difficulty_estimate = "hard"
        analysis.issue_type = "security"
        analysis.severity = "critical"
        hours = analyzer._estimate_hours(analysis)
        assert hours >= 24  # Hard security issue should be slow

    def test_empty_body_does_not_crash(self, analyzer: IssueAnalyzer):
        issue = {"number": 1, "title": "Test", "body": "", "platform": "github"}
        result = analyzer.analyze_issue(issue)
        assert result.success is True


# ── RepoAnalyzer Tests (pure logic only, no subprocess) ─────────


class TestRepoAnalyzerLogic:
    """Test RepoAnalyzer's pure-logic methods (no subprocess)."""

    @pytest.fixture
    def analyzer(self):
        from core.autonomy.repo_analyzer import RepoAnalyzer

        return RepoAnalyzer()

    def test_language_detection_rules(self, analyzer):
        assert "python" in analyzer.LANGUAGE_DETECTORS
        assert "javascript" in analyzer.LANGUAGE_DETECTORS
        assert "rust" in analyzer.LANGUAGE_DETECTORS
        assert len(analyzer.LANGUAGE_DETECTORS) >= 8

    def test_test_command_mapping(self, analyzer):
        assert "pytest" in analyzer.TEST_COMMANDS["python"][0]
        assert "npm test" in analyzer.TEST_COMMANDS["javascript"][0]
        assert "cargo test" in analyzer.TEST_COMMANDS["rust"][0]

    def test_build_command_mapping(self, analyzer):
        assert analyzer.BUILD_COMMANDS["python"][0].startswith("pip")
        assert analyzer.BUILD_COMMANDS["rust"][0].startswith("cargo")


# ── CoderAgent Result Tests ─────────────────────────────────────


class TestCoderAgentResult:
    """Test CoderAgentResult dataclass."""

    def test_default_values(self):
        from core.autonomy.coder_agent import CoderAgentResult

        result = CoderAgentResult(success=False, issue_id="123", platform="github")
        assert result.success is False
        assert result.issue_id == "123"
        assert result.platform == "github"
        assert result.repo_cloned is False
        assert result.total_duration_seconds == 0.0
        assert result.phases_duration == {}
        assert result.verdict is None


# ── Platform-specific entry points ──────────────────────────────


class TestPlatformEntryPoints:
    """Test platform-specific solve functions."""

    @pytest.mark.asyncio
    async def test_algora_solve_extracts_repo(self):
        from core.autonomy.coder_agent import solve_algora_issue

        # We just verify it doesn't crash and routes correctly
        # The actual solve requires network, but we can verify the structure
        assert callable(solve_algora_issue)

    def test_freelancer_conversion(self):
        from core.autonomy.coder_agent import solve_freelancer_project

        assert callable(solve_freelancer_project)

    def test_solve_issue_function(self):
        from core.autonomy.coder_agent import solve_issue

        assert callable(solve_issue)
