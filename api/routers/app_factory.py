"""APP FACTORY API — validation experiments NEXA vs FOCUS.

POST /ingest: 1 evento desde landing estática (público, sin auth: la landing
  no tiene token; solo conteos, email solo en email_signup, jamás se expone).
POST /import: bulk [{experiment,event,...}] para volcar export Formspree/CSV.
GET /overview: conteos + Demand Score + veredicto (best-effort, nunca 500).
GET /experiments: registry estático (posicionamiento + pricing hipótesis).

CSRF: POST ingest/import son ingesta pública desde origen externo
(Netlify → localhost falla best-effort en prod, OK en beta local).
Se validan con 422 fail-closed, nunca ejecutan nada.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/app-factory", tags=["app-factory"])


class IngestIn(BaseModel):
    experiment: str = Field(min_length=1, max_length=32)
    event: str = Field(min_length=1, max_length=32)
    properties: dict[str, Any] = Field(default_factory=dict)
    session_id: str = Field(default="", max_length=64)
    email: str = Field(default="", max_length=254)


class ImportIn(BaseModel):
    events: list[IngestIn] = Field(max_length=5000)


@router.post("/ingest")
async def app_factory_ingest(payload: IngestIn) -> dict[str, Any]:
    """Ingiere 1 evento de validación. 422 si experimento/evento/email inválido."""
    from cores.app_factory.experiments import record_event

    try:
        return record_event(
            experiment=payload.experiment,
            event=payload.event,
            properties=payload.properties,
            session_id=payload.session_id,
            email=payload.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post("/import")
async def app_factory_import(payload: ImportIn) -> dict[str, Any]:
    """Bulk import (volcado Formspree). Best-effort por fila, reporta ok/errors."""
    from cores.app_factory.experiments import record_event

    ok, errors = 0, 0
    for item in payload.events:
        try:
            record_event(
                experiment=item.experiment,
                event=item.event,
                properties=item.properties,
                session_id=item.session_id,
                email=item.email,
            )
            ok += 1
        except ValueError:
            errors += 1
    return {"ok": ok, "errors": errors, "total": len(payload.events)}


@router.get("/overview")
async def app_factory_overview() -> dict[str, Any]:
    """Conteos + Demand Score + veredicto. Nunca 500, sin emails crudos."""
    from cores.app_factory.experiments import get_overview

    try:
        return get_overview()
    except Exception:  # noqa: BLE001 — contrato: overview jamás 500
        return {"generated_at": None, "total_events": 0, "experiments": {}}


@router.get("/experiments")
async def app_factory_experiments() -> dict[str, Any]:
    """Registry NEXA/FOCUS (posicionamiento + pricing hipótesis)."""
    from cores.app_factory.experiments import list_experiments

    items = list_experiments()
    return {"total": len(items), "experiments": items}
