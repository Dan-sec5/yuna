#!/usr/bin/env python3
"""
Yuna - Agente IA Local
Punto de entrada principal

Uso:
  python app.py            # TUI textual (por defecto)
  python app.py menu       # Menú clásico (rich)
  python app.py chat       # Chat conversacional directo
  python app.py agent      # Agente autónomo directo
  python app.py aprender   # Analizar patrones y memoria
  python app.py migrate    # Migrar memoria.txt → SQLite
  python app.py logs       # Últimas 50 líneas del log
  python app.py test       # Ejecutar tests
"""
import sys
import os

sys.path.insert(0, os.path.expanduser("~/yuna"))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tui"

    if cmd == "tui":
        from interface.tui import main as tui_main
        tui_main()

    elif cmd == "menu":
        # Menú clásico rich (el de fix_yuna.sh)
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich import box

        console = Console()
        console.print("[bold green]\n  Y  U  N  A[/bold green] [dim]— agente local[/dim]\n")

        opciones = {
            "1": ("chat",     "Chat",       "Conversación con Yuna"),
            "2": ("agent",    "Agente",     "Herramientas, archivos y búsqueda"),
            "3": ("aprender", "Aprender",   "Analizar patrones y memoria"),
            "4": ("logs",     "Logs",       "Últimas 50 líneas del registro"),
            "5": ("tui",      "TUI",        "Interfaz textual avanzada"),
            "0": ("salir",    "Salir",      "Detener modelo y cerrar"),
        }

        while True:
            console.print()
            for k, (_, t, d) in opciones.items():
                console.print(f"  [bold green]{k}[/bold green]  {t:<12} [dim]{d}[/dim]")
            console.print()
            try:
                eleccion = input("yuna> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if eleccion not in opciones:
                console.print("[red]Opción inválida[/red]")
                continue

            accion = opciones[eleccion][0]
            if accion == "salir":
                import subprocess
                subprocess.run(["ollama", "stop", CONFIG.get('models', {}).get('chat', 'maid:latest')], capture_output=True)
                console.print("[green]Hasta luego, Luis.[/green]")
                break
            elif accion == "logs":
                log_file = os.path.expanduser("~/yuna/logs/yuna.log")
                if os.path.exists(log_file):
                    import subprocess
                    subprocess.run(["tail", "-50", log_file])
                else:
                    console.print("[yellow]No hay logs aún[/yellow]")
            elif accion == "tui":
                from interface.tui import main as tui_main
                tui_main()
            elif accion == "aprender":
                from tools.aprender import main as aprender_main
                aprender_main()
                console.print("[dim](Enter para volver)[/dim]")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    break
            else:
                console.print()
                if accion == "chat":
                    from interface.cli import main as chat_main
                    chat_main()
                else:
                    from interface.agent_cli import main as agent_main
                    agent_main()
                console.print("[dim](volviendo al menú)[/dim]\n")

    elif cmd == "chat":
        from interface.cli import main as chat_main
        chat_main()

    elif cmd == "agent":
        from interface.agent_cli import main as agent_main
        agent_main()

    elif cmd == "aprender":
        from tools.aprender import main as aprender_main
        aprender_main()

    elif cmd == "migrate":
        from memory.manager import migrar_memoria_txt
        migrar_memoria_txt()
        print("✓ Migración completa")

    elif cmd == "logs":
        import subprocess
        log_file = os.path.expanduser("~/yuna/logs/yuna.log")
        if os.path.exists(log_file):
            subprocess.run(["tail", "-50", log_file])
        else:
            print("No hay logs aún. Usa el agente primero.")

    elif cmd == "test":
        import pytest
        pytest.main(["-v", "tests/"])

    else:
        print(f"Comando desconocido: {cmd}")


if __name__ == "__main__":
    main()
