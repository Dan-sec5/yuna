#!/bin/zsh

set -e

YUNA_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$YUNA_DIR/.venv/bin/python"

echo
echo "════════════════════════════════════════════════════"
echo "        YUNA // OPTIMIZACIÓN SEGURA"
echo "════════════════════════════════════════════════════"
echo

# ---------------------------------------------------------
# 1. Comprobar entorno
# ---------------------------------------------------------

if [[ ! -x "$PYTHON" ]]; then
    echo "❌ No existe:"
    echo "   $PYTHON"
    exit 1
fi

cd "$YUNA_DIR"

echo "▶ Entorno"
echo "────────────────────────────────────────────────────"
echo "Yuna:   $YUNA_DIR"
echo "Python: $("$PYTHON" --version)"
echo

# ---------------------------------------------------------
# 2. Backup de archivos que vamos a tocar
# ---------------------------------------------------------

STAMP="$(date '+%Y%m%d_%H%M%S')"
BACKUP_DIR="$YUNA_DIR/.backup_optimizacion_$STAMP"

mkdir -p "$BACKUP_DIR"

cp app.py "$BACKUP_DIR/app.py"
cp interface/tui.py "$BACKUP_DIR/tui.py"

if [[ -f config/yuna_tui_config.json ]]; then
    cp config/yuna_tui_config.json \
       "$BACKUP_DIR/yuna_tui_config.json"
fi

echo "▶ Backup creado:"
echo "   $BACKUP_DIR"
echo

# ---------------------------------------------------------
# 3. Limpiar basura generada por Python/macOS
# ---------------------------------------------------------

echo "▶ Limpiando archivos temporales"
echo "────────────────────────────────────────────────────"

find "$YUNA_DIR" \
    -path "$YUNA_DIR/.git" -prune -o \
    -path "$YUNA_DIR/.venv" -prune -o \
    -type d -name "__pycache__" \
    -print -exec rm -rf {} +

find "$YUNA_DIR" \
    -path "$YUNA_DIR/.git" -prune -o \
    -path "$YUNA_DIR/.venv" -prune -o \
    -type f -name ".DS_Store" \
    -print -delete

echo

# ---------------------------------------------------------
# 4. Corregir configuración TUI v3.1 -> v3.2
# ---------------------------------------------------------

if [[ -f config/yuna_tui_config.json ]]; then

    "$PYTHON" - <<'PY'
from pathlib import Path
import json

p = Path("config/yuna_tui_config.json")

try:
    data = json.loads(p.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"⚠ No se pudo leer la configuración: {exc}")
    raise SystemExit(0)

if data.get("version") != "v3.2":
    data["version"] = "v3.2"
    p.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("✅ Configuración TUI actualizada a v3.2")
else:
    print("✓ Configuración TUI ya está en v3.2")
PY

fi

echo

# ---------------------------------------------------------
# 5. Verificar imports y sintaxis
# ---------------------------------------------------------

echo "▶ Verificando código Python"
echo "────────────────────────────────────────────────────"

"$PYTHON" -m compileall -q \
    app.py \
    core \
    interface \
    memory \
    tools

echo "✅ Compilación correcta"
echo

# ---------------------------------------------------------
# 6. Verificar TUI
# ---------------------------------------------------------

echo "▶ Verificando TUI"
echo "────────────────────────────────────────────────────"

"$PYTHON" - <<'PY'
import sys

print("Python:", sys.version.split()[0])
print("Executable:", sys.executable)

import textual
import PIL
import rich

print("Textual:", textual.__version__)
print("Pillow:", PIL.__version__)

try:
    import interface.tui
    print("TUI import: OK")
except Exception as exc:
    print("❌ TUI import ERROR:", repr(exc))
    raise
PY

echo

# ---------------------------------------------------------
# 7. Detectar imports potencialmente pesados
# ---------------------------------------------------------

echo "▶ Paquetes grandes / IA"
echo "────────────────────────────────────────────────────"

"$PYTHON" - <<'PY'
from importlib.util import find_spec

packages = [
    "torch",
    "transformers",
    "sentence_transformers",
    "scipy",
    "sklearn",
    "numpy",
    "pandas",
    "openpyxl",
    "pdfplumber",
    "ollama",
]

for package in packages:
    print(
        f"{package:<22}",
        "INSTALADO" if find_spec(package) else "no instalado"
    )
PY

echo

# ---------------------------------------------------------
# 8. Medir .venv
# ---------------------------------------------------------

echo "▶ Tamaño del entorno"
echo "────────────────────────────────────────────────────"

du -sh "$YUNA_DIR/.venv"

echo

# ---------------------------------------------------------
# 9. Tests
# ---------------------------------------------------------

echo "▶ Tests"
echo "────────────────────────────────────────────────────"

if [[ -d tests ]]; then
    "$PYTHON" -m pytest -q
else
    echo "⚠ No existe tests/"
fi

echo

# ---------------------------------------------------------
# 10. Estado final
# ---------------------------------------------------------

echo "▶ Estado Git"
echo "────────────────────────────────────────────────────"

git status --short

echo
echo "════════════════════════════════════════════════════"
echo "        OPTIMIZACIÓN SEGURA COMPLETADA"
echo "════════════════════════════════════════════════════"
echo
echo "Backup:"
echo "  $BACKUP_DIR"
echo
echo "Arrancar Yuna:"
echo "  ./run_yuna.sh"
echo
