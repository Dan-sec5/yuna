"""
core/agent.py — Agente Yuna V3 con dos modelos
"""
import re
import logging
from core.logger import get_logger
from core.llm import chat_with_tools, chat_simple, clean_response, get_tool_calls
from core.context import ContextManager
from core.executor import ToolExecutor
from core.evaluator import ResultEvaluator
from tools.schemas import ALL_SCHEMAS
from memory.manager import get_relevant_memory
from config import get

logger = get_logger(__name__)

MODEL_AGENT = get("models.agent", "qwen2.5:7b")
MODEL_CHAT  = get("models.chat",  "qwen3:4b")

SYSTEM_AGENT = """/no_think Eres un selector de herramientas.
Tu ÚNICO trabajo: llamar la herramienta correcta con los argumentos correctos.
NO expliques. NO razones. SOLO ejecuta la herramienta.
Si no hay herramienta aplicable responde exactamente: DIRECTO: [respuesta en español]"""

SYSTEM_SINTETIZADOR = """/no_think Eres Yuna. Responde en español mexicano, máximo 2 oraciones.
Usa los datos proporcionados. Sin razonamiento. Sin "Okay". Sin inglés. Ve al punto."""

def _extraer_español(texto: str) -> str:
    """Extrae solo el contenido en español eliminando razonamiento en inglés."""
    if not texto:
        return ""

    # Si tiene tags de thinking, eliminarlos
    texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL)

    # Separar por líneas y quedarse con las que tienen español
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]

    triggers_ingles = {
        "okay", "let me", "first,", "i need", "looking at", "the user",
        "wait,", "hmm,", "so,", "based on", "i should", "let's", "alright",
        "sure,", "of course", "so the", "the answer", "therefore", "in summary",
        "in conclusion", "so i", "i can", "i'll", "i will", "now,", "next,",
        "finally,", "since ", "given that", "looking", "checking", "maybe",
        "perhaps", "actually,", "essentially", "basically", "the response",
        "so the response", "so the answer"
    }

    resultado = []
    for linea in lineas:
        lower = linea.lower()
        es_ingles = any(lower.startswith(t) or f" {t}" in lower[:30]
                       for t in triggers_ingles)
        tiene_español = bool(re.search(r'[áéíóúüñ¿¡]', linea))
        empieza_español = bool(re.match(
            r'^(hoy|mañana|los|las|el |la |en |no |sí|para|desde|según|hay|'
            r'puedo|podría|yuna|claro|aquí|esto|ese|esa|con |sin |una |un )',
            lower
        ))

        if (tiene_español or empieza_español) and not es_ingles:
            resultado.append(linea)
        elif resultado and not es_ingles and len(linea) > 10:
            resultado.append(linea)

    if resultado:
        return ' '.join(resultado[:3])  # Máximo 3 líneas

    # Fallback: última línea
    return lineas[-1] if lineas else texto


class YunaAgent:
    def __init__(self, confirm_callback=None):
        self.executor = ToolExecutor(confirm_callback)
        self.evaluator = ResultEvaluator(max_iterations=5)
        self.history = []

    def process(self, user_input: str) -> str:
        logger.info(f"Input: {user_input[:80]}")
        memoria = get_relevant_memory(user_input)

        # Contexto selector de herramientas
        ctx_selector = [{"role": "system", "content": SYSTEM_AGENT}]
        if memoria:
            ctx_selector[0]["content"] += f"\n\nCONTEXTO:\n{memoria}"
        for msg in self.history[-4:]:
            ctx_selector.append(msg)
        ctx_selector.append({"role": "user", "content": user_input})

        # Paso 1: qwen2.5:7b selecciona herramienta
        response = chat_with_tools(
            ctx_selector, ALL_SCHEMAS,
            model=MODEL_AGENT,
            num_predict=200,
            temperature=0.1
        )
        tool_calls = get_tool_calls(response)
        contenido = clean_response(response)

        # Respuesta directa sin herramienta
        if not tool_calls:
            if "DIRECTO:" in contenido:
                respuesta = contenido.split("DIRECTO:")[-1].strip()
            else:
                respuesta = _extraer_español(contenido) or contenido
            self._guardar(user_input, respuesta)
            return respuesta

        # Paso 2: ejecutar herramientas
        resultados_tools = []
        self.evaluator.reset()
        if self.evaluator.should_continue(tool_calls, contenido):
            resultados = self.executor.execute_batch(tool_calls)
            for name, error, result in resultados:
                if error:
                    resultados_tools.append(f"Error en {name}: {error}")
                    logger.error(f"Tool {name}: {error}")
                else:
                    resultados_tools.append(f"{name}: {str(result)[:800]}")
                    logger.info(f"Tool {name} OK")

        # Paso 3: qwen3:4b sintetiza SIN thinking
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
        respuesta = _extraer_español(respuesta) or respuesta

        self._guardar(user_input, respuesta)
        logger.info(f"Respuesta: {respuesta[:80]}")
        return respuesta

    def _guardar(self, user_input: str, respuesta: str):
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": respuesta})
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def reset(self):
        self.history = []
        self.evaluator.reset()
        logger.info("Agente reiniciado")
