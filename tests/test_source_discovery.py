from __future__ import annotations

import json
from datetime import datetime, timedelta

import httpx
import pytest

from core.opportunity.source_discovery import (
    SourceDiscoveryRegistry,
    SourceLifecycle,
    SourceProfile,
    UniversalSourceAdapter,
    discover_github_bounty_issues,
    discover_github_repositories,
)


@pytest.fixture
def public_hosts(monkeypatch):
    monkeypatch.setattr("core.opportunity.source_discovery._validate_public_url", lambda url: url.rstrip("/"))


def _transport(documents: dict[str, tuple[int, str, str]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        status, content_type, content = documents.get(request.url.path, (404, "text/plain", "missing"))
        return httpx.Response(status, headers={"content-type": content_type}, content=content.encode(), request=request)

    return httpx.MockTransport(handler)


def test_probe_openapi_builds_read_only_descriptor(public_hosts):
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "Bounties", "version": "v1"},
        "paths": {"/tasks": {"get": {}, "post": {}}},
        "components": {"securitySchemes": {"Bearer": {}}},
    }
    adapter = UniversalSourceAdapter(transport=_transport({"/openapi.json": (200, "application/json", json.dumps(spec))}))

    profile = adapter.probe("https://source.example")
    descriptor = adapter.generate_adapter(profile)

    assert profile.adapter_type == "openapi"
    assert profile.title == "Bounties"
    assert profile.endpoints == [{"method": "GET", "path": "/tasks"}, {"method": "POST", "path": "/tasks"}]
    assert descriptor["executable"] is False
    assert descriptor["task_schema_verified"] is False


@pytest.mark.parametrize(
    ("path", "content", "kind"),
    [
        ("/skill.md", "# Skill\nGET /api/tasks", "skill_md"),
        ("/ai-catalog.json", json.dumps({"name": "Agent", "tools": [{"name": "list_tasks"}]}), "ai_catalog"),
        ("/.well-known/agent.json", json.dumps({"name": "Agent Card", "capabilities": ["tasks"]}), "a2a"),
        ("/llms.txt", "# API\n- [Tasks](/api/tasks)", "llms_txt"),
    ],
)
def test_probe_falls_through_to_supported_metadata(public_hosts, path, content, kind):
    adapter = UniversalSourceAdapter(transport=_transport({path: (200, "application/json", content)}))

    profile = adapter.probe("https://source.example")

    assert profile.adapter_type == kind
    assert profile.document_url.endswith(path)


def test_probe_rejects_malformed_openapi_and_continues(public_hosts):
    adapter = UniversalSourceAdapter(
        transport=_transport({"/openapi.json": (200, "application/json", "[]"), "/skill.md": (200, "text/markdown", "# API\nPOST /tasks")})
    )

    profile = adapter.probe("https://source.example")

    assert profile.adapter_type == "skill_md"


def test_probe_rejects_unrecognized_json_manifests(public_hosts):
    adapter = UniversalSourceAdapter(transport=_transport({"/ai-catalog.json": (200, "application/json", json.dumps({"random": "data"}))}))

    profile = adapter.probe("https://source.example")

    assert profile.adapter_type == "unknown"


def test_probe_does_not_follow_redirects(public_hosts):
    adapter = UniversalSourceAdapter(transport=_transport({"/openapi.json": (302, "text/plain", "redirect")}))

    profile = adapter.probe("https://source.example")

    assert profile.adapter_type == "unknown"
    assert any(row["result"] == "http_302" for row in profile.evidence)


def test_probe_rejects_local_and_non_https_urls():
    adapter = UniversalSourceAdapter(transport=_transport({}))
    for url in ("http://public.example", "https://localhost", "https://127.0.0.1", "https://user:pass@example.com"):
        with pytest.raises(ValueError):
            adapter.probe(url)


def test_normalize_does_not_infer_reward_or_eligibility():
    profile = SourceProfile(source_url="https://source.example", adapter_type="openapi")

    normalized = UniversalSourceAdapter.normalize(
        {"id": "42", "title": "Fix parser", "description": "Issue body", "reward": 900}, source_id="abc", profile=profile
    )

    assert normalized["id"] == "abc:42"
    assert normalized["reward"] is None
    assert normalized["reward_reported"] == 900
    assert normalized["reward_status"] == "REPORTED"
    assert normalized["eligibility"] == "PENDING"


def test_normalize_requires_explicit_task_fields():
    with pytest.raises(ValueError):
        UniversalSourceAdapter.normalize({"title": "No description"}, source_id="x", profile=SourceProfile("https://a"))


def test_registry_probe_verification_and_activation_require_human_evidence(tmp_path, public_hosts):
    path = tmp_path / "candidates.json"
    registry = SourceDiscoveryRegistry(path)
    candidate = registry.add("Work source", "https://source.example", "fixture")
    profile = SourceProfile(source_url=candidate.source_url, adapter_type="openapi")
    registry.set_profile(candidate.id, profile)

    with pytest.raises(ValueError):
        registry.activate(candidate.id, approval_note="approve")
    with pytest.raises(ValueError):
        registry.mark_verified(candidate.id, {"honeypot_pass": "fixture"})

    registry.mark_verified(candidate.id, {"honeypot_pass": "review:1", "funding_verified": "escrow:2", "eligibility_verified": "terms:3"})
    with pytest.raises(ValueError):
        registry.activate(candidate.id, approval_note=" ")
    active = registry.activate(candidate.id, approval_note="operator approved for evaluation")
    reloaded = SourceDiscoveryRegistry(path).get(candidate.id)

    assert active.lifecycle == SourceLifecycle.ACTIVE
    assert reloaded is not None and reloaded.lifecycle == SourceLifecycle.ACTIVE
    assert reloaded.verification_evidence[-1].startswith("human_approval:")


def test_lifecycle_decay_and_deactivation_use_last_payout(tmp_path, public_hosts):
    registry = SourceDiscoveryRegistry(tmp_path / "candidates.json")
    item = registry.add("Work source", "https://source.example", "fixture")
    registry.set_profile(item.id, SourceProfile(item.source_url, adapter_type="openapi"))
    registry.mark_verified(item.id, {"honeypot_pass": "review", "funding_verified": "escrow", "eligibility_verified": "terms"})
    active = registry.activate(item.id, approval_note="approved")
    anchor = datetime.fromisoformat(active.activated_at)

    decayed = registry.refresh_lifecycle(now=anchor + timedelta(days=7))
    assert decayed[0].lifecycle == SourceLifecycle.DECAY
    deactivated = registry.refresh_lifecycle(now=anchor + timedelta(days=30))
    assert deactivated[0].lifecycle == SourceLifecycle.DEACTIVATED


def test_verified_payout_evidence_reactivates_source(tmp_path, public_hosts):
    registry = SourceDiscoveryRegistry(tmp_path / "candidates.json")
    item = registry.add("Work source", "https://source.example", "fixture")
    registry.set_profile(item.id, SourceProfile(item.source_url, adapter_type="openapi"))
    registry.mark_verified(item.id, {"honeypot_pass": "review", "funding_verified": "escrow", "eligibility_verified": "terms"})
    active = registry.activate(item.id, approval_note="approved")
    registry.refresh_lifecycle(now=datetime.fromisoformat(active.activated_at) + timedelta(days=31))

    with pytest.raises(ValueError):
        registry.record_confirmed_payout(item.id, evidence_reference="unverified")
    reactivated = registry.record_confirmed_payout(item.id, evidence_reference="tx:0x123")

    assert reactivated.lifecycle == SourceLifecycle.ACTIVE
    assert reactivated.last_payout_at is not None


def test_github_discovery_deduplicates_and_skips_archived_and_forks(tmp_path, public_hosts):
    registry = SourceDiscoveryRegistry(tmp_path / "candidates.json")
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        payload = {
            "items": [
                {
                    "full_name": "org/project",
                    "html_url": "https://github.com/org/project",
                    "archived": False,
                    "fork": False,
                    "description": "AI data annotation platform paying via USDC and Payoneer to Argentine contributors",
                },
                {"full_name": "org/archived", "html_url": "https://github.com/org/archived", "archived": True, "fork": False},
                {"full_name": "org/fork", "html_url": "https://github.com/org/fork", "archived": False, "fork": True},
            ]
        }
        return httpx.Response(200, json=payload, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover_github_repositories(registry=registry, client=client)
        second = discover_github_repositories(registry=registry, client=client)

    assert calls["n"] == result["http_requests"]
    assert second["http_requests"] == 0
    assert second["cache_hits"] == result["http_requests"]
    assert result["new_candidates"] == 1
    assert second["new_candidates"] == 0
    assert len(registry.list()) == 1
    assert result["activation_requires_human"] is True


def test_github_issue_search_registers_opportunities_and_skips_prs(tmp_path, public_hosts):
    registry = SourceDiscoveryRegistry(tmp_path / "candidates.json")
    auth_headers: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        auth_headers.append(request.headers.get("authorization"))
        return httpx.Response(
            200,
            json={
                "items": [
                    {"title": "Paid fix", "html_url": "https://github.com/org/repo/issues/1", "labels": [{"name": "bounty $100"}], "body": ""},
                    {
                        "title": "PR with reward label",
                        "html_url": "https://github.com/org/repo/pull/2",
                        "pull_request": {"url": "https://api.github.com/x"},
                        "labels": [{"name": "bounty $999"}],
                    },
                    {"title": "Unknown reward", "html_url": "https://github.com/org/repo/issues/3", "labels": [{"name": "bug"}], "body": "Needs investigation"},
                ]
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover_github_bounty_issues(registry=registry, client=client, github_token="tok", min_interval_seconds=0)
        second = discover_github_bounty_issues(registry=registry, client=client, github_token="tok", min_interval_seconds=0)

    candidates = {candidate.source_url: candidate for candidate in registry.list()}
    paid = candidates["https://github.com/org/repo/issues/1"]
    unknown = candidates["https://github.com/org/repo/issues/3"]

    assert result["http_requests"] == 5
    assert result["new_opportunities"] == 2
    assert result["reward_reported"] == 1
    assert result["reward_verification_required"] is True
    assert second["http_requests"] == 0
    assert second["cache_hits"] == 5
    assert auth_headers == ["Bearer tok"] * 5
    assert paid.record_type == "opportunity"
    assert paid.profile["reward_reported"] == 100.0
    assert paid.profile["reward_currency"] == "USD"
    assert paid.profile["reward_status"] == "REPORTED"
    assert unknown.profile["reward_reported"] is None
    assert unknown.profile["reward_status"] == "UNKNOWN"
    assert "https://github.com/org/repo/pull/2" not in candidates


def test_github_issue_search_retries_retryable_status_without_long_sleep(tmp_path, public_hosts):
    registry = SourceDiscoveryRegistry(tmp_path / "candidates.json")
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0"}, json={"message": "rate limited"}, request=request)
        return httpx.Response(200, json={"items": []}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover_github_bounty_issues(registry=registry, client=client, min_interval_seconds=0)

    assert result["errors"] == []
    assert result["http_requests"] == calls["n"] == 6


def test_github_bounty_reward_details_require_context_and_preserve_currency():
    from core.opportunity.source_discovery import _extract_github_bounty_reward_details

    assert _extract_github_bounty_reward_details({"labels": [{"name": "bounty $75"}]}) == (75.0, "USD")
    assert _extract_github_bounty_reward_details({"labels": [{"name": "bounty-100-usdc"}]}) == (100.0, "USDC")
    assert _extract_github_bounty_reward_details({"title": "Task", "body": "Reward: 100 USDC for the fix"}) == (100.0, "USDC")
    assert _extract_github_bounty_reward_details({"title": "Task", "body": "This costs $5 to run tests"}) == (None, None)
    assert _extract_github_bounty_reward_details({"title": "Bounty: parser edge case", "body": "Pay $5"}) == (5.0, "USD")


def test_scheduler_registers_daily_discovery_job():
    from core.scheduler.jobs import get_all_jobs

    jobs = [job for group in get_all_jobs().values() for job in group]
    job = next(item for item in jobs if item.job_id == "meta_source_discovery_daily")

    assert job.trigger == "cron"
    assert job.handler == "core.opportunity.discovery_to_workbank:run_daily_meta_discovery_and_integrate"


def test_source_discovery_api_routes_are_mounted():
    from api.main import app

    paths = app.openapi()["paths"]

    assert "/api/discovery/sources/candidates" in paths
    assert "/api/discovery/sources/discover" in paths
    assert "/api/discovery/sources/{source_id}/probe" in paths
    assert "/api/discovery/sources/{source_id}/verify" in paths
    assert "/api/discovery/sources/{source_id}/activate" in paths
