import ast
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def _resolver_ruta(ruta: str) -> Path:
    p = Path(os.path.expanduser(str(ruta)))
    if not p.is_absolute():
        p = Path.home() / "yuna" / p
    return p.resolve()


def editar_archivo(
    ruta: str,
    operacion: str,
    contenido: str = "",
    buscar: str = "",
) -> dict:
    """
    Edita un archivo de texto existente con backup automático.

    Operaciones:
    - reemplazar_texto: sustituye una coincidencia única de `buscar` por `contenido`
    - insertar_despues: inserta `contenido` después de una coincidencia única de `buscar`
    - agregar: agrega `contenido` al final
    - sobrescribir: reemplaza el archivo completo por `contenido`
    """
    path = _resolver_ruta(ruta)

    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    if not path.is_file():
        raise ValueError(f"La ruta no es un archivo: {path}")
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Archivo demasiado grande (>10MB)")

    actual = path.read_text(encoding="utf-8")
    operacion = str(operacion).strip().lower()

    if operacion == "reemplazar_texto":
        if not buscar:
            raise ValueError("'buscar' es obligatorio para reemplazar_texto")
        coincidencias = actual.count(buscar)
        if coincidencias == 0:
            raise ValueError("No se encontró el texto indicado")
        if coincidencias > 1:
            raise ValueError(
                f"El texto aparece {coincidencias} veces; usa un fragmento más específico"
            )
        nuevo = actual.replace(buscar, contenido, 1)

    elif operacion == "insertar_despues":
        if not buscar:
            raise ValueError("'buscar' es obligatorio para insertar_despues")
        coincidencias = actual.count(buscar)
        if coincidencias == 0:
            raise ValueError("No se encontró el texto indicado")
        if coincidencias > 1:
            raise ValueError(
                f"El texto aparece {coincidencias} veces; usa un fragmento más específico"
            )
        nuevo = actual.replace(buscar, buscar + contenido, 1)

    elif operacion == "agregar":
        nuevo = actual + contenido

    elif operacion == "sobrescribir":
        nuevo = contenido

    else:
        raise ValueError(
            "Operación inválida. Usa reemplazar_texto, insertar_despues, agregar o sobrescribir"
        )

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.bak.{marca}")
    backup.write_text(actual, encoding="utf-8")

    tmp = path.with_name(f".{path.name}.yuna_tmp")
    tmp.write_text(nuevo, encoding="utf-8")
    tmp.replace(path)

    return {
        "ok": True,
        "ruta": str(path),
        "operacion": operacion,
        "backup": str(backup),
        "bytes_antes": len(actual.encode("utf-8")),
        "bytes_despues": len(nuevo.encode("utf-8")),
    }


def ejecutar_python(
    objetivo: str,
    modo: str = "archivo",
    argumentos: list | None = None,
    cwd: str = "~/yuna",
    timeout: int = 60,
) -> dict:
    """
    Ejecuta Python sin shell.

    modo='archivo': objetivo es una ruta .py
    modo='modulo': objetivo es un módulo Python, por ejemplo pytest o compileall
    """
    argumentos = argumentos or []
    if not isinstance(argumentos, list):
        raise ValueError("argumentos debe ser una lista")

    argumentos = [str(x) for x in argumentos]
    timeout = max(1, min(int(timeout), 120))
    working_dir = _resolver_ruta(cwd)

    if not working_dir.exists() or not working_dir.is_dir():
        raise ValueError(f"cwd inválido: {working_dir}")

    modo = str(modo).strip().lower()

    if modo == "archivo":
        script = _resolver_ruta(objetivo)
        if not script.exists() or not script.is_file():
            raise FileNotFoundError(f"Script no encontrado: {script}")
        if script.suffix.lower() != ".py":
            raise ValueError("Solo se pueden ejecutar archivos .py")
        comando = [sys.executable, str(script), *argumentos]

    elif modo == "modulo":
        modulo = str(objetivo).strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", modulo):
            raise ValueError("Nombre de módulo inválido")
        comando = [sys.executable, "-m", modulo, *argumentos]

    else:
        raise ValueError("modo debe ser 'archivo' o 'modulo'")

    try:
        proc = subprocess.run(
            comando,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "timeout": True,
            "codigo_salida": None,
            "stdout": (e.stdout or "")[-6000:] if isinstance(e.stdout, str) else "",
            "stderr": (e.stderr or "")[-6000:] if isinstance(e.stderr, str) else "",
            "comando": comando,
        }

    return {
        "ok": proc.returncode == 0,
        "timeout": False,
        "codigo_salida": proc.returncode,
        "stdout": proc.stdout[-6000:],
        "stderr": proc.stderr[-6000:],
        "comando": comando,
        "cwd": str(working_dir),
    }


def inspeccionar_proyecto(
    ruta: str = "~/yuna",
    profundidad: int = 3,
    max_archivos: int = 200,
) -> dict:
    """Inspecciona estructura, Python y estado Git de un proyecto local."""
    raiz = _resolver_ruta(ruta)
    if not raiz.exists() or not raiz.is_dir():
        raise ValueError(f"Proyecto no encontrado: {raiz}")

    profundidad = max(1, min(int(profundidad), 6))
    max_archivos = max(20, min(int(max_archivos), 500))

    excluidos = {
        ".git", "__pycache__", ".pytest_cache", ".mypy_cache",
        ".venv", "venv", "node_modules", "backups", "legacy"
    }

    archivos = []
    directorios = set()
    extensiones = Counter()
    arbol = []
    python_info = []

    for current, dirs, files in os.walk(raiz):
        current_path = Path(current)
        rel_dir = current_path.relative_to(raiz)
        nivel = len(rel_dir.parts)

        dirs[:] = [d for d in dirs if d not in excluidos]

        if nivel >= profundidad:
            dirs[:] = []

        directorios.add(str(rel_dir) if str(rel_dir) != "." else ".")

        for nombre in sorted(files):
            if len(archivos) >= max_archivos:
                break

            path = current_path / nombre
            rel = path.relative_to(raiz)
            archivos.append(path)
            extensiones[path.suffix.lower() or "[sin_ext]"] += 1
            arbol.append(str(rel))

            if path.suffix.lower() == ".py" and len(python_info) < 50:
                try:
                    contenido = path.read_text(encoding="utf-8")
                    tree = ast.parse(contenido)
                    funciones = []
                    clases = []
                    imports = []

                    for node in tree.body:
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            funciones.append(node.name)
                        elif isinstance(node, ast.ClassDef):
                            clases.append(node.name)
                        elif isinstance(node, ast.Import):
                            imports.extend(alias.name for alias in node.names)
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            imports.append(node.module)

                    python_info.append({
                        "archivo": str(rel),
                        "funciones": funciones[:20],
                        "clases": clases[:20],
                        "imports": sorted(set(imports))[:20],
                    })
                except (OSError, UnicodeDecodeError, SyntaxError):
                    pass

        if len(archivos) >= max_archivos:
            break

    archivos_grandes = []
    for path in archivos:
        try:
            archivos_grandes.append((path.stat().st_size, str(path.relative_to(raiz))))
        except OSError:
            pass
    archivos_grandes.sort(reverse=True)

    git_status = None
    if (raiz / ".git").exists():
        try:
            proc = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(raiz),
                capture_output=True,
                text=True,
                timeout=5,
                shell=False,
            )
            git_status = proc.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            git_status = None

    return {
        "ruta": str(raiz),
        "archivos_analizados": len(archivos),
        "directorios_detectados": len(directorios),
        "limite_alcanzado": len(archivos) >= max_archivos,
        "extensiones": dict(extensiones.most_common(15)),
        "archivos_mas_grandes": [
            {"ruta": ruta_rel, "kb": round(size / 1024, 1)}
            for size, ruta_rel in archivos_grandes[:10]
        ],
        "arbol": arbol[:max_archivos],
        "python": python_info,
        "git_status": git_status,
    }
