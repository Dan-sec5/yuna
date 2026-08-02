import os
import glob
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def buscar_archivos(patron: str = "*", carpeta: str = "~/Downloads") -> list:
    carpeta = os.path.expanduser(carpeta)
    if not os.path.exists(carpeta):
        return []
    resultados = glob.glob(os.path.join(carpeta, patron))
    return sorted(resultados, key=os.path.getmtime, reverse=True)

def listar_recientes(carpeta: str = "~/Downloads", dias: int = 7) -> list:
    carpeta = os.path.expanduser(carpeta)
    dias = int(dias)
    if not os.path.exists(carpeta):
        return []
    limite = datetime.now() - timedelta(days=dias)
    archivos = []
    for f in os.listdir(carpeta):
        ruta = os.path.join(carpeta, f)
        if os.path.isfile(ruta):
            try:
                modificado = datetime.fromtimestamp(os.path.getmtime(ruta))
                if modificado > limite:
                    archivos.append({
                        "nombre": f,
                        "ruta": ruta,
                        "modificado": modificado.strftime("%Y-%m-%d %H:%M"),
                        "tamano_kb": round(os.path.getsize(ruta) / 1024, 1)
                    })
            except OSError:
                continue
    return sorted(archivos, key=lambda x: x["modificado"], reverse=True)

def organizar_por_tipo(carpeta_origen: str = "~/Downloads") -> list:
    carpeta = os.path.expanduser(carpeta_origen)
    if not os.path.exists(carpeta):
        return ["Error: carpeta no existe"]
    destinos = {
        "PDF": ["pdf"],
        "Excel": ["xlsx", "xls"],
        "Datos": ["csv", "json"],
        "Imagenes": ["png", "jpg", "jpeg", "gif", "webp"],
        "Documentos": ["docx", "doc", "txt", "md"],
        "Codigo": ["py", "js", "ts", "html", "css", "json"],
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
                if os.path.exists(nuevo):
                    base, ext = os.path.splitext(archivo)
                    nuevo = os.path.join(destino, f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
                try:
                    shutil.move(ruta, nuevo)
                    movidos.append(f"{archivo} -> {carpeta_destino}/")
                except Exception as e:
                    movidos.append(f"Error moviendo {archivo}: {e}")
                break
    return movidos

def leer_texto(ruta: str) -> str:
    """Lee un archivo de texto. Lanza FileNotFoundError si no existe."""
    ruta = os.path.expanduser(ruta)

    if not os.path.exists(ruta):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

    if os.path.getsize(ruta) > 10 * 1024 * 1024:
        raise ValueError("Archivo demasiado grande (>10MB)")

    with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
