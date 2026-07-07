import os
import re
import subprocess
from datetime import datetime
import ollama

memoria_path = os.path.expanduser("~/yuna/memoria.txt")
bitacora_path = os.path.expanduser("~/yuna/bitacora.txt")
memoria = open(memoria_path).read() if os.path.exists(memoria_path) else ""

mensajes = [
    {
        "role": "system", 
        "content": f"Eres Yuna, asistente personal femenina de Luis. Contexto: {memoria}. Hablas en español, eres inteligente y directa. Ayudas con análisis de carteras de fideicomisos, datos en tiempo real, SQL, Power BI y Python. Responde de forma concisa. NUNCA muestres tu proceso de pensamiento."
    }
]

def hablar(texto):
    subprocess.run([
        "edge-tts", "--voice", "es-MX-DaliaNeural",
        "--text", texto,
        "--write-media", "/tmp/yuna_respuesta.mp3"
    ], capture_output=True)
    os.system("afplay /tmp/yuna_respuesta.mp3")

def limpiar(texto):
    if "...done thinking." in texto:
        texto = texto.split("...done thinking.")[-1].strip()
    texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL).strip()
    return texto

def registrar(luis, yuna):
    with open(bitacora_path, "a") as f:
        hora = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"[{hora}] Luis: {luis}\n")
        f.write(f"[{hora}] Yuna: {yuna}\n\n")

saludo = "Hola Luis, soy Yuna. ¿En qué te puedo ayudar hoy?"
print(f"\nYuna → {saludo}\n")
hablar(saludo)
print("(escribe 'salir' para terminar)\n")

mensajes.append({"role": "assistant", "content": saludo})

while True:
    mensaje = input("Luis → ")
    if mensaje.lower() == "salir":
        despedida = "Hasta luego Luis, guardando tu sesión."
        print(f"\nYuna → {despedida}")
        hablar(despedida)
        break

    mensajes.append({"role": "user", "content": mensaje})

    respuesta_cruda = ollama.chat(model='qwen3:4b', messages=mensajes)
    respuesta = limpiar(respuesta_cruda['message']['content'])
    
    mensajes.append({"role": "assistant", "content": respuesta})
    
    registrar(mensaje, respuesta)
    print(f"\nYuna → {respuesta}\n")
    hablar(respuesta)
