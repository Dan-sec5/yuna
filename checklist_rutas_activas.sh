#!/bin/bash

set -e

YUNA_ROOT="$HOME/yuna"

echo "========================================"
echo " YUNA CHECKLIST - RUTAS ACTIVAS"
echo "========================================"
echo

cd "$YUNA_ROOT"

echo "ROOT:"
echo "  $YUNA_ROOT"
echo

echo "----------------------------------------"
echo "1. ARCHIVOS ACTIVOS CON DOWNLOADS"
echo "----------------------------------------"

grep -RInE '~/Downloads|/Users/[^"]+/Downloads' \
    config \
    core \
    tools \
    interface \
    app.py \
    aprender.py \
    migrate_memoria.py \
    2>/dev/null || true

echo
echo "----------------------------------------"
echo "2. ARCHIVOS ACTIVOS CON YUNA ROOT"
echo "----------------------------------------"

grep -RInE '~/yuna|/Users/[^"]+/yuna' \
    config \
    core \
    tools \
    interface \
    app.py \
    aprender.py \
    migrate_memoria.py \
    2>/dev/null || true

echo
echo "----------------------------------------"
echo "3. ARCHIVOS DE RESPALDO / LEGACY"
echo "----------------------------------------"

find . \
    \( -name "*.bak" -o -name "*.save" -o -name "*.normalizado" \) \
    -o -path "./legacy/*" \
    2>/dev/null | sort

echo
echo "----------------------------------------"
echo "4. TESTS ACTUALES"
echo "----------------------------------------"

python3 -m pytest -q

echo
echo "========================================"
echo " AUDITORÍA COMPLETADA"
echo "========================================"
