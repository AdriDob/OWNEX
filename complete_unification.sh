#!/bin/bash
# Complete EventBus unification - Update all core.events.* imports to cores.events.*
# This ensures consistency across the entire codebase

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== Complete EventBus Unification Script ==="
echo "Target: Update all core.events.* imports to cores.events.*"
echo ""

# Count of files to process
files_without_fix=0

# Process core.events.correlation imports
echo "Processing core.events.correlation imports..."
sed -i 's|from core\.events\.correlation|from cores.events.correlation|g' $(find . -name "*.py" -type f)
sed -i 's|import core\.events\.correlation import|import cores.events.correlation import|g' $(find . -name "*.py" -type f)
sed -i 's|core\.events\.correlation\.|cores.events.correlation.|g' $(find . -name "*.py" -type f)

# Process core.events.types imports  
echo "Processing core.events.types imports..."
sed -i 's|from core\.events\.types|from cores.events.types|g' $(find . -name "*.py" -type f)
sed -i 's|import core\.events\.types import|import cores.events.types import|g' $(find . -name "*.py" -type f)
sed -i 's|core\.events\.types\.|cores.events.types.|g' $(find . -name "*.py" -type f)

# Process core.events.store imports
echo "Processing core.events.store imports..."
sed -i 's|from core\.events\.store|from cores.events.store|g' $(find . -name "*.py" -type f)
sed -i 's|import core\.events\.store import|import cores.events.store import|g' $(find . -name "*.py" -type f)
sed -i 's|core\.events\.store\.|cores.events.store.|g' $(find . -name "*.py" -type f)

# Verify that no core.events.* imports remain (excluding __pycache__)
remaining=$(find . -name "*.py" -type f -not -path "./.*" -not -path "./__pycache__/*" -exec grep -l "from core\.events\." {} \;)
if [ -n "$remaining" ]; then
    echo ""
    echo "❌ Found remaining core.events.* imports in:"
    echo "$remaining"
    echo ""
    for file in $remaining; do
        echo "File: $file"
        grep -n "core\.events\." "$file"
    done
    exit 1
else
    echo ""
    echo "✓ All core.events.* imports have been successfully updated to cores.events.*"
fi

# Verify that cores.events.* imports are present
files_with_new_imports=$(find . -name "*.py" -type f -not -path "./.*" -not -path "./__pycache__/*" -exec grep -l "from cores\.events\." {} \;)
if [ -n "$files_with_new_imports" ]; then
    echo "✓ Found $files_with_new_imports files with cores.events.* imports"
else
    echo "❌ No files found with cores.events.* imports"
    exit 1
fi

echo ""
echo "=== EventBus Unification Complete ==="
echo "All imports now consistently use: cores.events.*"
echo "Legacy CoreEventBus should still be accessible for backward compatibility"
