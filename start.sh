#!/bin/bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/.venv/bin/activate"
export PYTHONPATH="${PYTHONPATH:-}:$DIR"
cd "$DIR"
echo "Starting Rastro API..."
python -m api.main
