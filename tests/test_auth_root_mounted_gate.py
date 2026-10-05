"""El gate de auth debe cubrir las rutas montadas en RAÍZ, incluidas las que
tienen parámetros de path.

Por qué este test existe (bug medido el 2026-10-05):

`AuthMiddleware` distingue "endpoint del backend" de "asset/SPA route" con
`path not in _MOUNTED_PATHS`. Pero `_MOUNTED_PATHS` guarda el path **con
plantilla** (`/direct-work/workbank/{item_id}/deliver/approve`) y el dispatch
lo comparaba contra el path **concreto** de la request
(`/direct-work/workbank/1/deliver/approve`). Nunca coinciden.

Consecuencia: las 51 rutas root-mounted con parámetro de path pasaban sin
credencial. Medido en vivo contra el server, anónimo:

    GET  /mobile/reject/1                 → 405   (llegó al router: auth evitada)
    GET  /today                           → 401   (correcto)
    POST /direct-work/workbank/1/submit   → 403   (CSRF, no auth)

Entre las afectadas: `POST /mobile/approve/{approval_id}`,
`POST /mobile/reject/{approval_id}` y `POST
/direct-work/workbank/{item_id}/deliver/approve` — aprobar y rechazar
entregas en nombre del owner.

Este archivo pinaba las 4 propiedades que cierran el bypass:
1. Toda ruta root-mounted con parámetro se resuelve como montada.
2. Anónimo ⇒ 401 en las templated root-mounted (no 405/403/404).
3. Las rutas SPA/asset (no montadas) siguen pasando sin credencial, o la app
   no carga.
4. Las allowlist públicas siguen respondiendo sin credencial.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def app_and_client():
    from fastapi.testclient import TestClient

    from api.main import app

    return app, TestClient(app)


@pytest.fixture(scope="module")
def licensed_client(app_and_client):
    """TestClient con licencia activada: sin ella el license gate responde 402
    y no se distingue el 401 del gate de auth."""
    from cores.license.validator import generate_license

    _, client = app_and_client
    lic = generate_license(expiry_days=365)
    client.post("/api/license/activate", json={"key": lic})
    return client


def _templated_root_mounted(app) -> list[str]:
    """Plantillas root-mounted que tienen al menos un parámetro de path."""
    out = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path or path.startswith("/api/") or "{" not in path:
            continue
        out.append(path)
    return out


def _concretize(template: str) -> str:
    """`/x/{id}/y` → `/x/probe-id-42/y` (rellena cada parámetro)."""
    out, i = [], 0
    for segment in template.strip("/").split("/"):
        if segment.startswith("{") and segment.endswith("}"):
            i += 1
            out.append(f"probe-id-{i}")
        else:
            out.append(segment)
    return "/" + "/".join(out)


class TestMountedResolution:
    def test_templated_root_mounted_routes_exist(self, app_and_client):
        """Guard de fiabilidad: si esto falla, el archivo probaría nada."""
        app, _ = app_and_client
        templates = _templated_root_mounted(app)
        assert len(templates) >= 40, f"sólo {len(templates)} rutas templated root-mounted"

    def test_every_templated_route_resolves_as_mounted(self, app_and_client):
        """El bug: el path concreto no matcheaba la plantilla."""
        from api.middleware.auth_middleware import AuthMiddleware

        app, _ = app_and_client
        missed = [t for t in _templated_root_mounted(app) if not AuthMiddleware._is_mounted(_concretize(t))]
        assert not missed, f"{len(missed)} rutas templated no se resuelven como montadas: {missed[:5]}"

    def test_literal_root_mounted_still_resolves(self, app_and_client):
        from api.middleware.auth_middleware import AuthMiddleware

        _, _ = app_and_client
        assert AuthMiddleware._is_mounted("/today")
        assert AuthMiddleware._is_mounted("/direct-work/revenue-ledger")

    def test_spa_routes_are_not_mounted(self, app_and_client):
        """Si un path de SPA se marcara como montado, la app pediría
        credencial en /settings y no cargaría."""
        from api.middleware.auth_middleware import AuthMiddleware

        app, _ = app_and_client
        for spa in ("/settings", "/daily", "/mission-control"):
            assert spa not in {getattr(r, "path", "") for r in app.routes}
            assert not AuthMiddleware._is_mounted(spa), f"{spa} no debe matchear como endpoint"

    def test_catchall_patterns_are_indexed(self, app_and_client):
        """Las rutas cuyo primer segmento es un parámetro no se pueden indexar
        por prefijo: van al catch-all, que debe seguir populated."""
        from api.middleware.auth_middleware import AuthMiddleware

        assert AuthMiddleware._MOUNTED_BY_PREFIX
        # y el índice debe servir las rutas con primer segmento literal
        assert "mobile" in AuthMiddleware._MOUNTED_BY_PREFIX


class TestAnonymousRequests:
    def test_templated_get_requires_auth(self, licensed_client):
        """El caso exacto del bypass: GET a una templated root-mounted."""
        resp = licensed_client.get("/mobile/reject/1")
        assert resp.status_code == 401, f"esperaba 401, recibí {resp.status_code}: {resp.text[:120]}"

    def test_literal_get_requires_auth(self, licensed_client):
        resp = licensed_client.get("/today")
        assert resp.status_code == 401, f"esperaba 401, recibí {resp.status_code}"

    def test_templated_post_requires_auth_not_just_csrf(self, licensed_client, monkeypatch):
        """Sin credencial debe cortar el gate de auth (401), no el de CSRF.

        El orden importa: un 403 significa que la request llegó al router.
        """
        monkeypatch.setenv("CATEYE_CSRF_DISABLED", "1")
        resp = licensed_client.post("/direct-work/workbank/1/submit", json={})
        assert resp.status_code == 401, f"esperaba 401 (auth), recibí {resp.status_code}: {resp.text[:120]}"

    def test_spa_route_loads_without_auth(self, licensed_client):
        """La contraparte: la app tiene que cargar sin sesión."""
        resp = licensed_client.get("/settings")
        assert resp.status_code == 404, f"un asset inexistente da 404, no 401 (recibí {resp.status_code})"


class TestPublicAllowlistStillOpen:
    @pytest.mark.parametrize("path", ["/api/health", "/api/version", "/api/system/health"])
    def test_public_api_paths_open(self, licensed_client, path):
        assert licensed_client.get(path).status_code == 200

    def test_root_exact_public_open(self, licensed_client):
        """`/version` está en PUBLIC_ROOT_EXACT. Que dé 404 y no 401 es la
        prueba: la allowlist lo dejó pasar y el 404 es del router, que es lo
        único que se puede afirmar sin depender de que la ruta exista."""
        assert licensed_client.get("/version").status_code != 401

    def test_root_exact_public_open_when_route_exists(self, licensed_client):
        """`/` sí está montada (endpoint raíz del backend) y es pública."""
        assert licensed_client.get("/").status_code != 401

    def test_auth_prefix_open(self, licensed_client):
        """`/auth/*` responde (405 en GET = llegó al router, no 401)."""
        resp = licensed_client.get("/auth/login")
        assert resp.status_code in (405, 404, 200), f"cerrado por auth: {resp.status_code}"
