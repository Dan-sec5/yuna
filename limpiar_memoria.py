import os
import ollama
from datetime import datetime

memoria_path = os.path.expanduser("~/yuna/memoria.txt")
memoria = open(memoria_path).read() if os.path.exists(memoria_path) else ""

lineas = [l for l in memoria.strip().split('\n') if l.strip()]

# Solo limpia si hay más de 40 líneas
if len(lineas) < 40:
    print(f"✓ Memoria saludable ({len(lineas)} líneas). No necesita limpieza.")
    exit()

print(f"🧹 Memoria tiene {len(lineas)} líneas. Consolidando...")

prompt = f"""Consolida esta memoria sobre Luis en máximo 20 puntos esenciales.
Elimina duplicados y mantén solo lo más relevante y reciente.
Formato: una línea por punto, empezando con "-"

MEMORIA ACTUAL:
{memoria}"""

resultado = ollama.chat(
    model='llama3.2:3b',
    messages=[{"role": "user", "content": prompt}],
    options={"num_predict": 400, "temperature": 0.3, "num_ctx": 2048}
)

memoria_consolidada = resultado['message']['content'].strip()

# Backup antes de sobrescribir
fecha = datetime.now().strftime("%Y-%m-%d")
backup_path = os.path.expanduser(f"~/yuna/historial/memoria_backup_{fecha}.txt")
os.makedirs(os.path.expanduser("~/yuna/historial/"), exist_ok=True)
with open(backup_path, "w") as f:
    f.write(memoria)

# Guardar memoria consolidada
with open(memoria_path, "w") as f:
    f.write(memoria_consolidada)

print(f"✓ Memoria consolidada a {len(memoria_consolidada.split(chr(10)))} líneas.")
print(f"✓ Backup guardado en {backup_path}")
