#!/usr/bin/env python3
"""OWNEX TUI — Terminal User Interface

A rich-based TUI for OWENEX that provides keyboard-navigable access
to all system functionality without requiring technical knowledge.

Principio V14: Any person should be able to use OWNEX without
knowing its architecture, technologies, or internal concepts.
"""

from __future__ import annotations

import sys
from enum import Enum

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


class Screen(Enum):
    """Available TUI screens."""

    MAIN = "main"
    OPPORTUNITIES = "opportunities"
    FINANCE = "finance"
    CONNECTIONS = "connections"
    AGENTS = "agents"
    SETTINGS = "settings"
    HELP = "help"


class Status(Enum):
    """Status states for display."""

    HEALTHY = "✅ Healthy"
    DEGRADED = "⚠️ Degraded"
    ERROR = "❌ Error"
    OFFLINE = "📡 Offline"


def main():
    """Main entry point for OWENEX TUI."""
    try:
        run_tui()
    except KeyboardInterrupt:
        console.print("\n[dim]Saliendo de OWENEX...[/dim]")
        sys.exit(0)


def run_tui():
    """Run the TUI main loop."""
    current_screen = Screen.MAIN
    running = True

    while running:
        if current_screen == Screen.MAIN:
            running, current_screen = show_main_screen()
        elif current_screen == Screen.OPPORTUNITIES:
            running, current_screen = show_opportunities_screen()
        elif current_screen == Screen.FINANCE:
            running, current_screen = show_finance_screen()
        elif current_screen == Screen.CONNECTIONS:
            running, current_screen = show_connections_screen()
        elif current_screen == Screen.AGENTS:
            running, current_screen = show_agents_screen()
        elif current_screen == Screen.SETTINGS:
            running, current_screen = show_settings_screen()
        elif current_screen == Screen.HELP:
            running, current_screen = show_help_screen()


def show_main_screen() -> tuple[bool, Screen]:
    """Show the main OWENEX status screen."""
    # Fetch real data from API
    try:
        import httpx

        health = httpx.get("http://localhost:8000/api/health", timeout=2.0)
        system = httpx.get("http://localhost:8000/api/system/health", timeout=2.0)

        health_data = health.json() if health.status_code == 200 else {}
        system_data = system.json() if system.status_code == 200 else {}
    except Exception:
        health_data = {}
        system_data = {}

    # Build status table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan", no_wrap=True)
    table.add_column("Valor", style="green")

    # System health
    status_val = health_data.get("status", "unknown")
    table.add_row("Estado del sistema", status_val.upper())

    # Targets
    targets = system_data.get("targets", 0)
    table.add_row("Targets registrados", str(targets))

    # Endpoints
    endpoints = system_data.get("endpoints", 0)
    table.add_row("Endpoints monitorizados", str(endpoints))

    # Findings
    findings = system_data.get("findings", 0)
    table.add_row("Findings detectados", str(findings))

    # Verdicts
    verdicts = system_data.get("verdicts", 0)
    table.add_row("Verdictos confirmados", str(verdicts))

    # Active scans
    active_scans = system_data.get("active_scans", 0)
    table.add_row("Scans activos", str(active_scans))

    # Autonomy
    autonomy = system_data.get("autonomy_score", 0)
    table.add_row("Score de autonomía", f"{autonomy:.1f}")

    # Last sync
    last_sync = system_data.get("last_health_check", "n/a")
    table.add_row("Última sincronización", str(last_sync))

    panel = Panel(
        table,
        title="[bold]OWNEX Personal Work & Capital System[/bold]",
        border_style="blue",
        subtitle="[dim]Use ↑/downarrow arrows, Enter, Escape[/dim]",
    )

    rprint(panel)

    # Show hint
    rprint("[dim]Controles:[/dim] ")
    rprint("  ↑/downarrow: Navegar")
    rprint("  Enter: Seleccionar")
    rprint("  Escape: Retroceder")
    rprint("  F1: Ayuda")
    rprint("  q: Salir")

    # Wait for user input
    choice = Prompt.ask(
        "[bold green]Seleccionar opción[/bold green]",
        choices=["1", "2", "3", "4", "5", "6", "7", "8", "q"],
        default="1",
    )

    destinations = {
        "q": (False, Screen.MAIN),
        "1": (True, Screen.OPPORTUNITIES),
        "2": (True, Screen.FINANCE),
        "3": (True, Screen.CONNECTIONS),
        "4": (True, Screen.AGENTS),
        "5": (True, Screen.SETTINGS),
        "6": (True, Screen.HELP),
    }
    return destinations.get(choice, (True, Screen.MAIN))


def show_opportunities_screen() -> tuple[bool, Screen]:
    """Show opportunities/search screen."""
    rprint("[bold]Oportunidades de Bug Bounty[/bold]")

    try:
        import httpx

        resp = httpx.get(
            "http://localhost:8000/api/opportunities/remote-jobs/search?limit=10",
            timeout=3.0,
        )
        data = resp.json() if resp.status_code == 200 else []

        table = Table(show_header=True, header_style="bold green")
        table.add_column("ID", style="cyan")
        table.add_column("Título", style="white")
        table.add_column("Fuente", style="magenta")
        table.add_column("Pago estimado", style="green")
        table.add_column("Argentina", style="yellow")

        if isinstance(data, list) and data:
            for opp in data[:10]:
                argentina = "✓" if opp.get("argentina_ok", False) else ""
                table.add_row(
                    opp.get("id", "n/a"),
                    opp.get("title", "n/a")[:50],
                    opp.get("platform", "n/a")[:20],
                    f"${opp.get('estimated_payout', 0):,.0f}" if opp.get("estimated_payout") else "N/A",
                    argentina,
                )
        else:
            table.add_row("No hay oportunidades", "", "", "", "")

        panel = Panel(table, border_style="green")
        rprint(panel)

    except Exception as e:
        rprint(f"[red]Error cargando oportunidades: {e}[/red]")

    rprint("[dim]Presione Enter para volver al menú principal[/dim]")
    Prompt.ask("", default="")

    return True, Screen.MAIN


def show_finance_screen() -> tuple[bool, Screen]:
    """Show finance/earnings screen."""
    rprint("[bold]Finanzas OWENEX[/bold]")

    try:
        import httpx

        resp = httpx.get(
            "http://localhost:8000/api/financial/hub/status",
            timeout=3.0,
        )
        data = resp.json() if resp.status_code == 200 else {}

        table = Table(show_header=True, header_style="bold green")
        table.add_column("Métrica", style="cyan", no_wrap=True)
        table.add_column("Valor", style="green")

        table.add_row("Ingresos totales", f"${data.get('total_earnings', 0):,.2f}")
        table.add_row("Pagos pendientes", f"${data.get('pending_payouts', 0):,.2f}")
        table.add_row("Comisiones totales", f"${data.get('total_fees', 0):,.2f}")
        table.add_row("Cuentas sincronizadas", str(data.get("linked_accounts", 0)))
        table.add_row("Próximo pago estimado", f"${data.get('next_payout', 0):,.2f}")

        panel = Panel(table, border_style="green")
        rprint(panel)

    except Exception as e:
        rprint(f"[red]Error cargando finanzas: {e}[/red]")

    rprint("[dim]Presione Enter para volver al menú principal[/dim]")
    Prompt.ask("", default="")

    return True, Screen.MAIN


def show_connections_screen() -> tuple[bool, Screen]:
    """Show connections screen."""
    rprint("[bold]Conexiones OWENEX[/bold]")

    try:
        import httpx

        resp = httpx.get(
            "http://localhost:8000/api/auth/list-devices",
            timeout=3.0,
        )
        data = resp.json() if resp.status_code == 200 else []

        table = Table(show_header=True, header_style="bold green")
        table.add_column("Dispositivo", style="cyan", no_wrap=True)
        table.add_column("Último visto", style="magenta")
        table.add_column("Estado", style="green")

        if isinstance(data, list):
            for device in data:
                last_seen = device.get("last_seen", "n/a")
                status = "✅ Active" if device.get("active", False) else "🔌 Inactive"
                table.add_row(
                    device.get("device_id", "n/a"),
                    str(last_seen) if last_seen != "n/a" else "n/a",
                    status,
                )
        else:
            table.add_row("No hay conexiones registradas", "", "")

        panel = Panel(table, border_style="green")
        rprint(panel)

    except Exception as e:
        rprint(f"[red]Error cargando conexiones: {e}[/red]")

    rprint("[dim]Presione Enter para volver al menú principal[/dim]")
    Prompt.ask("", default="")

    return True, Screen.MAIN


def show_agents_screen() -> tuple[bool, Screen]:
    """Show agents screen."""
    rprint("[bold]Agentes OWENEX[/bold]")

    try:
        import httpx

        resp = httpx.get(
            "http://localhost:8000/api/intelligence/agents",
            timeout=3.0,
        )
        data = resp.json() if resp.status_code == 200 else []

        table = Table(show_header=True, header_style="bold green")
        table.add_column("Agente", style="cyan", no_wrap=True)
        table.add_column("Estado", style="magenta")
        table.add_column("Tareas", style="green")

        if isinstance(data, list):
            for agent in data:
                table.add_row(
                    agent.get("name", "n/a"),
                    agent.get("status", "unknown")[:20],
                    str(agent.get("tasks", 0)),
                )
        else:
            table.add_row("No hay agentes registrados", "", "")

        panel = Panel(table, border_style="green")
        rprint(panel)

    except Exception as e:
        rprint(f"[red]Error cargando agentes: {e}[/red]")

    rprint("[dim]Presione Enter para volver al menú principal[/dim]")
    Prompt.ask("", default="")

    return True, Screen.MAIN


def show_settings_screen() -> tuple[bool, Screen]:
    """Show settings screen."""
    rprint("[bold]Configuración OWENEX[/bold]")

    if Confirm.ask("¿Deseas cerrar sesión actual?"):
        try:
            import httpx

            httpx.post("http://localhost:8000/api/auth/logout", timeout=3.0)
            rprint("[green]Sesión cerrada exitosamente[/green]")
        except Exception as e:
            rprint(f"[red]Error cerrando sesión: {e}[/red]")

    if Confirm.ask("¿Deseas desconectar todos los dispositivos?"):
        try:
            import httpx

            httpx.post(
                "http://localhost:8000/api/auth/revoke-all",
                timeout=3.0,
            )
            rprint("[green]Todos los dispositivos desconectados[/green]")
        except Exception as e:
            rprint(f"[red]Error: {e}[/red]")

    rprint("[dim]Presione Enter para volver al menú principal[/dim]")
    Prompt.ask("", default="")

    return True, Screen.MAIN


def show_help_screen() -> tuple[bool, Screen]:
    """Show help/controls screen."""
    rprint("[bold]Ayuda — OWENEX TUI[/bold]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Acción", style="cyan", no_wrap=True)
    table.add_column("Tecla", style="green")
    table.add_column("Descripción", style="white")

    table.add_row("Navegar hacia arriba", "↑", "Mover selección arriba")
    table.add_row("Navegar hacia abajo", "↓", "Mover selección abajo")
    table.add_row("Seleccionar/Entrar", "Enter", "Ejecutar acción o entrar en submenú")
    table.add_row("Retrocedir", "Escape", "Volver al menú anterior")
    table.add_row("Salir de la aplicación", "q", "Cerrar OWENEX TUI")
    table.add_row("Ayuda contextual", "F1", "Mostrar esta pantalla")
    table.add_row("Buscar", "/", "Buscar en la pantalla actual")
    table.add_row("Actualizar datos", "F5", "Refrescar información desde API")

    panel = Panel(table, border_style="magenta")
    rprint(panel)

    rprint("[dim]Presione Enter para volver al menú[/dim]")
    Prompt.ask("", default="")

    return True, Screen.MAIN


if __name__ == "__main__":
    main()
