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

# ─── SYSTEM PROMPT V2 — Anti-alucinación ────────────────────
SYSTEM_PROMPT = f"""Eres Yuna, agente IA personal de Luis.

CONTEXTO: {memoria}

RUTAS DEL SISTEMA:
- Descargas: ~/Downloads
- Reportes: ~/Desktop/Reportes
- Datos Excel: ~/Desktop/Datos

REGLAS ABSOLUTAS (incumplir = fallo crítico):
1. NUNCA inventes nombres de archivos, rutas, datos ni resultados.
2. Si NO has ejecutado una herramienta, NO describas lo que "podría" haber.
3. Si una herramienta retorna error o vacío, dilo exactamente: "No encontré nada".
4. Habla en español mexicano. Sé directa y concisa.

PROTOCOLO DE DOS FASES:
FASE 1 — PLAN: El usuario pide algo que requiere datos del sistema. Tú SOLO escribes las herramientas necesarias. Cero texto explicativo. Cero saludos. Solo líneas TOOL:.
FASE 2 — RESPUESTA: Recibes los resultados REALES de las herramientas. Ahora sí respondes a Luis usando SOLO esos datos.

HERRAMIENTAS (escribe EXACTAMENTE así):
TOOL:buscar_archivos("*.xlsx", "~/Downloads")
TOOL:listar_recientes("~/Downloads", 7)
TOOL:leer_excel("~/Downloads/reporte.xlsx")
TOOL:leer_pdf("~/Downloads/documento.pdf")
TOOL:precio_activo("AAPL")
TOOL:buscar_web("noticias fideicomisos mexico")
TOOL:noticias_mx()
TOOL:info_sistema()
TOOL:organizar_archivos("~/Downloads")

EJEMPLO DE FLURO CORRECTO:
Luis: "¿Qué archivos tengo en Descargas?"
Yuna (Fase 1): TOOL:listar_recientes("~/Downloads", 30)
[Se ejecuta la herramienta y retorna datos reales]
Yuna (Fase 2): Encontré 3 archivos: reporte.xlsx, datos.csv y notas.txt.

EJEMPLO DE FLUJO PROHIBIDO:
Luis: "¿Qué archivos tengo en Descargas?"
Yuna: "Tienes archivo1.pdf, archivo2.mp4..." ← ¡INVENTADO! NUNCA hagas esto.

Si no sabes algo, di "No tengo acceso a eso aún, ¿quieres que busque?" y usa TOOL:."""


# ─── Palabras clave que indican necesidad de herramienta ────
PALABRAS_TOOL = [
    "busca", "encuentra", "lista", "muéstrame", "dime qué", "qué hay",
    "lee", "abre", "analiza", "revisa", "cuántos", "cuáles", "precio de",
    "noticias", "organiza", "info del sistema", "estado del sistema",
    "archivos", "excel", "pdf", "csv", "imágenes", "fotos", "descargas",
    "reporte", "carpeta", "directorio", "downloads", "desktop",
]

def requiere_herramienta(texto):
    """Detecta si la petición del usuario probablemente necesita una tool."""
    t = texto.lower()
    return any(p in t for p in PALABRAS_TOOL)


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

    # ─── FASE 1: Planificación (solo tools) ─────────────────
    # Si la tarea parece requerir herramienta, forzamos modo plan
    necesita_tool = requiere_herramienta(tarea)

    contexto = [mensajes[0]] + mensajes[-6:]

    respuesta_cruda = llamar_ollama(
        contexto,
        num_predict=400, temperature=0.2, num_ctx=2048  # temp bajo = más obediente
    )
    respuesta = limpiar(respuesta_cruda['message']['content'])

    # Si el usuario pidió algo que requiere tool pero el LLM no generó ninguna,
    # forzamos una segunda llamada con instrucción directa.
    tools_encontradas = detectar_y_ejecutar_tools(respuesta)

    if necesita_tool and not tools_encontradas:
        print("\n🔄 Forzando ejecución de herramienta...")
        mensajes.append({"role": "assistant", "content": respuesta})
        mensajes.append({
            "role": "user",
            "content": (
                "INSTRUCCIÓN DEL SISTEMA: La tarea anterior REQUIERE que uses una herramienta. "
                "NO respondas con texto. SOLO escribe la línea TOOL: necesaria. "
                "Ejemplo: TOOL:listar_recientes(\"~/Downloads\", 30)"
            )
        })
        contexto = [mensajes[0]] + mensajes[-4:]
        respuesta_cruda = llamar_ollama(
            contexto,
            num_predict=100, temperature=0.1, num_ctx=2048
        )
        respuesta = limpiar(respuesta_cruda['message']['content'])
        tools_encontradas = detectar_y_ejecutar_tools(respuesta)

    # ─── FASE 2: Ejecución de tools ─────────────────────────
    iteracion = 0
    while tools_encontradas and iteracion < MAX_ITERACIONES:
        iteracion += 1

        print(f"\n📊 Resultados ({len(tools_encontradas)} herramienta(s)):")
        for nombre, resultado in tools_encontradas:
            preview = resultado[:300].replace('\n', ' ')
            print(f"  [{nombre}]: {preview}...")

        contexto_tools = "\n\n".join([
            f"[RESULTADO REAL de {nombre}]:\n{resultado[:600]}"
            for nombre, resultado in tools_encontradas
        ])

        mensajes.append({"role": "assistant", "content": respuesta})
        mensajes.append({
            "role": "user",
            "content": (
                f"DATOS REALES DE LAS HERRAMIENTAS:\n{contexto_tools}\n\n"
                f"REGLA: Usa ÚNICAMENTE los datos de arriba. "
                f"NO inventes nombres, rutas ni descripciones. "
                f"Responde a Luis de forma clara y concisa en español mexicano."
            )
        })

        contexto = [mensajes[0]] + mensajes[-6:]
        respuesta_cruda = llamar_ollama(
            contexto,
            num_predict=300, temperature=0.4, num_ctx=2048
        )
        respuesta = limpiar(respuesta_cruda['message']['content'])

        # Verificar si quiere más herramientas
        tools_encontradas = detectar_y_ejecutar_tools(respuesta)

    if iteracion >= MAX_ITERACIONES:
        respuesta += "\n\n(Alcancé el límite de pasos. Si necesitas más, dime la siguiente acción.)"

    mensajes.append({"role": "assistant", "content": respuesta})
    registrar(tarea, respuesta)
    print(f"\nYuna → {respuesta}\n")
    hablar(respuesta)
