#!/usr/bin/env python3
"""
Example: Custom Autonomous Agent

This example demonstrates how to create a custom autonomous agent
that integrates with OWNEX's event bus and agent system.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents.base import BaseAgent
from core.cycles.base import CycleResult

from core.events import Event, EventBus


@dataclass
class CustomTask:
    """A task for our custom agent."""

    name: str
    params: dict[str, Any]
    priority: int = 1


class MyCustomAgent(BaseAgent):
    """
    Custom autonomous agent example.

    This agent demonstrates:
    - Event-driven architecture
    - Integration with OWNEX event bus
    - Task processing with results
    - Error handling and recovery
    """

    def __init__(self, event_bus: EventBus, config: dict[str, Any] = None):
        super().__init__(name="custom_analyzer", event_bus=event_bus, config=config or {})
        self.processed_count = 0
        self.results: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Custom analyzer agent initialized")

        # Subscribe to relevant events
        await self.subscribe("task.created", self.on_task_created)
        await self.subscribe("analysis.requested", self.on_analysis_requested)

    async def on_task_created(self, event: Event) -> None:
        """Handle new task creation."""
        task_data = event.data
        self.logger.info(f"Received new task: {task_data.get('name')}")

        # Process task asynchronously
        asyncio.create_task(self.process_task(CustomTask(**task_data)))

    async def on_analysis_requested(self, event: Event) -> None:
        """Handle analysis requests."""
        request = event.data
        self.logger.info(f"Analysis requested: {request.get('type')}")

        # Emit analysis started
        await self.emit(Event("analysis.started", {"request_id": request.get("id"), "agent": self.name}))

        # Perform analysis (placeholder)
        result = await self.analyze(request)

        # Emit analysis completed
        await self.emit(Event("analysis.completed", {"request_id": request.get("id"), "result": result}))

    async def process_task(self, task: CustomTask) -> dict[str, Any]:
        """Process a custom task."""
        self.logger.info(f"Processing task: {task.name}")

        # Emit task started
        await self.emit(Event("task.started", {"task_name": task.name, "agent": self.name}))

        try:
            # Simulate work
            await asyncio.sleep(0.1)  # Simulate processing

            # Generate result
            result = {
                "task_name": task.name,
                "status": "completed",
                "output": f"Processed {task.name} with params: {task.params}",
                "metrics": {"duration_ms": 100, "items_processed": len(task.params)},
            }

            self.results.append(result)
            self.processed_count += 1

            # Emit task completed
            await self.emit(Event("task.completed", {"task_name": task.name, "result": result}))

            return result

        except Exception as e:
            self.logger.error(f"Task failed: {e}")

            # Emit task failed
            await self.emit(Event("task.failed", {"task_name": task.name, "error": str(e)}))

            raise

    async def analyze(self, request: dict[str, Any]) -> dict[str, Any]:
        """Perform analysis based on request."""
        analysis_type = request.get("type", "general")
        data = request.get("data", {})

        # Simulate analysis
        await asyncio.sleep(0.05)

        return {
            "type": analysis_type,
            "summary": f"Analyzed {len(data)} items",
            "insights": [
                f"Pattern detected in {analysis_type}",
                "Optimization opportunity identified",
                "Risk level: Low",
            ],
            "confidence": 0.85,
        }

    async def execute_cycle(self, cycle_name: str, limit: int = 10) -> CycleResult:
        """Execute agent's main cycle."""
        self.logger.info(f"Executing {cycle_name} cycle")

        # Process pending tasks
        processed = 0
        for result in self.results[-limit:]:
            if result["status"] == "completed":
                processed += 1

        return CycleResult(
            cycle=cycle_name,
            processed=processed,
            success=True,
            details={"agent": self.name, "total_processed": self.processed_count},
        )

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        return {
            "name": self.name,
            "processed_count": self.processed_count,
            "results_count": len(self.results),
            "status": "running" if self._running else "stopped",
        }


async def main():
    """Run custom agent example."""

    print("🤖 OWNEX Custom Agent Example")
    print("=" * 50)

    # Create event bus
    event_bus = EventBus()

    # Create custom agent
    agent = MyCustomAgent(event_bus, config={"debug": True})

    # Initialize
    await agent.initialize()
    await agent.start()

    print(f"\n✅ Agent started: {agent.name}")
    print(f"   Status: {agent.get_stats()['status']}")

    # Create some tasks
    tasks = [
        CustomTask("analyze_logs", {"source": "api", "lines": 1000}),
        CustomTask("scan_endpoints", {"targets": ["api", "web", "admin"]}),
        CustomTask("check_vulnerabilities", {"cves": ["CVE-2024-1234", "CVE-2024-5678"]}),
        CustomTask("generate_report", {"format": "markdown", "include": "all"}),
    ]

    print(f"\n📋 Submitting {len(tasks)} tasks...")

    # Emit task created events
    for task in tasks:
        await event_bus.emit(
            Event("task.created", {"name": task.name, "params": task.params, "priority": task.priority})
        )

    # Wait for processing
    await asyncio.sleep(0.5)

    # Request analysis
    print("\n🔍 Requesting analysis...")
    await event_bus.emit(
        Event(
            "analysis.requested",
            {"id": "analysis_001", "type": "security_posture", "data": {"endpoints": 15, "findings": 3, "critical": 1}},
        )
    )

    await asyncio.sleep(0.2)

    # Execute a cycle
    print("\n🔄 Executing agent cycle...")
    result = await agent.execute_cycle("custom_analysis", limit=5)
    print(f"   Cycle result: {result.details}")

    # Show stats
    print("\n📊 Agent Statistics:")
    print("-" * 30)
    stats = agent.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Show results
    print("\n📝 Task Results:")
    print("-" * 30)
    for result in agent.results:
        print(f"   ✅ {result['task_name']}: {result['metrics']['duration_ms']}ms")

    # Stop agent
    await agent.stop()
    print(f"\n🛑 Agent stopped: {agent.name}")

    print("\n✨ Example complete!")
    print("\n💡 Key integration points:")
    print("   - EventBus for communication")
    print("   - BaseAgent for lifecycle management")
    print("   - CycleResult for cycle execution")
    print("   - Event emission for observability")


if __name__ == "__main__":
    asyncio.run(main())
