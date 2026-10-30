"""Automation-as-a-Service — micro-workflows vendibles ($0 + n8n/Playwright/Python).

Catálogo de ofertas con setup fee + MRR. La ejecución reusa
AutonomousWorkflow + BrowserAgent existentes (no se duplica).
Aquí solo vive el packaging comercial: oferta, precio, entrega, gate humano.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("ownex.automation_service")

_OFFERS: list[dict[str, object]] = [
    {
        "id": "scrape_to_sheets",
        "title": "Scrapeo directorio -> Google Sheets",
        "setup_usd": 150.0,
        "mrr_usd": 50.0,
        "stack": "playwright + python",
        "deliverable": "CSV/Sheets + run semanal",
    },
    {
        "id": "form_filler",
        "title": "Carga masiva de formularios/portales",
        "setup_usd": 200.0,
        "mrr_usd": 80.0,
        "stack": "browseragent + vault",
        "deliverable": "Bot + log de ejecuciones",
    },
    {
        "id": "report_bot",
        "title": "Reportes automáticos semanales",
        "setup_usd": 120.0,
        "mrr_usd": 40.0,
        "stack": "python + scheduler",
        "deliverable": "PDF/Email + dashboard",
    },
    {
        "id": "lead_bot",
        "title": "Lead capture + WhatsApp follow-up",
        "setup_usd": 300.0,
        "mrr_usd": 100.0,
        "stack": "n8n + wa-cloud-api",
        "deliverable": "Pipeline + funnel en OWNEX",
    },
    {
        "id": "catalog_sync",
        "title": "Sync catálogo proveedor -> Meli/IG",
        "setup_usd": 250.0,
        "mrr_usd": 60.0,
        "stack": "ecommerce engine",
        "deliverable": "Sync diario + alertas",
    },
]


def offer_catalog() -> list[dict[str, object]]:
    return [dict(o) for o in _OFFERS]


def quote_offer(offer_id: str, complexity_mult: float = 1.0) -> dict[str, object] | None:
    offer = next((o for o in _OFFERS if o["id"] == offer_id), None)
    if not offer:
        return None
    try:
        mult = max(0.5, min(3.0, float(complexity_mult or 1.0)))
    except (TypeError, ValueError):
        mult = 1.0
    setup = round(float(offer["setup_usd"]) * mult, 2)  # type: ignore[arg-type]
    mrr = round(float(offer["mrr_usd"]) * mult, 2)  # type: ignore[arg-type]
    return {
        "offer_id": offer_id,
        "title": offer["title"],
        "setup_usd": setup,
        "mrr_usd": mrr,
        "stack": offer["stack"],
        "note": "Deploy tras seña 50%. Acceso del cliente por credenciales en vault, nunca en chat.",
    }
