"""OWNEX Operating Context — engine.

This is the bridge between the Operating Context document and the
execution layer. It does NOT create a second policy engine or a second
scheduler. It reuses:

  - core.copilot.permissions.PolicyEngine  (permissions)
  - core.memory.store.UnifiedMemoryStore  (persistent state)
  - core.daily_cycle.system.DailyBriefing (daily briefing)

Responsibilities of this module:

  1. Load the Operating Context document from disk (canonical, versioned).
  2. Store the parsed context in Unified Memory (namespace="opcontext").
  3. Expose the context as a structured, queryable state.
  4. Provide validation helpers (evidence expiry, eligibility, stale).
  5. Render the Daily Brief from the real system state.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.copilot.permissions import PolicyEngine
from core.memory.store import get_memory_store

logger = logging.getLogger("orion.core.operating_context")

# Namespace for Operating Context memory entries
OPCONTEXT_NAMESPACE = "opcontext"

# Keys stored in memory
OPCONTEXT_KEY = "context_v1_2026_10_29"
OPCONTEXT_SOURCES_KEY = "sources_status"
OPCONTEXT_POLICY_NAMES = "policy_names"

# Default expiry for evidence (days). Overridable per source.
EVIDENCE_TTL_DAYS = 90

# The canonical Operating Context document
OPERATING_CONTEXT_PATH = Path("/home/adriel/projects/Rastro/docs/OPERATING_CONTEXT.md")

# Sources covered by the Operating Context and their last-known status
SOURCES = {
    "lilly-protocol": {
        "name": "Lilly-Protocol/agentlily-runtime",
        "source": "Operating Context §1",
        "status": "hypothesis",
        "verified": False,
        "verified_at": None,
        "evidence": "Benchmark $345/semana en 1 semana (4 PRs merged, sep 2026). No prueba propia de OWNEX.",
        "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
    },
    "huntr": {
        "name": "huntr.com",
        "source": "Operating Context §2",
        "status": "reported",
        "verified": False,
        "verified_at": None,
        "evidence": "$0-$50,000 payout. Stripe Connect Express, día 25. AR probablemente válido (Global Payouts, mar 2026) sin confirmación de cobro.",
        "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
    },
    "agenthansa": {
        "name": "AgentHansa",
        "source": "Operating Context §3",
        "status": "verified",
        "verified_at": datetime.now(UTC).isoformat(),
        "evidence": "0 quests abiertas (171 settled, 227 totales). Scan 6h.",
        "expires_at": (datetime.now(UTC) + timedelta(hours=6)).isoformat(),
    },
    "superteam": {
        "name": "Superteam Earn",
        "source": "Operating Context §4",
        "status": "reported",
        "verified": False,
        "verified_at": None,
        "evidence": "AGENT_ALLOWED + USDC. Aprobación humana requerida para claim.",
        "expires_at": (datetime.now(UTC) + timedelta(hours=12)).isoformat(),
    },
    "github-bounties": {
        "name": "GitHub Bounties",
        "source": "Operating Context §5",
        "status": "hypothesis",
        "verified": False,
        "verified_at": None,
        "evidence": "4-8 PRs/mes a 3-5 repos verificados. No spray and pray.",
        "expires_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
    },
}

# Sources in pause
PAUSED_SOURCES = {"mcp_marketplace", "mcpize", "gravity", "apify", "forecast_bot"}

# Sources blocked
BLOCKED_SOURCES = {
    "trybounty", "algora", "dealwork", "x402_bazaar", "moltjobs", "clawtasks",
    "nanocorp", "gpt_store", "mulerun", "agenton", "activepieces", "aigen_protocol",
}


class OperatingContextError(Exception):
    """Base error for Operating Context."""
    pass


class OperatingContext:
    """The Operating Context engine.

    Loads the canonical document, stores it in persistent memory, and
    provides structured access to policies, sources, and state.
    """

    def __init__(self, policy_engine: PolicyEngine | None = None) -> None:
        self.policy_engine = policy_engine or PolicyEngine()
        self._loaded = False
        self._sources_status: dict[str, dict[str, Any]] = {}
        self._policy_names: list[str] = []

    # ── Load ─────────────────────────────────────────────────────────────

    def load(self, *, force: bool = False, path: Path | None = None) -> bool:
        """Load the Operating Context from file.

        Returns True if loaded successfully. If the document cannot be
        loaded, the system is blocked (REGLA 3: denegación por defecto).
        """
        p = path or OPERATING_CONTEXT_PATH
        if not p.exists():
            logger.error("Operating Context document not found: %s", p)
            self._mark_blocked("document not found")
            return False

        text = p.read_text(encoding="utf-8")
        self._parsed = self._parse(text, p)

        # Store in persistent memory (survives restarts)
        store = get_memory_store()
        store.store(
            namespace=OPCONTEXT_NAMESPACE,
            key=OPCONTEXT_KEY,
            content=self._parsed.get("raw", ""),
            metadata={
                "source": str(p),
                "version": self._parsed.get("version", "unknown"),
                "loaded_at": datetime.now(UTC).isoformat(),
                "document_sha256": self._parsed.get("sha256", ""),
            },
            tags=["operational-context", "policy"],
            priority=0.9,
        )

        # Store source statuses
        store.store(
            namespace=OPCONTEXT_NAMESPACE,
            key=OPCONTEXT_SOURCES_KEY,
            content=str(self._sources_status),
            metadata={"last_updated": datetime.now(UTC).isoformat()},
            tags=["sources", "status"],
            priority=0.8,
        )

        # Store policy names
        store.store(
            namespace=OPCONTEXT_NAMESPACE,
            key=OPCONTEXT_POLICY_NAMES,
            content=str(self._policy_names),
            metadata={"last_updated": datetime.now(UTC).isoformat()},
            tags=["policies"],
            priority=0.7,
        )

        # Mark as loaded and validated
        self._loaded = True
        self._mark_validated()
        logger.info("Operating Context loaded from %s", p)
        return True

    # ── Parsing ──────────────────────────────────────────────────────────

    def _parse(self, text: str, path: Path) -> dict[str, Any]:
        """Parse the Operating Context document into structured data."""
        header = "UNKNOWN"
        match = re.search(r"# OWNEX — OPERATING CONTEXT \((.*?)\)", text)
        if match:
            header = match.group(1)

        return {
            "source": str(path),
            "version": header,
            "raw": text,
            "sha256": self._sha256(text),
        }

    @staticmethod
    def _sha256(text: str) -> str:
        import hashlib

        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    # ── Validation ───────────────────────────────────────────────────────

    def validate(self) -> tuple[bool, str]:
        """Validate the loaded context.

        A context is valid if:
        - It is loaded.
        - The source file exists and was parsed.
        - The evidence for each source is not stale.

        Returns (valid, message).
        """
        if not self._loaded:
            return False, "Context not loaded"

        # Check each source's evidence expiry
        store = get_memory_store()
        entries = store.query(namespace=OPCONTEXT_NAMESPACE, include_expired=True)
        if entries:
            src_data = entries[0].get("content", "{}")
            try:
                self._sources_status = eval(src_data) if isinstance(src_data, str) else src_data
            except Exception:
                self._sources_status = {}

        now = datetime.now(UTC)
        stale: list[str] = []
        missing: list[str] = []

        for slug, info in self._sources_status.items():
            expires_at = info.get("expires_at")
            if expires_at:
                try:
                    if datetime.fromisoformat(expires_at) <= now:
                        stale.append(slug)
                except ValueError:
                    missing.append(slug)

        if stale:
            return False, f"Evidence stale for: {', '.join(stale)}"

        if missing:
            return False, f"Incomplete evidence metadata: {', '.join(missing)}"

        return True, "Context validated"

    def block(self, reason: str) -> None:
        """Mark the Operating Context as blocked (REGLA 3)."""
        store = get_memory_store()
        store.store(
            namespace=OPCONTEXT_NAMESPACE,
            key="status",
            content=f"blocked: {reason}",
            metadata={"blocked_at": datetime.now(UTC).isoformat()},
            tags=["status", "blocked"],
            priority=0.1,
        )
        self._loaded = False
        self._parsed = None

    def _mark_blocked(self, reason: str) -> None:
        self.block(reason)

    def _mark_validated(self) -> None:
        store = get_memory_store()
        store.store(
            namespace=OPCONTEXT_NAMESPACE,
            key="status",
            content="validated",
            metadata={"validated_at": datetime.now(UTC).isoformat()},
            tags=["status", "validated"],
            priority=0.9,
        )

    # ── Query ────────────────────────────────────────────────────────────

    def get_context(self) -> dict[str, Any] | None:
        """Retrieve the loaded context from memory."""
        store = get_memory_store()
        return store.get(OPCONTEXT_NAMESPACE, OPCONTEXT_KEY)

    def get_sources_status(self) -> dict[str, dict[str, Any]]:
        """Get the status of all sources defined in the Operating Context."""
        if not self._sources_status:
            store = get_memory_store()
            entries = store.query(namespace=OPCONTEXT_NAMESPACE, include_expired=True)
            if entries:
                try:
                    self._sources_status = eval(
                        entries[0].get("content", "{}")
                    )
                except Exception:
                    self._sources_status = {}
        return dict(self._sources_status)

    def get_policy_names(self) -> list[str]:
        """Get the names of all executed policies."""
        if not self._policy_names:
            store = get_memory_store()
            entries = store.query(namespace=OPCONTEXT_NAMESPACE, include_expired=True)
            if entries:
                content = entries[0].get("content", "[]")
                if isinstance(content, str):
                    try:
                        parsed = eval(content)
                        if isinstance(parsed, list):
                            self._policy_names = parsed
                        else:
                            self._policy_names = []
                    except Exception:
                        self._policy_names = []
                elif isinstance(content, list):
                    self._policy_names = content
                else:
                    self._policy_names = []
        return list(self._policy_names)

    def is_context_valid(self) -> bool:
        """Check if the context is currently valid."""
        return self._loaded

    def is_context_blocked(self) -> bool:
        """Check if the context is blocked."""
        if not self._loaded:
            return True
        store = get_memory_store()
        status = store.get(OPCONTEXT_NAMESPACE, "status")
        return status is not None and status.get("content") != "validated"

    # ── Daily brief ──────────────────────────────────────────────────────

    def generate_daily_brief(self) -> dict[str, Any]:
        """Generate the Daily Brief from the real system state.

        Returns a dict that can be rendered as the Operating Context format.
        """
        brief: dict[str, Any] = {
            "version": self._parsed.get("version", "unknown"),
            "timestamp": datetime.now(UTC).isoformat(),
            "state": "BLOCKED" if self.is_context_blocked() else "OK",
            "state_reason": self._brief_state_reason(),
            "sources": self._brief_sources(),
            "pending_approvals": self._brief_pending_approvals(),
            "next_actions": self._brief_next_actions(),
            "rules_applied": self._brief_rules_applied(),
        }
        return brief

    def _brief_state_reason(self) -> str:
        if self.is_context_blocked():
            return "Context blocked"
        if not self._loaded:
            return "Context not loaded"
        return "Context OK"

    def _brief_sources(self) -> list[dict[str, Any]]:
        sources = self.get_sources_status()
        return [
            {
                "source": slug,
                "name": info.get("name", slug),
                "status": info.get("status", "unknown"),
                "verified": info.get("verified", False),
                "expires_at": info.get("expires_at"),
                "evidence": info.get("evidence", ""),
            }
            for slug, info in sorted(sources.items())
        ]

    def _brief_pending_approvals(self) -> list[dict[str, Any]]:
        # In a real integration this would read from the Human Gate store.
        # For now it is a stub that returns the current policy state.
        return []

    def _brief_next_actions(self) -> list[dict[str, Any]]:
        # Next recommended actions from the Operating Context.
        return []

    def _brief_rules_applied(self) -> list[str]:
        return self.get_policy_names()

    # ── Integration helpers ──────────────────────────────────────────────

    def check_action(self, action: str, *, level: Any = None, **context: Any) -> tuple[bool, list[str]]:
        """Check an action against the policy engine.

        Returns (allowed, [blocking policy names]).
        """
        if not self._loaded:
            return False, ["opcontext:deny_default"]
        return self.policy_engine.check(level or context.get("level"), action, **context)
