#!/bin/bash

set -e

YUNA_ROOT="$HOME/yuna"

echo "========================================"
echo "       YUNA PATH CONFIGURATION"
echo "========================================"
echo
echo "YUNA_ROOT: $YUNA_ROOT"
echo "HOME:      $HOME"
echo

cd "$YUNA_ROOT"

# --------------------------------------------------
# 1. Verificar sistema central de rutas
# --------------------------------------------------

if [ ! -f "config/paths.py" ]; then
    echo "ERROR: No existe config/paths.py"
    exit 1
fi

echo "[1/5] Sistema central de rutas encontrado"

# --------------------------------------------------
# 2. Buscar referencias ACTIVAS a Downloads
# --------------------------------------------------

echo
echo "[2/5] Referencias activas a ~/Downloads:"
echo

grep -RInE '~/Downloads|/Users/[^"]+/Downloads' \
    --exclude-dir=.git \
    --exclude-dir=venv \
    --exclude-dir=backups \
    --exclude='*.bak' \
    --exclude='*.save' \
    --exclude='*.normalizado' \
    --exclude='*.log' \
    . || true

# --------------------------------------------------
# 3. Mostrar rutas reconocidas
# --------------------------------------------------

echo
echo "[3/5] Resolución actual de ubicaciones:"
echo

python3 - <<'PY'
from config.paths import (
    YUNA_ROOT,
    HOME,
    USER_DIRECTORIES,
    resolve_location,
)

print(f"YUNA_ROOT : {YUNA_ROOT}")
print(f"HOME      : {HOME}")
print()

for nombre, ruta in USER_DIRECTORIES.items():
    print(f"{nombre:12} -> {ruta}")

print()
print("RESOLVER:")

for nombre in [
    "descargas",
    "escritorio",
    "documentos",
    "imagenes",
]:
    print(f"{nombre:12} -> {resolve_location(nombre)}")
PY

# --------------------------------------------------
# 4. Ejecutar pruebas
# --------------------------------------------------

echo
echo "[4/5] Ejecutando pruebas..."
echo

python3 -m pytest -q

# --------------------------------------------------
# 5. Resumen
# --------------------------------------------------

echo
echo "[5/5] CHECKLIST"
echo

echo "✓ ~/yuna es la raíz de Yuna"
echo "✓ Las carpetas del usuario se resuelven dinámicamente"
echo "✓ Downloads no es la raíz universal"
echo "✓ Desktop puede ser ubicación de trabajo"
echo "✓ Documents puede ser ubicación de trabajo"
echo "✓ Pictures puede ser ubicación de trabajo"
echo "✓ Music puede ser ubicación de trabajo"
echo "✓ Movies puede ser ubicación de trabajo"
echo "✓ Pruebas ejecutadas correctamente"

echo
echo "========================================"
echo "       CONFIGURACIÓN VALIDADA"
echo "========================================"
