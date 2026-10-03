import os
import glob
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from config.paths import resolve_location

def buscar_archivos(
    patron: str = "*",
    carpeta: str = "home",
    metadata: bool = False
) -> list:
    """
    Busca archivos recursivamente.

    Admite:
    - patrones glob: *.py
    - nombres: agent.py
    - rutas relativas: core/executor.py
    - rutas absolutas
    - ubicaciones conocidas: home, descargas, yuna, etc.
    """

    carpeta_path = resolve_location(carpeta)

    if not carpeta_path.exists():
        return []

    patron = str(patron).strip()

    # --------------------------------------------------------
    # Ruta explícita relativa dentro de la carpeta
    # Ejemplo: core/executor.py + ~/yuna
    # --------------------------------------------------------
    ruta_relativa = carpeta_path / patron

    if ruta_relativa.exists() and ruta_relativa.is_file():
        resultados = [str(ruta_relativa.resolve())]

    else:
        resultados = glob.glob(
            os.path.join(str(carpeta_path), "**", patron),
            recursive=True
        )

    # Directorios internos que no deben considerarse parte
    # del árbol activo cuando se busca dentro de Yuna.
    exclusiones_yuna = {
        ".git",
        "__pycache__",
        "backups",
        "legacy",
    }

    carpeta_resuelta = carpeta_path.resolve()

    resultados = [
        ruta for ruta in resultados
        if os.path.isfile(ruta)
        and not (
            carpeta_resuelta == Path.home() / "yuna"
            and exclusiones_yuna.intersection(
                Path(ruta).resolve().relative_to(carpeta_resuelta).parts
            )
        )
    ]

    resultados = sorted(
        resultados,
        key=os.path.getmtime,
        reverse=True
    )

    if metadata:
        archivos = []

        for ruta in resultados:
            try:
                stat = os.stat(ruta)

                archivos.append({
                    "nombre": os.path.basename(ruta),
                    "ruta": ruta,
                    "tamano_kb": round(stat.st_size / 1024, 1),
                    "tamano_bytes": stat.st_size,
                    "modificado": datetime.fromtimestamp(
                        stat.st_mtime
                    ).strftime("%Y-%m-%d %H:%M")
                })

            except OSError:
                continue

        return archivos

    return resultados

def listar_recientes(carpeta: str = "home", dias: int = 7) -> list:
    carpeta = str(resolve_location(carpeta))
    dias = int(dias)

    if not os.path.exists(carpeta):
        return []

    limite = datetime.now() - timedelta(days=dias)
    archivos = []

    for ruta in Path(carpeta).rglob("*"):
        if not ruta.is_file():
            continue

        try:
            modificado = datetime.fromtimestamp(ruta.stat().st_mtime)

            if modificado > limite:
                archivos.append({
                    "nombre": ruta.name,
                    "ruta": str(ruta),
                    "modificado": modificado.strftime("%Y-%m-%d %H:%M"),
                    "tamano_kb": round(ruta.stat().st_size / 1024, 1)
                })

        except OSError:
            continue

    return sorted(
        archivos,
        key=lambda x: x["modificado"],
        reverse=True
    )

def organizar_por_tipo(carpeta_origen: str = "home") -> list:
    carpeta = str(resolve_location(carpeta_origen))
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


def detectar_descargas(carpeta: str = "descargas", dias: int = 30) -> list:
    """
    Detecta archivos que presentan metadata de descarga de macOS.

    Usa el atributo extendido com.apple.quarantine como evidencia
    de que macOS registró el archivo como procedente de una descarga.

    No todos los archivos descargados necesariamente conservan esta
    metadata, por lo que un resultado vacío NO significa que no hubo
    descargas.
    """
    import subprocess

    carpeta = str(resolve_location(carpeta))
    dias = max(0, int(dias))

    if not os.path.exists(carpeta):
        return []

    limite = datetime.now() - timedelta(days=dias)
    resultados = []

    for ruta in Path(carpeta).rglob("*"):
        if not ruta.is_file():
            continue

        try:
            proceso = subprocess.run(
                ["xattr", "-p", "com.apple.quarantine", str(ruta)],
                capture_output=True,
                text=True,
                timeout=2
            )

            if proceso.returncode != 0:
                continue

            valor = proceso.stdout.strip()

            if not valor:
                continue

            partes = valor.split(";")

            fecha_descarga = None

            # Formato habitual:
            # flags;timestamp;agent;uuid
            if len(partes) >= 2:
                try:
                    timestamp = int(partes[1], 16)
                    fecha_descarga = datetime.fromtimestamp(timestamp)
                except (ValueError, OSError, OverflowError):
                    fecha_descarga = None

            # Si podemos obtener fecha de descarga, filtramos por días.
            if fecha_descarga is not None:
                if fecha_descarga <= limite:
                    continue

                fecha_texto = fecha_descarga.strftime(
                    "%Y-%m-%d %H:%M"
                )
            else:
                # Tenemos evidencia de cuarentena, pero no fecha interpretable.
                fecha_texto = None

            stat = ruta.stat()

            resultados.append({
                "nombre": ruta.name,
                "ruta": str(ruta),
                "descargado": fecha_texto,
                "tamano_kb": round(stat.st_size / 1024, 1),
                "evidencia": "com.apple.quarantine"
            })

        except (OSError, subprocess.SubprocessError):
            continue

    return sorted(
        resultados,
        key=lambda x: x.get("descargado") or "",
        reverse=True
    )



def _trash_root() -> Path:
    """Papelera reversible interna de Yuna."""
    root = (Path.home() / "yuna" / ".trash").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _ruta_archivo_permitida(ruta: str) -> Path:
    """Permite archivos de Yuna y carpetas personales habituales, bloqueando rutas sensibles."""
    home = Path.home().resolve()
    candidato = Path(ruta).expanduser()

    if not candidato.is_absolute():
        candidato = home / "yuna" / candidato

    candidato = candidato.resolve()

    permitidas = [
        (home / "yuna").resolve(),
        (home / "Downloads").resolve(),
        (home / "Desktop").resolve(),
        (home / "Documents").resolve(),
        (home / "Pictures").resolve(),
        (home / "Movies").resolve(),
        (home / "Music").resolve(),
        Path("/tmp").resolve(),
    ]

    sensibles = [
        (home / ".ssh").resolve(),
        (home / ".aws").resolve(),
        (home / ".config").resolve(),
        (home / "Library").resolve(),
        Path("/etc").resolve(),
        Path("/System").resolve(),
        Path("/var").resolve(),
    ]

    tmp_real = Path("/tmp").resolve()
    try:
        candidato.relative_to(tmp_real)
        es_tmp = True
    except ValueError:
        es_tmp = False

    if not es_tmp:
        for base in sensibles:
            try:
                candidato.relative_to(base)
                raise PermissionError(f"Ruta sensible no permitida: {ruta}")
            except ValueError:
                pass

    for base in permitidas:
        try:
            candidato.relative_to(base)
            return candidato
        except ValueError:
            pass

    raise PermissionError(f"Ruta no permitida: {ruta}")


def eliminar_archivo(ruta: str) -> str:
    """
    Mueve un archivo a la papelera interna de Yuna.
    No elimina carpetas ni borra permanentemente.
    """
    import json
    import uuid

    origen = _ruta_archivo_permitida(ruta)

    if not origen.exists():
        return f"⚠ Archivo no encontrado: {origen}"
    if not origen.is_file():
        return "⛔ Solo se pueden eliminar archivos, no carpetas."

    trash = _trash_root()

    # Evitar intentar eliminar elementos que ya están en la papelera.
    try:
        origen.relative_to(trash)
        return "⛔ El archivo ya está dentro de la papelera de Yuna."
    except ValueError:
        pass

    token = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    destino = trash / f"{token}__{origen.name}"
    metadata = trash / f"{token}.json"

    try:
        shutil.move(str(origen), str(destino))
        metadata.write_text(
            json.dumps({
                "token": token,
                "nombre": origen.name,
                "ruta_original": str(origen),
                "ruta_papelera": str(destino),
                "eliminado": datetime.now().isoformat(timespec="seconds"),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return (
            f"✓ Archivo enviado a la papelera: {origen}\n"
            f"ID restauración: {token}"
        )
    except Exception as e:
        # Si se movió pero falló metadata, intentar devolverlo.
        try:
            if destino.exists() and not origen.exists():
                shutil.move(str(destino), str(origen))
        except Exception:
            pass
        return f"⚠ Error enviando archivo a papelera: {e}"


def restaurar_archivo(token: str) -> str:
    """Restaura un archivo eliminado por Yuna usando su ID de restauración."""
    import json

    token = str(token).strip()
    if not token or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in token):
        return "⛔ ID de restauración inválido."

    trash = _trash_root()
    metadata = trash / f"{token}.json"

    if not metadata.exists():
        return f"⚠ No existe un archivo eliminado con ID: {token}"

    try:
        info = json.loads(metadata.read_text(encoding="utf-8"))
        origen = Path(info["ruta_papelera"]).resolve()
        destino = _ruta_archivo_permitida(info["ruta_original"])

        try:
            origen.relative_to(trash)
        except ValueError:
            return "⛔ Metadata de papelera inválida."

        if not origen.exists():
            return "⚠ El archivo ya no está disponible en la papelera."

        if destino.exists():
            return (
                f"⛔ No se restauró porque ya existe un archivo en: {destino}. "
                "Renombra o mueve ese archivo primero."
            )

        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origen), str(destino))
        metadata.unlink(missing_ok=True)

        return f"✓ Archivo restaurado: {destino}"

    except Exception as e:
        return f"⚠ Error restaurando archivo: {e}"
