import os
import ollama

def consolidar_memoria():
    bitacora_path = os.path.expanduser("~/yuna/bitacora.txt")
    memoria_path = os.path.expanduser("~/yuna/memoria.txt")
    
    if not os.path.exists(bitacora_path) or os.path.getsize(bitacora_path) == 0:
        return

    with open(bitacora_path, 'r') as f:
        contenido_bitacora = f.read()
    
    with open(memoria_path, 'r') as f:
        memoria_actual = f.read()

    prompt = f"""Analiza la siguiente bitácora de conversaciones y la memoria actual. 
    Extrae nuevos patrones de trabajo, preferencias de Luis y correcciones de tareas. 
    Actualiza la memoria para que sea más precisa.
    
    Memoria actual: {memoria_actual}
    Bitácora reciente: {contenido_bitacora}
    
    Responde SOLO con el texto actualizado para el archivo memoria.txt, 
    sin explicaciones ni texto extra."""

    respuesta = ollama.chat(model='qwen3:4b', messages=[{"role": "user", "content": prompt}])
    nueva_memoria = respuesta['message']['content']

    with open(memoria_path, 'w') as f:
        f.write(nueva_memoria.strip())
    
    print("✓ Memoria actualizada con nuevos patrones.")
