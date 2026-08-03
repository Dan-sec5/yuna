"""
Resolución centralizada de rutas de Yuna.

Responsabilidad:
- Conocer la raíz de Yuna.
- Resolver carpetas estándar del usuario.
- Permitir rutas personalizadas.
- Evitar rutas absolutas hardcodeadas dentro de Yuna.
"""

from pathlib import Path
import os


# ============================================================
# RAÍCES
# ============================================================

# config/paths.py
#       └── config/
#             └── paths.py
#
# parents[1] = raíz del proyecto Yuna

YUNA_ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()


# ============================================================
# ESTRUCTURA INTERNA DE YUNA
# ============================================================

YUNA_CONFIG = YUNA_ROOT / "config"
YUNA_CORE = YUNA_ROOT / "core"
YUNA_MEMORY = YUNA_ROOT / "memory"
YUNA_TOOLS = YUNA_ROOT / "tools"
YUNA_INTERFACE = YUNA_ROOT / "interface"
YUNA_DATA = YUNA_ROOT / "data"
YUNA_LOGS = YUNA_ROOT / "logs"
YUNA_HISTORY = YUNA_ROOT / "historial"


# ============================================================
# DIRECTORIOS DEL USUARIO
# ============================================================

USER_DIRECTORIES = {
    "home": HOME,
    "descargas": HOME / "Downloads",
    "downloads": HOME / "Downloads",

    "escritorio": HOME / "Desktop",
    "desktop": HOME / "Desktop",

    "documentos": HOME / "Documents",
    "documents": HOME / "Documents",

    "imagenes": HOME / "Pictures",
    "pictures": HOME / "Pictures",

    "musica": HOME / "Music",
    "music": HOME / "Music",

    "videos": HOME / "Movies",
    "movies": HOME / "Movies",
}


# ============================================================
# RESOLVER
# ============================================================

def resolve_user_path(path: str | Path) -> Path:
    """
    Convierte una ruta proporcionada por el usuario en una Path absoluta.

    Ejemplos:
        ~/Downloads
        ~/Desktop
        ~/Documents/reporte.xlsx
        /tmp/test.txt
    """

    return Path(os.path.expanduser(str(path))).resolve()


def resolve_location(location: str | Path) -> Path:
    """
    Resuelve una ubicación conocida o una ruta personalizada.

    Ejemplos:

        resolve_location("descargas")
        resolve_location("escritorio")
        resolve_location("imagenes")
        resolve_location("~/Proyectos")
        resolve_location("/tmp")
    """

    key = str(location).strip().lower()

    if key in USER_DIRECTORIES:
        return USER_DIRECTORIES[key]

    return resolve_user_path(location)


def get_user_directories() -> dict[str, Path]:
    """
    Devuelve las ubicaciones conocidas del usuario.
    """

    return USER_DIRECTORIES.copy()


def is_inside_yuna(path: str | Path) -> bool:
    """
    Determina si una ruta pertenece a la estructura interna de Yuna.
    """

    try:
        resolve_user_path(path).relative_to(YUNA_ROOT)
        return True
    except ValueError:
        return False


def ensure_yuna_directories() -> None:
    """
    Garantiza que las carpetas internas esenciales de Yuna existan.
    """

    directories = (
        YUNA_DATA,
        YUNA_LOGS,
        YUNA_HISTORY,
    )

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


__all__ = [
    "YUNA_ROOT",
    "YUNA_CONFIG",
    "YUNA_CORE",
    "YUNA_MEMORY",
    "YUNA_TOOLS",
    "YUNA_INTERFACE",
    "YUNA_DATA",
    "YUNA_LOGS",
    "YUNA_HISTORY",
    "HOME",
    "USER_DIRECTORIES",
    "resolve_user_path",
    "resolve_location",
    "get_user_directories",
    "is_inside_yuna",
    "ensure_yuna_directories",
]
