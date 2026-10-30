"""
IDs del WorkBank utilizables como path param.

Regresión medida el 2026-10-05: los ids de oportunidad vienen de URLs de
GitHub (`github_bounty_github_<owner>/<repo>#<n>`). En FastAPI/Starlette:

- `/` crea una ruta nueva ⇒ nunca matchea `{item_id}`;
- `#` trunca el fragmento **antes** de que el router vea la URL.

Y `encodeURIComponent` NO lo salva: medido que `a/b`, `a%2Fb` y `a%23b` dan
404 los tres. Resultado: **los 11 items del banco eran inalcanzables por API**
y el Work Room no cargaba para ningún trabajo real.
"""

from pathlib import Path

from cores.direct_work_engine.workbank import _path_safe_id

SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")


def test_id_con_url_de_github_queda_path_safe():
    raw = "github_bounty_github_warpspeedopen-source/warpspeed-bounties#9"
    out = _path_safe_id(raw)
    assert "/" not in out and "#" not in out
    assert set(out) <= SAFE


def test_ids_existentes_no_cambian():
    """Los ids ya limpios deben quedar idénticos (no romper el store)."""
    for raw in ("opire-1", "deliver-1", "freelance-1", "bounty-1", "pend-1"):
        assert _path_safe_id(raw) == raw


def test_legibilidad_conservada():
    out = _path_safe_id("github_bounty_github_acme/repo#7")
    # Sigue siendo legible: no nos fijamos en un hash opaco.
    assert out == "github_bounty_github_acme_repo_7"


def test_entradas_hostiles_no_dejan_rastro_vacio():
    for raw in ("", "   ", "#", "///", "???", "\n\t"):
        out = _path_safe_id(raw)
        assert out, f"id vacío para {raw!r}"
        assert set(out) <= SAFE


def test_no_hay_colisiones_entre_urls_distintas():
    a = _path_safe_id("gh_acme/repo#1")
    b = _path_safe_id("gh_acme/repo#2")
    assert a != b, "ids distintos no pueden colapsar al mismo path"


def test_el_id_generado_llega_al_item(tmp_path: Path):
    """End-to-end del ciclo: el item creado debe ser alcanzable por API."""
    from api.routers.direct_work import router
    from cores.direct_work_engine.workbank import WorkBank, WorkItem

    bank = WorkBank(store_path=str(tmp_path / "wb.json"))
    item = WorkItem(
        id=_path_safe_id("github_bounty_github_acme/repo#7"),
        title="Fix",
        platform="github",
        category="dev_bounty",
        reward=100.0,
        barrier_score=90.0,
        employment_type="bounty",
    )
    bank._items[item.id] = item
    bank._save()

    # El router expone las rutas con `{item_id}`: si el id tuviera `/`, la
    # URL `/workbank/<id>/deliver/prepare` no matchearía ninguna ruta.
    paths = [getattr(r, "path", "") for r in router.routes]
    assert any("deliver/prepare" in p for p in paths)

    reloaded = WorkBank(store_path=str(tmp_path / "wb.json"))
    assert item.id in reloaded._items, "el item debe persistir y ser recuperable"
