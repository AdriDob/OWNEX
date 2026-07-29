#!/bin/bash
# Fix EventBus imports in api/main.py

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== Fixing EventBus imports in api/main.py ==="

echo "Current incorrect import at line 360: from core.events.bus import get_event_bus"
echo "Should be changed to:      from cores.events.event_bus import get_event_bus"

echo "\nApplying fix..."
sed -i '360s|from core.events.bus import get_event_bus|from cores.events.event_bus import get_event_bus|' api/main.py

echo "Checking fix..."
if grep -q "from cores.events.event_bus import get_event_bus" api/main.py; then
    echo "✓ Fixed: Found correct import at line 360"
else
    echo "❌ Fix failed: Could not find correct import"
    exit 1
fi

# Also verify there are no remaining references to core.events.bus
echo "\nChecking for any remaining references to core.events.bus..."
if grep -r "core.events.bus" api/main.py 2>/dev/null; then
    echo "❌ Found remaining core.events.bus references"
    exit 1
else
    echo "✓ No remaining core.events.bus references"
fi

echo "\n=== EventBus imports fixed successfully ==="
echo "All EventBus imports now consistently use: cores.events.event_bus"
