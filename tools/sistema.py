import os
import subprocess
import shlex
from datetime import datetime
from tools.permisos import is_bash_allowed

def ejecutar_bash_seguro(comando: str) -> str:
    """Ejecuta comando bash con whitelist de seguridad"""
    if not is_bash_allowed(comando):
        return f"❌ Comando no permitido: {comando}. Solo: {', '.join(['ls','cat','echo','pwd','head','tail','grep','find','wc'])}"
    
    try:
        parts = shlex.split(comando)
        result = subprocess.run(parts, capture_output=True, text=True, timeout=30)
        if result.stdout:
            return result.stdout.strip()
        if result.stderr:
            return f"⚠ {result.stderr.strip()}"
        return "✓ Ejecutado sin salida"
    except subprocess.TimeoutExpired:
        return f"⏱ Timeout: comando excedió 30 segundos"
    except Exception as e:
        return f"Error: {e}"

def ejecutar_bash(comando: str, confirmar: bool = True, timeout: int = 30) -> str:
    """Ejecuta comando bash arbitrario (PELIGROSO - requiere confirmación explícita)"""
    if confirmar:
        print(f"📋 Comando: {comando}")
        resp = input("¿Ejecuto? (s/n) → ")
        if resp.lower() != "s":
            return "Cancelado por el usuario."
    
    try:
        result = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.stdout:
            return result.stdout.strip()
        if result.stderr:
            return f"⚠ {result.stderr.strip()}"
        return "✓ Ejecutado sin salida"
    except subprocess.TimeoutExpired:
        return f"⏱ El comando excedió {timeout} segundos y fue cancelado."
    except Exception as e:
        return f"⚠ Error: {e}"

def notificar(titulo: str, mensaje: str) -> str:
    """Muestra notificación nativa de macOS"""
    script = f'display notification "{mensaje}" with title "{titulo}"'
    os.system(f"osascript -e '{script}'")
    return f"✓ Notificación enviada: {titulo}"

def crear_archivo(ruta: str, contenido: str) -> str:
    """Crea un archivo con contenido dado"""
    ruta = os.path.expanduser(ruta)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    return f"✓ Archivo creado: {ruta}"

def info_sistema() -> str:
    """Retorna información básica del sistema"""
    uso_disco = subprocess.run("df -h ~", shell=True, capture_output=True, text=True).stdout.strip()
    memoria = subprocess.run("memory_pressure | head -1", shell=True, capture_output=True, text=True).stdout.strip()
    fecha = datetime.now().strftime("%A %d de %B, %Y — %H:%M")
    return f"📅 {fecha}\n💾 Disco:\n{uso_disco}\n🧠 {memoria}"

def leer_texto(ruta: str) -> str:
    """Lee un archivo de texto"""
    ruta = os.path.expanduser(ruta)
    with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
