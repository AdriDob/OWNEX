"""Tests para el perfil kit: generación de textos listos para copiar por plataforma."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from cores.direct_work_engine import profile_kit as core

PLATFORMS = [
    "fiverr",
    "github",
    "hackerone",
    "bugcrowd",
    "intigriti",
    "yeswehack",
    "opire",
    "issuehunt",
    "algora",
    "outlier",
    "mindrift",
    "linkedin",
]


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(core, "_DATA_DIR", tmp_path / "profile_kit.json")
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"device_id": "pytest-profile-kit"})
    if resp.status_code == 200 and "token" in resp.json().get("data", {}):
        client.headers.update({"Authorization": f"Bearer {resp.json()['data']['token']}"})
    csrf = resp.cookies.get("csrf-token")
    if csrf:
        client.headers.update({"X-CSRF-Token": csrf})
    return client


SAMPLE_PROFILE = {
    "name": "Adriel",
    "country": "Argentina",
    "skills": ["Python", "Go", "TypeScript"],
    "languages": ["es", "en"],
    "experience_level": "mid",
    "availability_hours": 40,
    "github_url": "https://github.com/adriel",
    "linkedin_url": "https://linkedin.com/in/adriel",
    "portfolio_url": "https://adriel.dev",
    "projects": ["recon-automation", "api-scanner"],
}


class TestProfileKitApi:
    def test_status_endpoint_shape(self, client: TestClient) -> None:
        resp = client.get("/api/profile-kit/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is False
        assert data["available_platforms"] == PLATFORMS
        assert "profile" in data

    def test_save_endpoint_persists(self, client: TestClient) -> None:
        resp = client.post("/api/profile-kit/", json=SAMPLE_PROFILE)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["saved"]["name"] == "Adriel"
        status = client.get("/api/profile-kit/").json()
        assert status["saved"] is True
        assert status["profile"]["name"] == "Adriel"
        assert "Python" in status["profile"]["skills"]

    def test_generate_endpoint_returns_all_langs(self, client: TestClient) -> None:
        resp = client.post("/api/profile-kit/generate", json=SAMPLE_PROFILE)
        assert resp.status_code == 200
        kits = resp.json()["kits"]
        assert set(kits.keys()) == {"es", "en"}

    def test_generate_endpoint_returns_all_platforms(self, client: TestClient) -> None:
        resp = client.post("/api/profile-kit/generate", json=SAMPLE_PROFILE)
        assert resp.status_code == 200
        kits = resp.json()["kits"]
        for lang in ("es", "en"):
            assert set(kits[lang].keys()) == set(PLATFORMS)

    def test_generate_fields_shape(self, client: TestClient) -> None:
        resp = client.post("/api/profile-kit/generate", json=SAMPLE_PROFILE)
        fields = resp.json()["kits"]["en"]["fiverr"]
        assert len(fields) >= 4
        for field in fields:
            assert {"key", "label", "text"}.issubset(set(field.keys()))
            assert isinstance(field["text"], str) and field["text"]

    def test_bug_bounty_platforms_use_specific_generators(self, client: TestClient) -> None:
        resp = client.post("/api/profile-kit/generate", json=SAMPLE_PROFILE)
        fields = resp.json()["kits"]["en"]["hackerone"]
        keys = [f["key"] for f in fields]
        assert "hackerone_bio" in keys
        assert "hackerone_specialty" in keys
        assert "hackerone_languages" in keys
        assert "hackerone_availability" in keys
        bio = next(f for f in fields if f["key"] == "hackerone_bio")
        assert "Python" in bio["text"] or "Go" in bio["text"]

    def test_not_invented_data(self, client: TestClient) -> None:
        resp = client.post("/api/profile-kit/generate", json={"country": "Chile"})
        fields = resp.json()["kits"]["es"]["github"]
        texts = " ".join(f["text"] for f in fields)
        assert "Chile" in texts
        assert "Adriel" not in texts

    def test_empty_profile_uses_defaults(self, client: TestClient) -> None:
        resp = client.post("/api/profile-kit/generate", json={})
        assert resp.status_code == 200
        fields = resp.json()["kits"]["es"]["fiverr"]
        title = next(f for f in fields if f["key"] == "fiverr_title")
        assert "Full-stack" in title["text"]

    def test_generate_uses_saved_when_no_payload(self, client: TestClient) -> None:
        client.post("/api/profile-kit/", json=SAMPLE_PROFILE)
        resp = client.post("/api/profile-kit/generate")
        assert resp.status_code == 200
        fields = resp.json()["kits"]["es"]["github"]
        texts = " ".join(f["text"] for f in fields)
        assert "Adriel" in texts


class TestProfileKitEngine:
    def test_api_generates_match_engine(self) -> None:
        engine = core.ProfileKitEngine()
        profile = core.ProfileKitEngine.profile_from_dict(SAMPLE_PROFILE)
        engine_kits = engine.generate(profile)
        assert "en" in engine_kits and "hackerone" in engine_kits["en"]

    def test_engine_persists_roundtrip(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(core, "_DATA_DIR", tmp_path / "profile_kit.json")
        engine = core.ProfileKitEngine()
        assert engine.data_path == tmp_path / "profile_kit.json"
        payload = {"name": "Adriel", "skills": ["Python"]}
        saved = engine.save(payload)
        assert saved["name"] == "Adriel"
        engine2 = core.ProfileKitEngine()
        assert engine2.load() == payload

    def test_profile_from_dict_partial(self) -> None:
        profile = core.ProfileKitEngine.profile_from_dict({"country": "Chile", "skills": ["Python"]})
        assert profile.country == "Chile"
        assert profile.skills == {"Python"}
        assert profile.name == ""
        assert profile.experience_level.value == "none"
