#!/usr/bin/env python3
"""
Example: Security Research Workflow with OWNEX

This example demonstrates running a security research cycle
using OWNEX's Rastro security pipeline.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cycles.metrics import SecurityMetrics
from core.cycles.security import SecurityCycle


async def main():
    """Run security research cycle example."""

    print("🔒 OWNEX Security Research Example")
    print("=" * 50)

    # Initialize security cycle
    cycle = SecurityCycle()

    # Configure target
    target_config = {
        "domain": "example.com",
        "scope": ["web", "api", "subdomains"],
        "depth": "comprehensive",
        "rate_limit": 100,  # requests per minute
        "timeout": 300,  # seconds
    }

    print(f"\n🎯 Target: {target_config['domain']}")
    print(f"   Scope: {', '.join(target_config['scope'])}")
    print(f"   Depth: {target_config['depth']}")

    # Run security cycle
    print("\n🔍 Running security research cycle...")
    print("   Stages: Recon → Attack Surface → Hypothesis → Validation → Evidence → Report → Learning")

    try:
        results = await cycle.execute(target_config)

        print("\n✅ Cycle completed!")
        print(f"   Findings: {len(results.findings)}")
        print(f"   Critical: {sum(1 for f in results.findings if f.severity == 'critical')}")
        print(f"   High: {sum(1 for f in results.findings if f.severity == 'high')}")
        print(f"   Medium: {sum(1 for f in results.findings if f.severity == 'medium')}")
        print(f"   Low: {sum(1 for f in results.findings if f.severity == 'low')}")
        print(f"   Info: {sum(1 for f in results.findings if f.severity == 'info')}")

        # Show top findings
        if results.findings:
            print("\n🔝 Top Findings:")
            print("-" * 50)
            for finding in sorted(results.findings, key=lambda f: f.cvss_score, reverse=True)[:5]:
                print(f"  [{finding.severity.upper()}] {finding.title}")
                print(f"      CVSS: {finding.cvss_score} | Type: {finding.vuln_type}")
                print(f"      Endpoint: {finding.endpoint}")
                print()

        # Generate report
        print("📋 Generating structured report...")
        report = await cycle.generate_report(results)
        print(f"   Report ID: {report.id}")
        print(f"   Format: {report.format}")
        print(f"   Size: {len(report.content)} chars")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Note: This example requires configured targets and API keys")

    # Show metrics
    print("\n📊 Security Metrics:")
    print("-" * 50)
    metrics = SecurityMetrics()
    stats = await metrics.get_summary()
    print(f"  Total Cycles Run: {stats.total_cycles}")
    print(f"  Total Findings: {stats.total_findings}")
    print(f"  Accepted Reports: {stats.accepted_reports}")
    print(f"  Average CVSS: {stats.avg_cvss:.1f}")
    print(f"  Success Rate: {stats.success_rate * 100:.1f}%")

    print("\n✨ Example complete!")


if __name__ == "__main__":
    asyncio.run(main())
