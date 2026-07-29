import logging
from typing import List, Dict, Any, Optional
from core.llm import chat_with_tools, clean_response, get_tool_calls
from core.context import ContextManager
from core.executor import ToolExecutor
from core.evaluator import ResultEvaluator
from tools.registry import TOOLS
from tools.schemas import ALL_SCHEMAS
from memory.manager import get_relevant_memory

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres Yuna, agente IA personal de Luis.

REGLAS ABSOLUTAS:
1. NUNCA inventes nombres de archivos, rutas, datos ni resultados.
2. Si NO has ejecutado una herramienta, NO describas lo que "podría" haber.
3. Si una herramienta retorna error o vacío, dilo exactamente: "No encontré nada".
4. Habla en español mexicano. Sé directa y concisa.

HERRAMIENTAS DISPONIBLES:
{tools_description}

Cuando necesites información del sistema, USA LAS HERRAMIENTAS. El modelo las invocará automáticamente via tool calling.
"""

class YunaAgent:
    def __init__(self, confirm_callback=None):
        self.context = ContextManager()
        self.executor = ToolExecutor(confirm_callback)
        self.evaluator = ResultEvaluator()
        self._init_system_prompt()
    
    def _init_system_prompt(self):
        tools_desc = []
        for schema in ALL_SCHEMAS:
            func = schema["function"]
            params = func.get("parameters", {}).get("properties", {})
            param_desc = ", ".join(f"{k}: {v.get('type', 'str')}" for k, v in params.items())
            tools_desc.append(f"- {func['name']}({param_desc}): {func['description']}")
        self.context.add_system(SYSTEM_PROMPT.format(tools_description="\n".join(tools_desc)))
    
    def process(self, user_input: str) -> str:
        self.context.add_user(user_input)
        self.context.enrich_with_memory(user_input)
        
        tools = ALL_SCHEMAS
        
        response = chat_with_tools(self.context.get_context(), tools)
        content = clean_response(response)
        
        tool_calls = get_tool_calls(response)
        self.evaluator.reset()
        
        while tool_calls and self.evaluator.should_continue(tool_calls, content):
            results = self.executor.execute_batch(tool_calls)
            
            context_str = self.evaluator.build_context(results)
            self.context.add_assistant(content)
            
            for name, error, result in results:
                self.context.add_tool_result(name, result if not error else f"ERROR: {error}")
            
            self.context.add_user(
                f"DATOS REALES DE HERRAMIENTAS:\n{context_str}\n\n"
                f"Usa ÚNICAMENTE estos datos. NO inventes nada. Responde a Luis en español mexicano."
            )
            
            response = chat_with_tools(self.context.get_context(), tools)
            content = clean_response(response)
            tool_calls = get_tool_calls(response)
        
        self.context.add_assistant(content)
        return content
    
    def reset(self):
        self.context.clear_history()
        self.evaluator.reset()
        self._init_system_prompt()
