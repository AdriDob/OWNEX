from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProbeRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    params: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "url": self.url,
            "headers": dict(self.headers),
            "body": self.body,
            "params": dict(self.params),
        }


@dataclass
class AttackStep:
    purpose: str
    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    params: dict[str, str] = field(default_factory=dict)
    payload_key: str | None = None
    expected_outcome: str = ""

    def to_request(self, base_url: str) -> ProbeRequest:
        url = base_url.rstrip("/") + "/" + self.path.lstrip("/")
        return ProbeRequest(
            method=self.method,
            url=url,
            headers=dict(self.headers),
            body=self.body,
            params=dict(self.params),
        )


@dataclass
class TestPlan:
    hypothesis_id: str
    vulnerability_type: str
    target: str
    endpoint_path: str
    steps: list[AttackStep] = field(default_factory=list)
    payloads: dict[str, list[str]] = field(default_factory=dict)
    detection_strategy: str = ""
    auth_required: bool = False
