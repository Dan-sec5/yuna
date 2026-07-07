import os
import ollama
from datetime import datetime

bitacora_path = os.path.expanduser("~/yuna/bitacora.txt")
memoria_path = os.path.expanduser("~/yuna/memoria.txt")

if not os.path.exists(bitacora_path) or os.path.getsize(bitacora_path) == 0:
    print("No hay bitácora aún. Usa yuna-chat primero.")
    exit()

bitacora = open(bitacora_path).read()
print("🧠 Analizando tus actividades...")

prompt = f"""Analiza esta bitácora de conversaciones y extrae:
1. Las tareas que Luis hace con más frecuencia
2. Los horarios en que más usa el asistente
3. Sus temas de trabajo más comunes
4. Sugerencias de automatización útiles para él

Bitácora:
{bitacora}

Responde en español, de forma concisa y estructurada."""

resultado = ollama.chat(
    model='llama3.2:3b',
    messages=[{"role": "user", "content": prompt}],
    options={"num_predict": 400, "temperature": 0.3, "num_ctx": 2048}
)

patrones = resultado['message']['content'].strip()
print(f"\n📊 Patrones detectados:\n{patrones}\n")

fecha = datetime.now().strftime("%Y-%m-%d")
with open(memoria_path, "a") as f:
    f.write(f"\n\n--- Patrones aprendidos ({fecha}) ---\n")
    f.write(patrones)

print("✓ Memoria actualizada con tus patrones de uso.")
