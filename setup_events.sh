#!/bin/bash
# Rastro setup - EventBus unification
# Unifies the two EventBus implementations into one system

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== Rastro EventBus Unification ==="

echo "Step 1: Checking current EventBus state..."
