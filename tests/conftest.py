"""Shared fixtures for CATEYE test suite."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("CATEYE_CSRF_DISABLED", "1")

# Isolate test DB: never touch the real database/catseye.db
os.environ["DATABASE_URL"] = f"sqlite:////tmp/cateye_test_{os.getpid()}.db"

from database.db import DATABASE_URL as _DB_URL  # noqa: E402

if "catseye.db" in _DB_URL:
    raise RuntimeError(
        "Refusing to run tests against the real database "
        f"(DATABASE_URL={_DB_URL!r}). Set DATABASE_URL to a temp path first."
    )


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
