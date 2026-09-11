"""Live offensive loop — reasoner → ProbeEngine → Finding, against an authorized fixture.

The fixture is a loopback-only HTTP server (stdlib, no deps) with INTENTIONAL
vulnerabilities. It is the only target this test ever touches: fully
authorized, deterministic, no external network.

Proves with real HTTP (httpx, not mocks):
  - IDORReasoner/XSSReasoner/SQLiReasoner emit hypotheses on fixture endpoints
  - ProbeEngine.probe() hits the FULL path (P0 regression: host-only probing)
  - confirmations persist as Finding rows with executable curl+python PoCs
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from cores.offensive.engine import OffensiveEngine
from cores.offensive.models import Hypothesis
from cores.offensive.probe.engine import ProbeEngine, _resolve_request_url
from cores.validation.evidence_builder import EvidenceBuilder


class _VulnHandler(BaseHTTPRequestHandler):
    """Intentionally vulnerable fixture app. NEVER bind beyond loopback."""

    server_version = "FixtureHTTP/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A002 — stdlib signature
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        get = lambda k, d="": qs.get(k, [d])[0]  # noqa: E731

        if parsed.path == "/api/user":
            uid = get("id", "1")
            if not uid.isdigit():
                self._send(400, b'{"error":"invalid id"}')
                return
            self._send(
                200, json.dumps({"id": int(uid), "name": f"user{uid}", "email": f"user{uid}@example.com"}).encode()
            )
            return

        if parsed.path == "/search":
            q = get("q", "")
            html = f"<html><body><h1>Results for: {q}</h1></body></html>"
            self._send(200, html.encode(), "text/html")
            return

        if parsed.path == "/product":
            pid = get("id", "1")
            if "'" in pid or "OR" in pid.upper():
                self._send(500, f"{{'error': \"SQL syntax error near '{pid}' (SQLite3::SQLException)\"}}".encode())
                return
            self._send(200, json.dumps({"id": pid, "name": "widget", "price": 9.99}).encode())
            return

        if parsed.path == "/admin":
            # Broken access control simulation: ANY param valued "admin" → admin data.
            if any(v == "admin" for vals in qs.values() for v in vals):
                big = json.dumps({"role": "admin", "secret": "flag{fixture}", "users": ["alice", "bob", "carol"]})
                self._send(200, big.encode())
                return
            self._send(200, b'{"role":"user"}')
            return

        if parsed.path == "/fetch":
            url = get("url", "")
            if "127.0.0.1" in url:
                self._send(502, b'{"error":"Bad Gateway: connection refused by upstream"}')
                return
            self._send(200, json.dumps({"fetched_bytes": 1256, "url": url}).encode())
            return

        if parsed.path == "/health":
            self._send(200, b'{"ok": true}')
            return

        self._send(404, b'{"error":"not found"}')


@pytest.fixture(scope="module")
def fixture_base_url() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _VulnHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def _endpoint(base: str, path: str, params: dict[str, str]) -> dict:
    return {"path": path, "method": "GET", "params": params, "host": base, "target_id": ""}


class TestUrlResolution:
    def test_path_plus_host(self):
        assert _resolve_request_url("/api/users", "http://127.0.0.1:8000") == "http://127.0.0.1:8000/api/users"

    def test_absolute_endpoint_wins(self):
        assert (
            _resolve_request_url("http://127.0.0.1:8000/api/users/1", "http://other:9")
            == "http://127.0.0.1:8000/api/users/1"
        )

    def test_missing_slash(self):
        assert _resolve_request_url("api/users", "http://h:1/") == "http://h:1/api/users"


class TestEvidencePoC:
    def test_curl_uses_request_not_response(self):
        from types import SimpleNamespace

        req = SimpleNamespace(
            url="http://127.0.0.1:9/api/user",
            method="GET",
            headers={"Authorization": "Bearer secret", "X-A": "b"},
            params={"id": "999999"},
            body=None,
        )
        poc = EvidenceBuilder().build_poc_from_probe(req)
        assert "/api/user?id=999999" in poc["curl_command"]
        assert "Bearer secret" not in poc["curl_command"]
        assert "<redacted>" in poc["curl_command"]
        assert "requests.get" in poc["python_command"]
        assert "999999" in poc["python_command"]


class TestLiveLoop:
    def test_idor_confirmed_and_persisted(self, fixture_base_url):
        engine = OffensiveEngine()
        out = engine.hunt_endpoint(_endpoint(fixture_base_url, "/api/user", {"id": "1"}))
        assert out["hypotheses"] >= 1
        idor = [p for p in out["probed"] if p["vulnerability_type"] == "idor" and p["confirmed"]]
        assert idor, f"IDOR not confirmed: {out['probed']}"
        assert out["finding_ids"], "confirmed IDOR must persist a Finding"
        assert "/api/user" in idor[0]["poc"]["curl_command"]
        assert "id=999999" in idor[0]["poc"]["curl_command"]

    def test_xss_confirmed(self, fixture_base_url):
        engine = OffensiveEngine()
        out = engine.hunt_endpoint(_endpoint(fixture_base_url, "/search", {"q": "hello123"}))
        xss = [p for p in out["probed"] if p["vulnerability_type"] == "xss" and p["confirmed"]]
        assert xss, f"XSS not confirmed: {out['probed']}"
        assert out["finding_ids"]

    def test_sqli_confirmed(self, fixture_base_url):
        engine = OffensiveEngine()
        out = engine.hunt_endpoint(_endpoint(fixture_base_url, "/product", {"id": "7"}))
        sqli = [p for p in out["probed"] if p["vulnerability_type"] == "sqli" and p["confirmed"]]
        assert sqli, f"SQLi not confirmed: {out['probed']}"
        assert sqli[0]["confidence"] >= 0.9 - 1e-9

    def test_finding_row_holds_evidence(self, fixture_base_url):
        from database.db import SessionLocal
        from database.models import Finding

        engine = OffensiveEngine()
        out = engine.hunt_endpoint(_endpoint(fixture_base_url, "/api/user", {"id": "1"}))
        assert out["finding_ids"]
        session = SessionLocal()
        try:
            row = session.query(Finding).filter(Finding.id == out["finding_ids"][0]).first()
            assert row is not None
            assert str(row.vulnerability_type) == "idor"
            assert str(row.status) == "open"
            notes = json.loads(str(row.notes or "{}"))
            assert notes["vulnerable_param"] == "id"
            assert "curl_command" in notes["poc"]
        finally:
            session.close()

    def test_probe_hits_full_path_not_root(self, fixture_base_url):
        """P0 regression: probe must request the endpoint path, never host-only."""
        engine = OffensiveEngine()
        out = engine.hunt_endpoint(_endpoint(fixture_base_url, "/api/user", {"id": "1"}))
        idor = [p for p in out["probed"] if p["vulnerability_type"] == "idor"]
        assert idor
        # Confirmation itself proves the path was hit (root has no /api/user?id= → 404).
        assert idor[0]["confirmed"]

    def test_auth_bypass_and_ssrf_paths_execute(self, fixture_base_url):
        pe = ProbeEngine()
        admin = Hypothesis(
            vulnerability_type="auth_bypass",
            endpoint="/admin",
            method="GET",
            confidence=0.5,
            parameters_of_interest=["role"],
        )
        res = pe.probe(admin, host=fixture_base_url, baseline_params={"role": "user"})
        assert res.error == ""
        assert res.confirmed
        assert res.test_response is not None and res.test_response.body_size > 50

        ssrf = Hypothesis(
            vulnerability_type="ssrf",
            endpoint="/fetch",
            method="GET",
            confidence=0.5,
            parameters_of_interest=["url"],
        )
        res2 = pe.probe(ssrf, host=fixture_base_url, baseline_params={"url": "https://example.com"})
        assert res2.error == ""
        assert res2.confirmed
        assert res2.detection_method == "error_pattern"
