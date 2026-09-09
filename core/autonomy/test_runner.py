"""Test Runner — Execute tests for various languages and parse results."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.autonomy.repo_analyzer import RepoInfo


@dataclass
class TestResult:
    """Result of a single test run."""

    command: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = -1
    duration_seconds: float = 0.0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0


@dataclass
class TestRunSummary:
    """Summary of test run across all commands tried."""

    overall_success: bool = False
    results: list[TestResult] = field(default_factory=list)
    best_result: TestResult | None = None
    total_duration: float = 0.0
    language: str = "unknown"
    test_commands_tried: list[str] = field(default_factory=list)


class TestRunner:
    """Runs tests for various languages and parses results."""

    # Test command patterns per language
    TEST_COMMANDS = {
        "python": [
            "pytest -v --tb=short",
            "python -m pytest -v --tb=short",
            "python -m unittest discover -v",
        ],
        "javascript": [
            "npm test -- --reporter=verbose",
            "pnpm test -- --reporter=verbose",
            "yarn test --verbose",
            "bun test",
        ],
        "typescript": [
            "npm test -- --reporter=verbose",
            "pnpm test -- --reporter=verbose",
            "yarn test --verbose",
            "bun test",
        ],
        "go": [
            "go test ./... -v",
            "go test -v ./...",
        ],
        "rust": [
            "cargo test -- --nocapture",
            "cargo test",
        ],
        "java": [
            "mvn test",
            "./gradlew test",
        ],
        "csharp": [
            "dotnet test --no-build --verbosity normal",
            "dotnet test --verbosity normal",
        ],
        "php": [
            "php vendor/bin/phpunit --testdox",
            "phpunit --testdox",
        ],
        "ruby": [
            "bundle exec rspec --format documentation",
            "rspec --format documentation",
        ],
    }

    # Patterns to parse test output
    TEST_PATTERNS = {
        "python": {
            "passed": re.compile(r"(\d+) passed"),
            "failed": re.compile(r"(\d+) failed"),
            "skipped": re.compile(r"(\d+) skipped"),
            "errors": re.compile(r"(\d+) error"),
            "total": re.compile(r"=+ (\d+) (?:passed|failed|error)"),
        },
        "javascript": {
            "passed": re.compile(r"(\d+) passing"),
            "failed": re.compile(r"(\d+) failing"),
            "skipped": re.compile(r"(\d+) pending"),
            "total": re.compile(r"(\d+) (?:passing|failing|pending)"),
        },
        "go": {
            "passed": re.compile(r"--- PASS:.*?\n", re.MULTILINE),
            "failed": re.compile(r"--- FAIL:.*?\n", re.MULTILINE),
        },
        "rust": {
            "passed": re.compile(r"test result:.*?(\d+) passed"),
            "failed": re.compile(r"test result:.*?(\d+) failed"),
        },
        "java": {
            "passed": re.compile(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)"),
        },
        "csharp": {
            "passed": re.compile(r"Passed:\s+(\d+)"),
            "failed": re.compile(r"Failed:\s+(\d+)"),
            "skipped": re.compile(r"Skipped:\s+(\d+)"),
        },
        "php": {
            "passed": re.compile(r"(\d+) tests?, (\d+) assertions?"),
            "failed": re.compile(r"(\d+) failures?"),
        },
        "ruby": {
            "passed": re.compile(r"(\d+) examples?, (\d+) failures?"),
        },
    }

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 300)  # 5 minutes default
        self.max_output_size = self.config.get("max_output_size", 100000)

    async def run_tests(
        self,
        repo_path: Path,
        repo_info: RepoInfo | None = None,
        test_command: str | None = None,
        env: dict[str, str] | None = None,
    ) -> TestRunSummary:
        """Run tests in repository, auto-detecting language and commands."""
        start_time = time.time()

        # Detect language if not provided
        if repo_info is None:
            from core.autonomy.repo_analyzer import RepoAnalyzer

            analyzer = RepoAnalyzer()
            repo_info = await analyzer.analyze_repo(repo_path)

        language = repo_info.language.lower() if repo_info.language else "unknown"

        # Determine test commands to try
        commands = []
        if test_command:
            commands = [test_command]
        elif repo_info.test_command:
            commands = [repo_info.test_command]
        else:
            commands = self.TEST_COMMANDS.get(language, [])

        # Add language-specific defaults if none found
        if not commands:
            commands = self._get_fallback_commands(language)

        summary = TestRunSummary(
            language=language,
            test_commands_tried=commands,
        )

        # Try each command until one works
        for cmd in commands:
            result = await self._run_single_test(repo_path, cmd, env)
            summary.results.append(result)

            if result.success:
                summary.overall_success = True
                summary.best_result = result
                break  # Stop on first success
            elif summary.best_result is None or result.returncode < summary.best_result.returncode:
                summary.best_result = result

        summary.total_duration = time.time() - start_time
        return summary

    def _get_fallback_commands(self, language: str) -> list[str]:
        """Get fallback test commands for a language."""
        return self.TEST_COMMANDS.get(language, ["make test", "./test.sh", "test"])

    async def _run_single_test(
        self,
        repo_path: Path,
        command: str,
        env: dict[str, str] | None = None,
    ) -> TestResult:
        """Run a single test command."""
        start = time.time()
        test_env = {**os.environ, **(env or {})}

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=test_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout,
                )
            except TimeoutError:
                proc.kill()
                await proc.communicate()
                return TestResult(
                    command=command,
                    success=False,
                    stdout="",
                    stderr=f"Test timed out after {self.timeout}s",
                    returncode=-1,
                    duration_seconds=self.timeout,
                )

            duration = time.time() - start
            stdout_str = stdout.decode("utf-8", errors="replace")[-self.max_output_size :]
            stderr_str = stderr.decode("utf-8", errors="replace")[-self.max_output_size :]

            # Parse test counts
            passed, failed, skipped, errors = self._parse_test_output(
                stdout_str + stderr_str,
                repo_path,
            )

            success = proc.returncode == 0 and failed == 0 and errors == 0

            return TestResult(
                command=command,
                success=success,
                stdout=stdout_str,
                stderr=stderr_str,
                returncode=proc.returncode,
                duration_seconds=duration,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
            )

        except Exception as e:
            return TestResult(
                command=command,
                success=False,
                stdout="",
                stderr=str(e),
                returncode=-1,
                duration_seconds=time.time() - start,
            )

    def _parse_test_output(self, output: str, repo_path: Path) -> tuple[int, int, int, int]:
        """Parse test output to extract counts."""
        # Try to detect language from files
        language = self._detect_language_from_files(repo_path)

        patterns = self.TEST_PATTERNS.get(language, {})

        passed = failed = skipped = errors = 0

        if language == "python":
            for pattern_name, pattern in patterns.items():
                match = pattern.search(output)
                if match:
                    if pattern_name == "total":
                        # Could calculate from passed+failed+skipped+errors
                        pass
                    else:
                        val = int(match.group(1))
                        if pattern_name == "passed":
                            passed = val
                        elif pattern_name == "failed":
                            failed = val
                        elif pattern_name == "skipped":
                            skipped = val
                        elif pattern_name == "errors":
                            errors = val

        elif language == "java":
            match = patterns.get("passed", re.compile("")).search(output)
            if match:
                passed = int(match.group(1))
                failed = int(match.group(2))
                errors = int(match.group(3))
                skipped = int(match.group(4))

        else:
            # Generic parsing
            for pattern_name, pattern in patterns.items():
                match = pattern.search(output)
                if match:
                    try:
                        val = int(match.group(1))
                        if pattern_name == "passed":
                            passed = val
                        elif pattern_name == "failed":
                            failed = val
                        elif pattern_name == "skipped":
                            skipped = val
                        elif pattern_name == "errors":
                            errors = val
                    except (ValueError, IndexError):
                        pass

        return passed, failed, skipped, errors

    def _detect_language_from_files(self, repo_path: Path) -> str:
        """Detect language from file extensions in repo."""
        extensions = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".cs": "csharp",
            ".php": "php",
            ".rb": "ruby",
        }

        counts = {}
        for ext, lang in extensions.items():
            matches = list(repo_path.rglob(f"*{ext}"))
            if matches:
                counts[lang] = len(matches)

        if counts:
            return max(counts.items(), key=lambda x: x[1])[0]
        return "unknown"

    async def run_specific_test(
        self,
        repo_path: Path,
        test_file: Path,
        repo_info: RepoInfo | None = None,
    ) -> TestResult:
        """Run a specific test file."""
        if repo_info is None:
            from core.autonomy.repo_analyzer import RepoAnalyzer

            analyzer = RepoAnalyzer()
            repo_info = await analyzer.analyze_repo(repo_path)

        # Build command for specific test file
        language = repo_info.language.lower() if repo_info.language else "unknown"

        commands = {
            "python": f"pytest {test_file} -v --tb=short",
            "javascript": f"npm test -- {test_file} --reporter=verbose",
            "typescript": f"npm test -- {test_file} --reporter=verbose",
            "go": f"go test -v {test_file}",
            "rust": f"cargo test --test {test_file.stem} -- --nocapture",
            "java": f"mvn test -Dtest={test_file.stem}",
            "csharp": f"dotnet test --filter FullyQualifiedName~{test_file.stem}",
        }

        cmd = commands.get(language, f"echo 'No specific test command for {language}'")
        return await self._run_single_test(repo_path, cmd)

    def get_test_summary(self, summary: TestRunSummary) -> str:
        """Get human-readable summary of test run."""
        if summary.overall_success:
            result = summary.best_result
            return f"✅ Tests passed ({result.passed} passed, {result.failed} failed, {result.skipped} skipped in {result.duration_seconds:.1f}s)"
        else:
            result = summary.best_result
            return f"❌ Tests failed ({result.passed} passed, {result.failed} failed, {result.errors} errors in {result.duration_seconds:.1f}s)"


import os  # noqa: E402
