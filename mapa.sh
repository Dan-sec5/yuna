#!/bin/bash

ROOT="${1:-.}"

if [ ! -d "$ROOT" ]; then
    echo "Error: '$ROOT' no es una carpeta válida."
    exit 1
fi

echo
echo "MAPA DE: $(cd "$ROOT" && pwd)"
echo "========================================"

mostrar_arbol() {
    local carpeta="$1"
    local prefijo="$2"

    for item in "$carpeta"/*; do
        [ -e "$item" ] || continue

        local nombre
        nombre=$(basename "$item")

        if [ -d "$item" ]; then
            echo "${prefijo}📁 $nombre/"
            mostrar_arbol "$item" "${prefijo}    "
        else
            echo "${prefijo}📄 $nombre"
        fi
    done
}

mostrar_arbol "$ROOT" ""

echo "========================================"
echo "Fin del mapa"
