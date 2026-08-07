#!/bin/bash
# ============================================================
# FREE VPN OPTIONS FOR OUTLIER / DATAANNOTATION FROM ARGENTINA
# ============================================================
# Todas las opciones GRATIS para acceder a Outlier/DataAnnotation desde Argentina
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ============================================================
# OPCIÓN 1: CLOUDFLARE WARP (Gratis, fácil, PERO bloqueado por Outlier)
# ============================================================
setup_cloudflare_warp() {
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════╗
║  OPCIÓN 1: CLOUDFLARE WARP (1.1.1.1)                         ║
╠═══════════════════════════════════════════════════════════════╣
║  ✅ GRATIS, open source client, WireGuard                     ║
║  ✅ Instalación: 1 click (app) / apt install cloudflare-warp  ║
║  ❌ PROBLEMA: Outlier/DataAnnotation BLOQUEAN IPs de Cloudflare║
║  ❌ IPs de WARP son conocidas y bloqueadas                    ║
║                                                               ║
║  VEREDICTO: ❌ NO FUNCIONA para Outlier/DataAnnotation        ║
╚═══════════════════════════════════════════════════════════════╝

# Instalación (solo por si acaso):
# Ubuntu/Debian:
#   curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
#   echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list
#   sudo apt update && sudo apt install cloudflare-warp
#   warp-cli register
#   warp-cli connect

EOF
}

# ============================================================
# OPCIÓN 2: PROTONVPN FREE (Gratis, 3 países, 1 dispositivo)
# ============================================================
setup_protonvpn_free() {
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════╗
║  OPCIÓN 2: PROTONVPN FREE                                     ║
╠═══════════════════════════════════════════════════════════════╣
║  ✅ GRATIS, open source client, sin logs, Suiza               ║
║  ⚠️ SOLO 3 países: US, NL, JP                                ║
║  ⚠️ 1 dispositivo, velocidad limitada                         ║
║  ⚠️ IPs a veces quemadas por Outlier                          ║
║  ⚠️ 1 dispositivo solo                                        ║
║                                                               ║
║  VEREDICTO: ⚠️ FUNCIONA A VECES (rotar IPs)                   ║
╚═══════════════════════════════════════════════════════════════╝

# Instalación Linux:
#   sudo apt update && sudo apt install -y protonvpn-cli
#   protonvpn-cli login <tu_usuario>
#   protonvpn-cli connect --free

# O con OpenVPN (más estable):
#   Descargar configs de: https://account.protonvpn.com/downloads
#   sudo openvpn --config us-free-01.protonvpn.com.udp.ovpn

# Verificar IP:
#   curl ifconfig.me

EOF
}

# ============================================================
# OPCIÓN 3: WINDSCRIBE FREE (10GB/mes, 10 países)
# ============================================================
setup_windscribe_free() {
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════╗
║  OPCIÓN 3: WINDSCRIBE FREE (10GB/mes)                        ║
╠═══════════════════════════════════════════════════════════════╣
║  ✅ 10GB/mes gratis (confirmando email)                       ║
║  ✅ 10 países gratis (US, UK, CA, FR, DE, NL, CH, NO, RO, TR)║
║  ✅ Cliente CLI nativo Linux                                  ║
║  ⚠️ 10GB/mes se agota si usás video/streaming                ║
║  ⚠️ IPs a veces quemadas, pero rotan                          ║
║                                                               ║
║  VEREDICTO: ✅ MEJOR OPCIÓN 100% GRATIS                       ║
╚═══════════════════════════════════════════════════════════════╝

# Instalación Ubuntu/Debian:
#   sudo apt update && sudo apt install -y wget gpg
#   wget -qO- https://repo.windscribe.com/keys/windscribe.gpg | sudo gpg --dearmor -o /usr/share/keyrings/windscribe.gpg
#   echo "deb [signed-by=/usr/share/keyrings/windscribe.gpg] https://repo.windscribe.com/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/windscribe.list
#   sudo apt update && sudo apt install -y windscribe-cli

# Uso:
#   windscribe login        # Tu usuario/email
#   windscribe connect US   # Conectar a US
#   windscribe status       # Ver estado
#   windscribe disconnect   # Desconectar

# Verificar IP:
#   curl ifconfig.me

EOF
}

# ============================================================
# OPCIÓN 4: PROTONVPN FREE + WIREGUARD (OpenVPN configs)
# ============================================================
setup_protonvpn_wireguard() {
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════╗
║  OPCIÓN 4: PROTONVPN FREE + WIREGUARD (configs manuales)     ║
╠═══════════════════════════════════════════════════════════════╣
║  ✅ Usa WireGuard (más rápido que OpenVPN)                   ║
║  ⚠️ Configs manuales desde: https://account.protonvpn.com/downloads ║
║  ⚠️ Solo 3 países free: US, NL, JP                            ║
║                                                               ║
║  VEREDICTO: ⚠️ FUNCIONA PERO IPs A VECES QUEMADAS            ║
╚═══════════════════════════════════════════════════════════════╝

# Descargar configs WireGuard de: https://account.protonvpn.com/downloads
#   wget "https://api.protonvpn.ch/vpn/config?version=2&platform=linux&protocol=wireguard" -O protonvpn-wg.zip
#   unzip protonvpn-wg.zip
#   sudo cp *.conf /etc/wireguard/
#   sudo wg-quick up protonvpn-us-free-01

EOF
}

# ============================================================
# OPCIÓN 5: TAILSCALE + VPS PROPIO ($5/mes - "gratis" si tenés VPS)
# ============================================================
setup_tailscale_vps() {
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════╗
║  OPCIÓN 5: TAILSCALE + VPS PROPIO ($5/mes)                   ║
╠═══════════════════════════════════════════════════════════════╣
║  ✅ 100% confiable, IP dedicada, nunca bloqueada             ║
║  ✅ Mesh VPN: PC + Celular + VPS en una red                   ║
║  ✅ Exit node: todo el tráfico sale por el VPS                ║
║  💰 $5-6/mes (Hetzner CX22, DigitalOcean $4, Vultr $5)       ║
║  🛠 Setup: 15 min                                             ║
║                                                               ║
║  VEREDICTO: ✅ MEJOR OPCIÓN SI TENÉS $5/MES                  ║
╚═══════════════════════════════════════════════════════════════╝

# 1. Crear VPS (Hetzner CX22 $5.83/mes, DigitalOcean $4, Vultr $5)
# 2. En VPS:
#    curl -fsSL https://tailscale.com/install.sh | sh
#    sudo tailscale up --advertise-exit-node
# 3. En PC/Cell:
#    curl -fsSL https://tailscale.com/install.sh | sh
#    sudo tailscale up --login-server=https://controlplane.tailscale.com
# 4. En Tailscale admin: habilitar "Exit node" para tu VPS
# 4. En celular/PC: conectar al exit node del VPS

# Verificar:
#   curl ifconfig.me  # Debe mostrar IP del VPS

EOF
}

# ============================================================
# OPCIÓN 6: WIREGUARD + VPS PROPIO ($5/mes) - SCRIPT INCLUIDO
# ============================================================
setup_wireguard_vps() {
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════╗
║  OPCIÓN 6: WIREGUARD + VPS PROPIO ($5/mes) - SCRIPT INCLUIDO ║
╠═══════════════════════════════════════════════════════════════╣
║  ✅ IP dedicada, nunca bloqueada                               ║
║  ✅ Control total, sin logs de terceros                        ║
║  ✅ Sirve para: Outlier, DataAnnotation, Obsidian, Git, trading ║
║  💰 $5-6/mes (Hetzner CX22 $5.83, DO $4, Vultr $5)            ║
║  🛠 Script automático: wg-setup.sh (ya incluido en OWNEX)     ║
║                                                               ║
║  VEREDICTO: ✅ MEJOR OPCIÓN SI TENÉS $5/MES                  ║
╚═══════════════════════════════════════════════════════════════╝

# Ver script: wg-setup.sh (ya incluido en OWNEX)
#   sudo ./wg-setup.sh install
#   sudo ./wg-setup.sh add-client iphone
#   sudo ./wg-setup.sh show iphone

EOF
}

# ============================================================
# OPCIÓN 7: TAILSCALE + VPS PROPIO (Alternativa a WireGuard)
# ============================================================
setup_tailscale_vps() {
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════╗
║  OPCIÓN 7: TAILSCALE + VPS PROPIO ($5/mes)                   ║
╠═══════════════════════════════════════════════════════════════╣
║  ✅ Mesh VPN: PC + Celular + VPS en una red                  ║
║  ✅ Exit node: todo el tráfico sale por el VPS                ║
║  ✅ No configura firewall/iptables manualmente                ║
║  💰 $5-6/mes (Hetzner CX22 $5.83, DO $4, Vultr $5)           ║
║  🛠 Setup: 10 min                                             ║
║                                                               ║
║  VEREDICTO: ✅ ALTERNATIVA SIMPLE A WIREGUARD                ║
╚═══════════════════════════════════════════════════════════════╝

# 1. VPS + Tailscale:
#    curl -fsSL https://tailscale.com/install.sh | sh
#    sudo tailscale up --advertise-exit-node
# 
# 2. PC/Cell:
#    curl -fsSL https://tailscale.com/install.sh | sh
#    sudo tailscale up --login-server=https://controlplane.tailscale.com
# 
# 3. En Tailscale admin: habilitar "Exit node" para tu VPS
# 4. En celular/PC: conectar al exit node del VPS

EOF
}

# ============================================================
# OPCIÓN 8: PROTONVPN FREE + WIREGUARD (configs manuales)
# ============================================================
setup_protonvpn_wg() {
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════╗
║  OPCIÓN 8: PROTONVPN FREE + WIREGUARD (configs manuales)     ║
╠═══════════════════════════════════════════════════════════════╣
║  ✅ WireGuard nativo (más rápido que OpenVPN)                ║
║  ⚠️ Configs manuales desde: https://account.protonvpn.com/downloads ║
║  ⚠️ Solo 3 países free: US, NL, JP                            ║
║                                                               ║
║  VEREDICTO: ⚠️ FUNCIONA PERO IPs A VECES QUEMADAS            ║
╚═══════════════════════════════════════════════════════════════╝

# Descargar configs:
#   wget "https://api.protonvpn.ch/vpn/config?version=2&platform=linux&protocol=wireguard" -O protonvpn-wg.zip
#   unzip protonvpn-wg.zip
#   sudo cp *.conf /etc/wireguard/
#   sudo wg-quick up protonvpn-us-free-01

EOF
}

# ============================================================
# COMPARATIVA FINAL
# ============================================================
show_comparison() {
    cat <<'EOF'

╔════════════════════════════════════════════════════════════════════════╗
║                    RESUMEN: VPN GRATIS PARA OUTLIER                  ║
╠═══════════════════════════════════════════════════════════════════════╣
║ OPCIÓN                    │ COSTO  │ CONFIABLE │ VELOCIDAD │ ESFUERZO ║
╠───────────────────────────┼────────┼───────────┼───────────┼──────────╣
║ Cloudflare WARP           │ $0     │ ❌ Bloqueada │ Rápida    │ 1 min    ║
║ ProtonVPN Free            │ $0     │ ⚠️ Media    │ Media     │ 5 min    ║
║ Windscribe Free (10GB)    │ $0     │ ✅ Media    │ Buena     │ 5 min    ║
║ ProtonVPN Free + WG       │ $0     │ ⚠️ Media    │ Rápida    │ 10 min   ║
║ Tailscale + VPS propio    │ $5/mes │ ✅ 100%      │ Muy rápida│ 15 min   ║
║ WireGuard + VPS propio    │ $5/mes │ ✅ 100%      │ Muy rápida│ 15 min   ║
║ Tailscale + VPS propio    │ $5/mes │ ✅ 100%      │ Muy rápida│ 10 min   ║
╚═══════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════╗
║                         RECOMENDACIÓN FINAL                            ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  🆓 SI QUERÉS 100% GRATIS:                                            ║
║     Windscribe Free (10GB/mes) + rotar con ProtonVPN Free             ║
║     Funciona ~80% del tiempo, rotar IPs cuando falle                 ║
║                                                                        ║
║  💰 SI QUERÉS 100% CONFIABLE, UNA VEZ Y LISTO:                        ║
║     VPS $5/mes (Hetzner/Do/Vultr) + WireGuard/Tailscale              ║
║     IP dedicada, nunca bloqueada, sirve para TODO                    ║
║                                                                        ║
║  🚫 NO PIERDAS TIEMPO: Cloudflare WARP NO FUNCIONA (IPs quemadas)   ║
║                                                                        ║
╚═══════════════════════════════════════════════════════════════════════╝

EOF
}

# ============================================================
# MENU INTERACTIVO
# ============================================================

main() {
    clear
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════════════╗
║           🇦🇷 VPN GRATIS PARA OUTLIER / DATAANNOTATION 🇦🇷          ║
║                    DESDE ARGENTINA - TODAS LAS OPCIONES              ║
╚══════════════════════════════════════════════════════════════════════╝

EOF

    show_comparison

    echo -e "\n${BLUE}¿Qué opción querés ver en detalle?${NC}"
    echo "  1) Cloudflare WARP (NO funciona - solo info)"
    echo "  2) ProtonVPN Free"
    echo "  3) Windscribe Free (10GB) ⭐ RECOMENDADA GRATIS"
    echo "  4) ProtonVPN Free + WireGuard"
    echo "  5) Tailscale + VPS propio ($5/mes)"
    echo "  6) WireGuard + VPS propio ($5/mes) - SCRIPT INCLUIDO"
    echo "  7) Tailscale + VPS propio ($5/mes)"
    echo "  8) ProtonVPN Free + WireGuard"
    echo "  9) Comparativa completa"
    echo "  0) Salir"
    echo ""
    read -rp "Opción [0-9]: " opt

    case ${opt:-} in
        1) setup_cloudflare_warp ;;
        2) setup_protonvpn_free ;;
        3) setup_windscribe_free ;;
        4) setup_protonvpn_wireguard ;;
        5) setup_tailscale_vps ;;
        6) setup_wireguard_vps ;;
        7) setup_tailscale_vps ;;
        8) setup_protonvpn_wireguard ;;
        9) show_comparison ;;
        0) exit 0 ;;
        *) warn "Opción inválida" ;;
    esac

    echo ""
    read -rp "Presioná Enter para continuar..."
    main
}

main "$@"
