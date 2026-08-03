#!/bin/bash

set -e

ROOT="$HOME/yuna"
cd "$ROOT"

echo "========================================"
echo " YUNA FASE 2 - DESACOPLAR DOWNLOADS"
echo "========================================"
echo
echo "ROOT: $ROOT"
echo

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP="$ROOT/backups/pre_paths_phase2_$TIMESTAMP"

mkdir -p "$BACKUP"

echo "[1/6] Creando respaldo..."

cp tools/archivos.py "$BACKUP/archivos.py"
cp tools/schemas.py "$BACKUP/schemas.py"
cp core/planner.py "$BACKUP/planner.py"
cp core/agent.py "$BACKUP/agent.py"

echo "✓ Respaldo creado:"
echo "  $BACKUP"
echo


# ============================================================
# 2. tools/archivos.py
# ============================================================

echo "[2/6] Actualizando tools/archivos.py..."

python3 <<'PY'
from pathlib import Path

path = Path("tools/archivos.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
    'from pathlib import Path\n',
    'from pathlib import Path\n\nfrom config.paths import resolve_location\n'
)

text = text.replace(
    'def buscar_archivos(patron: str = "*", carpeta: str = "~/Downloads") -> list:',
    'def buscar_archivos(patron: str = "*", carpeta: str = "home") -> list:'
)

text = text.replace(
    '    carpeta = os.path.expanduser(carpeta)\n',
    '    carpeta = str(resolve_location(carpeta))\n',
    1
)

text = text.replace(
    'def listar_recientes(carpeta: str = "~/Downloads", dias: int = 7) -> list:',
    'def listar_recientes(carpeta: str = "home", dias: int = 7) -> list:'
)

# Segunda aparición de expansión de ruta
old = '    carpeta = os.path.expanduser(carpeta)\n    dias = int(dias)\n'
new = '    carpeta = str(resolve_location(carpeta))\n    dias = int(dias)\n'

text = text.replace(old, new, 1)

text = text.replace(
    'def organizar_por_tipo(carpeta_origen: str = "~/Downloads") -> list:',
    'def organizar_por_tipo(carpeta_origen: str = "home") -> list:'
)

old = '    carpeta = os.path.expanduser(carpeta_origen)\n'
new = '    carpeta = str(resolve_location(carpeta_origen))\n'

text = text.replace(old, new, 1)

text = text.replace(
    'def detectar_descargas(carpeta: str = "~/Downloads", dias: int = 30) -> list:',
    'def detectar_descargas(carpeta: str = "descargas", dias: int = 30) -> list:'
)

old = '    carpeta = os.path.expanduser(carpeta)\n    dias = max(0, int(dias))\n'
new = '    carpeta = str(resolve_location(carpeta))\n    dias = max(0, int(dias))\n'

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
PY

echo "✓ tools/archivos.py actualizado"
echo


# ============================================================
# 3. schemas
# ============================================================

echo "[3/6] Actualizando schemas..."

python3 <<'PY'
from pathlib import Path

path = Path("tools/schemas.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
    '"Ruta base, ej: ~/Downloads"',
    '"Ubicación: descargas, escritorio, documentos, imagenes, home o una ruta personalizada"'
)

text = text.replace(
    '"Ruta a revisar, normalmente ~/Downloads"',
    '"Ubicación a revisar: descargas, escritorio, documentos, imagenes o una ruta personalizada"'
)

text = text.replace(
    '"Carpeta a organizar"',
    '"Ubicación a organizar: descargas, escritorio, documentos, imagenes o una ruta personalizada"'
)

path.write_text(text, encoding="utf-8")
PY

echo "✓ schemas actualizados"
echo


# ============================================================
# 4. planner
# ============================================================

echo "[4/6] Actualizando planner..."

python3 <<'PY'
from pathlib import Path

path = Path("core/planner.py")
text = path.read_text(encoding="utf-8")

old = """RUTAS DEL SISTEMA:
- Descargas: ~/Downloads
- Reportes: ~/Desktop/Reportes
- Datos Excel: ~/Desktop/Datos
"""

new = """UBICACIONES DEL USUARIO:

Las ubicaciones del usuario son dinámicas y deben resolverse mediante
el sistema central de rutas de Yuna.

Alias disponibles:
- home
- descargas / downloads
- escritorio / desktop
- documentos / documents
- imagenes / pictures
- musica / music
- videos / movies

IMPORTANTE:
- ~/yuna es exclusivamente la raíz interna de Yuna.
- Downloads NO es la ubicación universal de trabajo.
- No asumas que los archivos del usuario están en Downloads.
- Si el usuario indica una ubicación, respétala exactamente.
- Si el usuario utiliza un alias como "escritorio", debe utilizarse
  ese alias como ubicación.
"""

if old in text:
    text = text.replace(old, new)
else:
    print("ADVERTENCIA: bloque esperado del planner no encontrado.")

path.write_text(text, encoding="utf-8")
PY

echo "✓ planner actualizado"
echo


# ============================================================
# 5. agent
# ============================================================

echo "[5/6] Actualizando reglas del agente..."

python3 <<'PY'
from pathlib import Path

path = Path("core/agent.py")
text = path.read_text(encoding="utf-8")

needle = """REGLAS PARA ARCHIVOS:

buscar_archivos:
"""

replacement = """REGLAS DE UBICACIONES:

1. ~/yuna es la raíz interna de Yuna.
2. No asumas que Downloads es la ubicación de trabajo.
3. Si el usuario dice:
   - "descargas" -> usa "descargas"
   - "downloads" -> usa "downloads"
   - "escritorio" -> usa "escritorio"
   - "desktop" -> usa "desktop"
   - "documentos" -> usa "documentos"
   - "documents" -> usa "documents"
   - "imagenes" -> usa "imagenes"
   - "pictures" -> usa "pictures"
   - "musica" -> usa "musica"
   - "music" -> usa "music"
   - "videos" -> usa "videos"
   - "movies" -> usa "movies"
4. No conviertas automáticamente una ubicación en otra.
5. Si el usuario proporciona una ruta explícita, respétala.
6. No describas Downloads como ubicación predeterminada del usuario.

REGLAS PARA ARCHIVOS:

buscar_archivos:
"""

if needle in text:
    text = text.replace(needle, replacement)
else:
    print("ADVERTENCIA: bloque esperado del agente no encontrado.")

path.write_text(text, encoding="utf-8")
PY

echo "✓ agent actualizado"
echo


# ============================================================
# 6. AUDITORÍA
# ============================================================

echo "[6/6] Ejecutando auditoría..."
echo

echo "REFERENCIAS ACTIVAS A ~/Downloads:"
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
echo "EJECUTANDO TESTS..."
echo "----------------------------------------"

python3 -m pytest -q

echo
echo "========================================"
echo " FASE 2 COMPLETADA"
echo "========================================"
echo
echo "Respaldo:"
echo "$BACKUP"
echo
