#!/usr/bin/env python3
"""
Example: Mobile Companion Integration

This example demonstrates how OWNEX OMEGA mobile companion
integrates with the core system.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mobile.notifications import NotificationManager
from core.mobile.sync import MobileSync


async def main():
    """Run mobile companion example."""

    print("📱 OWNEX OMEGA Mobile Companion Example")
    print("=" * 50)

    # Initialize mobile sync
    sync = MobileSync()
    notifications = NotificationManager()

    print("\n🔄 Mobile Sync:")
    print("-" * 30)

    # Sync status
    print("\n📊 Sync Status:")
    try:
        status = await sync.get_status()
        print(f"   Connected: {status.connected}")
        print(f"   Last Sync: {status.last_sync}")
        print(f"   Pending: {status.pending_items}")
        print(f"   Device: {status.device_info}")
    except Exception as e:
        print(f"   (Demo mode - requires mobile app: {e})")

    # Sync data
    print("\n🔄 Syncing data...")
    try:
        result = await sync.sync_all()
        print(f"   Cycles synced: {result.cycles}")
        print(f"   Findings synced: {result.findings}")
        print(f"   Reports synced: {result.reports}")
        print(f"   Config synced: {result.config}")
    except Exception as e:
        print(f"   (Demo mode - requires mobile app: {e})")

    # Notifications
    print("\n🔔 Notifications:")
    print("-" * 30)

    # Send test notifications
    test_notifications = [
        {
            "type": "approval_required",
            "title": "Bug Bounty Report Approval",
            "body": "Target: example.com | Reward: $500 | Action needed",
            "priority": "high",
            "action_url": "ownex://approval/report_123",
        },
        {
            "type": "cycle_completed",
            "title": "Forge Cycle Complete",
            "body": "3 opportunities discovered, 1 executed",
            "priority": "medium",
            "action_url": "ownex://cycle/forge_456",
        },
        {
            "type": "security_alert",
            "title": "Critical Finding Validated",
            "body": "SQL Injection on api.target.com - CVSS 9.1",
            "priority": "critical",
            "action_url": "ownex://finding/vuln_789",
        },
        {
            "type": "merlin_suggestion",
            "title": "MERLIN Recommendation",
            "body": "Switch to API testing - higher ROI detected",
            "priority": "low",
            "action_url": "ownex://merlin/suggestion_001",
        },
    ]

    print("\n📤 Sending test notifications...")
    for notif in test_notifications:
        try:
            await notifications.send(notif)
            print(f"   ✅ Sent: {notif['title']} [{notif['priority']}]")
        except Exception as e:
            print(f"   (Demo mode - requires mobile app: {e})")

    # Get notification history
    print("\n📜 Notification History:")
    try:
        history = await notifications.get_history(limit=10)
        for notif in history:
            print(f"   [{notif.timestamp}] {notif.title} ({notif.priority})")
    except Exception as e:
        print(f"   (Demo mode - requires mobile app: {e})")

    # Wear OS integration
    print("\n⌚ Wear OS Integration:")
    print("-" * 30)

    print("\n📱 Companion app features:")
    print("   • Real-time approval requests")
    print("   • System health at a glance")
    print("   • MERLIN chat on wrist")
    print("   • Critical alerts with haptics")
    print("   • Quick actions (approve/reject/defer)")

    print("\n⌚ Wear OS features:")
    print("   • Glanceable system status")
    print("   • Critical alerts only")
    print("   • Voice replies to MERLIN")
    print("   • Complication support")

    print("\n✨ Example complete!")
    print("\n💡 Mobile integration:")
    print("   - Bidirectional sync with desktop")
    print("   - Push notifications for approvals")
    print("   - Offline-capable with sync on reconnect")
    print("   - Wear OS for critical-only alerts")


if __name__ == "__main__":
    asyncio.run(main())
