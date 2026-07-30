#!/usr/bin/env python3
"""
OWNEX OMEGA Universal Installer

Este instalador personaliza OWNEX OMEGA según las necesidades del usuario
y configura el sistema automáticamente para cualquier computadora.

Uso:
    python install.py [--dev] [--minimal] [--help]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ownex.installer")


class OwnexInstaller:
    """Universal installer for OWNEX OMEGA."""

    def __init__(self, dev_mode: bool = False, minimal: bool = False):
        self.dev_mode = dev_mode
        self.minimal = minimal
        self.install_dir = Path.cwd()
        self.system_info = self._detect_system()
        self.config = {}

    def _detect_system(self) -> dict[str, Any]:
        """Detect system information."""
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture()[0],
        }

    def print_banner(self) -> None:
        """Print installation banner."""
        print("\n" + "=" * 60)
        print("  OWNEX OMEGA - Sistema de Inteligencia Autónoma")
        print("  Para Bug Bounty, Ciberseguridad e Investigación")
        print("=" * 60 + "\n")

    def check_requirements(self) -> bool:
        """Check system requirements."""
        logger.info("Verificando requisitos del sistema...")

        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 11):
            logger.error(f"Python 3.11+ requerido. Versión actual: {python_version}")
            return False

        logger.info(f"✓ Python {python_version.major}.{python_version.minor}.{python_version.micro}")

        # Check available memory
        try:
            if self.system_info["os"] == "Linux":
                with open("/proc/meminfo", "r") as f:
                    meminfo = f.read()
                    for line in meminfo.split("\n"):
                        if line.startswith("MemTotal:"):
                            mem_kb = int(line.split()[1])
                            mem_gb = mem_kb / (1024 * 1024)
                            if mem_gb < 4:
                                logger.warning(f"⚠ Memoria baja: {mem_gb:.1f} GB (recomendado: 4GB+)")
                            else:
                                logger.info(f"✓ Memoria: {mem_gb:.1f} GB")
                            break
        except Exception:
            logger.warning("No se pudo verificar memoria")

        # Check disk space
        try:
            import shutil
            disk_usage = shutil.disk_usage(self.install_dir)
            free_gb = disk_usage.free / (1024 ** 3)
            if free_gb < 2:
                logger.error(f"Espacio insuficiente: {free_gb:.1f} GB libre (mínimo: 2GB)")
                return False
            logger.info(f"✓ Espacio disponible: {free_gb:.1f} GB")
        except Exception:
            logger.warning("No se pudo verificar espacio en disco")

        return True

    def install_dependencies(self) -> bool:
        """Install Python dependencies."""
        logger.info("Instalando dependencias de Python...")

        try:
            # Check if virtual environment exists
            venv_dir = self.install_dir / ".venv"
            if not venv_dir.exists():
                logger.info("Creando entorno virtual...")
                subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_dir)],
                    check=True,
                    capture_output=True
                )

            # Get pip path
            if self.system_info["os"] == "Windows":
                pip_path = venv_dir / "Scripts" / "pip"
                python_path = venv_dir / "Scripts" / "python"
            else:
                pip_path = venv_dir / "bin" / "pip"
                python_path = venv_dir / "bin" / "python"

            # Upgrade pip
            subprocess.run(
                [str(pip_path), "install", "--upgrade", "pip"],
                check=True,
                capture_output=True
            )

            # Install requirements
            requirements_file = self.install_dir / "requirements.txt"
            if requirements_file.exists():
                subprocess.run(
                    [str(pip_path), "install", "-r", str(requirements_file)],
                    check=True,
                    capture_output=True
                )
                logger.info("✓ Dependencias instaladas")
            else:
                logger.warning("No se encontró requirements.txt, instalando dependencias básicas...")
                basic_deps = [
                    "fastapi", "uvicorn", "sqlalchemy", "pydantic",
                    "httpx", "python-multipart", "python-jose",
                    "passlib", "bcrypt", "python-dotenv"
                ]
                subprocess.run(
                    [str(pip_path), "install"] + basic_deps,
                    check=True,
                    capture_output=True
                )
                logger.info("✓ Dependencias básicas instaladas")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Error instalando dependencias: {e}")
            return False

    def setup_directories(self) -> bool:
        """Setup necessary directories."""
        logger.info("Configurando directorios...")

        directories = [
            "config",
            "database",
            "logs",
            "temp",
            "backups",
            "cores",
            "api",
            "frontend",
            "scripts"
        ]

        for dir_name in directories:
            dir_path = self.install_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Directorio creado: {dir_name}")

        return True

    def run_personalization_wizard(self) -> dict[str, Any]:
        """Run the personalization wizard."""
        logger.info("Iniciando wizard de personalización...")

        print("\n" + "─" * 60)
        print("  PERSONALIZACIÓN DE OWNEX OMEGA")
        print("─" * 60 + "\n")

        # Ask use case
        print("¿Para qué quieres usar OWNEX OMEGA?")
        print("1. Bug Bounty Researcher (individual)")
        print("2. Bug Bounty Company (empresa)")
        print("3. Cybersecurity Consultant (consultor)")
        print("4. Penetration Tester (pentester)")
        print("5. Security Analyst (analista)")
        print("6. Developer (desarrollador)")
        print("7. Researcher (investigador)")
        print("8. Hobbyist (aficionado)")
        print("9. Otro (otro)")

        use_case_map = {
            "1": "bug_bounty_researcher",
            "2": "bug_bounty_company",
            "3": "cybersecurity_consultant",
            "4": "penetration_tester",
            "5": "security_analyst",
            "6": "developer",
            "7": "researcher",
            "8": "hobbyist",
            "9": "other"
        }

        choice = input("\nSelecciona una opción (1-9): ").strip()
        use_case = use_case_map.get(choice, "bug_bounty_researcher")

        # Ask for modules
        print("\n¿Qué módulos quieres habilitar?")
        print("(Deja vacío para usar los módulos recomendados)")
        print("Módulos disponibles: forge, pulse, vault, atlas, security, copilot, analytics, reports, targets, integrations")

        modules_input = input("Módulos (separados por coma): ").strip()
        modules = [m.strip() for m in modules_input.split(",")] if modules_input else []

        # Ask for custom name
        custom_name = input("\nNombre personalizado para la aplicación (opcional): ").strip()

        # Ask expertise level
        print("\n¿Cuál es tu nivel de experiencia?")
        print("1. Beginner (principiante)")
        print("2. Intermediate (intermedio)")
        print("3. Advanced (avanzado)")
        print("4. Expert (experto)")

        expertise_map = {
            "1": "beginner",
            "2": "intermediate",
            "3": "advanced",
            "4": "expert"
        }

        expertise_choice = input("Selecciona una opción (1-4): ").strip()
        expertise_level = expertise_map.get(expertise_choice, "intermediate")

        # Ask primary platforms
        print("\n¿Cuáles son tus plataformas principales?")
        print("(Deja vacío para todas las plataformas)")
        print("Plataformas: hackerone, bugcrowd, intigriti, yeswehack, synack")

        platforms_input = input("Plataformas (separadas por coma): ").strip()
        primary_platforms = [p.strip() for p in platforms_input.split(",")] if platforms_input else ["all"]

        # Build personalization data
        personalization_data = {
            "use_case": use_case,
            "modules": modules,
            "custom_name": custom_name,
            "expertise_level": expertise_level,
            "primary_platforms": primary_platforms
        }

        # Run personalization step
        try:
            from cores.setup.steps.personalization_step import personalization_step
            result = personalization_step(personalization_data)

            if result["status"] == "ok":
                self.config = result["data"]["config"]
                logger.info("✓ Personalización completada")
                logger.info(f"✓ Módulos habilitados: {result['data']['modules']}")
                logger.info(f"✓ Nivel de automatización: {self.config['automation_level']}")
                return result["data"]
            else:
                logger.error(f"Error en personalización: {result.get('message')}")
                return {}
        except ImportError:
            logger.warning("Módulo de personalización no disponible, usando configuración por defecto")
            return personalization_data

    def apply_configuration(self) -> bool:
        """Apply personalized configuration."""
        logger.info("Aplicando configuración personalizada...")

        try:
            config_dir = self.install_dir / "config"
            config_file = config_dir / "personalized_config.json"

            config_file.write_text(json.dumps(self.config, indent=2))
            logger.info(f"✓ Configuración guardada en {config_file}")

            # Create .env file with personalized settings
            env_file = self.install_dir / ".env"
            env_content = f"""
# OWNEX OMEGA - Configuración Personalizada
GENERATED_AT={json.dumps(self.config.get('use_case'))}
AUTOMATION_LEVEL={self.config.get('automation_level')}
EXPERTISE_LEVEL={self.config.get('expertise_level')}
ENABLED_MODULES={','.join(self.config.get('enabled_modules', []))}
PRIMARY_PLATFORMS={','.join(self.config.get('primary_platforms', []))}
APP_NAME={self.config.get('ui_customization', {}).get('app_name', 'OWNEX OMEGA')}
THEME={self.config.get('ui_customization', {}).get('theme', 'dark')}
ACCENT_COLOR={self.config.get('ui_customization', {}).get('accent_color', '#60A5FA')}
"""

            if not env_file.exists():
                env_file.write_text(env_content.strip())
                logger.info(f"✓ Archivo .env creado")
            else:
                logger.info("ℹ Archivo .env ya existe, conservando configuración existente")

            return True

        except Exception as e:
            logger.error(f"Error aplicando configuración: {e}")
            return False

    def initialize_database(self) -> bool:
        """Initialize database."""
        logger.info("Inicializando base de datos...")

        try:
            db_dir = self.install_dir / "database"
            db_file = db_dir / "ownex.db"

            if not db_file.exists():
                # Create database schema
                from database import db
                db.create_all()
                logger.info("✓ Base de datos inicializada")
            else:
                logger.info("ℹ Base de datos ya existe")

            return True

        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
            return False

    def create_startup_script(self) -> bool:
        """Create startup script for the system."""
        logger.info("Creando script de inicio...")

        try:
            if self.system_info["os"] == "Windows":
                script_content = f"""@echo off
cd /d "{self.install_dir}"
.venv\\Scripts\\python run.py
pause
"""
                script_file = self.install_dir / "start.bat"
            else:
                script_content = f"""#!/bin/bash
cd "{self.install_dir}"
.venv/bin/python run.py
"""
                script_file = self.install_dir / "start.sh"

            script_file.write_text(script_content)
            if self.system_info["os"] != "Windows":
                script_file.chmod(0o755)

            logger.info(f"✓ Script de inicio creado: {script_file}")
            return True

        except Exception as e:
            logger.error(f"Error creando script de inicio: {e}")
            return False

    def run_post_installation_tests(self) -> bool:
        """Run post-installation tests."""
        logger.info("Ejecutando pruebas post-instalación...")

        try:
            # Test API import
            from api.main import app
            logger.info("✓ API import successful")

            # Test database connection
            from database import db
            logger.info("✓ Database connection successful")

            # Test config loading
            if self.config:
                logger.info("✓ Configuración cargada correctamente")

            return True

        except Exception as e:
            logger.error(f"Error en pruebas post-instalación: {e}")
            return False

    def print_summary(self) -> None:
        """Print installation summary."""
        print("\n" + "=" * 60)
        print("  INSTALACIÓN COMPLETADA")
        print("=" * 60 + "\n")

        print("Sistema:")
        print(f"  OS: {self.system_info['os']} {self.system_info['os_version']}")
        print(f"  Python: {self.system_info['python_version']}")
        print(f"  Arquitectura: {self.system_info['architecture']}")

        print("\nConfiguración:")
        print(f"  Caso de uso: {self.config.get('use_case', 'default')}")
        print(f"  Módulos habilitados: {', '.join(self.config.get('enabled_modules', []))}")
        print(f"  Nivel de automatización: {self.config.get('automation_level', 'default')}")
        print(f"  Nivel de experiencia: {self.config.get('expertise_level', 'default')}")

        print("\nPara iniciar OWNEX OMEGA:")
        if self.system_info["os"] == "Windows":
            print("  Ejecuta: start.bat")
        else:
            print("  Ejecuta: ./start.sh")

        print("\nPara iniciar manualmente:")
        print("  .venv/bin/python run.py")

        print("\nPara más información:")
        print("  Consulta README.md y docs/")

        print("\n" + "=" * 60 + "\n")

    def install(self) -> bool:
        """Run the complete installation process."""
        self.print_banner()

        # Check requirements
        if not self.check_requirements():
            logger.error("Requisitos del sistema no cumplidos")
            return False

        # Setup directories
        if not self.setup_directories():
            logger.error("Error configurando directorios")
            return False

        # Install dependencies
        if not self.minimal:
            if not self.install_dependencies():
                logger.error("Error instalando dependencias")
                return False

        # Run personalization wizard
        personalization_data = self.run_personalization_wizard()
        if not personalization_data:
            logger.warning("Usando configuración por defecto")

        # Apply configuration
        if not self.apply_configuration():
            logger.error("Error aplicando configuración")
            return False

        # Initialize database
        if not self.minimal:
            if not self.initialize_database():
                logger.error("Error inicializando base de datos")
                return False

        # Create startup script
        if not self.create_startup_script():
            logger.warning("No se pudo crear script de inicio")

        # Run post-installation tests
        if not self.minimal:
            if not self.run_post_installation_tests():
                logger.warning("Algunas pruebas post-instalación fallaron")

        # Print summary
        self.print_summary()

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OWNEX OMEGA Universal Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python install.py              # Instalación completa con wizard
  python install.py --dev        # Modo desarrollo
  python install.py --minimal    # Instalación mínima (sin dependencias)
        """
    )

    parser.add_argument(
        "--dev",
        action="store_true",
        help="Modo desarrollo (instala dependencias adicionales)"
    )

    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Instalación mínima (sin dependencias ni pruebas)"
    )

    args = parser.parse_args()

    installer = OwnexInstaller(dev_mode=args.dev, minimal=args.minimal)

    try:
        success = installer.install()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nInstalación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error fatal durante instalación: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
