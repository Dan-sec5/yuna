from enum import Enum

class PermissionLevel(Enum):
    SAFE = "safe"
    CONFIRM = "confirm"
    DANGEROUS = "dangerous"

# Clasificación de herramientas por nivel de riesgo
_PERMISSIONS = {
    "buscar_archivos":        PermissionLevel.SAFE,
    "listar_recientes":       PermissionLevel.SAFE,
    "leer_texto":             PermissionLevel.SAFE,
    "leer_excel":             PermissionLevel.SAFE,
    "leer_csv":               PermissionLevel.SAFE,
    "leer_pdf":               PermissionLevel.SAFE,
    "buscar_web":             PermissionLevel.SAFE,
    "precio_activo":          PermissionLevel.SAFE,
    "noticias_financieras_mx":PermissionLevel.SAFE,
    "info_sistema":           PermissionLevel.SAFE,
    "consultar_memoria":      PermissionLevel.SAFE,
    "escribir_memoria":       PermissionLevel.SAFE,
    "notificar":              PermissionLevel.SAFE,
    "organizar_archivos":     PermissionLevel.CONFIRM,
    "crear_archivo":          PermissionLevel.CONFIRM,
    "ejecutar_bash_seguro":   PermissionLevel.CONFIRM,
}

_BASH_WHITELIST = {"ls", "cat", "echo", "pwd", "head", "tail", "grep", "find", "wc", "date", "du", "df"}

def check_permission(tool_name: str) -> PermissionLevel:
    return _PERMISSIONS.get(tool_name, PermissionLevel.DANGEROUS)

def is_bash_allowed(comando: str) -> bool:
    cmd = comando.strip().split()[0] if comando.strip() else ""
    return cmd in _BASH_WHITELIST

def confirm_user(tool_name: str, args: dict) -> bool:
    print(f"\n⚠ Confirmación: {tool_name}({args})")
    return input("¿Ejecutar? (s/n) → ").strip().lower() == "s"
