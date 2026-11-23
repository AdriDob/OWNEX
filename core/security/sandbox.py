"""Sandbox execution infrastructure for isolated code execution.

Provides isolated execution environments using Docker with proper security
constraints. Designed for OWNEX Engineering Factory v1.

Security principles:
- Rootless containers when possible
- No host filesystem access outside the mounted workspace
- No Docker socket access
- No privileged mode
- Resource limits (CPU, memory, time)
- Network isolation by default
- Secure cleanup
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.security.sandbox")


class SandboxConfig:
    """Configuration for sandbox execution isolation."""

    # Resource limits
    CPU_LIMIT: float = 2.0  # CPU cores
    MEMORY_LIMIT_MB: int = 512  # Maximum memory in MB
    TIME_LIMIT_S: int = 120  # Maximum execution time in seconds

    # Container image used for isolation
    DOCKER_IMAGE: str = "python:3.12-slim"

    # Filesystem boundaries
    ENABLE_WORKSPACE: bool = True
    READ_ONLY_HOST_PATHS: tuple[str, ...] = ()  # Empty = no host access

    # Network boundaries
    ENABLE_NETWORK: bool = False  # Default: no network access
    ALLOWED_PORTS: tuple[int, ...] = ()

    # Process boundaries
    DISABLE_PRIVILEGED: bool = True
    DROP_CAPABILITIES: tuple[str, ...] = ("ALL",)

    # Security
    READ_ONLY_ROOTFILESYSTEM: bool = True
    PROHIBIT_DOCKER_SOCKET: bool = True
    PROHIBIT_SHARED_MEMORY: bool = True


class SandboxResult:
    """Result of sandbox execution."""

    def __init__(
        self,
        success: bool,
        output: str = "",
        error: str = "",
        exit_code: int = 0,
        execution_time: float = 0.0,
        resource_usage: dict[str, Any] | None = None,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.exit_code = exit_code
        self.execution_time = execution_time
        self.resource_usage = resource_usage or {}


class Sandbox:
    """Docker-based sandbox for isolated execution.

    Provides isolated execution environments with strict security
    constraints suitable for executing external/third-party code.
    ``execute`` fails closed when no verified Docker daemon is available;
    ``_fallback_execute`` remains only for explicit trusted callers.
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self._docker_available = self._check_docker()
        self._daemon_ok: bool | None = None

    def _check_docker(self) -> bool:
        """Check if the Docker CLI is available."""
        return shutil.which("docker") is not None

    async def is_ready(self) -> bool:
        """True only when a usable Docker daemon answers ``docker info``.

        The CLI existing is not enough: the daemon may be stopped. Cached
        per instance so repeated calls in one run cost one probe.
        """
        if not self._docker_available:
            return False
        if self._daemon_ok is not None:
            return self._daemon_ok
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "info",
                "--format",
                "{{.ServerVersion}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            self._daemon_ok = proc.returncode == 0
            if not self._daemon_ok:
                logger.warning("Docker daemon not ready: %s", stderr.decode()[:300])
        except Exception as exc:
            logger.warning("Docker readiness probe failed: %s", exc)
            self._daemon_ok = False
        return self._daemon_ok

    async def execute(
        self,
        work_dir: Path | str,
        command: list[str],
        input_data: bytes | None = None,
        timeout: int | None = None,
        writable: bool = False,
        network: bool | None = None,
    ) -> SandboxResult:
        """Execute a command in an isolated sandbox environment.

        Args:
            work_dir: Working directory mounted at ``/work`` (read-only by
                default; ``writable=True`` mounts it rw for ephemeral
                workspaces that need build caches/artifacts).
            command: Command and arguments to execute
            input_data: Optional stdin data
            timeout: Override default time limit in seconds
            writable: Mount ``/work`` read-write (only for disposable clones)
            network: Override network policy; ``None`` uses the config default

        Returns:
            SandboxResult with execution output and metadata
        """
        if not self._docker_available or not await self.is_ready():
            return SandboxResult(
                success=False,
                error="sandbox unavailable: docker daemon not ready (fail-closed, no host fallback for untrusted code)",
                exit_code=-1,
            )

        return await self._docker_execute(
            Path(work_dir), command, input_data, timeout, writable=writable, network=network
        )

    async def _docker_execute(
        self,
        work_dir: Path,
        command: list[str],
        input_data: bytes | None = None,
        timeout: int | None = None,
        writable: bool = False,
        network: bool | None = None,
    ) -> SandboxResult:
        """Execute command in Docker container with security constraints."""
        final_timeout = timeout or self.config.TIME_LIMIT_S
        docker_args = self._build_docker_args(work_dir, command, writable=writable, network=network)
        start_time = time.time()

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                *docker_args,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_data), timeout=final_timeout)
            except TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxResult(
                    success=False,
                    error=f"Execution timed out after {final_timeout}s",
                    exit_code=124,
                    execution_time=time.time() - start_time,
                )

            return SandboxResult(
                success=proc.returncode == 0,
                output=stdout.decode("utf-8", errors="replace") if stdout else "",
                error=stderr.decode("utf-8", errors="replace") if stderr else "",
                exit_code=proc.returncode,
                execution_time=time.time() - start_time,
            )

        except Exception as exc:
            logger.exception("Sandbox execution failed")
            return SandboxResult(
                success=False,
                error=f"Sandbox execution error: {exc}",
                exit_code=-1,
                execution_time=time.time() - start_time,
            )

    def _build_docker_args(
        self,
        work_dir: Path,
        command: list[str],
        writable: bool = False,
        network: bool | None = None,
    ) -> list[str]:
        """Build `docker run` arguments that enforce the isolation policy.

        Guarantees: no privileged mode, read-only root filesystem, dropped
        capabilities, no Docker socket mount, no network unless enabled,
        explicit CPU/memory limits and a read-only workspace mount.
        """
        args: list[str] = ["run", "--rm"]

        if self.config.DISABLE_PRIVILEGED:
            args.append("--security-opt=no-new-privileges")

        for capability in self.config.DROP_CAPABILITIES:
            args.extend(["--cap-drop", capability])

        if self.config.READ_ONLY_ROOTFILESYSTEM:
            args.append("--read-only")
            # Writable scratch space for commands that need it, isolated per run.
            args.extend(["--tmpfs", "/tmp:rw,noexec,nosuid,size=64m"])

        # The Docker socket is deliberately never mounted (PROHIBIT_DOCKER_SOCKET).

        args.extend(["--memory", f"{self.config.MEMORY_LIMIT_MB}m"])
        args.extend(["--cpus", str(self.config.CPU_LIMIT)])

        for path in self.config.READ_ONLY_HOST_PATHS:
            args.extend(["--volume", f"{path}:{path}:ro"])

        work_dir_str = str(work_dir.resolve())
        args.extend(["--volume", f"{work_dir_str}:/work:{'rw' if writable else 'ro'}"])
        args.extend(["--user", "1000:1000"])

        enable_network = self.config.ENABLE_NETWORK if network is None else network
        if enable_network:
            args.append("--network=bridge")
            for port in self.config.ALLOWED_PORTS:
                args.extend(["--publish", f"{port}:{port}"])
        else:
            args.append("--network=none")

        args.extend(["--workdir", "/work"])
        args.append(self.config.DOCKER_IMAGE)
        args.extend(command)

        return args

    async def _fallback_execute(
        self,
        command: list[str],
        input_data: bytes | None = None,
        timeout: int | None = None,
    ) -> SandboxResult:
        """Fallback execution when Docker is not available.

        Runs the command as a subprocess with a CPU-time limit applied in the
        child process only (never in the agent process itself). Memory limits
        are enforced only in Docker mode: the forked child inherits this
        process's address space, so ``RLIMIT_AS`` here would kill it instantly.
        """
        final_timeout = timeout or self.config.TIME_LIMIT_S
        start_time = time.time()

        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=self._apply_child_limits(final_timeout),
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_data), timeout=final_timeout)
            except TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxResult(
                    success=False,
                    error=f"Execution timed out after {final_timeout}s",
                    exit_code=124,
                    execution_time=time.time() - start_time,
                )

            return SandboxResult(
                success=proc.returncode == 0,
                output=stdout.decode("utf-8", errors="replace") if stdout else "",
                error=stderr.decode("utf-8", errors="replace") if stderr else "",
                exit_code=proc.returncode,
                execution_time=time.time() - start_time,
            )

        except Exception as exc:
            logger.exception("Fallback sandbox execution failed")
            return SandboxResult(
                success=False,
                error=f"Fallback execution error: {exc}",
                exit_code=-1,
                execution_time=time.time() - start_time,
            )

    def _apply_child_limits(self, cpu_seconds: int):
        """Return a preexec hook that applies rlimits to the child only."""

        def _limits() -> None:  # pragma: no cover - runs in the forked child
            import resource

            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

        return _limits
