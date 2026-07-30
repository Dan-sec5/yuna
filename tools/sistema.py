import os
import subprocess
from datetime import datetime
from tools.permisos import is_bash_allowed

def ejecutar_bash_seguro(comando: str) -> str:
    """Ejecuta solo comandos de la lista blanca"""
    if not is_bash_allowed(comando):
        cmd = comando.strip().split()[0]
        return f"⛔ Comando '{cmd}' no permitido. Permitidos: ls, cat, echo, pwd, head, tail, grep, find, wc, date, du, df"
    try:
        resultado = subprocess.run(
            comando, shell=True, capture_output=True, text=True, timeout=10
        )
        return resultado.stdout.strip() or resultado.stderr.strip() or "✓ Sin salida"
    except subprocess.TimeoutExpired:
        return "⏱ Timeout: el comando tardó demasiado"
    except Exception as e:
        return f"Error: {e}"

def notificar(titulo: str, mensaje: str) -> str:
    script = f'display notification "{mensaje}" with title "{titulo}"'
    os.system(f"osascript -e '{script}'")
    return f"✓ Notificación enviada: {titulo}"

def crear_archivo(ruta: str, contenido: str) -> str:
    ruta = os.path.expanduser(ruta)
    os.makedirs(os.path.dirname(ruta) if os.path.dirname(ruta) else ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    return f"✓ Archivo creado: {ruta}"

def info_sistema() -> str:
    disco = subprocess.run("df -h ~", shell=True, capture_output=True, text=True).stdout.strip()
    fecha = datetime.now().strftime("%A %d de %B, %Y — %H:%M")
    return f"📅 {fecha}\n💾 Disco:\n{disco}"
