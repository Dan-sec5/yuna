"""
interface/actions.py

Capa de acciones de la interfaz de Yuna.

La GUI no debe conocer cómo se arrancan los módulos internos de Yuna.
Si mañana cambia app.py, el launcher, el modelo o la forma de abrir una
sesión, idealmente solo se modifica este archivo.
"""

import os
import subprocess
import threading
from datetime import datetime


YUNA_DIR = os.path.expanduser("~/yuna")


def abrir_terminal(comando: str) -> None:
    """Ejecuta un comando de Yuna en una nueva sesión de Terminal en macOS."""

    def _run():
        script = (
            'tell application "Terminal" to do script "'
            + comando.replace('"', '\\"')
            + '"'
        )

        subprocess.run(
            ["osascript", "-e", script],
            check=False
        )

    threading.Thread(
        target=_run,
        daemon=True
    ).start()


def abrir_chat() -> None:
    """Abre el chat conversacional de Yuna."""
    abrir_terminal(
        f"cd {YUNA_DIR} && python3 app.py chat"
    )


def abrir_agente() -> None:
    """Abre el agente autónomo de Yuna."""
    abrir_terminal(
        f"cd {YUNA_DIR} && python3 app.py agent"
    )


def abrir_aprendizaje() -> None:
    """Abre el módulo de aprendizaje de Yuna."""
    abrir_terminal(
        f"cd {YUNA_DIR} && python3 aprender.py"
    )


def guardar_bitacora() -> None:
    """Archiva la bitácora actual como una sesión fechada."""

    bitacora = os.path.join(
        YUNA_DIR,
        "bitacora.txt"
    )

    historial_dir = os.path.join(
        YUNA_DIR,
        "historial"
    )

    os.makedirs(
        historial_dir,
        exist_ok=True
    )

    if (
        not os.path.exists(bitacora)
        or os.path.getsize(bitacora) == 0
    ):
        return

    fecha = datetime.now().strftime(
        "%Y-%m-%d_%H-%M"
    )

    destino = os.path.join(
        historial_dir,
        f"sesion_{fecha}.txt"
    )

    with open(
        bitacora,
        "r",
        encoding="utf-8"
    ) as src:
        contenido = src.read()

    with open(
        destino,
        "w",
        encoding="utf-8"
    ) as dst:
        dst.write(contenido)

    open(
        bitacora,
        "w",
        encoding="utf-8"
    ).close()


def detener_modelo(
    modelo: str = "qwen3:8b"
) -> None:
    """Detiene el modelo local cuando Yuna se cierra."""

    subprocess.run(
        ["ollama", "stop", modelo],
        capture_output=True,
        check=False
    )


def cerrar_terminales_yuna() -> None:
    """Cierra pestañas de Terminal cuyo título contenga 'yuna'."""

    script = """
tell application "Terminal"
    set windowList to every window

    repeat with w in windowList
        set tabList to every tab of w

        repeat with t in tabList
            set cmd to custom title of t

            if cmd contains "yuna" then
                close t
            end if
        end repeat
    end repeat
end tell
"""

    subprocess.run(
        ["osascript", "-e", script],
        check=False
    )


def cerrar_yuna() -> None:
    """Ejecuta el cierre completo de Yuna."""

    guardar_bitacora()
    detener_modelo()
    cerrar_terminales_yuna()
