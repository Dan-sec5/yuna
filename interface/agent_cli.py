import sys
import os
import subprocess
import threading
sys.path.insert(0, os.path.expanduser("~/yuna"))

from core.agent import YunaAgent
from memory.manager import init_db, add_episodic
from config import get

VOICE = get("voice.voice", "es-MX-DaliaNeural")
MAX_CHARS = get("voice.max_chars", 300)

def hablar(texto: str):
    def _hablar():
        if not texto or not texto.strip():
            return
        resultado = subprocess.run([
            "edge-tts", "--voice", VOICE,
            "--text", str(texto).strip()[:MAX_CHARS],
            "--write-media", "/tmp/yuna_agent.mp3"
        ], capture_output=True, timeout=15)
        if resultado.returncode != 0:
            return
        if os.path.getsize("/tmp/yuna_agent.mp3") < 1024:
            return
        os.system("afplay /tmp/yuna_agent.mp3")
    threading.Thread(target=_hablar, daemon=True).start()

def main():
    init_db()
    agente = YunaAgent()

    saludo = "Hola Luis, modo agente activo. Puedo buscar archivos, analizar datos, consultar precios y más."
    print(f"\n🤖 Yuna Agente\n")
    print(f"Yuna → {saludo}\n")
    hablar(saludo)
    print("(escribe 'salir' para terminar, 'reset' para nueva sesión)\n")

    while True:
        try:
            entrada = input("Luis → ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not entrada:
            continue

        if entrada.lower() == "salir":
            hablar("Hasta luego Luis.")
            print("Yuna → Hasta luego Luis.")
            break

        if entrada.lower() == "reset":
            agente.reset()
            print("✓ Sesión reiniciada\n")
            continue

        print("⏳ Procesando...\n")
        respuesta = agente.process(entrada)
        add_episodic("agente", f"Luis: {entrada[:100]} | Yuna: {respuesta[:100]}")
        print(f"Yuna → {respuesta}\n")
        hablar(respuesta)

if __name__ == "__main__":
    main()
