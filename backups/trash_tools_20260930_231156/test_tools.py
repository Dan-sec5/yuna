import sys, os
sys.path.insert(0, os.path.expanduser("~/yuna"))
import pytest

# ─── tests/tools/archivos ───────────────────────────────────

from tools.archivos import buscar_archivos, listar_recientes, leer_texto

def test_listar_recientes_downloads():
    resultados = listar_recientes("~/Downloads", dias=30)
    assert isinstance(resultados, list)

def test_listar_recientes_carpeta_invalida():
    resultados = listar_recientes("~/carpeta_que_no_existe", dias=7)
    assert resultados == [] or isinstance(resultados, list)

def test_buscar_archivos_patron():
    resultados = buscar_archivos("*.py", "~/yuna")
    assert isinstance(resultados, list)
    assert any("app.py" in r for r in resultados)

def test_leer_texto_valido():
    ruta = os.path.expanduser("~/yuna/README.md")
    if os.path.exists(ruta):
        contenido = leer_texto(ruta)
        assert isinstance(contenido, str)
        assert len(contenido) > 0

def test_leer_texto_invalido():
    with pytest.raises(Exception):
        leer_texto("~/archivo_inexistente_xyz.txt")

# ─── tests/tools/datos ──────────────────────────────────────

from tools.datos import leer_excel, leer_csv, leer_pdf

def test_leer_excel_invalido():
    resultado = leer_excel("~/archivo_inexistente.xlsx")
    assert "Error" in resultado

def test_leer_csv_invalido():
    resultado = leer_csv("~/archivo_inexistente.csv")
    assert "Error" in resultado

def test_leer_pdf_invalido():
    resultado = leer_pdf("~/archivo_inexistente.pdf")
    assert "Error" in resultado

# ─── tests/tools/web ────────────────────────────────────────

from tools.web import precio_activo

def test_precio_activo_ticker_valido():
    resultado = precio_activo("AAPL")
    assert isinstance(resultado, str)
    assert "AAPL" in resultado

def test_precio_activo_ticker_invalido():
    resultado = precio_activo("TICKER_INVALIDO_XYZ999")
    assert isinstance(resultado, str)

# ─── tests/tools/sistema ────────────────────────────────────

from tools.sistema import ejecutar_bash_seguro

def test_bash_seguro_permitido():
    resultado = ejecutar_bash_seguro("echo hola")
    assert "hola" in resultado

def test_bash_seguro_bloqueado():
    resultado = ejecutar_bash_seguro("rm -rf /tmp/test")
    assert "no permitido" in resultado or "⛔" in resultado

def test_bash_seguro_ls():
    resultado = ejecutar_bash_seguro("ls ~/yuna")
    assert isinstance(resultado, str)
    assert "app.py" in resultado

# ─── tests/tools/permisos ───────────────────────────────────

from tools.permisos import check_permission, PermissionLevel, is_bash_allowed

def test_permisos_safe():
    assert check_permission("buscar_archivos") == PermissionLevel.SAFE
    assert check_permission("leer_excel") == PermissionLevel.SAFE
    assert check_permission("precio_activo") == PermissionLevel.SAFE

def test_permisos_confirm():
    assert check_permission("organizar_archivos") == PermissionLevel.CONFIRM
    assert check_permission("crear_archivo") == PermissionLevel.SAFE

def test_permisos_dangerous():
    assert check_permission("herramienta_desconocida") == PermissionLevel.DANGEROUS

def test_bash_whitelist():
    assert is_bash_allowed("ls ~/Downloads") == True
    assert is_bash_allowed("cat archivo.txt") == True
    assert is_bash_allowed("rm -rf /") == False
    assert is_bash_allowed("sudo comando") == False


def test_detectar_descargas():
    from tools.archivos import detectar_descargas

    resultado = detectar_descargas("~/Downloads", dias=30)

    assert isinstance(resultado, list)

    for item in resultado:
        assert isinstance(item, dict)
        assert "nombre" in item
        assert "ruta" in item
        assert "evidencia" in item

def test_buscar_archivos_yuna_excluye_directorios_no_activos():
    resultados = buscar_archivos("*.py", "~/yuna")

    assert resultados

    for ruta in resultados:
        ruta_normalizada = ruta.replace("\\", "/")

        assert "/backups/" not in ruta_normalizada
        assert "/legacy/" not in ruta_normalizada
        assert "/.git/" not in ruta_normalizada
        assert "/__pycache__/" not in ruta_normalizada


# ─── tests/tools/desarrollo ─────────────────────────────────

from tools.desarrollo import editar_archivo, ejecutar_python, inspeccionar_proyecto


def test_editar_archivo_reemplaza_y_crea_backup(tmp_path):
    archivo = tmp_path / "demo.txt"
    archivo.write_text("hola mundo", encoding="utf-8")

    resultado = editar_archivo(
        str(archivo),
        "reemplazar_texto",
        contenido="Yuna",
        buscar="mundo",
    )

    assert resultado["ok"] is True
    assert archivo.read_text(encoding="utf-8") == "hola Yuna"
    assert os.path.exists(resultado["backup"])


def test_editar_archivo_rechaza_coincidencia_ambigua(tmp_path):
    archivo = tmp_path / "demo.txt"
    archivo.write_text("x x", encoding="utf-8")

    with pytest.raises(ValueError):
        editar_archivo(
            str(archivo),
            "reemplazar_texto",
            contenido="y",
            buscar="x",
        )


def test_ejecutar_python_archivo(tmp_path):
    script = tmp_path / "ok.py"
    script.write_text('print("YUNA_OK")', encoding="utf-8")

    resultado = ejecutar_python(
        str(script),
        modo="archivo",
        cwd=str(tmp_path),
        timeout=10,
    )

    assert resultado["ok"] is True
    assert "YUNA_OK" in resultado["stdout"]


def test_inspeccionar_proyecto(tmp_path):
    (tmp_path / "demo.py").write_text(
        "import os\n\ndef hola():\n    return 1\n\nclass Demo:\n    pass\n",
        encoding="utf-8",
    )

    resultado = inspeccionar_proyecto(str(tmp_path), profundidad=2)

    assert resultado["archivos_analizados"] >= 1
    assert any(x["archivo"] == "demo.py" for x in resultado["python"])
