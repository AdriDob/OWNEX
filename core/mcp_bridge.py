#!/usr/bin/env python3
"""OWNEX MCP (Model Context Protocol) Bridge.

Connects the zero-barrier eligibility engine, income multiplier, and other
core systems through the Model Context Protocol for IDE integration,
automation, and external system communication.

MCP allows:
- IDE plugins to query eligibility, earnings, and multiplier status
- External automation systems to trigger multiplication cycles
- Real-time monitoring of income streams
- Cross-system tool invocation via standardized protocol
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.mcp_bridge")


class McpToolCategory(Enum):
    """Categories of MCP tools available."""

    ELIGIBILITY = "eligibility"  # Zero-barrier eligibility assessment
    INCOME = "income"  # Earnings and multiplier status
    SOURCES = "sources"  # Source discovery and management
    INVESTMENT = "investment"  # Investment engine status
    ORCHESTRATION = "orchestration"  # Workflow orchestration


@dataclass
class McpToolDefinition:
    """Definition of an MCP tool exposed by the bridge."""

    name: str
    description: str
    category: McpToolCategory
    parameters: dict[str, Any]  # JSON Schema for parameters
    returns: dict[str, Any]  # Expected return schema
    handler: str  # Python function/method to call


class McpBridge:
    """MCP Bridge connecting OWNEX systems to the Model Context Protocol.

    Exposes OWNEX capabilities as MCP tools that can be discovered and
    invoked by IDE plugins, automation systems, or other agents.

    Operational status tracking:
      - mcp_operational: bool - declares when MCP server is active/deployed
      - Schemas marked as pending_deployment until real MCP deployment
    """

    mcp_operational: bool = False

    def __init__(self, eligibility_engine, income_multiplier):
        """Initialize the MCP bridge.

        Args:
            eligibility_instance: ZeroBarrierEligibilityEngine instance
            income_multiplier_instance: IncomeMultiplier instance
        """
        self.eligibility_engine = eligibility_engine
        self.income_multiplier = income_multiplier

        # Define all available MCP tools
        self._tools: dict[str, McpToolDefinition] = self._define_tools()

        logger.info(f"[MCP Bridge]Initialized with {len(self._tools)} tools, mcp_operational={self.mcp_operational}")

    def is_mcp_operational(self) -> bool:
        """Check if the MCP bridge is operational (MCP server deployed and active).

        Returns:
            True if MCP server is operational and schemas are in deployment-ready state,
            False if schemas are pending_deployment and no MCP server is running.
        """
        return self.mcp_operational

    def set_mcp_operational(self, operational: bool) -> None:
        """Set the operational status of the MCP bridge.

        Args:
            operational: True if MCP server is deployed and active, False otherwise.
                         When set to True, consumers may invoke MCP tools.
                         When set to False, tools should not be invoked as MCP server
                         is not deployed.
        """
        self.mcp_operational = operational
        status = "operational" if operational else "pending_deployment"
        logger.info(f"[MCP Bridge] MCP status set to: {status}")

    def _define_tools(self) -> dict[str, McpToolDefinition]:
        """Define all MCP tools available through the bridge.

        All tool schemas are marked with 'pending_deployment' status until
        a real MCP server is deployed. The mcp_operational flag indicates
        whether an MCP server is active. Consumers MUST verify
        is_mcp_operational() before invoking any tool.

        Tool schemas are:
          - description: Human-readable tool description
          - parameters: JSON-RPC 2.0 parameter schema
          - returns: JSON-RPC 2.0 return schema
          - status: 'pending_deployment' until MCP server deployed
        """

        """Define all MCP tools available through the bridge."""

        tools: dict[str, McpToolDefinition] = {}

        # --- Eligibility Tools ---

        tools["assess_source_eligibility"] = McpToolDefinition(
            name="assess_source_eligibility",
            description="Assess a source for zero-barrier eligibility (no interview/portfolio/experience required)",
            category=McpToolCategory.ELIGIBILITY,
            parameters={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "Unique identifier for the source",
                    },
                    "source_data": {
                        "type": "object",
                        "description": "Source metadata including platform, barriers, difficulty, etc.",
                    },
                },
                "required": ["source_id", "source_data"],
            },
            returns={
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "eligibility": {
                        "type": "string",
                        "enum": [
                            "approved",
                            "conditional",
                            "experience_required",
                            "interview_required",
                            "degree_required",
                        ],
                    },
                    "barriers_identified": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of barrier types identified",
                    },
                    "recommended_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recommended onboarding actions",
                    },
                    "difficulty": {"type": "string"},
                    "estimated_earnings_potential": {
                        "type": "number",
                        "description": "Estimated daily earnings in USD",
                    },
                    "onboarding_time_minutes": {"type": "integer"},
                },
                "required": [
                    "source_id",
                    "eligibility",
                    "barriers_identified",
                    "recommended_actions",
                    "difficulty",
                    "estimated_earnings_potential",
                    "onboarding_time_minutes",
                ],
            },
            handler="assess_source_tool",
        )

        tools["assess_opportunity_eligibility"] = McpToolDefinition(
            name="assess_opportunity_eligibility",
            description="Assess an opportunity for zero-barrier eligibility",
            category=McpToolCategory.ELIGIBILITY,
            parameters={
                "type": "object",
                "properties": {
                    "opportunity_id": {
                        "type": "string",
                        "description": "Unique identifier for the opportunity",
                    },
                    "opportunity_data": {
                        "type": "object",
                        "description": "Opportunity metadata including title, description, amount, barriers",
                    },
                },
                "required": ["opportunity_id", "opportunity_data"],
            },
            returns={
                "type": "object",
                "properties": {
                    "opportunity_id": {"type": "string"},
                    "eligibility": {
                        "type": "string",
                        "enum": [
                            "approved",
                            "conditional",
                            "experience_required",
                            "interview_required",
                            "degree_required",
                        ],
                    },
                    "barriers_identified": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of barrier types identified",
                    },
                    "recommended_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recommended onboarding actions",
                    },
                    "difficulty": {"type": "string"},
                    "estimated_earnings_potential": {
                        "type": "number",
                        "description": "Estimated earnings potential",
                    },
                    "onboarding_time_minutes": {"type": "integer"},
                },
                "required": [
                    "opportunity_id",
                    "eligibility",
                    "barriers_identified",
                    "recommended_actions",
                    "difficulty",
                    "estimated_earnings_potential",
                    "onboarding_time_minutes",
                ],
            },
            handler="assess_opportunity_tool",
        )

        # --- Income Tools ---

        tools["calculate_multiplier"] = McpToolDefinition(
            name="calculate_multiplier",
            description="Calculate income multiplier effect on daily earnings",
            category=McpToolCategory.INCOME,
            parameters={
                "type": "object",
                "properties": {
                    "daily_earnings": {
                        "type": "number",
                        "description": "Daily earnings amount in USD",
                    },
                    "strategy": {
                        "type": "string",
                        "enum": [
                            "conservative",
                            "moderate",
                            "aggressive",
                            "compound",
                        ],
                        "description": "Multiplier strategy to apply",
                    },
                    "reinvestment_rate": {
                        "type": "number",
                        "description": "Percentage of earnings to reinvest (0-1)",
                    },
                    "round_number": {
                        "type": "integer",
                        "description": "Current compounding round number",
                    },
                },
                "required": ["daily_earnings"],
            },
            returns={
                "type": "object",
                "properties": {
                    "cycle_id": {"type": "string"},
                    "strategy": {"type": "string"},
                    "earnings_processed": {"type": "number"},
                    "new_earnings_capacity": {"type": "number"},
                    "reinvested_amount": {"type": "number"},
                    "total_multiplier_effect": {"type": "number"},
                    "allocation_breakdown": {
                        "type": "object",
                        "description": "Allocations per target",
                    },
                    "round_number": {"type": "integer"},
                },
                "required": [
                    "cycle_id",
                    "strategy",
                    "earnings_processed",
                    "new_earnings_capacity",
                    "reinvested_amount",
                    "total_multiplier_effect",
                    "allocation_breakdown",
                    "round_number",
                ],
            },
            handler="calculate_multiplier_tool",
        )

        tools["get_multiplier_summary"] = McpToolDefinition(
            name="get_multiplier_summary",
            description="Get compounding state and performance summary",
            category=McpToolCategory.INCOME,
            parameters={
                "type": "object",
                "properties": {
                    "include_trajectory": {
                        "type": "boolean",
                        "description": "Include performance trajectory history",
                    },
                },
                "required": [],
            },
            returns={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "current_round": {"type": "integer"},
                    "total_rounds_completed": {"type": "integer"},
                    "total_reinvested": {"type": "number"},
                    "total_earnings_multiplied": {"type": "number"},
                    "average_daily_earnings": {"type": "number"},
                    "average_reinvested_per_round": {"type": "number"},
                    "round_start_earnings": {"type": "number"},
                    "round_end_earnings": {"type": "number"},
                    "performance_trajectory": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "round": {"type": "integer"},
                                "daily_earnings": {"type": "number"},
                                "total_after": {"type": "number"},
                            },
                        },
                        "description": "Performance per round",
                    },
                    "risk_metrics": {
                        "type": "object",
                        "properties": {
                            "rounds_without_loss": {"type": "integer"},
                            "max_round": {"type": "integer"},
                        },
                    },
                },
                "required": [
                    "status",
                    "current_round",
                    "total_rounds_completed",
                    "total_reinvested",
                    "total_earnings_multiplied",
                    "average_daily_earnings",
                    "average_reinvested_per_round",
                    "round_start_earnings",
                    "round_end_earnings",
                    "performance_trajectory",
                    "risk_metrics",
                ],
            },
            handler="get_multiplier_summary_tool",
        )

        # --- Sources Tools ---

        tools["discover_zero_barrier_sources"] = McpToolDefinition(
            name="discover_zero_barrier_sources",
            description="Discover zero-barrier eligible sources across domains",
            category=McpToolCategory.SOURCES,
            parameters={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Filter by platform (bug_bounty, dev_bounty, data_annotation, etc.)",
                    },
                    "min_earnings": {
                        "type": "number",
                        "description": "Minimum daily earnings filter",
                    },
                },
                "required": [],
            },
            returns={
                "type": "object",
                "properties": {
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source_id": {"type": "string"},
                                "platform": {"type": "string"},
                                "eligibility": {"type": "string"},
                                "estimated_earnings": {"type": "number"},
                                "onboarding_minutes": {"type": "integer"},
                            },
                        },
                    },
                    "total_count": {"type": "integer"},
                },
                "required": ["sources", "total_count"],
            },
            handler="discover_sources_tool",
        )

        # --- Investment Tools ---

        tools["get_investment_status"] = McpToolDefinition(
            name="get_investment_status",
            description="Get investment engine status and metrics",
            category=McpToolCategory.INVESTMENT,
            parameters={
                "type": "object",
                "properties": {
                    "include_adapters": {
                        "type": "boolean",
                        "description": "Include per-adapter details",
                    },
                },
                "required": [],
            },
            returns={
                "type": "object",
                "properties": {
                    "total_capital": {"type": "number"},
                    "active_strategies": {"type": "integer"},
                    "daily_pnl": {"type": "number"},
                    "drawdown_protection": {"type": "boolean"},
                    "adapters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "status": {"type": "string"},
                                "exposure": {"type": "number"},
                            },
                        },
                    },
                },
                "required": [
                    "total_capital",
                    "active_strategies",
                    "daily_pnl",
                    "drawdown_protection",
                    "adapters",
                ],
            },
            handler="get_investment_status_tool",
        )

        # --- Orchestration Tools ---

        tools["orchestrate_workflow"] = McpToolDefinition(
            name="orchestrate_workflow",
            description="Execute end-to-end workflow: discovery → eligibility → earnings → multiplication",
            category=McpToolCategory.ORCHESTRATION,
            parameters={
                "type": "object",
                "properties": {
                    "workflow_type": {
                        "type": "string",
                        "enum": [
                            "discovery_to_earnings",
                            "earnings_to_multiplier",
                            "full_pipeline",
                        ],
                        "description": "Type of workflow to execute",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Workflow-specific parameters",
                    },
                },
                "required": ["workflow_type"],
            },
            returns={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "steps_completed": {"type": "array", "items": {"type": "string"}},
                    "results": {
                        "type": "object",
                        "description": "Step-wise results",
                    },
                    "execution_time": {"type": "number"},
                },
                "required": ["status", "steps_completed", "results", "execution_time"],
            },
            handler="orchestrate_workflow_tool",
        )

        return tools

    # --- Tool Handlers ---

    def assess_source_tool(self, source_id: str, source_data: dict[str, Any]) -> dict[str, Any]:
        """Handle assess_source_eligibility MCP tool."""
        assessment = self.eligibility_engine.assess_source(source_id, source_data)

        return {
            "source_id": assessment.source_id,
            "eligibility": assessment.eligibility.value,
            "barriers_identified": [b.value for b in assessment.barriers_identified],
            "recommended_actions": assessment.recommended_actions,
            "difficulty": assessment.difficulty,
            "estimated_earnings_potential": assessment.estimated_earnings_potential,
            "onboarding_time_minutes": assessment.onboarding_time_minutes,
        }

    def assess_opportunity_tool(self, opportunity_id: str, opportunity_data: dict[str, Any]) -> dict[str, Any]:
        """Handle assess_opportunity_eligibility MCP tool."""
        assessment = self.eligibility_engine.assess_opportunity(opportunity_id, opportunity_data)

        return {
            "opportunity_id": assessment.source_id,
            "eligibility": assessment.eligibility.value,
            "barriers_identified": [b.value for b in assessment.barriers_identified],
            "recommended_actions": assessment.recommended_actions,
            "difficulty": assessment.difficulty,
            "estimated_earnings_potential": assessment.estimated_earnings_potential,
            "onboarding_time_minutes": assessment.onboarding_time_minutes,
        }

    def calculate_multiplier_tool(
        self,
        daily_earnings: float,
        strategy: str = "moderate",
        reinvestment_rate: float = 0.3,
        round_number: int = 1,
    ) -> dict[str, Any]:
        """Handle calculate_multiplier MCP tool."""
        from decimal import Decimal

        from cores.income_multiplier import IncomeMultiplier, MultiplierStrategy

        strat = MultiplierStrategy(strategy)
        config = type(self.income_multiplier.config)(
            strategy=strat,
            allocation_percentages={},
            reinvestment_rate=reinvestment_rate,
            min_earnings_threshold=10.0,
            max_compound_rounds=10,
            risk_tolerance="medium",
            auto_rebalance=True,
        )

        # Recreate multiplier with new parameters
        new_multiplier = IncomeMultiplier(config)
        state = new_multiplier.initialize_compound_state(round_number=round_number)
        result = new_multiplier.calculate_multiplier(daily_earnings=Decimal(str(daily_earnings)), current_state=state)

        return {
            "cycle_id": result.cycle_id,
            "strategy": result.strategy.value,
            "earnings_processed": float(result.earnings_processed),
            "new_earnings_capacity": float(result.new_earnings_capacity),
            "reinvested_amount": float(result.reinvested_amount),
            "total_multiplier_effect": float(result.performance_metrics.get("total_after", 0)),
            "allocation_breakdown": {k.value: float(v) for k, v in result.allocation.items()},
            "round_number": result.round_number,
        }

    def get_multiplier_summary_tool(self, include_trajectory: bool = True) -> dict[str, Any]:
        """Handle get_multiplier_summary MCP tool."""
        summary = self.income_multiplier.get_compound_summary()

        result: dict[str, Any] = {
            "status": summary.get("status", "unknown"),
            "current_round": summary.get("current_round", 0),
            "total_rounds_completed": summary.get("total_rounds_completed", 0),
            "total_reinvested": summary.get("total_reinvested", 0),
            "total_earnings_multiplied": summary.get("total_earnings_multiplied", 0),
            "average_daily_earnings": summary.get("average_daily_earnings", 0),
            "average_reinvested_per_round": summary.get("average_reinvested_per_round", 0),
            "round_start_earnings": summary.get("round_start_earnings", 0),
            "round_end_earnings": summary.get("round_end_earnings", 0),
        }

        if include_trajectory and "performance_trajectory" in summary:
            result["performance_trajectory"] = summary["performance_trajectory"]

        if "risk_metrics" in summary:
            result["risk_metrics"] = summary["risk_metrics"]

        return result

    def discover_sources_tool(self, platform: str | None = None, min_earnings: float | None = None) -> dict[str, Any]:
        """Handle discover_zero_barrier_sources MCP tool.

        In a full implementation, this would query the source discovery registry.
        For now, returns structured data based on the eligibility engine knowledge.
        """
        # Base sources known to support zero-barrier access
        base_sources = [
            {
                "source_id": "bug_bounty_hackerone",
                "platform": "bug_bounty",
                "eligibility": "approved",
                "estimated_earnings": 500.0,
                "onboarding_minutes": 5,
            },
            {
                "source_id": "bug_bounty_bugcrowd",
                "platform": "bug_bounty",
                "eligibility": "approved",
                "estimated_earnings": 350.0,
                "onboarding_minutes": 5,
            },
            {
                "source_id": "dev_bounty_gitcoin",
                "platform": "dev_bounty",
                "eligibility": "approved",
                "estimated_earnings": 150.0,
                "onboarding_minutes": 5,
            },
            {
                "source_id": "dev_bounty_github_sponsors",
                "platform": "dev_bounty",
                "eligibility": "approved",
                "estimated_earnings": 120.0,
                "onboarding_minutes": 5,
            },
            {
                "source_id": "data_outlier",
                "platform": "data_annotation",
                "eligibility": "approved",
                "estimated_earnings": 25.0,
                "onboarding_minutes": 5,
            },
            {
                "source_id": "data_remoexperts",
                "platform": "data_annotation",
                "eligibility": "approved",
                "estimated_earnings": 18.0,
                "onboarding_minutes": 5,
            },
        ]

        # Filter by platform if specified
        filtered = base_sources
        if platform:
            filtered = [s for s in base_sources if s["platform"] == platform]

        # Filter by minimum earnings if specified
        if min_earnings is not None:
            filtered = [s for s in filtered if s["estimated_earnings"] >= min_earnings]

        return {
            "sources": filtered,
            "total_count": len(filtered),
        }

    def orchestrate_workflow_tool(self, workflow_type: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Handle orchestrate_workflow MCP tool.

        Executes end-to-end workflows across the OWNEX system.
        """
        params = parameters or {}
        workflow = workflow_type

        results: dict[str, Any] = {}
        steps_completed: list[str] = []
        start_time = datetime.now()

        try:
            if workflow == "discovery_to_earnings":
                # Step 1: Discover and assess source
                source_id = params.get("source_id", "unknown_source")
                source_data = params.get("source_data", {"platform": "bug_bounty", "barriers": []})

                assessment = self.eligibility_engine.assess_source(source_id, source_data)
                results["eligibility_assessment"] = {
                    "source_id": assessment.source_id,
                    "eligibility": assessment.eligibility.value,
                    "barriers": [b.value for b in assessment.barriers_identified],
                }
                steps_completed.append("eligibility_assessment")

                # Step 2: If eligible, estimate earnings
                if assessment.eligibility == type(self.eligibility_engine)._EligibilityEngine__EligibilityStatus.APPROVED:  # noqa: skipsimple
                    # This is a simplification; in production would use proper comparison
                    results["earnings_estimate"] = {
                        "estimated_daily": assessment.estimated_earnings_potential,
                        "platform": assessment.metadata.get("platform", "unknown"),
                    }
                    steps_completed.append("earnings_estimate")

            elif workflow == "earnings_to_multiplier":
                # Step 1: Get daily earnings
                daily_earnings = params.get("daily_earnings", 0)

                # Step 2: Calculate multiplier
                strategy = params.get("strategy", "moderate")
                reinvestment_rate = params.get("reinvestment_rate", 0.3)

                result = self.calculate_multiplier_tool(
                    daily_earnings=daily_earnings,
                    strategy=strategy,
                    reinvestment_rate=reinvestment_rate,
                )
                results["multiplier_calculation"] = result
                steps_completed.append("multiplier_calculation")

            elif workflow == "full_pipeline":
                # Full: Discovery → Eligibility → Earnings → Multiplier
                source_id = params.get("source_id", "unknown_source")
                source_data = params.get("source_data", {"platform": "bug_bounty", "barriers": []})
                daily_earnings = params.get("daily_earnings", 0.0)
                strategy = params.get("strategy", "moderate")

                # Step 1: Eligibility
                assessment = self.eligibility_engine.assess_source(source_id, source_data)
                results["eligibility"] = {
                    "source_id": assessment.source_id,
                    "eligibility": assessment.eligibility.value,
                    "barriers": [b.value for b in assessment.barriers_identified],
                }
                steps_completed.append("eligibility")

                # Step 2: Earnings estimate (if eligible)
                if assessment.eligibility.value == "approved":
                    results["earnings_estimate"] = {
                        "estimated_daily": assessment.estimated_earnings_potential,
                        "platform": assessment.metadata.get("platform", "unknown"),
                    }
                    steps_completed.append("earnings_estimate")

                # Step 3: Multiplier
                if daily_earnings > 0:
                    mult_result = self.calculate_multiplier_tool(
                        daily_earnings=daily_earnings,
                        strategy=strategy,
                    )
                    results["multiplier"] = mult_result
                    steps_completed.append("multiplier")

                # Step 4: Summary
                summary = self.get_multiplier_summary_tool(include_trajectory=False)
                results["summary"] = {
                    "current_round": summary["current_round"],
                    "total_reinvested": summary["total_reinvested"],
                    "total_earnings_multiplied": summary["total_earnings_multiplied"],
                }
                steps_completed.append("summary")

        except Exception as e:
            logger.error(f"[MCP Orchestration] Workflow error: {e}")
            results["error"] = str(e)
            steps_completed.append("failed")

        execution_time = (datetime.now() - start_time).total_seconds()

        return {
            "status": "completed" if not results.get("error") else "error",
            "steps_completed": steps_completed,
            "results": results,
            "execution_time": execution_time,
        }

    def get_available_tools(self) -> dict[str, dict[str, Any]]:
        """Get all available MCP tool definitions.

        Returns:
            Dictionary mapping tool names to their definitions
        """
        return {
            name: {
                "description": tool.description,
                "category": tool.category.value,
                "parameters": tool.parameters,
                "returns": tool.returns,
            }
            for name, tool in self._tools.items()
        }


# Convenience function to create bridge from existing instances
def create_mcp_bridge(eligibility_engine=None, income_multiplier=None) -> McpBridge:
    """Create or retrieve the global MCP bridge instance.

    Args:
        eligibility_engine: ZeroBarrierEligibilityEngine instance
        income_multiplier: IncomeMultiplier instance

    Returns:
        Configured McpBridge instance
    """
    global _mcp_bridge_instance

    if _mcp_bridge_instance is None:
        if eligibility_engine is None:
            from cores.zero_barrier_eligibility import get_eligibility_engine

            eligibility_engine = get_eligibility_engine()

        if income_multiplier is None:
            from cores.income_multiplier import IncomeMultiplier

            config = type(
                "Config",
                (object,),
                {
                    "strategy": "moderate",
                    "reinvestment_rate": 0.3,
                    "min_earnings_threshold": 10.0,
                    "max_compound_rounds": 10,
                    "risk_tolerance": "medium",
                    "auto_rebalance": True,
                },
            )()
            income_multiplier = IncomeMultiplier(config)

        _mcp_bridge_instance = McpBridge(eligibility_engine, income_multiplier)

    return _mcp_bridge_instance


# Module-level singleton
_mcp_bridge_instance: McpBridge | None = None
