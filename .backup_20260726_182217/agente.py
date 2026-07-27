import os
import re
import sys
import threading
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/yuna"))
from core import cargar_memoria, limpiar, hablar, registrar, llamar_ollama, parsear_argumentos
from tools.archivos import buscar_archivos, listar_recientes, organizar_por_tipo
from tools.datos import leer_excel, leer_csv, leer_pdf
from tools.web import buscar_web, precio_activo, noticias_financieras_mx
from tools.sistema import ejecutar_bash, notificar, info_sistema

memoria = cargar_memoria()

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
- Puedes escribir múltiples TOOL: si la tarea requiere varios pasos
- Después de ver los resultados, dáselo a Luis de forma clara y concisa
- Habla en español mexicano
- NUNCA inventes resultados — solo usa lo que retorna la herramienta"""


def detectar_y_ejecutar_tools(respuesta):
    """Detecta TODAS las líneas TOOL: y las ejecuta en orden."""
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

        args = parsear_argumentos(args_str)
        print(f"\n⚙ Ejecutando: {nombre}({args_str})")
        try:
            resultado = HERRAMIENTAS[nombre](*args) if args else HERRAMIENTAS[nombre]()
            resultados.append((nombre, str(resultado)))
        except Exception as e:
            resultados.append((nombre, f"Error: {e}"))

    return resultados


# ─── Loop principal ─────────────────────────────────────────
mensajes = [{"role": "system", "content": SYSTEM_PROMPT}]
MAX_ITERACIONES = 5

print("\n🤖 Yuna Agente — Modo autónomo activado")
print("(escribe 'salir' para terminar)\n")

saludo = "Hola Luis, modo agente activo. ¿Qué necesitas hacer hoy?"
print(f"Yuna → {saludo}\n")
hablar(saludo)
mensajes.append({"role": "assistant", "content": saludo})

while True:
    tarea = input("Luis → ").strip()
    if tarea.lower() == "salir":
        despedida = "Hasta luego Luis."
        print(f"\nYuna → {despedida}")
        hablar(despedida)
        break

    mensajes.append({"role": "user", "content": tarea})

    # Contexto: system + últimos 6 mensajes
    contexto = [mensajes[0]] + mensajes[-6:]

    respuesta_cruda = llamar_ollama(
        contexto,
        num_predict=400, temperature=0.3, num_ctx=2048
    )
    respuesta = limpiar(respuesta_cruda['message']['content'])

    # ─── Loop de herramientas ───────────────────────────────
    iteracion = 0
    while iteracion < MAX_ITERACIONES:
        tools_ejecutadas = detectar_y_ejecutar_tools(respuesta)

        if not tools_ejecutadas:
            break  # No hay más herramientas, terminamos

        # Mostrar resultados
        print(f"\n📊 Resultados ({len(tools_ejecutadas)} herramienta(s)):")
        for nombre, resultado in tools_ejecutadas:
            print(f"  [{nombre}]: {resultado[:300]}...")

        # Construir contexto con TODOS los resultados
        contexto_tools = "\n\n".join([
            f"Resultado de {nombre}:\n{resultado[:500]}"
            for nombre, resultado in tools_ejecutadas
        ])

        mensajes.append({"role": "assistant", "content": respuesta})
        mensajes.append({
            "role": "user",
            "content": f"Resultados reales de las herramientas:\n{contexto_tools}\n\n"
                       f"Resume todo para Luis de forma clara. Si necesitas ejecutar más herramientas, escríbelas."
        })

        # Segunda llamada con resultados
        contexto = [mensajes[0]] + mensajes[-6:]
        respuesta_cruda = llamar_ollama(
            contexto,
            num_predict=300, temperature=0.5, num_ctx=2048
        )
        respuesta = limpiar(respuesta_cruda['message']['content'])
        iteracion += 1

    if iteracion >= MAX_ITERACIONES:
        respuesta += "\n\n(Alcancé el límite de iteraciones. Si necesitas más pasos, dime la siguiente acción.)"

    mensajes.append({"role": "assistant", "content": respuesta})
    registrar(tarea, respuesta)
    print(f"\nYuna → {respuesta}\n")
    hablar(respuesta)
