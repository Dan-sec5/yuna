import os
import glob
from datetime import datetime, timedelta
from pathlib import Path

def buscar_archivos(patron: str = "*", carpeta: str = "~/Downloads") -> list:
    """Busca archivos por patrón en una carpeta"""
    carpeta = os.path.expanduser(carpeta)
    resultados = glob.glob(os.path.join(carpeta, patron))
    return sorted(resultados, key=os.path.getmtime, reverse=True)

def listar_recientes(carpeta: str = "~/Downloads", dias: int = 7) -> list:
    """Lista archivos modificados en los últimos N días"""
    carpeta = os.path.expanduser(carpeta)
    dias = int(dias)
    limite = datetime.now() - timedelta(days=dias)
    archivos = []
    for f in os.listdir(carpeta):
        ruta = os.path.join(carpeta, f)
        if os.path.isfile(ruta):
            modificado = datetime.fromtimestamp(os.path.getmtime(ruta))
            if modificado > limite:
                archivos.append({
                    "nombre": f,
                    "ruta": ruta,
                    "modificado": modificado.strftime("%Y-%m-%d %H:%M"),
                    "tamaño_kb": round(os.path.getsize(ruta) / 1024, 1)
                })
    return sorted(archivos, key=lambda x: x["modificado"], reverse=True)

def organizar_por_tipo(carpeta_origen: str = "~/Downloads") -> list:
    """Organiza archivos por extensión en subcarpetas"""
    carpeta = os.path.expanduser(carpeta_origen)
    destinos = {
        "PDF": ["pdf"],
        "Excel": ["xlsx", "xls"],
        "Datos": ["csv", "json"],
        "Imágenes": ["png", "jpg", "jpeg", "gif", "webp"],
        "Documentos": ["docx", "doc", "txt", "md"],
        "Código": ["py", "js", "ts", "html", "css", "json"],
    }
    movidos = []
    for archivo in os.listdir(carpeta):
        ruta = os.path.join(carpeta, archivo)
        if not os.path.isfile(ruta):
            continue
        ext = archivo.split(".")[-1].lower()
        for carpeta_destino, extensiones in destinos.items():
            if ext in extensiones:
                destino = os.path.join(carpeta, carpeta_destino)
                os.makedirs(destino, exist_ok=True)
                nuevo = os.path.join(destino, archivo)
                os.rename(ruta, nuevo)
                movidos.append(f"{archivo} → {carpeta_destino}/")
                break
    return movidos

def leer_texto(ruta: str) -> str:
    """Lee un archivo de texto"""
    ruta = os.path.expanduser(ruta)
    with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
