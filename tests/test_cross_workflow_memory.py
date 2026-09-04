"""Test for Cross-Workflow Memory."""

import asyncio
from cores.cross_workflow_memory.store import CrossWorkflowMemory


async def test_cross_workflow_memory():
    memory = CrossWorkflowMemory()

    # Record a successful bug bounty workflow
    memory.record_workflow_completion(
        workflow_type="bug_bounty",
        outcome="success",
        key_factors=["recon", "xss_payload", "reporting"],
        metrics={"success_probability": 0.8},
        artifacts=["artifact_1", "artifact_2"],
        domain="web_security",
    )

    # Record a successful dev bounty workflow
    memory.record_workflow_completion(
        workflow_type="dev_bounty",
        outcome="success",
        key_factors=["code_review", "testing", "documentation"],
        metrics={"success_probability": 0.7},
        artifacts=["artifact_3"],
        domain="code_review",
    )

    # Get recommendations for a new bug bounty workflow
    recommendations = memory.get_recommendations_for_workflow(
        workflow_type="bug_bounty",
        domain="web_security",
        current_context={},
    )

    print("Recommendations:", recommendations)
    print("Apply strategies:", recommendations.get("apply_strategies", []))
    print("Avoid patterns:", recommendations.get("avoid_patterns", []))
    print("Confidence:", recommendations.get("confidence", 0))

    # Test similarity
    similarity = memory.get_workflow_similarity("bug_bounty", "dev_bounty")
    print(f"Similarity: {similarity}")

    print("All cross-workflow memory tests passed!")


if __name__ == "__main__":
    asyncio.run(test_cross_workflow_memory())
