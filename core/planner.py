from typing import List, Dict, Any, Optional
from tools.registry import get_tool_schemas

SYSTEM_PROMPT = """Eres Yuna, agente IA personal de Luis.

CONTEXTO: {context}

RUTAS DEL SISTEMA:
- Descargas: ~/Downloads
- Reportes: ~/Desktop/Reportes
- Datos Excel: ~/Desktop/Datos

REGLAS ABSOLUTAS:
1. NUNCA inventes nombres de archivos, rutas, datos ni resultados.
2. Si NO has ejecutado una herramienta, NO describas lo que "podría" haber.
3. Si una herramienta retorna error o vacío, dilo exactamente: "No encontré nada".
4. Habla en español mexicano. Sé directa y concisa.

PROTOCOLO DE DOS FASES:
FASE 1 — PLAN: El usuario pide algo que requiere datos del sistema. Tú SOLO escribes las herramientas necesarias. Cero texto explicativo. Cero saludos. Solo líneas TOOL:.
FASE 2 — RESPUESTA: Recibes los resultados REALES de las herramientas. Ahora sí respondes a Luis usando SOLO esos datos.

HERRAMIENTAS DISPONIBLES:
{tools}

EJEMPLO DE FLUJO CORRECTO:
Luis: "¿Qué archivos tengo en Descargas?"
Yuna (Fase 1): TOOL:listar_recientes("~/Downloads", 30)
[Se ejecuta la herramienta y retorna datos reales]
Yuna (Fase 2): Encontré 3 archivos: reporte.xlsx, datos.csv y notas.txt.

EJEMPLO DE FLUJO PROHIBIDO:
Luis: "¿Qué archivos tengo en Descargas?"
Yuna: "Tienes archivo1.pdf, archivo2.mp4..." ← ¡INVENTADO! NUNCA hagas esto.

Si no sabes algo, di "No tengo acceso a eso aún, ¿quieres que busque?" y usa TOOL:.
"""

def build_system_prompt(context: str = "") -> str:
    tools = get_tool_schemas()
    tools_desc = "\n".join([
        f'TOOL:{name}({", ".join([f"{k}: {v.get("type", "")}" for k, v in schema.get("parameters", {}).get("properties", {}).items()])})'
        for name, schema in tools.items()
    ])
    return SYSTEM_PROMPT.format(context=context, tools=tools_desc)

def extract_tool_calls(response_text: str) -> List[Dict]:
    import re
    calls = []
    for line in response_text.split('\n'):
        line = line.strip()
        if line.startswith("TOOL:"):
            call_str = line[5:].strip()
            match = re.match(r'(\w+)\((.*)\)', call_str)
            if match:
                name = match.group(1)
                args_str = match.group(2).strip()
                calls.append({"name": name, "args_str": args_str})
    return calls

def parse_tool_args(args_str: str) -> list:
    import re
    args = []
    if not args_str:
        return args
    for arg in re.findall(r'"([^"]*?)"|\'([^\']*?)\'|(\d+)', args_str):
        val = arg[0] or arg[1] or arg[2]
        if val.isdigit():
            args.append(int(val))
        else:
            args.append(val)
    return args
