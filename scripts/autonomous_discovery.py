#!/usr/bin/env python3
"""CLI command for autonomous discovery research runs."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from cores.direct_work_engine.autonomous_discovery import AutonomousDiscoveryEngine, DiscoveryConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ownex.discovery.cli")


async def run_discovery(max_platforms: int = 50, show_details: bool = False, output_json: bool = False):
    """Run one discovery cycle and print results."""
    config = DiscoveryConfig(
        research_interval_hours=6,
        max_platforms_to_research=max_platforms,
        persist_state=True,
    )

    engine = AutonomousDiscoveryEngine(config)

    logger.info(f"🔬 Starting autonomous discovery (max {max_platforms} platforms)...")
    try:
        await engine._research_new_platforms()

        # Get top platforms by EV
        platforms = sorted(engine.discovered_platforms.values(), key=lambda p: p.get("ev_score", 0), reverse=True)[
            :max_platforms
        ]

        if output_json:
            print(json.dumps(platforms, indent=2, ensure_ascii=False))
        else:
            print(f"\n🎯 Discovered {len(platforms)} platforms (ranked by Expected Value):\n")
            for i, p in enumerate(platforms, 1):
                print(f"{i:3d}. {p.get('title', 'N/A')[:60]}")
                print(f"      Domain: {p.get('domain', 'N/A')} | EV: ${p.get('ev_score', 0):.2f}/hr")
                print(
                    f"      Zero-barrier signals: {p.get('zero_barrier_signals', 0)} | Source: {p.get('source', 'web')}"
                )
                print(f"      URL: {p.get('url', 'N/A')}")
                if show_details:
                    print(f"      Positive: {p.get('positive_signals', 0)} | Negative: {p.get('negative_signals', 0)}")
                print()

        return platforms
    except Exception as e:
        logger.exception(f"Discovery failed: {e}")
        sys.exit(1)
    finally:
        await engine.stop()


async def run_continuous(interval_hours: int = 6, max_platforms: int = 50):
    """Run continuous discovery cycles."""
    config = DiscoveryConfig(
        research_interval_hours=interval_hours,
        max_platforms_to_research=max_platforms,
        persist_state=True,
    )

    engine = AutonomousDiscoveryEngine(config)
    await engine.start()

    logger.info(f"🚀 Continuous discovery started (every {interval_hours}h, max {max_platforms} platforms)")
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            await asyncio.sleep(3600)  # Keep alive
    except KeyboardInterrupt:
        logger.info("🛑 Stopping continuous discovery...")
        await engine.stop()


def main():
    parser = argparse.ArgumentParser(description="OWNEX Autonomous Discovery CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Single run
    run_parser = subparsers.add_parser("run", help="Run one discovery cycle")
    run_parser.add_argument("-n", "--max-platforms", type=int, default=50, help="Max platforms to discover")
    run_parser.add_argument("-d", "--details", action="store_true", help="Show detailed info")
    run_parser.add_argument("-j", "--json", action="store_true", help="Output as JSON")

    # Continuous run
    cont_parser = subparsers.add_parser("continuous", help="Run continuous discovery")
    cont_parser.add_argument("-i", "--interval", type=int, default=6, help="Interval in hours")
    cont_parser.add_argument("-n", "--max-platforms", type=int, default=50, help="Max platforms per cycle")

    args = parser.parse_args()

    if args.command == "run":
        asyncio.run(run_discovery(args.max_platforms, args.details, args.json))
    elif args.command == "continuous":
        asyncio.run(run_continuous(args.interval, args.max_platforms))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
