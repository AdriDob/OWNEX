import logging
import sys

PREFIX_MAP: dict[str, str] = {
    "CATEYE.identity_vault": "[VAULT]",
    "CATEYE.identity": "[IDENTITY]",
    "CATEYE.auth": "[AUTH]",
    "CATEYE.license": "[LICENSE]",
    "CATEYE.hardware": "[HW]",
    "CATEYE.pipeline": "[PIPELINE]",
    "CATEYE.report": "[REPORT]",
    "CATEYE.reporting": "[REPORT]",
    "CATEYE.ai": "[AI]",
    "CATEYE.assistant": "[AI]",
    "CATEYE.intelligence": "[INTEL]",
    "CATEYE.learning": "[LEARN]",
    "CATEYE.memory": "[MEMORY]",
    "CATEYE.finance": "[FINANCE]",
    "CATEYE.roi": "[FINANCE]",
    "CATEYE.sync": "[SYNC]",
    "CATEYE.build": "[BUILD]",
    "CATEYE.desktop": "[DESKTOP]",
    "CATEYE.updater": "[UPDATE]",
    "CATEYE.ws": "[WS]",
    "CATEYE.events": "[EVENTS]",
    "CATEYE.orchestrator": "[ORCH]",
    "CATEYE.observability": "[OBS]",
    "CATEYE.recon": "[RECON]",
    "CATEYE.validation": "[VALIDATE]",
    "CATEYE.evidence": "[EVIDENCE]",
    "CATEYE.notifications": "[NOTIFY]",
    "CATEYE.opportunity": "[OPPORTUNITY]",
    "CATEYE.targets": "[TARGET]",
    "CATEYE.engine": "[ENGINE]",
    "CATEYE.execution": "[EXEC]",
    "CATEYE.analysis": "[ANALYSIS]",
    "CATEYE.attack": "[ATTACK]",
    "CATEYE.explainability": "[EXPLAIN]",
    "CATEYE.contracts": "[CONTRACT]",
    "CATEYE.fallback": "[FALLBACK]",
    "CATEYE.confidence": "[CONFIDENCE]",
    "CATEYE.product_rules": "[RULES]",
    "CATEYE.system_state": "[STATE]",
    "CATEYE.system_health": "[HEALTH]",
    "CATEYE.timeline": "[TIMELINE]",
    "CATEYE.screenshot": "[SCREENSHOT]",
    "CATEYE.web3": "[WEB3]",
    "CATEYE.quick_wins": "[QUICKWIN]",
    "CATEYE.ux": "[UX]",
    "CATEYE.accountability": "[ACCT]",
    "CATEYE.review_queue": "[REVIEW]",
    "CATEYE.gateway": "[GATEWAY]",
    "CATEYE.platform": "[PLATFORM]",
    "CATEYE.unification": "[UNIFY]",
    "CATEYE.clustering": "[CLUSTER]",
    "CATEYE.differential": "[DIFF]",
    "CATEYE.target_auth": "[AUTH]",
    "CATEYE.serve": "[SERVE]",
}


class PrefixedFormatter(logging.Formatter):
    """Log formatter that injects structured prefixes based on logger name.

    Uses longest-prefix-match: for ``CATEYE.auth.manager`` it will match
    ``CATEYE.auth`` (not just exact ``record.name`` lookups).
    """

    def format(self, record: logging.LogRecord) -> str:
        prefix = ""
        name = record.name
        # Longest-prefix match
        for key, value in PREFIX_MAP.items():
            if name.startswith(key) and len(key) > len(prefix):
                prefix = value
        record.prefix = prefix
        return super().format(record)


def setup_logging(level: str | None = None, json_output: bool = False) -> None:
    """Configure unified logging across all CATEYE modules."""
    if json_output:
        fmt = '{"time":"%(asctime)s","prefix":"%(prefix)s","logger":"%(name)s","level":"%(levelname)s","message":"%(message)s"}'
    else:
        fmt = "%(asctime)s %(prefix)-12s | %(levelname)-5s | %(message)s"
    root = logging.getLogger("CATEYE")
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(PrefixedFormatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
        root.addHandler(handler)
    root.setLevel(level or "INFO")
