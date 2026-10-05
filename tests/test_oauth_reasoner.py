"""Tests for the OAuth/SSO reasoner.

Positives pin detection (redirect/token/state/PKCE), negatives pin honest
silence, plus wiring (engine count, VulnType, scorer, feedback).
"""

from __future__ import annotations

from cores.offensive.engine import OffensiveEngine
from cores.offensive.models import EndpointInfo
from cores.offensive.reasoners.oauth import OAuthReasoner


class TestOAuthReasoner:
    def test_detects_authorize_with_redirect(self):
        r = OAuthReasoner()
        ep = EndpointInfo(
            path="/oauth/authorize",
            method="GET",
            params={"client_id": "abc", "redirect_uri": "https://app.test/cb", "state": "xyz"},
        )
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].vulnerability_type == "oauth"
        assert "redirect_uri" in hyps[0].parameters_of_interest
        assert hyps[0].confidence >= 0.1

    def test_token_in_url_is_high(self):
        r = OAuthReasoner()
        ep = EndpointInfo(
            path="/oauth/callback",
            method="GET",
            params={"code": "abc123", "state": "xyz"},
        )
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].severity == "high"

    def test_missing_state_and_pkce_flagged(self):
        r = OAuthReasoner()
        ep = EndpointInfo(path="/login/oauth", method="GET", params={"code": "x", "client_id": "y"})
        text = " ".join(r.analyze(ep)[0].signals)
        assert "PKCE" in text or "state" in text

    def test_scope_note_own_accounts_only(self):
        r = OAuthReasoner()
        ep = EndpointInfo(path="/oauth/authorize", method="GET", params={"redirect_uri": "x"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert "own test accounts" in " ".join(hyps[0].test_instructions)
        assert hyps[0].alternative_explanations

    def test_silent_on_plain_endpoint(self):
        r = OAuthReasoner()
        ep = EndpointInfo(path="/api/users", method="GET", params={"page": "1"})
        assert r.analyze(ep) == []

    def test_ignores_unsafe_methods(self):
        r = OAuthReasoner()
        ep = EndpointInfo(path="/oauth/authorize", method="DELETE", params={"redirect_uri": "x"})
        assert r.analyze(ep) == []

    def test_supported_methods(self):
        assert set(OAuthReasoner().supported_methods()) == {"GET", "POST"}


class TestOAuthWiring:
    def test_engine_registers_thirteen(self):
        engine = OffensiveEngine()
        assert len(engine._reasoners) == 21
        assert engine.get_reasoner("oauth") is not None

    def test_vuln_type_exists(self):
        from cores.validation.models import VulnType

        assert VulnType.OAUTH.value == "oauth"

    def test_scorer_defaults(self):
        from cores.validation.economic_scorer import (
            BASE_ACCEPTANCE,
            VALIDATION_EFFORT_MINUTES,
            VULN_PAYOUT_MULTIPLIER,
        )
        from cores.validation.models import VulnType

        assert VULN_PAYOUT_MULTIPLIER.get(VulnType.OAUTH) == 1.5
        assert BASE_ACCEPTANCE.get(VulnType.OAUTH) == 0.50
        assert VALIDATION_EFFORT_MINUTES.get(VulnType.OAUTH) == 10.0

    def test_feedback_loop(self):
        engine = OffensiveEngine()
        engine.record_outcome("oauth", "hyp-001", True)  # must not crash
        assert "oauth" in engine.get_reasoner_stats()

    def test_end_to_end_oauth_endpoint(self):
        engine = OffensiveEngine()
        result = engine.analyze_endpoint(
            {
                "path": "/oauth/authorize",
                "method": "GET",
                "params": {"client_id": "c", "redirect_uri": "https://app.test/cb"},
            },
        )
        types = [h.vulnerability_type for h in result.hypotheses]
        assert "oauth" in types
