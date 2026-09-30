#!/bin/bash

set -e

cd "$(dirname "$0")"

echo "════════════════════════════════════════════════════"
echo "        YUNA // SINCRONIZACIÓN CON GIT"
echo "════════════════════════════════════════════════════"
echo

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "❌ Este directorio no es un repositorio Git."
    exit 1
fi

BRANCH="$(git branch --show-current)"

if [ -z "$BRANCH" ]; then
    echo "❌ No se pudo determinar la rama actual."
    exit 1
fi

echo "📁 Repositorio: $(pwd)"
echo "🌿 Rama: $BRANCH"
echo

echo "🔎 Cambios detectados:"
echo "────────────────────────────────────────────────────"

if git status --short | grep -q .; then
    git status --short
else
    echo "   No hay cambios."
    echo
    echo "✅ Yuna ya está sincronizada."
    exit 0
fi

echo
echo "────────────────────────────────────────────────────"
echo

printf "¿Subir todos estos cambios a Git? [s/N]: "
read -r CONFIRM

if [[ ! "$CONFIRM" =~ ^[sS]$ ]]; then
    echo
    echo "⏹️ Operación cancelada."
    exit 0
fi

echo
echo "📦 Añadiendo cambios..."
git add -A

echo
echo "📋 Cambios incluidos:"
git diff --cached --stat

echo
echo "💾 Creando commit..."

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

git commit -m "Yuna update $TIMESTAMP"

echo
echo "🚀 Subiendo a origin/$BRANCH..."

git push origin "$BRANCH"

echo
echo "════════════════════════════════════════════════════"
echo "              ✅ YUNA SINCRONIZADA"
echo "════════════════════════════════════════════════════"
echo

git log -1 --oneline

echo
