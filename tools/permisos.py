SAFE = {
    "buscar_archivos", "listar_recientes", "leer_excel", "leer_csv", "leer_pdf",
    "leer_texto", "buscar_web", "precio_activo", "noticias_financieras_mx",
    "info_sistema", "notificar", "consultar_memoria"
}

CONFIRM = {
    "organizar_archivos", "crear_archivo", "escribir_memoria"
}

DANGEROUS = {
    "ejecutar_bash_seguro"
}

BASH_WHITELIST = {
    "ls", "cat", "echo", "pwd", "head", "tail", "grep", "find", "wc", "df", "du", "ps"
}

def check_permission(tool_name: str) -> str:
    if tool_name in SAFE:
        return "SAFE"
    if tool_name in CONFIRM:
        return "CONFIRM"
    if tool_name in DANGEROUS:
        return "DANGEROUS"
    return "UNKNOWN"

def is_bash_allowed(command: str) -> bool:
    import shlex
    try:
        parts = shlex.split(command)
        return parts[0] in BASH_WHITELIST
    except:
        return False

def confirm_user(prompt: str) -> bool:
    from config import get
    if not get("permissions.confirmations", True):
        return True
    resp = input(f"{prompt} (s/n) → ").strip().lower()
    return resp in ("s", "si", "sí", "y", "yes")
