import os
import re
import subprocess
import platform
from datetime import datetime
from tools.permisos import is_bash_allowed

def ejecutar_bash_seguro(comando: str) -> str:
    """Ejecuta comandos Bash simples previamente autorizados."""
    if not is_bash_allowed(comando):
        cmd = comando.strip().split()[0] if comando.strip() else ""
        return (
            f"⛔ Comando '{cmd}' no permitido. "
            "Revisa la whitelist y las rutas autorizadas."
        )

    comando_limpio = comando.strip()

    if re.search(r"[;&|`$()<>]", comando_limpio):
        return "⛔ Detectados caracteres de shell injection."

    try:
        import shlex
        partes = shlex.split(comando_limpio)
    except ValueError:
        return "⛔ Sintaxis de comando invalida."

    if not partes:
        return "⛔ Comando vacio."

    if len(partes) > 5:
        return "⛔ Comando demasiado complejo. Maximo 5 argumentos."

    # Resolver ~ de forma independiente para cada argumento.
    partes = [os.path.expanduser(p) for p in partes]

    try:
        resultado = subprocess.run(
            partes,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
            cwd=os.path.expanduser("~/yuna"),
        )

        return (
            resultado.stdout.strip()
            or resultado.stderr.strip()
            or "✓ Sin salida"
        )

    except subprocess.TimeoutExpired:
        return "⏱ Timeout: el comando tardo demasiado"

    except Exception as e:
        return f"Error: {e}"

def notificar(titulo: str, mensaje: str) -> str:
    sistema = platform.system()
    try:
        if sistema == "Darwin":
            script = f'display notification "{mensaje}" with title "{titulo}"'
            os.system(f"osascript -e '{script}'")
        elif sistema == "Linux":
            os.system(f'notify-send "{titulo}" "{mensaje}"')
        else:
            return f"Notificacion: {titulo} - {mensaje}"
        return f"✓ Notificacion enviada: {titulo}"
    except Exception as e:
        return f"⚠ Error notificando: {e}"

def crear_archivo(ruta: str, contenido: str) -> str:
    ruta = os.path.expanduser(ruta)
    ruta_abs = os.path.abspath(ruta)
    home_abs = os.path.abspath(os.path.expanduser("~"))
    if not (ruta_abs.startswith(home_abs) or ruta_abs.startswith("/tmp")):
        return f"⛔ Ruta no permitida: {ruta}. Solo dentro de ~/ o /tmp/"
    if os.path.exists(ruta_abs):
        backup = ruta_abs + ".bak"
        os.rename(ruta_abs, backup)
    os.makedirs(os.path.dirname(ruta_abs) if os.path.dirname(ruta_abs) else ".", exist_ok=True)
    with open(ruta_abs, "w", encoding="utf-8") as f:
        f.write(contenido)
    return f"✓ Archivo creado: {ruta}"

def info_sistema() -> str:
    try:
        disco = subprocess.run(["df", "-h", os.path.expanduser("~")], capture_output=True, text=True).stdout.strip()
        fecha = datetime.now().strftime("%A %d de %B, %Y — %H:%M")
        return f"📅 {fecha}\n💾 Disco:\n{disco}"
    except Exception as e:
        return f"Error obteniendo info: {e}"
