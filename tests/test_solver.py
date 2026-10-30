"""Universal Solver tests — cualquier duda/problema/tarea → next_action con superficie."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from cores.solver.solver import assemble_context, classify_intent

client = TestClient(app)


def _auth() -> TestClient:
    r = client.post("/api/auth/login", json={"device_id": "solver-test"})
    token = r.json()["data"]["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    g = client.get("/api/system/pc-health")
    csrf = g.cookies.get("csrf-token")
    if csrf:
        client.headers.update({"X-CSRF-Token": csrf})
    return client


class TestClassify:
    def test_knowledge(self) -> None:
        assert classify_intent("cómo funciona el workbank") == "knowledge"

    def test_task_code(self) -> None:
        assert classify_intent("implementa un fix de XSS en el repo") == "task_code"

    def test_task_platform(self) -> None:
        assert classify_intent("quiero claim un bounty en algora") == "task_platform"

    def test_system_state(self) -> None:
        assert classify_intent("cuál es el estado de mis pagos") == "system_state"

    def test_planning(self) -> None:
        assert classify_intent("cómo llego a 50k para marzo 2027") == "planning"

    def test_unknown_to_question(self) -> None:
        assert classify_intent("hola") == "question"


class TestContext:
    def test_context_never_raises(self) -> None:
        ctx = assemble_context()
        assert "source" in ctx
        assert isinstance(ctx, dict)


class TestSolveEndpoint:
    def test_solve_returns_actionable(self) -> None:
        c = _auth()
        resp = c.post("/api/solve", json={"message": "cuál es el estado de mis ingresos"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "system_state"
        assert data["next_action"]["what"]
        assert data["surfaces"]
        assert data["needs_human_gate"] is False

    def test_code_task_needs_gate(self) -> None:
        c = _auth()
        resp = c.post("/api/solve", json={"message": "implementa un fix de bug en el repo"})
        assert resp.status_code == 200
        assert resp.json()["needs_human_gate"] is True

    def test_empty_message_400(self) -> None:
        c = _auth()
        resp = c.post("/api/solve", json={"message": "   "})
        assert resp.status_code == 400

    def test_economic_context_in_digest(self) -> None:
        c = _auth()
        resp = c.post("/api/solve", json={"message": "cómo llego a 50k para marzo 2027"})
        data = resp.json()
        assert data["intent"] == "planning"
        assert "march2027" in " ".join(data["surfaces"])
