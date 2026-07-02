"""
api.routers.zap — OWASP ZAP passive integration endpoints.

All ZAP scan operations are exclusively passive (spider + passive scan).
NO active scan endpoints are exposed here.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/zap", tags=["zap"])
LOG = logging.getLogger("rastro.api.zap")


class ZapScanRequest(BaseModel):
    target_url: str
    max_children: int = 10


class ZapTargetRequest(BaseModel):
    target_url: str


@router.get("/health")
async def zap_health():
    """Check if the ZAP daemon is running and responsive."""
    from cores.recon.zap_runner import ZapRunner
    runner = ZapRunner()
    try:
        status = await runner.health_check()
        return status
    finally:
        await runner.close()


@router.post("/spider")
async def spider_scan(req: ZapScanRequest):
    """Run ZAP spider (crawling only — NO active scanning).

    Discovers endpoints, forms, and parameters by navigating the
    application like a browser would. Does NOT send attack payloads.
    """
    from cores.recon.zap_runner import ZapConnectionError, ZapRunner
    runner = ZapRunner()
    try:
        result = await runner.spider_scan(req.target_url, req.max_children)
        return {
            "status": "completed",
            "urls_found": result["urls_found"],
            "url_count": result["url_count"],
            "scan_id": result["scan_id"],
        }
    except ZapConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        await runner.close()


@router.post("/passive-scan")
async def passive_scan(req: ZapTargetRequest):
    """Run passive scan analysis on a target URL.

    Reads ZAP's passive scan alerts: missing security headers,
    cookie flags, information disclosure, weak TLS, etc.
    All detected WITHOUT sending attack payloads.
    """
    from cores.recon.zap_runner import ZapConnectionError, ZapRunner, INSTALL_HINT
    runner = ZapRunner()
    try:
        health = await runner.health_check()
        if not health.get("running"):
            return {
                "status": "zap_not_available",
                "detail": "OWASP ZAP daemon no está corriendo",
                "install_hint": INSTALL_HINT.strip(),
                "alerts": [],
            }

        await runner.access_url(req.target_url)
        import asyncio
        await asyncio.sleep(3)
        alerts = await runner.passive_scan_results(req.target_url)
        return {
            "status": "completed",
            "target_url": req.target_url,
            "alerts": alerts,
            "alert_count": len(alerts),
        }
    except ZapConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        await runner.close()


@router.post("/alerts")
async def get_alerts(req: ZapTargetRequest, risk_level: str | None = None):
    """Get ZAP passive alerts, optionally filtered by risk level.

    Returns alerts normalized to the system's hypothesis format.
    """
    from cores.recon.zap_runner import ZapConnectionError, ZapRunner
    runner = ZapRunner()
    try:
        alerts = await runner.get_alerts(req.target_url, risk_level)
        return {
            "target_url": req.target_url,
            "alerts": alerts,
            "alert_count": len(alerts),
        }
    except ZapConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        await runner.close()


@router.post("/technologies")
async def get_technologies(req: ZapTargetRequest):
    """Get technologies detected by ZAP's passive fingerprinting."""
    from cores.recon.zap_runner import ZapConnectionError, ZapRunner
    runner = ZapRunner()
    try:
        technologies = await runner.get_technologies(req.target_url)
        return {
            "target_url": req.target_url,
            "technologies": technologies,
        }
    except ZapConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        await runner.close()


@router.post("/hypotheses/{target_id}")
async def generate_zap_hypotheses(target_id: int, req: ZapTargetRequest):
    """Run ZAP passive scan and generate didactic hypotheses from alerts.

    Returns enriched Hypothesis objects with:
      - what_is_this: plain-language explanation
      - how_to_verify: concrete step-by-step validation instructions
      - estimated difficulty / time
      - real-world impact explanation
    """
    from cores.recon.zap_runner import ZapConnectionError, ZapRunner
    from cores.engine.hypothesis.zap_generator import generate_from_zap_alerts

    runner = ZapRunner()
    try:
        health = await runner.health_check()
        if not health.get("running"):
            return {
                "status": "zap_not_available",
                "detail": "OWASP ZAP daemon no está corriendo. Instálalo e inícialo con: zap.sh -daemon -port 8090 -config api.disablekey=true",
                "hypotheses": [],
                "total": 0,
            }

        await runner.access_url(req.target_url)
        import asyncio
        await asyncio.sleep(3)
        alerts = await runner.passive_scan_results(req.target_url)

        hypotheses = generate_from_zap_alerts(
            target_id=target_id,
            target_name=req.target_url,
            zap_alerts=alerts,
        )

        from cores.engine.hypothesis.models import Hypothesis
        result = []
        for h in hypotheses:
            result.append({
                "id": h.id,
                "vulnerability_type": h.vulnerability_type.value,
                "target_id": h.target_id,
                "target_name": h.target_name,
                "endpoint": h.endpoint,
                "likelihood": h.likelihood,
                "impact": h.impact,
                "confidence": h.confidence,
                "priority_score": h.priority_score,
                "evidence": h.evidence,
                "reasoning": h.reasoning,
                "suggested_actions": list(h.suggested_actions),
                "source": h.source.value,
                "vector": h.vector,
                "what_is_this": h.what_is_this,
                "why_suspected": h.why_suspected,
                "real_world_impact": h.real_world_impact,
                "how_to_verify": list(h.how_to_verify),
                "estimated_difficulty": h.estimated_difficulty,
                "estimated_time_minutes": h.estimated_time_minutes,
                "estimated_reward_range": h.estimated_reward_range,
            })

        return {
            "status": "completed",
            "target_url": req.target_url,
            "hypotheses": result,
            "total": len(result),
        }

    except ZapConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        await runner.close()
