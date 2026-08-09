#!/usr/bin/env bash
# OWNEX — Brand & screenshot regeneration pipeline.
#
# Regenerates every visual asset from source:
#   1. Logo system (O+X mark, wordmark, lockup, favicon) — SVG + PNG
#   2. Hero banner + OpenGraph social preview — SVG + PNG
#   3. Real product screenshots (Playwright, requires backend+frontend up)
#
# Usage:
#   scripts/brand/regenerate.sh           # logo + banners only
#   scripts/brand/regenerate.sh --shots   # everything (needs servers on :8000/:5173)
set -euo pipefail
cd "$(dirname "$0")/../.."

PY=.venv/bin/python
[ -x "$PY" ] || PY=python3

echo "→ Logo system"
"$PY" scripts/brand/generate_ownex_logo.py

echo "→ Banner + social preview"
"$PY" scripts/brand/generate_ownex_banners.py

# Keep legacy assets dir in sync (README v2 compat paths — deprecated)
echo "→ Sync legacy assets/logo dir"
mkdir -p assets/logos
for f in docs/assets/branding/logo/*.svg; do
  cp "$f" assets/logos/$(basename "$f")
done
for f in docs/assets/branding/logo/*.png; do
  cp "$f" assets/logos/$(basename "$f")
done

if [ "${1:-}" = "--shots" ]; then
  echo "→ Product screenshots (Playwright)"
  node scripts/capture_screenshots.mjs
fi

echo "→ Optimize screenshots (palette quantization)"
"$PY" scripts/brand/optimize_assets.py

echo "→ Validate presentation assets"
"$PY" scripts/brand/validate_assets.py

echo "→ Done. Assets live in docs/assets/branding/ and docs/assets/screenshots/"