"""P1 regression: async jobs awaited + WorkPlatform.OPEN_SOURCE + profile sin name.

2026-09-15 PHASE 3 audit (evidencia runtime):
- 21 handlers async de get_all_jobs eran llamados sin await → coroutine nunca
  awaited (discovery/execution/worker muertos). Fix: lifespan._run_job los aguarda.
- WorkPlatform no tenía OPEN_SOURCE pero bountyboard/polar lo usaban → error
  runtime "type object 'WorkPlatform' has no attribute 'OPEN_SOURCE'". Fix: enum.
- _profile_from_dict sin name rompía /recommend (500): default "me".

Estos tres eran bugs REALES de producción (no tests).
"""

from __future__ import annotations

import os

os.environ["CATEYE_CSRF_DISABLED"] = "1"


def test_workplatform_has_open_source() -> None:
    from cores.direct_work_engine.models import WorkPlatform

    assert WorkPlatform.OPEN_SOURCE == "open_source"
    assert WorkPlatform("open_source") == WorkPlatform.OPEN_SOURCE


def test_all_adapters_use_existing_workplatform_values() -> None:
    """Cada plataforma que los adapters usan existe en el enum (regresión OPEN_SOURCE).

    Incluye dígitos ([A-Z0-9_]+) para no dar falsos positivos con CODE4RENA.
    """
    import re
    from pathlib import Path

    from cores.direct_work_engine.models import WorkPlatform

    valid_names = {v.name for v in WorkPlatform}
    adapters_dir = Path(__file__).resolve().parent.parent / "api" / "adapters"
    missing: set[str] = set()
    for f in adapters_dir.glob("direct_work_*.py"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        for match in re.findall(r"WorkPlatform\.([A-Z0-9_]+)", text):
            if match not in valid_names:
                missing.add(f"{f.name}:{match}")
    assert not missing, f"Plataformas inexistentes usadas en adapters: {sorted(missing)[:10]}"


def test_recommend_works_without_profile_name() -> None:
    """El endpooint /direct-work/recommend no debe 500 cuando el profile no trae name."""
    from fastapi.testclient import TestClient

    import api.main as m

    client = TestClient(m.app)
    login = client.post("/api/auth/login", json={"device_id": "phase3-regression"}).json()
    headers = {"Authorization": f"Bearer {login['data']['token']}"}
    payload = {"profile": {"skills": ["python"], "languages": ["en"], "availability_hours": 4}}
    r = client.post("/direct-work/recommend", headers=headers, json=payload)
    # 200 (o 422 si algún campo es estrictamente inválido) — pero NUNCA 500.
    assert r.status_code != 500
    if r.status_code == 200:
        body = r.json()
        assert "ranked" in body or "recommendations" in body or "total" in body
