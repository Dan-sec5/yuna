#!/bin/bash

set -e

YUNA_ROOT="$HOME/yuna"

cd "$YUNA_ROOT"

echo "============================================================"
echo " YUNA - CHECKLIST GENERAL"
echo "============================================================"
echo

PASS=0
FAIL=0

check() {
    local nombre="$1"
    local comando="$2"

    echo "------------------------------------------------------------"
    echo "$nombre"
    echo "------------------------------------------------------------"

    if eval "$comando"; then
        echo "PASS: $nombre"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $nombre"
        FAIL=$((FAIL + 1))
    fi

    echo
}

echo "ROOT:"
echo "  $YUNA_ROOT"
echo

# ============================================================
# 1. ESTRUCTURA
# ============================================================

check \
    "Estructura principal" \
    "test -f core/agent.py && test -f core/llm.py && test -f core/executor.py && test -f tools/schemas.py"

# ============================================================
# 2. SINTAXIS
# ============================================================

check \
    "Compilación Python" \
    "python3 -m py_compile core/agent.py core/llm.py core/executor.py tools/schemas.py"

# ============================================================
# 3. TESTS
# ============================================================

check \
    "Suite completa de tests" \
    "python3 -m pytest -q"

# ============================================================
# 4. TOOL CALLING
# ============================================================

echo "------------------------------------------------------------"
echo "Tool Calling"
echo "------------------------------------------------------------"

if grep -q "get_tool_calls(response)" core/agent.py; then
    echo "PASS: detección de tool calls"
    PASS=$((PASS + 1))
else
    echo "FAIL: detección de tool calls"
    FAIL=$((FAIL + 1))
fi

if grep -q '"role": "assistant"' core/agent.py && \
   grep -q '"tool_calls"' core/agent.py; then
    echo "PASS: preservación assistant + tool_calls"
    PASS=$((PASS + 1))
else
    echo "FAIL: preservación assistant + tool_calls"
    FAIL=$((FAIL + 1))
fi

if grep -q '"role": "tool"' core/agent.py; then
    echo "PASS: resultados role=tool"
    PASS=$((PASS + 1))
else
    echo "FAIL: resultados role=tool"
    FAIL=$((FAIL + 1))
fi

# ============================================================
# 5. MULTI-TOOL 13C
# ============================================================

echo
echo "------------------------------------------------------------"
echo "FASE 13C - Multi-Tool Chaining"
echo "------------------------------------------------------------"

if grep -q "messages.append(assistant_message)" core/agent.py; then
    echo "PASS: assistant tool-call entra al contexto"
    PASS=$((PASS + 1))
else
    echo "FAIL: assistant tool-call NO entra al contexto"
    FAIL=$((FAIL + 1))
fi

if grep -q '"tool_name": name' core/agent.py; then
    echo "PASS: tool result identifica herramienta"
    PASS=$((PASS + 1))
else
    echo "FAIL: tool result sin identificación"
    FAIL=$((FAIL + 1))
fi

if grep -q "llamadas_vistas" core/agent.py; then
    echo "PASS: protección contra tool loop infinito"
    PASS=$((PASS + 1))
else
    echo "FAIL: protección contra tool loop infinito"
    FAIL=$((FAIL + 1))
fi

# ============================================================
# 6. EXECUTOR
# ============================================================

check \
    "Executor disponible" \
    "python3 -c 'from core.executor import ToolExecutor; print(\"ToolExecutor OK\")'"

# ============================================================
# 7. SCHEMAS
# ============================================================

check \
    "Schemas disponibles" \
    "python3 -c 'from tools.schemas import ALL_SCHEMAS; print(len(ALL_SCHEMAS), \"schemas\")'"

echo
echo "------------------------------------------------------------"
echo "FASE 13D - Multi-Tool REAL"
echo "------------------------------------------------------------"

check \
    "Tool loop implementado" \
    "grep -q 'for step in range(max_steps)' core/agent.py"

check \
    "Tool result conserva tool_name" \
    "grep -Fq '\"tool_name\": name' core/agent.py"

check \
    "Assistant conserva tool_calls" \
    "grep -Fq '\"tool_calls\":' core/agent.py"

check \
    "Executor ejecuta batch de tools" \
    "grep -q 'execute_batch' core/agent.py"

check \
    "Protección contra llamadas repetidas" \
    "grep -q 'llamadas_vistas' core/agent.py"

echo
echo "------------------------------------------------------------"
echo "FASE 13D-C - Búsqueda Activa"
echo "------------------------------------------------------------"

check \
    "buscar_archivos implementado" \
    "grep -q 'def buscar_archivos' tools/archivos.py"

check \
    "Exclusión de backups" \
    "grep -q 'backups' tools/archivos.py"

check \
    "Exclusión de legacy" \
    "grep -q 'legacy' tools/archivos.py"

check \
    "Exclusión de .git" \
    "grep -q '\\.git' tools/archivos.py"

check \
    "Exclusión de __pycache__" \
    "grep -q '__pycache__' tools/archivos.py"

check \
    "Test de búsqueda activa" \
    "grep -q 'test_buscar_archivos_yuna_excluye_directorios_no_activos' tests/test_tools.py"

check \
    "Búsqueda real sin resultados no activos" \
    "python3 -c 'from tools.archivos import buscar_archivos; r=buscar_archivos(\"*.py\", \"~/yuna\"); assert r and not any(any(f\"/{x}/\" in p.replace(chr(92), \"/\") for x in (\"backups\", \"legacy\", \".git\", \"__pycache__\")) for p in r)'"

echo
echo "------------------------------------------------------------"
echo "FASE 13E - PRUEBA DE ENCADENAMIENTO REAL"
echo "------------------------------------------------------------"

check \
    "buscar_archivos registrado" \
    "grep -q '\"buscar_archivos\"' tools/registry.py"

check \
    "leer_texto registrado" \
    "grep -q '\"leer_texto\"' tools/registry.py"

check \
    "buscar_archivos disponible en schemas" \
    "grep -q '\"name\": \"buscar_archivos\"' tools/schemas.py"

check \
    "leer_texto disponible en schemas" \
    "grep -q '\"name\": \"leer_texto\"' tools/schemas.py"

check \
    "Executor soporta múltiples llamadas" \
    "grep -q 'for call in calls' core/executor.py"

check \
    "Tool loop permite múltiples pasos" \
    "grep -q 'for step in range(max_steps)' core/agent.py"

echo
echo "------------------------------------------------------------"

echo
echo "------------------------------------------------------------"
echo "FASE 13F - RAZONAMIENTO SOBRE RESULTADOS"
echo "------------------------------------------------------------"

check \
    "buscar_archivos permite obtener resultados" \
    "python3 -c 'from tools.archivos import buscar_archivos; r=buscar_archivos(\"*.py\", \"~/yuna\"); assert r'"

check \
    "Primer resultado puede alimentar leer_texto" \
    "python3 -c 'from tools.archivos import buscar_archivos, leer_texto; r=buscar_archivos(\"*.py\", \"~/yuna\"); assert r; c=leer_texto(r[0]); assert c'"

check \
    "Contenido puede analizarse" \
    "python3 -c 'from tools.archivos import leer_texto; c=leer_texto(\"core/agent.py\"); assert \"_ejecutar_tool_loop\" in c; assert \"process\" in c'"

check \
    "Síntesis usa datos reales" \
    "grep -q 'DATOS REALES OBTENIDOS DE LAS HERRAMIENTAS' core/agent.py"

check \
    "Síntesis LLM disponible" \
    "grep -q 'chat_simple' core/agent.py"

echo
echo "------------------------------------------------------------"
echo "FASE 13F-D - REGISTRY Y CHAINING"
echo "------------------------------------------------------------"

check \
    "registry.py contiene TOOLS" \
    "grep -q 'TOOLS = {' tools/registry.py"

check \
    "Registry contiene las 17 tools" \
    "python3 -c 'from tools.registry import list_tools; assert len(list_tools()) == 17'"

check \
    "buscar_archivos encuentra registry.py" \
    "python3 -c 'from tools.archivos import buscar_archivos; r=buscar_archivos(\"registry.py\", \"~/yuna\"); assert r'"

check \
    "leer_texto puede leer registry.py" \
    "python3 -c 'from tools.archivos import leer_texto; t=leer_texto(\"~/yuna/tools/registry.py\"); assert \"TOOLS = {\" in t'"

check \
    "Chain buscar_archivos -> leer_texto -> TOOLS" \
    "python3 -c 'from tools.archivos import buscar_archivos, leer_texto; from tools.registry import list_tools; r=buscar_archivos(\"registry.py\", \"~/yuna\"); assert r; t=leer_texto(r[0]); assert \"TOOLS = {\" in t; assert len(list_tools()) == 17'"

echo "RESULTADO"
echo "------------------------------------------------------------"

echo
echo "PASS: $PASS"
echo "FAIL: $FAIL"
echo

if [ "$FAIL" -eq 0 ]; then
    echo "CHECKLIST GENERAL: PASS"
    echo
    echo "Yuna está lista para la siguiente prueba."
    exit 0
else
    echo "CHECKLIST GENERAL: FAIL"
    echo
    echo "Hay validaciones pendientes."
    exit 1
fi

