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

SYSTEM_AGENT = """Eres el SELECTOR DE HERRAMIENTAS de Yuna.

Tu trabajo es determinar si la solicitud del usuario requiere una herramienta
y, si la requiere, llamar EXACTAMENTE a la herramienta correcta.

REGLAS ABSOLUTAS:

1. Si el usuario pide información REAL del sistema, usa una herramienta.
2. Nunca inventes archivos, rutas, fechas, datos, resultados ni precios.
3. No respondas con información que una herramienta pueda comprobar.
4. No uses una herramienta diferente solo porque parezca relacionada.
5. Los argumentos deben representar exactamente lo que pidió el usuario.
6. Si el usuario especifica una extensión, usa buscar_archivos.
7. Si el usuario especifica un nombre o patrón, usa buscar_archivos.
8. Si el usuario pregunta por archivos recientes o modificados durante
   determinado número de días, usa listar_recientes.
9. buscar_archivos y listar_recientes NO son intercambiables.

REGLAS PARA ARCHIVOS:

buscar_archivos:
- Buscar por extensión.
- Buscar por nombre.
- Buscar por patrón.
- Buscar recursivamente dentro de una carpeta.

Ejemplos:
"busca todos los PDFs" -> buscar_archivos con *.pdf
"busca Excel" -> buscar_archivos con *.xlsx
"busca archivos llamados reporte" -> buscar_archivos con *reporte*

listar_recientes:
- Solo para solicitudes basadas en tiempo.
- "qué archivos modifiqué recientemente"
- "qué archivos cambiaron en los últimos 30 días"
- "archivos recientes"

IMPORTANTE:
"modificado recientemente" NO significa "descargado recientemente".
La herramienta listar_recientes informa archivos modificados.

Si no existe una herramienta apropiada, responde exactamente:

DIRECTO: No tengo una herramienta para comprobar eso todavía.

NO expliques tu razonamiento.
NO describas lo que harías.
NO inventes resultados.
"""


SYSTEM_SINTETIZADOR = """Eres Yuna, agente IA personal de Luis.

REGLAS ABSOLUTAS:

1. Los DATOS proporcionados son la única fuente de verdad.
2. Nunca conviertas una propiedad en otra.
3. "modificado" significa MODIFICADO.
4. "creado" significa CREADO.
5. "descargado" significa DESCARGADO.
6. Si los datos dicen "modificado", NO digas "descargado".
7. Si la pregunta solicita un dato que los resultados no contienen,
   debes decir que no puede determinarse con los datos disponibles.
8. Nunca infieras que un archivo fue descargado porque está dentro de
   ~/Downloads.
9. Nunca inventes archivos, fechas, tamaños, rutas ni cantidades.
10. No agregues información que no aparezca en los datos.
11. Responde en español mexicano, directamente y sin razonamiento.

IMPORTANTE:
Si el usuario pregunta "¿qué archivos descargué?" y los resultados
solo contienen archivos "modificados", debes decir que no es posible
determinar cuáles fueron descargados con esos datos.
"""


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

def _respuesta_archivos_determinista(user_input: str, resultados_tools: list):
    """
    Genera respuestas deterministas para herramientas de archivos.

    buscar_archivos() devuelve una lista de rutas:
        ["/ruta/a.pdf", "/ruta/b.pdf"]

    listar_recientes() devuelve una lista de diccionarios:
        [{"nombre": "...", "ruta": "...", "modificado": "..."}]
    """

    if not resultados_tools:
        return None

    pregunta = user_input.lower()

    for item in resultados_tools:

        if not isinstance(item, str):
            continue

        if not item.startswith(("buscar_archivos:", "listar_recientes:")):
            continue

        try:
            _, datos = item.split(":", 1)
            datos = datos.strip()

            if not datos or datos == "[]":
                return "No encontré nada"

            # Primero intentamos JSON, que es el formato oficial
            # producido por _formatear_resultado_tool().
            try:
                archivos = json.loads(datos)
            except (json.JSONDecodeError, TypeError, ValueError):
                # Compatibilidad con resultados antiguos.
                try:
                    import ast
                    archivos = ast.literal_eval(datos)
                except (SyntaxError, ValueError, TypeError):
                    logger.warning(
                        "No se pudo interpretar resultado de archivos"
                    )
                    return None

            if not isinstance(archivos, list):
                return None

        except Exception as e:
            logger.warning(
                f"No se pudo interpretar resultado de archivos: {e}"
            )
            return None

        # =====================================================
        # BUSCAR ARCHIVOS
        # =====================================================

        if item.startswith("buscar_archivos:"):

            if not archivos:
                return "No encontré nada"

            rutas = []

            for archivo_encontrado in archivos:

                # buscar_archivos devuelve rutas directamente
                if isinstance(archivo_encontrado, str):
                    rutas.append(archivo_encontrado)

                # Compatibilidad por si en el futuro devuelve dicts
                elif isinstance(archivo_encontrado, dict):
                    ruta = (
                        archivo_encontrado.get("ruta")
                        or archivo_encontrado.get("nombre")
                    )

                    if ruta:
                        rutas.append(str(ruta))

            if not rutas:
                return "No encontré nada"

            return (
                f"Encontré {len(rutas)} archivos:\n"
                + "\n".join(
                    f"{i}. {ruta}"
                    for i, ruta in enumerate(rutas, 1)
                )
            )

        # =====================================================
        # ARCHIVOS RECIENTES
        # =====================================================

        if item.startswith("listar_recientes:"):

            # IMPORTANTE:
            # listar_recientes informa MODIFICACIÓN.
            # No demuestra que un archivo haya sido descargado.

            if any(
                palabra in pregunta
                for palabra in [
                    "descargué",
                    "descargue",
                    "descargados",
                    "descargado",
                    "descargas",
                ]
            ):
                return (
                    "No puedo determinar qué archivos fueron descargados. "
                    "La herramienta disponible solo informa archivos "
                    "modificados en los últimos días."
                )

            if not archivos:
                return "No encontré nada"

            nombres = []

            for archivo_encontrado in archivos:

                if isinstance(archivo_encontrado, dict):
                    nombre = (
                        archivo_encontrado.get("nombre")
                        or archivo_encontrado.get("ruta")
                    )

                    if nombre:
                        nombres.append(str(nombre))

                elif isinstance(archivo_encontrado, str):
                    nombres.append(archivo_encontrado)

            if not nombres:
                return "No encontré nada"

            return (
                f"Encontré {len(nombres)} archivos modificados recientemente:\n"
                + "\n".join(
                    f"{i}. {nombre}"
                    for i, nombre in enumerate(nombres, 1)
                )
            )

    return None


class YunaAgent:
    def __init__(self, confirm_callback=None):
        self.executor = ToolExecutor(confirm_callback)
        self.evaluator = ResultEvaluator(max_iterations=5)
        self.learner = LearningEngine()
        self.history = []
        self.session_stats = {"tools_used": [], "success": True, "latency": 0}

    @staticmethod
    def _formatear_resultado_tool(name: str, result) -> str:
        """
        Serializa resultados de herramientas de forma estable.

        Las herramientas de archivos se conservan completas y en JSON
        para que las respuestas deterministas puedan reconstruirlas
        sin depender de ast.literal_eval().
        """

        if result is None:
            return f"{name}: null"

        # Herramientas de archivos:
        # conservar el resultado completo y estructurado.
        if name in {"buscar_archivos", "listar_recientes"}:
            try:
                texto = json.dumps(
                    result,
                    ensure_ascii=False
                )
            except (TypeError, ValueError):
                texto = repr(result)

            return f"{name}: {texto}"

        # Otras herramientas.
        try:
            texto = json.dumps(
                result,
                ensure_ascii=False
            )
        except (TypeError, ValueError):
            texto = str(result)

        if len(texto) > 12000:
            texto = (
                texto[:12000]
                + "\n[RESULTADO_TRUNCADO_POR_TAMAÑO]"
            )

        return f"{name}: {texto}"

    def process(self, user_input: str) -> str:
        start_time = time.time()

        self.session_stats["tools_used"] = []
        self.session_stats["success"] = True

        logger.info(f"Input: {user_input[:80]}")
        memoria = get_relevant_memory(user_input, top_k=5)

        # Consultar experiencias previas para orientar la selección de herramientas.
        herramientas_aprendidas = self.learner.get_best_tools_for(user_input)

        if herramientas_aprendidas:
            memoria += (
                "\n\nHERRAMIENTAS APRENDIDAS PARA ESTA CONSULTA:\n"
                + "\n".join(
                    f"- {tool}" for tool in herramientas_aprendidas
                )
            )

        ctx_selector = [{"role": "system", "content": SYSTEM_AGENT}]
        if memoria:
            ctx_selector[0]["content"] += (
                "\n\nCONTEXTO SECUNDARIO:\n"
                "Este contexto puede ayudar a comprender la solicitud, "
                "pero NO determina qué herramienta usar y NO es una fuente "
                "de datos actuales del sistema.\n"
                + memoria
            )
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
                    resultados_tools.append(
                        self._formatear_resultado_tool(name, result)
                    )
                    logger.info(f"Tool {name} OK")
                    self.session_stats["tools_used"].append(name)
                    self.learner.record_lesson(user_input, name, str(result)[:200], success=True)

        # ---------------------------------------------------------
        # Respuestas deterministas para herramientas de archivos
        # ---------------------------------------------------------

        respuesta_determinista = _respuesta_archivos_determinista(
            user_input,
            resultados_tools
        )

        if respuesta_determinista is not None:
            respuesta = respuesta_determinista

            self._guardar(user_input, respuesta, direct=False)
            self._record_metrics(
                start_time,
                user_input,
                respuesta,
                self.session_stats["tools_used"],
                True
            )

            logger.info(f"Respuesta determinista: {respuesta[:80]}")
            return respuesta

        datos = "\n".join(resultados_tools) if resultados_tools else "Sin datos"
        prompt = f"""PREGUNTA DEL USUARIO:
{user_input}

DATOS REALES OBTENIDOS DE LAS HERRAMIENTAS:
{datos}

INSTRUCCIÓN:
Responde la pregunta usando exclusivamente los datos anteriores.
Si los datos no contienen la información solicitada, dilo claramente.
No completes información faltante con suposiciones.
"""
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
