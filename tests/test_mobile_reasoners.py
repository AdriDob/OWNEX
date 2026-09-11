"""Tests for mobile offensive reasoners — deep link, data exposure, transport.

Each reasoner analyzes server-visible API surface used by mobile clients.
Negative cases pin honest silence (no fabricated hypotheses).
"""

from __future__ import annotations

from cores.offensive.engine import OffensiveEngine
from cores.offensive.models import EndpointInfo
from cores.offensive.reasoners.deeplink import DeepLinkReasoner
from cores.offensive.reasoners.mobile_data import MobileDataExposureReasoner
from cores.offensive.reasoners.mobile_transport import MobileTransportReasoner


class TestDeepLinkReasoner:
    def test_detects_redirect_param(self):
        r = DeepLinkReasoner()
        ep = EndpointInfo(path="/api/auth/callback", method="GET", params={"redirect_url": "https://x.test"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].vulnerability_type == "deeplink_hijack"
        assert "redirect_url" in hyps[0].parameters_of_interest
        assert hyps[0].confidence >= 0.1

    def test_detects_auth_code_in_link(self):
        r = DeepLinkReasoner()
        ep = EndpointInfo(path="/oauth/authorize", method="GET", params={"auth_code": "abc", "scheme": "myapp"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].severity in ("high", "medium")

    def test_silent_on_plain_endpoint(self):
        r = DeepLinkReasoner()
        ep = EndpointInfo(path="/api/users", method="GET", params={"page": "1"})
        assert r.analyze(ep) == []

    def test_supported_methods(self):
        assert set(DeepLinkReasoner().supported_methods()) == {"GET", "POST"}


class TestMobileDataExposureReasoner:
    def test_detects_secret_in_query(self):
        r = MobileDataExposureReasoner()
        ep = EndpointInfo(path="/api/data", method="GET", params={"api_key": "secret123"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].vulnerability_type == "mobile_data_exposure"
        assert "api_key" in hyps[0].parameters_of_interest

    def test_detects_pii_in_get(self):
        r = MobileDataExposureReasoner()
        ep = EndpointInfo(path="/api/profile", method="GET", params={"ssn": "123"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].severity in ("high", "medium")

    def test_detects_backup_endpoint(self):
        r = MobileDataExposureReasoner()
        ep = EndpointInfo(path="/api/backup", method="GET", params={})
        hyps = r.analyze(ep)
        assert len(hyps) == 1

    def test_silent_on_clean_post(self):
        r = MobileDataExposureReasoner()
        ep = EndpointInfo(path="/api/users", method="POST", params={})
        assert r.analyze(ep) == []


class TestMobileTransportReasoner:
    def test_detects_plaintext_host(self):
        r = MobileTransportReasoner()
        ep = EndpointInfo(path="/api/login", method="POST", params={}, host="http://api.example.com")
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].vulnerability_type == "mobile_transport"
        assert hyps[0].severity in ("high", "medium")

    def test_detects_session_in_path(self):
        r = MobileTransportReasoner()
        ep = EndpointInfo(path="/api/session/abc123/data", method="GET", params={})
        hyps = r.analyze(ep)
        assert len(hyps) == 1

    def test_detects_token_in_query(self):
        r = MobileTransportReasoner()
        ep = EndpointInfo(path="/api/data", method="GET", params={"sessionid": "xyz"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1

    def test_silent_on_https_clean(self):
        r = MobileTransportReasoner()
        ep = EndpointInfo(path="/api/users", method="GET", params={"page": "1"}, host="https://api.example.com")
        assert r.analyze(ep) == []


class TestMobileReasonersWired:
    def test_engine_discovers_all_eight(self):
        engine = OffensiveEngine()
        types = {r.vulnerability_type for r in engine._reasoners}
        assert {"deeplink_hijack", "mobile_data_exposure", "mobile_transport"} <= types
        assert len(engine._reasoners) == 8

    def test_get_reasoner_by_type(self):
        engine = OffensiveEngine()
        assert engine.get_reasoner("deeplink_hijack") is not None
        assert engine.get_reasoner("mobile_data_exposure") is not None
        assert engine.get_reasoner("mobile_transport") is not None
        assert engine.get_reasoner("nonexistent") is None

    def test_feedback_loop_works(self):
        engine = OffensiveEngine()
        engine.record_outcome("deeplink_hijack", "hyp-1", True)
        stats = engine.get_reasoner_stats()["deeplink_hijack"]
        assert stats["total"] == 1
        assert stats["confirmed"] == 1

    def test_vuln_types_registered(self):
        from cores.validation.models import VulnType

        assert VulnType.DEEPLINK_HIJACK.value == "deeplink_hijack"
        assert VulnType.MOBILE_DATA_EXPOSURE.value == "mobile_data_exposure"
        assert VulnType.MOBILE_TRANSPORT.value == "mobile_transport"

    def test_economic_defaults_apply(self):
        from cores.validation.economic_scorer import BASE_ACCEPTANCE, VALIDATION_EFFORT_MINUTES, VULN_PAYOUT_MULTIPLIER
        from cores.validation.models import VulnType

        for vt in (VulnType.DEEPLINK_HIJACK, VulnType.MOBILE_DATA_EXPOSURE, VulnType.MOBILE_TRANSPORT):
            assert VULN_PAYOUT_MULTIPLIER.get(vt) is not None
            assert BASE_ACCEPTANCE.get(vt) is not None
            assert VALIDATION_EFFORT_MINUTES.get(vt) is not None
