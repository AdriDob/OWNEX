"""Setup Wizard — configuración inicial interactiva de Rastro.

Guía al usuario paso a paso para configurar:
1. API keys de plataformas de bug bounty
2. API keys de OpenAI/Anthropic (o usar Ollama local)
3. Targets iniciales de alto pago
4. Capital inicial para inversiones
5. Auto-submit settings

Uso:
    python run.py --setup
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("orion.setup_wizard")


# ── Helpers ───────────────────────────────────────────────────────


def _input(prompt: str, default: str = "") -> str:
    """Get user input with optional default."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    value = input(prompt).strip()
    return value or default


def _input_bool(prompt: str, default: bool = True) -> bool:
    """Get boolean input."""
    default_str = "Y/n" if default else "y/N"
    value = _input(f"{prompt} ({default_str})", "y" if default else "n")
    return value.lower() in ("y", "yes", "s", "si", "1", "true")


def _input_float(prompt: str, default: float = 0.0) -> float:
    """Get float input."""
    value = _input(prompt, str(default))
    try:
        return float(value)
    except ValueError:
        return default


def _section(title: str) -> None:
    """Print section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def _save_env(key: str, value: str) -> None:
    """Save a key-value pair to opportunity.env."""
    env_path = Path.home() / ".config" / "ownex" / "opportunity.env"
    env_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    # Replace existing key or append
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n")
    os.environ[key] = value


# ── Steps ─────────────────────────────────────────────────────────


def step_welcome() -> None:
    """Welcome message."""
    _section("RASTRO Setup Wizard")
    print("Bienvenido a Rastro — tu sistema autónomo de bug bounty.")
    print("Este wizard te configura en 5 minutos.")
    print("Presiona Ctrl+C en cualquier momento para cancelar.\n")


def step_bug_bounty_keys() -> dict[str, str]:
    """Configure bug bounty platform API keys."""
    _section("Step 1: Bug Bounty Platforms")
    print("Configura las APIs de las plataformas de bug bounty.")
    print("Rastro puede auto-subir reportes a estas plataformas.\n")

    keys = {}
    platforms = [
        ("HACKERONE_API_KEY", "HackerOne", "https://docs.hackerone.com"),
        ("BUGCROWD_API_KEY", "Bugcrowd", "https://docs.bugcrowd.com"),
        ("INTIGRITI_API_KEY", "Intigriti", "https://docs.intigriti.com"),
        ("IMMUNEFI_API_KEY", "Immunefi", "https://immunefi.com"),
        ("SYNACK_API_KEY", "Synack", "https://www.synack.com"),
        ("YESWEHACK_API_KEY", "YesWeHack", "https://www.yeswehack.com"),
    ]

    for env_key, name, docs in platforms:
        if _input_bool(f"  Configurar {name}?", default=False):
            key = _input(f"    API Key de {name}")
            if key:
                _save_env(env_key, key)
                keys[env_key] = key
                print(f"    ✅ {name} configurado")
        else:
            print(f"    ⏭️  {name} omitido")

    return keys


def step_ai_provider() -> dict[str, str]:
    """Configure AI provider for AI Worker."""
    _section("Step 2: AI Worker (Inteligencia Artificial)")
    print("Rastro usa IA para hacer tareas humanas automáticamente:")
    print("  - Evaluar respuestas de IA (Pulse)")
    print("  - Generar propuestas (Freelancer)")
    print("  - Escribir código (Forge)")
    print("  - Responder triage (Bug Bounty)")
    print()

    config = {}
    use_ai = _input_bool("¿Activar AI Worker?", default=True)
    if not use_ai:
        print("  ⏭️  AI Worker desactivado")
        return config

    print("\nSelecciona proveedor de IA:")
    print("  1. Ollama (local, gratis, necesita Ollama instalado)")
    print("  2. OpenAI (GPT-4o-mini, mejor calidad, ~$0.01/tarea)")
    print("  3. Anthropic (Claude, balance calidad/precio)")
    print("  4. Saltar (configurar después)")

    choice = _input("Elige (1-4)", "1")

    if choice == "1":
        _save_env("AI_WORKER_PROVIDER", "ollama")
        model = _input("Modelo Ollama", "llama3.2")
        _save_env("AI_WORKER_MODEL", model)
        ollama_url = _input("URL Ollama", "http://localhost:11434")
        _save_env("OLLAMA_BASE_URL", ollama_url)
        config["provider"] = "ollama"
        print(f"  ✅ Ollama configurado ({model})")

    elif choice == "2":
        _save_env("AI_WORKER_PROVIDER", "openai")
        model = _input("Modelo OpenAI", "gpt-4o-mini")
        _save_env("AI_WORKER_MODEL", model)
        key = _input("OpenAI API Key")
        if key:
            _save_env("OPENAI_API_KEY", key)
            config["provider"] = "openai"
            print(f"  ✅ OpenAI configurado ({model})")

    elif choice == "3":
        _save_env("AI_WORKER_PROVIDER", "anthropic")
        model = _input("Modelo Anthropic", "claude-sonnet-4-6")
        _save_env("AI_WORKER_MODEL", model)
        key = _input("Anthropic API Key")
        if key:
            _save_env("ANTHROPIC_API_KEY", key)
            config["provider"] = "anthropic"
            print(f"  ✅ Anthropic configurado ({model})")

    else:
        print("  ⏭️  AI Worker pendiente de configurar")

    return config


def step_targets() -> list[dict[str, str]]:
    """Add initial bug bounty targets."""
    _section("Step 3: Targets Iniciales")
    print("Agrega programas de bug bounty de alto pago.")
    print("Rastro los escanea automáticamente 24/7.\n")

    targets = []
    presets = [
        ("hackerone_tesla", "tesla.com", "HackerOne"),
        ("hackerone_cloudflare", "cloudflare.com", "HackerOne"),
        ("hackerone_paypal", "paypal.com", "HackerOne"),
        ("bugcrowd_okta", "okta.com", "Bugcrowd"),
        ("bugcrowd_twitter", "twitter.com", "Bugcrowd"),
        ("immunefi_solana", "solana.com", "Immunefi"),
        ("immunefi_ethereum", "ethereum.org", "Immunefi"),
        ("intigriti_intigriti", "intigriti.com", "Intigriti"),
    ]

    print("Targets recomendados (elige cuáles agregar):")
    for i, (name, domain, platform) in enumerate(presets, 1):
        print(f"  {i}. {name} ({domain}) [{platform}]")
    print(f"  {len(presets) + 1}. Agregar targets personalizados")
    print(f"  {len(presets) + 2}. Saltar (agregar después)")

    choice = _input(f"Elige (1-{len(presets) + 2})", str(len(presets) + 2))

    try:
        choice_num = int(choice)
        if choice_num <= len(presets):
            for i in range(choice_num):
                name, domain, platform = presets[i]
                targets.append({"name": name, "domain": domain, "platform": platform})
        elif choice_num == len(presets) + 1:
            # Custom targets
            while True:
                name = _input("Nombre del target (o Enter para terminar)")
                if not name:
                    break
                domain = _input("Dominio")
                platform = _input("Plataforma (hackerone/bugcrowd/etc)")
                targets.append({"name": name, "domain": domain, "platform": platform})
    except ValueError:
        pass

    print(f"\n  ✅ {len(targets)} targets configurados")
    return targets


def step_auto_submit() -> dict[str, bool]:
    """Configure auto-submit settings."""
    _section("Step 4: Auto-Submit")
    print("Rastro puede auto-subir reportes de alta calidad sin tu intervención.")
    print("Solo se suben reportes con score > 85 (élite).\n")

    settings = {}
    enable = _input_bool("¿Activar auto-submit para findings élite?", default=True)
    settings["auto_submit"] = enable

    if enable:
        _save_env("CATEYE_AUTO_SUBMIT", "true")
        print("  ✅ Auto-submit activado (solo élitaire, score > 85)")
    else:
        _save_env("CATEYE_AUTO_SUBMIT", "false")
        print("  ⏭️  Auto-submit desactivado (aprobación manual)")

    return settings


def step_notifications() -> dict[str, str]:
    """Configure notifications."""
    _section("Step 5: Notificaciones")
    print("Rastro te avisa solo cuando necesita tu intervención.")
    print("Configura cómo quieres recibir notificaciones.\n")

    config = {}

    # Discord
    if _input_bool("¿Configurar Discord webhook?", default=False):
        webhook = _input("Discord Webhook URL")
        if webhook:
            _save_env("CATEYE_DISCORD_WEBHOOK_URL", webhook)
            config["discord"] = webhook
            print("  ✅ Discord configurado")

    # WhatsApp
    if _input_bool("¿Configurar WhatsApp (via Twilio)?", default=False):
        sid = _input("Twilio Account SID")
        token = _input("Twilio Auth Token")
        from_num = _input("Twilio WhatsApp Number")
        to_num = _input("Tu WhatsApp Number")
        if sid and token and from_num and to_num:
            _save_env("CATEYE_TWILIO_ACCOUNT_SID", sid)
            _save_env("CATEYE_TWILIO_AUTH_TOKEN", token)
            _save_env("CATEYE_TWILIO_WHATSAPP_FROM", from_num)
            _save_env("CATEYE_NOTIFICATION_WHATSAPP_TO", to_num)
            config["whatsapp"] = to_num
            print("  ✅ WhatsApp configurado")

    if not config:
        print("  ⏭️  Sin notificaciones externas (solo in-app)")

    return config


def step_summary(
    bb_keys: dict[str, str],
    ai_config: dict[str, str],
    targets: list[dict[str, str]],
    auto_submit: dict[str, bool],
    notifications: dict[str, str],
) -> None:
    """Show summary and next steps."""
    _section("¡Configuración Completa!")
    print("Resumen de tu configuración:\n")

    print(f"  Plataformas BB: {len(bb_keys)} configuradas")
    for key in bb_keys:
        print(f"    ✅ {key}")

    print(f"\n  AI Worker: {ai_config.get('provider', 'no configurado')}")
    if ai_config.get("model"):
        print(f"    Modelo: {ai_config['model']}")

    print(f"\n  Targets: {len(targets)} programas")
    for t in targets:
        print(f"    • {t['name']} ({t['domain']})")

    print(f"\n  Auto-submit: {'activado' if auto_submit.get('auto_submit') else 'desactivado'}")
    print(f"  Notificaciones: {len(notifications)} canales")

    print("\n" + "=" * 60)
    print("  Próximos pasos:")
    print("=" * 60)
    print("""
  1. Ejecutar: python run.py --auto
  2. Abrir dashboard: http://localhost:8000
  3. Revisar Mission Control para verificar que todo corre
  4. Rastro trabaja 24/7 — vos solo revisás 5 min/día

  Para agregar más targets:
    python run.py --add-target <name> --domain <domain>

  Para ver logs:
    python run.py --logs
    """)


# ── Main ───────────────────────────────────────────────────────────


def run_setup_wizard() -> None:
    """Run the full setup wizard."""
    try:
        step_welcome()
        bb_keys = step_bug_bounty_keys()
        ai_config = step_ai_provider()
        targets = step_targets()
        auto_submit = step_auto_submit()
        notifications = step_notifications()
        step_summary(bb_keys, ai_config, targets, auto_submit, notifications)
    except KeyboardInterrupt:
        print("\n\nSetup cancelado. Puedes continuar después con: python run.py --setup")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error en setup: {e}")
        logger.exception("Setup wizard failed")
        sys.exit(1)


if __name__ == "__main__":
    run_setup_wizard()
