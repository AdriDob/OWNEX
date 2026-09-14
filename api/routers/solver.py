"""Solver API — un solo endpoint para resolver cualquier duda, problema o tarea.

Delega en cores.solver.solver (que a su vez reutiliza OAR chat, opencode bridge,
knowledge index, workbank y daily-digest). No duplica motores: clasifica
intención → ensambla contexto real → responde → next_action con superficie.
Acciones irreversibles → Human Gate (nunca ejecuta acá).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.solver.solver import solve

router = APIRouter(prefix="/api/solve", tags=["solver"])


class SolveRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    persona: str = "copilot"


@router.post("")
async def solve_endpoint(body: SolveRequest) -> dict[str, Any]:
    """Resuelve cualquier consulta: respuesta + contexto + next_action + superficies."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    try:
        return await solve(body.message, history=body.history, persona=body.persona)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — solver never 500s unseen
        raise HTTPException(status_code=500, detail=f"solver error: {exc}") from exc
