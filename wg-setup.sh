#!/bin/bash
# ============================================================
# WIREGUARD VPN SETUP PARA OUTLIER / DATAANNOTATION DESDE ARGENTINA
# ============================================================
# Uso: curl -sSL https://raw.githubusercontent.com/tu-repo/wg-setup.sh | bash
# O descargar y ejecutar: chmod +x wg-setup.sh && sudo ./wg-setup.sh
# ============================================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ============================================================
# CONFIGURACIÓN - EDITAR ANTES DE EJECUTAR
# ============================================================

# IP pública de tu VPS (se detecta automáticamente si está vacío)
SERVER_PUBLIC_IP=""

# Puerto WireGuard (default 51820)
WG_PORT=51820

# Subred VPN (CIDR) - no cambiar a menos que sepas lo que haces
WG_SUBNET="10.8.0.0/24"
SERVER_WG_IP="10.8.0.1"

# Rango de IPs para clientes
CLIENT_IP_START=2
CLIENT_IP_END=254

# DNS para clientes (Cloudflare + Google)
CLIENT_DNS="1.1.1.1, 8.8.8.8"

# Nombre de la interfaz
WG_INTERFACE="wg0"

# Puerto SSH (por si acaso)
SSH_PORT=22

# Usuario que tendrá acceso sudo (tu usuario actual)
SUDO_USER="${SUDO_USER:-$(whoami)}"

# ============================================================
# FUNCIONES
# ============================================================

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "Ejecutar como root: sudo ./wg-setup.sh"
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    else
        error "No se puede detectar el OS"
    fi
    log "OS detectado: $OS $VER"
}

detect_public_ip() {
    if [[ -z "$SERVER_PUBLIC_IP" ]]; then
        log "Detectando IP pública..."
        SERVER_PUBLIC_IP=$(curl -s -4 ifconfig.me || curl -s -4 icanhazip.com || curl -s -4 ipinfo.io/ip)
        if [[ -z "$SERVER_PUBLIC_IP" ]]; then
            error "No se pudo detectar IP pública. Configura SERVER_PUBLIC_IP manualmente."
        fi
        log "IP pública detectada: $SERVER_PUBLIC_IP"
    fi
}

install_dependencies() {
    log "Instalando dependencias..."
    case $OS in
        ubuntu|debian)
            apt-get update -qq
            apt-get install -y -qq wireguard wireguard-tools qrencode iptables-persistent resolvconf >/dev/null 2>&1
            ;;
        centos|rhel|fedora|rocky|almalinux)
            dnf install -y -q wireguard-tools qrencode iptables-services >/dev/null 2>&1
            ;;
        arch|manjaro)
            pacman -S --noconfirm wireguard-tools qrencode iptables >/dev/null 2>&1
            ;;
        *)
            warn "OS no reconocido, intentando con wireguard-tools genérico..."
            ;;
    esac
    log "Dependencias instaladas"
}

generate_keys() {
    log "Generando claves WireGuard..."
    mkdir -p /etc/wireguard
    chmod 700 /etc/wireguard

    # Claves del servidor
    SERVER_PRIVATE_KEY=$(wg genkey)
    SERVER_PUBLIC_KEY=$(echo "$SERVER_PRIVATE_KEY" | wg pubkey)

    # Pre-shared key (opcional, extra seguridad)
    PSK=$(wg genpsk)

    # Guardar claves del servidor
    cat > /etc/wireguard/server_keys.conf <<EOF
[Server]
PrivateKey = $SERVER_PRIVATE_KEY
PublicKey = $SERVER_PUBLIC_KEY
PreSharedKey = $PSK
EOF
    chmod 600 /etc/wireguard/server_keys.conf

    log "Claves generadas"
    log "Server Public Key: $SERVER_PUBLIC_KEY"
}

create_server_config() {
    log "Creando configuración del servidor..."

    cat > /etc/wireguard/$WG_INTERFACE.conf <<EOF
[Interface]
Address = $SERVER_WG_IP/24
ListenPort = $WG_PORT
PrivateKey = $SERVER_PRIVATE_KEY
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o $(ip route | grep default | awk '{print $5}') -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o $(ip route | grep default | awk '{print $5}') -j MASQUERADE
SaveConfig = true

EOF

    chmod 600 /etc/wireguard/$WG_INTERFACE.conf
    log "Configuración del servidor creada"
}

configure_sysctl() {
    log "Configurando sysctl para forwarding..."
    cat > /etc/sysctl.d/99-wireguard.conf <<EOF
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
EOF
    sysctl --system >/dev/null 2>&1
    log "IP forwarding habilitado"
}

configure_firewall() {
    log "Configurando firewall..."

    # UFW
    if command -v ufw >/dev/null 2>&1; then
        ufw allow $SSH_PORT/tcp comment "SSH" >/dev/null 2>&1
        ufw allow $WG_PORT/udp comment "WireGuard" >/dev/null 2>&1
        ufw --force enable >/dev/null 2>&1
        log "UFW configurado"
    fi

    # iptables persistente
    if command -v netfilter-persistent >/dev/null 2>&1; then
        netfilter-persistent save >/dev/null 2>&1
    elif command -v iptables-save >/dev/null 2>&1; then
        iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
        ip6tables-save > /etc/iptables/rules.v6 2>/dev/null || true
    fi
}

create_client_config() {
    local client_name=$1
    local client_ip=$2

    log "Generando configuración para cliente: $client_name ($client_ip)"

    # Generar claves del cliente
    CLIENT_PRIVATE_KEY=$(wg genkey)
    CLIENT_PUBLIC_KEY=$(echo "$CLIENT_PRIVATE_KEY" | wg pubkey)

    # Agregar peer al servidor
    cat >> /etc/wireguard/$WG_INTERFACE.conf <<EOF

[Peer]
# $client_name
PublicKey = $CLIENT_PUBLIC_KEY
PresharedKey = $PSK
AllowedIPs = $client_ip/32
EOF

    # Recargar configuración
    wg syncconf $WG_INTERFACE <(wg-quick strip $WG_INTERFACE) 2>/dev/null || true

    # Generar archivo de configuración del cliente
    local client_conf="/etc/wireguard/client_${client_name}.conf"
    cat > "$client_conf" <<EOF
[Interface]
PrivateKey = $CLIENT_PRIVATE_KEY
Address = $client_ip/24
DNS = $CLIENT_DNS

[Peer]
PublicKey = $SERVER_PUBLIC_KEY
PresharedKey = $PSK
Endpoint = $SERVER_PUBLIC_IP:$WG_PORT
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
EOF

    # Generar QR code
    qrencode -t ansiutf8 < "$client_conf" > "/etc/wireguard/client_${client_name}.qr" 2>/dev/null || true

    # Guardar credenciales del cliente
    cat > "/etc/wireguard/client_${client_name}_keys.conf" <<EOF
[Client: $client_name]
PrivateKey = $CLIENT_PRIVATE_KEY
PublicKey = $CLIENT_PUBLIC_KEY
PresharedKey = $PSK
Address = $client_ip/24
EOF
    chmod 600 "/etc/wireguard/client_${client_name}_keys.conf"

    log "Cliente $client_name creado: $client_ip"
    log "Config guardada en: $client_conf"
    log "QR code guardado en: /etc/wireguard/client_${client_name}.qr"
}

add_client() {
    local name=$1
    if [[ -z "$name" ]]; then
        read -rp "Nombre del cliente (ej: iphone, laptop, android): " name
    fi

    # Buscar IP libre
    local used_ips=()
    while IFS= read -r line; do
        if [[ $line =~ AllowedIPs\ =\ ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) ]]; then
            used_ips+=("${BASH_REMATCH[1]}")
        fi
    done < /etc/wireguard/$WG_INTERFACE.conf

    local next_ip=$CLIENT_IP_START
    while [[ " ${used_ips[*]} " =~ " 10.8.0.$next_ip " ]]; do
        ((next_ip++))
    done

    if [[ $next_ip -gt $CLIENT_IP_END ]]; then
        error "No hay IPs disponibles"
    fi

    local client_ip="10.8.0.$next_ip"
    create_client_config "$name" "$client_ip"

    # Recargar WireGuard
    wg syncconf $WG_INTERFACE <(wg-quick strip $WG_INTERFACE) 2>/dev/null || systemctl reload wg-quick@$WG_INTERFACE 2>/dev/null || true

    log "Cliente $name agregado con IP $client_ip"
}

enable_service() {
    log "Habilitando y iniciando servicio WireGuard..."
    systemctl enable wg-quick@$WG_INTERFACE >/dev/null 2>&1
    systemctl start wg-quick@$WG_INTERFACE
    sleep 2
    if systemctl is-active --quiet wg-quick@$WG_INTERFACE; then
        log "WireGuard iniciado correctamente"
    else
        error "WireGuard no pudo iniciarse. Revisa: journalctl -u wg-quick@$WG_INTERFACE"
    fi
}

show_client_config() {
    local name=$1
    if [[ -z "$name" ]]; then
        read -rp "Nombre del cliente: " name
    fi

    local conf="/etc/wireguard/client_${name}.conf"
    local qr="/etc/wireguard/client_${name}.qr"

    if [[ -f "$conf" ]]; then
        echo -e "\n${GREEN}=== Configuración para $name ===${NC}"
        cat "$conf"
        echo -e "\n${BLUE}QR Code (escanear con app WireGuard en celular):${NC}"
        if [[ -f "$qr" ]]; then
            cat "$qr"
        else
            qrencode -t ansiutf8 < "/etc/wireguard/client_${name}.conf" 2>/dev/null || echo "qrencode no disponible"
        fi
        echo -e "\nArchivo de config: $conf"
        echo "QR code: $qr"
    else
        error "Cliente '$name' no encontrado"
    fi
}

list_clients() {
    echo -e "\n${BLUE}=== Clientes configurados ===${NC}"
    if [[ -f /etc/wireguard/$WG_INTERFACE.conf ]]; then
        grep -A1 "^\[Peer\]" /etc/wireguard/$WG_INTERFACE.conf | grep -E "(Peer|PublicKey|AllowedIPs)" | sed 's/^[[:space:]]*//' | while IFS= read -r line; do
            if [[ $line == "[Peer]" ]]; then
                echo ""
            else
                echo "  $line"
            fi
        done
    else
        echo "  (ningún cliente configurado)"
    fi
}

show_status() {
    echo -e "\n${BLUE}=== Estado WireGuard ===${NC}"
    echo "Interfaz: $WG_INTERFACE"
    echo "Puerto: $WG_PORT"
    echo "IP Server: $SERVER_WG_IP"
    echo "IP Pública: $SERVER_PUBLIC_IP"
    echo "Subred: $WG_SUBNET"
    echo ""

    if systemctl is-active --quiet wg-quick@$WG_INTERFACE; then
        echo -e "Estado: ${GREEN}ACTIVO${NC}"
    else
        echo -e "Estado: ${RED}INACTIVO${NC}"
    fi

    echo ""
    wg show 2>/dev/null || echo "WireGuard no está corriendo"
}

uninstall() {
    warn "Esto eliminará WireGuard completamente. ¿Continuar? (y/N)"
    read -r confirm
    [[ $confirm != "y" && $confirm != "Y" ]] && exit 0

    systemctl stop wg-quick@$WG_INTERFACE 2>/dev/null || true
    systemctl disable wg-quick@$WG_INTERFACE >/dev/null 2>&1 || true

    # Eliminar reglas iptables
    iptables -t nat -D POSTROUTING -o $(ip route | grep default | awk '{print $5}') -j MASQUERADE 2>/dev/null || true

    # Eliminar archivos
    rm -rf /etc/wireguard
    rm -f /etc/sysctl.d/99-wireguard.conf
    rm -f /etc/iptables/rules.v4 /etc/iptables/rules.v6

    apt-get remove -y wireguard wireguard-tools qrencode >/dev/null 2>&1 || dnf remove -y wireguard-tools qrencode >/dev/null 2>&1 || true

    log "WireGuard desinstalado completamente"
}

usage() {
    cat <<EOF
${BLUE}===========================================${NC}
${GREEN}WIREGUARD VPN SETUP - OUTLIER / DATAANNOTATION${NC}
${BLUE}===========================================${NC}

Uso: sudo ./wg-setup.sh [comando] [opciones]

COMANDOS:
  install              Instala y configura WireGuard completo
  add-client <nombre>  Agrega un nuevo cliente (ej: iphone, laptop)
  list                 Lista clientes configurados
  show <nombre>        Muestra config + QR code del cliente
  status               Estado del servidor WireGuard
  uninstall            Desinstala WireGuard completamente

EJEMPLOS:
  sudo ./wg-setup.sh install              # Instalación completa
  sudo ./wg-setup.sh add-client iphone    # Agregar cliente "iphone"
  sudo ./wg-setup.sh add-client laptop    # Agregar cliente "laptop"
  ./go --mega-fast-status                 # Ver estado desde OWNEX
  ./go --mega-fast-plan                   # Ver plan del día

CONFIGURACIÓN PREVIA (editar variables al inicio del script):
  SERVER_PUBLIC_IP=""     # IP pública del VPS (auto-detecta)
  WG_PORT=51820           # Puerto WireGuard
  WG_SUBNET="10.8.0.0/24" # Subred VPN
  SERVER_WG_IP="10.8.0.1" # IP del servidor en la VPN

REQUISITOS:
  - VPS con Ubuntu 20.04+/22.04+/24.04, Debian 11+/12, CentOS 8+, Fedora, Arch
  - Acceso root (sudo)
  - Puerto 51820/udp abierto en firewall/cloud firewall
  - IP pública estática en el VPS

DESPUÉS DE INSTALAR:
  1. sudo ./wg-setup.sh add-client iphone
  2. sudo ./wg-setup.sh show iphone
  3. Escanear QR en app WireGuard del celular
  3. Configurar en Outlier/DataAnnotation: usar IP 10.8.0.x como proxy

${BLUE}===========================================${NC}
EOF
}

# ============================================================
# MAIN
# ============================================================

main() {
    check_root
    detect_os
    detect_public_ip

    case "${1:-}" in
        install)
            install_dependencies
            generate_keys
            create_server_config
            configure_sysctl
            configure_firewall
            enable_service
            # Crear cliente por defecto
            add_client "default"
            show_status
            echo -e "\n${GREEN}✅ Instalación completada!${NC}"
            echo "Agrega clientes con: sudo ./wg-setup.sh add-client <nombre>"
            ;;
        add-client)
            add_client "${2:-}"
            ;;
        list)
            list_clients
            ;;
        show)
            show_client_config "${2:-}"
            ;;
        status)
            show_status
            ;;
        uninstall)
            uninstall
            ;;
        *)
            usage
            ;;
    esac
}

main "$@"