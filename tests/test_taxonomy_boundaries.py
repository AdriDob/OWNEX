"""Phase 2 boundary tests: taxonomy mapper adoption at persistence boundaries.

- bounty_coordinator normalizes persisted engine categories to canonical
- opportunity_feedback API rejects unknown categories (fail-closed)
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cores.agents.bounty_coordinator import _normalize_category


class TestCoordinatorNormalization:
    def test_engine_value_maps_to_canonical(self) -> None:
        assert _normalize_category("testing_qa") == "qa_automation"

    def test_microtasks_collapses_into_annotation(self) -> None:
        assert _normalize_category("microtasks") == "data_annotation"

    def test_exact_family_stays_stable(self) -> None:
        assert _normalize_category("bug_bounty") == "bug_bounty"

    def test_unknown_string_passes_verbatim(self) -> None:
        # historical/garbage values are never invented nor dropped
        assert _normalize_category("legacy_garbage") == "legacy_garbage"

    def test_missing_defaults_to_legacy_oss(self) -> None:
        assert _normalize_category(None) == "oss"
        assert _normalize_category("") == "oss"


@pytest.fixture()
def feedback_client(monkeypatch):
    """TestClient with a fake feedback loop capturing record/multiplier calls."""
    from api.routers import opportunity_feedback as router_mod

    calls: dict[str, object] = {}

    class FakeLoop:
        def record_feedback(self, **kwargs):  # noqa: ANN003
            calls["record"] = kwargs
            return {"status": "ok"}

        def get_personalized_multipliers(self, **kwargs):  # noqa: ANN003
            calls["multipliers"] = kwargs
            return {"combined_multiplier": 1.0}

    monkeypatch.setattr(router_mod, "get_feedback_loop", lambda: FakeLoop())
    app = FastAPI()
    app.include_router(router_mod.router)
    return TestClient(app), calls


class TestFeedbackValidation:
    def test_record_rejects_unknown_category(self, feedback_client) -> None:
        client, _ = feedback_client
        resp = client.post(
            "/api/opportunity-feedback/record",
            json={
                "opportunity_id": "o1",
                "outcome": "accepted",
                "category": "not_a_real_category",
                "platform": "outlier",
            },
        )
        assert resp.status_code == 400
        assert "Invalid category" in resp.json()["detail"]

    def test_record_is_case_insensitive_and_normalizes(self, feedback_client) -> None:
        client, calls = feedback_client
        resp = client.post(
            "/api/opportunity-feedback/record",
            json={
                "opportunity_id": "o2",
                "outcome": "accepted",
                "category": "BUG_BOUNTY",
                "platform": "hackerone",
            },
        )
        assert resp.status_code == 200
        assert calls["record"]["category"] == "bug_bounty"

    def test_record_rejects_canonical_only_values(self, feedback_client) -> None:
        # qa_automation is canonical vocabulary, not engine taxonomy: fail-closed
        client, _ = feedback_client
        resp = client.post(
            "/api/opportunity-feedback/record",
            json={
                "opportunity_id": "o3",
                "outcome": "rejected",
                "category": "qa_automation",
                "platform": "x",
            },
        )
        assert resp.status_code == 400

    def test_multipliers_rejects_unknown(self, feedback_client) -> None:
        client, _ = feedback_client
        resp = client.post(
            "/api/opportunity-feedback/multipliers",
            json={"category": "bogus", "platform": "p"},
        )
        assert resp.status_code == 400

    def test_multipliers_delegates_normalized(self, feedback_client) -> None:
        client, calls = feedback_client
        resp = client.post(
            "/api/opportunity-feedback/multipliers",
            json={"category": "testing_qa", "platform": "p"},
        )
        assert resp.status_code == 200
        assert calls["multipliers"]["category"] == "testing_qa"
