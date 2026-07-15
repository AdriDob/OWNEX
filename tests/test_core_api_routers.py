"""Tests for core/api/routers.py — extension, secrets, health endpoints."""

from __future__ import annotations

# Build a minimal FastAPI app with just the core router
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.api.routers import router as core_router
from core.health.engine import get_health_center

app = FastAPI()
app.include_router(core_router)
client = TestClient(app)


class TestExtensionEndpoints:
    def test_list_extensions(self):
        resp = client.get("/api/core/extensions")
        assert resp.status_code == 200
        data = resp.json()
        # Should be a dict of extension_id -> status
        assert isinstance(data, dict)

    def test_list_hooks(self):
        resp = client.get("/api/core/hooks")
        assert resp.status_code == 200
        data = resp.json()
        assert "hooks" in data
        assert len(data["hooks"]) > 0

    def test_list_capabilities(self):
        resp = client.get("/api/core/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert "capabilities" in data


class TestSecretsEndpoints:
    def test_list_secrets(self):
        resp = client.get("/api/core/secrets")
        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data

    def test_get_nonexistent_secret(self):
        resp = client.get("/api/core/secrets/NONEXISTENT_TEST_KEY")
        assert resp.status_code == 404

    def test_set_and_get_secret(self):
        resp = client.put(
            "/api/core/secrets/TEST_API_KEY",
            json={"value": "test-value-123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stored"] is True

        resp = client.get("/api/core/secrets/TEST_API_KEY")
        assert resp.status_code == 200
        data = resp.json()
        assert data["value"] == "test-value-123"

        # Cleanup
        client.delete("/api/core/secrets/TEST_API_KEY")

    def test_delete_secret(self):
        client.put("/api/core/secrets/TEST_DELETE", json={"value": "delete-me"})
        resp = client.delete("/api/core/secrets/TEST_DELETE")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True

    def test_secrets_health(self):
        resp = client.get("/api/core/secrets/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "secrets" in data
        assert "vault_available" in data["secrets"]


class TestHealthEndpoints:
    def test_health_summary(self):
        center = get_health_center()
        center.register("test_ok", lambda: True, "system")
        resp = client.get("/api/core/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_run_health_check(self):
        center = get_health_center()
        center.register("test_run", lambda: True, "system")
        resp = client.post("/api/core/health/run")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data

    def test_list_health_checks(self):
        resp = client.get("/api/core/health/checks")
        assert resp.status_code == 200
        data = resp.json()
        assert "checks" in data


class TestIntegrationCenterEndpoints:
    def test_list_integrations(self):
        resp = client.get("/api/core/integrations")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_status" in data
        assert "by_category" in data
        assert "categories" in data
        assert "integrations" in data
        assert data["total"] >= 20  # At least the built-in integrations

    def test_list_categories(self):
        resp = client.get("/api/core/integrations")
        data = resp.json()
        categories = data["categories"]
        assert "platform" in categories
        assert "ai" in categories
        assert "exchange" in categories
        assert "blockchain" in categories
        assert "financial" in categories
        assert "messaging" in categories
        assert "infrastructure" in categories

    def test_get_known_integration(self):
        resp = client.get("/api/core/integrations/coingecko")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "coingecko"
        assert data["category"] == "financial"
        assert "status" in data
        assert "checked_at" in data

    def test_get_unknown_integration(self):
        resp = client.get("/api/core/integrations/nonexistent_xyz")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_test_integration(self):
        resp = client.post("/api/core/integrations/coingecko/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "coingecko"
        assert "status" in data
        assert "checked_at" in data

    def test_test_unknown_integration(self):
        resp = client.post("/api/core/integrations/nonexistent_xyz/test")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data


class TestKnowledgeGraphEndpoints:
    """Tests for /api/core/knowledge/* endpoints."""

    def setup_method(self) -> None:
        from core.knowledge.graph import reset_knowledge_graph

        reset_knowledge_graph()

    def test_find_nodes_by_type(self):
        from core.knowledge.graph import reset_knowledge_graph

        reset_knowledge_graph()

        app = FastAPI()
        app.include_router(core_router)
        c = TestClient(app)
        resp = c.get("/api/core/knowledge/nodes?node_type=finding")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data

    def test_get_node(self):
        from core.knowledge.graph import reset_knowledge_graph

        reset_knowledge_graph()

        app = FastAPI()
        app.include_router(core_router)
        c = TestClient(app)
        resp = c.get("/api/core/knowledge/nodes/find-1")
        assert resp.status_code == 404  # fresh state, no nodes

    def test_add_node(self):
        from core.knowledge.graph import reset_knowledge_graph

        reset_knowledge_graph()

        app = FastAPI()
        app.include_router(core_router)
        c = TestClient(app)
        resp = c.post(
            "/api/core/knowledge/nodes",
            json={"node_type": "target", "name": "api.example.com", "properties": {"domain": "example.com"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["node_type"] == "target"
        assert data["name"] == "api.example.com"

    def test_delete_node_missing(self):
        from core.knowledge.graph import reset_knowledge_graph

        reset_knowledge_graph()

        app = FastAPI()
        app.include_router(core_router)
        c = TestClient(app)
        resp = c.delete("/api/core/knowledge/nodes/nonexistent")
        assert resp.status_code == 404

    def test_get_neighbors_no_nodes(self):
        from core.knowledge.graph import reset_knowledge_graph

        reset_knowledge_graph()

        app = FastAPI()
        app.include_router(core_router)
        c = TestClient(app)
        resp = c.get("/api/core/knowledge/nodes/missing/neighbors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    def test_get_path_no_path(self):
        from core.knowledge.graph import reset_knowledge_graph

        reset_knowledge_graph()

        app = FastAPI()
        app.include_router(core_router)
        c = TestClient(app)
        resp = c.get("/api/core/knowledge/path?source=a&target=b")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    def test_get_subgraph(self):
        from core.knowledge.graph import reset_knowledge_graph

        reset_knowledge_graph()

        app = FastAPI()
        app.include_router(core_router)
        c = TestClient(app)
        resp = c.get("/api/core/knowledge/subgraph")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_nodes" in data
        assert "total_edges" in data
        assert "center" in data

    def test_add_edge_missing_nodes(self):
        from core.knowledge.graph import reset_knowledge_graph

        reset_knowledge_graph()

        app = FastAPI()
        app.include_router(core_router)
        c = TestClient(app)
        resp = c.post(
            "/api/core/knowledge/edges",
            json={"source_id": "missing-1", "target_id": "missing-2"},
        )
        assert resp.status_code == 404

    def test_stats(self):
        from core.knowledge.graph import reset_knowledge_graph

        reset_knowledge_graph()

        app = FastAPI()
        app.include_router(core_router)
        c = TestClient(app)
        resp = c.get("/api/core/knowledge/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_nodes" in data
        assert "total_edges" in data
