#!/usr/bin/env python3
"""
Example: MERLIN Assistant Integration

This example demonstrates how to interact with MERLIN,
OWNEX's intelligent assistant with persistent memory.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.memory import MemoryStore
from core.ai.merlin import Merlin


async def main():
    """Run MERLIN assistant example."""

    print("🧠 OWNEX MERLIN Assistant Example")
    print("=" * 50)

    # Initialize MERLIN
    merlin = Merlin()
    memory = MemoryStore()

    # Example 1: Basic chat
    print("\n💬 Basic Chat:")
    print("-" * 30)

    questions = [
        "What are my current active bug bounty targets?",
        "Analyze my revenue performance this month",
        "Suggest optimal task allocation for tomorrow",
        "What vulnerabilities should I prioritize?",
    ]

    for question in questions:
        print(f"\n👤 You: {question}")
        try:
            response = await merlin.chat(question, context="security_research")
            print(f"🤖 MERLIN: {response[:200]}...")
        except Exception as e:
            print(f"   (Demo mode - requires configured system: {e})")

    # Example 2: Context-aware assistance
    print("\n\n🎯 Context-Aware Assistance:")
    print("-" * 30)

    # Store some context
    await memory.store(
        namespace="user_preferences", key="focus_areas", value=["web_security", "api_testing", "smart_contracts"]
    )

    await memory.store(
        namespace="session_context", key="current_targets", value=["target1.com", "target2.io", "target3.org"]
    )

    # Ask with context
    print("\n👤 You: Based on my preferences and current targets, what should I focus on?")
    try:
        response = await merlin.chat(
            "Based on my preferences and current targets, what should I focus on?", context="personalized"
        )
        print(f"🤖 MERLIN: {response[:300]}...")
    except Exception as e:
        print(f"   (Demo mode - requires configured system: {e})")

    # Example 3: Task planning
    print("\n\n📋 Task Planning:")
    print("-" * 30)

    print("\n👤 You: Plan my bug bounty workflow for today")
    try:
        plan = await merlin.plan_workflow(
            goal="Complete bug bounty recon and initial testing", constraints={"hours": 4, "focus": "web_apps"}
        )
        print("🤖 MERLIN Workflow Plan:")
        for step in plan.steps[:5]:
            print(f"   {step.order}. {step.description} ({step.estimated_minutes} min)")
    except Exception as e:
        print(f"   (Demo mode - requires configured system: {e})")

    # Example 4: Learning from outcomes
    print("\n\n📈 Learning from Outcomes:")
    print("-" * 30)

    # Simulate outcome recording
    outcome = {
        "task": "recon_target1",
        "result": "found_xss",
        "effort_hours": 2.5,
        "reward": 500,
        "tools_used": ["nuclei", "ffuf", "burp"],
    }

    print(f"\n📝 Recording outcome: {outcome['result']} (${outcome['reward']})")
    try:
        await merlin.learn_from_outcome(outcome)
        print("✅ MERLIN updated its models with this outcome")
    except Exception as e:
        print(f"   (Demo mode - requires configured system: {e})")

    print("\n✨ Example complete!")
    print("\n💡 In production, MERLIN:")
    print("   - Maintains persistent memory across sessions")
    print("   - Learns from every interaction")
    print("   - Provides context-aware recommendations")
    print("   - Integrates with all OWNEX cycles")


if __name__ == "__main__":
    asyncio.run(main())
