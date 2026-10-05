"""Guard: el banco de entregables sólo contiene trabajo PROGRAMABLE.

Contexto 2026-09-30: el WorkBank mezclaba código real con trabajo que no se
entrega con un pull request — research, QA manual de un producto, carga de
datos y artículos de blog. Un bounty de "$3.000 research" llegó a ser el 34%
del pipeline y tapaba el trabajo programable real.

El filtro NO usa `category` (el radar conserva esas fuentes): usa el
contenido, porque un bounty legítimo que dice "security research" sí es
trabajo técnico. Ante duda deja pasar: es preferible un falso positivo
barato que perder dinero real.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cores.direct_work_engine.workbank import _is_programmable_dev_work


def dev(title: str, description: str = "") -> bool:
    return _is_programmable_dev_work(SimpleNamespace(title=title, description=description))


# ══════════════════════════════════════════════════════════════════
# Trabajo NO programable — no entra al banco de entregables
# ══════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "title",
    [
        "[Bounty $3k] [ Research ] Collect and compare AI-generated AGI architecture proposals",
        "Frantic bounty #135: Run an Ausca Agent Inbox end to end and report the process",
        "Frantic bounty #132: Run Ausca Document Analysis end to end and report the process",
        "Frantic bounty #120: Add a valuable startup offer to Sourcey",
        "[BOUNTY] Write a Blog Post About Proof-of-Antiquity — 15 RTC",
        "Survey the developer community and report the process",
    ],
)
def test_trabajo_no_programable_no_entra(title):
    assert dev(title) is False, f"{title!r} no se entrega con un PR"


# ══════════════════════════════════════════════════════════════════
# Trabajo programable real — entra
# ══════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "title",
    [
        "[Bounty: $1,250] Optimize Subgraph Isomorphism to Strict O(N) Deterministic Space",
        "[PAID BOUNTY - $960] Attachment Summarizer Service",
        "[PAID BOUNTY - $750] Email Threads API",
        "[PAID BOUNTY - $660] Enhanced Image Preview",
        "[PAID BOUNTY - $660] Note Locking - Biometrics/PIN",
        "[PAID BOUNTY - $440] Messenger Group Chat Poll Creation & Voting UI",
        "[PAID BOUNTY - $330] Email Inbox Classic View Page UI",
        "[BOUNTY $200] WORKFLOW: n8n + Claude Code — automated weekly dev summary",
        "[BOUNTY $50] SKILL: Generate a structured CHANGELOG from git",
    ],
)
def test_trabajo_programable_entra(title):
    assert dev(title) is True, f"{title!r} sí es un PR y debe entrar"


# ══════════════════════════════════════════════════════════════════
# Orden de precedencia: "research" no anula "security research"
# ══════════════════════════════════════════════════════════════════


def test_security_research_no_se_descarta():
    """Un bounty de bug bounty que dice 'security research' SÍ es trabajo técnico."""
    assert dev("Fix a security research vulnerability in the parser (bounty $2000)") is True


def test_el_veto_no_dev_gana_al_dev():
    """ "Add a valuable startup offer" contiene 'add ' (señal dev) pero es carga
    de datos: el veto no-dev se evalúa PRIMERO."""
    assert dev("Add a valuable startup offer to Sourcey") is False


def test_titulo_sin_señal_no_entra_pero_no_se_pierde():
    """Sin señal explícita de trabajo programable NO entra al banco.

    No se pierde: queda en el radar con motivo `not_programnable_dev_work`
    visible. Es preferible a declarar "ready" algo que quizá no sea código.
    """
    assert dev("Trabajo pendiente de definir") is False
