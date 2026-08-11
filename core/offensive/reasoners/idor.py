"""IDOR Reasoner — detects potential Insecure Direct Object Reference patterns.

Analyzes endpoints for object reference patterns in paths and parameters.
Generates hypotheses with confidence scores, test instructions, and
alternative explanations — exactly what a human triager would consider.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from core.offensive.models import EndpointInfo, Hypothesis
from core.offensive.reasoners.base import BaseReasoner
from core.offensive.templates import IDOR_ALTERNATIVES, IDOR_PATTERNS

logger = logging.getLogger("orion.core.offensive.reasoners.idor")

# Objects commonly referenced in APIs — higher = more likely to be IDOR-vulnerable
OBJECT_REFERENCE_KEYWORDS: dict[str, float] = {
    # Direct object references (highest signal)
    "id": 0.9,
    "user_id": 0.95,
    "userId": 0.9,
    "account_id": 0.9,
    "accountId": 0.9,
    "customer_id": 0.9,
    "customerId": 0.9,
    "profile_id": 0.85,
    "profileId": 0.85,
    "order_id": 0.8,
    "orderId": 0.8,
    "document_id": 0.85,
    "documentId": 0.85,
    "file_id": 0.8,
    "fileId": 0.8,
    "ticket_id": 0.8,
    "ticketId": 0.8,
    "invoice_id": 0.85,
    "invoiceId": 0.85,
    "payment_id": 0.85,
    "paymentId": 0.85,
    "transaction_id": 0.85,
    "transactionId": 0.85,
    # Short forms (common in APIs)
    "uid": 0.85,
    "pid": 0.7,
    "eid": 0.7,
    "oid": 0.75,
    "gid": 0.6,
    "sid": 0.7,
    # Implicit references (weaker signal)
    "user": 0.6,
    "account": 0.65,
    "profile": 0.6,
    "customer": 0.6,
    "owner": 0.7,
    "target": 0.5,
    "resource": 0.5,
    "object": 0.5,
    "entity": 0.5,
    "record": 0.5,
    "item": 0.4,
}

# HTTP methods and their IDOR risk
METHOD_RISK: dict[str, float] = {
    "GET": 0.6,  # Read — information disclosure
    "POST": 0.4,  # Create — can create as other user
    "PUT": 0.7,  # Update — modify other's data
    "PATCH": 0.7,  # Partial update — modify other's data
    "DELETE": 0.8,  # Delete — destroy other's data
}

UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
NUMERIC_PATTERN = re.compile(r"^\d+$")


class IDORReasoner(BaseReasoner):
    """Analyzes endpoints for potential IDOR vulnerabilities."""

    @property
    def vulnerability_type(self) -> str:
        return "idor"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH", "DELETE"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        # ── Signal 1: Path-based object references ────────────────
        path_parts = [p for p in endpoint.path.split("/") if p]
        path_refs = self._find_references(path_parts)

        for ref, score in path_refs:
            signals.append(f"Path contains object reference: {ref}")
            params_of_interest.append(ref)
            confidence += score * 0.4  # Path refs are strong

        # ── Signal 2: Path params (from framework routing) ────────
        for pp in endpoint.path_params:
            if self._is_object_reference(pp):
                signals.append(f"Route parameter suggests object reference: {pp}")
                params_of_interest.append(pp)
                confidence += self._keyword_score(pp) * 0.35
            elif UUID_PATTERN.match(pp):
                signals.append(f"UUID in route path: {pp}")
                params_of_interest.append(pp)
                confidence += 0.4
            elif NUMERIC_PATTERN.match(pp):
                signals.append(f"Numeric ID in route path: {pp}")
                params_of_interest.append(pp)
                confidence += 0.5

        # ── Signal 3: Query parameters ────────────────────────────
        for qp in endpoint.query_params:
            if self._is_object_reference(qp):
                signals.append(f"Query parameter suggests object reference: {qp}")
                params_of_interest.append(qp)
                confidence += self._keyword_score(qp) * 0.25
                # Value hints
                val = endpoint.params.get(qp, "")
                if UUID_PATTERN.match(val):
                    signals.append(f"UUID value in query param {qp}")
                    confidence += 0.15
                elif NUMERIC_PATTERN.match(val):
                    signals.append(f"Numeric value in query param {qp}")
                    confidence += 0.1

        # ── Signal 4: HTTP method risk ────────────────────────────
        method = endpoint.method.upper()
        if method in METHOD_RISK:
            risk = METHOD_RISK[method]
            if risk >= 0.7:
                signals.append(f"High-risk method for IDOR: {method}")
            confidence += risk * 0.2

        # ── Signal 5: Path depth and structure ────────────────────
        depth = len(path_parts)
        if depth >= 3 and any(self._is_object_reference(p) for p in path_parts):
            signals.append(f"Nested endpoint with object references (depth={depth})")
            confidence += 0.1

        # ── Signal 6: Body parameters ─────────────────────────────
        if endpoint.body:
            body_refs = self._find_references(list(endpoint.body.keys()))
            if body_refs:
                signals.append(f"Body contains object references: {[r for r, _ in body_refs]}")
                params_of_interest.extend(r for r, _ in body_refs)
                confidence += sum(s for _, s in body_refs) * 0.15

        # ── Build hypothesis if confidence is meaningful ──────────
        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        severity = self._compute_severity(confidence, method)

        hypothesis = Hypothesis(
            vulnerability_type="idor",
            endpoint=endpoint.path,
            method=endpoint.method,
            confidence=confidence,
            severity=severity,
            summary=self._build_summary(endpoint, params_of_interest),
            description=self._build_description(endpoint, params_of_interest, method),
            why_human_would_investigate=self._build_triager_justification(
                endpoint, params_of_interest, method, signals
            ),
            parameters_of_interest=params_of_interest,
            signals=signals,
            test_instructions=self._build_test_instructions(endpoint, params_of_interest, method),
            alternative_explanations=self._build_alternatives(endpoint, params_of_interest),
            scope_check=self._scope_check(endpoint),
            reproducibility_notes=self._reproducibility_notes(method, params_of_interest),
        )

        return [hypothesis]

    # ── Internal helpers ──────────────────────────────────────────

    def _is_object_reference(self, name: str) -> bool:
        return name.lower() in OBJECT_REFERENCE_KEYWORDS

    def _keyword_score(self, name: str) -> float:
        return OBJECT_REFERENCE_KEYWORDS.get(name.lower(), 0.0)

    def _find_references(self, candidates: list[str]) -> list[tuple[str, float]]:
        return [(c, self._keyword_score(c)) for c in candidates if self._is_object_reference(c)]

    def _compute_severity(self, confidence: float, method: str) -> str:
        base = confidence
        if method.upper() in ("DELETE", "PUT", "PATCH"):
            base += 0.15
        elif method.upper() == "GET":
            base += 0.05
        if base >= 0.7:
            return "high"
        if base >= 0.4:
            return "medium"
        return "low"

    def _build_summary(self, endpoint: EndpointInfo, params_of_interest: list[str]) -> str:
        refs = ", ".join(params_of_interest[:3])
        return f"Potential IDOR via {refs} on {endpoint.method} {endpoint.path}"

    def _build_description(self, endpoint: EndpointInfo, params: list[str], method: str) -> str:
        refs = ", ".join(params[:4])
        if method.upper() == "GET":
            action = "read data belonging to other users by changing the"
        elif method.upper() == "DELETE":
            action = "delete resources belonging to other users by manipulating the"
        elif method.upper() in ("PUT", "PATCH"):
            action = "modify resources belonging to other users by altering the"
        elif method.upper() == "POST":
            action = "create resources referencing other users by controlling the"
        else:
            action = "access resources by manipulating the"

        return (
            f"The endpoint {endpoint.method} {endpoint.path} accepts object references "
            f"({refs}) that could allow an attacker to {action} referenced identifier. "
            f"If the server does not verify ownership before processing the request, "
            f"this is an IDOR vulnerability."
        )

    def _build_triager_justification(
        self,
        endpoint: EndpointInfo,
        params: list[str],
        method: str,
        signals: list[str],
    ) -> str:
        strong_signals = sum(1 for s in signals if "high-risk" in s or "object reference" in s)
        return (
            f"A human triager would investigate this because: "
            f"{endpoint.method} {endpoint.path} uses {params[0] if params else 'an identifier'} "
            f"as a direct reference to a server-side object. "
            f"The endpoint has {len(signals)} IDOR indicators "
            f"({strong_signals} of them high-confidence). "
            f"A quick test with an alternate identifier would confirm or rule out IDOR."
        )

    def _build_test_instructions(self, endpoint: EndpointInfo, params: list[str], method: str) -> list[str]:
        instructions = []
        for param in params[:2]:
            instructions.extend(
                IDOR_PATTERNS.get("test_instructions", [])
                + [
                    f"Try replacing {param} with a value belonging to a different user "
                    f"(e.g., add 1 to a numeric ID, or substitute a known UUID).",
                    "Send the request as an unprivileged user and observe if the response "
                    "contains data that does not belong to that user.",
                    f"If the endpoint returns data for the substituted {param}, "
                    f"without proper authorization — it's an IDOR.",
                ]
            )
        if method.upper() == "GET":
            instructions.append(
                "Test mass enumeration: iterate through sequential IDs "
                "and check if responses differ between authenticated users."
            )
        return instructions

    def _build_alternatives(self, endpoint: EndpointInfo, params: list[str]) -> list[dict[str, Any]]:
        return [
            {
                "label": alt["label"],
                "description": alt["description"],
                "how_to_rule_out": alt["how_to_rule_out"],
            }
            for alt in IDOR_ALTERNATIVES.get("idor", [])
        ]

    def _scope_check(self, endpoint: EndpointInfo) -> str:
        return (
            f"Verify that {endpoint.path} is within the program's scope. "
            f"Check that the {endpoint.method} method is explicitly allowed. "
            f"Confirm there are no rate limits or WAF rules that would block testing."
        )

    def _reproducibility_notes(self, method: str, params: list[str]) -> str:
        param = params[0] if params else "the identifier"
        return (
            f"Create two test accounts (A and B). Authenticate as user A. "
            f"Send {method} request to the endpoint with user B's {param}. "
            f"If user B's data is returned/modified/deleted, the issue is reproducible."
        )
