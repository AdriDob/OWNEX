"""System monitoring and control tools — processes, services, resources."""

from __future__ import annotations

import contextlib
import logging
import platform
import subprocess
from pathlib import Path

import psutil

from apps.hermes.tools.base import BaseTool, ToolResult

logger = logging.getLogger("catseye.hermes.tools.system")


class ProcessManager(BaseTool):
    name = "process"
    description = "List, monitor, and manage system processes"

    def check_available(self) -> ToolResult:
        return ToolResult(True, "psutil available")

    def list_all(self, sort_by: str = "memory") -> ToolResult:
        processes = []
        for proc in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent", "status"]):
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                processes.append(proc.info)
        processes.sort(key=lambda p: p.get(sort_by, 0) or 0, reverse=True)
        return ToolResult(True, f"{len(processes)} processes", {"processes": processes[:50]})

    def top_memory(self, limit: int = 10) -> ToolResult:
        all_proc = []
        for proc in psutil.process_iter(["pid", "name", "memory_percent", "memory_info"]):
            try:
                info = proc.info
                if info["memory_info"]:
                    info["memory_mb"] = round(info["memory_info"].rss / (1024 * 1024), 1)
                all_proc.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        all_proc.sort(key=lambda p: p.get("memory_percent", 0) or 0, reverse=True)
        return ToolResult(True, f"Top {min(limit, len(all_proc))} processes by RAM", {"processes": all_proc[:limit]})

    def kill(self, pid: int) -> ToolResult:
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            return ToolResult(True, f"Terminated {name} (PID {pid})")
        except psutil.NoSuchProcess:
            return ToolResult(False, f"No process with PID {pid}")
        except psutil.AccessDenied:
            return ToolResult(False, f"Access denied to terminate PID {pid} (run as admin)")

    def get_details(self, pid: int) -> ToolResult:
        try:
            proc = psutil.Process(pid)
            info = {
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_mb": round(proc.memory_info().rss / (1024 * 1024), 1),
                "create_time": proc.create_time(),
                "exe": proc.exe(),
                "cmdline": proc.cmdline(),
                "num_threads": proc.num_threads(),
                "connections": len(proc.connections()),
            }
            return ToolResult(True, f"Process {proc.name()} (PID {pid})", info)
        except psutil.NoSuchProcess:
            return ToolResult(False, f"No process with PID {pid}")
        except psutil.AccessDenied:
            return ToolResult(False, f"Access denied for PID {pid}")


class SystemMonitor(BaseTool):
    name = "system"
    description = "CPU, RAM, disk, network, GPU monitoring"

    def check_available(self) -> ToolResult:
        return ToolResult(True, "psutil available")

    def snapshot(self) -> ToolResult:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()
        cpu_freq = psutil.cpu_freq()
        return ToolResult(
            True,
            "System snapshot",
            {
                "platform": platform.platform(),
                "cpu": {
                    "cores_physical": psutil.cpu_count(logical=False),
                    "cores_logical": psutil.cpu_count(logical=True),
                    "percent": psutil.cpu_percent(interval=0.5),
                    "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else 0,
                },
                "memory": {
                    "total_gb": round(mem.total / (1024**3), 2),
                    "used_gb": round(mem.used / (1024**3), 2),
                    "available_gb": round(mem.available / (1024**3), 2),
                    "percent": mem.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": disk.percent,
                },
                "network": {
                    "bytes_sent_mb": round(net.bytes_sent / (1024 * 1024), 1),
                    "bytes_recv_mb": round(net.bytes_recv / (1024 * 1024), 1),
                },
                "boot_time": psutil.boot_time(),
                "users": [u.name for u in psutil.users()],
            },
        )


class ServiceManager(BaseTool):
    name = "service"
    description = "List and manage Windows/Linux services"

    def check_available(self) -> ToolResult:
        return ToolResult(True, "subprocess available")

    def list_all(self) -> ToolResult:
        is_windows = platform.system() == "Windows"
        try:
            if is_windows:
                r = subprocess.run(
                    ["powershell", "-Command", "Get-Service | Select-Object Name,Status,DisplayName | ConvertTo-Json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            else:
                r = subprocess.run(
                    ["systemctl", "list-units", "--type=service", "--no-pager"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
            if r.returncode == 0:
                return ToolResult(True, "Services retrieved", {"services": r.stdout[:5000]})
            return ToolResult(False, r.stderr.strip())
        except Exception as exc:
            return ToolResult(False, str(exc))

    def start(self, name: str) -> ToolResult:
        is_windows = platform.system() == "Windows"
        try:
            if is_windows:
                r = subprocess.run(
                    ["powershell", "-Command", f"Start-Service -Name '{name}'"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            else:
                r = subprocess.run(["sudo", "systemctl", "start", name], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return ToolResult(True, f"Service '{name}' started")
            return ToolResult(False, r.stderr.strip() or f"Failed to start '{name}'")
        except Exception as exc:
            return ToolResult(False, str(exc))

    def stop(self, name: str) -> ToolResult:
        is_windows = platform.system() == "Windows"
        try:
            if is_windows:
                r = subprocess.run(
                    ["powershell", "-Command", f"Stop-Service -Name '{name}'"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            else:
                r = subprocess.run(["sudo", "systemctl", "stop", name], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return ToolResult(True, f"Service '{name}' stopped")
            return ToolResult(False, r.stderr.strip() or f"Failed to stop '{name}'")
        except Exception as exc:
            return ToolResult(False, str(exc))


class FileManager(BaseTool):
    name = "files"
    description = "File and directory listing, search, operations"

    def check_available(self) -> ToolResult:
        return ToolResult(True, "stdlib available")

    def list_dir(self, path: str = ".") -> ToolResult:
        try:
            p = Path(path).expanduser().resolve()
            if not p.is_dir():
                return ToolResult(False, f"Not a directory: {path}")
            entries = []
            for entry in sorted(p.iterdir()):
                try:
                    stat = entry.stat()
                    entries.append(
                        {
                            "name": entry.name,
                            "type": "dir" if entry.is_dir() else "file",
                            "size_bytes": stat.st_size,
                            "modified": stat.st_mtime,
                        }
                    )
                except OSError:
                    entries.append({"name": entry.name, "type": "unknown"})
            return ToolResult(True, f"{len(entries)} entries in {p}", {"entries": entries, "path": str(p)})
        except Exception as exc:
            return ToolResult(False, str(exc))

    def disk_usage(self) -> ToolResult:
        try:
            parts = psutil.disk_partitions()
            disks = []
            for part in parts:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append(
                        {
                            "device": part.device,
                            "mount": part.mountpoint,
                            "fstype": part.fstype,
                            "total_gb": round(usage.total / (1024**3), 2),
                            "used_gb": round(usage.used / (1024**3), 2),
                            "free_gb": round(usage.free / (1024**3), 2),
                            "percent": usage.percent,
                        }
                    )
                except PermissionError:
                    pass
            return ToolResult(True, f"{len(disks)} volumes", {"volumes": disks})
        except Exception as exc:
            return ToolResult(False, str(exc))
