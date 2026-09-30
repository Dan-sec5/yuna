"""
interface/agent_cli.py

Agente autónomo de Yuna con herramientas (terminal).
La voz se centraliza en interface/voice.py — no duplicar hablar() aquí.
"""
import sys
import os

sys.path.insert(0, os.path.expanduser("~/yuna"))

from rich.console import Console

from core.agent import YunaAgent
from core.llm import preload_model
from memory.manager import init_db, add_episodic
from interface.voice import hablar

console = Console()

POSITIVO = ("👍", "bien", "util", "up")
NEGATIVO = ("👎", "mal", "inutil", "down")


def main():
    init_db()
    console.print("[dim]⏳ Precargando modelo en RAM...[/dim]")
    preload_model()
    console.print("[green]✅ Modelo listo.[/green]\n")

    agente = YunaAgent()
    saludo = "Hola Luis, modo agente activo. Puedo buscar archivos, analizar datos, consultar precios y más."
    console.print(f"[bold green]Yuna Agente[/bold green]\n")
    console.print(f"[green]Yuna[/green] → {saludo}\n")
    hablar(saludo)
    console.print("[dim](salir: terminar · reset: nueva sesión · 👍/👎: feedback)[/dim]\n")

    ultima_query = ""
    while True:
        try:
            entrada = input("Luis → ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not entrada:
            continue
        low = entrada.lower()

        if low in ("salir", "exit", "quit"):
            hablar("Hasta luego Luis.")
            console.print("[green]Yuna[/green] → Hasta luego Luis.")
            break
        if low == "reset":
            agente.reset()
            console.print("[green]✓ Sesión reiniciada[/green]\n")
            continue
        if entrada in POSITIVO:
            if ultima_query:
                agente.provide_feedback(ultima_query, "positive")
                console.print("[green]✓ Feedback positivo registrado[/green]\n")
            continue
        if entrada in NEGATIVO:
            if ultima_query:
                agente.provide_feedback(ultima_query, "negative")
                console.print("[yellow]✓ Feedback negativo registrado. Intentaré mejorar.[/yellow]\n")
            continue

        console.print("[dim]⏳ Procesando...[/dim]\n")
        ultima_query = entrada
        respuesta = agente.process(entrada)
        add_episodic("agente", f"Luis: {entrada[:100]} | Yuna: {respuesta[:100]}")
        console.print(f"[bold green]Yuna[/bold green] → {respuesta}\n")
        hablar(respuesta)


if __name__ == "__main__":
    main()
