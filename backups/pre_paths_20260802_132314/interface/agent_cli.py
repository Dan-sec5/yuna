import sys
import os
import subprocess
import threading
sys.path.insert(0, os.path.expanduser("~/yuna"))

from core.agent import YunaAgent
from core.llm import preload_model
from memory.manager import init_db, add_episodic
from config import get

VOICE = get("voice.voice", "es-MX-DaliaNeural")
MAX_CHARS = get("voice.max_chars", 300)

def hablar(texto: str):
    def _hablar():
        if not texto or not texto.strip():
            return
        try:
            resultado = subprocess.run([
                "edge-tts", "--voice", VOICE,
                "--text", str(texto).strip()[:MAX_CHARS],
                "--write-media", "/tmp/yuna_agent.mp3"
            ], capture_output=True, timeout=15)
            if resultado.returncode != 0:
                return
            if os.path.getsize("/tmp/yuna_agent.mp3") < 1024:
                return
            sistema = os.name
            if sistema == 'posix' and os.uname().sysname == 'Darwin':
                subprocess.run(["afplay", "/tmp/yuna_agent.mp3"], timeout=60)
            else:
                subprocess.run(["mpg123", "-q", "/tmp/yuna_agent.mp3"], timeout=60)
        except Exception:
            pass
    threading.Thread(target=_hablar, daemon=True).start()

def main():
    init_db()
    print("⏳ Precargando modelo en RAM...")
    preload_model()
    print("✅ Modelo listo.\n")

    agente = YunaAgent()
    saludo = "Hola Luis, modo agente activo. Puedo buscar archivos, analizar datos, consultar precios y mas."
    print(f"🤖 Yuna Agente\n")
    print(f"Yuna -> {saludo}\n")
    hablar(saludo)
    print("(escribe 'salir' para terminar, 'reset' para nueva sesion, '👍' o '👎' despues de una respuesta)\n")

    ultima_query = ""
    while True:
        try:
            entrada = input("Luis -> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not entrada:
            continue
        if entrada.lower() == "salir":
            hablar("Hasta luego Luis.")
            print("Yuna -> Hasta luego Luis.")
            break
        if entrada.lower() == "reset":
            agente.reset()
            print("✓ Sesion reiniciada\n")
            continue
        if entrada in ("👍", "bien", "util", "up"):
            if ultima_query:
                agente.provide_feedback(ultima_query, "positive")
                print("✓ Feedback positivo registrado para aprendizaje\n")
            continue
        if entrada in ("👎", "mal", "inutil", "down"):
            if ultima_query:
                agente.provide_feedback(ultima_query, "negative")
                print("✓ Feedback negativo registrado. Intentare mejorar.\n")
            continue
        print("⏳ Procesando...\n")
        ultima_query = entrada
        respuesta = agente.process(entrada)
        add_episodic("agente", f"Luis: {entrada[:100]} | Yuna: {respuesta[:100]}")
        print(f"Yuna -> {respuesta}\n")
        hablar(respuesta)

if __name__ == "__main__":
    main()
