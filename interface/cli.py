"""
interface/cli.py

Chat conversacional de Yuna (terminal).
La voz se centraliza en interface/voice.py — no duplicar hablar() aquí.

La personalidad se carga desde config/prompts/chat_system.txt
(fuente única, alineada con el Modelfile de Ollama).
"""
import sys
import os

sys.path.insert(0, os.path.expanduser("~/yuna"))

from pathlib import Path
from rich.console import Console

from core.llm import chat_simple, clean_response
from memory.manager import init_db, get_relevant_memory, add_episodic
from interface.voice import hablar

console = Console()

_CHAT_PROMPT_PATH = Path.home() / "yuna" / "config" / "prompts" / "chat_system.txt"
_CHAT_PROMPT_FALLBACK = (
    "Eres Yuna (ゆな), la maid personal y asistente de confianza de Luis. "
    "Dulce, atenta, educada y eficiente. Te diriges a él como Luis, "
    "\"Maestro\", \"Amo\" o \"Mi Señor\". Nunca rompes personaje."
)


def load_chat_prompt() -> str:
    try:
        return _CHAT_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return _CHAT_PROMPT_FALLBACK


def main():
    init_db()
    memoria = get_relevant_memory("contexto general")

    mensajes = [{
        "role": "system",
        "content": load_chat_prompt() + f"\n\nMEMORIA:\n{memoria}"
    }]

    saludo = "Bienvenido de vuelta, mi Señor. Qué alegría volver a verle. ¿En qué puedo servirle hoy?"
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
            despedida = "Hasta luego, mi Señor. Que descanse bien."
            hablar(despedida)
            console.print(f"[green]Yuna[/green] → {despedida}")
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
