import sys
import os
sys.path.insert(0, os.path.expanduser("~/yuna"))
import pytest

def test_agent_importa():
    from core.agent import YunaAgent
    agente = YunaAgent()
    assert agente is not None

def test_agent_reset():
    from core.agent import YunaAgent
    agente = YunaAgent()
    agente.reset()
    assert agente is not None

def test_agent_process_simple():
    from core.agent import YunaAgent
    agente = YunaAgent()
    respuesta = agente.process("hola")
    assert isinstance(respuesta, str)
    assert len(respuesta) > 0


def test_archivos_pdf_determinista():
    from core.agent import _respuesta_archivos_determinista

    resultado = _respuesta_archivos_determinista(
        "busca todos los PDF en ~/Downloads",
        [
            "buscar_archivos: ['/Users/test/a.pdf', '/Users/test/b.pdf']"
        ],
    )

    assert resultado == (
        "Encontré 2 archivos:\n"
        "1. /Users/test/a.pdf\n"
        "2. /Users/test/b.pdf"
    )


def test_archivos_excel_determinista():
    from core.agent import _respuesta_archivos_determinista

    resultado = _respuesta_archivos_determinista(
        "busca todos los Excel en ~/Downloads",
        [
            "buscar_archivos: ['/Users/test/a.xlsx', '/Users/test/b.xlsx']"
        ],
    )

    assert "Encontré 2 archivos:" in resultado
    assert "/Users/test/a.xlsx" in resultado
    assert "/Users/test/b.xlsx" in resultado


def test_archivos_recientes_determinista():
    from core.agent import _respuesta_archivos_determinista

    resultado = _respuesta_archivos_determinista(
        "qué archivos modifiqué recientemente",
        [
            (
                "listar_recientes: "
                "[{'nombre': 'archivo.txt', "
                "'ruta': '/Users/test/archivo.txt', "
                "'modificado': '2026-08-02 03:00', "
                "'tamano_kb': 10.0}]"
            )
        ],
    )

    assert "Encontré 1 archivos modificados recientemente:" in resultado
    assert "archivo.txt" in resultado


def test_no_confunde_descargados_con_modificados():
    from core.agent import _respuesta_archivos_determinista

    resultado = _respuesta_archivos_determinista(
        "qué archivos descargué en los últimos 30 días",
        [
            (
                "listar_recientes: "
                "[{'nombre': 'archivo.pdf', "
                "'ruta': '/Users/test/archivo.pdf', "
                "'modificado': '2026-08-02 03:00', "
                "'tamano_kb': 100.0}]"
            )
        ],
    )

    assert "no puedo determinar" in resultado.lower()
    assert "descargados" in resultado.lower()


def test_resultado_archivos_vacio():
    from core.agent import _respuesta_archivos_determinista

    resultado = _respuesta_archivos_determinista(
        "busca todos los PDF",
        ["buscar_archivos: []"],
    )

    assert resultado == "No encontré nada"


def test_resultado_archivos_malformado_no_rompe():
    from core.agent import _respuesta_archivos_determinista

    resultado = _respuesta_archivos_determinista(
        "busca todos los PDF",
        ["buscar_archivos: esto no es una lista válida"],
    )

    assert resultado is None
