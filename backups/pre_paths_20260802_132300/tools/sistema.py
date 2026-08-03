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
    """Crea archivos únicamente dentro de directorios autorizados."""

    from pathlib import Path

    home = Path.home().resolve()

    directorios_permitidos = [
        (home / "yuna").resolve(),
        (home / "Downloads").resolve(),
        (home / "Desktop").resolve(),
        (home / "Documents").resolve(),
        (home / "Pictures").resolve(),
        (home / "Movies").resolve(),
        (home / "Music").resolve(),
        Path("/tmp").resolve(),
    ]

    rutas_sensibles = [
        (home / ".ssh").resolve(),
        (home / ".aws").resolve(),
        (home / ".config").resolve(),
        Path("/etc").resolve(),
        Path("/System").resolve(),
        Path("/private").resolve(),
        Path("/var").resolve(),
    ]

    ruta_expandida = Path(os.path.expanduser(ruta))

    try:
        ruta_abs = ruta_expandida.resolve()
    except OSError:
        return f"⛔ Ruta no permitida: {ruta}"

    # macOS: /tmp normalmente resuelve físicamente a /private/tmp.
    tmp_real = Path("/tmp").resolve()

    try:
        ruta_abs.relative_to(tmp_real)
        es_tmp = True
    except ValueError:
        es_tmp = False

    # Bloquear rutas sensibles, excepto /private/tmp.
    if not es_tmp:
        for sensible in rutas_sensibles:
            try:
                ruta_abs.relative_to(sensible)
                return f"⛔ Ruta no permitida: {ruta}"
            except ValueError:
                pass

    # La ruta debe estar dentro de un directorio autorizado.
    permitida = False

    for base in directorios_permitidos:
        try:
            ruta_abs.relative_to(base)
            permitida = True
            break
        except ValueError:
            pass

    if not permitida:
        return (
            f"⛔ Ruta no permitida: {ruta}. "
            "Solo dentro de los directorios autorizados."
        )

    try:
        ruta_abs.parent.mkdir(parents=True, exist_ok=True)

        if ruta_abs.exists():
            backup = Path(str(ruta_abs) + ".bak")
            ruta_abs.replace(backup)

        ruta_abs.write_text(contenido, encoding="utf-8")

        return f"✓ Archivo creado: {ruta_abs}"

    except Exception as e:
        return f"⚠ Error creando archivo: {e}"

def info_sistema() -> str:
    try:
        disco = subprocess.run(["df", "-h", os.path.expanduser("~")], capture_output=True, text=True).stdout.strip()
        fecha = datetime.now().strftime("%A %d de %B, %Y — %H:%M")
        return f"📅 {fecha}\n💾 Disco:\n{disco}"
    except Exception as e:
        return f"Error obteniendo info: {e}"
