import os
import re
import ollama

memoria_path = os.path.expanduser("~/yuna/memoria.txt")
memoria = open(memoria_path).read() if os.path.exists(memoria_path) else ""


print("🤖 Yuna ejecutora - escribe tu tarea o 'salir'")
print("----------------------------------------")

COMANDOS_PROHIBIDOS = [
    r'rm\s+-rf\s+/',
    r'rm\s+-rf\s+~',
    r':\(\)\s*\{\s*:\|\:',
    r'mkfs\.',
    r'dd\s+if=.*of=/dev/',
    r'>?\s*/etc/',
    r'curl\s+.*\|\s*sh',
]

def es_comando_seguro(comando):
    for patron in COMANDOS_PROHIBIDOS:
        if re.search(patron, comando, re.IGNORECASE):
            return False, f"Patrón peligroso detectado: {patron}"
    return True, "OK"

while True:
    tarea = input("\n¿Qué hago? → ")
    if tarea.lower() == "salir":
        break
    
    prompt_ejecucion = f"Contexto: {memoria}. Tu única tarea es escribir un comando bash para macOS que cumpla con esto: {tarea}. Envuelve el comando estrictamente dentro de un bloque de código markdown (```bash ... ```). No agregues texto introductorio ni explicaciones."
    
    respuesta = ollama.chat(model= 'llama3.2:3b', messages=[
        {"role": "user", "content": prompt_ejecucion}
    ])
    texto_salida = respuesta['message']['content']
    
    match = re.search(r'```(?:bash|sh)?\s*(.*?)\s*```', texto_salida, re.DOTALL)
    comando = match.group(1).strip() if match else ""
    
    if not comando:
        print("⚠ No pude generar un comando limpio, esto fue lo que devolvió el modelo:")
        print(texto_salida)
        continue
    
    print(f"\n📋 Comando: {comando}")
    confirmar = input("¿Ejecuto? (s/n) → ")
    
    if confirmar.lower() == "s":
        os.system(comando)
        print("✓ Listo")
