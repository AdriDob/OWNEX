from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="langfuse",
    name="Langfuse Observability",
    version="1.0.0",
    description="Open-source LLM observability, evals, and prompt management. "
    "Every agent call, tool execution, and LLM interaction is traced, "
    "scored, and analyzable. Includes prompt playground, dataset "
    "management, and cost tracking for all OWNEX AI operations.",
    author="OWNEX",
    icon="Activity",
    capabilities=[
        Capability(domain="llm_tracing",
            name="LLM Tracing",
            description="Full trace of every LLM call: prompt, response, latency, cost",
        ),
        Capability(domain="prompt_management",
            name="Prompt Management",
            description="Versioned prompt templates with playground testing",
        ),
        Capability(domain="evaluation",
            name="Evaluation & Scoring",
            description="Score agent outputs, track quality metrics over time",
        ),
        Capability(domain="cost_tracking",
            name="Cost Tracking",
            description="Track LLM costs per agent, per session, per workflow",
        ),
    ],
    hooks={
        "llm_call": "langfuse.hooks.on_llm_call",
        "agent_action": "langfuse.hooks.on_agent_action",
        "evaluation_score": "langfuse.hooks.on_evaluation_score",
    },
    providers=["langfuse_observer"],
    hot_reloadable=False,
    requires_core="5.0.0",
)
