"""Asistente de VPN gratis para Argentina → Outlier/DataAnnotation.

Detecta la IP actual, evalúa compatibilidad, y guía/conecta opciones 100% gratis.
No pide inversión: todo es gratuito.

NOTA técnica: Outlier y DataAnnotation corriendo en el NAVEGADOR de WINDOWS necesitan
que la VPN corra a nivel de SISTEMA en Windows (no solo dentro de WSL2). Este módulo
detecta el escenario real y da el camino correcto.

ACTUALIZACIÓN 2026-08-24 (verificación de mercado): Outlier acepta Argentina DIRECTO
(ID + móvil del país real, postulación sin VPN); ídem Mercor/Alignerr/Mindrift.
DataAnnotation sigue limitado a US/UK/CA/AU/NZ/IE. La vía VPN queda ARCHIVADA —
el flujo activo es core/application_assistant.py (postulación honesta).
Fuentes: outlier.ai (requisitos ID/país), reviews 2026 (theairankings.com,
remotestack.in — AR listado entre países aceptados, tarifas region-tiered).
"""

from __future__ import annotations

import json
import logging
import platform
import socket
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("core.vpn_assistant")

# Países aceptados por OUTLIER (trabajo remoto, 2026). Argentina verificado
# aceptado directo — postulación con ID + móvil reales, sin VPN.
ALLOWED_COUNTRIES: set[str] = {
    "AR",
    "MX",
    "US",
    "CA",
    "GB",
    "AU",
    "NZ",
    "IE",
    "IN",
    "PH",
    "ZA",
    "MY",
    "NG",
    "PK",
    "BD",
    "KE",
    "GH",
    "LK",
    "NP",
    "PL",
    "RO",
    "ES",
    "IT",
    "FR",
    "DE",
    "NL",
    "PT",
    "GR",
    "HU",
    "BG",
    "HR",
}

# DataAnnotation sigue limitado a estos 6 países (2026) — AR NO incluido.
DATAANNOTATION_ALLOWED_COUNTRIES: set[str] = {"US", "CA", "GB", "AU", "NZ", "IE"}

DISALLOWED_COUNTRIES: set[str] = {"CN", "RU", "IR", "KP", "CU", "VN", "VE"}


@dataclass
class VpnStatus:
    """Estado actual de conexión/VPN."""

    online: bool = False
    public_ip: str = ""
    country_code: str = ""
    country_name: str = ""
    isp: str = ""
    provider: str = ""
    compatible: bool = False
    reason: str = ""
    source: str = "ipapi"  # ipapi | cached | unknown

    def to_dict(self) -> dict[str, Any]:
        return {
            "online": self.online,
            "public_ip": self.public_ip,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "isp": self.isp,
            "provider": self.provider,
            "compatible": self.compatible,
            "reason": self.reason,
        }


def _public_ip() -> str:
    """Obtener IP pública real."""
    for base in (
        "https://ifconfig.me",
        "https://api.ipify.org",
        "https://4.icanhazip.com",
    ):
        try:
            out = subprocess.run(
                ["curl", "-4", "-s", "--max-time", "8", base],
                capture_output=True,
                text=True,
                timeout=12,
            )
            ip = out.stdout.strip()
            if ip and "error" not in ip.lower():
                # validar que es IPv4
                try:
                    socket.inet_pton(socket.AF_INET, ip)
                    return ip
                except OSError:
                    continue
        except Exception:
            continue
    return ""


def _geo(ip: str) -> dict[str, str]:
    """Geolocalización simple vía ip-api.com (gratis, sin key)."""
    try:
        out = subprocess.run(
            [
                "curl",
                "-s",
                "--max-time",
                "8",
                f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,query,isp",
            ],
            capture_output=True,
            text=True,
            timeout=12,
        )
        data = json.loads(out.stdout)
        if data.get("status") == "success":
            return {
                "country": data.get("country", ""),
                "country_code": data.get("countryCode", ""),
                "isp": data.get("isp", ""),
            }
    except Exception:
        return {}
    return {}


class VpnAssistant:
    """Detecta y facilita VPN gratis para acceder desde Argentina."""

    def __init__(self) -> None:
        self.os_name = platform.system()
        # WSL2 se ve como "Linux" pero es Windows en el fondo
        self.is_wsl = "microsoft" in (platform.release() or "").lower() or "WSL" in platform.release().upper()

    # ── Diagnóstico ──

    def detect(self) -> VpnStatus:
        """Detectar estado actual: IP, país, compatibilidad."""
        ip = _public_ip()
        status = VpnStatus()
        if not ip:
            status.online = False
            status.provider = "windscribe"
            return status

        status.online = True
        status.public_ip = ip
        geo = _geo(ip)
        status.country_code = geo.get("country_code", "??")
        status.country_name = geo.get("country", "")
        status.isp = geo.get("isp", "")
        status.provider = "windscribe"

        code = status.country_code.upper()
        if code in DISALLOWED_COUNTRIES:
            status.compatible = False
            status.reason = f"País ({code}) no habilitado para Outlier/DataAnnotation"
        elif code in ALLOWED_COUNTRIES:
            status.compatible = True
            if code in DATAANNOTATION_ALLOWED_COUNTRIES:
                status.reason = f"País ({code}) compatible con Outlier y DataAnnotation"
            else:
                status.reason = (
                    f"País ({code}) aceptado por Outlier/Mercor/Alignerr/Mindrift — "
                    "postulá directo sin VPN (core/application_assistant). "
                    "DataAnnotation sigue limitado a US/UK/CA/AU/NZ/IE."
                )
        else:
            status.compatible = False
            status.reason = f"País ({code}) no confirmado — verificar manualmente"

        # Detectar VPN activa por ISP conocido
        isp = status.isp.lower()
        for marker, name in {
            "windscribe": "Windscribe",
            "proton": "ProtonVPN",
            "mullvad": "Mullvad",
            "nordvpn": "NordVPN",
            "data center": "DataCenter",
            "constant company": "Windscribe",
        }.items():
            if marker in isp:
                status.provider = name
                break

        return status

    # ── Comparativa / guía ──

    def free_options(self) -> list[dict[str, Any]]:
        """Opciones 100% gratis ordenadas por recomendación."""
        options = [
            {
                "name": "Windscribe Free (10GB/mes)",
                "cost": "$0",
                "reliability": "alta",
                "extra": "10 países gratis (US, CA, UK...). Cliente nativo Windows/Mac/Linux. IPs rotan bien. 10GB/mes alcanza para Outlier/DataAnnotation (no para streaming).",
                "order": 1,
                "recommended": True,
            },
            {
                "name": "ProtonVPN Free",
                "cost": "$0",
                "reliability": "media",
                "extra": "3 países (US, NL, JP), 1 dispositivo. Open source, sin logs. IPs a veces quemadas por Outlier, pero rotando puede funcionar.",
                "order": 2,
                "recommended": False,
            },
            {
                "name": "Cloudflare WARP (1.1.1.1)",
                "cost": "$0",
                "reliability": "baja",
                "extra": "Rápido y fácil, PERO las IPs de WARP son conocidas y Outlier/DataAnnotation las BLOQUEAN. No recomendado para esto.",
                "order": 3,
                "recommended": False,
            },
        ]
        options.sort(key=lambda x: x["order"])
        return options

    def guidance(self) -> dict[str, Any]:
        """Guía práctica adaptada al OS real."""
        status = self.detect()
        steps = []
        if platform.system() == "Windows":
            steps = [
                "1. Descargá Windscribe desde https://windscribe.com/download (app de Windows).",
                "2. Creá cuenta gratis (email + confirmación). Sin tarjeta.",
                "3. Abrí la app y elegí un servidor de Estados Unidos (p.ej. US Central).",
                "4. Apretá CONNECT. La app cubre TODO el tráfico de Windows, incluye el navegador.",
                "5. Verificá acá en OWNEX que tu IP quedó en US y sea compatible.",
            ]
        else:
            steps = [
                "Estás en WSL/Linux. Si Outlier/DataAnnotation corren en el navegador de WINDOWS,",
                "la VPN debe activarse en Windows (app Windscribe), NO solo en Linux.",
                "Instalá Windscribe en el lado Windows: https://windscribe.com/download",
                "Si vas a usar herramientas de línea de comandos de OWNEX en Linux, también podés",
                "instalar Windscribe acá (apt), ver 'auto_install'.",
            ]

        return {
            "os": platform.system(),
            "is_wsl": self.is_wsl,
            "status": status.to_dict(),
            "steps": steps,
            "options": self.free_options(),
        }

    # ── Checks de compatibilidad rápidos ──

    def check_outlier(self) -> dict[str, Any]:
        """Chequeo de alcance real: si IP actual permitiría Outlier/DA."""
        status = self.detect()
        if status.compatible:
            verdict = "OK — postulá directo (ver /api/applications/plan)"
        else:
            verdict = "Sin cobertura directa — revisá /api/applications/plan"
        return {
            "compatible": status.compatible,
            "country": status.country_name,
            "country_code": status.country_code,
            "ip": status.public_ip,
            "isp": status.isp,
            "reason": status.reason,
            "verdict": verdict,
        }

    # ── Auto-instalación (Linux/WSL) ──

    def install_windscribe_linux(self) -> dict[str, Any]:
        """Instalar y configurar Windscribe CLI en Linux/WSL (libre)."""
        try:
            if self.is_wsl and "microsoft" in (platform.release() or "").lower():
                return {
                    "success": False,
                    "note": "Estás en WSL2: la VPN para Outlier debe ir en Windows. `windscribe` en WSL no cubre el navegador.",
                }

            cmds = [
                "sudo apt-get update -y",
                "sudo apt-get install -y wget gpg apt-transport-https",
                "wget -qO- https://repo.windscribe.com/keys/windscribe.gpg | sudo gpg --dearmor -o /usr/share/keyrings/windscribe.gpg",
                'echo "deb [signed-by=/usr/share/keyrings/windscribe.gpg] https://repo.windscribe.com/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/windscribe.list',
                "sudo apt-get update -y",
                "sudo apt-get install -y windscribe-cli",
            ]
            for c in cmds:
                subprocess.run(["bash", "-c", c], check=True, capture_output=True, timeout=120)
            return {
                "success": True,
                "message": "Windscribe CLI instalado. Logueate con: windscribe login  y conectá con:  windscribe connect US",
            }
        except Exception as e:
            return {"success": False, "message": f"Error instalando Windscribe: {e}"}

    # ── Integración con Windows (WSL2 → powershell) ──

    @staticmethod
    def _win_app_installed(exe_name: str) -> bool:
        """Comprobar si un .exe está instalado en Windows (Program Files)."""
        out = _win_powershell(
            [
                "Get-ChildItem -Path 'C:\\Program Files\\','C:\\Program Files (x86)\\' "
                f"-Filter '{exe_name}.exe' -Recurse -Depth 3 -ErrorAction SilentlyContinue "
                "| Select-Object -First 1 -ExpandProperty FullName"
            ]
        )
        clean = out.strip().replace("\r", "").replace("\n", "")
        return bool(clean) and "ERR:" not in out

    @staticmethod
    def _win_app_running(exe_name: str) -> bool:
        cnt = _win_powershell(
            [f"if (Get-Process {exe_name} -ErrorAction SilentlyContinue) {{ 'UP' }} else {{ 'DOWN' }}"]
        )
        return "UP" in cnt

    @staticmethod
    def _win_launch(exe_name: str) -> None:
        _win_powershell(
            [
                f"Start-Process -FilePath (Get-Command {exe_name} -ErrorAction SilentlyContinue).Source -ErrorAction SilentlyContinue"
            ]
        )

    # ── PHP de cuentas gratuitas conocidas ──

    FREE_VPNS = [
        {
            "key": "windscribe",
            "name": "Windscribe",
            "exe": "Windscribe",
            "url": "https://windscribe.com/download",
            "free": "10GB/mes, 10 países",
            "install_step": "Instalá la app de Windows (siguiente/siguiente) y creá cuenta gratis en windscribe.com.",
        },
        {
            "key": "protonvpn",
            "name": "ProtonVPN",
            "exe": "ProtonVPN",
            "url": "https://protonvpn.com/download-windows",
            "free": "3 países (US, NL, JP), 1 dispositivo",
            "install_step": "Instalá la app de Windows y creá cuenta gratis en account.protonvpn.com (sin tarjeta).",
        },
    ]

    def _check_installs(self) -> list[dict[str, Any]]:
        """Comprobar instalación de cada VPN gratis en Windows."""
        return self._installed_free_vpns()

    def readiness_report(self) -> dict[str, Any]:
        """Informe: qué VPNs gratis tenés instaladas, cuáles te faltan, y plan accionable."""
        vpns = self._installed_free_vpns()
        missing = [v for v in vpns if v["needs_install"]]
        status = self.detect()

        return {
            "success": True,
            "os": self.os_name,
            "is_wsl": self.is_wsl,
            "ip_status": status.to_dict(),
            "vpns": vpns,
            "missing_count": len(missing),
            "present": [v["name"] for v in vpns if not v["needs_install"]],
            "missing": [v["name"] for v in missing],
            "plan": self._alternation_plan(missing),
            "message": (
                f"Te falta instalar {len(missing)} VPN gratis: {', '.join(v['name'] for v in missing) or 'ninguna'}."
                if missing
                else "Tenés las dos VPNs gratis listas. Intercalá con el plan de abajo."
            ),
        }

    def _installed_free_vpns(self) -> list[dict[str, Any]]:
        """Devolver el estado instalación de cada VPN."""
        out = []
        for vpn in self.FREE_VPNS:
            installed = self._win_app_installed(vpn["exe"]) if self.is_wsl else False
            out.append(
                {
                    **vpn,
                    "installed": installed,
                    "needs_install": not installed,
                }
            )
        return out

    def _alternation_plan(self, missing: list[dict[str, Any]]) -> list[str]:
        """Plan para intercalar las dos VPNs (o la que falte)."""
        if any(v["key"] == "windscribe" for v in missing):
            return [
                "Actualmente te falta instalar. Prioridad: Windscribe (más IPs pool).",
                "1. Instalá Windscribe (windows) y creá la cuenta gratis.",
                "2. Cuando la app funcione, conectá a US.",
                "3. Como respaldo añadí ProtonVPN (us, nl) para alternar IPs.",
                "Plan de intercalado: Lunes/Miércoles/Viernes Windscribe · Martes/Jueves/Sábado ProtonVPN.",
            ]
        return [
            "Todas las VPNs gratis instaladas.",
            "Intercalá así para rotar IPs y no quemar ninguna:",
            "Día impar (Lun/Mié/Vie): Windscribe → US",
            "Día par (Mar/Jue/Sáb): ProtonVPN → US",
            "Domingo: repasá IPs y elegí la que responde mejor a Outlier.",
        ]

    def windscribe_on_windows(self) -> dict[str, Any]:
        """Detectar, abrir y guiar Windscribe en Windows desde WSL2 (legacy, via readiness)."""
        report = self.readiness_report()
        ws = next((v for v in report["vpns"] if v["key"] == "windscribe"), None)
        if not ws or ws["needs_install"]:
            return {
                "success": False,
                "installed": False,
                "country_code": "US",
                "next_steps": report["plan"] if isinstance(report["plan"], list) else [str(report["plan"])],
            }
        self._win_launch("Windscribe")
        running = self._win_app_running("Windscribe")
        return {
            "success": True,
            "installed": True,
            "running": running,
            "aimed_country": "US",
            "next_steps": [
                "Windscribe abierto en Windows.",
                "En la app: elegí un servidor de Estados Unidos (p.ej. 'US Central').",
                "Apretá CONNECT.",
                "Revolvé acá → 'Chequear'. Tu IP debe quedar en US y la luz en verde.",
            ],
        }


def _win_powershell(cmd_parts: list[str]) -> str:
    """Ejecutar PowerShell en el lado Windows desde WSL/USUARIO."""
    try:
        script = " ".join(cmd_parts)
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return (out.stdout + out.stderr).strip()
    except Exception as e:
        return f"ERR:{e}"


def get_vpn_assistant() -> VpnAssistant:
    return VpnAssistant()
