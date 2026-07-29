import sys
sys.path.insert(0, os.path.expanduser("~/yuna"))

import pytest
from memory.manager import (
    init_db, set_preferencia, get_preferencia,
    add_episodic, get_episodic, get_relevant_memory
)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    # Limpiar
    import sqlite3
    from config import get
    from pathlib import Path
    db = Path(get("paths.memory_db")).expanduser()
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM preferencias")
        conn.execute("DELETE FROM episodic")
    yield
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM preferencias")
        conn.execute("DELETE FROM episodic")

class TestMemory:
    def test_preferencias(self):
        set_preferencia("test_key", "test_val")
        assert get_preferencia("test_key") == "test_val"
        assert get_preferencia("nonexistente") is None
    
    def test_episodic(self):
        add_episodic("Evento 1", "detalle 1")
        add_episodic("Evento 2", "detalle 2")
        events = get_episodic(10)
        assert len(events) == 2
        assert events[0]["evento"] == "Evento 2"  # más reciente primero
    
    def test_relevant_memory(self):
        set_preferencia("nombre", "Luis")
        add_episodic("Hablamos de Python")
        mem = get_relevant_memory("test")
        assert "Luis" in mem
        assert "Python" in mem
