#!/usr/bin/env python3
"""
Yuna - Agente IA Local
Punto de entrada principal
"""
import sys
import os

# Asegurar path
sys.path.insert(0, os.path.expanduser("~/yuna"))

def main():
    if len(sys.argv) < 2:
        print("""
Yuna - Agente IA Local

Uso:
  python app.py chat      # Chat conversacional
  python app.py agent     # Agente autónomo con tools
  python app.py avatar    # GUI flotante
  python app.py migrate   # Migrar memoria.txt → SQLite
  python app.py test      # Ejecutar tests
        """)
        return
    
    cmd = sys.argv[1]
    
    if cmd == "chat":
        from interface.cli import main as chat_main
        chat_main()
    
    elif cmd == "agent":
        from interface.agent_cli import main as agent_main
        agent_main()
    
    elif cmd == "avatar":
        from interface.avatar import main as avatar_main
        avatar_main()
    
    elif cmd == "migrate":
        from memory.manager import migrar_memoria_txt
        migrar_memoria_txt()
        print("✓ Migración completa")
    
    elif cmd == "test":
        import pytest
        pytest.main(["-v", "tests/"])
    
    elif cmd == "logs":
        import subprocess
        log_file = os.path.expanduser("~/yuna/logs/yuna.log")
        if os.path.exists(log_file):
            subprocess.run(["tail", "-50", log_file])
        else:
            print("No hay logs aún. Usa yuna-agente primero.")

    else:
        print(f"Comando desconocido: {cmd}")

if __name__ == "__main__":
    main()
