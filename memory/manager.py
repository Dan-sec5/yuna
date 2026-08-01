import sqlite3
import os
import json
import re
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
            CREATE TABLE IF NOT EXISTS entity_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT UNIQUE,
                relation TEXT,
                value TEXT,
                confidence REAL DEFAULT 1.0,
                updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_entity ON entity_memory(entity);
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

def set_entity(entity: str, relation: str, value: str, confidence: float = 1.0):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO entity_memory
               (entity, relation, value, confidence, updated)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (entity.lower(), relation, value, confidence)
        )

def get_entity(entity: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT value, relation FROM entity_memory WHERE entity = ?",
            (entity.lower(),)
        )
        row = cur.fetchone()
        return f"{row[1]}: {row[0]}" if row else None

def get_relevant_memory(query: str, top_k: int = 5) -> str:
    partes = []
    query_lower = query.lower()
    entities = re.findall(r'\b[A-Z][a-z]+\b', query)
    entities += re.findall(r'"([^"]+)"', query)
    entity_data = []
    for ent in entities:
        val = get_entity(ent)
        if val:
            entity_data.append(f"{ent} -> {val}")
    if entity_data:
        partes.append("ENTIDADES CONOCIDAS:\n" + "\n".join(entity_data))

    prefs = get_all_preferencias()
    relevant_prefs = {}
    for k, v in prefs.items():
        k_lower = k.lower()
        v_lower = str(v).lower()
        if any(word in k_lower or word in v_lower for word in query_lower.split() if len(word) > 3):
            relevant_prefs[k] = v
    if relevant_prefs:
        partes.append("PREFERENCIAS RELEVANTES:\n" +
            "\n".join(f"- {k}: {v}" for k, v in list(relevant_prefs.items())[:top_k]))

    episodic = get_episodic(20)
    relevant_episodes = []
    query_words = set(w for w in query_lower.split() if len(w) > 3)
    for e in episodic:
        content = f"{e['evento']} {e['detalles']}".lower()
        score = len(query_words & set(content.split()))
        if score > 0 or len(relevant_episodes) < 3:
            relevant_episodes.append((score, e))
    relevant_episodes.sort(key=lambda x: x[0], reverse=True)
    top_episodes = [e for _, e in relevant_episodes[:top_k]]
    if top_episodes:
        partes.append("HISTORIAL RELEVANTE:\n" +
            "\n".join(f"- [{e['fecha']}] {e['evento']}" for e in top_episodes))

    return "\n\n".join(partes) if partes else ""

def migrar_memoria_txt():
    init_db()
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
    print(f"✓ Migracion completa. Backup en {backup}")

def consultar_memoria(tabla: str, clave: str = "") -> str:
    if tabla == "preferencias":
        if clave:
            val = get_preferencia(clave)
            return f"{clave}: {val}" if val else f"Clave '{clave}' no encontrada"
        prefs = get_all_preferencias()
        return "\n".join(f"{k}: {v}" for k, v in prefs.items()) if prefs else "Sin preferencias"
    if tabla == "episodic":
        episodic = get_episodic(20)
        return "\n".join(f"[{e['fecha']}] {e['evento']}: {e['detalles']}" for e in episodic) if episodic else "Historial vacio"
    if tabla == "entities":
        ent = get_entity(clave)
        return ent or f"Entidad '{clave}' no encontrada"
    return f"Tabla '{tabla}' no valida"

def escribir_memoria(clave: str, valor: str) -> str:
    set_preferencia(clave, valor)
    return f"✓ Memoria guardada: {clave} = {valor}"

def escribir_entidad(entidad: str, relacion: str, valor: str) -> str:
    set_entity(entidad, relacion, valor)
    return f"✓ Entidad guardada: {entidad} es {relacion} de {valor}"

# FIX: Funcion que agent.py necesita importar desde aqui
def add_interaction_metric(query: str, response: str, tools: list, success: bool, latency: float):
    """Guarda metricas de interaccion en la base de datos."""
    import json
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO interaction_metrics (query, response, tools_used, success, latency_ms)
               VALUES (?, ?, ?, ?, ?)""",
            (query[:500], response[:500], json.dumps(tools), success, latency * 1000)
        )
