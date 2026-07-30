import sqlite3
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from config import get

DB_PATH = Path(get("paths.memory_db", "~/yuna/data/yuna.db")).expanduser()

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS preferencias (
                clave TEXT PRIMARY KEY,
                valor TEXT,
                actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                evento TEXT,
                detalles TEXT
            );
            CREATE TABLE IF NOT EXISTS tarea_actual (
                id TEXT PRIMARY KEY,
                estado TEXT,
                datos JSON,
                actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_episodic_fecha ON episodic(fecha);
        """)

def set_preferencia(clave: str, valor: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO preferencias (clave, valor) VALUES (?, ?)",
            (clave, valor)
        )

def get_preferencia(clave: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT valor FROM preferencias WHERE clave = ?", (clave,))
        row = cur.fetchone()
        return row[0] if row else None

def get_all_preferencias() -> Dict[str, str]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT clave, valor FROM preferencias")
        return {row[0]: row[1] for row in cur.fetchall()}

def add_episodic(evento: str, detalles: str = ""):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO episodic (evento, detalles) VALUES (?, ?)",
            (evento, detalles)
        )

def get_episodic(limit: int = 50) -> List[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT fecha, evento, detalles FROM episodic ORDER BY fecha DESC LIMIT ?",
            (limit,)
        )
        return [{"fecha": r[0], "evento": r[1], "detalles": r[2]} for r in cur.fetchall()]

def set_tarea_actual(tarea_id: str, estado: str, datos: Dict = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tarea_actual (id, estado, datos) VALUES (?, ?, ?)",
            (tarea_id, estado, json.dumps(datos or {}))
        )

def get_tarea_actual(tarea_id: str) -> Optional[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT estado, datos FROM tarea_actual WHERE id = ?", (tarea_id,)
        )
        row = cur.fetchone()
        if row:
            return {"estado": row[0], "datos": json.loads(row[1])}
        return None

def migrar_memoria_txt():
    """Migración única desde memoria.txt a SQLite"""
    init_db()  # Asegurar tablas antes de escribir
    txt_path = Path(get("paths.memory_txt_legacy", "~/yuna/memoria.txt")).expanduser()
    if not txt_path.exists():
        return
    
    print(f"📦 Migrando memoria desde {txt_path}...")
    with open(txt_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("[P]"):
                partes = line[3:].split(":", 1)
                if len(partes) == 2:
                    set_preferencia(partes[0].strip(), partes[1].strip())
    
    backup = txt_path.with_suffix(".txt.bak")
    txt_path.rename(backup)
    print(f"✓ Migración completa. Backup en {backup}")

def get_relevant_memory(query: str) -> str:
    """Obtiene memoria relevante para enriquecer el contexto"""
    partes = []
    
    prefs = get_all_preferencias()
    if prefs:
        partes.append("PREFERENCIAS:\n" + "\n".join(f"- {k}: {v}" for k, v in prefs.items()))
    
    episodic = get_episodic(10)
    if episodic:
        partes.append("HISTORIAL RECIENTE:\n" + "\n".join(f"- [{e['fecha']}] {e['evento']}" for e in episodic))
    
    return "\n\n".join(partes) if partes else ""

# Tools para el agente
def consultar_memoria(tabla: str, clave: str = "") -> str:
    if tabla == "preferencias":
        if clave:
            val = get_preferencia(clave)
            return f"{clave}: {val}" if val else f"Clave '{clave}' no encontrada"
        prefs = get_all_preferencias()
        return "\n".join(f"{k}: {v}" for k, v in prefs.items()) if prefs else "Sin preferencias"
    
    if tabla == "episodic":
        episodic = get_episodic(20)
        return "\n".join(f"[{e['fecha']}] {e['evento']}: {e['detalles']}" for e in episodic) if episodic else "Historial vacío"
    
    return f"Tabla '{tabla}' no válida"

def escribir_memoria(clave: str, valor: str) -> str:
    set_preferencia(clave, valor)
    return f"✓ Memoria guardada: {clave} = {valor}"
