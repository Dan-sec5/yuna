"""
interface/cli.py

Chat conversacional de Yuna (terminal).
La voz se centraliza en interface/voice.py — no duplicar hablar() aquí.
"""
import sys
import os

sys.path.insert(0, os.path.expanduser("~/yuna"))

from rich.console import Console

from core.llm import chat_simple, clean_response
from memory.manager import init_db, get_relevant_memory, add_episodic
from interface.voice import hablar

console = Console()


def main():
    init_db()
    memoria = get_relevant_memory("contexto general")

    mensajes = [{
        "role": "system",
        "content": f"""Eres Yuna, asistente personal de Luis. Eres inteligente, directa y hablas en español mexicano.
Cuando hables de archivos o datos, usa el modo agente (app.py agent).

MEMORIA:\n{memoria}"""
    }]

    saludo = "Hola Luis, soy Yuna. ¿En qué te ayudo?"
    console.print(f"\n[bold green]Yuna[/bold green] → {saludo}\n")
    hablar(saludo)
    console.print("[dim](escribe 'salir' para terminar)[/dim]\n")

    while True:
        try:
            entrada = input("Luis → ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not entrada:
            continue
        if entrada.lower() in ("salir", "exit", "quit"):
            hablar("Hasta luego Luis.")
            console.print("[green]Yuna[/green] → Hasta luego Luis.")
            break

        mensajes.append({"role": "user", "content": entrada})
        contexto = [mensajes[0]] + mensajes[-6:]

        resp = chat_simple(contexto)
        respuesta = clean_response(resp)

        mensajes.append({"role": "assistant", "content": respuesta})
        add_episodic("chat", f"Luis: {entrada[:100]} | Yuna: {respuesta[:100]}")
        console.print(f"\n[bold green]Yuna[/bold green] → {respuesta}\n")
        hablar(respuesta)


if __name__ == "__main__":
    main()
