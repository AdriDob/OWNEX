#!/usr/bin/env python3
"""Script para sincronizar cambios locales con GitHub automáticamente.

Este script:
1. Agrega todos los archivos modificados y nuevos
2. Crea un commit con un mensaje automático
3. Sube los cambios al repositorio origin/main
"""

import os
import subprocess
from datetime import datetime


def run_git(command_list):
    """Ejecuta un comando git y retorna el resultado."""
    result = subprocess.run(["git"] + command_list, capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
    return result


def sync():
    """Sincroniza cambios locales con GitHub."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando sincronización con GitHub...")

    # Step 1: Status check
    print("Verificando estado de cambios...")
    status = run_git(["status", "--porcelain"])
    if status.stdout.strip() == "":
        print("No hay cambios para sincronizar.")
        return

    print(f"Archivos modificados:\n{status.stdout.strip()}")

    # Step 2: Add all changes
    print("Agregando todos los archivos...")
    add_result = run_git(["add", "."])
    if add_result.returncode != 0:
        print(f"Error al agregar archivos: {add_result.stderr}")
        return
    print("Archivos agregados correctamente.")

    # Step 3: Commit
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    commit_msg = f"sync_{timestamp}: actualización automática de cambios locales"
    print(f"Creando commit: {commit_msg}")
    commit_result = run_git(["commit", "-m", commit_msg])
    if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stderr:
        # Si el commit falla por mensaje vacío, intentamos con --no-verify
        if "empty" in commit_result.stderr.lower():
            print("Commit vacío, intentando con --no-verify...")
            commit_result = run_git(["commit", "-m", commit_msg, "--no-verify"])
        else:
            print(f"Error al hacer commit: {commit_result.stderr}")
            return
    elif commit_result.returncode == 0:
        print("Commit creado.")

    # Step 4: Push to origin
    print("Subiendo cambios a GitHub (origin/main)...")
    push_result = run_git(["push", "origin", "main"])

    if push_result.returncode != 0:
        error_msg = push_result.stderr.strip()
        print(f"Error al push: {error_msg}")

        # Intenta hacer pull rebase primero
        print("Intentando pull rebase para resolver conflictos...")
        pull_result = run_git(["pull", "--rebase", "origin", "main"])
        if pull_result.returncode != 0:
            print(f"Error en rebase: {pull_result.stderr}")
            # Intentar merge simple
            pull_result = run_git(["pull", "origin", "main"])
            if pull_result.returncode != 0:
                print(f"Error en pull también: {pull_result.stderr}")
                return
        print("Pull completado exitosamente.")
        # Reintentar push
        push_result = run_git(["push", "origin", "main"])

    if push_result.returncode == 0:
        print("¡Éxito! Cambios subidos a GitHub.")
        print(push_result.stdout)
    else:
        print("La sincronización terminó con advertencias.")


if __name__ == "__main__":
    sync()
