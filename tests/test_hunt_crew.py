"""Tests Sprint 1 Hunt Crew — asignación validada + métricas por agente.

Todo offline: HuntCrew acepta paths inyectados; el loop vivo jamás se toca.
"""

from __future__ import annotations

from pathlib import Path


def _crew(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    import cores.hunt.crew as crew_mod

    monkeypatch.setattr(crew_mod, "_store", None)
    return crew_mod.get_hunt_crew()


class TestAgents:
    def test_create_y_duplicado(self, tmp_path, monkeypatch):
        crew = _crew(tmp_path, monkeypatch)
        assert crew.create_agent("a1", name="Caza Alpha", mode="deep")["ok"] is True
        assert crew.create_agent("a1")["ok"] is False
        assert crew.create_agent("")["ok"] is False
        assert crew.create_agent("ax", mode="nope")["ok"] is False

    def test_remove(self, tmp_path, monkeypatch):
        crew = _crew(tmp_path, monkeypatch)
        crew.create_agent("a1")
        assert crew.remove_agent("a1")["ok"] is True
        assert crew.remove_agent("a1")["ok"] is False

    def test_persiste_entre_instancias(self, tmp_path, monkeypatch):
        import cores.hunt.crew as crew_mod

        crew = _crew(tmp_path, monkeypatch)
        crew.create_agent("a1")
        crew.assign("a1", "example.com")
        crew2 = crew_mod.HuntCrew()
        assert [a["agent_id"] for a in crew2.list_agents()] == ["a1"]
        assert crew2.list_agents()[0]["targets"] == ["example.com"]

    def test_store_corrupto_no_raisea(self, tmp_path, monkeypatch):
        import cores.hunt.crew as crew_mod

        (tmp_path / "hunt_crew.json").write_text("{no-json", encoding="utf-8")
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(crew_mod, "_store", None)
        assert crew_mod.get_hunt_crew().list_agents() == []


class TestAssign:
    def test_valida_dns_cupo_y_duplicados(self, tmp_path, monkeypatch):
        crew = _crew(tmp_path, monkeypatch)
        crew.create_agent("a1", max_targets=1)
        crew.create_agent("a2")
        assert crew.assign("nope", "example.com")["ok"] is False
        assert crew.assign("a1", "")["ok"] is False
        assert crew.assign("a1", "bad_host.com")["ok"] is False
        assert crew.assign("a1", "example.com")["ok"] is True
        assert crew.assign("a1", "example.com")["ok"] is False  # duplicado propio
        assert crew.assign("a2", "example.com")["ok"] is False  # lo cubre otro
        assert crew.assign("a1", "other.com")["ok"] is False  # cupo lleno

    def test_unassign(self, tmp_path, monkeypatch):
        crew = _crew(tmp_path, monkeypatch)
        crew.create_agent("a1")
        assert crew.unassign("a1", "x.test")["ok"] is False
        crew.assign("a1", "example.com")
        assert crew.unassign("a1", "example.com")["ok"] is True
        assert crew.unassign("nope", "example.com")["ok"] is False


class TestStats:
    def test_vacio_honesto_y_acumulado(self, tmp_path, monkeypatch):
        crew = _crew(tmp_path, monkeypatch)
        crew.create_agent("a1")
        assert crew.agent_stats("a1") == {
            "agent_id": "a1",
            "scans": 0,
            "findings": 0,
            "confirmed": 0,
            "targets": [],
        }
        crew.assign("a1", "example.com")
        crew.record_scan("a1", "example.com", findings_found=3, confirmed=1)
        crew.record_scan("a1", "example.com", findings_found=2)
        stats = crew.agent_stats("a1")
        assert (stats["scans"], stats["findings"], stats["confirmed"]) == (2, 5, 1)
        assert stats["targets"] == ["example.com"]

    def test_record_negativos_se_clampean(self, tmp_path, monkeypatch):
        crew = _crew(tmp_path, monkeypatch)
        assert crew.record_scan("a1", "x", findings_found=-5)["ok"] is True
        assert crew.agent_stats("a1")["findings"] == 0


class TestEndpoints:
    def _client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.hunt import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_crew_status_200(self, tmp_path, monkeypatch):
        _crew(tmp_path, monkeypatch)
        r = self._client().get("/api/hunt/crew")
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_create_y_assign_200_422(self, tmp_path, monkeypatch):
        _crew(tmp_path, monkeypatch)
        c = self._client()
        assert c.post("/api/hunt/crew/agents", json={"agent_id": "a1", "mode": "FAST"}).status_code == 200
        assert c.post("/api/hunt/crew/agents", json={"agent_id": "a1"}).status_code == 422
        assert c.post("/api/hunt/crew/agents", json={"agent_id": "", "mode": "FAST"}).status_code == 422
        assert c.post("/api/hunt/crew/assign", json={"agent_id": "a1", "target": "example.com"}).status_code == 200
        assert c.post("/api/hunt/crew/assign", json={"agent_id": "a1", "target": "bad_host.com"}).status_code == 422
