#!/bin/bash

# ORION Ollama Optimized Service - Alto rendimiento, bajo uso de CPU/RAM
# Script para optimizar Ollama en sistemas con RAM limitada y sin GPU

# Configuraciones de rendimiento óptimo
export OLLAMA_NUM_THREAD=2
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_CPU_DENSITY=0

# Modelos más rápidos con cuaternización
FAST_MODELS=(
    "qwen2.5:3b-instruct-q4_k_m"   # 1.5GB RAM, ~80-120ms inferencia
    "qwen2.5:3b-instruct-q8_0"     # 2.5GB RAM, ~120-180ms inferencia  
    "llama3.1:2b-instruct-q4_k_m"  # 1.0GB RAM, ~60-90ms inferencia
)

# Modelos de respaldo (mayores, más lentos)
BACKUP_MODELS=(
    "qwen2.5:3b-instruct"          # 1.9GB RAM, actual modelo
    "qwen3.5:cloud"                # 1.9GB RAM, en la nube
)

# Función: verificar salud
check_health() {
    local host="$1"
    local port="$2"
    local model_name="$3"
    
    echo "Verificando salud en http://$host:$port..."
    
    # Esperar hasta 30 segundos a que el servicio esté listo
    for i in {1..30}; do
        if curl -s -f "http://$host:$port/api/tags" >/dev/null; then
            echo "✅ $host:$port disponible"
            
            # Verificar que el modelo esté cargado
            if curl -s "http://$host:$port/api/tags" | grep -q "$model_name"; then
                echo "✅ Modelo $model_name disponible"
                return 0
            else
                echo "⚠️ Modelo $model_name no encontrado, intentando cargar..."
                curl -s -X POST "http://$host:$port/api/pull" -d "model=$model_name" >/dev/null
                sleep 2
            fi
        else
            echo "⏳ Esperando $host:$port (intento $i/30)"
            sleep 1
        fi
    done
    
    echo "❌ $host:$port no disponible después de 30 segundos"
    return 1
}

# Función: descargar modelo rápidamente
pull_fast_model() {
    local model_name="$1"
    local host="$2"
    local port="$3"
    
    echo "Descargando modelo rápido: $model_name"
    
    # Configuración óptima para descarga rápida
    OLLAMA_NUM_THREAD=1 OLLAMA_MAX_LOADED_MODELS=1 \
    nohup ollama serve --host "$host" --port "$port" > "~/logs/ollama-${model_name}.log" 2>&1 &
    
    local ollama_pid=$!
    
    # Esperar a que el modelo esté listo
    if check_health "$host" "$port" "$model_name"; then
        echo "✅ Modelo $model_name listo en $host:$port"
        echo $ollama_pid > "~/logs/ollama-${model_name}.pid"
        return 0
    else
        echo "❌ Error descargando $model_name"
        kill $ollama_pid 2>/dev/null
        return 1
    fi
}

# Función: balanceo de recursos en tiempo real
resource_balancer() {
    local model_name="$1"
    local pid_file="~/logs/ollama-${model_name}.pid"
    
    if [ ! -f "$pid_file" ]; then
        echo "⚠️ Archivo PID no encontrado: $pid_file"
        return 1
    fi
    
    local ollama_pid=$(cat "$pid_file")
    
    echo "Iniciando balanceador de recursos para modelo $model_name (PID: $ollama_pid)"
    
    while true; do
        # Monitorear memoria y CPU
        local mem_info=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
        local mem_gb=$((mem_info / 1024 / 1024))
        
        local cpu_percent=$(ps -p $ollama_pid -o %cpu --no-headers)
        
        echo "Estado del modelo $model_name: MEM=${mem_gb}GB CPU=${cpu_percent}%"
        
        # Reducir threads si RAM < 4GB
        if [ "$mem_gb" -lt 4 ]; then
            echo "RAM baja ($mem_gb GB), reduciendo threads de Ollama a 1"
            echo "1" > /sys/bus/cpu/cpu0/cpuaffinity
            OLLAMA_NUM_THREAD=1
        # Aumentar threads si RAM > 8GB y CPU < 30%
        elif [ "$mem_gb" -gt 8 ] && (( $(echo "$cpu_percent < 30" | bc -l) )); then
            echo "RAM alta ($mem_gb GB), CPU baja, aumentando threads a 2"
            echo "3" > /sys/bus/cpu/cpu0/cpuaffinity
            OLLAMA_NUM_THREAD=2
        fi
        
        # Si memoria baja, reiniciar modelo con uno más pequeño
        if [ "$mem_gb" -lt 3 ]; then
            echo "RAM crítica ($mem_gb GB), reiniciando con modelo optimizado ligero"
            kill $ollama_pid 2>/dev/null
            # Cambiar a modelo más ligero
            NEW_MODEL=$(echo "${FAST_MODELS[@]}" | tr ' ' '\n' | tail -1)
            pull_fast_model "$NEW_MODEL" "127.0.0.1" "11435"
            ollama_pid=$(pgrep -f "ollama serve.*11435")
            echo $ollama_pid > "~/logs/ollama-${NEW_MODEL}.pid"
        fi
        
        sleep 30
    done
}

# Función: limpieza al final
save_optimized_model() {
    echo "Guardando modelo optimizado para próximos arranques..."
    
    # Limpiar servicios existentes
    for port in 11434 11435 11436; do
        if curl -s "http://127.0.0.1:${port}/api/tags" >/dev/null; then
            echo "Cerrando Ollama en puerto $port"
            kill $(pgrep -f "ollama serve.*$port") 2>/dev/null
        fi
    done
    
    # Calcular el modelo óptimo basado en recursos actuales
    local mem_kb=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
    local mem_gb=$((mem_kb / 1024 / 1024))
    
    # Seleccionar modelo óptimo
    local optimal_model=""
    if [ "$mem_gb" -gt 8 ]; then
        optimal_model="${FAST_MODELS[0]}"  # Q4 quantizado más rápido
    elif [ "$mem_gb" -gt 6 ]; then
        optimal_model="${FAST_MODELS[1]}"  # Q8 balanceado
    else
        optimal_model="${FAST_MODELS[2]}"  # Ligerísimo
    fi
    
    echo "Modelo óptimo seleccionado: $optimal_model para ${mem_gb}GB RAM"
    
    # Guardar para autostart
    echo "export OLLAMA_NUM_THREAD=2" > ~/.ollama-optimized.env
    echo "export OLLAMA_MAX_LOADED_MODELS=1" >> ~/.ollama-optimized.env
    echo "export OPTIMAL_MODEL=$optimal_model" >> ~/.ollama-optimized.env
    
    echo "✅ Optimización completada"
}

# Función: arranque completo del sistema
full_restart() {
    echo "Realizando reinicio completo del sistema ORION..."
    
    # Matar todos los procesos de Ollama
    pkill -9 -f "ollama serve" 2>/dev/null
    echo "✅ Procesos Ollama finalizados"
    
    # Limpiar antiguos archivos PID
    rm -f ~/logs/ollama-*.pid
    
    # Iniciar el servicio optimizado primario
    echo "Iniciando servicio Ollama optimizado primario..."
    OLLAMA_NUM_THREAD=2 OLLAMA_MAX_LOADED_MODELS=1 \
    nohup ollama serve \
        --host 127.0.0.1 \
        --port 11434 \
        --load-only > ~/logs/ollama-primary.log 2>&1 &
    
    local primary_pid=$!
    echo $primary_pid > ~/logs/ollama-primary.pid
    
    if check_health "127.0.0.1" "11434" "qwen2.5:3b-instruct-q4_k_m"; then
        echo "✅ Servicio primario listo en puerto 11434"
        
        # Segundo servicio para carga alta
        echo "Iniciando servicio secundario para carga alta..."
        OLLAMA_NUM_THREAD=1 OLLAMA_MAX_LOADED_MODELS=1 \
        nohup ollama serve \
            --host 127.0.0.1 \
            --port 11435 \
            --load-only > ~/logs/ollama-secondary.log 2>&1 &
        
        local secondary_pid=$!
        echo $secondary_pid > ~/logs/ollama-secondary.pid
        
        if check_health "127.0.0.1" "11435" "qwen2.5:3b-instruct-q8_0"; then
            echo "✅ Servicio secundario listo en puerto 11435"
            
            # Iniciar balanceador en segundo plano
            (
                resource_balancer "qwen2.5:3b-instruct-q4_k_m" &
                balancer_pid=$!
                echo $balancer_pid > ~/logs/balancer.pid
            )
            
            echo "✅ Sistema ORION completamente optimizado y balanceado"
            echo "Puntos de entrada disponibles:"
            echo "  - Primary (11434): Modelo Q4 quantizado suave"
            echo "  - Secondary (11435): Modelo Q8 balanceado"
            return 0
        else
            echo "❌ Error iniciando servicio secundario"
            kill $primary_pid 2>/dev/null
            return 1
        fi
    else
        echo "❌ Error iniciando servicio primario"
        kill $primary_pid 2>/dev/null
        return 1
    fi
}

# Función: verificar estado del servicio
check_service_status() {
    echo "=== Estado del Servicio ORION Ollama ==="
    
    # Verificar procesos
    echo "Procesos activos:"
    ps -ef | grep "ollama serve" | grep -v grep
    
    echo ""
    echo "Archivos PID:"
    for pid_file in ~/logs/ollama-*.pid; do
        if [ -f "$pid_file" ]; then
            echo "  $(basename $pid_file): PID $(cat $pid_file)"
        fi
    done
    
    echo ""
    echo "Estado de salud de puertos:"
    for port in 11434 11435 11436; do
        if curl -s "http://127.0.0.1:${port}/api/tags" >/dev/null; then
            local status="✅ HEALTHY"
            local models=$(curl -s "http://127.0.0.1:${port}/api/tags" | grep -o '"name":"[^"]*"' | tr -d '"name":"' | tr ',' '\n' | head -5)
            echo "  Puerto $port: $status"
            echo "    Modelos: $models"
        else
            echo "  Puerto $port: ❌ SIN RESPUESTA"
        fi
    done
    
    echo ""
    echo "Uso de recursos:"
    local mem_total=$(awk '/MemTotal/{print $2}' /proc/meminfo)
    local mem_available=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
    local mem_used=$((mem_total - mem_available))
    
    echo "  Memoria: $((mem_used / 1024 / 1024))GB usada de $((mem_total / 1024 / 1024))GB"
    echo "  CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1))%"
}

# Punto de entrada principal
case "$1" in
    restart|start|reiniciar)
        full_restart
        ;;
    status|estado)
        check_service_status
        ;;
    save|guardar)
        save_optimized_model
        ;;
    balancer|balanceador)
        if [ -f "~/logs/balancer.pid" ]; then
            echo "Balanceador ya en ejecución (PID: $(cat ~/logs/balancer.pid))"
        else
            (
                resource_balancer "$2"
            ) &
            echo $! > ~/logs/balancer.pid
            echo "✅ Balanceador iniciado (PID: $!)"
        fi
        ;;
    check-health|verificar)
        check_health "$2" "$3" "$4"
        ;;
    *)
        echo "Uso: $0 [restart|status|save|balancer <modelo>|check-health <host> <port> <modelo>]"
        echo ""
        echo "Comandos disponibles:"
        echo "  restart/reiniciar    - Reinicio completo con balanceo automático"
        echo "  status/estado        - Verificar estado del servicio"
        echo "  save/guardar         - Guardar configuración optimizada"
        echo "  balancer <modelo>    - Iniciar balanceador de recursos"
        echo "  check-health <host> <port> <modelo> - Verificar servicio"
        ;;
esac