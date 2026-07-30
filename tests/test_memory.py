import sys, os
sys.path.insert(0, os.path.expanduser("~/yuna"))
import pytest
import tempfile

def test_init_db():
    from memory.manager import init_db
    init_db()
    from pathlib import Path
    from config import get
    db_path = Path(get("paths.memory_db")).expanduser()
    assert db_path.exists()

def test_set_get_preferencia():
    from memory.manager import init_db, set_preferencia, get_preferencia
    init_db()
    set_preferencia("test_clave", "test_valor")
    val = get_preferencia("test_clave")
    assert val == "test_valor"

def test_get_preferencia_inexistente():
    from memory.manager import init_db, get_preferencia
    init_db()
    val = get_preferencia("clave_que_no_existe_xyz")
    assert val is None

def test_add_get_episodic():
    from memory.manager import init_db, add_episodic, get_episodic
    init_db()
    add_episodic("test_evento", "detalles de prueba")
    episodic = get_episodic(limit=10)
    assert isinstance(episodic, list)
    assert any(e["evento"] == "test_evento" for e in episodic)

def test_escribir_consultar_memoria():
    from memory.manager import init_db, consultar_memoria, escribir_memoria
    init_db()
    escribir_memoria("nombre_test", "Luis")
    resultado = consultar_memoria("preferencias", "nombre_test")
    assert "Luis" in resultado
