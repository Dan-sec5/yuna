"""
yuna/core.py — Módulo central de Yuna
Funciones compartidas, wrapper de Ollama y utilidades.
"""
import os
import re
import subprocess
import threading
from datetime import datetime
import ollama

# ─── Rutas ──────────────────────────────────────────────────
MEMORIA_PATH = os.path.expanduser("~/yuna/memoria.txt")
BITACORA_PATH = os.path.expanduser("~/yuna/bitacora.txt")

# ─── Configuración global ───────────────────────────────────
MODELO_DEFAULT = "qwen3:8b"
MAX_VOZ_CHARS = 300

# ─── Memoria ────────────────────────────────────────────────
def cargar_memoria():
    """Carga el contenido de memoria.txt o retorna cadena vacía."""
    if os.path.exists(MEMORIA_PATH):
        with open(MEMORIA_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def guardar_aprendizaje(mensajes, max_intercambios=2):
    """Extrae aprendizajes de la conversación y los guarda en memoria."""
    intercambios = [m for m in mensajes if m.get("role") == "user"]
    if len(intercambios) < max_intercambios:
        return

    print("\n🧠 Guardando aprendizajes de esta sesión...")
    resumen = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in mensajes[-8:] if m.get("role") in ["user", "assistant"]
    ])
    prompt = f"""Analiza esta conversación entre Luis y Yuna.
Extrae MÁXIMO 3 aprendizajes concretos y útiles sobre Luis:
preferencias, tareas que hizo, temas que le interesan o datos nuevos sobre su trabajo.
Formato: una línea por aprendizaje, empezando con "-"
Sin explicaciones, solo los puntos.

CONVERSACIÓN:
{resumen}"""
    try:
        resultado = llamar_ollama(
            [{"role": "user", "content": prompt}],
            num_predict=150, temperature=0.3
        )
        aprendizajes = limpiar(resultado['message']['content'].strip())
        if aprendizajes:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(MEMORIA_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n\n--- Sesión {fecha} ---\n")
                f.write(aprendizajes)
            print(f"✓ Memoria actualizada:\n{aprendizajes}")
    except Exception as e:
        print(f"⚠ No se pudo guardar aprendizaje: {e}")

# ─── Limpieza de respuestas ─────────────────────────────────
def limpiar(texto):
    """Elimina tags de thinking y limpia espacios."""
    texto = re.sub(r'\<think\>.*?\</think\>', '', texto, flags=re.DOTALL)
    if "...done thinking." in texto:
        texto = texto.split("...done thinking.")[-1]
    return texto.strip()

# ─── Voz ────────────────────────────────────────────────────
def hablar(texto, max_chars=None):
    """Convierte texto a voz con DaliaNeural (async)."""
    max_chars = max_chars or MAX_VOZ_CHARS
    texto = texto[:max_chars]
    def _hablar():
        subprocess.run([
            "edge-tts", "--voice", "es-MX-DaliaNeural",
            "--text", texto,
            "--write-media", "/tmp/yuna_voz.mp3"
        ], capture_output=True)
        os.system("afplay /tmp/yuna_voz.mp3")
    threading.Thread(target=_hablar, daemon=True).start()

# ─── Bitácora ───────────────────────────────────────────────
def registrar(usuario, agente):
    """Registra un intercambio en la bitácora."""
    os.makedirs(os.path.dirname(BITACORA_PATH), exist_ok=True)
    with open(BITACORA_PATH, "a", encoding="utf-8") as f:
        hora = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"[{hora}] Luis: {usuario}\n")
        f.write(f"[{hora}] Yuna: {agente}\n\n")

# ─── Wrapper robusto de Ollama ──────────────────────────────
def llamar_ollama(mensajes, modelo=None, max_reintentos=2, **opciones):
    """
    Wrapper universal para llamadas a Ollama.
    Maneja: modelo no encontrado, timeout, errores de conexión, reintentos.
    """
    modelo = modelo or MODELO_DEFAULT
    opciones_default = {
        "num_predict": 400,
        "temperature": 0.5,
        "num_ctx": 2048
    }
    opciones_default.update(opciones)

    for intento in range(max_reintentos + 1):
        try:
            return ollama.chat(
                model=modelo,
                messages=mensajes,
                options=opciones_default
            )
        except ollama.ResponseError as e:
            error_msg = str(e).lower()
            if "not found" in error_msg:
                return {
                    "message": {
                        "content": f"⚠️ El modelo '{modelo}' no está disponible. Ejecuta: ollama pull {modelo}"
                    }
                }
            if intento < max_reintentos:
                import time
                time.sleep(1)
            else:
                return {
                    "message": {
                        "content": f"⚠️ Error de conexión con Ollama: {e}. ¿Está corriendo el servicio? (ollama serve)"
                    }
                }
        except Exception as e:
            return {
                "message": {
                    "content": f"⚠️ Error inesperado: {e}"
                }
            }

# ─── Parsing de herramientas ────────────────────────────────
def parsear_argumentos(args_str):
    """Extrae argumentos de una llamada TOOL: de forma robusta."""
    args = []
    if not args_str:
        return args
    # Soporta: "string", 'string', 123
    for arg in re.findall(r'"([^"]*?)"|\'([^\']*?)\'|(\d+)', args_str):
        valor = arg[0] or arg[1] or arg[2]
        if valor.isdigit():
            args.append(int(valor))
        else:
            args.append(valor)
    return args
