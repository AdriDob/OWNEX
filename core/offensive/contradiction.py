"""Contradiction Engine — attacks hypotheses with counterarguments.

For every hypothesis, generates contradictions that a triager
or program owner would raise. This forces the system to
consider alternative explanations BEFORE generating a report.

Only hypotheses that survive contradiction should proceed.
"""

from __future__ import annotations

import logging

from core.offensive.models import Contradiction, Hypothesis

logger = logging.getLogger("orion.core.offensive.contradiction")


class ContradictionEngine:
    """Generates counterarguments for a given hypothesis.

    Each vulnerability type has specific contradictions based on
    common triager objections and real-world program outcomes.
    """

    def attack(self, hypothesis: Hypothesis) -> list[Contradiction]:
        """Generate all contradictions for a hypothesis.

        Returns a list of Contradiction objects that weaken the hypothesis.
        """
        contradictions: list[Contradiction] = []
        vtype = hypothesis.vulnerability_type

        # Type-specific contradictions
        type_method = f"_attack_{vtype}"
        if hasattr(self, type_method):
            contradictions.extend(getattr(self, type_method)(hypothesis))

        # Generic contradictions that apply to everything
        contradictions.extend(self._attack_generic(hypothesis))

        # Deduplicate by label
        seen: set[str] = set()
        unique: list[Contradiction] = []
        for c in contradictions:
            if c.label not in seen:
                seen.add(c.label)
                unique.append(c)

        return unique

    # ── IDOR contradictions ──────────────────────────────────────

    def _attack_idor(self, hypothesis: Hypothesis) -> list[Contradiction]:
        return [
            Contradiction(
                label="Ownership verified server-side",
                description="The server may verify that the authenticated user owns the requested resource before returning it. The presence of an identifier in the endpoint does not guarantee IDOR.",
                confidence_reduction=0.35,
                how_to_rule_out="Try accessing a resource belonging to a different user account. If the server returns 403 or masks sensitive data, ownership is enforced.",
            ),
            Contradiction(
                label="Access control at gateway level",
                description="Authorization may be enforced at a reverse proxy, API gateway, or WAF level — not at the application endpoint itself.",
                confidence_reduction=0.25,
                how_to_rule_out="Check if the endpoint is behind a gateway that validates JWTs or session tokens. Try bypassing the gateway.",
            ),
            Contradiction(
                label="Resource may be public",
                description="The accessed resource might be intentionally public (e.g., a user's public profile). What looks like IDOR might be intended behavior.",
                confidence_reduction=0.3,
                how_to_rule_out="Check if the same data is accessible without authentication. If yes, it's public, not IDOR.",
            ),
            Contradiction(
                label="UUID/GUID not enumerable",
                description="If identifiers are random UUIDs, exploitation requires guessing or obtaining valid IDs through other means.",
                confidence_reduction=0.2,
                how_to_rule_out="Check if IDs follow a predictable pattern. Sequential numeric IDs are strong evidence of vulnerability.",
            ),
            Contradiction(
                label="Indirect reference map in use",
                description="The application may use indirect references (session-scoped mappings) rather than exposing direct object references.",
                confidence_reduction=0.3,
                how_to_rule_out="Try the same ID from a different session. If it resolves differently, indirect mapping is in use.",
            ),
            Contradiction(
                label="Rate limiting prevents mass enumeration",
                description="Even if IDOR exists, aggressive rate limiting may prevent practical exploitation at scale.",
                confidence_reduction=0.1,
                how_to_rule_out="Test rate limits by sending rapid requests. Check for X-RateLimit headers or 429 responses.",
            ),
            Contradiction(
                label="Authorization at parameter level not path level",
                description="The endpoint may authorize based on a different parameter than the one being tested. E.g., the path has user_id but auth checks the JWT sub claim.",
                confidence_reduction=0.25,
                how_to_rule_out="Try changing different parameters independently. Compare behavior when changing the path param vs a header/session.",
            ),
        ]

    # ── Generic contradictions ───────────────────────────────────

    @staticmethod
    def _attack_generic(hypothesis: Hypothesis) -> list[Contradiction]:
        contradictions: list[Contradiction] = []

        if hypothesis.confidence < 0.5:
            contradictions.append(
                Contradiction(
                    label="Low confidence hypothesis",
                    description=f"The hypothesis confidence is only {hypothesis.confidence:.2f}, meaning the signals are weak. A triager would deprioritize this.",
                    confidence_reduction=0.2,
                    how_to_rule_out="Gather more evidence before investigating. Look for additional signals.",
                )
            )

        if hypothesis.severity == "low":
            contradictions.append(
                Contradiction(
                    label="Low severity reduces triage priority",
                    description="Triagers prioritize high/critical severity findings. Low severity findings may not be triaged at all.",
                    confidence_reduction=0.1,
                    how_to_rule_out=None,
                )
            )

        if not hypothesis.reproducibility_notes:
            contradictions.append(
                Contradiction(
                    label="Missing reproduction steps",
                    description="Without clear reproduction steps, a triager cannot verify the finding. This is the #1 reason for 'cannot reproduce' rejections.",
                    confidence_reduction=0.3,
                    how_to_rule_out="Add precise steps: which account, which request, expected vs actual response.",
                )
            )

        if not hypothesis.alternative_explanations:
            contradictions.append(
                Contradiction(
                    label="No alternative explanations considered",
                    description="The hypothesis did not consider alternative explanations. A triager will — and may find one that invalidates the finding.",
                    confidence_reduction=0.15,
                    how_to_rule_out="Run through common alternative explanations for this vulnerability type.",
                )
            )

        return contradictions
