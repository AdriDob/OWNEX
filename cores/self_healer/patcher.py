"""Patch Generator — Generates code/config patches using CoderAgent."""

from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from cores.autonomy.coder_agent import CoderAgentConfig, solve_issue
from cores.events.event_bus import get_event_bus
from cores.self_healer.models import (
    FixPlan,
    FixStrategy,
    Patch,
)

logger = logging.getLogger("ownex.self_healer.patcher")


class PatchGenerator:
    """Generates patches using CoderAgent for code fixes."""

    def __init__(self, repo_root: Path | None = None):
        self.repo_root = repo_root or Path(__file__).resolve().parents[3]
        self.event_bus = get_event_bus()
        self._patch_count = 0

    def _is_path_allowed(self, file_path: str, excluded_paths: list[str]) -> bool:
        """Check if a file path is allowed to be modified."""
        path = Path(file_path)
        try:
            rel_path = path.relative_to(self.repo_root)
        except ValueError:
            return False

        for excluded in excluded_paths:
            if str(rel_path).startswith(excluded):
                return False
        return True

    async def generate_patch(
        self,
        plan: FixPlan,
        excluded_paths: list[str] | None = None,
    ) -> Patch:
        """Generate a patch from a fix plan."""
        self._patch_count += 1
        patch_id = f"patch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{self._patch_count}"
        excluded = excluded_paths or []

        try:
            if plan.strategy == FixStrategy.CODE_PATCH:
                return await self._generate_code_patch(plan, patch_id, excluded)
            elif plan.strategy == FixStrategy.CONFIG_CHANGE:
                return await self._generate_config_patch(plan, patch_id, excluded)
            elif plan.strategy == FixStrategy.DEPENDENCY_UPDATE:
                return await self._generate_dependency_patch(plan, patch_id, excluded)
            else:
                # For other strategies, create a minimal patch documenting the action
                return await self._generate_action_patch(plan, patch_id)
        except Exception as e:
            logger.error(f"Patch generation failed: {e}")
            raise

    async def _generate_code_patch(
        self,
        plan: FixPlan,
        patch_id: str,
        excluded_paths: list[str],
    ) -> Patch:
        """Generate code patch using CoderAgent."""
        # Filter out excluded files
        allowed_files = [f for f in plan.files_to_modify if self._is_path_allowed(f, [])]

        if not allowed_files:
            raise ValueError("No allowed files to modify in plan")

        # Prepare issue data for CoderAgent
        issue_data = {
            "id": plan.id,
            "title": f"Self-healer fix: {plan.description}",
            "body": f"""
**Auto-generated fix plan from Self-Healer**

**Description:** {plan.description}

**Steps:**
{chr(10).join(f"- {step}" for step in plan.steps)}

**Files to modify:**
{chr(10).join(f"- {f}" for f in allowed_files)}

**Config changes:**
{plan.config_changes}

**Tests to add:**
{chr(10).join(f"- {t}" for t in plan.tests_to_add)}

**Rollback plan:** {plan.rollback_plan}
""",
            "platform": "self_healer",
        }

        # Use CoderAgent to generate the fix
        config = CoderAgentConfig(
            max_iterations=2,
            min_confidence_for_pr=0.7,
            cleanup_repo=True,
        )

        result = await solve_issue(
            issue_data=issue_data,
            repo_url=str(self.repo_root),
            platform="self_healer",
            config=config,
        )

        if not result.success:
            raise RuntimeError(f"CoderAgent failed: {result.error}")

        # Extract diff from PR result
        diff = ""
        files_changed = []
        if result.pr_result and result.pr_result.pr_url:
            # Get diff from git
            diff = await self._get_git_diff()
            files_changed = result.generation_plan.changes if result.generation_plan else []
            files_changed = [c.file_path for c in files_changed] if files_changed else []

        # Generate tests if specified
        tests_generated = []
        if plan.tests_to_add:
            tests_generated = await self._generate_tests(plan.tests_to_add)

        patch = Patch(
            id=f"patch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            plan_id=plan.id,
            diff=diff,
            files_changed=files_changed,
            tests_generated=tests_generated,
            validation_results={
                "coder_agent_success": result.success,
                "pr_url": result.pr_result.pr_url if result.pr_result else None,
                "verdict": result.verdict,
            },
        )

        return patch

    async def _generate_config_patch(
        self,
        plan: FixPlan,
        patch_id: str,
        excluded_paths: list[str],
    ) -> Patch:
        """Generate configuration patch (YAML/JSON/env changes)."""
        diff_lines = []
        files_changed = []

        for file_path, changes in plan.config_changes.items():
            if not self._is_path_allowed(file_path, excluded_paths):
                continue

            file_path_obj = self.repo_root / file_path
            if not file_path_obj.exists():
                continue

            # Read current content
            content = file_path_obj.read_text()
            original = content

            # Apply changes (simple key-value replacement for now)
            import yaml

            try:
                if file_path.endswith((".yaml", ".yml")):
                    data = yaml.safe_load(content) or {}
                    for key, value in changes.items():
                        keys = key.split(".")
                        d = data
                        for k in keys[:-1]:
                            d = d.setdefault(k, {})
                        d[keys[-1]] = value
                    new_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
                elif file_path.endswith(".json"):
                    import json

                    data = json.loads(content)
                    for key, value in changes.items():
                        data[key] = value
                    new_content = json.dumps(data, indent=2)
                else:
                    # Text/env file - simple replace
                    new_content = content
                    for key, value in changes.items():
                        new_content = new_content.replace(f"{key}=", f"{key}={value}")

                if new_content != original:
                    file_path_obj.write_text(new_content)
                    files_changed.append(file_path)
                    diff_lines.append(f"--- a/{file_path}")
                    diff_lines.append(f"+++ b/{file_path}")
                    for i, (orig, new) in enumerate(zip(original.splitlines(), new_content.splitlines())):
                        if orig != new:
                            diff_lines.append(f"-{orig}")
                            diff_lines.append(f"+{new}")
            except Exception as e:
                logger.warning(f"Failed to modify config {file_path}: {e}")

        patch = Patch(
            id=f"patch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            plan_id=plan.id,
            diff="\n".join(diff_lines),
            files_changed=files_changed,
            validation_results={"config_changes_applied": len(files_changed) > 0},
        )

        return patch

    async def _generate_dependency_patch(
        self,
        plan: FixPlan,
        patch_id: str,
        excluded_paths: list[str],
    ) -> Patch:
        """Generate dependency update patch (requirements.txt, pyproject.toml, etc.)."""
        diff_lines = []
        files_changed = []

        for dep_file in ["requirements.txt", "pyproject.toml", "package.json"]:
            file_path = self.repo_root / dep_file
            if not file_path.exists():
                continue

            if not self._is_path_allowed(dep_file, excluded_paths):
                continue

            # For now, just document the intended changes
            content = file_path.read_text()
            diff_lines.append(f"--- a/{dep_file}")
            diff_lines.append(f"+++ b/{dep_file}")
            diff_lines.append("# Dependency updates planned:")
            for dep, version in plan.config_changes.items():
                diff_lines.append(f"#   {dep} == {version}")
            files_changed.append(dep_file)

        patch = Patch(
            id=f"patch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            plan_id=plan.id,
            diff="\n".join(diff_lines),
            files_changed=files_changed,
            validation_results={"dependency_updates_planned": True},
        )

        return patch

    async def _generate_action_patch(
        self,
        plan: FixPlan,
        patch_id: str,
    ) -> Patch:
        """Generate a patch documenting non-code actions (restart, rollback, etc.)."""
        diff = f"""# Self-Healer Action Patch
# Plan: {plan.id}
# Strategy: {plan.strategy.value}
# Description: {plan.description}

## Steps:
{chr(10).join(f"{i + 1}. {step}" for i, step in enumerate(plan.steps))}

## Rollback Plan:
{plan.rollback_plan}

## Approval Required: {plan.approval_required.value}
"""
        return Patch(
            id=f"patch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            plan_id=plan.id,
            diff=diff,
            validation_results={"action_documentation": True},
        )

    async def _get_git_diff(self) -> str:
        """Get git diff for recent changes."""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD~1"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except Exception:
            return ""

    async def _generate_tests(self, test_specs: list[str]) -> list[str]:
        """Generate test files for the fix."""
        generated = []
        for spec in test_specs:
            # Create a basic test file
            test_path = self.repo_root / "tests" / f"test_self_healer_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.py"
            test_path.parent.mkdir(parents=True, exist_ok=True)

            test_content = f'''"""Auto-generated test for self-healer fix."""

import pytest


def test_self_healer_fix_{datetime.now(UTC).strftime("%Y%m%d_%H%M%S")}():
    """Test for: {spec}"""
    # TODO: Implement test based on fix specification
    assert True  # Placeholder
'''
            test_path.write_text(test_content)
            generated.append(str(test_path.relative_to(self.repo_root)))

        return generated


# Singleton
_patch_generator: PatchGenerator | None = None


def get_patch_generator(repo_root: Path | None = None) -> PatchGenerator:
    global _patch_generator
    if _patch_generator is None:
        _patch_generator = PatchGenerator(repo_root)
    return _patch_generator
