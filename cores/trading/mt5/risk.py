"""Risk gating for the MT5 bridge arm."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REQUIREMENTS_MAP: dict[str, str] = {
    "personal": "PERSONAL_VULN_REQUIREMENT",
    "unique": "UNIQUE_VULN_REQUIREMENT",
    "deep": "DEEP_SEARCH_VULN_REQUIREMENT",
    "lab": "LAB_VULN_REQUIREMENT",
}

GLOBAL_VULN_REQUIREMENT = "PERSONAL_VULN_REQUIREMENT"

DEFAULT_NOTES = {
    "hard_fail": "needs a valid MT5 account",
    "reject": "requires a registered broker login",
    "hold": "account not yet validated",
    "test_only": "skip only in local/test runs",
    "dry_run": "no live orders",
}


@dataclass
class MT5GateResult:
    """Structured outcome of a single arm gate.

    ``resolve`` follows the rules in core.integrations.opportunity.RuleMutator
    to turn a raw check result into the exact payload a bridge sidecar can
    consume.
    """

    ok: bool
    reason: str
    state: str
    details: dict[str, Any] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)
    requirements: list[str] = field(default_factory=list)
    required_for: str = "personal"

    def resolve(self, **overrides: Any) -> dict[str, Any]:
        out = {
            "ok": self.ok,
            "state": self.state,
            "reason": self.reason,
            "details": dict(self.details),
            "notes": dict(self.notes),
            "requirements": list(self.requirements),
            "required_for": self.required_for,
        }
        out.update(overrides)
        return out


class MT5GateValidator:
    """Validates arm requests against risk requirements.

    The validator is intentionally thin: every rule is pluggable and every
    payload is returned at the top level so callers (controller, bridge
    proxy, desktop UI) can decide how to encode it.
    """

    def __init__(self, requirements_map: dict[str, str] | None = None):
        self._map = requirements_map or dict(REQUIREMENTS_MAP)

    # -- public API -----------------------------------------------------

    def validate(
        self,
        *,
        subscription: bool,
        intent: str,
        broker_login: str | None = None,
        account_validated: bool = False,
        vulnerability_requirements: list[str] | None = None,
        context: str = "request",
    ) -> MT5GateResult:
        if not subscription:
            return MT5GateResult(
                ok=False,
                state="hard_fail",
                reason="subscription not active",
                notes=dict(DEFAULT_NOTES["hard_fail"]),
                requirements=["SUBSCRIPTION_ACTIVE"],
            )

        if intent not in {"spot", "leverage", "signals"}:
            return MT5GateResult(
                ok=False,
                state="reject",
                reason="invalid intent",
                notes=dict(DEFAULT_NOTES["hard_fail"]),
                requirements=["VALID_INTENT"],
            )

        if broker_login is None and account_validated:
            return MT5GateResult(
                ok=False,
                state="reject",
                reason="no broker login bound to this arm",
                notes=dict(DEFAULT_NOTES["reject"]),
                requirements=["BROKER_LOGIN_BOUND"],
            )

        reqs = list(vulnerability_requirements or [])
        if GLOBAL_VULN_REQUIREMENT not in reqs:
            return MT5GateResult(
                ok=False,
                state="hold",
                reason="global vulnerability requirement missing",
                notes=dict(DEFAULT_NOTES["hold"]),
                requirements=[GLOBAL_VULN_REQUIREMENT],
                required_for=GLOBAL_VULN_REQUIREMENT,
            )

        return MT5GateResult(
            ok=True,
            state="pass",
            reason="all risk gates satisfied",
            details={
                "intent": intent,
                "account_validated": account_validated,
                "requirements": reqs,
            },
            requirements=reqs,
            required_for=GLOBAL_VULN_REQUIREMENT,
        )

    # -- pluggable rule hooks ---------------------------------------------

    def _check_broker_auth(
        self,
        broker_login: str | None,
        account_validated: bool,
    ) -> MT5GateResult:
        if broker_login is None:
            return MT5GateResult(
                ok=False,
                state="reject",
                reason="no broker login bound to this arm",
                notes=dict(DEFAULT_NOTES["reject"]),
                requirements=["BROKER_LOGIN_BOUND"],
            )
        return MT5GateResult(
            ok=True,
            state="pass",
            reason="broker auth ok",
            requirements=["BROKER_LOGIN_BOUND"],
        )

    def _check_vuln_requirement(
        self,
        vulnerability_requirements: list[str],
    ) -> MT5GateResult:
        if GLOBAL_VULN_REQUIREMENT not in vulnerability_requirements:
            return MT5GateResult(
                ok=False,
                state="hold",
                reason="global vulnerability requirement missing",
                notes=dict(DEFAULT_NOTES["hold"]),
                requirements=[GLOBAL_VULN_REQUIREMENT],
                required_for=GLOBAL_VULN_REQUIREMENT,
            )
        return MT5GateResult(
            ok=True,
            state="pass",
            reason="vuln requirement ok",
            requirements=[GLOBAL_VULN_REQUIREMENT],
            required_for=GLOBAL_VULN_REQUIREMENT,
        )
