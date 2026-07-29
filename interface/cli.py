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
    
    print("\n💬 Yuna Chat — Modo conversación")
    print("(escribe 'salir' para terminar)\n")
    
    agent = YunaAgent()
    
    saludo = "Hola Luis, soy Yuna. ¿En qué te ayudo hoy?"
    print(f"Yuna → {saludo}\n")
    hablar(saludo)
    
    while True:
        try:
            user = input("Luis → ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if user.lower() in ("salir", "exit", "quit"):
            despedida = "Hasta luego Luis."
            print(f"\nYuna → {despedida}")
            hablar(despedida)
            break
        
        respuesta = agent.process(user)
        print(f"\nYuna → {respuesta}\n")
        hablar(respuesta)

if __name__ == "__main__":
    main()
