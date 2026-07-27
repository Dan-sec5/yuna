from core import cargar_memoria, limpiar, hablar, registrar, llamar_ollama
import os
import re
import sys
import subprocess
import threading
from datetime import datetime
import ollama

sys.path.insert(0, os.path.expanduser("~/yuna"))
from tools.archivos import buscar_archivos, listar_recientes, organizar_por_tipo
from tools.datos import leer_excel, leer_csv, leer_pdf
from tools.web import buscar_web, precio_activo, noticias_financieras_mx
from tools.sistema import ejecutar_bash, notificar, info_sistema

memoria_path = os.path.expanduser("~/yuna/memoria.txt")
bitacora_path = os.path.expanduser("~/yuna/bitacora.txt")
memoria = open(memoria_path).read() if os.path.exists(memoria_path) else ""

HERRAMIENTAS = {
    "buscar_archivos": buscar_archivos,
    "listar_recientes": listar_recientes,
    "organizar_archivos": organizar_por_tipo,
    "leer_excel": leer_excel,
    "leer_csv": leer_csv,
    "leer_pdf": leer_pdf,
    "buscar_web": buscar_web,
    "precio_activo": precio_activo,
    "noticias_mx": noticias_financieras_mx,
    "info_sistema": info_sistema,
}

SYSTEM_PROMPT = f"""Eres Yuna, agente IA personal de Luis. Ejecutas tareas reales usando herramientas.

CONTEXTO: {memoria}

RUTAS DEL SISTEMA:
- Descargas: ~/Downloads
- Reportes: ~/Desktop/Reportes
- Datos Excel: ~/Desktop/Datos

HERRAMIENTAS DISPONIBLES (escribe exactamente así para usarlas):
TOOL:listar_recientes("~/Downloads", 7)
TOOL:leer_excel("ruta/archivo.xlsx")
TOOL:precio_activo("AAPL")
TOOL:buscar_web("tu búsqueda")
TOOL:noticias_mx()
TOOL:info_sistema()
TOOL:organizar_archivos("~/Downloads")

REGLAS:
- Cuando necesites ejecutar algo, escribe TOOL:nombre(args) en una línea sola
- Después de ver el resultado, dáselo a Luis de forma clara y concisa
- Habla en español mexicano
- NUNCA inventes resultados — solo usa lo que retorna la herramienta"""

def limpiar(texto):
    texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL)
    if "...done thinking." in texto:
        texto = texto.split("...done thinking.")[-1]
    return texto.strip()

def hablar(texto):
    def _hablar():
        subprocess.run([
            "edge-tts", "--voice", "es-MX-DaliaNeural",
            "--text", texto[:300],
            "--write-media", "/tmp/yuna_agente.mp3"
        ], capture_output=True)
        os.system("afplay /tmp/yuna_agente.mp3")
    threading.Thread(target=_hablar, daemon=True).start()

def detectar_y_ejecutar_tools(respuesta):
    """Detecta TODAS las líneas TOOL: y las ejecuta en orden"""
    resultados = []
    lineas = respuesta.split('\n')
    
    for linea in lineas:
        linea = linea.strip()
        if not linea.startswith("TOOL:"):
            continue
        
        llamada = linea[5:].strip()
        match = re.match(r'(\w+)\((.*)\)', llamada)
        if not match:
            continue
            
        nombre = match.group(1)
        args_str = match.group(2).strip()
        
        if nombre not in HERRAMIENTAS:
            resultados.append((nombre, f"Error: herramienta '{nombre}' no existe"))
            continue
        
        # Extraer argumentos (mejorado)
        args = []
        if args_str:
            # Soporta strings, ints y listas vacías
            for arg in re.findall(r'"([^"]*?)"|\'([^\']*?)\'|(\d+)', args_str):
                valor = arg[0] or arg[1] or arg[2]
                if valor.isdigit():
                    args.append(int(valor))
                else:
                    args.append(valor)
        
        print(f"\n⚙ Ejecutando: {nombre}({args_str})")
        try:
            resultado = HERRAMIENTAS[nombre](*args) if args else HERRAMIENTAS[nombre]()
            resultados.append((nombre, str(resultado)))
        except Exception as e:
            resultados.append((nombre, f"Error: {e}"))
    
    return resultados  # ← Lista de tuplas (nombre, resultado)



def registrar(usuario, agente):
    with open(bitacora_path, "a") as f:
        hora = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"[{hora}] Luis: {usuario}\n")
        f.write(f"[{hora}] Yuna: {agente}\n\n")

mensajes = [{"role": "system", "content": SYSTEM_PROMPT}]

print("\n🤖 Yuna Agente — Modo autónomo activado")
print("(escribe 'salir' para terminar)\n")

saludo = "Hola Luis, modo agente activo. ¿Qué necesitas hacer hoy?"
print(f"Yuna → {saludo}\n")
hablar(saludo)
mensajes.append({"role": "assistant", "content": saludo})

MAX_ITERACIONES = 5
iteracion = 0

while iteracion < MAX_ITERACIONES:
    iteracion += 1
    respuesta = limpiar(respuesta_cruda['message']['content'])
    
    tools_ejecutadas = detectar_y_ejecutar_tools(respuesta)
    
    if not tools_ejecutadas:
        break  # No hay más herramientas, terminamos
    
    # Construir contexto con TODOS los resultados
    contexto_tools = "\n\n".join([
        f"Resultado de {nombre}:\n{resultado[:400]}"
        for nombre, resultado in tools_ejecutadas
    ])
    
    mensajes.append({"role": "assistant", "content": respuesta})
    mensajes.append({
        "role": "user",
        "content": f"Resultados reales de las herramientas:\n{contexto_tools}\n\nResume todo para Luis de forma clara. Si necesitas ejecutar más herramientas, escríbelas."
    })
    
    # Segunda llamada

        respuesta_cruda = ollama.chat(
            model='llama3.2:3b',
            messages=[mensajes[0]] + mensajes[-4:],
            options={"num_predict": 300, "temperature": 0.5, "num_ctx": 2048},
            think=False
        )
        respuesta = limpiar(respuesta_cruda['message']['content'])

    mensajes.append({"role": "assistant", "content": respuesta})
    registrar(tarea, respuesta)
    print(f"\nYuna → {respuesta}\n")
    hablar(respuesta)
