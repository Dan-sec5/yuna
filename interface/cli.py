import sys
import os
import subprocess
import threading
sys.path.insert(0, os.path.expanduser("~/yuna"))

from core.llm import chat_simple, clean_response
from memory.manager import init_db, get_relevant_memory, add_episodic
from config import get

VOICE = get("voice.voice", "es-MX-DaliaNeural")
MAX_CHARS = get("voice.max_chars", 300)

def hablar(texto: str):
    def _hablar():
        subprocess.run([
            "edge-tts", "--voice", VOICE,
            "--text", str(texto)[:MAX_CHARS],
            "--write-media", "/tmp/yuna_chat.mp3"
        ], capture_output=True)
        os.system("afplay /tmp/yuna_chat.mp3")
    threading.Thread(target=_hablar, daemon=True).start()

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
    print(f"\nYuna → {saludo}\n")
    hablar(saludo)
    print("(escribe 'salir' para terminar)\n")

    while True:
        try:
            entrada = input("Luis → ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if entrada.lower() == "salir":
            hablar("Hasta luego Luis.")
            print("Yuna → Hasta luego Luis.")
            break

        mensajes.append({"role": "user", "content": entrada})
        contexto = [mensajes[0]] + mensajes[-6:]

        resp = chat_simple(contexto)
        respuesta = clean_response(resp)

        mensajes.append({"role": "assistant", "content": respuesta})
        add_episodic("chat", f"Luis: {entrada[:100]} | Yuna: {respuesta[:100]}")
        print(f"\nYuna → {respuesta}\n")
        hablar(respuesta)

if __name__ == "__main__":
    main()
