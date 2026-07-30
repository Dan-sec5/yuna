"""
core/agent.py — Agente con paralelismo de herramientas y caché de resultados
"""
import logging
import concurrent.futures
from typing import List, Dict, Any, Optional
from core.llm import chat_with_tools, clean_response, get_tool_calls, preload_model
from core.context import ContextManager
from core.executor import ToolExecutor
from core.evaluator import ResultEvaluator
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

Cuando necesites información del sistema, USA LAS HERRAMIENTAS.
"""

class YunaAgent:
    def __init__(self, confirm_callback=None):
        self.context = ContextManager()
        self.executor = ToolExecutor(confirm_callback)
        self.evaluator = ResultEvaluator()
        self._tool_cache = {}  # Caché de resultados de herramientas
        self._init_system_prompt()
        # Precargar modelo al iniciar para evitar latencia de carga
        preload_model()

    def _init_system_prompt(self):
        tools_desc = []
        for schema in ALL_SCHEMAS:
            func = schema["function"]
            params = func.get("parameters", {}).get("properties", {})
            param_desc = ", ".join(f"{k}: {v.get('type', 'str')}" for k, v in params.items())
            tools_desc.append(f"- {func['name']}({param_desc}): {func['description']}")
        self.context.add_system(SYSTEM_PROMPT.format(tools_description="\n".join(tools_desc)))

    def _hash_tool_call(self, name: str, args: dict) -> str:
        """Genera un hash para caché de herramientas."""
        import hashlib
        return hashlib.md5(f"{name}:{str(sorted(args.items()))}".encode()).hexdigest()

    def process(self, user_input: str) -> str:
        self.context.add_user(user_input)
        self.context.enrich_with_memory(user_input)

        tools = ALL_SCHEMAS

        # ─── LLAMADA 1: Planificación ─────────────────────────
        response = chat_with_tools(self.context.get_context(), tools)
        content = clean_response(response)
        tool_calls = get_tool_calls(response)

        self.evaluator.reset()

        # ─── LOOP DE EJECUCIÓN ────────────────────────────────
        while tool_calls and self.evaluator.should_continue(tool_calls, content):
            # Ejecutar herramientas en PARALELO cuando sea seguro
            results = self._execute_parallel(tool_calls)

            context_str = self.evaluator.build_context(results)
            self.context.add_assistant(content)

            for name, error, result in results:
                self.context.add_tool_result(name, result if not error else f"ERROR: {error}")

            self.context.add_user(
                f"DATOS REALES DE HERRAMIENTAS:\n{context_str}\n\n"
                f"Usa ÚNICAMENTE estos datos. NO inventes nada. Responde a Luis en español mexicano."
            )

            # ─── LLAMADA 2: Respuesta con datos reales ──────────
            response = chat_with_tools(self.context.get_context(), tools)
            content = clean_response(response)
            tool_calls = get_tool_calls(response)

        self.context.add_assistant(content)
        return content

    def _execute_parallel(self, calls: List[Dict]) -> List[tuple]:
        """
        Ejecuta herramientas independientes en paralelo.
        Herramientas que modifican estado (escribir, organizar) se ejecutan secuencialmente.
        """
        MUTATING_TOOLS = {"organizar_archivos", "crear_archivo", "escribir_memoria", "ejecutar_bash_seguro"}

        results = []
        sequential = []
        parallel = []

        for call in calls:
            name = call.get("name", "")
            args = call.get("arguments", call.get("args", {}))

            # Verificar caché
            cache_key = self._hash_tool_call(name, args)
            if cache_key in self._tool_cache:
                results.append((name, None, self._tool_cache[cache_key]))
                continue

            if name in MUTATING_TOOLS:
                sequential.append((name, args))
            else:
                parallel.append((name, args))

        # Ejecutar en paralelo las de solo lectura
        if parallel:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(self._run_tool_safe, name, args): (name, args)
                    for name, args in parallel
                }
                for future in concurrent.futures.as_completed(futures):
                    name, args = futures[future]
                    try:
                        error, result = future.result()
                        cache_key = self._hash_tool_call(name, args)
                        self._tool_cache[cache_key] = result
                        results.append((name, error, result))
                    except Exception as e:
                        results.append((name, str(e), None))

        # Ejecutar secuencialmente las que mutan estado
        for name, args in sequential:
            error, result = self._run_tool_safe(name, args)
            results.append((name, error, result))

        return results

    def _run_tool_safe(self, name: str, args: dict) -> tuple:
        """Wrapper seguro para ejecutar una herramienta."""
        try:
            error, result = self.executor.execute(name, args)
            return error, result
        except Exception as e:
            return str(e), None

    def reset(self):
        self.context.clear_history()
        self.evaluator.reset()
        self._tool_cache.clear()
        self._init_system_prompt()
