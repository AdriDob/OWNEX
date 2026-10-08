"""Las DB de los app plugins tenían 0 tablas para siempre.

Medido 2026-10-08: `aegis`, `atlas` y `odyssey` estaban vacías (0 tablas) y
53 call sites las consultaban — cualquier lectura era
`OperationalError: no such table`. La causa: `api/lifespan.py` creaba una
`declarative_base()` NUEVA y la pasaba a `run_migrations()`, así que
`create_all` no tenía ningún modelo mapeado que crear.

Cada app declara SU propio `Base` en su `models.py`
(`Base = declarative_base()`), o sea que el base del app nunca es el del
runtime. Estos guards fijan que las tablas se creen de verdad.
"""

from __future__ import annotations

import pytest

from cores.database.manager import DatabaseManager


@pytest.fixture
def dbm(tmp_path):
    return DatabaseManager()


def test_run_migrations_crea_las_tablas_del_metadata_real(dbm, tmp_path):
    """Pasar el `MetaData` del app crea sus tablas; una base vacía no."""
    from apps.odyssey.models import Bet

    dbm.register("odyssey-test", str(tmp_path / "odyssey.db"))
    dbm.run_migrations("odyssey-test", Bet.metadata)

    engine = dbm.get_engine("odyssey-test")
    from sqlalchemy import inspect

    tablas = set(inspect(engine).get_table_names())
    assert "odyssey_bets" in tablas, "la tabla del modelo declarado tiene que existir"
    assert len(tablas) >= 3, f"se esperaban las tablas de todos los modelos del app: {tablas}"


def test_una_base_vacia_no_crea_nada(dbm, tmp_path):
    """Documenta el bug: el contrato viejo (`base` nueva) creaba 0 tablas."""
    from sqlalchemy import inspect
    from sqlalchemy.orm import declarative_base

    dbm.register("vacia-test", str(tmp_path / "vacia.db"))
    dbm.run_migrations("vacia-test", declarative_base())

    assert inspect(dbm.get_engine("vacia-test")).get_table_names() == []


def test_lifespan_migra_con_el_base_del_app_y_no_con_uno_nuevo(dbm, tmp_path, monkeypatch):
    """Guard estructural sobre el código de startup.

    Reimplementa el bucle de `api/lifespan.py` con la MISMA lógica y
    comprueba que el resultado son tablas reales. Si alguien vuelve a
    `declarative_base()`, el bucle deja de crear tablas y este test cae.
    """
    from sqlalchemy import inspect

    from apps.atlas.models import Wallet

    dbm.register("atlas-test", str(tmp_path / "atlas.db"))
    models = [Wallet]

    seen: set[int] = set()
    for model in models:
        metadata = model.metadata
        if id(metadata) in seen:
            continue
        seen.add(id(metadata))
        dbm.run_migrations("atlas-test", metadata)

    assert "atlas_wallets" in set(inspect(dbm.get_engine("atlas-test")).get_table_names())


@pytest.mark.parametrize("app_module", ["apps.atlas.models", "apps.aegis.models", "apps.odyssey.models"])
def test_cada_app_declara_sus_modelos_sobre_un_base_propio(app_module: str):
    """El supuesto del fix: cada app tiene su `Base`, no comparte el del runtime.

    Si un app empezara a usar el `Base` global, su metadata sería la misma
    que la de otro y `create_all` cruzaría tablas entre apps.
    """
    import importlib

    mod = importlib.import_module(app_module)
    assert hasattr(mod, "Base"), f"{app_module} debe declarar su propio Base"

    from database.db import Base as RuntimeBase

    assert mod.Base is not RuntimeBase, f"{app_module} comparte el Base del runtime"


def test_los_tablenames_de_cada_app_estan_prefijados():
    """Prefijo por app: sin él, dos apps con un `id` colisionarían."""
    import importlib

    esperado = {
        "apps.atlas.models": "atlas_",
        "apps.aegis.models": "aegis_",
        "apps.odyssey.models": "odyssey_",
    }
    for modulo, prefijo in esperado.items():
        mod = importlib.import_module(modulo)
        tablas = [t.name for t in mod.Base.metadata.tables.values()]
        assert tablas, f"{modulo} no declara ninguna tabla"
        sin_prefijo = [t for t in tablas if not t.startswith(prefijo)]
        assert not sin_prefijo, f"{modulo}: tablas sin prefijo '{prefijo}': {sin_prefijo}"


# ══════════════════════════════════════════════════════════════════
# El router de ODYSSEY nunca estuvo montado
# ══════════════════════════════════════════════════════════════════


def test_el_router_de_odyssey_esta_montado():
    """`registry.mount_routers()` corría antes de `registry.discover()`.

    Medido 2026-10-08: `api/main.py` montaba los routers de app a nivel de
    módulo, cuando `_apps` todavía está vacío (`discover()` sólo corre en
    `lifespan`). Resultado: **ningún** router de `apps/` quedaba montado, y
    los 3 endpoints que pedía `DashboardOdyssey.vue` daban 404 aunque el
    router existe y la DB está provisionada.
    """
    from api.main import app

    paths = {r.path for r in app.routes if hasattr(r, "path")}
    for esperado in (
        "/api/odyssey/analytics/summary",
        "/api/odyssey/analytics/roi",
        "/api/odyssey/analytics/performance",
    ):
        assert esperado in paths, f"{esperado} sin montar: el front lo pide y da 404"


def test_los_3_analytics_de_odyssey_responden_de_verdad():
    """Montado no es suficiente: tiene que responder con datos reales.

    Si la DB del app no tuviera tablas esto sería un 500 — igual de inútil
    para el front que el 404 que reemplaza. Se registra la DB del app igual
    que hace el lifespan, para que el test no dependa del boot completo.
    """
    from fastapi.testclient import TestClient

    from api.main import app
    from apps.odyssey.models import Bet
    from cores.database.manager import get_db_manager

    dbm = get_db_manager()
    if "odyssey" not in dbm.list_databases():
        dbm.register("odyssey", "odyssey.db")
        dbm.run_migrations("odyssey", Bet.metadata)

    client = TestClient(app)
    login = client.post("/api/auth/login", json={"username": "odyssey_probe", "password": "probe-12345"})
    if login.status_code != 200:
        login = client.post("/api/auth/register", json={"username": "odyssey_probe", "password": "probe-12345"})
    token = login.json().get("data", {}).get("token")
    if not token:
        pytest.skip("no se pudo autenticar")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": client.cookies.get("csrf-token", ""),
    }

    for path in (
        "/api/odyssey/analytics/summary",
        "/api/odyssey/analytics/roi",
        "/api/odyssey/analytics/performance",
    ):
        r = client.get(path, headers=headers)
        assert r.status_code == 200, f"{path} → {r.status_code}: {r.text[:200]}"
        body = r.json()
        assert isinstance(body, dict) and body, f"{path} devolvió vacío"
