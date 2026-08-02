from tools.archivos import (
    buscar_archivos, listar_recientes, organizar_por_tipo, leer_texto
)
from tools.datos import leer_excel, leer_csv, leer_pdf
from tools.web import buscar_web, precio_activo, noticias_financieras_mx
from tools.sistema import info_sistema, notificar, crear_archivo, ejecutar_bash_seguro
from memory.manager import consultar_memoria, escribir_memoria

TOOLS = {
    "buscar_archivos": buscar_archivos,
    "listar_recientes": listar_recientes,
    "organizar_archivos": organizar_por_tipo,
    "leer_texto": leer_texto,
    "leer_excel": leer_excel,
    "leer_csv": leer_csv,
    "leer_pdf": leer_pdf,
    "buscar_web": buscar_web,
    "precio_activo": precio_activo,
    "noticias_financieras_mx": noticias_financieras_mx,
    "info_sistema": info_sistema,
    "notificar": notificar,
    "crear_archivo": crear_archivo,
    "consultar_memoria": consultar_memoria,
    "escribir_memoria": escribir_memoria,
    "ejecutar_bash_seguro": ejecutar_bash_seguro,
}

def get_tool(name: str):
    return TOOLS.get(name)

def list_tools():
    return list(TOOLS.keys())
