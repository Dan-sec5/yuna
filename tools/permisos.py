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
    if not comando or not comando.strip():
        return False
    cmd = comando.strip().split()[0]
    allowed = cmd in _BASH_WHITELIST
    if not allowed:
        logger.warning(f"Bash bloqueado: {comando}")
    return allowed

def confirm_user(tool_name: str, args: dict) -> bool:
    print(f"\n⚠ Confirmacion: {tool_name}({args})")
    resp = input("¿Ejecutar? (s/n) -> ").strip().lower()
    logger.info(f"Confirmacion usuario para {tool_name}: {resp}")
    return resp == "s"
