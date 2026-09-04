"""Creative Hypothesis Generator — uses OAR to find vulnerabilities rules miss.

Unlike the 10 rule-based generators (IDOR, auth_bypass, SSRF, etc.), this
generator asks OAR/LLM: "given this attack surface, what creative attack
vector would a skilled human researcher try that no template covers?"

This is the bridge between scanner findings ($50-300) and manual research
findings ($500+) — it automates the "creative thinking" phase.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cores.engine.hypothesis.models import (
    Hypothesis,
    HypothesisSource,
    VulnerabilityType,
)

logger = logging.getLogger("ownex.hypothesis.creative")

_CREATIVE_PROMPT = """You are an elite bug bounty researcher. Given this target's attack surface,
propose 1-3 creative vulnerability hypotheses that automated scanners would MISS.

Target: {target_name}
Endpoints summary: {endpoints_summary}
Attack surface signals: {surface_signals}
Technologies detected: {technologies}

Focus on:
- Business logic flaws (price manipulation, workflow bypass)
- Authentication chain attacks (token confusion, session fixation)
- Race conditions (double-spend, TOCTOU on critical actions)
- Authorization gaps between roles (horizontal/vertical privilege escalation)
- API mass assignment or parameter pollution

Output STRICT JSON array:
[
  {{
    "title": "short description",
    "vulnerability_type": "one_of: business_logic|auth_chain|race_condition|privilege_escalation|mass_assignment|other",
    "endpoint": "/api/path",
    "method": "GET|POST|PUT|DELETE",
    "likelihood": 0.0-1.0,
    "impact": 0.0-1.0,
    "reasoning": "why this might work",
    "suggested_test": "specific test to perform"
  }}
]

If no creative hypotheses possible, return []"""


def generate_creative_hypotheses(
    target_id: int,
    target_name: str,
    endpoints: list[dict[str, Any]],
    attack_surface: dict[str, Any],
) -> list[Hypothesis]:
    """Generate creative hypotheses using OAR LLM analysis.

    Unlike rule-based generators that match known patterns, this asks
    the LLM to think creatively about what could be wrong given the
    specific attack surface of THIS target.

    Returns empty list if OAR unavailable or LLM fails gracefully.
    """
    if not endpoints:
        return []

    prompt = _CREATIVE_PROMPT.format(
        target_name=target_name,
        endpoints_summary=_summarize_endpoints(endpoints[:20]),
        surface_signals=json.dumps(attack_surface.get("signals", [])[:15]),
        technologies=json.dumps(attack_surface.get("technologies", [])[:10]),
    )

    response_text = _call_oar_for_creative(prompt)
    if not response_text:
        return []

    hypotheses = _parse_llm_hypotheses(response_text, target_id, target_name)
    logger.info("Creative generator produced %d hypotheses for %s", len(hypotheses), target_name)
    return hypotheses


def _call_oar_for_creative(prompt: str) -> str | None:
    """Call OAR with SECURITY_ANALYSIS task type (handles async)."""
    try:
        import asyncio

        from cores.ai.runtime import TaskType, get_oar

        async def _do_chat():
            oar = get_oar()
            if not oar._initialized:
                await oar.initialize()
            return await oar.chat(prompt, task_type=TaskType.SECURITY_ANALYSIS)

        try:
            asyncio.get_running_loop()
            # Already in async context — use thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _do_chat())
                response = future.result(timeout=60)
        except RuntimeError:
            response = asyncio.run(_do_chat())

        if response and hasattr(response, "content") and response.content:
            return response.content
    except Exception as e:
        logger.debug("OAR creative call failed: %s", e)
    return None


def _parse_llm_hypotheses(text: str, target_id: int, target_name: str) -> list[Hypothesis]:
    """Parse LLM JSON output into Hypothesis objects. Defensive against malformed output."""
    from uuid import NAMESPACE_OID, uuid5

    # Extract JSON array from response (LLM may wrap in ```json blocks)
    text = text.strip()
    if "```" in text:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            text = text[start:end]

    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        logger.debug("Creative LLM output is not valid JSON")
        return []

    if not isinstance(items, list):
        return []

    type_map = {
        "business_logic": VulnerabilityType.RATE_LIMIT_BYPASS,
        "auth_chain": VulnerabilityType.AUTH_BYPASS,
        "race_condition": VulnerabilityType.RATE_LIMIT_BYPASS,
        "privilege_escalation": VulnerabilityType.PRIVILEGE_ESCALATION,
        "mass_assignment": VulnerabilityType.DATA_EXPOSURE,
    }

    hypotheses = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        vtype_str = str(item.get("vulnerability_type", "other")).lower().replace(" ", "_").replace("-", "_")
        vtype = type_map.get(vtype_str, VulnerabilityType.DATA_EXPOSURE)

        likelihood = min(1.0, max(0.0, float(item.get("likelihood", 0.5))))
        impact = min(1.0, max(0.0, float(item.get("impact", 0.5))))

        h = Hypothesis(
            id=str(uuid5(NAMESPACE_OID, f"creative-{target_id}-{i}")),
            vulnerability_type=vtype,
            target_id=target_id,
            target_name=target_name,
            endpoint={
                "path": str(item.get("endpoint", "")),
                "method": str(item.get("method", "GET")).upper(),
                "source": "creative_llm",
            },
            likelihood=round(likelihood, 2),
            impact=round(impact, 2),
            exploitability=round(likelihood * 0.9, 2),
            confidence=round(0.6 + likelihood * 0.3, 2),
            priority_score=round(likelihood * impact * 100, 1),
            evidence=[item.get("reasoning", "")],
            reasoning=item.get("reasoning", ""),
            suggested_actions=[item.get("suggested_test", "")],
            source=HypothesisSource.LLM,
            vector=f"creative:{vtype_str}",
        )
        hypotheses.append(h)

    return hypotheses


def _summarize_endpoints(endpoints: list[dict[str, Any]]) -> str:
    lines = []
    for ep in endpoints:
        path = ep.get("path", "")
        method = ep.get("method", "")
        params = ep.get("params", [])
        labels = ep.get("labels", [])
        sig = f"{method} {path}"
        if params:
            sig += f" params={params}"
        if labels:
            sig += f" labels={labels}"
        lines.append(sig)
    return "\n".join(lines[:20])
