#!/usr/bin/env python3
"""
CATEYE Copilot CLI — terminal-based interactive assistant.

Usage:
    python scripts/copilot.py              # interactive mode
    python scripts/copilot.py "pregunta"   # single query mode

Commands:
    /quit       Salir
    /help       Mostrar ayuda
    /insights   Mostrar insights del sistema
    /recommend  Mostrar recomendaciones
    /status     Estado del sistema
    /context    Contexto completo
    /clear      Limpiar pantalla
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

logging.disable(logging.CRITICAL)
os.environ["CATEYE_DESKTOP"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db  # noqa: E402

db.init_db()

from cores.ai.assistant import get_assistant  # noqa: E402
from cores.ai.context_builder import build_full_context  # noqa: E402

VERDE = "\033[92m"
CYAN = "\033[96m"
AMARILLO = "\033[93m"
MAGENTA = "\033[95m"
ROJO = "\033[91m"
NEGRITA = "\033[1m"
RESET = "\033[0m"
GRIS = "\033[90m"


def print_banner():
    print(f"\n  {NEGRITA}{CYAN}╔═══════════════════════════╗{RESET}")
    print(f"  {NEGRITA}{CYAN}║     CATEYE  COPILOT      ║{RESET}")
    print(f"  {NEGRITA}{CYAN}║  Bug Bounty Intelligence  ║{RESET}")
    print(f"  {NEGRITA}{CYAN}╚═══════════════════════════╝{RESET}")
    print(f"  {GRIS}Escribí una pregunta o /help para comandos{RESET}")
    print()


def print_suggestions(suggestions: list[str]):
    if not suggestions:
        return
    print(f"\n  {GRIS}Sugerencias:{RESET}")
    for i, s in enumerate(suggestions, 1):
        print(f"  {GRIS}{i}. {s}{RESET}")
    print()


def get_user_choice(suggestions: list[str]) -> str | None:
    if not suggestions:
        return None
    try:
        choice = input(f"  {AMARILLO}Seleccioná opción (1-{len(suggestions)}) o Enter para escribir: {RESET}").strip()
        if not choice:
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(suggestions):
            return suggestions[idx]
    except (ValueError, IndexError):
        pass
    return None


def handle_command(cmd: str) -> bool:
    cmd = cmd.lower().strip()

    if cmd in ("/quit", "/exit", "/q"):
        print(f"  {VERDE}¡Hasta luego!{RESET}")
        return False

    if cmd in ("/help", "/h"):
        print(f"""
  {NEGRITA}Comandos disponibles:{RESET}
    {CYAN}/quit{RESET}        Salir del copilot
    {CYAN}/help{RESET}        Mostrar esta ayuda
    {CYAN}/insights{RESET}    Mostrar insights automáticos del sistema
    {CYAN}/recommend{RESET}   Mostrar recomendaciones prioritarias
    {CYAN}/status{RESET}      Estado del sistema y proveedor AI
    {CYAN}/context{RESET}     Contexto completo del sistema
    {CYAN}/clear{RESET}       Limpiar pantalla

  {NEGRITA}O escribí cualquier pregunta en lenguaje natural.{RESET}
  {GRIS}Ejemplos:{RESET}
    - "¿Qué target tiene mejor ROI?"
    - "¿Qué cambió hoy?"
    - "¿Qué oportunidades puedo completar en dos horas?"
    - "¿Cómo va el pipeline?"
""")
        return True

    if cmd == "/insights":
        assistant = get_assistant()
        insights = assistant.get_insights()
        if not insights:
            print(f"  {AMARILLO}No hay insights disponibles todavía.{RESET}")
            return True
        print(f"  {NEGRITA}Insights del sistema ({len(insights)}):{RESET}")
        for ins in insights[:10]:
            level = ins.get("level", "info")
            color = {"critical": ROJO, "high": AMARILLO, "medium": CYAN, "info": VERDE}.get(level, GRIS)
            print(f"  {color}[{level.upper()}]{RESET} {ins.get('title', '')}")
            if ins.get("description"):
                print(f"    {GRIS}{ins['description']}{RESET}")
            if ins.get("action"):
                print(f"    {AMARILLO}→ {ins['action']}{RESET}")
        return True

    if cmd in ("/recommend", "/recommendations"):
        assistant = get_assistant()
        recs = assistant.get_recommendations()
        if not recs:
            print(f"  {AMARILLO}No hay recomendaciones disponibles todavía.{RESET}")
            return True
        print(f"  {NEGRITA}Recomendaciones ({len(recs)}):{RESET}")
        for rec in recs[:5]:
            print(f"  {MAGENTA}{rec.get('target', rec.get('name', ''))}{RESET}")
            if rec.get("reason"):
                print(f"    {GRIS}{rec['reason']}{RESET}")
            score = rec.get("score", rec.get("priority", rec.get("roi_score", 0)))
            if score:
                print(f"    {AMARILLO}Score: {score}{RESET}")
        return True

    if cmd in ("/status", "/stats"):
        assistant = get_assistant()
        status = assistant.get_status()
        provider = status.get("provider", "N/A")
        available = status.get("available", False)
        ctx = build_full_context()
        t = ctx.get("targets", {})
        e = ctx.get("endpoints", {})
        f = ctx.get("findings", {})
        p = ctx.get("pipeline", {})
        print(f"""
  {NEGRITA}Estado del sistema:{RESET}
  {GRIS}Proveedor AI:{RESET}   {provider} {"✅" if available else "❌"}
  {GRIS}Memoria:{RESET}        {status.get("memory_exchanges", 0)} intercambios
  {GRIS}Targets:{RESET}        {t.get("total", 0)}
  {GRIS}Endpoints:{RESET}      {e.get("total", 0)} ({e.get("high_signal", 0)} high signal)
  {GRIS}Findings:{RESET}       {f.get("total", 0)}
  {GRIS}Pipeline:{RESET}       {p.get("detected", 0)}D → {p.get("validated", 0)}V → {p.get("confirmed", 0)}C
""")
        return True

    if cmd == "/context":
        ctx = build_full_context()
        print(f"  {NEGRITA}Contexto completo del sistema:{RESET}")
        for key, val in ctx.items():
            if isinstance(val, dict):
                print(f"  {CYAN}{key}:{RESET}")
                for k, v in list(val.items())[:5]:
                    print(f"    {GRIS}{k}:{RESET} {v}")
                if len(val) > 5:
                    print(f"    {GRIS}... y {len(val) - 5} más{RESET}")
            else:
                print(f"  {CYAN}{key}:{RESET} {val}")
        return True

    if cmd == "/clear":
        os.system("clear" if os.name == "posix" else "cls")
        print_banner()
        return True

    print(f"  {ROJO}Comando desconocido: {cmd}{RESET}")
    print(f"  {AMARILLO}Usá /help para ver comandos disponibles.{RESET}")
    return True


def chat_once(message: str) -> dict[str, Any]:
    assistant = get_assistant()
    result = assistant.chat(message)
    return result


def show_answer(result: dict[str, Any]):
    answer = result.get("answer", "")
    source = result.get("source", "local/rules")
    suggestions = result.get("suggestions", [])

    source_color = VERDE if source != "local/rules" else GRIS
    print(f"\n  {source_color}[{source}]{RESET}")
    print(f"  {answer}")
    print()
    if suggestions:
        print_suggestions(suggestions)


def interactive_loop():
    print_banner()

    initial_suggestions = [
        "¿Qué target tiene mejor ROI?",
        "¿Qué cambió hoy?",
        "¿Qué oportunidades puedo completar en dos horas?",
        "¿Cómo va el pipeline?",
    ]
    print_suggestions(initial_suggestions)
    choice = get_user_choice(initial_suggestions)
    message = choice or ""

    while True:
        if not message:
            try:
                message = input(f"\n  {NEGRITA}❯{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

        if not message:
            continue

        if message.startswith("/"):
            if not handle_command(message):
                break
            message = ""
            continue

        result = chat_once(message)
        show_answer(result)

        suggestions = result.get("suggestions", [])
        choice = get_user_choice(suggestions)
        message = choice or ""


def single_query(query: str):
    result = chat_once(query)
    print(f"\n{result.get('answer', '')}")
    print(f"\n{GRIS}[{result.get('source', 'local/rules')}]{RESET}")
    suggestions = result.get("suggestions", [])
    if suggestions:
        print()
        print_suggestions(suggestions)


def main():
    if len(sys.argv) > 1:
        single_query(" ".join(sys.argv[1:]))
    else:
        interactive_loop()


if __name__ == "__main__":
    main()
