from typing import Any
from urllib.parse import urlencode

from cores.validation.replayer import ComparisonResult, RequestSpec

_REDACTED_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key", "api-key"}
_SKIP_HEADERS = {"content-length", "host"}


def _redact_headers(headers: dict[str, str] | None) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for k, v in (headers or {}).items():
        if k.lower() in _REDACTED_HEADERS:
            cleaned[k] = "<redacted>"
        elif k.lower() not in _SKIP_HEADERS:
            cleaned[k] = v
    return cleaned


def _url_with_params(url: str, params: dict[str, str] | None) -> str:
    if not params:
        return url
    qs = urlencode(params)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{qs}"


class EvidenceBuilder:
    def build_from_comparison(
        self,
        request_spec: RequestSpec,
        auth_label: str,
        comparison: ComparisonResult,
        verdict_id: int | None = None,
    ) -> dict[str, Any]:
        import json as _json

        return {
            "verdict_id": verdict_id,
            "attempt_label": f"attempt_{comparison.attempt}",
            "request_url": request_spec.url,
            "request_method": request_spec.method,
            "request_headers": _json.dumps(request_spec.headers) if request_spec.headers else None,
            "request_params": _json.dumps(request_spec.params) if request_spec.params else None,
            "request_body": request_spec.body,
            "auth_label": auth_label,
            "response_status": comparison.probe.status_code,
            "response_headers": _json.dumps(comparison.probe.headers) if comparison.probe.headers else None,
            "response_body": comparison.probe.body,
            "response_body_hash": comparison.probe.body_hash,
            "status_match": "true" if comparison.status_match else "false",
            "body_diff_ratio": str(comparison.body_diff_ratio),
            "sensitive_fields": _json.dumps(comparison.sensitive_fields_detected),
            "consistent": "true" if comparison.consistent else "false",
            "curl_command": self._build_curl(request_spec, auth_label, comparison),
            "python_command": self._build_python(request_spec, auth_label),
        }

    def build_all_from_comparisons(
        self,
        request_spec: RequestSpec,
        auth_context: Any,
        comparisons: list[ComparisonResult],
        verdict_id: int | None = None,
    ) -> list[dict[str, Any]]:
        auth_label = getattr(auth_context, "label", "unknown")
        return [self.build_from_comparison(request_spec, auth_label, c, verdict_id) for c in comparisons]

    def build_comparison_summary(self, comparisons: list[ComparisonResult]) -> dict[str, Any]:
        if not comparisons:
            return {"total": 0}
        return {
            "total": len(comparisons),
            "consistent_count": sum(1 for c in comparisons if c.consistent),
            "has_rate_limit": any(c.has_rate_limit for c in comparisons),
            "has_timeout": any(c.has_timeout for c in comparisons),
            "body_diff_range": [
                min(c.body_diff_ratio for c in comparisons),
                max(c.body_diff_ratio for c in comparisons),
            ],
            "status_matches": sum(1 for c in comparisons if c.status_match),
            "sensitive_fields_found": sorted(set(f for c in comparisons for f in c.sensitive_fields_detected)),
        }

    def build_poc_from_probe(self, probe_request: Any) -> dict[str, str]:
        """Build curl + python PoCs from a probe's ProbeRequest.

        Bridges cores/offensive/probe results into executable evidence
        without going through the replayer comparison path.
        """
        spec = RequestSpec(
            url=getattr(probe_request, "url", ""),
            method=getattr(probe_request, "method", "GET") or "GET",
            headers=dict(getattr(probe_request, "headers", {}) or {}),
            params=dict(getattr(probe_request, "params", {}) or {}),
            body=getattr(probe_request, "body", None),
        )
        return {
            "curl_command": self._build_curl(spec, "probe", None),
            "python_command": self._build_python(spec, "probe"),
        }

    def _build_curl(self, spec: RequestSpec, auth_label: str, comparison: ComparisonResult | None = None) -> str:
        """Reproducible curl built from the REQUEST spec (never response headers).

        GET-like methods carry params in the query string; others use -d.
        Auth-bearing headers are redacted, never dropped silently.
        """
        parts = ["curl"]
        if spec.method != "GET":
            parts.append(f"-X {spec.method}")
        for k, v in _redact_headers(spec.headers).items():
            parts.append(f"-H '{k}: {v}'")
        if spec.method in ("POST", "PUT", "PATCH"):
            if isinstance(spec.body, dict):
                import json as _json

                parts.append("-H 'Content-Type: application/json'")
                parts.append(f"-d '{_json.dumps(spec.body)}'")
            for k, v in (spec.params or {}).items():
                parts.append(f"-d '{k}={v}'")
            parts.append(f"'{spec.url}'")
        else:
            parts.append(f"'{_url_with_params(spec.url, spec.params)}'")
        return " \\\n  ".join(parts)

    def _build_python(self, spec: RequestSpec, auth_label: str) -> str:
        """Equivalent requests-based PoC (same request the curl reproduces)."""
        import json as _json

        lines = ["import requests", ""]
        headers = _redact_headers(spec.headers)
        lines.append(f"url = '{spec.url}'")
        lines.append(f"headers = {_json.dumps(headers)}")
        if spec.params:
            lines.append(f"params = {_json.dumps(spec.params)}")
        else:
            lines.append("params = None")
        if spec.body is not None:
            lines.append(f"body = {_json.dumps(spec.body)}")
            lines.append(f"r = requests.{spec.method.lower()}(url, headers=headers, params=params, json=body)")
        else:
            lines.append(f"r = requests.{spec.method.lower()}(url, headers=headers, params=params)")
        lines.append("print(r.status_code)")
        lines.append("print(r.text[:2000])")
        return "\n".join(lines)
