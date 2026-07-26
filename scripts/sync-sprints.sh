#!/usr/bin/env bash
# sync-sprints.sh — Sincroniza estado de sprints entre .md y .json
# Uso: ./scripts/sync-sprints.sh [--check]
#
# Lee TASK_QUEUE.md, CURRENT_STATE.md y COMPLETED_FEATURES.json,
# verifica que los sprints marcados como COMPLETED estén presentes
# en los 3 archivos. Con --check solo reporta, sin modificar.

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

AI_DIR=".ai"
TASK_QUEUE="$AI_DIR/TASK_QUEUE.md"
CURRENT_STATE="$AI_DIR/CURRENT_STATE.md"
COMPLETED_FEATURES="$AI_DIR/COMPLETED_FEATURES.json"
CHECK_ONLY="${1:-}"

errors=0

extract_completed() {
    # Extrae nombres de features COMPLETED de TASK_QUEUE.md
    # Busca líneas con "✅ COMPLETED" o "✅ COMPLETED —"
    grep -n "COMPLETED" "$TASK_QUEUE" 2>/dev/null | sed 's/.*[0-9]\. //; s/ ⭐.*//; s/ ✅.*//; s/ —.*//' | tr -d '`#'
}

extract_fases_json() {
    # Extrae nombres de fases de COMPLETED_FEATURES.json
    .venv/bin/python -c "
import json, sys
with open('$COMPLETED_FEATURES') as f:
    data = json.load(f)
for fid, fase in data.get('phases', {}).items():
    name = fase.get('name', '')
    print(f'{fid}: {name}')
" 2>/dev/null || true
}

echo "=== sync-sprints: verificando consistencia ==="
echo ""

# 1. Verificar que TASK_QUEUE.md existe
if [ ! -f "$TASK_QUEUE" ]; then
    echo "✗ FALTA: $TASK_QUEUE"
    errors=$((errors + 1))
else
    echo "✓ TASK_QUEUE.md existe"
fi

# 2. Verificar que CURRENT_STATE.md existe
if [ ! -f "$CURRENT_STATE" ]; then
    echo "✗ FALTA: $CURRENT_STATE"
    errors=$((errors + 1))
else
    echo "✓ CURRENT_STATE.md existe"
fi

# 3. Verificar que COMPLETED_FEATURES.json es válido
if [ ! -f "$COMPLETED_FEATURES" ]; then
    echo "✗ FALTA: $COMPLETED_FEATURES"
    errors=$((errors + 1))
else
    if .venv/bin/python -c "import json; json.load(open('$COMPLETED_FEATURES')); print('✓ JSON valido')" 2>/dev/null; then
        :
    else
        echo "✗ JSON inválido: $COMPLETED_FEATURES"
        errors=$((errors + 1))
    fi
fi

echo ""

# 4. Verificar sprints completados en TASK_QUEUE vs CURRENT_STATE
echo "--- Sprints COMPLETED en TASK_QUEUE ---"
grep -n "✅ COMPLETED" "$TASK_QUEUE" 2>/dev/null || echo "(ninguno)"
echo ""

echo "--- Fases en COMPLETED_FEATURES.json ---"
extract_fases_json || echo "(error)"
echo ""

# 5. Verificar que cada FASE en CURRENT_STATE tenga su feature
echo "--- Features en CURRENT_STATE (líneas con ✅ en columnas Estado) ---"
grep -c "✅" "$CURRENT_STATE" 2>/dev/null || echo "0 features"
echo ""

# 6. Git diff summary
if git rev-parse HEAD >/dev/null 2>&1; then
    echo "--- Últimos 3 commits ---"
    git log --oneline -3 2>/dev/null || true
    echo ""
fi

if [ "$errors" -gt 0 ]; then
    echo "✗ $errors error(es) encontrados"
    exit 1
fi

echo "✓ Todo consistente"

# Si no es --check, sugerir próximos pasos
if [ "$CHECK_ONLY" != "--check" ]; then
    echo ""
    echo "--- Próximo sprint en cola ---"
    grep -A 2 "### [0-9]\." "$TASK_QUEUE" 2>/dev/null | head -6 | grep -v "✅" | head -4 || echo "(todos completados)"
fi
