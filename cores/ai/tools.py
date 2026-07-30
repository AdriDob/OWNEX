from __future__ import annotations

import logging
from typing import Any

from database import db, models

logger = logging.getLogger("ownex.ai.tools")

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_top_bounties",
            "description": "Devuelve las oportunidades de bounty mejor rankeadas",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 5},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_earnings_summary",
            "description": "Devuelve el resumen de ganancias del usuario: total, pendiente, por plataforma",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_report_status",
            "description": "Devuelve el estado de los reportes en el pipeline: cuantos en cada etapa (detectado, validado, confirmado, reportado) y total estimado",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_target_details",
            "description": "Devuelve detalles de un target/programa específico",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nombre o ID del target a buscar",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Busca información actualizada en internet. Usar cuando la pregunta sea sobre noticias, cambios recientes en programas, o información que no está en la base de datos local",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La consulta de búsqueda",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def _get_session():
    db.init_db()
    return db.SessionLocal()


async def execute_tool(name: str, args: dict) -> dict:
    logger.info("Executing tool: %s with args: %s", name, args)
    if name == "get_top_bounties":
        return _get_top_bounties(args.get("limit", 5))
    if name == "get_earnings_summary":
        return _get_earnings_summary()
    if name == "get_report_status":
        return _get_report_status()
    if name == "get_target_details":
        return _get_target_details(args.get("name", ""))
    if name == "web_search":
        return await _web_search(args.get("query", ""))
    return {"error": f"Tool desconocida: {name}"}


def _get_top_bounties(limit: int = 5) -> dict:
    session = _get_session()
    try:
        from cores.targets.models import TargetIntel

        targets = session.query(models.Target).limit(limit * 3).all()
        intel_map = {}
        if targets:
            target_ids = [t.id for t in targets]
            for intel in session.query(TargetIntel).filter(TargetIntel.id.in_(target_ids)).all():
                intel_map[intel.id] = intel

        bounties: list[dict[str, Any]] = []
        for t in targets:
            findings = session.query(models.Finding).filter(models.Finding.target_id == t.id).all()
            intel = intel_map.get(t.id)
            opp_score = round((intel.opportunity_score or 0) / 10, 1) if intel else 0
            bounties.append(
                {
                    "id": t.id,
                    "name": t.name or f"Target #{t.id}",
                    "domain": t.domain or "",
                    "opportunity_score": opp_score,
                    "findings_count": len(findings),
                    "competition_score": int(intel.competition_score or 0) if intel else 0,
                    "freshness_score": int(intel.freshness_score or 0) if intel else 50,
                }
            )
            if len(bounties) >= limit:
                break
        bounties.sort(key=lambda x: x["opportunity_score"], reverse=True)
        return {"bounties": bounties[:limit]}
    finally:
        session.close()


def _get_earnings_summary() -> dict:
    session = _get_session()
    try:
        total_rewards = 0
        pending_rewards = 0
        by_status: dict[str, int] = {}
        for r in session.query(models.Report).all():
            payout = r.estimated_reward or 0
            total_rewards += payout
            status = r.status or "draft"
            by_status[status] = by_status.get(status, 0) + 1
            if status in ("draft", "pending"):
                pending_rewards += payout

        paid_count = by_status.get("paid", 0)

        confirmed_verdicts = session.query(models.Verdict).filter(models.Verdict.status == "confirmed").count()

        return {
            "total_rewards": total_rewards,
            "pending_rewards": pending_rewards,
            "paid_count": paid_count,
            "confirmed_verdicts": confirmed_verdicts,
            "reports_by_status": by_status,
            "platforms": {},
        }
    finally:
        session.close()


def _get_report_status() -> dict:
    session = _get_session()
    try:
        from api.services.data_service import get_pipeline_stages

        stages = get_pipeline_stages()
        total = sum(len(v) for v in stages.values())

        verdict_counts = {
            "detected": session.query(models.Verdict).filter(models.Verdict.status == "detected").count(),
            "validated": session.query(models.Verdict).filter(models.Verdict.status == "validated").count(),
            "confirmed": session.query(models.Verdict).filter(models.Verdict.status == "confirmed").count(),
            "reported": session.query(models.Verdict).filter(models.Verdict.status == "reported").count(),
            "inconclusive": session.query(models.Verdict).filter(models.Verdict.status == "inconclusive").count(),
        }
        return {
            "pipeline_stages": {k: len(v) for k, v in stages.items()},
            "verdict_counts": verdict_counts,
            "total": total,
        }
    finally:
        session.close()


def _get_target_details(name: str) -> dict:
    session = _get_session()
    try:
        t = (
            session.query(models.Target)
            .filter((models.Target.name.ilike(f"%{name}%")) | (models.Target.id == _parse_int(name)))
            .first()
        )
        if not t:
            return {"error": f"No se encontró target: {name}"}

        endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == t.id).all()
        findings = session.query(models.Finding).filter(models.Finding.target_id == t.id).all()
        confirmed = (
            session.query(models.Verdict)
            .filter(
                models.Verdict.endpoint_id.in_([ep.id for ep in endpoints]),
                models.Verdict.status == "confirmed",
            )
            .count()
        )

        from cores.targets.models import TargetIntel

        intel = session.query(TargetIntel).filter(TargetIntel.id == t.id).first()

        return {
            "id": t.id,
            "name": t.name,
            "domain": t.domain or "",
            "endpoints_count": len(endpoints),
            "findings_count": len(findings),
            "confirmed_findings": confirmed,
            "opportunity_score": round((intel.opportunity_score or 0) / 10, 1) if intel else 0,
            "competition_score": int(intel.competition_score or 0) if intel else 0,
            "freshness_score": int(intel.freshness_score or 0) if intel else 50,
        }
    finally:
        session.close()


async def _web_search(query: str) -> dict:
    try:
        import httpx
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
            )
        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict[str, str]] = []
        for r in soup.select(".result__body")[:5]:
            title_el = r.select_one(".result__title")
            snippet_el = r.select_one(".result__snippet")
            link_el = r.select_one(".result__url")
            if title_el and snippet_el:
                results.append(
                    {
                        "title": title_el.get_text(strip=True),
                        "snippet": snippet_el.get_text(strip=True),
                        "url": link_el.get_text(strip=True) if link_el else "",
                    }
                )
        return {"query": query, "results": results}
    except Exception as e:
        logger.warning("Web search failed: %s", e)
        return {"query": query, "results": [], "error": str(e)}


def _parse_int(s: str) -> int:
    try:
        return int(s)
    except (ValueError, TypeError):
        return -1
