from enum import Enum
import logging

logger = logging.getLogger(__name__)

class PermissionLevel(Enum):
    SAFE = "safe"
    CONFIRM = "confirm"
    DANGEROUS = "dangerous"

_PERMISSIONS = {
    "buscar_archivos": PermissionLevel.SAFE,
    "listar_recientes": PermissionLevel.SAFE,
    "leer_texto": PermissionLevel.SAFE,
    "leer_excel": PermissionLevel.SAFE,
    "leer_csv": PermissionLevel.SAFE,
    "leer_pdf": PermissionLevel.SAFE,
    "buscar_web": PermissionLevel.SAFE,
    "precio_activo": PermissionLevel.SAFE,
    "noticias_financieras_mx": PermissionLevel.SAFE,
    "info_sistema": PermissionLevel.SAFE,
    "consultar_memoria": PermissionLevel.SAFE,
    "escribir_memoria": PermissionLevel.SAFE,
    "notificar": PermissionLevel.SAFE,
    "organizar_archivos": PermissionLevel.CONFIRM,
    "crear_archivo": PermissionLevel.CONFIRM,
    "ejecutar_bash_seguro": PermissionLevel.CONFIRM,
}

_BASH_WHITELIST = {"ls", "cat", "echo", "pwd", "head", "tail", "grep", "find", "wc", "date", "du", "df", "top", "ps", "lsof", "uname", "uptime", "whoami", "which"}

def check_permission(tool_name: str) -> PermissionLevel:
    perm = _PERMISSIONS.get(tool_name, PermissionLevel.DANGEROUS)
    logger.info(f"Permiso consultado: {tool_name} -> {perm.value}")
    return perm

def is_bash_allowed(comando: str) -> bool:
    """Valida comandos Bash simples y restringe el acceso a rutas sensibles."""

    import re
    import shlex
    from pathlib import Path

    if not comando or not comando.strip():
        return False

    comando = comando.strip()

    # Nunca permitir operadores o construcciones del shell.
    if re.search(r"[;&|`$()<>]", comando):
        logger.warning(f"Bash bloqueado por operador shell: {comando}")
        return False

    try:
        partes = shlex.split(comando)
    except ValueError:
        logger.warning(f"Bash bloqueado por sintaxis invalida: {comando}")
        return False

    if not partes:
        return False

    cmd = partes[0]

    if cmd not in _BASH_WHITELIST:
        logger.warning(f"Bash bloqueado: {comando}")
        return False

    home = Path.home().resolve()
    yuna = (home / "yuna").resolve()
    downloads = (home / "Downloads").resolve()
    desktop = (home / "Desktop").resolve()
    documents = (home / "Documents").resolve()
    pictures = (home / "Pictures").resolve()
    movies = (home / "Movies").resolve()
    music = (home / "Music").resolve()
    tmp = Path("/tmp").resolve()

    root = Path("/").resolve()

    rutas_sensibles = {
        Path("/etc").resolve(),
        Path("/System").resolve(),
        Path("/private").resolve(),
        Path("/var").resolve(),
        (home / ".ssh").resolve(),
        (home / ".aws").resolve(),
        (home / ".config").resolve(),
    }

    def ruta_permitida(valor: str) -> bool:
        """Comprueba que una ruta quede dentro de un directorio autorizado."""

        ruta = Path(valor).expanduser()

        # Las rutas relativas se interpretan respecto al workspace de Yuna.
        if not ruta.is_absolute():
            ruta = yuna / ruta

        try:
            ruta = ruta.resolve()
        except OSError:
            return False

        # Nunca permitir la raiz del sistema ni rutas sensibles.
        if ruta == root:
            return False

        for sensible in rutas_sensibles:
            try:
                ruta.relative_to(sensible)
                return False
            except ValueError:
                pass

        # Directorios de trabajo autorizados.
        for base in (
            yuna,
            downloads,
            desktop,
            documents,
            pictures,
            movies,
            music,
            tmp,
        ):
            try:
                ruta.relative_to(base)
                return True
            except ValueError:
                pass

        return False

    # Argumentos que parecen rutas deben permanecer dentro
    # de los directorios autorizados.
    for argumento in partes[1:]:
        if argumento.startswith("-"):
            continue

        # Argumentos de grep/find pueden ser patrones, no rutas.
        if cmd in {"grep", "find"} and argumento.startswith("*"):
            continue

        if not ruta_permitida(argumento):
            logger.warning(
                f"Bash bloqueado por ruta no permitida: {comando}"
            )
            return False

    return True

def confirm_user(tool_name: str, args: dict) -> bool:
    print(f"\n⚠ Confirmacion: {tool_name}({args})")
    resp = input("¿Ejecutar? (s/n) -> ").strip().lower()
    logger.info(f"Confirmacion usuario para {tool_name}: {resp}")
    return resp == "s"
