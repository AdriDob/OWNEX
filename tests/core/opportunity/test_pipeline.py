import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# Add the project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.opportunity.adapters import get_adapters
from core.opportunity.engine import OpportunityOrchestrator
from core.opportunity.executors import get_executors
from core.scheduler.jobs import get_all_jobs


class TestOpportunityPipeline:
    """Comprehensive test suite for opportunity pipeline components."""

    __test__ = False

    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()

    async def run_all_tests(self) -> dict[str, Any]:
        """Run the complete test suite."""
        print("=== OWNEX Opportunity Pipeline Test Suite ===\n")

        # Run all test suites
        self.test_results["adapters"] = await self.test_adapters()
        self.test_results["executors"] = await self.test_executors()
        self.test_results["engine"] = await self.test_engine()
        self.test_results["scheduler"] = await self.test_scheduler()

        # Generate summary
        summary = self.generate_summary()
        self.test_results["summary"] = summary

        # Save results
        await self.save_results()

        return self.test_results

    async def test_adapters(self) -> dict[str, Any]:
        """Test that adapters can fetch opportunities (graceful auth failure handling)."""
        print("Testing adapters...")

        try:
            adapters = get_adapters()
            results = {}

            for name, adapter in adapters.items():
                try:
                    opportunities = await adapter.fetch_opportunities()
                    results[name] = {
                        "status": "PASS",
                        "opportunities_found": len(opportunities),
                        "platform": getattr(adapter, "platform", "unknown"),
                        "cycle": getattr(adapter, "cycle", "unknown"),
                        "error": None,
                        "execution_time_ms": int((time.time() - self.start_time) * 1000),
                    }
                except Exception as e:
                    results[name] = {
                        "status": "FAIL",
                        "opportunities_found": 0,
                        "platform": getattr(adapter, "platform", "unknown"),
                        "cycle": getattr(adapter, "cycle", "unknown"),
                        "error": str(e),
                        "execution_time_ms": int((time.time() - self.start_time) * 1000),
                    }

            passed = sum(1 for r in results.values() if r["status"] == "PASS")
            total = len(results)
            success_rate = (passed / total * 100) if total > 0 else 0

            return {
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "success_rate": success_rate,
                },
                "results": results,
                "took_seconds": time.time() - self.start_time,
            }

        except Exception as e:
            return {
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 1,
                    "success_rate": 0,
                },
                "results": {"import_error": str(e)},
                "took_seconds": time.time() - self.start_time,
            }

    async def test_executors(self) -> dict[str, Any]:
        """Test executor health checks."""
        print("Testing executors...")

        try:
            executors = get_executors()
            results = {}

            for name, executor in executors.items():
                try:
                    if hasattr(executor, "health_check"):
                        health = await executor.health_check()
                        success = health.success if hasattr(health, "success") else health.get("success", False)
                        results[name] = {
                            "status": "PASS" if success else "FAIL",
                            "platform": getattr(executor, "platform", "unknown"),
                            "health_details": {
                                "success": health.success,
                                "action": health.action,
                                "target": health.target,
                                "message": health.message,
                                "error": health.error,
                                "data": health.data,
                                "created_at": health.created_at,
                            }
                            if hasattr(health, "success")
                            else health,
                            "execution_time_ms": int((time.time() - self.start_time) * 1000),
                            "error": None
                            if success
                            else (health.error if hasattr(health, "error") else "Health check failed"),
                        }
                    else:
                        results[name] = {
                            "status": "SKIP",
                            "reason": "No health_check method",
                            "platform": getattr(executor, "platform", "unknown"),
                            "execution_time_ms": int((time.time() - self.start_time) * 1000),
                        }
                except Exception as e:
                    results[name] = {
                        "status": "FAIL",
                        "platform": getattr(executor, "platform", "unknown"),
                        "error": str(e),
                        "execution_time_ms": int((time.time() - self.start_time) * 1000),
                    }

            passed = sum(1 for r in results.values() if r["status"] == "PASS")
            total = len(results)
            success_rate = (passed / total * 100) if total > 0 else 0

            return {
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "skipped": len([r for r in results.values() if r["status"] == "SKIP"]),
                    "success_rate": success_rate,
                },
                "results": results,
                "took_seconds": time.time() - self.start_time,
            }

        except Exception as e:
            return {
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 1,
                    "success_rate": 0,
                },
                "results": {"import_error": str(e)},
                "took_seconds": time.time() - self.start_time,
            }

    async def test_engine(self) -> dict[str, Any]:
        """Test the OpportunityEngine orchestrator structure."""
        print("Testing engine...")

        try:
            engine = OpportunityOrchestrator()

            if hasattr(engine, "health_check"):
                health = await engine.health_check()
                success = isinstance(health, dict) and health.get("status") == "healthy"
                results = {
                    "engine_type": type(engine).__name__,
                    "status": "PASS" if success else "FAIL",
                    "health_details": health,
                    "forge_adapters_count": len(engine.forge_adapters),
                    "pulse_adapters_count": len(engine.pulse_adapters),
                    "forge_executors_count": len(engine.forge_executors),
                    "pulse_executors_count": len(engine.pulse_executors),
                    "execution_time_ms": int((time.time() - self.start_time) * 1000),
                    "error": None if success else str(health),
                }
            else:
                results = {
                    "engine_type": type(engine).__name__,
                    "status": "SKIP",
                    "reason": "No health_check method",
                    "execution_time_ms": int((time.time() - self.start_time) * 1000),
                }

            return {
                "summary": {
                    "test_performed": "health_check",
                    "result": "PASS"
                    if results["status"] == "PASS"
                    else "FAILED"
                    if results["status"] == "FAIL"
                    else "SKIPPED",
                },
                "results": results,
                "took_seconds": time.time() - self.start_time,
            }

        except Exception as e:
            return {
                "summary": {
                    "test_performed": "engine_initialization",
                    "result": "FAILED",
                },
                "results": {"error": str(e)},
                "took_seconds": time.time() - self.start_time,
            }

    async def test_scheduler(self) -> dict[str, Any]:
        """Test scheduler job generation."""
        print("Testing scheduler...")

        try:
            all_jobs = get_all_jobs()
            total_jobs = sum(len(jobs) for jobs in all_jobs.values())

            results = {}
            for cycle, jobs in all_jobs.items():
                results[cycle] = {
                    "total_jobs": len(jobs),
                    "jobs": [
                        {
                            "job_id": job.job_id,
                            "app_id": job.app_id,
                            "trigger": job.trigger,
                            "handler": job.handler,
                        }
                        for job in jobs
                    ],
                }

            # Check that we have the expected cycles
            expected_cycles = {"forge", "pulse", "vault", "atlas"}
            found_cycles = set(results.keys())
            cycles_match = expected_cycles == found_cycles

            results["summary_validation"] = {
                "cycles_match": cycles_match,
                "missing_cycles": list(expected_cycles - found_cycles),
                "extra_cycles": list(found_cycles - expected_cycles),
                "total_jobs": total_jobs,
            }

            return {
                "summary": {
                    "test_performed": "job_generation",
                    "result": "PASS" if total_jobs > 0 and cycles_match else "FAILED",
                    "total_jobs": total_jobs,
                    "cycles_match": cycles_match,
                },
                "results": results,
                "took_seconds": time.time() - self.start_time,
            }

        except Exception as e:
            return {
                "summary": {
                    "test_performed": "scheduler_job_generation",
                    "result": "FAILED",
                },
                "results": {"error": str(e)},
                "took_seconds": time.time() - self.start_time,
            }

    def generate_summary(self) -> dict[str, Any]:
        """Generate a comprehensive test summary."""
        summary = {
            "test_suite": "OWNEX Opportunity Pipeline",
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "overall_success_rate": 0,
            "execution_time_seconds": time.time() - self.start_time,
            "timestamp": time.time(),
        }

        # Calculate overall stats
        for test_name, test_result in self.test_results.items():
            if test_name == "summary":
                continue

            if isinstance(test_result, dict) and "summary" in test_result:
                test_summary = test_result["summary"]
                summary["total_tests"] += test_summary.get("total", 0)
                summary["passed_tests"] += test_summary.get("passed", 0)
                summary["failed_tests"] += test_summary.get("failed", 0)
                summary["skipped_tests"] += test_summary.get("skipped", 0)

        if summary["total_tests"] > 0:
            summary["overall_success_rate"] = (summary["passed_tests"] / summary["total_tests"]) * 100

        return summary

    async def save_results(self) -> None:
        """Save test results to a JSON file."""
        output_path = Path(__file__).parent / "opportunity_pipeline_test_results.json"

        # Ensure the directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write results
        with open(output_path, "w") as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\nTest results saved to: {output_path}")

    def print_results(self) -> None:
        """Print formatted test results."""
        print("\n=== TEST RESULTS SUMMARY ===")

        for test_name, test_result in self.test_results.items():
            if test_name == "summary":
                continue

            print(f"\n{test_name.upper().replace('_', ' ')}:")
            if isinstance(test_result, dict) and "summary" in test_result:
                summary = test_result["summary"]
                if "total" in summary:
                    print(f"  Total: {summary['total']}")
                    print(f"  Passed: {summary['passed']}")
                    print(f"  Failed: {summary['failed']}")
                    if "skipped" in summary:
                        print(f"  Skipped: {summary['skipped']}")
                    print(f"  Success Rate: {summary['success_rate']:.1f}%")
                elif "result" in summary:
                    print(f"  Result: {summary['result']}")
                    print(f"  Test: {summary.get('test_performed', 'unknown')}")
                print(f"  Time: {test_result['took_seconds']:.2f}s")
            else:
                print(f"  Status: ERROR - {test_result.get('error', 'Unknown')}")

        summary = self.test_results.get("summary", {})
        print(f"\n{'=' * 50}")
        print("OVERALL RESULTS:")
        print(f"  Tests: {summary.get('total_tests', 0)}")
        print(f"  Passed: {summary.get('passed_tests', 0)}")
        print(f"  Failed: {summary.get('failed_tests', 0)}")
        print(f"  Skipped: {summary.get('skipped_tests', 0)}")
        print(f"  Success Rate: {summary.get('overall_success_rate', 0):.1f}%")
        print(f"  Execution Time: {summary.get('execution_time_seconds', 0):.2f}s")
        print(f"{'=' * 50}")


async def main():
    """Run the complete test suite."""
    tester = TestOpportunityPipeline()

    await tester.run_all_tests()
    tester.print_results()

    # Overall success criteria
    summary = tester.test_results.get("summary", {})
    total_tests = summary.get("total_tests", 0)
    passed_tests = summary.get("passed_tests", 0)
    failed_tests = summary.get("failed_tests", 0)

    # Calculate if we have meaningful success
    min_pass_ratio = 0.5  # At least 50% of components should pass
    min_total_tests = 3  # At least 3 test categories should pass

    conditions_met = [
        total_tests >= min_total_tests,
        (passed_tests / total_tests * 100) >= (min_pass_ratio * 100) if total_tests > 0 else False,
        failed_tests == 0 or total_tests < 10,  # Allow some failures for lightweight test
    ]

    overall_success = all(conditions_met)

    print(f"\n{'=' * 50}")
    print(f"OVERALL TEST SUITE: {'PASSED' if overall_success else 'FAILED'}")
    print(f"Criteria met: {sum(conditions_met)}/{len(conditions_met)}")
    print(f"{'=' * 50}")

    return 0 if overall_success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
