import os
import subprocess
import threading
from config import get

MAX_VOZ_CHARS = get("voice.max_chars", 300)
VOICE = get("voice.voice", "es-MX-DaliaNeural")

def hablar(texto: str, max_chars: int = None):
    """Convierte texto a voz con edge-tts (async, no bloquea)"""
    max_chars = max_chars or MAX_VOZ_CHARS
    texto = texto[:max_chars]
    
    def _hablar():
        mp3_path = "/tmp/yuna_voz.mp3"
        
        # Limpiar archivo anterior
        if os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
            except:
                pass
        
        # Generar audio
        try:
            result = subprocess.run(
                ["edge-tts", "--voice", VOICE, "--text", texto, "--write-media", mp3_path],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                print(f"⚠ edge-tts falló: {result.stderr.strip()}")
                return
        except subprocess.TimeoutExpired:
            print("⚠ edge-tts tardó demasiado")
            return
        except FileNotFoundError:
            print("⚠ edge-tts no instalado: pip install edge-tts")
            return
        except Exception as e:
            print(f"⚠ Error generando audio: {e}")
            return
        
        # Verificar archivo
        if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) < 1024:
            print("⚠ Audio no generado o corrupto")
            return
        
        # Reproducir
        try:
            subprocess.run(["afplay", mp3_path], capture_output=True, timeout=60)
        except Exception as e:
            print(f"⚠ Error reproduciendo: {e}")
    
    threading.Thread(target=_hablar, daemon=True).start()

def escuchar(duracion: int = 5) -> str:
    """Graba audio y usa Whisper para transcribir (requiere whisper instalado)"""
    try:
        import whisper
    except ImportError:
        return "⚠ whisper no instalado: pip install openai-whisper"
    
    wav_path = "/tmp/yuna_mic.wav"
    
    # Grabar con sox o ffmpeg
    try:
        subprocess.run(
            ["sox", "-d", wav_path, "trim", "0", str(duracion)],
            capture_output=True, timeout=duracion + 2
        )
    except:
        try:
            subprocess.run(
                ["ffmpeg", "-f", "avfoundation", "-i", ":0", "-t", str(duracion), wav_path, "-y"],
                capture_output=True, timeout=duracion + 2
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
