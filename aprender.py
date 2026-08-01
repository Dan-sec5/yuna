import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/yuna"))

from memory.manager import DB_PATH, get_all_preferencias, get_episodic
from core.llm import chat_simple

def main():
    if not DB_PATH.exists():
        print("No hay base de datos. Usa yuna-chat primero.")
        return

    # Obtener datos de SQLite
    prefs = get_all_preferencias()
    episodic = get_episodic(100)
    
    if not episodic:
        print("No hay suficientes datos para analizar.")
        return

    # Construir contexto de aprendizaje
    bitacora_resumen = []
    for e in episodic:
        detalles = e.get('detalles', '{}')
        try:
            import json
            d = json.loads(detalles)
            bitacora_resumen.append(f"- {e['fecha']}: {d.get('user', e['evento'])}")
        except:
            bitacora_resumen.append(f"- {e['fecha']}: {e['evento']}")

    prompt = f"""Analiza esta bitacora de conversaciones y extrae:
1. Las tareas que Luis hace con mas frecuencia
2. Los horarios en que mas usa el asistente
3. Sus temas de trabajo mas comunes
4. Sugerencias de automatizacion utiles para el

Bitacora:
{chr(10).join(bitacora_resumen[:50])}

Responde en espanol, de forma concisa y estructurada."""

    print("🧠 Analizando tus actividades...")

    respuesta = chat_simple(
        [{"role": "user", "content": prompt}],
        model="qwen3:8b",
        num_predict=400,
        temperature=0.3
    )

    if respuesta and hasattr(respuesta, 'message'):
        patrones = respuesta.message.content.strip()
    else:
        patrones = "No se pudo generar analisis."

    print(f"\n📊 Patrones detectados:\n{patrones}\n")

    # Guardar en preferencias
    from memory.manager import set_preferencia
    fecha = datetime.now().strftime("%Y-%m-%d")
    set_preferencia(f"patrones_{fecha}", patrones[:500])
    print("✓ Memoria actualizada con tus patrones de uso.")

if __name__ == "__main__":
    main()
