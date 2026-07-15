"""Recon Engine — orchestrates subdomain discovery, endpoint collection, and tech detection."""

from __future__ import annotations

import logging
from typing import Any

from apps.aegis.models import AegisTarget, ScanResult
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.aegis.engines.recon")


class ReconEngine:
    """Coordinates recon tools to build a target's attack surface."""

    async def run(self, target_id: int) -> dict[str, Any]:
        """Run full recon pipeline against a target."""
        db = get_db_manager().get_session("aegis")
        try:
            target = db.query(AegisTarget).filter(AegisTarget.id == target_id).first()
            if not target:
                return {"error": "target not found"}

            target.status = "active"
            db.flush()

            domain = target.domain or target.name
            results: dict[str, dict] = {}

            # 1. Subdomain enumeration
            try:
                from cores.tools.subfinder import SubfinderTool

                subdomains = SubfinderTool().enumerate(domain)
                for r in subdomains:
                    db.add(
                        ScanResult(
                            target_id=target_id,
                            scan_type="subdomain",
                            tool="subfinder",
                            severity="info",
                            title=r.name or f"Subdomain: {r.target}",
                            endpoint=r.target,
                            evidence=str(r.evidence) if r.evidence else None,
                        )
                    )
                db.flush()
                results["subfinder"] = {"status": "ok", "count": len(subdomains)}
            except Exception as exc:
                logger.warning("subfinder failed: %s", exc)
                results["subfinder"] = {"status": "error", "error": str(exc)}

            # 2. HTTP probing
            try:
                from cores.tools.httpx import HttpxTool

                sub_rows = (
                    db.query(ScanResult).filter(ScanResult.target_id == target_id, ScanResult.tool == "subfinder").all()
                )
                probe_targets = [r.endpoint for r in sub_rows if r.endpoint] or [domain]
                endpoints = HttpxTool().probe(probe_targets)
                for r in endpoints:
                    db.add(
                        ScanResult(
                            target_id=target_id,
                            scan_type="probing",
                            tool="httpx",
                            severity="info",
                            title=r.name or f"Live: {r.target}",
                            endpoint=r.target,
                        )
                    )
                db.flush()
                results["httpx"] = {"status": "ok", "count": len(endpoints)}
            except Exception as exc:
                logger.warning("httpx failed: %s", exc)
                results["httpx"] = {"status": "error", "error": str(exc)}

            # 3. Crawling
            try:
                from cores.tools.extra import KatanaTool

                crawled = KatanaTool().crawl(domain)
                for r in crawled:
                    db.add(
                        ScanResult(
                            target_id=target_id,
                            scan_type="crawling",
                            tool="katana",
                            severity="info",
                            title=r.name or f"URL: {r.target}",
                            endpoint=r.target,
                        )
                    )
                db.flush()
                results["katana"] = {"status": "ok", "count": len(crawled)}
            except Exception as exc:
                logger.warning("katana failed: %s", exc)
                results["katana"] = {"status": "error", "error": str(exc)}

            # 4. Historical URLs
            try:
                from cores.tools.extra import GauTool

                urls = GauTool().discover_urls(domain)
                for r in urls:
                    db.add(
                        ScanResult(
                            target_id=target_id,
                            scan_type="urls",
                            tool="gau",
                            severity="info",
                            title=r.name or f"URL: {r.target}",
                            endpoint=r.target,
                        )
                    )
                db.flush()
                results["gau"] = {"status": "ok", "count": len(urls)}
            except Exception as exc:
                logger.warning("gau failed: %s", exc)
                results["gau"] = {"status": "error", "error": str(exc)}

            db.commit()
            return {
                "target_id": target_id,
                "target_name": target.name,
                "status": "completed",
                "results": results,
            }
        except Exception as exc:
            db.rollback()
            logger.error("Recon failed for target %d: %s", target_id, exc)
            return {"error": str(exc)}
        finally:
            db.close()
