from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from .tools import _resolve_tool

logger = logging.getLogger("ownex.recon.naabu")


class NaabuRunner:
    def __init__(self, output_dir: Path, timeout: int = 300):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._binary = _resolve_tool("naabu") or "naabu"

    async def run_naabu(
        self,
        input_file: Path,
        out_file: str = "naabu.json",
        ports: str = "top-1000",
        rate: int = 1000,
        service_detect: bool = True,
        exclude_cdn: bool = True,
    ) -> Path:
        path = self.output_dir / out_file
        cmd = [
            self._binary,
            "-list",
            str(input_file),
            "-json",
            "-o",
            str(path),
            "-rate",
            str(rate),
        ]
        if service_detect:
            cmd.append("-sv")
        if exclude_cdn:
            cmd.append("-exclude-cdn")
        if ports and ports != "top-1000":
            cmd.extend(["-ports", ports])

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            path.write_text("NAABU TIMED OUT")
            return path
        if stderr:
            logger.debug("naabu stderr: %s", stderr.decode(errors="ignore")[:500])
        return path

    def load_open_ports(self, path: Path) -> list[dict[str, str | int]]:
        if not path.exists():
            return []
        results: list[dict[str, str | int]] = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                host = entry.get("host", entry.get("ip", ""))
                port = entry.get("port", 0)
                if host and port:
                    results.append(
                        {
                            "host": str(host),
                            "port": int(port),
                            "protocol": entry.get("protocol", "tcp"),
                        }
                    )
            except (json.JSONDecodeError, ValueError):
                continue
        return results

    def as_httpx_targets(self, open_ports: list[dict[str, str | int]]) -> list[str]:
        seen: set[str] = set()
        targets: list[str] = []
        for entry in open_ports:
            host = entry["host"]
            port = int(entry["port"])
            key = f"{host}:{port}"
            if key not in seen:
                seen.add(key)
                if port == 443:
                    targets.append(f"https://{host}")
                elif port == 80:
                    targets.append(f"http://{host}")
                else:
                    targets.append(f"http://{host}:{port}")
                    targets.append(f"https://{host}:{port}")
        return targets
