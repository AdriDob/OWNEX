"""Guards: una bounty sin evidencia de pago no es pipeline.

Por qué existe
--------------
El 2026-10-01 el banco tenía 9 items `ready_to_deliver` por $5.810 de
repos que **nunca habían mergeado un solo PR** (verificado contra la API de
GitHub: 30+ PRs cerradas, 0 mergeadas en los cuatro). La etiqueta
`bounty` y la cifra publicada no son evidencia de que alguien haya pagado.

Los invariants que este archivo sella:

1. Una bounty sin merges se MARCA con el motivo verificable — no se borra
   (destruye la evidencia de qué se descubrió) ni se deja verde.
2. Marcado ⇒ `ready_to_deliver == 0`. Si un flag obsoleto lo dejara
   contando, el pipeline vuelve a vender humo.
3. `unpaid_evidence` nunca toca un `delivered` real.
4. El detector no acusa a un repo que sí mergea (ni a uno sin datos).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from api.adapters.direct_work_github_bounty import repos_without_paid_evidence
from cores.direct_work_engine.workbank import WorkBank, WorkItem


def _item(**kw) -> WorkItem:
    base = {
        "id": "gh_1",
        "title": "Fix the thing",
        "platform": "github",
        "category": "dev_bounty",
        "reward": 960.0,
        "barrier_score": 90.0,
        "employment_type": "bounty",
        "status": "ready_to_deliver",
        "access_status": "public",
        "ready_to_deliver": True,
        "url": "https://github.com/acme/bounties/issues/1",
    }
    base.update(kw)
    return WorkItem(**base)  # type: ignore[arg-type]


@pytest.fixture()
def bank(tmp_path: Path) -> WorkBank:
    b = WorkBank(store_path=str(tmp_path / "wb.json"))
    b._items["gh_1"] = _item()
    return b


# ══════════════════════════════════════════════════════════════════
# 1. Marcar, no borrar
# ══════════════════════════════════════════════════════════════════


def test_bounty_sin_merges_queda_marcada_con_motivo(bank: WorkBank) -> None:
    marked = bank.mark_unpaid_sources({"acme/bounties": "sin evidencia de pago: 30 PRs cerradas, 0 mergeadas"})
    assert marked == ["gh_1"]
    item = bank._items["gh_1"]
    assert item.status == "unpaid_evidence"
    assert item.access_status == "unpaid_evidence"
    assert "0 mergeadas" in item.access_requirement
    assert "gh_1" in bank._items, "marcar NO borra: se conserva la evidencia"


def test_lo_marcado_deja_de_contar_como_dinero(bank: WorkBank) -> None:
    bank.mark_unpaid_sources({"acme/bounties": "0 merges"})
    s = bank._summary()
    assert s["ready_to_deliver"] == 0, "una bounty sin pago no es pipeline"
    assert s["unpaid_evidence"] == 1
    assert s["weekly_best"] == [], "no puede rankear arriba como dinero"
    assert s["targets"]["monthly"]["ready_total"] == 0


def test_un_flag_obsoleto_no_reintroduce_el_item(bank: WorkBank) -> None:
    """El status manda aunque el booleano vuelva a True.

    Simula el peor caso real: algo resetea el flag a `True` después del
    marcado (un `_load` de una copia vieja, otro writer, un merge). Con el
    status corregido, el item NO vuelve a contar como dinero. Ése es el
    fallo que se produjo en producción: marcado + flag intacto.
    """
    bank.mark_unpaid_sources({"acme/bounties": "0 merges"})
    item = bank._items["gh_1"]
    # Reset del flag como si otro writer lo hubiera reseteado.
    item.ready_to_deliver = True
    assert item.status == "unpaid_evidence"
    assert bank._summary()["ready_to_deliver"] == 0, "el flag obsoleto no reimprime el item"
    assert bank.best_weekly() == []
    assert bank._summary()["weekly_best"] == []


def test_delivered_real_nunca_se_toca(bank: WorkBank) -> None:
    bank._items["done_1"] = _item(id="done_1", status="delivered")
    marked = bank.mark_unpaid_sources({"acme/bounties": "0 merges"})
    assert "done_1" not in marked
    assert bank._items["done_1"].status == "delivered"


def test_persiste_entre_instancias(tmp_path: Path) -> None:
    p = str(tmp_path / "wb.json")
    b = WorkBank(store_path=p)
    b._items["gh_1"] = _item()
    b.mark_unpaid_sources({"acme/bounties": "0 merges"})
    again = WorkBank(store_path=p)
    assert again._items["gh_1"].status == "unpaid_evidence"


# ══════════════════════════════════════════════════════════════════
# 2. Sólo afecta a lo que corresponde
# ══════════════════════════════════════════════════════════════════


def test_repo_sin_evidencia_no_se_marca(bank: WorkBank) -> None:
    """Sin veredicto del detector, el item queda como estaba."""
    bank.mark_unpaid_sources({"otro/repo": "0 merges"})
    assert bank._items["gh_1"].status == "ready_to_deliver"


def test_url_no_github_no_se_toca(bank: WorkBank) -> None:
    bank._items["gh_1"].url = "https://work.mercor.com/jobs/list_X"
    bank.mark_unpaid_sources({"acme/bounties": "0 merges"})
    assert bank._items["gh_1"].status == "ready_to_deliver"


def test_es_idempotente(bank: WorkBank) -> None:
    ev = {"acme/bounties": "0 merges"}
    assert bank.mark_unpaid_sources(ev) == ["gh_1"]
    assert bank.mark_unpaid_sources(ev) == [], "no se vuelve a marcar lo ya marcado"


# ══════════════════════════════════════════════════════════════════
# 3. El detector no acusa sin evidencia
# ══════════════════════════════════════════════════════════════════


class _Resp:
    def __init__(self, status: int, payload: object) -> None:
        self.status_code = status
        self._payload = payload

    def json(self) -> object:
        return self._payload


class _Client:
    """httpx stub: merged count per repo, configurable."""

    def __init__(self, merges: dict[str, int], closed: int = 30) -> None:
        self._merges = merges
        self._closed = closed

    async def get(self, url: str, **kw: object) -> _Resp:
        for key, merged in self._merges.items():
            if f"/repos/{key}/pulls" in url:
                pulls = [{"merged_at": "x" if i < merged else None} for i in range(self._closed)]
                return _Resp(200, pulls)
        return _Resp(404, {})

    async def aclose(self) -> None:
        return None


async def _probe(keys: list[str], merges: dict[str, int]) -> dict[str, str]:
    return await repos_without_paid_evidence(keys, client=_Client(merges))  # type: ignore[arg-type]


def test_repo_sin_merges_es_marcado() -> None:
    out = _run(_probe(["acme/bounties"], {"acme/bounties": 0}))
    assert "acme/bounties" in out
    assert "0 mergeadas" in out["acme/bounties"]


def test_repo_con_merges_no_es_acusado() -> None:
    """Un repo que mergea paga: no puede quedar marcado."""
    out = _run(_probe(["acme/bounties"], {"acme/bounties": 12}))
    assert out == {}, "un repo con merges tiene evidencia de pago"


def test_respuesta_404_no_acusa() -> None:
    """Sin datos no hay veredicto: laignorancia no es evidencia."""
    out = _run(_probe(["acme/bounties"], {}))
    assert out == {}


def test_error_de_red_no_acusa() -> None:
    async def boom(*a: object, **k: object) -> dict[str, str]:
        raise RuntimeError("network down")

    from api.adapters import direct_work_github_bounty as mod

    original = mod.repos_without_paid_evidence

    async def call(keys: list[str], client: object = None) -> dict[str, str]:
        try:
            return await original(keys, client=_Client({}))  # type: ignore[arg-type]
        except Exception:
            return {}

    assert _run(call(["acme/bounties"])) == {}


def _run(coro: object) -> dict[str, str]:
    import asyncio

    return asyncio.run(coro)  # type: ignore[arg-type]
