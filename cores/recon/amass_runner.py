"""
core_engines.recon.amass_runner — Deep subdomain enumeration via Amass.

Amass is run in passive + active modes depending on configuration.
Passive mode uses only free data sources (certificate transparency,
search engines, DNS). Active mode adds DNS brute-force with a wordlist.

Installation:
  # Go install (recommended)
  go install -v github.com/owasp-amass/amass/v4/...@master

  # Or package manager (Linux)
  sudo snap install amass
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger("catseye.recon.amass")

ENUM_MODES = {
    "passive": ["amass", "enum", "-passive", "-nocolor", "-json"],
    "active": ["amass", "enum", "-active", "-nocolor", "-json"],
    "intel": ["amass", "intel", "-whois", "-nocolor", "-json"],
}


class AmassRunner:
    """Wrapper around Amass for deep subdomain enumeration.

    Amass discovers 3-5x more subdomains than subfinder alone by combining:
      - Certificate transparency logs (crt.sh, Google, Facebook, etc.)
      - DNS brute-force with large wordlists
      - Reverse DNS sweeps
      - Search engine scraping
      - Machine learning predictions (Amass v4)
    """

    def __init__(self, output_dir: Path | str | None = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "amass_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._amass_path = self._resolve_amass()

    def _resolve_amass(self) -> str | None:
        """Find amass binary, preferring Go-installed version."""
        go_path = Path.home() / "go" / "bin" / "amass"
        if go_path.is_file():
            return str(go_path)
        return shutil.which("amass")

    def is_available(self) -> bool:
        return self._amass_path is not None

    async def enum_passive(self, domain: str, timeout: int = 180) -> list[dict[str, Any]]:
        """Run Amass in passive mode — no DNS queries to the target."""
        return await self._run_enum(domain, mode="passive", timeout=timeout)

    async def enum_active(self, domain: str, timeout: int = 600) -> list[dict[str, Any]]:
        """Run Amass in active mode — includes DNS brute-force.

        Only use for targets explicitly in scope.
        """
        return await self._run_enum(domain, mode="active", timeout=timeout)

    async def _run_enum(
        self, domain: str, mode: str = "passive", timeout: int = 300,
    ) -> list[dict[str, Any]]:
        if not self._amass_path:
            logger.warning("Amass not installed. Skipping enum for %s", domain)
            return []

        output_file = self.output_dir / f"{domain}_{mode}.json"
        cmd = ENUM_MODES[mode][:]
        cmd += ["-d", domain, "-o", str(output_file)]

        logger.info("Amass %s enum: %s (timeout=%ds)", mode, domain, timeout)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                if proc.returncode != 0:
                    stderr_text = stderr.decode("utf-8", errors="replace")[:500]
                    logger.warning("Amass %s returned %d: %s", mode, proc.returncode, stderr_text)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                logger.warning("Amass %s timed out after %ds", mode, timeout)
        except FileNotFoundError:
            logger.error("Amass binary not found at %s", self._amass_path)
            return []
        except Exception as e:
            logger.error("Amass %s failed: %s", mode, e)
            return []

        # Parse results
        results: list[dict[str, Any]] = []
        if output_file.exists() and output_file.stat().st_size > 0:
            try:
                raw = output_file.read_text(encoding="utf-8", errors="ignore")
                for line in raw.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        results.append(entry)
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                logger.warning("Failed to parse Amass output: %s", e)

        logger.info(
            "Amass %s enum for %s: %d subdomains found",
            mode, domain, len(results),
        )
        return results

    def parse_subdomains(self, results: list[dict[str, Any]]) -> list[str]:
        """Extract unique subdomain names from Amass results."""
        subdomains: set[str] = set()
        for entry in results:
            name = entry.get("name", "").strip().lower()
            if name and not name.startswith("*"):
                subdomains.add(name)
            # Also check addresses records
            for addr in entry.get("addresses", []):
                ip = addr.get("ip", "")
                if ip and not ip.startswith("*"):
                    subdomains.add(ip)
        return sorted(subdomains)

    async def run_intel(self, domain: str, timeout: int = 120) -> list[dict[str, Any]]:
        """Run Amass intel to discover root domains via whois/ reverse lookup."""
        if not self._amass_path:
            return []

        output_file = self.output_dir / f"{domain}_intel.json"
        cmd = ["amass", "intel", "-whois", "-d", domain, "-json", str(output_file)]

        logger.info("Amass intel: %s", domain)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
        except Exception as e:
            logger.warning("Amass intel failed: %s", e)
            return []

        results: list[dict[str, Any]] = []
        if output_file.exists() and output_file.stat().st_size > 0:
            try:
                raw = output_file.read_text(encoding="utf-8", errors="ignore")
                for line in raw.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        results.append(entry)
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                logger.warning("Failed to parse Amass intel output: %s", e)

        return results
