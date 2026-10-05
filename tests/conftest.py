"""Shared fixtures for CATEYE test suite."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("CATEYE_CSRF_DISABLED", "1")

# Isolate test DB: never touch the real database/catseye.db
os.environ["DATABASE_URL"] = f"sqlite:////tmp/cateye_test_{os.getpid()}.db"

# Isolate the data dir: never write to ~/.ownex nor ~/ownex/submissions.
#
# Antes se escribían paquetes de trabajo reales en el HOME: 1.354 fixtures
# ("deliv-1", "e2e-1", "wire-1", todos con `[Add implementation details here]`)
# acumulados en ~/ownex/submissions/opire/ entre el 4 y el 5 de agosto. La causa
# era doble: AssistedExecutor tenía "~/ownex/submissions" hardcodeado (corregido
# para respetar OWNEX_DATA_DIR) y conftest sólo aislaba DATABASE_URL.
#
# A nivel de módulo, no con monkeypatch: debe cubrir toda la sesión, igual que
# DATABASE_URL.
_TEST_DATA_DIR = Path(f"/tmp/OWNEX_test_{os.getpid()}")  # OWNEX en mayúsculas: lo valida test_desktop_release
_TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["OWNEX_DATA_DIR"] = str(_TEST_DATA_DIR)
os.environ.setdefault("CATEYE_DATA_DIR", str(_TEST_DATA_DIR))

from database.db import DATABASE_URL as _DB_URL  # noqa: E402

# El guard anterior (`if "catseye.db" in _DB_URL`) era tautológico: DATABASE_URL
# se fija 14 líneas más arriba, así que nunca podía dispararse. Éste compara la
# ruta RESUELTA contra las dos bases reales — la del repo (90 MB con datos del
# usuario) y la de la app instalada.
_REAL_DATABASES = {
    (Path(__file__).resolve().parent.parent / "database" / "catseye.db").resolve(),
    (Path.home() / ".ownex" / "database" / "catseye.db").resolve(),
}
_resolved_db = Path(_DB_URL.replace("sqlite:///", "", 1)).resolve()
if _resolved_db in _REAL_DATABASES:
    raise RuntimeError(
        f"Refusing to run tests against a real database: {_resolved_db}. "
        "A test writing there writes to production data."
    )


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_artifacts_in_data_dir():
    """Red de seguridad: borra artefactos de test que se filtren al data dir real.

    `OWNEX_DATA_DIR` aísla la mayoría, pero cualquier code path que resuelva el
    path por otra vía (o que corra fuera de pytest) escribe en
    `~/.ownex/database/`. Ya se acumulaban 8.597 bases `knowledge_graph_kg_test_*`
    (663 MB) ahí, en el directorio de la app instalada.

    No borra nada del directorio real de la app: sólo ficheros cuyo nombre
    matchea los prefijos de test conocidos.
    """

    yield

    data_dir = Path(os.environ.get("OWNEX_DATA_DIR", ""))
    # Nunca tocar el directorio real de la app instalada: sólo temporales.
    if not data_dir or data_dir == Path.home() / ".ownex":
        return
    db_dir = data_dir / "database"
    if not db_dir.is_dir():
        return
    patterns = ("*_test_*.db", "*_test_*.db-wal", "*_test_*.db-shm", "*_kg_test_*.db*")
    removed = 0
    for pattern in patterns:
        for f in db_dir.glob(pattern):
            try:
                f.unlink()
                removed += 1
            except OSError:
                pass
    if removed:
        print(f"[conftest] limpiados {removed} artefactos de test de {db_dir}")


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db() -> None:
    """Remove the per-PID temp test DB after the session."""
    yield
    for suffix in ("", "-shm", "-wal"):
        p = Path(f"/tmp/cateye_test_{os.getpid()}.db{suffix}")
        if p.exists():
            p.unlink()


@pytest.fixture(scope="session", autouse=True)
def _init_test_db() -> None:
    """Create all tables once for the session.

    TestClient(app) without a `with:` block does not run the lifespan, so
    db.init_db() never fires and tables like `users`/`memory_records` are missing
    when tests query the DB directly (e.g. tests/test_learning.py fixture).
    """
    from cores.learning import profile as _learning_models  # noqa: F401
    from cores.targets import models as _targets_models  # noqa: F401
    from database import models  # noqa: F401 — register metadata
    from database.db import Base, engine

    Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _set_license_key() -> None:
    """Generate a dev Ed25519 key pair at test time for license generation."""
    if "CATEYE_LICENSE_PRIVATE_KEY" not in os.environ:
        from base64 import b64encode

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        priv_raw = key.private_bytes_raw()
        os.environ["CATEYE_LICENSE_PRIVATE_KEY"] = b64encode(priv_raw).decode()
        os.environ["CATEYE_LICENSE_PUBLIC_KEY"] = b64encode(key.public_key().public_bytes_raw()).decode()


# ── Auth para tests que pegan a rutas montadas en RAÍZ ─────────────

# `AuthMiddleware` exige sesión en las rutas montadas en raíz desde el fix del
# gate de auth (KNOWN_DEBT #32, 2026-10-04) — y desde el 2026-10-05 también en
# las que tienen parámetro de path, que antes se colaban sin credencial.
# `test_mission_hub.py`, `test_mobile_copilot.py` y `test_night_session_fixes.py`
# seguían pegando a `/mission-hub/*` y `/mobile/*` sin autenticar: tests que
# medían el 401 en vez del endpoint.
#
# El fixture replica el flujo real del navegador (login → cookie de sesión),
# no una backdoor: si el gate se rompe, vuelven a fallar en vez de pasar.


@pytest.fixture(scope="session")
def ownex_login():
    """Devuelve un callable que autentica un `TestClient` como el cliente real.

    Usa el login por `device_id` (`/api/auth/login`) y deja la cookie
    `ownex-session` en el jar del cliente — el mismo camino que sigue el
    navegador. El token se cachea a nivel sesión y se reintenta ante 429: el
    login está rate-limited, así que un fixture function-scoped queloguea en
    cada test se autobloquea (medido: 7 errores 429 en test_mission_hub.py).
    """
    import time

    from api.middleware.auth_middleware import SESSION_COOKIE

    cache: dict[str, str] = {}

    def _login(client) -> str:
        if "token" not in cache:
            last = ""
            for _ in range(6):
                resp = client.post(
                    "/api/auth/login",
                    json={"device_id": "pytest-suite", "device_info": {"kind": "pytest"}},
                )
                if resp.status_code == 200:
                    cache["token"] = resp.json().get("data", {}).get("token", "")
                    break
                last = f"{resp.status_code}: {resp.text[:200]}"
                if resp.status_code == 429:
                    time.sleep(1.5)
                    continue
                break
            if not cache.get("token"):
                pytest.fail(f"login de tests falló con {last}")
        client.cookies.set(SESSION_COOKIE, cache["token"])
        return cache["token"]

    return _login


# ── Path fixtures ─────────────────────────────────────────────────


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def go_bin() -> Path:
    return Path.home() / "go" / "bin"


@pytest.fixture
def recon_tools(go_bin: Path) -> dict[str, Path | None]:
    """Resolve all recon tool paths."""
    from cores.recon.tools import _resolve_tool

    return {
        "subfinder": _resolve_tool("subfinder"),
        "katana": _resolve_tool("katana"),
        "httpx": _resolve_tool("httpx"),
    }


# ── Test data factories ───────────────────────────────────────────


@pytest.fixture
def target_factory() -> dict[str, Any]:
    """Create a minimal target payload."""
    return {
        "name": "test-target.example.com",
        "domain": "example.com",
    }


@pytest.fixture
def endpoint_factory() -> dict[str, Any]:
    """Create a minimal endpoint payload."""
    return {
        "path": "/api/test",
        "method": "GET",
        "params": {},
    }


@pytest.fixture
def finding_factory() -> dict[str, Any]:
    """Create a minimal finding payload."""
    return {
        "vulnerability_type": "information_disclosure",
        "severity": "medium",
        "description": "Test finding description",
    }


@pytest.fixture
def report_factory() -> dict[str, Any]:
    """Create a minimal report payload."""
    return {
        "format": "hackerone_json",
        "severity": "medium",
        "vulnerability": "information_disclosure",
    }


@pytest.fixture
def verdict_factory() -> dict[str, Any]:
    """Create a confirmed verdict payload."""
    return {
        "hot_path_id": "0:endpoint:GET:/api/test",
        "status": "confirmed",
        "confidence": 0.85,
        "reason": "Test verdict reason",
    }


@pytest.fixture
def evidence_factory() -> dict[str, Any]:
    """Create a minimal evidence entry."""
    return {
        "type": "request_response",
        "request": "GET /api/test HTTP/1.1",
        "response": "HTTP/1.1 200 OK",
        "signals": ["test_signal"],
    }


@pytest.fixture
def scan_context_factory() -> dict[str, Any]:
    """Create a full scan context for pipeline testing."""
    return {
        "target_id": 1,
        "target_name": "test-target.example.com",
        "baseline_token": None,
        "probe_token": None,
        "endpoints": [
            {"path": "/api/users", "method": "GET", "params": {"id": "1"}},
            {"path": "/api/admin", "method": "POST", "params": {"action": "delete"}},
            {"path": "/api/data", "method": "GET", "params": {}},
        ],
    }
