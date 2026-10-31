#!/usr/bin/env bash
#
# launch_ownex.sh — Launch OWNEX Alpha Desktop multiplataforma
# Un script simple para iniciar el sistema completo
#

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Iniciando OWNEX Alpha...${NC}"
echo ""

# 1. Verificar si el backend ya está corriendo
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend ya corriendo${NC}"
    BACKEND_READY=true
else
    echo -e "${YELLOW}Iniciando backend...${NC}"
    python run.py --serve &
    BACKEND_PID=$!
    # Esperar max 20 segundos
    for i in $(seq 1 20); do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend listo${NC}"
            BACKEND_READY=true
            break
        fi
        sleep 1
    done
    if [ "$BACKEND_READY" != "true" ]; then
        echo -e "${RED}✗ Backend no inició${NC}"
        exit 1
    fi
fi

# 2. Abrir el navegador
echo -e "${GREEN}Abriendo navegador...${NC}"
sleep 2
if command -v xdg-open > /dev/null 2>&1; then
    xdg-open "http://localhost:8000/" &
elif command -v open > /dev/null 2>&1; then
    open "http://localhost:8000/" &
elif command -v firefox > /dev/null 2>&1; then
    firefox "http://localhost:8000/" &
fi

# 3. Intentar lanzar la App Image de Tauri (Linux)
if [ "$(uname -s)" = "Linux" ] && [ -f "$PROJECT_DIR/src-tauri/target/release/bundle/appimage/OWNEX Alpha_7.7.7_amd64.AppImage" ]; then
    echo -e "${GREEN}Lanzando aplicación desktop (AppImage)...${NC}"
    chmod +x "$PROJECT_DIR/src-tauri/target/release/bundle/appimage/OWNEX Alpha_7.7.7_amd64.AppImage"
    "$PROJECT_DIR/src-tauri/target/release/bundle/appimage/OWNEX Alpha_7.7.7_amd64.AppImage" &
    echo -e "${GREEN}✓ Aplicación desktop en background${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "OWNEX Alpha está corriendo"
echo -e "========================================${NC}"
echo ""
echo -e "   🌐 http://localhost:8000/   (interfaz web)"
echo -e "   🏥 http://localhost:8000/api/health   (health check)"
echo -e "   💰 http://localhost:8000/api/capital/snapshot   (ingresos)"
echo -e "   📋 http://localhost:8000/api/direct-work/workbank   (oportunidades)"
echo ""
echo -e "Presiona Ctrl+C para mantener el backend vivo o cerrar"
#

# Mantener el script vivo para que el backend no se detenga
# El usuario puede cerrar con Ctrl+C
wait 2>/dev/null

# Al salir, intentar detener el backend
if [ ! -z "$BACKEND_PID" ]; then
    kill $BACKEND_PID 2>/dev/null
    echo -e "\n${GREEN}Backend detenido${NC}"
fi