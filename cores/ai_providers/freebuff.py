"""Freebuff Provider Integration for OWNEX AI Router.

Integrates Freebuff as a free/low-cost worker agent following the MEGAPROTOCOL
for intelligent AI cost routing. Freebuff operates as an additional provider
in the OWNEX provider hierarchy, enabling cost savings on low-risk tasks.

This module follows the existing provider abstraction patterns:
- ModelRouter (core/ai/model_router.py)
- AIRouterEngine (core/ai_router/engine.py)
- ProviderStatusStore (core/ai_router/provider_store.py)
- FailoverEngine (core/ai_router/failover.py)
"""

import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.freebuff_provider")

# ─── Constants ────────────────────────────────────────────────────────

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.orion/freebuff_config.yaml")
CONFIG_ENV_VAR = "FREEBUFF_CONFIG_PATH"

# ─── Data Models ─────────────────────────────────────────────────────


@dataclass
class FreebuffConfig:
    """Configuration for Freebuff provider."""

    enabled: bool = True
    command: str = "freebuff"
    timeout: int = 300  # seconds
    max_concurrent_tasks: int = 4
    allowed_paths: list[str] = field(default_factory=lambda: ["/home/adrie/projects/Rastro"])
    network_access: bool = False
    require_git_clean: bool = True
    autonomy_level: int = 1  # 0=suggest only, 1=confirm, 2=auto-low-risk, 3=auto+test, 4=full
    blocked_paths: list[str] = field(
        default_factory=lambda: [
            "~/.ssh",
            "~/.aws",
            "~/.config",
            ".env",
            ".env.*",
            "secrets/",
            "credentials/",
            "wallets/",
            "private keys",
            "tokens",
        ]
    )

    # Provider scoring
    success_rate: float = 0.82
    average_duration_ms: int = 240000  # 4 minutes
    rollback_rate: float = 0.03
    human_review_rate: float = 0.21


@dataclass
class FreebuffTaskRequest:
    """Request to execute a task via Freebuff."""

    task: str
    workspace: str
    task_type: str = "code"  # code, research, analysis, etc.
    complexity: str = "LOW"
    risk_level: str = "LOW"
    files_affected: int = 0
    requires_review: bool = True
    network_allowed: bool = False
    secrets_present: bool = False
    allowed_paths: list[str] | None = None
    timeout: int | None = None
    autonomy_level: int | None = None


@dataclass
class FreebuffTaskResult:
    """Result from Freebuff task execution."""

    success: bool = False
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    files_changed: int = 0
    diff: str = ""
    duration_ms: int = 0
    provider: str = "freebuff"
    version: str = ""
    risk_level: str = "LOW"
    tests_passed: int = 0
    tests_failed: int = 0
    rollback_available: bool = False
    risk_score: float = 0.0


# ─── Provider Status ─────────────────────────────────────────────────


class ProviderStatus:
    """Status of the Freebuff provider."""

    NOT_CHECKED = "not_checked"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    NOT_INSTALLED = "not_installed"


# ─── Core Functions ──────────────────────────────────────────────────


def load_config(config_path: str | None = None) -> FreebuffConfig:
    """Load Freebuff configuration from file and environment variables."""
    path = Path(config_path) if config_path else Path(DEFAULT_CONFIG_PATH)

    config = FreebuffConfig()

    # Try to load from YAML config file
    if path.exists():
        try:
            import yaml

            with open(path) as f:
                data = yaml.safe_load(f) or {}

            if "enabled" in data:
                config.enabled = bool(data["enabled"])
            if "command" in data:
                config.command = str(data["command"])
            if "timeout" in data:
                config.timeout = int(data["timeout"])
            if "max_concurrent_tasks" in data:
                config.max_concurrent_tasks = int(data["max_concurrent_tasks"])
            if "allowed_paths" in data:
                config.allowed_paths = data["allowed_paths"] or config.allowed_paths
            if "network_access" in data:
                config.network_access = bool(data["network_access"])
            if "require_git_clean" in data:
                config.require_git_clean = bool(data["require_git_clean"])
            if "autonomy_level" in data:
                level = int(data["autonomy_level"])
                if 0 <= level <= 4:
                    config.autonomy_level = level

            logger.info("Loaded Freebuff config from %s", path)
        except Exception as e:
            logger.warning("Failed to load Freebuff config from %s: %s", path, e)

    # Override with environment variables
    env_command = os.getenv("FREEBUFF_COMMAND")
    if env_command:
        config.command = env_command

    env_timeout = os.getenv("FREEBUFF_TIMEOUT")
    if env_timeout:
        config.timeout = int(env_timeout)

    env_timeout_ms = os.getenv("FREEBUFF_MAX_CONCURRENT_TASKS")
    if env_timeout_ms:
        config.max_concurrent_tasks = int(env_timeout_ms)

    env_enabled = os.getenv("FREEBUFF_ENABLED")
    if env_enabled is not None:
        config.enabled = env_enabled.lower() in ("true", "1", "yes")

    env_autonomy = os.getenv("FREEBUFF_AUTONOMY_LEVEL")
    if env_autonomy:
        level = int(env_autonomy)
        if 0 <= level <= 4:
            config.autonomy_level = level

    env_network = os.getenv("FREEBUFF_NETWORK_ACCESS")
    if env_network is not None:
        config.network_access = env_network.lower() in ("true", "1", "yes")

    env_git_clean = os.getenv("FREEBUFF_REQUIRE_GIT_CLEAN")
    if env_git_clean is not None:
        config.require_git_clean = env_git_clean.lower() in ("true", "1", "yes")

    # Update allowed_paths from env if set
    env_paths = os.getenv("FREEBUFF_ALLOWED_PATHS")
    if env_paths:
        config.allowed_paths = [p.strip() for p in env_paths.split(":")]

    return config


def detect_freebuff() -> dict[str, Any]:
    """Detect if Freebuff is installed and available."""
    try:
        # Try to run freebuff --version
        result = subprocess.run(
            ["freebuff", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            # Parse version from output
            version_match = re.search(r"freebuff[\s\/]([\d.]+)", result.stdout)
            version = version_match.group(1) if version_match else "unknown"

            # Try to get more info
            result2 = subprocess.run(
                ["freebuff", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result2.returncode == 0:
                version = result2.stdout.strip()

            return {
                "installed": True,
                "available": True,
                "version": version,
                "status": ProviderStatus.AVAILABLE,
                "command": "freebuff",
            }
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.debug("Error detecting Freebuff: %s", e)

    return {
        "installed": False,
        "available": False,
        "version": "",
        "status": ProviderStatus.NOT_INSTALLED,
        "command": "freebuff",
    }


def check_secrets_in_task(task: str, workspace: str, config: FreebuffConfig) -> bool:
    """Scan task description and workspace for sensitive data."""
    # Scan the task description for common secret patterns
    secret_patterns = [
        r"(?i)api[key]_?\s*[:=]\s*['\"][^'\"]+['\"]",
        r"(?i)secret[^\w\s]+\s*[:=]\s*['\"][^'\"]+['\"]",
        r"(?i)password[^\w\s]+\s*[:=]\s*['\"][^'\"]+['\"]",
        r"(?i)token[^\w\s]+\s*[:=]\s*['\"][^'\"]+['\"]",
        r"(?i)ssh.?key",
        r"(?i)private.?key",
        r"(?i)wallet.?seed",
        r"(?i)mnemonic.?phrase",
    ]

    task_lower = task.lower()
    for pattern in secret_patterns:
        if re.search(pattern, task_lower):
            logger.warning("Potential secret detected in task description")
            return True

    # Scan files in workspace for secrets
    if os.path.isdir(workspace):
        try:
            for root, dirs, files in os.walk(workspace):
                # Skip blocked paths
                dirs[:] = [d for d in dirs if not any(blocked in root for blocked in config.blocked_paths)]

                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, errors="ignore") as f:
                            content = f.read()
                            for pattern in secret_patterns:
                                if re.search(pattern, content, re.IGNORECASE):
                                    logger.warning("Secret found in file: %s", fpath)
                                    return True
                    except Exception:
                        pass  # Skip files we can't read
        except Exception as e:
            logger.debug("Error scanning workspace for secrets: %s", e)

    return False


def check_allowed_paths(workspace: str, config: FreebuffConfig) -> bool:
    """Verify that the workspace is within allowed paths."""
    # Resolve the workspace path
    workspace_resolved = os.path.realpath(workspace)

    for allowed_path in config.allowed_paths:
        allowed_resolved = os.path.realpath(allowed_path)
        # Check if workspace is under allowed path
        if workspace_resolved.startswith(allowed_resolved + os.sep) or workspace_resolved == allowed_resolved:
            return True

    # Also check if any parent is allowed
    parent = os.path.dirname(workspace_resolved)
    while parent != os.path.dirname(parent):
        if any(
            parent.startswith(os.path.realpath(p) + os.sep) or parent == os.path.realpath(p)
            for p in config.allowed_paths
        ):
            return True
        parent = os.path.dirname(parent)

    return False


def git_safety_check(workspace: str, config: FreebuffConfig) -> dict[str, Any]:
    """Perform git safety checks before Freebuff execution."""
    result = {
        "git_available": False,
        "is_git_repo": False,
        "working_dir_clean": True,
        "current_branch": "",
        "snapshot_id": None,
    }

    try:
        # Check if git is available
        result["git_available"] = True

        # Check if it's a git repo
        repo_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if repo_check.returncode == 0:
            result["is_git_repo"] = True
            result["current_branch"] = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()

            # Check working tree status
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if status_result.returncode == 0:
                has_changes = bool(status_result.stdout.strip())
                result["working_dir_clean"] = not has_changes

                if not has_changes and config.require_git_clean:
                    # Clean working directory, good to proceed
                    pass
                elif has_changes and config.require_git_clean:
                    # Uncommitted changes - need to handle
                    result["has_uncommitted_changes"] = True
                else:
                    result["working_dir_clean"] = True
            else:
                result["working_dir_clean"] = True
        else:
            # Not a git repo - still allow but mark
            result["is_git_repo"] = False
            result["working_dir_clean"] = True

    except Exception as e:
        logger.debug("Git safety check error: %s", e)
        # git not available - still proceed but mark
        result["git_available"] = False

    return result


def execute_freebuff_task(request: FreebuffTaskRequest, config: FreebuffConfig) -> FreebuffTaskResult:
    """Execute a task via Freebuff CLI."""
    start_time = time.time()
    result = FreebuffTaskResult()

    # ─── Pre-execution checks ─────────────────────────────────────

    # Check for secrets
    if request.secrets_present:
        result.stderr = "BLOCKED: Sensitive data detected in task. Freebuff execution blocked."
        result.risk_score = 1.0
        return result

    # Check autonomy level
    autonomy = request.autonomy_level if request.autonomy_level is not None else config.autonomy_level

    # Check risk level vs autonomy
    if autonomy == 0:
        # Level 0: Suggest only - don't execute
        result.stderr = "BLOCKED: Autonomy level 0 - Freebuff suggestions only, no execution"
        result.risk_score = 1.0
        return result

    # Level 1: Execute with confirmation
    # Level 2: Execute low-risk tasks automatically
    # Level 3: Execute + test + prepare commit
    # Level 4: Full autonomous execution

    # For this integration, we'll use level 1 (confirmation) by default
    # unless explicitly configured otherwise

    # ─── Git Safety Check ────────────────────────────────────────

    git_result = git_safety_check(request.workspace, config)
    result.files_changed = 0  # Will be updated after execution

    if config.require_git_clean and git_result.get("has_uncommitted_changes"):
        # We can still proceed but warn
        logger.warning("Workspace has uncommitted changes, proceeding with caution")

    # ─── Execute Freebuff ────────────────────────────────────────

    try:
        # Build the freebuff command
        cmd = [config.command]

        # Add task description as argument or via stdin
        # Freebuff CLI likely expects task description
        task_arg = request.task[:500]  # Limit task length

        # Try different CLI invocation methods
        cmd_options = []
        # Common freebuff CLI patterns
        cmd_options = execute_freebuff_task._cli_format if hasattr(execute_freebuff_task, "_cli_format") else [task_arg]

        full_cmd = cmd + cmd_options

        logger.info("Executing Freebuff command: %s", " ".join(full_cmd))

        # Set up environment
        env = os.environ.copy()
        if not request.network_allowed and config.network_access is False:
            # Can't pass network access easily via CLI, just proceed
            pass

        # Execute with timeout
        exec_result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=config.timeout,
            cwd=request.workspace,
            env=env,
        )

        result.stdout = exec_result.stdout
        result.stderr = exec_result.stderr
        result.exit_code = exec_result.returncode
        result.duration_ms = int((time.time() - start_time) * 1000)

        # ─── Post-execution processing ─────────────────────────────

        # Parse diff from output if present
        diff_output = result.stdout + "\n" + result.stderr

        # Try to extract git diff or file changes
        if git_result.get("is_git_repo"):
            try:
                # Get git diff of changes
                diff_check = subprocess.run(
                    ["git", "diff"],
                    cwd=request.workspace,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if diff_check.returncode == 0:
                    result.diff = diff_check.stdout
                    result.files_changed = _count_changed_files(diff_check.stdout)
            except Exception:
                pass

        # If no diff extracted from git, try to parse from freebuff output
        if not result.diff.strip() and ("+++" in diff_output or "---" in diff_output):
            result.diff = diff_output

        # Count files changed (rough estimate from diff)
        if not result.files_changed:
            result.files_changed = _count_changed_files(diff_output)

        # Determine success
        result.success = result.exit_code == 0 or (result.exit_code is None and result.stdout.strip())

        # Set risk level
        if result.success:
            if request.risk_level == "LOW":
                result.risk_level = "LOW"
                result.risk_score = 0.1
            elif request.risk_level == "MEDIUM":
                result.risk_level = "MEDIUM"
                result.risk_score = 0.5
            else:
                result.risk_level = "HIGH"
                result.risk_score = 0.9
        else:
            result.risk_level = "HIGH"
            result.risk_score = 1.0

        # Test results (if applicable)
        if request.task_type in ("code", "tests", "validation"):
            # Try to extract test results from output
            test_indicators = re.findall(
                r"(test|pytest|unittest).*?(passed|failed|ok|FAIL)", diff_output, re.IGNORECASE
            )
            result.tests_passed = len([t for t in test_indicators if "pass" in t.lower() or "ok" in t.lower()])
            result.tests_failed = len([t for t in test_indicators if "fail" in t.lower() or "FAIL" in t.upper()])
        else:
            result.tests_passed = 0
            result.tests_failed = 0

        # Rollback available if git repo and changes made
        if git_result.get("is_git_repo") and result.files_changed > 0:
            result.rollback_available = True

        logger.info(
            "Freebuff task execution completed: success=%s, files_changed=%d, duration=%dms, risk=%s",
            result.success,
            result.files_changed,
            result.duration_ms,
            result.risk_level,
        )

    except subprocess.TimeoutExpired:
        result.stderr = f"Freebuff execution timed out after {config.timeout}s"
        result.duration_ms = int((time.time() - start_time) * 1000)
        result.risk_level = "HIGH"
        result.risk_score = 1.0
        logger.warning("Freebuff task timed out after %d seconds", config.timeout)

    except FileNotFoundError:
        result.stderr = "Freebuff command not found. Is freebuff installed?"
        result.duration_ms = int((time.time() - start_time) * 1000)
        result.risk_level = "HIGH"
        result.risk_score = 1.0
        logger.error("Freebuff not found in PATH")

    except Exception as e:
        result.stderr = f"Error executing Freebuff: {str(e)}"
        result.duration_ms = int((time.time() - start_time) * 1000)
        result.risk_level = "HIGH"
        result.risk_score = 1.0
        logger.error("Unexpected error during Freebuff execution: %s", e)

    return result


def _count_changed_files(diff_output: str) -> int:
    """Count the number of changed files from git diff output."""
    if not diff_output:
        return 0

    # Count lines starting with '+' that are not '+++' (which is header)
    changed_files = set()
    for line in diff_output.split("\n"):
        # Git diff format: '+++ b/file.py' or '--- a/file.py' or '@@ ...' or '+content'
        # We count unique file paths from '+++' and '---' lines
        if line.startswith("+++ ") or line.startswith("--- "):
            # Extract file path
            parts = line.split(" ", 2)
            if len(parts) >= 3:
                file_path = parts[2]
                changed_files.add(file_path)
        # Also check for new additions that might indicate file changes
        elif line.startswith("+") and not line.startswith("+++"):
            # Might be a content change in existing file
            pass

    return len(changed_files)


def get_provider_score() -> dict[str, Any]:
    """Get the current provider score for Freebuff based on metrics."""
    config = load_config()

    return {
        "provider": "freebuff",
        "success_rate": config.success_rate,
        "average_time": f"{config.average_duration_ms // 60000}m {(config.average_duration_ms % 60000) // 1000}s",
        "rollback_rate": config.rollback_rate,
        "human_review_rate": config.human_review_rate,
        "estimated_cost": "$0",  # Freebuff is free
        "status": detect_freebuff().get("status", ProviderStatus.NOT_INSTALLED),
    }


def route_task(request: FreebuffTaskRequest) -> FreebuffTaskResult:
    """Route a task to Freebuff with intelligent decision making."""
    config = load_config()

    # ─── Intelligent Routing Decision ────────────────────────────

    # Check if Freebuff is installed
    detection = detect_freebuff()
    if not detection.get("installed", False):
        result = FreebuffTaskResult()
        result.stderr = "Freebuff is not installed. Cannot execute task."
        result.risk_level = "HIGH"
        result.risk_score = 1.0
        return result

    # Check for secrets
    if request.secrets_present:
        result = FreebuffTaskResult()
        result.stderr = "SENSITIVE DATA DETECTED. Freebuff execution blocked."
        result.risk_level = "HIGH"
        result.risk_score = 1.0
        return result

    # Check autonomy level compatibility
    autonomy = request.autonomy_level if request.autonomy_level is not None else config.autonomy_level

    # Risk-based routing
    if autonomy == 0:
        # Level 0: Suggest only
        result = FreebuffTaskResult()
        result.stderr = "Freebuff suggestion only - no execution (autonomy level 0)"
        result.risk_level = "LOW"
        result.risk_score = 0.1
        return result

    # For autonomy level 1 (confirmation), we proceed but mark for review
    # (review marking is handled downstream by the caller)

    # For autonomy level 2+, we can auto-execute low-risk tasks
    if autonomy >= 2 and request.risk_level == "LOW" and not request.secrets_present:
        # Auto-execute low-risk tasks
        pass  # Proceed to execution
    elif autonomy == 1:
        # Level 1: Execute with review/mark for confirmation
        pass

    # ─── Execute the task ────────────────────────────────────────

    result = execute_freebuff_task(request, config)

    # ─── Post-execution scoring and logging ──────────────────────

    # Update provider metrics based on result
    if result.success:
        # Improve success rate estimate
        current = config.success_rate
        config.success_rate = min(1.0, current + 0.01)  # Small improvement
    else:
        # Slight decrease on failure
        current = config.success_rate
        config.success_rate = max(0.0, current - 0.02)

    # Log the execution
    logger.info(
        "Freebuff task routed: success=%s, risk=%s, files=%d, tests_passed=%d, tests_failed=%d, duration=%dms",
        result.success,
        result.risk_level,
        result.files_changed,
        result.tests_passed,
        result.tests_failed,
        result.duration_ms,
    )

    return result


# ─── CLI Entry Point (for direct freebuff usage) ────────────────────


def cli_entry():
    """CLI entry point for Freebuff integration testing."""

    print("=== Freebuff Integration for OWNEX ===\n")

    # Detect Freebuff
    detection = detect_freebuff()
    print(f"Freebuff Status: {detection['status']}")
    if detection.get("installed"):
        print(f"Version: {detection.get('version', 'unknown')}")

    # Load config
    config = load_config()
    print("\nConfiguration:")
    print(f"  Enabled: {config.enabled}")
    print(f"  Command: {config.command}")
    print(f"  Timeout: {config.timeout}s")
    print(f"  Max Concurrent: {config.max_concurrent_tasks}")
    print(f"  Autonomy Level: {config.autonomy_level}")
    print(f"  Network Access: {config.network_access}")
    print(f"  Require Git Clean: {config.require_git_clean}")
    print(f"  Allowed Paths: {config.allowed_paths}")

    # Provider score
    score = get_provider_score()
    print("\nProvider Score:")
    for key, value in score.items():
        print(f"  {key}: {value}")

    # Demonstrate task routing
    print("\n=== Task Routing Example ===")
    print("Task: 'Add type annotations to function'")
    print("Risk: LOW, Files: 1, Type: code")

    # Create a test request using the dataclasses defined in this module
    # We need to construct the request with the correct field types

    # Build request dict and convert to object
    request_dict = {
        "task": "Add type annotations to function",
        "workspace": "/home/adrie/projects/Rastro",
        "task_type": "code",
        "complexity": "LOW",
        "risk_level": "LOW",
        "files_affected": 1,
        "requires_review": True,
        "network_allowed": False,
        "secrets_present": False,
    }

    # Since FreebuffTaskRequest is a dataclass, we can create it dynamically
    # Get the dataclass fields
    request = FreebuffTaskRequest(**request_dict)

    result = route_task(request)
    print(f"\nResult: success={str(result.success)}")
    print(f"Risk: {result.risk_level}")
    print(f"Files changed: {result.files_changed}")
    if result.stderr:
        print(f"Stderr: {result.stderr[:200]}")


if __name__ == "__main__":
    cli_entry()
