import os
import re
import sys

sys.path.insert(0, os.path.expanduser("~/yuna"))
from core import cargar_memoria, llamar_ollama

memoria = cargar_memoria()

# Patrones de comandos peligrosos (lista negra)
COMANDOS_PROHIBIDOS = [
    r'rm\s+-rf\s+/',
    r'rm\s+-rf\s+~',
    r':\(\)\s*\{\s*:\|',
    r'mkfs\.',
    r'dd\s+if=.*of=/dev/',
    r'curl\s+.*\|\s*sh',
    r'wget\s+.*\|\s*sh',
    r'eval\s*\$',
    r'\bformat\b',
]

def es_comando_seguro(comando):
    """Valida que el comando no contenga patrones peligrosos."""
    for patron in COMANDOS_PROHIBIDOS:
        if re.search(patron, comando, re.IGNORECASE):
            return False, f"Patrón peligroso detectado: {patron}"
    return True, "OK"

print("🤖 Yuna ejecutora - escribe tu tarea o 'salir'")
print("----------------------------------------")

while True:
    tarea = input("\n¿Qué hago? → ").strip()
    if tarea.lower() == "salir":
        break

    prompt_ejecucion = (
        f"Contexto: {memoria}. "
        f"Tu única tarea es escribir un comando bash para macOS que cumpla con esto: {tarea}. "
        f"Envuelve el comando estrictamente dentro de un bloque de código markdown (```bash ... ```). "
        f"No agregues texto introductorio ni explicaciones. "
        f"IMPORTANTE: No uses rm -rf, mkfs, dd, ni pipes a sh."
    )

    respuesta = llamar_ollama(
        [{"role": "user", "content": prompt_ejecucion}],
        num_predict=200, temperature=0.3
    )
    texto_salida = respuesta['message']['content']

    match = re.search(r'```(?:bash|sh)?\s*(.*?)\s*```', texto_salida, re.DOTALL)
    comando = match.group(1).strip() if match else ""

    if not comando:
        print("⚠ No pude generar un comando limpio, esto fue lo que devolvió el modelo:")
        print(texto_salida)
        continue

    # Validar seguridad
    seguro, razon = es_comando_seguro(comando)
    if not seguro:
        print(f"\n🚫 Comando bloqueado por seguridad: {razon}")
        print(f"📋 Comando detectado: {comando}")
        continue

    print(f"\n📋 Comando: {comando}")
    confirmar = input("¿Ejecuto? (s/n) → ")

    if confirmar.lower() == "s":
        try:
            import subprocess
            resultado = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=60)
            if resultado.stdout:
                print(resultado.stdout)
            if resultado.stderr:
                print(f"⚠ {resultado.stderr}")
            print("✓ Listo")
        except subprocess.TimeoutExpired:
            print("⏱ El comando excedió 60 segundos y fue cancelado.")
        except Exception as e:
            print(f"⚠ Error ejecutando: {e}")
