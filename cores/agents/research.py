"""ResearchAgent — discovers targets, programs, and attack surface."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from cores.agents.base import BaseAgent
from cores.agents.types import AgentEvent, AgentId, EventType
from cores.recon.httpx_runner import HttpxRunner
from cores.recon.katana_runner import KatanaRunner
from cores.recon.subfinder_runner import SubfinderRunner

logger = logging.getLogger("ownex.agents.research")


class ResearchAgent(BaseAgent):
    """Discovers new targets, programs, endpoints, and attack surface.

    Delegates to the existing recon pipeline (subfinder, httpx, katana, etc.).
    Publishes discovered endpoints for validation.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_agent_id(self) -> AgentId:
        return AgentId.RESEARCH

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.RESEARCH_START]

    async def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.RESEARCH_START:
            await self._run_discovery(event)

    async def _run_discovery(self, event: AgentEvent) -> None:
        target_name = event.payload.get("target_name", "")
        target_id = event.payload.get("target_id", 0)
        pipeline_id = event.correlation_id
        logger.info("[RESEARCH] Starting discovery for %s", target_name)

        endpoints = []

        if not target_name:
            logger.warning("[RESEARCH] No target_name in event payload")
            self._publish_completion(target_id, target_name, 0, pipeline_id)
            return

        tmpdir = Path(tempfile.mkdtemp(prefix="research_"))

        # Phase 1: Subdomain enumeration
        try:
            sf = SubfinderRunner(output_dir=tmpdir)
            out = await sf.run_subfinder(target_name)
            subdomains = await sf.load_domains(out)
            for sd in subdomains or []:
                endpoints.append(
                    {
                        "path": f"https://{sd}/",
                        "method": "GET",
                        "params": {},
                        "source": "subfinder",
                    }
                )
            logger.info("[RESEARCH] subfinder found %d subdomains for %s", len(subdomains or []), target_name)
        except Exception as exc:
            logger.warning("[RESEARCH] subfinder failed: %s", exc)

        # Phase 2: HTTP probing
        if endpoints:
            try:
                input_file = tmpdir / "urls_for_httpx.txt"
                input_file.write_text("\n".join(e["path"] for e in endpoints[:50]))
                hx = HttpxRunner(output_dir=tmpdir)
                out = await hx.run_httpx(input_file)
                live = await hx.load_urls(out)
                live_set = set(live or [])
                endpoints = [e for e in endpoints if e["path"] in live_set]
                logger.info("[RESEARCH] httpx confirmed %d live endpoints", len(endpoints))
            except Exception as exc:
                logger.warning("[RESEARCH] httpx failed: %s", exc)

        # Phase 3: Path discovery
        if live_urls := list({e["path"] for e in endpoints[:20]}):
            try:
                kn = KatanaRunner(output_dir=tmpdir)
                for url in live_urls:
                    out = await kn.run_katana(url, out_file=f"katana_{target_name}.json")
                    if out.exists():
                        raw = out.read_text()
                        for line in raw.splitlines():
                            line = line.strip()
                            if line and line not in {e["path"] for e in endpoints}:
                                endpoints.append(
                                    {
                                        "path": line,
                                        "method": "GET",
                                        "params": {},
                                        "source": "katana",
                                    }
                                )
                logger.info("[RESEARCH] katana found additional paths")
            except Exception as exc:
                logger.warning("[RESEARCH] katana failed: %s", exc)

        self._publish_results(target_id, target_name, pipeline_id, endpoints)
        self._publish_completion(target_id, target_name, len(endpoints), pipeline_id)
        logger.info("[RESEARCH] Discovery completed: %d endpoints for %s", len(endpoints), target_name)

    def _publish_results(self, target_id: int, target_name: str, pipeline_id: str, endpoints: list) -> None:
        for ep in endpoints:
            self.emit(
                EventType.ENDPOINT_DISCOVERED,
                payload={
                    "target_id": target_id,
                    "target_name": target_name,
                    "endpoint": ep,
                    "pipeline_id": pipeline_id,
                },
                correlation_id=pipeline_id,
            )

    def _publish_completion(self, target_id: int, target_name: str, count: int, pipeline_id: str) -> None:
        self.emit(
            EventType.RESEARCH_COMPLETED,
            payload={
                "target_id": target_id,
                "target_name": target_name,
                "endpoints_count": count,
                "stage": "discovery",
                "next_stage": "validation",
                "pipeline_id": pipeline_id,
            },
            target=AgentId.COORDINATOR,
            correlation_id=pipeline_id,
        )
