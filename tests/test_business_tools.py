"""Tests for Free Business Tools Registry + API.

Determinista: la detección es pura (shutil.which / importlib.find_spec /
env-vault) y no ejecuta herramientas ni hace red. El estado real de cada
host puede variar; estos tests pinen el CONTRATO, no la instalación.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.business_tools import router
from cores.tools import business

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_task_catalog_has_canonical_tasks() -> None:
    tasks = business.task_catalog()
    ids = {t["id"] for t in tasks}
    assert ids >= {
        "catalog_fetch",
        "content_edit",
        "media_download",
        "stt",
        "tts",
        "llm_local",
        "lead_enrich",
        "automation_workflow",
        "data_cli",
        "oss_bounty",
        "docs_render",
        "security_signing",
        "db_cli",
    }
    for t in tasks:
        assert t["name"] and t["desc"]


def test_registry_every_tool_maps_to_task() -> None:
    tasks = {t["id"] for t in business.task_catalog()}
    for tool in business.REGISTRY:
        assert tool.task_id in tasks, tool.id
        assert tool.kind in ("binary", "module", "service")
        assert tool.install_hint and tool.license
    assert len(business.REGISTRY) >= 17


def test_inventory_shape_and_sort() -> None:
    rows = business.inventory()
    assert all({"id", "task_id", "kind", "license", "available", "install_hint"} <= set(r) for r in rows)
    # sorted by task order
    order = {tid: i for i, tid in enumerate(t for t in business.TASKS)}
    keys = [order[r["task_id"]] for r in rows]
    assert keys == sorted(keys)


def test_by_task_groups_all_tools() -> None:
    grouped = business.by_task()
    flat_total = sum(len(v) for v in grouped.values())
    assert flat_total == len(business.REGISTRY)
    for tid in business.TASKS:
        assert tid in grouped
        # cada tarea tiene al menos una herramienta gratis que la resuelve
        assert grouped[tid], f"task {tid} sin herramientas"


def test_availability_binary_pure(monkeypatch) -> None:
    monkeypatch.setattr(business.shutil, "which", lambda name: "/usr/bin/x" if name == "ffmpeg" else None)
    ff = business.find_tool("ffmpeg")
    assert ff is not None
    assert business._is_available(ff) == (True, "installed")
    git = business.find_tool("git")
    assert git is not None
    assert business._is_available(git)[0] is False


def test_availability_module_pure(monkeypatch) -> None:
    def _fake_spec(name):
        class _S:
            pass

        return _S() if name == "pandas" else None

    monkeypatch.setattr(business.importlib.util, "find_spec", _fake_spec)
    pd = business.find_tool("pandas")
    assert pd is not None
    assert business._is_available(pd)[0] is True
    pw = business.find_tool("playwright")
    assert pw is not None
    assert business._is_available(pw)[0] is False


def test_availability_service_env(monkeypatch) -> None:
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    monkeypatch.delenv("APOLLO_API_KEY", raising=False)
    hunter = business.find_tool("hunter_env")
    assert hunter is not None
    # enviroment vacío → missing; env presente → configured (valor jamás expuesto)
    assert business._is_available(hunter)[0] is False
    monkeypatch.setenv("HUNTER_API_KEY", "secret-value")
    ok, state = business._is_available(hunter)
    assert ok is True and state == "configured"
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)


def test_recommended_installs_only_missing() -> None:
    recs = business.recommended_installs()
    recommended_ids = {t["id"] for r in recs for t in r["missing"]}
    # las que están instaladas no se recomiendan
    avail_ids = {r["id"] for r in business.inventory() if r["available"]}
    assert not (recommended_ids & avail_ids)
    # Se agrupa por tarea
    for r in recs:
        assert r["missing"] and r["task"]


def test_summary_shape() -> None:
    s = business.summary()
    assert s["total_tools"] == len(business.REGISTRY)
    assert s["available"] + s["missing"] == s["total_tools"]
    assert set(s["by_kind"]) == {"binary", "module", "service"}


class TestBusinessToolsApi:
    def test_inventory_endpoint(self) -> None:
        r = client.get("/api/business-tools")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == len(business.REGISTRY)
        assert "summary" in body and "tools" in body

    def test_tasks_endpoint_coverage(self) -> None:
        r = client.get("/api/business-tools/tasks")
        assert r.status_code == 200
        tasks = r.json()["tasks"]
        assert len(tasks) == len(business.TASKS)
        for t in tasks:
            assert t["tools_count"] > 0
            assert t["available_count"] <= t["tools_count"]

    def test_installs_endpoint(self) -> None:
        r = client.get("/api/business-tools/installs")
        assert r.status_code == 200
        assert "recommendations" in r.json()


def test_service_key_never_leaked(tmp_path, monkeypatch) -> None:
    """Un service configurado aparece solo como 'configured', jamás con la key."""
    monkeypatch.setenv("HUNTER_API_KEY", "sk-ultra-secreto-123")
    rows = business.inventory()
    hunter = next(r for r in rows if r["id"] == "hunter_env")
    assert hunter["state"] == "configured"
    assert "sk-ultra-secreto-123" not in str(rows)
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
