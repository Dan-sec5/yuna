import os
import subprocess
from datetime import datetime

def ejecutar_bash(comando, confirmar=True, timeout=30):
    if confirmar:
        print(f"📋 Comando: {comando}")
        resp = input("¿Ejecuto? (s/n) → ")
        if resp.lower() != "s":
            return "Cancelado por el usuario."
    
    try:
        resultado = subprocess.run(
            comando, shell=True, capture_output=True, text=True, timeout=timeout
        )
        salida = resultado.stdout.strip()
        error = resultado.stderr.strip()
        if error:
            return f"⚠ Error: {error}"
        return salida if salida else "✓ Ejecutado sin salida"
    except subprocess.TimeoutExpired:
        return f"⏱ El comando excedió {timeout} segundos y fue cancelado."

def notificar(titulo, mensaje):
    """Muestra notificación nativa de macOS"""
    script = f'display notification "{mensaje}" with title "{titulo}"'
    os.system(f"osascript -e '{script}'")
    return f"✓ Notificación enviada: {titulo}"

def crear_archivo(ruta, contenido):
    """Crea un archivo con contenido dado"""
    ruta = os.path.expanduser(ruta)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    return f"✓ Archivo creado: {ruta}"

def info_sistema():
    """Retorna información básica del sistema"""
    uso_disco = subprocess.run(
        "df -h ~", shell=True, capture_output=True, text=True
    ).stdout.strip()
    memoria = subprocess.run(
        "memory_pressure | head -1", shell=True, capture_output=True, text=True
    ).stdout.strip()
    fecha = datetime.now().strftime("%A %d de %B, %Y — %H:%M")
    return f"📅 {fecha}\n💾 Disco:\n{uso_disco}\n🧠 {memoria}"
