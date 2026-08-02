"""
core/planner.py
Planner compatible con la arquitectura vNEXT de Yuna.

IMPORTANTE:
El agente principal utiliza tool calling nativo de Ollama.
Este módulo NO ejecuta herramientas y NO usa el antiguo protocolo TOOL:.

Su responsabilidad es construir contexto de planificación y exponer
las herramientas disponibles a componentes que necesiten inspeccionarlas.
"""

from typing import List, Dict, Any, Optional

from tools.schemas import ALL_SCHEMAS


SYSTEM_PROMPT = """Eres Yuna, agente IA personal de Luis.

CONTEXTO:
{context}

RUTAS DEL SISTEMA:
- Descargas: ~/Downloads
- Reportes: ~/Desktop/Reportes
- Datos Excel: ~/Desktop/Datos

REGLAS ABSOLUTAS:

1. NUNCA inventes nombres de archivos, rutas, datos ni resultados.
2. Si NO has ejecutado una herramienta, NO describas resultados.
3. Los resultados de las herramientas son la única fuente válida para
   afirmar qué existe realmente en el sistema.
4. Si el usuario pide información real del sistema, debe utilizarse
   una herramienta apropiada.
5. No uses una herramienta diferente solo porque parezca similar.
6. Respeta exactamente la diferencia entre:
   - buscar archivos
   - archivos recientes/modificados
   - descargas detectadas
7. Habla en español mexicano.
8. Sé directa y concisa.

ARQUITECTURA DE HERRAMIENTAS:

Las herramientas disponibles se proporcionan mediante schemas de
tool calling nativo.

NO utilices el antiguo formato textual:

TOOL:nombre(...)

El agente principal de Yuna utiliza tool calling estructurado.
"""


def get_available_schemas() -> List[Dict]:
    """
    Retorna los schemas oficiales de herramientas.

    ALL_SCHEMAS es la única fuente de verdad para las definiciones
    que recibe Ollama.
    """
    return ALL_SCHEMAS


def get_tool_schema(name: str) -> Optional[Dict]:
    """
    Busca un schema por nombre.
    """
    for schema in ALL_SCHEMAS:
        function = schema.get("function", {})

        if function.get("name") == name:
            return schema

    return None


def build_tools_description() -> str:
    """
    Construye una descripción legible de las herramientas disponibles.

    Esto NO sustituye los schemas enviados a Ollama.
    Sirve únicamente para contexto, diagnóstico o componentes
    que necesiten una representación textual.
    """

    lines = []

    for schema in ALL_SCHEMAS:
        function = schema.get("function", {})

        name = function.get("name", "")
        description = function.get("description", "")

        if not name:
            continue

        lines.append(
            f"- {name}: {description}"
        )

        parameters = function.get("parameters", {})
        properties = parameters.get("properties", {})

        for parameter_name, parameter_data in properties.items():
            parameter_type = parameter_data.get("type", "unknown")
            parameter_description = parameter_data.get(
                "description",
                ""
            )

            lines.append(
                f"    • {parameter_name}: "
                f"{parameter_type}"
                + (
                    f" — {parameter_description}"
                    if parameter_description
                    else ""
                )
            )

    return "\n".join(lines)


def build_system_prompt(context: str = "") -> str:
    """
    Construye el system prompt del planner.

    Compatible con la arquitectura actual de Yuna.
    """

    tools = build_tools_description()

    return SYSTEM_PROMPT.format(
        context=context,
    ) + (
        "\n\nHERRAMIENTAS DISPONIBLES:\n"
        + tools
    )


def extract_tool_calls(response_text: str) -> List[Dict]:
    """
    Compatibilidad con el antiguo planner textual.

    Actualmente el agente principal NO depende de esta función.
    Se conserva para evitar romper código legacy.

    Solo reconoce líneas explícitas TOOL:nombre(...).
    """

    import re

    calls = []

    if not response_text:
        return calls

    for line in response_text.splitlines():
        line = line.strip()

        if not line.startswith("TOOL:"):
            continue

        call_str = line[5:].strip()

        match = re.match(
            r"(\w+)\((.*)\)",
            call_str
        )

        if not match:
            continue

        name = match.group(1)
        args_str = match.group(2).strip()

        calls.append({
            "name": name,
            "args_str": args_str
        })

    return calls


def parse_tool_args(args_str: str) -> list:
    """
    Compatibilidad con el parser textual legacy.

    El flujo principal de Yuna utiliza argumentos estructurados
    provenientes de Ollama y no necesita esta función.
    """

    import re

    args = []

    if not args_str:
        return args

    pattern = r'"([^"]*?)"|\'([^\']*?)\'|(\d+)'

    for arg in re.findall(pattern, args_str):

        value = arg[0] or arg[1] or arg[2]

        if value.isdigit():
            args.append(int(value))
        else:
            args.append(value)

    return args
