import os
import ollama
from datetime import datetime

memoria_path = os.path.expanduser("~/yuna/memoria.txt")
historial_dir = os.path.expanduser("~/yuna/historial/")
os.makedirs(historial_dir, exist_ok=True)

if not os.path.exists(memoria_path):
    print("No existe memoria.txt")
    exit()

memoria = open(memoria_path).read()
lineas = [l for l in memoria.strip().split('\n') if l.strip()]

# Separar permanentes de aprendidas
permanentes = [l for l in lineas if l.startswith("[P]")]
aprendidas = [l for l in lineas if not l.startswith("[P]") and not l.startswith("---")]

print(f"📋 Memoria actual: {len(lineas)} líneas")
print(f"   [P] Permanentes: {len(permanentes)}")
print(f"   Aprendidas: {len(aprendidas)}")

if len(aprendidas) < 20:
    print("✓ Memoria saludable. No necesita limpieza aún.")
    exit()

print(f"\n🧹 Consolidando {len(aprendidas)} aprendizajes...")

prompt = f"""Consolida estos aprendizajes sobre Luis en máximo 15 puntos esenciales.
Elimina duplicados, mantén solo lo más relevante y reciente.
Formato: una línea por punto, empezando con "-"
Sin explicaciones, solo los puntos.

APRENDIZAJES:
{chr(10).join(aprendidas)}"""

resultado = ollama.chat(
    model='llama3.2:3b',
    messages=[{"role": "user", "content": prompt}],
    options={"num_predict": 300, "temperature": 0.3, "num_ctx": 2048}
)

consolidado = resultado['message']['content'].strip()

print(f"\n📝 Resultado de la consolidación:\n{consolidado}\n")
confirmar = input("¿Guardar esta versión consolidada? (s/n) → ")

if confirmar.lower() != "s":
    print("❌ Cancelado. Memoria sin cambios.")
    exit()

# Backup antes de sobrescribir
fecha = datetime.now().strftime("%Y-%m-%d_%H-%M")
backup_path = f"{historial_dir}memoria_backup_{fecha}.txt"
with open(backup_path, "w") as f:
    f.write(memoria)

# Nueva memoria: permanentes + consolidado
nueva_memoria = "\n".join(permanentes) + "\n\n--- Consolidado ---\n" + consolidado

with open(memoria_path, "w") as f:
    f.write(nueva_memoria)

print(f"✓ Memoria consolidada.")
print(f"✓ Backup guardado en {backup_path}")
