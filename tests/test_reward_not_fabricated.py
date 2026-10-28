"""Guard: el pipeline del WorkBank NO puede inventar dinero.

Regresión 2026-09-30 (P0): el extractor de recompensa de GitHub usaba un
regex con el signo de dolar OPCIONAL, así que el label "hacktoberfest2025" se parseaba
como **$2.025** y "warp-speed 2024" como $2.024. Como la query del adapter
busca `label:hacktoberfest`, el año pegado al nombre se convertía en bounty
real: 4 de 8 READY ($4.050 = 80% del pipeline) eran dinero FICTICIO.

Regla: un número sólo es dinero si trae marcador de moneda ($ / USD) o una
palabra de bounty explícita (bounty/reward/prize/payout: N). Un año pegado a
un nombre de label es UNKNOWN (0.0), nunca efectivo.
"""

from __future__ import annotations

import pytest

from api.adapters.direct_work_github_bounty import GitHubBountyDweAdapter


@pytest.fixture
def extract():
    a = GitHubBountyDweAdapter.__new__(GitHubBountyDweAdapter)
    return a._extract_reward


# ══════════════════════════════════════════════════════════════════
# El bug: un año pegado al label se leía como recompensa
# ══════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "label",
    [
        "hacktoberfest2025",
        "hacktoberfest2024",
        "warp-speed 2024",
        "sprint-2026",
        "good first issue",
        "bounty",
        "help wanted",
        "hacktoberfest",
    ],
)
def test_ano_en_label_sin_marcador_no_es_dinero(extract, label):
    assert extract([label], "") == 0.0, f"{label!r} no puede valer dinero"


# ══════════════════════════════════════════════════════════════════
# Lo que SÍ es dinero (no romper el caso real)
# ══════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("reward: $500", 500.0),
        ("bounty $1000", 1000.0),
        ("reward: 500 USD", 500.0),
        ("$250", 250.0),
        ("bounty:1500", 1500.0),
        ("prize $2,500", 2500.0),
    ],
)
def test_marcador_de_moneda_si_es_dinero(extract, label, expected):
    assert extract([label], "") == expected


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("This issue has a bounty of $750", 750.0),
        ("Bounty: 1,200 USD", 1200.0),
        ("reward is 300", 300.0),
        ("no money mentioned here", 0.0),
    ],
)
def test_body_solo_cuenta_con_palabra_de_bounty(extract, body, expected):
    assert extract([], body) == expected


# ══════════════════════════════════════════════════════════════════
# Invariante de la sesión: nada que no tenga marca = UNKNOWN
# ══════════════════════════════════════════════════════════════════


def test_reward_siempre_finito_y_no_negativo(extract):
    for labels, body in [
        (["$99999999999"], ""),  # sobre el techo
        (["$0"], ""),
        (["reward: -5"], ""),
    ]:
        r = extract(labels, body)
        assert r >= 0.0


def test_cifra_inventada_no_puede_llegar_al_workbank():
    """El caso exacto que contaminó el banco: label con año, body sin dinero."""
    r = GitHubBountyDweAdapter.__new__(GitHubBountyDweAdapter)._extract_reward(
        ["good first issue", "hacktoberfest", "hacktoberfest2025"],
        "<h1>Add AI Tools Hub Feature on this page</h1>",
    )
    assert r == 0.0, "un issue de Hacktoberfest sin bounty NO vale $2025"


# ══════════════════════════════════════════════════════════════════
# El título es fuente legítima (muchas plataformas ponen ahí el monto)
# ══════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("[PAID BOUNTY - $2000] doc", 2000.0),
        ("[Bounty $3k] Research", 3000.0),
        ("[BOUNTY $2,500] x", 2500.0),
        ("[Bounty $1.5k] y", 1500.0),
        ("[Bounty $0.5M] z", 500000.0),
        ("Issue sin cifra", 0.0),
    ],
)
def test_titulo_con_marcador_si_es_dinero(extract, title, expected):
    assert extract([], "", title) == expected


def test_ano_en_titulo_sigue_siendo_0(extract):
    assert extract([], "", "hacktoberfest 2024") == 0.0
