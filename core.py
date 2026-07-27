"""
yuna/core.py — Módulo central de Yuna
Funciones compartidas, wrapper de Ollama y utilidades.
"""
import os
import re
import subprocess
import threading
import time
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

# ─── Voz — Manejo robusto de edge-tts + afplay ──────────────
def hablar(texto, max_chars=None):
    """
    Convierte texto a voz con DaliaNeural (async).
    Si edge-tts o afplay fallan, continúa silenciosamente sin romper el programa.
    """
    max_chars = max_chars or MAX_VOZ_CHARS
    texto = texto[:max_chars]

    def _hablar():
        mp3_path = "/tmp/yuna_voz.mp3"

        # 1. Limpiar archivo anterior si existe
        if os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
            except:
                pass

        # 2. Generar audio con edge-tts
        try:
            result = subprocess.run(
                [
                    "edge-tts", "--voice", "es-MX-DaliaNeural",
                    "--text", texto,
                    "--write-media", mp3_path
                ],
                capture_output=True,
                text=True,
                timeout=15  # edge-tts no debería tardar más de 15s
            )
            if result.returncode != 0:
                print(f"⚠ edge-tts falló: {result.stderr.strip()}")
                return
        except subprocess.TimeoutExpired:
            print("⚠ edge-tts tardó demasiado, cancelado.")
            return
        except FileNotFoundError:
            print("⚠ edge-tts no está instalado. Instala: pip install edge-tts")
            return
        except Exception as e:
            print(f"⚠ Error generando audio: {e}")
            return

        # 3. Verificar que el archivo existe y tiene contenido
        if not os.path.exists(mp3_path):
            print("⚠ El archivo de audio no se generó.")
            return

        file_size = os.path.getsize(mp3_path)
        if file_size < 1024:  # Menos de 1KB = probablemente corrupto
            print(f"⚠ Archivo de audio demasiado pequeño ({file_size} bytes), posiblemente corrupto.")
            return

        # 4. Reproducir con afplay
        try:
            result = subprocess.run(
                ["afplay", mp3_path],
                capture_output=True,
                timeout=60
            )
            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
                if "wht?" in stderr or "AudioFileOpen failed" in stderr:
                    print("⚠ El archivo MP3 está corrupto (probablemente edge-tts falló silenciosamente).")
                else:
                    print(f"⚠ afplay falló: {stderr}")
        except subprocess.TimeoutExpired:
            print("⚠ afplay tardó demasiado, cancelado.")
        except FileNotFoundError:
            print("⚠ afplay no encontrado. Esto debería estar en macOS por defecto.")
        except Exception as e:
            print(f"⚠ Error reproduciendo audio: {e}")

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
    for arg in re.findall(r'"([^"]*?)"|\'([^\']*?)\'|(\d+)', args_str):
        valor = arg[0] or arg[1] or arg[2]
        if valor.isdigit():
            args.append(int(valor))
        else:
            args.append(valor)
    return args
