#!/bin/zsh

YUNA_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$YUNA_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    echo "❌ No se encontró el entorno virtual de Yuna:"
    echo "   $YUNA_DIR/.venv"
    exit 1
fi

cd "$YUNA_DIR" || exit 1

exec "$PYTHON" "$YUNA_DIR/app.py" "$@"
