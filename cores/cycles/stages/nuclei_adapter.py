"""NucleiAdapter — wraps NucleiTool for SecurityCycle recon stage integration."""

from __future__ import annotations

import logging
from typing import Any

from cores.tools.nuclei import NucleiTool

logger = logging.getLogger("ownex.cycles.nuclei")


class NucleiAdapter:
    """Adapter to run Nuclei scans within the SecurityCycle recon stage."""

    def __init__(
        self,
        templates_path: str = "/home/adriel/nuclei-templates",
        nuclei_binary: str = "/tmp/nuclei",
        severity: str = "medium,high,critical",
        rate_limit: int = 100,
        concurrency: int = 25,
        timeout: int = 120,
    ) -> None:
        self.templates_path = templates_path
        self.nuclei_binary = nuclei_binary
        self.severity = severity
        self.rate_limit = rate_limit
        self.concurrency = concurrency
        self.timeout = timeout
        self._tool: NucleiTool | None = None

    @property
    def tool(self) -> NucleiTool:
        if self._tool is None:
            self._tool = NucleiTool()
        return self._tool

    def is_available(self) -> bool:
        """Check if nuclei binary and templates are available."""
        import os

        return os.path.exists(self.nuclei_binary) and os.path.exists(self.templates_path)

    def scan_target(
        self,
        target: str,
        scope: dict[str, Any] | None = None,
        depth: str = "standard",
    ) -> dict[str, Any]:
        """Run nuclei scan on a target and return structured results."""
        if not self.is_available():
            logger.warning("Nuclei not available (binary: %s, templates: %s)", self.nuclei_binary, self.templates_path)
            return {"findings": [], "error": "Nuclei not available"}

        # Build target list from scope or single target
        targets = [target]
        if scope and "subdomains" in scope:
            targets.extend(scope["subdomains"])

        # Determine template set based on depth
        template_dirs = self._get_template_dirs(depth)

        all_findings: list[dict[str, Any]] = []

        for template_dir in template_dirs:
            try:
                findings = self.tool.scan(
                    targets=targets,
                    severity=self.severity,
                    templates=template_dir,
                    rate_limit=self.rate_limit,
                    concurrency=self.concurrency,
                    timeout=self.timeout,
                )
                for f in findings:
                    all_findings.append(
                        {
                            "template_id": f.evidence.get("template_id", ""),
                            "name": f.name,
                            "severity": f.severity,
                            "description": f.description,
                            "target": f.target,
                            "matched_at": f.evidence.get("matched_at", ""),
                            "extracted_results": f.evidence.get("extracted_results", []),
                            "curl_command": f.evidence.get("curl_command", ""),
                            "request": f.evidence.get("request", ""),
                            "response": f.evidence.get("response", ""),
                            "tags": f.tags,
                        }
                    )
            except Exception as exc:
                logger.warning("Nuclei scan failed for %s: %s", template_dir, exc)

        return {
            "findings": all_findings,
            "count": len(all_findings),
            "templates_used": template_dirs,
        }

    def _get_template_dirs(self, depth: str) -> list[str]:
        """Select template directories based on scan depth."""
        base = self.templates_path
        if depth == "shallow":
            return [
                f"{base}/http/exposed-panels",
                f"{base}/http/exposures",
                f"{base}/http/misconfiguration",
            ]
        elif depth == "deep":
            return [base]  # All templates
        else:  # standard
            return [
                f"{base}/http/exposed-panels",
                f"{base}/http/exposures",
                f"{base}/http/misconfiguration",
                f"{base}/http/vulnerabilities",
                f"{base}/http/cves",
                f"{base}/http/security-misconfiguration",
            ]


def run_nuclei_recon(
    target: str,
    scope: dict[str, Any] | None = None,
    depth: str = "standard",
) -> dict[str, Any]:
    """Convenience function for SecurityCycle integration."""
    adapter = NucleiAdapter()
    return adapter.scan_target(target, scope, depth)
