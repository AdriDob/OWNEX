"""Nuclei wrapper — vulnerability scanning."""
import json
import logging
from datetime import datetime, timezone

from cores.tools.base import BaseTool, UnifiedResult

logger = logging.getLogger("rastro.tools.nuclei")


class NucleiTool(BaseTool):
    name = "nuclei"
    install_hint = "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
    min_version = "3.0.0"

    SEVERITY_MAP = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "info": "info",
        "unknown": "info",
    }

    def scan(
        self,
        targets: list[str],
        severity: str = "medium",
        templates: str | None = None,
        exclude_templates: str | None = None,
        rate_limit: int = 150,
        concurrency: int = 50,
        timeout: int = 600,
    ) -> list[UnifiedResult]:
        """Run nuclei scan against targets."""
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp(prefix="nuclei_"))
        try:
            target_file = tmp / "targets.txt"
            target_file.write_text("\n".join(targets))

            args = ["-j", "-severity", severity, "-silent", "-l", str(target_file)]
            if templates:
                args.extend(["-t", templates])
            if exclude_templates:
                args.extend(["-exclude-templates", exclude_templates])
            args.extend(["-rl", str(rate_limit), "-c", str(concurrency)])

            result = self.run(args, timeout=timeout)
            if result.success:
                return self._parse_json_lines(result.stdout)
            logger.warning("nuclei scan failed: %s", result.error[:200])
            return []
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def _parse_json_lines(self, stdout: str) -> list[UnifiedResult]:
        results = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                host = data.get("host", data.get("matched-at", ""))
                template_id = data.get("template-id", "")
                template_name = data.get("template", template_id)
                severity = data.get("info", {}).get("severity", "info").lower()
                name = data.get("info", {}).get("name", template_id)
                description = data.get("info", {}).get("description", "")
                tags = data.get("info", {}).get("tags", [])
                if isinstance(tags, str):
                    tags = tags.split(",") if tags else []
                matched = data.get("matched-at", host)
                extracted = data.get("extracted-results", [])

                results.append(UnifiedResult(
                    source="nuclei",
                    target=host,
                    result_type="vulnerability",
                    severity=self.SEVERITY_MAP.get(severity, "info"),
                    confidence=0.7 if severity in ("critical", "high") else 0.5,
                    name=f"[{severity.upper()}] {name}",
                    description=description,
                    evidence={
                        "template_id": template_id,
                        "matched_at": matched,
                        "extracted_results": extracted,
                        "curl_command": data.get("curl-command", ""),
                        "request": data.get("request", ""),
                        "response": data.get("response", ""),
                    },
                    tags=tags,
                    raw=line,
                ))
            except json.JSONDecodeError:
                pass
        return results

    def list_templates(self) -> list[str]:
        """List available nuclei templates."""
        result = self.run(["-tl"], timeout=30)
        if result.success:
            return [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
        return []

    def update_templates(self) -> bool:
        """Update nuclei templates."""
        result = self.run(["-update-templates"], timeout=120)
        return result.success

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_json_lines(stdout)
