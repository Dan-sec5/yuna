import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.paths import (
    YUNA_ROOT,
    HOME,
    resolve_location,
    is_inside_yuna,
)


def test_yuna_root():
    assert YUNA_ROOT.name == "yuna"
    assert YUNA_ROOT.exists()


def test_home():
    assert HOME == Path.home()


def test_downloads():
    assert resolve_location("descargas") == Path.home() / "Downloads"


def test_desktop():
    assert resolve_location("escritorio") == Path.home() / "Desktop"


def test_documents():
    assert resolve_location("documentos") == Path.home() / "Documents"


def test_pictures():
    assert resolve_location("imagenes") == Path.home() / "Pictures"


def test_custom_path():
    result = resolve_location("~/Downloads")
    assert result == Path.home() / "Downloads"


def test_yuna_detection():
    assert is_inside_yuna(YUNA_ROOT / "core")
    assert not is_inside_yuna(Path.home() / "Downloads")
