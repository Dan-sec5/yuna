#!/usr/bin/env python3
"""
Migra memoria.txt y bitacora.txt a SQLite (data/yuna.db)
Ejecutar UNA sola vez después de la reestructura.
"""
import os
import sys
from pathlib import Path

# Asegurar imports
sys.path.insert(0, os.path.expanduser("~/yuna"))

from memory.manager import init_db, set_preferencia, add_episodic, migrar_memoria_txt

def main():
    print("🔄 Iniciando migración de memoria...")
    
    # 1. Inicializar DB
    init_db()
    print("✓ Base de datos inicializada")
    
    # 2. Migrar memoria.txt (preferencias con [P])
    migrar_memoria_txt()
    
    # 3. Migrar bitacora.txt a episodic
    bitacora_path = Path("~/yuna/bitacora.txt").expanduser()
    if bitacora_path.exists():
        print("📦 Migrando bitácora...")
        with open(bitacora_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Parsear líneas: [fecha] Luis: ... / [fecha] Yuna: ...
        import re
        lines = content.strip().split("\n")
        i = 0
        count = 0
        while i < len(lines) - 1:
            line = lines[i].strip()
            if line.startswith("[") and "] Luis:" in line:
                fecha_str = line[1:line.index("]")]
                user_msg = line[line.index("Luis:")+5:].strip()
                # Buscar respuesta de Yuna
                if i + 1 < len(lines) and "] Yuna:" in lines[i+1]:
                    yuna_line = lines[i+1].strip()
                    yuna_msg = yuna_line[yuna_line.index("Yuna:")+5:].strip()
                    add_episodic(f"Usuario: {user_msg[:80]}", f"Yuna: {yuna_msg[:200]}")
                    count += 1
                    i += 2
                    continue
            i += 1
        print(f"✓ {count} intercambios migrados a episodic")
        
        # Backup
        backup = bitacora_path.with_suffix(".txt.bak")
        bitacora_path.rename(backup)
        print(f"✓ Backup bitácora en {backup}")
    
    print("\n✅ Migración completada")
    print("   - Preferencias en tabla 'preferencias'")
    print("   - Historial en tabla 'episodic'")
    print("   - Archivos .txt originales respaldados como .bak")

if __name__ == "__main__":
    main()
