import asyncio
import json
import logging
from collections.abc import Coroutine, Iterable
from pathlib import Path
from typing import Any

from .amass_runner import AmassRunner
from .crtsh_runner import CrtshRunner
from .ffuf_runner import FfufRunner
from .gau_runner import GauRunner
from .httpx_runner import HttpxRunner
from .katana_runner import KatanaRunner
from .naabu_runner import NaabuRunner
from .nuclei_runner import NucleiRunner
from .parser import EndpointParser
from .subfinder_runner import SubfinderRunner
from .wayback_runner import WaybackRunner
from .whois_runner import WhoisRunner

logger = logging.getLogger("ownex.recon")


class ReconRunner:
    def __init__(self, target_root: Path):
        self.target_root = target_root

        self.recon_dir = self.target_root / "recon"
        self.endpoints_dir = self.target_root / "endpoints"
        self.analysis_dir = self.target_root / "analysis"
        self.logs_dir = self.target_root / "logs"
        self.screenshots_dir = self.target_root / "screenshots"

        for folder in [
            self.recon_dir,
            self.endpoints_dir,
            self.analysis_dir,
            self.logs_dir,
            self.screenshots_dir,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

        self.subfinder = SubfinderRunner(self.recon_dir)
        self.amass = AmassRunner(self.recon_dir)
        self.naabu = NaabuRunner(self.recon_dir)
        self.httpx = HttpxRunner(self.recon_dir)
        self.katana = KatanaRunner(self.recon_dir)
        self.wayback = WaybackRunner(self.recon_dir)
        self.nuclei = NucleiRunner(self.recon_dir)
        self.gau = GauRunner(self.recon_dir)
        self.ffuf = FfufRunner(self.recon_dir)
        self.crtsh = CrtshRunner(self.recon_dir)
        self.whois = WhoisRunner(self.recon_dir)

        self.parser = EndpointParser()

    async def _safe_run_tool(
        self,
        tool_name: str,
        coroutine: Coroutine,
        timeout: int = 120,
    ) -> Any:
        try:
            result = await asyncio.wait_for(
                coroutine,
                timeout=timeout,
            )

            if result is None:
                logger.warning("Tool %s returned no result", tool_name)
            else:
                result_path = Path(result) if isinstance(result, (str, Path)) else None
                if result_path and result_path.exists() and result_path.stat().st_size == 0:
                    logger.warning("Tool %s produced empty output: %s", tool_name, result_path)
                else:
                    logger.info("Tool completed: %s", tool_name)

            return result

        except TimeoutError:
            logger.error("Tool timeout: %s", tool_name)
            return None

        except Exception as e:
            logger.error("Tool %s failed: %s", tool_name, e)
            return None

    async def run_pipeline(
        self,
        domain: str,
        mode: str = "FAST",
    ) -> dict[str, str]:

        domain = domain.strip()

        if not domain:
            raise ValueError("Domain is required for recon.")

        outputs: dict[str, str] = {}
        source_files = []

        logger.info(f"Starting recon pipeline for {domain} in mode {mode}")

        # SUBFINDER

        subfinder_path = await self._safe_run_tool(
            "subfinder",
            self.subfinder.run_subfinder(
                domain,
                "subfinder.txt",
            ),
            timeout=120,
        )

        if subfinder_path:
            outputs["subfinder"] = str(subfinder_path)

        # AMASS — deep enumeration for DEEP/API modes
        if mode.upper() in {"DEEP", "API"} and self.amass.is_available():
            amass_results = await self._safe_run_tool(
                "amass",
                self.amass.enum_passive(domain, timeout=180),
                timeout=240,
            )
            if amass_results:
                amass_subs = self.amass.parse_subdomains(amass_results)
                amass_file = self.recon_dir / "amass_subs.txt"
                amass_file.write_text("\n".join(amass_subs))
                outputs["amass"] = str(amass_file)
                source_files.append(str(amass_file))
                logger.info("Amass: %d additional subdomains found", len(amass_subs))

        # NAABU — port scan (DEEP/API only)
        if mode.upper() in {"DEEP", "API"}:
            naabu_input = self.recon_dir / "naabu_input.txt"
            seen_hosts: set[str] = set()
            candidates: list[str] = []
            if subfinder_path:
                p = Path(subfinder_path) if isinstance(subfinder_path, str) else subfinder_path
                if p and p.exists():
                    candidates.append(str(subfinder_path))
            naabu_input.write_text("")
            for sf in candidates:
                p = Path(sf)
                if p.exists():
                    for line in p.read_text().splitlines():
                        host = line.strip()
                        if host and host not in seen_hosts:
                            seen_hosts.add(host)
            if seen_hosts:
                naabu_input.write_text("\n".join(sorted(seen_hosts)))
                naabu_path = await self._safe_run_tool(
                    "naabu",
                    self.naabu.run_naabu(
                        naabu_input,
                        "naabu.json",
                        ports="top-1000",
                    ),
                    timeout=300,
                )
                if naabu_path:
                    open_ports = self.naabu.load_open_ports(naabu_path)
                    logger.info("Naabu: %d open ports found", len(open_ports))
                    if open_ports:
                        from .dedup import dedup_naabu_ports

                        deduped = dedup_naabu_ports(open_ports)
                        httpx_targets = self.naabu.as_httpx_targets(deduped)
                        httpx_input_file = self.recon_dir / "naabu_httpx_input.txt"
                        httpx_input_file.write_text("\n".join(httpx_targets))
                        outputs["naabu"] = str(naabu_path)
                        outputs["naabu_httpx_input"] = str(httpx_input_file)
                        logger.info("Naabu → httpx: %d targets", len(httpx_targets))

        # PARALLEL TASKS

        crtsh_task = asyncio.create_task(
            self._safe_run_tool(
                "crtsh",
                self.crtsh.run_crtsh(domain, "crtsh.txt"),
                timeout=60,
            )
        )

        whois_task = asyncio.create_task(
            self._safe_run_tool(
                "whois",
                self.whois.run_whois(domain, "whois.txt"),
                timeout=30,
            )
        )

        wayback_task = asyncio.create_task(
            self._safe_run_tool(
                "wayback",
                self.wayback.run_wayback(
                    domain,
                    "wayback.txt",
                ),
                timeout=180,
            )
        )

        # ROUTER — intelligent recon before katana

        router_path = None
        try:
            from core.recon.router import ReconRouter

            router = ReconRouter()
            router_result = router.route(domain, output_dir=self.recon_dir)
            if router_result.endpoints_found:
                router_out = self.recon_dir / "router_endpoints.json"
                with router_out.open("w", encoding="utf-8") as f:
                    json.dump(router_result.endpoints_found, f, indent=2, ensure_ascii=False)
                router_path = str(router_out)
                outputs["router"] = router_path
                source_files.append(router_path)
                logger.info(
                    "[ROUTER] %s: %d tech-specific endpoints found (tech=%s)",
                    domain,
                    len(router_result.endpoints_found),
                    router_result.tech_summary,
                )
        except Exception:
            logger.warning("[ROUTER] Failed for %s, falling back to katana", domain, exc_info=True)
            router_path = None

        katana_task = asyncio.create_task(
            self._safe_run_tool(
                "katana",
                self.katana.run_katana(
                    domain,
                    "katana.json",
                ),
                timeout=300,
            )
        )

        # HTTPX ONLY FOR DEEP/API

        if mode.upper() in {"DEEP", "API"}:
            naabu_httpx = outputs.get("naabu_httpx_input")
            httpx_input = naabu_httpx if naabu_httpx else (subfinder_path if subfinder_path else domain)

            httpx_path = await self._safe_run_tool(
                "httpx",
                self.httpx.run_httpx(
                    Path(httpx_input),
                    "httpx.json",
                ),
                timeout=180,
            )

            if httpx_path:
                outputs["httpx"] = str(httpx_path)
                source_files.append(httpx_path)

        # WAIT TASKS

        wayback_path = await wayback_task

        if wayback_path:
            outputs["wayback"] = str(wayback_path)
            source_files.append(wayback_path)

        katana_path = await katana_task

        if katana_path:
            outputs["katana"] = str(katana_path)
            source_files.append(katana_path)

        # CRT.SH + WHOIS

        crtsh_path = await crtsh_task
        if crtsh_path:
            outputs["crtsh"] = str(crtsh_path)
            source_files.append(crtsh_path)

        whois_path = await whois_task
        if whois_path:
            outputs["whois"] = str(whois_path)
            source_files.append(whois_path)

        # NORMALIZATION

        normalized_path = self.endpoints_dir / "normalized_endpoints.json"

        parser_output = self.parser.parse_files(
            [Path(p) for p in source_files if p],
            normalized_path,
        )

        outputs["normalized_endpoints"] = str(parser_output)

        # LOAD NORMALIZED ENDPOINTS SAFELY

        endpoint_entries = []

        if parser_output.exists():
            try:
                with parser_output.open(
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as file:
                    endpoint_entries = json.load(file)

                    if not isinstance(
                        endpoint_entries,
                        list,
                    ):
                        logger.warning("normalized_endpoints.json is not a list")
                        endpoint_entries = []

            except json.JSONDecodeError as exc:
                logger.error(f"Invalid normalized endpoints JSON: {exc}")

            except Exception as exc:
                logger.error(f"Failed reading normalized endpoints: {exc}")

        logger.info(f"Normalized endpoints: {len(endpoint_entries)}")

        # NUCLEI VULNERABILITY SCAN (post-recon)

        if endpoint_entries and mode.upper() in {"DEEP", "API"}:
            targets_file = self.recon_dir / "nuclei_targets.txt"
            urls = [
                f"{ep.get('url', ep.get('path', ''))}" for ep in endpoint_entries if ep.get("url") or ep.get("path")
            ]
            if urls:
                targets_file.write_text("\n".join(urls))
                nuclei_path = await self._safe_run_tool(
                    "nuclei",
                    self.nuclei.run_nuclei(
                        targets_file,
                        "nuclei.json",
                        severity="medium,high,critical",
                    ),
                    timeout=300,
                )
                if nuclei_path:
                    outputs["nuclei"] = str(nuclei_path)
                    findings = await self.nuclei.load_findings(nuclei_path)
                    logger.info("nuclei findings: %d", len(findings))

        # SUMMARY

        summary_path = self.analysis_dir / "summary.json"

        summary_data = {
            "domain": domain,
            "mode": mode.upper(),
            "outputs": outputs,
            "endpoint_count": len(endpoint_entries),
        }

        try:
            summary_path.write_text(
                json.dumps(
                    summary_data,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            outputs["summary"] = str(summary_path)

        except Exception as exc:
            logger.error(f"Failed writing summary.json: {exc}")

        logger.info(f"Recon pipeline completed for {domain}")

        return outputs

    async def join_results(
        self,
        paths: Iterable[Path],
        out_file: str,
    ) -> Path:

        target = self.target_root / out_file

        with target.open("wb") as writer:
            for path in paths:
                if path.exists():
                    writer.write(path.read_bytes())
                    writer.write(b"\n")

        return target
