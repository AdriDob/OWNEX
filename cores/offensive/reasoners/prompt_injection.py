"""Prompt Injection Reasoner — detects LLM/AI-exposed endpoints.

Analyzes endpoints for conversational/AI surface (chat, completions, prompt,
generate, agent, assistant...). Generates hypotheses with confidence scores,
test instructions, and alternative explanations — exactly what a human
triager would consider.

Scope honesty: flags AI-exposed surface for AUTHORIZED targets only. Prompt
injection testing happens solely inside a program's scope or on your own
deployments — never against third-party AI products outside a bounty scope.
"""

from __future__ import annotations

import logging
from typing import Any

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import PROMPT_INJECTION_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.prompt_injection")

# Path fragments suggesting an LLM-backed endpoint — higher = stronger signal
AI_PATH_KEYWORDS: dict[str, float] = {
    "chat": 0.9,
    "completions": 0.95,
    "completion": 0.9,
    "prompt": 0.9,
    "generate": 0.7,
    "inference": 0.8,
    "assistant": 0.85,
    "agent": 0.85,
    "chatbot": 0.9,
    "copilot": 0.8,
    "playground": 0.75,
    "ask": 0.6,
    "talk": 0.55,
    "respond": 0.55,
    "messages": 0.6,
    "ai": 0.5,
    "llm": 0.85,
    "openai": 0.7,
    "anthropic": 0.7,
    "gemini": 0.7,
    "gpt": 0.65,
}

# Parameter names carrying user text into the model — higher = more control
PROMPT_PARAM_KEYWORDS: dict[str, float] = {
    "prompt": 0.95,
    "message": 0.8,
    "messages": 0.85,
    "query": 0.7,
    "input": 0.7,
    "user_input": 0.85,
    "instruction": 0.9,
    "instructions": 0.9,
    "system": 0.85,
    "system_prompt": 0.95,
    "context": 0.6,
    "question": 0.7,
    "text": 0.5,
    "content": 0.55,
}


class PromptInjectionReasoner(BaseReasoner):
    """Analyzes endpoints for prompt injection / LLM abuse surface."""

    @property
    def vulnerability_type(self) -> str:
        return "prompt_injection"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        # ── Signal 1: AI path fragments ──────────────────────────
        path_lower = endpoint.path.lower()
        for frag, score in AI_PATH_KEYWORDS.items():
            if frag in path_lower:
                signals.append(f"Path suggests LLM endpoint: {frag}")
                confidence += score * 0.4

        # ── Signal 2: prompt-carrying params (query + path) ──────
        for qp in list(endpoint.query_params) + list(endpoint.path_params):
            key = qp.lower()
            if key in PROMPT_PARAM_KEYWORDS:
                signals.append(f"Parameter feeds model input: {qp}")
                params_of_interest.append(qp)
                confidence += PROMPT_PARAM_KEYWORDS[key] * 0.35

        # ── Signal 3: prompt-carrying body keys ──────────────────
        if endpoint.body:
            for bk in endpoint.body:
                key = str(bk).lower()
                if key in PROMPT_PARAM_KEYWORDS:
                    signals.append(f"Body key feeds model input: {bk}")
                    params_of_interest.append(str(bk))
                    confidence += PROMPT_PARAM_KEYWORDS[key] * 0.3

        # ── Signal 4: system/config params user-controllable ─────
        sensitive = {"system", "system_prompt", "instruction", "instructions"}
        exposed = [p for p in params_of_interest if p.lower() in sensitive]
        if exposed:
            signals.append(f"System-level input exposed to caller: {exposed[0]}")
            confidence += 0.25

        # ── Build hypothesis if confidence is meaningful ─────────
        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        severity = "high" if exposed else ("medium" if confidence >= 0.4 else "low")

        hypothesis = Hypothesis(
            vulnerability_type="prompt_injection",
            endpoint=endpoint.path,
            method=endpoint.method,
            confidence=confidence,
            severity=severity,
            summary=self._build_summary(endpoint, params_of_interest),
            description=self._build_description(endpoint, params_of_interest),
            why_human_would_investigate=self._build_triager_justification(endpoint, params_of_interest, signals),
            parameters_of_interest=params_of_interest,
            signals=signals,
            test_instructions=self._build_test_instructions(endpoint, params_of_interest),
            alternative_explanations=self._build_alternatives(),
            scope_check=self._scope_check(endpoint),
            reproducibility_notes=self._reproducibility_notes(params_of_interest),
        )

        return [hypothesis]

    def _build_summary(self, endpoint: EndpointInfo, params: list[str]) -> str:
        refs = ", ".join(params[:3])
        return f"Potential prompt injection via {refs} on {endpoint.method} {endpoint.path}"

    def _build_description(self, endpoint: EndpointInfo, params: list[str]) -> str:
        refs = ", ".join(params[:4])
        return (
            f"The endpoint {endpoint.method} {endpoint.path} forwards caller-controlled "
            f"text ({refs}) into a language model. If model instructions, retrieved "
            f"context, or tool calls can be steered by that input, an attacker may "
            f"override intended behavior, extract system instructions, or abuse "
            f"connected tools and data."
        )

    def _build_triager_justification(self, endpoint: EndpointInfo, params: list[str], signals: list[str]) -> str:
        return (
            f"A human triager would investigate this because: "
            f"{endpoint.method} {endpoint.path} exposes {params[0] if params else 'model input'} "
            f"directly to an LLM ({len(signals)} AI-surface indicators). "
            f"Prompt injection reports grew 540% YoY with dedicated AI-scope programs "
            f"paying for them — a quick scoped test confirms or rules it out."
        )

    def _build_test_instructions(self, endpoint: EndpointInfo, params: list[str]) -> list[str]:
        instructions = [
            "Confirm the endpoint is inside the program's AI scope before testing.",
            "Try a direct instruction override in the main input (e.g., ask the model "
            "to ignore prior instructions and repeat a marker word).",
            "Try role-play framing that reassigns the assistant's role or rules.",
        ]
        for param in params[:2]:
            instructions.append(
                f"For {param}: attempt system-instruction extraction "
                f"(ask what rules it follows) and indirect injection via any "
                f"retrieved content the endpoint includes (URLs, documents, tool output)."
            )
        instructions.append(
            "If the model obeys injected instructions, leaks system content, or "
            "performs unauthorized tool actions — document the full transcript as PoC."
        )
        return instructions

    def _build_alternatives(self) -> list[dict[str, Any]]:
        return [
            {
                "label": alt["label"],
                "description": alt["description"],
                "how_to_rule_out": alt["how_to_rule_out"],
            }
            for alt in PROMPT_INJECTION_ALTERNATIVES.get("prompt_injection", [])
        ]

    def _scope_check(self, endpoint: EndpointInfo) -> str:
        return (
            f"Verify that {endpoint.path} is inside the program's AI scope and that "
            f"LLM testing is explicitly allowed. Test ONLY authorized targets or your "
            f"own deployments — never third-party AI products outside a bounty scope."
        )

    def _reproducibility_notes(self, params: list[str]) -> str:
        param = params[0] if params else "the input"
        return (
            f"Send a fixed benign prompt plus an injected instruction through {param}, "
            f"record the full transcript. Re-run with a fresh session: if the injected "
            f"behavior reproduces, the issue is reproducible."
        )


# ── F3: AI-audit methodology (pure, never executes) ──────────────
# Discovery inventory + tool-authZ matrix + RAG playbook. The human (or a
# scoped agent run) executes; these functions only map and prioritize.

# Tool-call surface: params/paths showing the agent can ACT, not just chat
TOOL_KEYWORDS: dict[str, float] = {
    "tool": 0.8,
    "tools": 0.8,
    "function": 0.7,
    "function_call": 0.9,
    "execute": 0.85,
    "run_action": 0.85,
    "action": 0.6,
    "mcp": 0.9,
    "webhook": 0.75,
    "send_email": 0.85,
    "send": 0.5,
    "query_db": 0.85,
    "database": 0.6,
    "shell": 0.9,
    "code_execution": 0.95,
    "browser": 0.6,
}

# RAG surface: retrieval-augmented inputs an attacker may poison
RAG_KEYWORDS: dict[str, float] = {
    "retrieve": 0.85,
    "retrieval": 0.85,
    "embed": 0.8,
    "embedding": 0.8,
    "vector": 0.75,
    "index": 0.6,
    "chunk": 0.7,
    "document": 0.6,
    "upload": 0.65,
    "ingest": 0.85,
    "knowledge": 0.6,
    "context_docs": 0.8,
    "search_docs": 0.8,
}

MAX_AI_SURFACE = 30


def _names_lower(endpoint: EndpointInfo) -> list[str]:
    out: list[str] = list(endpoint.query_params) + list(endpoint.path_params)
    if endpoint.body:
        out.extend(str(k) for k in endpoint.body)
    out.extend(str(k) for k in (endpoint.headers or {}))
    return [n.lower() for n in out]


def discover_ai_surface(endpoints: list[EndpointInfo]) -> list[dict[str, Any]]:
    """Ranked AI-surface inventory for a target. Pure, deterministic, capped.

    Scores path fragments (AI_PATH_KEYWORDS) + prompt params + tool signals
    + RAG signals. Returns endpoint dicts with ai_score, params, tool_hits,
    rag_hits — the input for matrix + playbook + weekly IA shot.
    """
    out: list[dict[str, Any]] = []
    for ep in endpoints or []:
        if not isinstance(ep, EndpointInfo):
            continue
        score = 0.0
        path_lower = ep.path.lower()
        for frag, weight in AI_PATH_KEYWORDS.items():
            if frag in path_lower:
                score += weight * 0.4
        names = _names_lower(ep)
        prompt_params = [n for n in names if n in PROMPT_PARAM_KEYWORDS]
        for p in prompt_params:
            score += PROMPT_PARAM_KEYWORDS[p] * 0.35
        tool_hits = sorted({n for n in names if n in TOOL_KEYWORDS} | {f for f in TOOL_KEYWORDS if f in path_lower})
        for t in tool_hits:
            score += TOOL_KEYWORDS.get(t, 0.5) * 0.3
        rag_hits = sorted({n for n in names if n in RAG_KEYWORDS} | {f for f in RAG_KEYWORDS if f in path_lower})
        for r in rag_hits:
            score += RAG_KEYWORDS.get(r, 0.5) * 0.3
        if score < 0.1 or not prompt_params:
            continue
        out.append(
            {
                "endpoint": ep.path,
                "method": ep.method,
                "ai_score": round(min(score, 1.0), 3),
                "prompt_params": prompt_params,
                "tool_hits": tool_hits,
                "rag_hits": rag_hits,
            }
        )
    out.sort(key=lambda d: d["ai_score"], reverse=True)
    return out[:MAX_AI_SURFACE]


def build_tool_matrix(surface: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tool-authZ matrix: per tool-hit, what to test and as whom. Pure.

    Each case: invoke the tool path as low principal, compare against owner,
    check whether the tool enforces the CALLER's permissions or the AGENT's.
    Human executes with own accounts; two transcripts = PoC.
    """
    cases: list[dict[str, Any]] = []
    for entry in surface or []:
        for tool in entry.get("tool_hits", []):
            for principal in ("low", "owner"):
                cases.append(
                    {
                        "endpoint": entry.get("endpoint"),
                        "method": entry.get("method"),
                        "tool": tool,
                        "principal": principal,
                        "action": (
                            f"As {principal}: steer the agent to invoke '{tool}' on another "
                            f"principal's data via {entry.get('endpoint')}; record transcript. "
                            f"Then repeat as the other role and diff: tool honoring agent "
                            f"perms over caller perms = authZ flaw."
                        ),
                        "priority": "P1" if tool in ("code_execution", "shell", "mcp", "function_call") else "P2",
                    }
                )
        if len(cases) >= MAX_AI_SURFACE:
            break
    return cases[:MAX_AI_SURFACE]


def rag_poisoning_playbook(surface: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordered RAG-poisoning procedure per rag-bearing endpoint. Pure.

    Stages: map ingestible sources → plant canary instruction → trigger via
    prompt param → verify canary fired → measure blast radius on own data
    only. Never poison shared/third-party corpora.
    """
    steps: list[dict[str, Any]] = []
    for entry in surface or []:
        rag = entry.get("rag_hits", [])
        if not rag:
            continue
        param = (entry.get("prompt_params") or ["input"])[0]
        steps.append(
            {
                "endpoint": entry.get("endpoint"),
                "method": entry.get("method"),
                "rag_via": rag,
                "stages": [
                    f"Map ingestible sources feeding {entry.get('endpoint')} (uploads, URLs, docs, tickets you own).",
                    f"Plant a canary instruction (unique marker word) ONLY in your own source via {', '.join(rag[:3])}.",
                    f"Trigger retrieval with a benign query through '{param}' and check if the canary fires.",
                    "If it fires: test a policy boundary (refuse vs obey) with reversible, benign content.",
                    "Measure blast radius on own data only; transcript everything for the report.",
                ],
            }
        )
    return steps
