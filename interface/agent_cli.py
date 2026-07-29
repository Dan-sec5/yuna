import sys
import os
sys.path.insert(0, os.path.expanduser("~/yuna"))

from core.agent import YunaAgent
from memory.manager import init_db, migrar_memoria_txt
from interface.voice import hablar
import logging

logging.basicConfig(level=logging.WARNING)

def main():
    init_db()
    migrar_memoria_txt()
    
    print("\n🤖 Yuna Agente — Modo autónomo con tools")
    print("(escribe 'salir' para terminar)\n")
    
    def confirmar(tool_name: str, args: dict) -> bool:
        print(f"\n⚠ Confirmación: {tool_name}({args})")
        resp = input("¿Ejecutar? (s/n) → ").strip().lower()
        return resp == 's'
    
    agent = YunaAgent(confirm_callback=confirmar)
    
    saludo = "Hola Luis, modo agente activo. ¿Qué necesitas hacer?"
    print(f"Yuna → {saludo}\n")
    hablar(saludo)
    
    while True:
        try:
            tarea = input("Luis → ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if tarea.lower() in ("salir", "exit", "quit"):
            despedida = "Hasta luego Luis."
            print(f"\nYuna → {despedida}")
            hablar(despedida)
            break
        
        respuesta = agent.process(tarea)
        print(f"\nYuna → {respuesta}\n")
        hablar(respuesta)

if __name__ == "__main__":
    main()
