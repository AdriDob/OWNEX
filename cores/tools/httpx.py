"""httpx wrapper — HTTP endpoint probing."""
import json
import logging
import os
import shutil

from cores.tools.base import BaseTool, UnifiedResult

logger = logging.getLogger("rastro.tools.httpx")


class HttpxTool(BaseTool):
    name = "httpx"
    install_hint = "go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest"
    min_version = "1.3.0"

    def __init__(self, binary_path: str | None = None):
        if binary_path is None:
            go_bin = os.path.expanduser("~/go/bin/httpx")
            if shutil.which(go_bin):
                binary_path = go_bin
        super().__init__(binary_path)

    def probe(
        self,
        targets: list[str],
        threads: int = 50,
        timeout: int = 180,
        follow_redirects: bool = False,
        tech_detect: bool = True,
        status_code: bool = True,
        content_length: bool = True,
        title: bool = True,
    ) -> list[UnifiedResult]:
        """Probe a list of targets (domains/URLs) for live HTTP endpoints."""
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp(prefix="httpx_"))
        try:
            target_file = tmp / "targets.txt"
            target_file.write_text("\n".join(targets))

            args = ["-json", "-l", str(target_file)]
            if tech_detect:
                args.append("-tech-detect")
            if follow_redirects:
                args.append("-follow-redirects")
            if status_code:
                args.append("-status-code")
            if content_length:
                args.append("-content-length")
            if title:
                args.append("-title")
            args.extend(["-t", str(threads)])

            result = self.run(args, timeout=timeout)
            if result.success:
                return self._parse_json_lines(result.stdout)
            logger.warning("httpx probe failed: %s", result.error[:200])
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
                url = data.get("url", "")
                if not url:
                    continue
                tech_list = data.get("tech", []) or []
                results.append(UnifiedResult(
                    source="httpx",
                    target=url,
                    result_type="endpoint",
                    confidence=0.9,
                    name=f"Live: {url}",
                    evidence={
                        "status_code": data.get("status_code"),
                        "content_length": data.get("content_length"),
                        "title": data.get("title", ""),
                        "webserver": data.get("webserver", ""),
                        "technologies": tech_list,
                    },
                    tags=["live", *[f"tech:{t}" for t in tech_list]],
                ))
            except json.JSONDecodeError:
                url = line.strip()
                if url:
                    results.append(UnifiedResult(
                        source="httpx", target=url, result_type="endpoint",
                        confidence=0.5, name=f"Live: {url}",
                    ))
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_json_lines(stdout)
