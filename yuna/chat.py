import os
import re
import subprocess
import threading
from datetime import datetime
import ollama

memoria_path = os.path.expanduser("~/yuna/memoria.txt")
bitacora_path = os.path.expanduser("~/yuna/bitacora.txt")
memoria = open(memoria_path).read() if os.path.exists(memoria_path) else ""

mensajes = [
    {
        "role": "system",
        "content": f"""Eres Yuna, asistente personal de Luis. Tienes personalidad propia: eres inteligente, directa, ocasionalmente bromista y genuinamente interesada en ayudar a Luis a crecer profesionalmente.

CONTEXTO DE LUIS: {memoria}

CÓMO HABLAS:
- Usas español mexicano natural, como una colega cercana
- Varías tu tono: formal cuando Luis pregunta algo técnico, más relajada en conversación casual
- Haces preguntas de seguimiento cuando algo no está claro
- A veces usas expresiones como oye, mira, la verdad es que, te cuento que
- Si comete un error, lo corriges con tacto, no de manera robótica
- Tienes opiniones propias sobre tecnología, datos y productividad
- Recuerdas lo que Luis te dijo en la conversación y lo referencias naturalmente

LO QUE NO HACES:
- No repites Claro o Por supuesto en cada respuesta
- No eres excesivamente formal ni usas lenguaje corporativo
- No muestras tu proceso de pensamiento
- No das respuestas genéricas, siempre conectas con el contexto de Luis

LONGITUD: Ajusta según el tema. Preguntas simples = 1-2 oraciones. Temas técnicos = lo que necesite."""
    }
]

def hablar(texto):
    def _hablar():
        subprocess.run([
            "edge-tts", "--voice", "es-MX-DaliaNeural",
            "--text", texto,
            "--write-media", "/tmp/yuna_respuesta.mp3"
        ], capture_output=True)
        os.system("afplay /tmp/yuna_respuesta.mp3")
    threading.Thread(target=_hablar, daemon=True).start()

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

def guardar_aprendizaje():
    intercambios = [m for m in mensajes if m["role"] == "user"]
    if len(intercambios) < 2:
        return
    print("\n🧠 Guardando aprendizajes de esta sesión...")
    resumen = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in mensajes[-8:] if m["role"] in ["user", "assistant"]
    ])
    prompt = f"""Analiza esta conversación entre Luis y Yuna.
Extrae MÁXIMO 3 aprendizajes concretos y útiles sobre Luis:
preferencias, tareas que hizo, temas que le interesan o datos nuevos sobre su trabajo.
Formato: una línea por aprendizaje, empezando con "-"
Sin explicaciones, solo los puntos.

CONVERSACIÓN:
{resumen}"""
    try:
        resultado = ollama.chat(
            model='llama3.2:3b',
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 150, "temperature": 0.3, "num_ctx": 2048}
        )
        aprendizajes = limpiar(resultado['message']['content'].strip())
        if aprendizajes:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(memoria_path, "a") as f:
                f.write(f"\n\n--- Sesión {fecha} ---\n")
                f.write(aprendizajes)
            print(f"✓ Memoria actualizada:\n{aprendizajes}")
    except Exception as e:
        print(f"⚠ No se pudo guardar aprendizaje: {e}")

saludo = "Hola Luis, soy Yuna. En que te puedo ayudar hoy?"
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
        guardar_aprendizaje()
        break
    mensajes.append({"role": "user", "content": mensaje})
    contexto = [mensajes[0]] + mensajes[-4:]
    respuesta_cruda = ollama.chat(
        model='llama3.2:3b',
        messages=contexto,
        options={"num_predict": 600, "temperature": 0.7, "num_ctx": 2048},
        think=False
    )
    respuesta = limpiar(respuesta_cruda['message']['content'])
    mensajes.append({"role": "assistant", "content": respuesta})
    registrar(mensaje, respuesta)
    print(f"\nYuna → {respuesta}\n")
    hablar(respuesta)
