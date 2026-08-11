"""Tests for cores/scope_enforcement — capa unificada de cumplimiento de alcance."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cores.scope_enforcement import (
    AssetType,
    ProgramScopePolicy,
    ScopeDecision,
    ScopeEnforcer,
    ScopeRule,
    ScopeViolationError,
)

WILDCARD_SCOPE = ProgramScopePolicy(
    program_id="h1-1",
    program_name="Test Program",
    platform="hackerone",
    rules=[
        ScopeRule(asset_type=AssetType.WILDCARD, pattern="*.example.com", is_in_scope=True),
        ScopeRule(asset_type=AssetType.DOMAIN, pattern=r"example\.com", is_in_scope=True),
        ScopeRule(asset_type=AssetType.DOMAIN, pattern=r"sub\.example\.com", is_in_scope=False),
        ScopeRule(asset_type=AssetType.URL, pattern=r"api\.example\.com", is_in_scope=True),
        ScopeRule(asset_type=AssetType.API_ENDPOINT, pattern=r"/internal/admin", is_in_scope=False),
        ScopeRule(asset_type=AssetType.IP, pattern=r"10\.0\.0\.[0-9]+", is_in_scope=True),
    ],
)


def make_enforcer(policy: ProgramScopePolicy | None = None) -> ScopeEnforcer:
    enforcer = ScopeEnforcer(event_bus=MagicMock())
    if policy:
        enforcer.register_policy(policy)
    return enforcer


class TestScopeDecision:
    def test_in_scope_wildcard(self) -> None:
        assert WILDCARD_SCOPE.is_endpoint_in_scope("https://app.example.com/x") == ScopeDecision.IN_SCOPE

    def test_in_scope_exact_domain(self) -> None:
        assert WILDCARD_SCOPE.is_endpoint_in_scope("https://example.com") == ScopeDecision.IN_SCOPE

    def test_out_of_scope_excluded_subdomain(self) -> None:
        assert WILDCARD_SCOPE.is_endpoint_in_scope("https://sub.example.com") == ScopeDecision.OUT_OF_SCOPE

    def test_out_of_scope_excluded_path(self) -> None:
        assert (
            WILDCARD_SCOPE.is_endpoint_in_scope("https://app.example.com/internal/admin") == ScopeDecision.OUT_OF_SCOPE
        )

    def test_unknown_domain(self) -> None:
        assert WILDCARD_SCOPE.is_endpoint_in_scope("https://otherdomain.com") == ScopeDecision.UNKNOWN

    def test_api_endpoint_in_scope(self) -> None:
        assert WILDCARD_SCOPE.is_endpoint_in_scope("https://api.example.com/v1/data") == ScopeDecision.IN_SCOPE

    def test_ip_in_scope(self) -> None:
        assert WILDCARD_SCOPE.is_endpoint_in_scope("https://10.0.0.5/") == ScopeDecision.IN_SCOPE


class TestEnforcer:
    def test_unknown_program_returns_unknown(self) -> None:
        enforcer = make_enforcer()
        assert enforcer.check_endpoint("nope", "https://example.com") == ScopeDecision.UNKNOWN

    def test_enforce_in_scope_passes(self) -> None:
        enforcer = make_enforcer(WILDCARD_SCOPE)
        enforcer.enforce_endpoint("h1-1", "https://app.example.com/")  # should not raise

    def test_enforce_out_of_scope_raises(self) -> None:
        enforcer = make_enforcer(WILDCARD_SCOPE)
        with pytest.raises(ScopeViolationError):
            enforcer.enforce_endpoint("h1-1", "https://sub.example.com/")

    def test_enforce_asset_raises(self) -> None:
        enforcer = make_enforcer(WILDCARD_SCOPE)
        with pytest.raises(ScopeViolationError):
            enforcer.enforce_asset("h1-1", AssetType.DOMAIN, "sub.example.com")

    def test_event_emitted_on_check(self) -> None:
        bus = MagicMock()
        policy = WILDCARD_SCOPE
        enforcer = ScopeEnforcer(event_bus=bus)
        enforcer.register_policy(policy)
        enforcer.check_endpoint("h1-1", "https://app.example.com/")
        bus.publish.assert_called_once()
        args = bus.publish.call_args
        assert args[0][0] == "scope.check"

    def test_get_policy(self) -> None:
        enforcer = make_enforcer(WILDCARD_SCOPE)
        assert enforcer.get_policy("h1-1") is WILDCARD_SCOPE
        assert enforcer.get_policy("other") is None

    def test_singleton(self) -> None:
        from cores.scope_enforcement import get_scope_enforcer

        assert get_scope_enforcer() is get_scope_enforcer()


class TestPlatformParsers:
    def test_hackerone_parse(self) -> None:
        data = {
            "id": 10,
            "name": "H1 Program",
            "structured_scope": [
                {"asset_type": "URL", "asset_identifier": "app.example.com", "eligible_for_submission": True},
                {
                    "asset_type": "DOMAIN",
                    "asset_identifier": "forbidden.example.com",
                    "eligible_for_submission": False,
                },
            ],
        }
        policy = ScopeEnforcer.parse_from_platform("hackerone", data)
        assert policy.platform == "hackerone"
        assert len(policy.rules) == 2
        assert policy.rules[0].is_in_scope is True
        assert policy.rules[1].is_in_scope is False

    def test_bugcrowd_parse(self) -> None:
        data = {
            "id": 20,
            "name": "BC Program",
            "targets": [
                {"category": "website", "name": "example.com", "in_scope": True},
                {"category": "api", "name": "api.example.com", "in_scope": False},
            ],
        }
        policy = ScopeEnforcer.parse_from_platform("bugcrowd", data)
        assert len(policy.rules) == 2
        assert policy.rules[0].is_in_scope is True

    def test_intigriti_parse(self) -> None:
        data = {
            "id": 30,
            "name": "Intigriti Program",
            "scope": [
                {"type": "wildcard", "endpoint": "*.example.com", "in_scope": True},
                {"type": "url", "endpoint": "old.example.com", "in_scope": False},
            ],
        }
        policy = ScopeEnforcer.parse_from_platform("intigriti", data)
        assert len(policy.rules) == 2
        assert policy.rules[0].asset_type == AssetType.WILDCARD

    def test_unknown_platform_raises(self) -> None:
        with pytest.raises(ValueError):
            ScopeEnforcer.parse_from_platform("unknown", {})
