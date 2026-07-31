import os
import sys

sys.path.insert(0, os.path.expanduser("~/yuna"))
from core import cargar_memoria, limpiar, hablar, registrar, guardar_aprendizaje, llamar_ollama

memoria = cargar_memoria()

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

saludo = "Hola Luis, soy Yuna. ¿En qué te puedo ayudar hoy?"
print(f"\nYuna → {saludo}\n")
hablar(saludo)
print("(escribe 'salir' para terminar)\n")
mensajes.append({"role": "assistant", "content": saludo})

while True:
    mensaje = input("Luis → ").strip()
    if mensaje.lower() == "salir":
        despedida = "Hasta luego Luis, guardando tu sesión."
        print(f"\nYuna → {despedida}")
        hablar(despedida)
        guardar_aprendizaje(mensajes)
        break

    mensajes.append({"role": "user", "content": mensaje})
    contexto = [mensajes[0]] + mensajes[-6:]  # System + últimos 6 mensajes

    respuesta_cruda = llamar_ollama(
        contexto,
        num_predict=600, temperature=0.7, num_ctx=2048
    )
    respuesta = limpiar(respuesta_cruda['message']['content'])

    mensajes.append({"role": "assistant", "content": respuesta})
    registrar(mensaje, respuesta)
    print(f"\nYuna → {respuesta}\n")
    hablar(respuesta)
