from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="promptfoo",
    name="PromptFoo Eval",
    version="1.0.0",
    description="Evaluation, testing, and red-teaming for LLM outputs. "
    "Automatically runs test suites against every agent prompt, "
    "detects regressions, measures quality scores, and generates "
    "human-readable evaluation reports for OWNEX AI operations.",
    author="OWNEX",
    icon="ShieldCheck",
    capabilities=[
        Capability(domain="prompt_testing",
            name="Prompt Testing",
            description="Run automated test suites against agent prompts",
        ),
        Capability(domain="regression_detection",
            name="Regression Detection",
            description="Automatically detect quality regressions in prompts",
        ),
        Capability(domain="eval_reporting",
            name="Evaluation Reports",
            description="Generate human-readable quality evaluation reports",
        ),
        Capability(domain="red_teaming",
            name="Red Teaming",
            description="Automated adversarial testing of LLM outputs",
        ),
    ],
    hooks={
        "evaluate_prompt": "promptfoo.hooks.on_evaluate_prompt",
        "eval_run": "promptfoo.hooks.on_eval_run",
    },
    providers=["promptfoo_evaluator"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
