"""
interface/voice.py

Voz de Yuna con edge-tts.
Configuración centralizada — no duplicar hablar() en otros módulos.
"""
import os
import subprocess
import threading
from config import get

# FIX: 300 chars cortaba respuestas largas del agente.
# 800 permite leer respuestas completas de ~2-3 párrafos cortos.
MAX_VOZ_CHARS = get("voice.max_chars", 800)
VOICE = get("voice.voice", "es-MX-DaliaNeural")


def hablar(texto: str, max_chars: int = None):
    """Convierte texto a voz con edge-tts (async, no bloquea)."""
    max_chars = max_chars or MAX_VOZ_CHARS
    texto = str(texto)[:max_chars]

    def _hablar():
        mp3_path = "/tmp/yuna_voz.mp3"

        # Limpiar archivo anterior
        if os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
            except OSError:
                pass

        # Generar audio
        try:
            result = subprocess.run(
                ["edge-tts", "--voice", VOICE, "--text", texto,
                 "--write-media", mp3_path],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return  # Falló TTS, no interrumpir el flujo
        except Exception:
            return

        # Verificar archivo generado
        if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) < 512:
            return

        # Reproducir según SO
        try:
            sistema = os.uname().sysname if os.name == 'posix' else 'Windows'
            if sistema == 'Darwin':
                subprocess.run(["afplay", mp3_path],
                               capture_output=True, timeout=120)
            elif sistema == 'Linux':
                subprocess.run(["mpg123", "-q", mp3_path],
                               capture_output=True, timeout=120)
            else:
                os.startfile(mp3_path)
        except Exception:
            pass

    threading.Thread(target=_hablar, daemon=True).start()


def escuchar(duracion: int = 5) -> str:
    """Graba audio y transcribe con Whisper (requiere openai-whisper)."""
    try:
        import whisper
    except ImportError:
        return "⚠ whisper no instalado: pip install openai-whisper"

    wav_path = "/tmp/yuna_mic.wav"

    try:
        subprocess.run(
            ["sox", "-d", wav_path, "trim", "0", str(duracion)],
            capture_output=True, timeout=duracion + 2,
        )
    except Exception:
        try:
            subprocess.run(
                ["ffmpeg", "-f", "avfoundation", "-i", ":0",
                 "-t", str(duracion), wav_path, "-y"],
                capture_output=True, timeout=duracion + 2,
            )
        except Exception as e:
            return f"⚠ Error grabando: {e}"

    if not os.path.exists(wav_path):
        return "⚠ No se grabó audio"

    try:
        model = whisper.load_model("base")
        result = model.transcribe(wav_path, language="es")
        return result["text"].strip()
    except Exception as e:
        return f"⚠ Error transcribiendo: {e}"
