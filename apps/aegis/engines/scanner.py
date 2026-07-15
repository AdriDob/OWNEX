"""Scanner Engine — runs vulnerability scanning using Nuclei, FFUF, Dalfox, etc."""

from __future__ import annotations

import logging
from typing import Any

from apps.aegis.engines.recon import ReconEngine
from apps.aegis.models import AegisTarget, ScanResult, VulnFinding
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.aegis.engines.scanner")


class ScannerEngine:
    """Full vulnerability scanner — runs after recon to find exploitable issues."""

    async def run_full(self, target_id: int) -> dict[str, Any]:
        """Run recon + full vulnerability scan."""
        db = get_db_manager().get_session("aegis")
        try:
            target = db.query(AegisTarget).filter(AegisTarget.id == target_id).first()
            if not target:
                return {"error": "target not found"}

            target.status = "active"
            db.flush()

            # 1. Recon first
            recon = ReconEngine()
            recon_result = await recon.run(target_id)

            # 2. Collect all live endpoints for scanning
            endpoints = (
                db.query(ScanResult)
                .filter(
                    ScanResult.target_id == target_id,
                    ScanResult.tool.in_(["httpx", "katana", "gau"]),
                )
                .all()
            )
            endpoint_urls = list({r.endpoint for r in endpoints if r.endpoint})

            scan_results: dict[str, dict] = {}

            # 3. Nuclei vulnerability scan
            if endpoint_urls:
                try:
                    from cores.tools.nuclei import NucleiTool

                    findings = NucleiTool().scan(
                        targets=endpoint_urls[:50],  # limit to first 50
                        severity="medium",
                    )
                    for r in findings:
                        self._save_finding(db, target_id, r)
                    db.flush()
                    scan_results["nuclei"] = {"status": "ok", "count": len(findings)}
                except Exception as exc:
                    logger.warning("nuclei failed: %s", exc)
                    scan_results["nuclei"] = {"status": "error", "error": str(exc)}

            # 4. FFUF fuzzing on primary domain
            try:
                from cores.tools.extra import FfufTool

                primary_url = f"https://{target.domain or target.name}"
                fuzz_results = FfufTool().discover_paths(primary_url, profile="fast")
                for r in fuzz_results:
                    db.add(
                        ScanResult(
                            target_id=target_id,
                            scan_type="fuzz",
                            tool="ffuf",
                            severity="medium",
                            title=r.name or f"Path: {r.target}",
                            endpoint=r.target,
                        )
                    )
                db.flush()
                scan_results["ffuf"] = {"status": "ok", "count": len(fuzz_results)}
            except Exception as exc:
                logger.warning("ffuf failed: %s", exc)
                scan_results["ffuf"] = {"status": "error", "error": str(exc)}

            # 5. Dalfox XSS scan on discovered endpoints
            if endpoint_urls:
                try:
                    from cores.tools.extra import DalfoxTool

                    xss_results = DalfoxTool().scan_urls(endpoint_urls[:10])  # limit to first 10
                    for r in xss_results:
                        self._save_finding(db, target_id, r)
                    db.flush()
                    scan_results["dalfox"] = {"status": "ok", "count": len(xss_results)}
                except Exception as exc:
                    logger.warning("dalfox failed: %s", exc)
                    scan_results["dalfox"] = {"status": "error", "error": str(exc)}

            db.commit()
            return {
                "target_id": target_id,
                "target_name": target.name,
                "status": "completed",
                "recon": recon_result.get("results", {}),
                "scans": scan_results,
            }
        except Exception as exc:
            db.rollback()
            logger.error("Full scan failed for target %d: %s", target_id, exc)
            return {"error": str(exc)}
        finally:
            db.close()

    def _save_finding(self, db, target_id: int, r) -> None:
        """Save a UnifiedResult as both ScanResult and VulnFinding."""
        severity = r.severity or "medium"
        db.add(
            ScanResult(
                target_id=target_id,
                scan_type="vuln",
                tool=r.source,
                severity=severity,
                title=r.name or f"Finding: {r.target}",
                endpoint=r.target,
                evidence=str(r.evidence) if r.evidence else None,
                raw_output=r.raw,
            )
        )
        db.flush()

        if severity in ("critical", "high", "medium"):
            cve = ""
            cwe = ""
            tags = r.tags or []
            for t in tags:
                if t.startswith("cve:"):
                    cve = t.replace("cve:", "")
                if t.startswith("cwe:"):
                    cwe = t.replace("cwe:", "")
            db.add(
                VulnFinding(
                    target_id=target_id,
                    scan_id=0,
                    title=r.name or f"Finding: {r.target}",
                    severity=severity,
                    cve=cve or None,
                    cwe=cwe or None,
                    description=r.description,
                )
            )
