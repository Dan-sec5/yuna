"""
core/agent.py — Agente Yuna V4 con auto-mejora
"""
import re
import json
import time
import logging
from core.logger import get_logger
from core.llm import chat_with_tools, chat_simple, clean_response, get_tool_calls
from core.context import ContextManager
from core.executor import ToolExecutor
from core.evaluator import ResultEvaluator
from core.learning import LearningEngine
from tools.schemas import ALL_SCHEMAS
from memory.manager import get_relevant_memory, add_episodic, add_interaction_metric
from config import get

logger = get_logger(__name__)

MODEL_AGENT = get("models.agent", "qwen3:8b")
MODEL_CHAT = get("models.chat", "qwen3:8b")

SYSTEM_AGENT = """Eres un selector de herramientas.
Tu UNICO trabajo: llamar la herramienta correcta con los argumentos correctos.
NO expliques. NO razones. SOLO ejecuta la herramienta.
Si no hay herramienta aplicable responde exactamente: DIRECTO: [respuesta en espanol]"""

SYSTEM_SINTETIZADOR = """Eres Yuna. Responde en espanol mexicano, maximo 2 oraciones.
Usa los datos proporcionados. Sin razonamiento. Sin "Okay". Sin ingles. Ve al punto."""

def _extraer_espanol(texto: str) -> str:
    if not texto:
        return ""
    texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL)
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    triggers_ingles = {
        "okay", "let me", "first,", "i need", "looking at", "the user",
        "wait,", "hmm,", "so,", "based on", "i should", "let's", "alright",
        "sure,", "of course", "so the", "the answer", "therefore", "in summary",
        "in conclusion", "so i", "i can", "i'll", "i will", "now,", "next,",
        "finally,", "since", "given that", "looking", "checking", "maybe",
        "perhaps", "actually,", "essentially", "basically", "the response",
        "so the response", "so the answer"
    }
    resultado = []
    for linea in lineas:
        lower = linea.lower()
        es_ingles = any(
            lower.startswith(t) or f" {t}" in lower[:40]
            for t in triggers_ingles
        )
        tiene_espanol = bool(re.search(r'[aáeéiíoóuúüñ¿¡]', linea))
        empieza_espanol = bool(re.match(
            r'^(hoy|mañana|los|las|el |la |en |no |sí|para|desde|según|hay|'
            r'puedo|podría|yuna|claro|aquí|esto|ese|esa|con |sin |una |un |'
            r'voy|son|está|están|tengo|tenemos|buenos|buenas)',
            lower
        ))
        if (tiene_espanol or empieza_espanol) and not es_ingles:
            resultado.append(linea)
        elif resultado and not es_ingles and len(linea) > 10:
            resultado.append(linea)
    if resultado:
        return ' '.join(resultado[:3])
    return lineas[-1] if lineas else texto

class YunaAgent:
    def __init__(self, confirm_callback=None):
        self.executor = ToolExecutor(confirm_callback)
        self.evaluator = ResultEvaluator(max_iterations=5)
        self.learner = LearningEngine()
        self.history = []
        self.session_stats = {"tools_used": [], "success": True, "latency": 0}

    def process(self, user_input: str) -> str:
        start_time = time.time()
        logger.info(f"Input: {user_input[:80]}")
        memoria = get_relevant_memory(user_input, top_k=5)
        ctx_selector = [{"role": "system", "content": SYSTEM_AGENT}]
        if memoria:
            ctx_selector[0]["content"] += f"\n\nCONTEXTO:\n{memoria}"
        for msg in self.history[-4:]:
            ctx_selector.append(msg)
        ctx_selector.append({"role": "user", "content": user_input})

        response = chat_with_tools(
            ctx_selector, ALL_SCHEMAS,
            model=MODEL_AGENT,
            num_predict=200,
            temperature=0.1
        )
        tool_calls = get_tool_calls(response)
        contenido = clean_response(response)

        if not tool_calls:
            if "DIRECTO:" in contenido:
                respuesta = contenido.split("DIRECTO:")[-1].strip()
            else:
                respuesta = _extraer_espanol(contenido) or contenido
            self._guardar(user_input, respuesta, direct=True)
            self._record_metrics(start_time, user_input, respuesta, [], True)
            return respuesta

        resultados_tools = []
        self.evaluator.reset()
        if self.evaluator.should_continue(tool_calls, contenido):
            resultados = self.executor.execute_batch(tool_calls)
            for name, error, result in resultados:
                if error:
                    resultados_tools.append(f"Error en {name}: {error}")
                    logger.error(f"Tool {name}: {error}")
                    self.session_stats["success"] = False
                    self.learner.record_lesson(user_input, name, error, success=False)
                else:
                    resultados_tools.append(f"{name}: {str(result)[:800]}")
                    logger.info(f"Tool {name} OK")
                    self.session_stats["tools_used"].append(name)
                    self.learner.record_lesson(user_input, name, str(result)[:200], success=True)

        datos = "\n".join(resultados_tools) if resultados_tools else "Sin datos"
        prompt = f"Pregunta: {user_input}\nDatos: {datos}"
        ctx_sintesis = [
            {"role": "system", "content": SYSTEM_SINTETIZADOR},
            {"role": "user", "content": prompt}
        ]
        resp_final = chat_simple(
            ctx_sintesis,
            model=MODEL_CHAT,
            num_predict=150,
            temperature=0.3
        )
        respuesta = clean_response(resp_final)
        respuesta = _extraer_espanol(respuesta) or respuesta

        self._guardar(user_input, respuesta, direct=False)
        self._record_metrics(start_time, user_input, respuesta, self.session_stats["tools_used"], True)
        self._auto_evaluate(user_input, respuesta, resultados_tools)
        logger.info(f"Respuesta: {respuesta[:80]}")
        return respuesta

    def _guardar(self, user_input: str, respuesta: str, direct: bool = False):
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": respuesta})
        if len(self.history) > 20:
            self.history = self.history[-20:]
        add_episodic(
            "interaccion",
            json.dumps({
                "user": user_input[:200],
                "response": respuesta[:200],
                "direct": direct,
                "tools": self.session_stats["tools_used"]
            })
        )

    def _record_metrics(self, start_time, query, response, tools, success):
        latency = time.time() - start_time
        add_interaction_metric(query, response, tools, success, latency)

    def _auto_evaluate(self, query: str, response: str, tool_results: list):
        if tool_results and len(response) < 10:
            self.learner.record_lesson(query, "synthesis", "respuesta_muy_corta", success=False)
        lower = response.lower()
        if any(x in lower for x in ["no encontré", "no pude", "error", "no tengo acceso", "falló"]):
            self.session_stats["success"] = False

    def provide_feedback(self, query: str, feedback: str):
        self.learner.record_user_feedback(query, feedback)

    def reset(self):
        self.history = []
        self.evaluator.reset()
        self.session_stats = {"tools_used": [], "success": True, "latency": 0}
        logger.info("Agente reiniciado")
