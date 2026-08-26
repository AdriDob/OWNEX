"""Code Generator — Write fixes/patches based on issue analysis and repo context."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.autonomy.issue_analyzer import IssueAnalysis
from core.autonomy.repo_analyzer import BrowserResult, RepoInfo

logger = logging.getLogger("ownex.autonomy.code_generator")


@dataclass
class CodeChange:
    """A single code change (file modification)."""

    file_path: Path
    original_content: str
    new_content: str
    change_type: str  # fix, feature, refactor, test, doc
    description: str
    confidence: float = 0.8


@dataclass
class GenerationPlan:
    """Plan for code generation."""

    issue_analysis: IssueAnalysis
    repo_info: RepoInfo
    changes: list[CodeChange] = field(default_factory=list)
    test_changes: list[CodeChange] = field(default_factory=list)
    summary: str = ""
    estimated_confidence: float = 0.5


class CodeGenerator:
    """Generates code fixes based on issue analysis and repository context."""

    # Marcadores del contrato de salida LLM (Zero Magic: constantes explícitas).
    _LLM_FILE_START = "<<<FILE_START>>>"
    _LLM_FILE_END = "<<<FILE_END>>>"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.use_llm = self.config.get("use_llm", True)
        self.max_file_size = self.config.get("max_file_size", 50000)  # chars
        self._llm_timeout = self.config.get("llm_timeout_s", 90)

    async def _llm_complete(self, system_prompt: str, user_prompt: str) -> str | None:
        """Single completion via the copilot provider router. Returns None on failure.

        Degrade defensivo: sin router/providers disponibles o ante cualquier
        error, devuelve None y el caller cae a los heurísticos existentes.
        """
        try:
            from core.copilot.providers.router import get_provider_router

            result = await get_provider_router().route(
                task_type="code",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            logger.warning("[CodeGenerator] LLM unavailable: %s", exc)
            return None
        if getattr(result, "error", None) or not getattr(result, "content", ""):
            return None
        return str(result.content)

    def _parse_llm_file_content(self, raw: str) -> str | None:
        """Extract file content between the contract markers."""
        start = raw.find(self._LLM_FILE_START)
        end = raw.find(self._LLM_FILE_END)
        if start == -1 or end == -1 or end <= start:
            return None
        content = raw[start + len(self._LLM_FILE_START) : end].strip("\n")
        if not content.strip():
            return None
        return content + "\n"

    async def _generate_llm_fix(
        self,
        plan: GenerationPlan,
    ) -> list[CodeChange]:
        """Generate a fix for the top target file via LLM. [] si no hay targets/LLM."""
        issue = plan.issue_analysis
        repo = plan.repo_info

        # Un solo archivo por pasada (mínima intervención; multi-file es fase futura)
        target = self._pick_primary_target(issue, repo)
        if target is None or not target.exists():
            return []
        original = target.read_text(errors="ignore")
        if len(original) > self.max_file_size:
            return []

        system_prompt = (
            "You are a senior software engineer fixing a GitHub issue.\n"
            f"Return ONLY the complete corrected content of ONE file between "
            f"{self._LLM_FILE_START} and {self._LLM_FILE_END} markers.\n"
            "No explanations outside the markers. Preserve style and imports."
        )
        repro = "\n".join(f"- {s}" for s in (issue.reproduction_steps or [])[:5])
        user_prompt = (
            f"Issue #{issue.issue_id}: {issue.title}\n\n{issue.body[:4000]}\n\n"
            f"Error messages:\n{'- ' + chr(10).join(map(str, issue.error_messages[:3])) if issue.error_messages else 'N/A'}\n\n"
            f"Reproduction steps:\n{repro or 'N/A'}\n\n"
            f"File to fix ({target.relative_to(repo.path)}):\n```{original}```"
        )

        raw = await self._llm_complete(system_prompt, user_prompt)
        if raw is None:
            return []
        new_content = self._parse_llm_file_content(raw)
        if new_content is None or new_content == original:
            return []

        return [
            CodeChange(
                file_path=target,
                original_content=original,
                new_content=new_content,
                change_type="fix",
                description=f"LLM fix for: {issue.title[:100]}",
                confidence=0.75,
            )
        ]

    def _pick_primary_target(self, issue: IssueAnalysis, repo: RepoInfo) -> Path | None:
        """Best single file to modify: mentioned files first, then entry points."""
        for f in issue.affected_files:
            path = Path(f)
            candidate = path if path.is_absolute() else repo.path / path
            if candidate.exists():
                return candidate
        for entry in repo.entry_points[:3]:
            candidate = repo.path / entry
            if candidate.exists():
                return candidate
        return repo.test_files[0] if repo.test_files else None

    async def generate_fix(
        self,
        issue_analysis: IssueAnalysis,
        repo_info: RepoInfo,
        relevant_files: dict[str, str] | None = None,
    ) -> BrowserResult:
        """Generate a fix for the analyzed issue."""
        try:
            plan = await self._create_generation_plan(issue_analysis, repo_info, relevant_files)
            changes = await self._generate_changes(plan)
            plan.changes = changes

            # Calculate overall confidence
            if changes:
                plan.estimated_confidence = sum(c.confidence for c in changes) / len(changes)
            else:
                plan.estimated_confidence = 0.1

            plan.summary = self._generate_summary(plan)

            return BrowserResult(
                True,
                "generate_fix",
                issue_analysis.issue_id,
                f"Generated {len(changes)} changes",
                data={"plan": plan, "changes": [c.__dict__ for c in changes]},
            )

        except Exception as e:
            return BrowserResult(False, "generate_fix", issue_analysis.issue_id, error=f"Generation failed: {e}")

    async def _create_generation_plan(
        self,
        issue: IssueAnalysis,
        repo: RepoInfo,
        relevant_files: dict[str, str] | None,
    ) -> GenerationPlan:
        """Create a plan for generating the fix."""
        plan = GenerationPlan(
            issue_analysis=issue,
            repo_info=repo,
        )
        # Determine target files
        self._identify_target_files(issue, repo, relevant_files)
        plan.changes = []  # Will be filled by _generate_changes

        return plan

    def _identify_target_files(
        self,
        issue: IssueAnalysis,
        repo: RepoInfo,
        relevant_files: dict[str, str] | None,
    ) -> list[Path]:
        """Identify which files need to be changed."""
        targets = set()

        # 1. Files explicitly mentioned in issue
        for f in issue.affected_files:
            path = Path(f)
            if path.exists() or (repo.path / path).exists():
                targets.add(repo.path / path if not path.is_absolute() else path)

        # 2. Files from relevant_files dict (passed from repo analysis)
        if relevant_files:
            for f in relevant_files:
                targets.add(repo.path / f)

        # 3. Test files related to affected functions
        for func in issue.affected_functions:
            for test_file in repo.test_files:
                if func.lower() in test_file.name.lower():
                    targets.add(test_file)

        # 4. Entry points for the language
        targets.update(repo.entry_points[:5])

        return list(targets)[:10]  # Max 10 files

    async def _generate_changes(self, plan: GenerationPlan) -> list[CodeChange]:
        """Generate code changes: LLM-first (real fix), heuristic fallback."""
        issue = plan.issue_analysis
        repo = plan.repo_info

        if self.use_llm:
            llm_changes = await self._generate_llm_fix(plan)
            if llm_changes:
                if issue.issue_type in ["bug", "feature", "security"]:
                    plan.test_changes = await self._generate_tests(issue, repo, llm_changes)
                return llm_changes
            logger.info(
                "[CodeGenerator] LLM produced no changes for %s — falling back to heuristics",
                issue.issue_id,
            )

        changes = []

        if issue.issue_type == "bug":
            changes.extend(await self._generate_bug_fix(issue, repo))
        elif issue.issue_type == "feature":
            changes.extend(await self._generate_feature(issue, repo))
        elif issue.issue_type == "security":
            changes.extend(await self._generate_security_fix(issue, repo))
        elif issue.issue_type == "documentation":
            changes.extend(await self._generate_docs(issue, repo))
        elif issue.issue_type == "refactor":
            changes.extend(await self._generate_refactor(issue, repo))

        # Always generate/update tests for bugs and features
        if issue.issue_type in ["bug", "feature", "security"]:
            test_changes = await self._generate_tests(issue, repo, changes)
            plan.test_changes = test_changes

        return changes

    async def _generate_bug_fix(self, issue: IssueAnalysis, repo: RepoInfo) -> list[CodeChange]:
        """Generate a bug fix."""
        changes = []

        # Strategy: Look at error messages, stack traces, affected files
        # and generate targeted fix

        if issue.error_messages:
            # Try to locate error in code
            for error in issue.error_messages[:3]:
                fix = self._create_error_based_fix(error, issue, repo)
                if fix:
                    changes.append(fix)

        if issue.affected_files:
            for file_path in issue.affected_files[:3]:
                fix = self._create_file_based_fix(file_path, issue, repo)
                if fix:
                    changes.append(fix)

        # If no specific targets, try entry points
        if not changes and repo.entry_points:
            for entry_str in repo.entry_points[:2]:
                entry_path = repo.path / entry_str
                fix = self._create_generic_fix(entry_path, issue, repo)
                if fix:
                    changes.append(fix)
                    break

        return changes

    def _create_error_based_fix(self, error: str, issue: IssueAnalysis, repo: RepoInfo) -> CodeChange | None:
        """Create fix based on error message."""
        # This is a template - in reality would use LLM
        # For now, create a placeholder that shows intent

        # Extract potential function/file from error
        func_match = re.search(r"(\w+)\(\)", error)
        file_match = re.search(r"([a-zA-Z0-9_\-./]+\.\w+)", error)

        target_file = None
        if file_match:
            target_file = repo.path / file_match.group(1)
        elif func_match:
            # Search for function in repo
            for test_file in repo.test_files:
                if func_match.group(1) in test_file.read_text(errors="ignore"):
                    target_file = test_file
                    break

        if not target_file or not target_file.exists():
            return None

        original = target_file.read_text(errors="ignore")
        if len(original) > self.max_file_size:
            return None

        # Simple heuristic fix - add try/except or null check
        new_content = self._apply_defensive_fix(original, error, func_match.group(1) if func_match else "")

        if new_content != original:
            return CodeChange(
                file_path=target_file,
                original_content=original,
                new_content=new_content,
                change_type="fix",
                description=f"Defensive fix for error: {error[:100]}",
                confidence=0.6,
            )

        return None

    def _create_file_based_fix(self, file_path: str, issue: IssueAnalysis, repo: RepoInfo) -> CodeChange | None:
        """Create fix for a specific file."""
        target = repo.path / file_path
        if not target.exists():
            # Try to find it
            for tf in repo.test_files:
                if file_path in str(tf):
                    target = tf
                    break

        if not target.exists():
            return None

        original = target.read_text(errors="ignore")
        if len(original) > self.max_file_size:
            return None

        # Apply fix based on issue type and content
        new_content = self._apply_contextual_fix(original, issue)

        if new_content != original:
            return CodeChange(
                file_path=target,
                original_content=original,
                new_content=new_content,
                change_type="fix",
                description=f"Fix for {issue.issue_type}: {issue.title[:80]}",
                confidence=0.7,
            )

        return None

    def _create_generic_fix(self, entry_point: Path, issue: IssueAnalysis, repo: RepoInfo) -> CodeChange | None:
        """Create a generic fix in entry point."""
        original = entry_point.read_text(errors="ignore")
        if len(original) > self.max_file_size:
            return None

        new_content = self._apply_contextual_fix(original, issue)

        if new_content != original:
            return CodeChange(
                file_path=entry_point,
                original_content=original,
                new_content=new_content,
                change_type="fix",
                description=f"Generic fix attempt for {issue.title[:80]}",
                confidence=0.4,
            )

        return None

    def _apply_defensive_fix(self, content: str, error: str, function: str) -> str:
        """Apply defensive programming fix (try/except, null checks)."""
        # This is a simplified template - real implementation would use LLM
        lines = content.split("\n")

        # Look for the function mentioned in error
        if function:
            for i, line in enumerate(lines):
                if f"def {function}" in line or f"function {function}" in line or f"fn {function}" in line:
                    # Found function, add try/except wrapper
                    indent = len(line) - len(line.lstrip())
                    new_lines = lines[: i + 1]
                    new_lines.append(" " * (indent + 4) + "try:")
                    j = len(lines)
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() and not lines[j].startswith(" " * (indent + 4)):
                            break
                        new_lines.append(" " * 4 + lines[j])
                    new_lines.append(" " * (indent + 4) + "except Exception as e:")
                    new_lines.append(" " * (indent + 8) + f"# Auto-added fix for: {error[:80]}")
                    new_lines.append(" " * (indent + 8) + "raise")
                    new_lines.extend(lines[j:])
                    return "\n".join(new_lines)

        return content

    def _apply_contextual_fix(self, content: str, issue: IssueAnalysis) -> str:
        """Apply contextual fix based on issue analysis."""
        # Template-based fixes for common patterns
        # Real implementation would use LLM with full context

        # Fix 1: Add null checks for "NoneType" errors
        if "NoneType" in issue.body or "null" in issue.body.lower() or "undefined" in issue.body.lower():
            content = self._add_null_checks(content)

        # Fix 2: Add bounds checks for index/key errors
        if any(kw in issue.body.lower() for kw in ["index", "key", "outofrange", "keyerror", "indexerror"]):
            content = self._add_bounds_checks(content)

        # Fix 3: Fix async/await issues
        if any(kw in issue.body.lower() for kw in ["async", "await", "coroutine", "event loop"]):
            content = self._fix_async_issues(content)

        return content

    def _add_null_checks(self, content: str) -> str:
        """Add defensive null checks."""
        # Simple pattern: add checks before attribute access on potentially None vars
        # This is a placeholder - real implementation needs AST analysis
        return content

    def _add_bounds_checks(self, content: str) -> str:
        """Add bounds checks for array/dict access."""
        return content

    def _fix_async_issues(self, content: str) -> str:
        """Fix common async/await issues."""
        return content

    async def _generate_feature(self, issue: IssueAnalysis, repo: RepoInfo) -> list[CodeChange]:
        """Generate new feature implementation."""
        # Features are too varied for template-based generation
        # Would need LLM with full repo context
        return []

    async def _generate_security_fix(self, issue: IssueAnalysis, repo: RepoInfo) -> list[CodeChange]:
        """Generate security fix."""
        changes = []

        # Common security patterns
        if "sql injection" in issue.body.lower() or "sqli" in issue.body.lower():
            changes.extend(self._fix_sql_injection(repo))
        elif "xss" in issue.body.lower() or "cross site" in issue.body.lower():
            changes.extend(self._fix_xss(repo))
        elif "path traversal" in issue.body.lower() or "lfi" in issue.body.lower():
            changes.extend(self._fix_path_traversal(repo))

        return changes

    def _fix_sql_injection(self, repo: RepoInfo) -> list[CodeChange]:
        """Fix SQL injection vulnerabilities."""
        changes = []
        for entry_str in repo.entry_points:
            entry = repo.path / entry_str
            if entry.exists():
                content = entry.read_text(errors="ignore")
                # Look for string formatting in SQL queries
                if re.search(r"execute\(f[\"']", content) or re.search(r"\.format\(.*select", content, re.IGNORECASE):
                    new_content = re.sub(r"execute\(f([\"'])(.*?)\1\)", r"execute(\2, params)", content)
                    if new_content != content:
                        changes.append(
                            CodeChange(
                                file_path=entry,
                                original_content=content,
                                new_content=new_content,
                                change_type="security",
                                description="Fix SQL injection: use parameterized queries",
                                confidence=0.8,
                            )
                        )
        return changes

    def _fix_xss(self, repo: RepoInfo) -> list[CodeChange]:
        """Fix XSS vulnerabilities."""
        return []

    def _fix_path_traversal(self, repo: RepoInfo) -> list[CodeChange]:
        """Fix path traversal vulnerabilities."""
        return []

    async def _generate_docs(self, issue: IssueAnalysis, repo: RepoInfo) -> list[CodeChange]:
        """Generate documentation updates."""
        return []

    async def _generate_refactor(self, issue: IssueAnalysis, repo: RepoInfo) -> list[CodeChange]:
        """Generate refactoring changes."""
        return []

    async def _generate_tests(
        self,
        issue: IssueAnalysis,
        repo: RepoInfo,
        changes: list[CodeChange],
    ) -> list[CodeChange]:
        """Generate test changes for the fix."""
        test_changes = []

        # Find or create test file for each changed file
        for change in changes:
            test_file = self._find_or_create_test_file(change.file_path, repo)
            if test_file and test_file.exists():
                original = test_file.read_text(errors="ignore")
                new_content = self._add_test_case(original, issue, change)
                if new_content != original:
                    test_changes.append(
                        CodeChange(
                            file_path=test_file,
                            original_content=original,
                            new_content=new_content,
                            change_type="test",
                            description=f"Add test for {issue.title[:60]}",
                            confidence=0.7,
                        )
                    )

        return test_changes

    def _find_or_create_test_file(self, source_file: Path, repo: RepoInfo) -> Path | None:
        """Find existing test file or determine where to create one."""
        # Look for existing test file
        for test_file in repo.test_files:
            if source_file.stem in test_file.stem or test_file.stem in source_file.stem:
                return test_file

        # Standard test locations
        test_dirs = ["tests", "test", "spec", "__tests__"]
        for test_dir in test_dirs:
            test_path = repo.path / test_dir
            if test_path.exists():
                # Try to mirror source structure
                rel = source_file.relative_to(repo.path)
                test_file = test_path / rel.parent / f"test_{rel.name}"
                if test_file.exists():
                    return test_file

        return None

    def _add_test_case(self, content: str, issue: IssueAnalysis, change: CodeChange) -> str:
        """Add a test case for the fix."""
        # Simple template - would use LLM in production
        test_name = f"test_fix_{issue.issue_id}_{change.change_type}"
        test_template = f"""

def {test_name}():
    \"\"\"Test for fix: {issue.title[:80]}\"\"\"
    # TODO: Implement test based on reproduction steps
    # Steps: {issue.reproduction_steps[:3] if issue.reproduction_steps else "N/A"}
    assert True  # Placeholder

"""
        # Insert before last line or at end
        if content.endswith("\n"):
            return content + test_template
        return content + "\n" + test_template

    def _generate_summary(self, plan: GenerationPlan) -> str:
        """Generate human-readable summary of changes."""
        parts = [f"Fix for: {plan.issue_analysis.title}"]

        if plan.changes:
            parts.append(f"\nCode changes ({len(plan.changes)}):")
            for c in plan.changes:
                parts.append(f"  - {c.file_path.relative_to(plan.repo_info.path)}: {c.description}")

        if plan.test_changes:
            parts.append(f"\nTest changes ({len(plan.test_changes)}):")
            for c in plan.test_changes:
                parts.append(f"  - {c.file_path.relative_to(plan.repo_info.path)}: {c.description}")

        parts.append(f"\nConfidence: {plan.estimated_confidence:.0%}")

        return "\n".join(parts)
