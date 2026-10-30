"""Auto-dispute - integración HackerOne/Gitcoin API para reclamos de pago."""

import contextlib
import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

DISPUTE_DIR = Path.home() / ".rastro" / "disputes"
DISPUTE_DIR.mkdir(parents=True, exist_ok=True)

# Configuración de APIs (se cargan desde env)
H1_API_BASE = os.getenv("HACKERONE_API_BASE", "https://api.hackerone.com/v1")
H1_API_USER = os.getenv("HACKERONE_API_USER")
H1_API_TOKEN = os.getenv("HACKERONE_API_TOKEN")

GITC_API_BASE = os.getenv("GITCOIN_API_BASE", "https://api.gitcoin.co")
GITC_API_TOKEN = os.getenv("GITCOIN_API_TOKEN")


class DisputeClient:
    """Cliente para abrir/gestionar disputas de pago en plataformas de bounties."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _h1_auth(self) -> httpx.BasicAuth | None:
        if H1_API_USER and H1_API_TOKEN:
            return httpx.BasicAuth(H1_API_USER, H1_API_TOKEN)
        return None

    async def _gitc_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {GITC_API_TOKEN}"} if GITC_API_TOKEN else {}

    # ── HackerOne ──
    async def h1_open_dispute(self, report_id: str, reason: str, evidence: dict[str, Any]) -> dict[str, Any]:
        """Abrir disputa en HackerOne por pago no recibido."""
        auth = await self._h1_auth()
        if not auth:
            return {"success": False, "error": "H1 credentials not configured (HACKERONE_API_USER/TOKEN)"}

        # H1 usa GraphQL; aquí simplificamos con REST endpoint si existe
        # En realidad H1 disputa se maneja via report comments + mediation request
        payload = {
            "data": {
                "type": "report-comment",
                "attributes": {
                    "message": f"[AUTO-DISPUTA OWNEX] Pago no recibido. RazÃ³n: {reason}\nEvidencia: {json.dumps(evidence)}",
                    "internal": False,
                },
                "relationships": {
                    "report": {"data": {"type": "report", "id": report_id}},
                },
            }
        }
        try:
            r = await self.client.post(f"{H1_API_BASE}/reports/{report_id}/comments", json=payload, auth=auth)
            r.raise_for_status()
            return {
                "success": True,
                "platform": "hackerone",
                "dispute_id": r.json().get("data", {}).get("id"),
                "raw": r.json(),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "platform": "hackerone"}

    async def h1_check_report(self, report_id: str) -> dict[str, Any]:
        """Consultar estado de reporte en H1."""
        auth = await self._h1_auth()
        if not auth:
            return {"success": False, "error": "H1 credentials not configured"}
        try:
            r = await self.client.get(f"{H1_API_BASE}/reports/{report_id}", auth=auth)
            r.raise_for_status()
            return {"success": True, "data": r.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Gitcoin ──
    async def gitc_open_dispute(self, bounty_id: str, reason: str, evidence: dict[str, Any]) -> dict[str, Any]:
        """Abrir disputa en Gitcoin (bounty no pagado)."""
        if not GITC_API_TOKEN:
            return {"success": False, "error": "Gitcoin token not configured (GITCOIN_API_TOKEN)"}

        # Gitcoin usa GraphQL; este es endpoint simplificado
        mutation = """
        mutation CreateDispute($bountyId: ID!, $reason: String!, $evidence: JSON!) {
            createDispute(bountyId: $bountyId, reason: $reason, evidence: $evidence) {
                id
                status
            }
        }
        """
        try:
            r = await self.client.post(
                f"{GITC_API_BASE}/graphql",
                json={"query": mutation, "variables": {"bountyId": bounty_id, "reason": reason, "evidence": evidence}},
                headers=await self._gitc_headers(),
            )
            r.raise_for_status()
            return {
                "success": True,
                "platform": "gitcoin",
                "dispute_id": r.json().get("data", {}).get("createDispute", {}).get("id"),
                "raw": r.json(),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "platform": "gitcoin"}

    # ── Generic local record ──
    def save_local_dispute(
        self, platform: str, finding_id: str, reason: str, evidence: dict[str, Any], remote_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Guardar disputa local con hash inmutable."""
        dispute_id = f"dsp_{uuid.uuid4().hex[:12]}"
        payload = {
            "dispute_id": dispute_id,
            "platform": platform,
            "finding_id": finding_id,
            "reason": reason,
            "evidence": evidence,
            "remote_result": remote_result,
            "created_at": datetime.now(UTC).isoformat(),
            "sha256": hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()[:16],
            "status": "opened" if remote_result.get("success") else "failed",
        }
        (DISPUTE_DIR / f"{dispute_id}.json").write_text(json.dumps(payload, indent=2))
        return payload

    def list_local_disputes(self) -> list[dict[str, Any]]:
        disputes = []
        for f in DISPUTE_DIR.glob("dsp_*.json"):
            with contextlib.suppress(Exception):
                disputes.append(json.loads(f.read_text()))
        disputes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return disputes


# Singleton
_dispute_client: DisputeClient | None = None


def get_dispute_client() -> DisputeClient:
    global _dispute_client
    if _dispute_client is None:
        _dispute_client = DisputeClient()
    return _dispute_client


def open_auto_dispute(
    platform: str,
    finding_id: str,
    reason: str,
    evidence: dict[str, Any],
    platform_ref: str | None = None,  # report_id (H1) or bounty_id (Gitcoin)
) -> dict[str, Any]:
    """Función sÃ­ncrona wrapper para abrir disputa (usa asyncio)."""
    import asyncio

    client = get_dispute_client()

    async def _run():
        if platform.lower() == "hackerone":
            return await client.h1_open_dispute(platform_ref or finding_id, reason, evidence)
        elif platform.lower() == "gitcoin":
            return await client.gitc_open_dispute(platform_ref or finding_id, reason, evidence)
        else:
            return {"success": False, "error": f"Platform {platform} not supported"}

    result = asyncio.run(_run())
    local = client.save_local_dispute(platform, finding_id, reason, evidence, result)
    return {"remote": result, "local": local}
