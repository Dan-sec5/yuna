"""
core/agent.py — Agente Yuna V4 con auto-mejora
"""
import ast
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

SYSTEM_AGENT = """Eres el AGENTE PRINCIPAL de Yuna.

Tu trabajo es resolver la solicitud del usuario usando las herramientas
disponibles cuando sean necesarias.

Debes trabajar de forma iterativa:

1. Analiza la solicitud del usuario.
2. Si necesitas información real del sistema, usa la herramienta apropiada.
3. Después de recibir el resultado de una herramienta, analiza ese resultado.
4. Decide si necesitas otra herramienta para completar la solicitud.
5. Si ya tienes información suficiente, responde directamente al usuario.
6. Nunca reinicies el análisis como si los resultados de herramientas no existieran.

IMPORTANTE SOBRE LOS RESULTADOS DE HERRAMIENTAS:

Los mensajes de tipo "tool" contienen resultados reales obtenidos durante
esta misma solicitud.

Cuando recibas un resultado de una herramienta:
- úsalo como contexto válido;
- no lo ignores;
- no vuelvas a tratar la solicitud como una consulta nueva;
- si contiene la información solicitada, responde directamente;
- solamente solicita otra herramienta si realmente falta información.

La respuesta DIRECTO solamente puede utilizarse cuando NO se haya
ejecutado ninguna herramienta y realmente no exista una herramienta
disponible para resolver la solicitud.

IMPORTANTE:
Si ya recibiste uno o más resultados de herramientas, NO puedes responder
DIRECTO.

Debes analizar los resultados recibidos y responder usando esos datos.

Si leer_texto devuelve contenido del archivo, ese contenido es información
real y suficiente para analizarlo. No vuelvas a decir que no puedes
comprobarlo.

Si buscar_archivos encontró una ruta y después leer_texto devolvió contenido,
la respuesta final debe integrar ambos resultados.

Nunca descartes un resultado de herramienta que ya fue ejecutado.

REGLAS ABSOLUTAS:

1. Si el usuario pide información REAL del sistema, usa una herramienta.
2. Nunca inventes archivos, rutas, fechas, datos, resultados ni precios.
3. No respondas con información que una herramienta pueda comprobar.
4. No uses una herramienta diferente solo porque parezca relacionada.
5. Los argumentos deben representar exactamente lo que pidió el usuario.
6. Si el usuario especifica una extensión, usa buscar_archivos.
7. Si el usuario especifica un nombre o patrón, usa buscar_archivos.
8. Si el usuario pide LEER, ANALIZAR, EXPLICAR, REVISAR, INSPECCIONAR
   o DECIR QUÉ HACE un archivo, debes obtener primero su contenido.
9. Si ya existe una ruta explícita a un archivo y el usuario pide leerlo,
   usa directamente leer_texto con esa ruta.
10. Si el usuario proporciona una ruta de archivo que todavía no ha sido
    localizada, puedes usar buscar_archivos primero y después leer_texto.
11. Si buscar_archivos encuentra un único archivo y la solicitud requiere
    leer o analizar su contenido, el siguiente paso obligatorio es
    leer_texto sobre esa ruta.
12. Una cadena válida puede ser:
    buscar_archivos -> leer_texto -> respuesta.
13. No respondas DIRECTO después de buscar un archivo si el usuario
    todavía pidió leer o analizar su contenido.
14. Si el usuario pregunta por una función, clase, variable o contenido
    específico de un archivo, leer_texto es obligatorio antes de responder.
15. Si el usuario pregunta por archivos recientes o modificados durante
    determinado número de días, usa listar_recientes.
16. buscar_archivos y listar_recientes NO son intercambiables.

REGLAS DE UBICACIONES:

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
7. Una ruta explícita SIEMPRE debe conservarse literalmente.
8. Nunca reemplaces una ruta explícita por una ubicación equivalente.
9. "~/yuna" significa exactamente la carpeta raíz del proyecto Yuna.
10. Si el usuario dice "~/yuna", debes enviar "~/yuna" como argumento "carpeta".
11. Si el usuario proporciona una ruta como "~/yuna/core", "/tmp", "~/Proyectos"
    o "~/Documents", NO la conviertas en "home", "documentos" ni otra ubicación.
12. "home" solo debe usarse cuando el usuario diga explícitamente "home",
    "mi carpeta personal", "directorio personal" o equivalente.

REGLAS PARA ARCHIVOS:

buscar_archivos:
- Buscar archivos por extensión.
- Buscar archivos por nombre.
- Buscar archivos por patrón.
- Buscar recursivamente dentro de una carpeta.
- Usar cuando el usuario QUIERE ENCONTRAR o LOCALIZAR un archivo.

leer_texto:
- Usar cuando el usuario pide LEER, MOSTRAR, REVISAR, ANALIZAR,
  EXPLICAR o CONSULTAR EL CONTENIDO de un archivo de texto.
- Si el usuario proporciona una ruta explícita, usar esa ruta directamente.
- No usar buscar_archivos como sustituto de leer_texto.
- Si la ruta es relativa, debe interpretarse respecto a ~/yuna cuando
  el usuario esté trabajando dentro del proyecto Yuna.

REGLA CRÍTICA:

"busca core/agent.py"
-> buscar_archivos

"encuentra core/agent.py"
-> buscar_archivos

"lee core/agent.py"
-> leer_texto con ruta="core/agent.py"

"lee ~/yuna/core/agent.py"
-> leer_texto con ruta="~/yuna/core/agent.py"

"lee core/agent.py y dime qué hace la función process"
-> leer_texto con ruta="core/agent.py"
-> después de recibir el contenido, responde usando ese contenido.

NUNCA respondas:

DIRECTO: No tengo una herramienta para comprobar eso todavía.

cuando exista leer_texto y el usuario haya pedido leer un archivo.

IMPORTANTE:
Si el usuario pide analizar el contenido de un archivo, primero debes
obtener el contenido mediante la herramienta correspondiente y después
responder basándote exclusivamente en ese contenido.

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
   las ubicaciones reales resueltas dinámicamente.
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

def _respuesta_agente_valida(contenido: str, resultados_tools: list) -> bool:
    """
    Determina si la respuesta final de Qwen puede entregarse al usuario.

    Una respuesta DIRECTO no es válida después de ejecutar herramientas,
    porque significa que el modelo ignoró resultados reales ya disponibles.
    """
    if not contenido or not contenido.strip():
        return False

    texto = contenido.strip()

    if resultados_tools and texto.startswith(
        "DIRECTO: No tengo una herramienta"
    ):
        logger.warning(
            "Qwen devolvió DIRECTO después de ejecutar herramientas"
        )
        return False

    return True


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

        if not item.startswith(("buscar_archivos:", "listar_recientes:", "detectar_descargas:")):
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
        # DESCARGAS DETECTADAS
        # =====================================================

        if item.startswith("detectar_descargas:"):

            if not archivos:
                return (
                    "No encontré descargas con evidencia de "
                    "com.apple.quarantine en el periodo indicado."
                )

            nombres = []

            for archivo_encontrado in archivos:

                if not isinstance(archivo_encontrado, dict):
                    continue

                nombre = archivo_encontrado.get("nombre")
                ruta_archivo = archivo_encontrado.get("ruta")
                fecha = archivo_encontrado.get("descargado")

                if nombre:
                    if fecha:
                        nombres.append(
                            f"{nombre} | {fecha} | {ruta_archivo}"
                        )
                    else:
                        nombres.append(
                            f"{nombre} | fecha no disponible | {ruta_archivo}"
                        )

            if not nombres:
                return (
                    "Encontré evidencia de descargas, "
                    "pero no pude interpretar sus datos."
                )

            return (
                f"Encontré {len(nombres)} archivos con evidencia de descarga:\n"
                + "\n".join(
                    f"{i}. {nombre}"
                    for i, nombre in enumerate(nombres, 1)
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



# ============================================================
# ROUTER DETERMINISTA DE LECTURA DE ARCHIVOS
# ============================================================

_INTENCIONES_LECTURA = re.compile(
    r"\b("
    r"lee|leer|leeme|léeme|"
    r"analiza|analizar|"
    r"revisa|revisar|"
    r"explica|explicar|"
    r"inspecciona|inspeccionar|"
    r"consulta|consultar"
    r")\b",
    re.IGNORECASE
)

_RUTA_ARCHIVO = re.compile(
    r"(?<![\w])"
    r"((?:~|/|\.)?(?:[\w.-]+[/\\])+[\w.-]+"
    r"|(?:~|/|\.)?[\w.-]+\.[A-Za-z0-9_+-]+)"
    r"(?![\w])"
)


def _detectar_lectura_archivo(user_input: str):
    """
    Detecta solicitudes deterministas de lectura de archivos.

    Ejemplos válidos:

        Lee core/agent.py
        Lee ~/yuna/core/agent.py
        Analiza core/agent.py
        Revisa tools/archivos.py

    Devuelve la ruta o None.

    El router NO intenta interpretar la intención completa.
    Solo identifica una operación inequívoca:
        intención de lectura + ruta de archivo explícita.
    """

    if not user_input:
        return None

    if not _INTENCIONES_LECTURA.search(user_input):
        return None

    coincidencias = _RUTA_ARCHIVO.findall(user_input)

    if not coincidencias:
        return None

    ruta = coincidencias[-1].strip(
        " \t\n\r`'\".,;:()[]{}"
    )

    if not ruta:
        return None

    # Si el usuario proporciona una ruta relativa,
    # la resolvemos contra la raíz del proyecto Yuna.
    if not ruta.startswith(("/", "~")):
        ruta = f"~/yuna/{ruta}"

    return ruta




def _extraer_bloque_codigo(
    contenido: str,
    nombre: str,
    tipo: str = "funcion"
) -> str | None:
    """
    Extrae de forma determinista una función, método o clase
    desde código Python usando AST.

    El LLM no decide qué bloque analizar.
    Python identifica primero el bloque exacto.
    """

    # Normalizar el tipo para aceptar variantes con acentos
    # o llamadas que envíen None.
    tipo = (tipo or "funcion").strip().lower()
    tipo = (
        tipo
        .replace("ó", "o")
        .replace("é", "e")
    )



    if not contenido or not nombre:
        return None

    try:
        tree = ast.parse(contenido)

    except (SyntaxError, ValueError, TypeError) as e:
        logger.warning(
            f"No se pudo analizar código Python: {e}"
        )
        return None

    candidatos = []

    for nodo in ast.walk(tree):

        if tipo in {"funcion", "metodo"}:

            if isinstance(
                nodo,
                (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                if nodo.name == nombre:
                    candidatos.append(nodo)

        elif tipo == "clase":

            if isinstance(nodo, ast.ClassDef):
                if nodo.name == nombre:
                    candidatos.append(nodo)

    if not candidatos:
        return None

    nodo = candidatos[0]

    inicio = getattr(nodo, "lineno", None)
    fin = getattr(nodo, "end_lineno", None)

    if inicio is None or fin is None:
        return None

    lineas = contenido.splitlines()

    bloque = "\n".join(
        lineas[inicio - 1:fin]
    )

    return bloque.strip() or None


def _es_pregunta_contextual_codigo(pregunta: str) -> bool:
    """
    Detecta preguntas que necesitan conservar el contexto completo
    del archivo en lugar de extraer únicamente una función o clase.

    Ejemplos:
        ¿Qué hace process después de leer el archivo?
        ¿Qué ocurre después?
        ¿Cuáles son las etapas posteriores?
        ¿Qué pasa luego de ejecutar esto?
    """
    if not pregunta:
        return False

    texto = pregunta.lower()

    patrones = (
        "después",
        "despues",
        "luego",
        "posterior",
        "posteriormente",
        "qué ocurre después",
        "que ocurre despues",
        "qué pasa después",
        "que pasa despues",
        "qué hace después",
        "que hace despues",
        "qué ocurre luego",
        "que ocurre luego",
        "qué pasa luego",
        "que pasa luego",
        "etapas posteriores",
    )

    return any(patron in texto for patron in patrones)


def _es_seguimiento_lectura(pregunta: str) -> bool:
    """
    Detecta preguntas que probablemente continúan el análisis
    del último archivo leído en la sesión.
    """
    if not pregunta:
        return False

    texto = pregunta.lower()

    referencias = (
        "archivo",
        "función",
        "funcion",
        "método",
        "metodo",
        "clase",
        "process",
        "código",
        "codigo",
    )

    seguimiento = (
        "después",
        "despues",
        "antes",
        "luego",
        "posterior",
        "anterior",
        "qué hace",
        "que hace",
        "cómo funciona",
        "como funciona",
        "cuáles son",
        "cuales son",
        "qué ocurre",
        "que ocurre",
    )

    tiene_referencia = any(x in texto for x in referencias)
    es_seguimiento = any(x in texto for x in seguimiento)

    return tiene_referencia or es_seguimiento


def _extraer_nombre_elemento_codigo(
    pregunta: str
) -> tuple[str | None, str | None]:
    """
    Detecta consultas sobre funciones, métodos o clases.

    Ejemplos reconocidos:

        función process
        funcion process
        método process
        metodo process
        def process
        clase YunaAgent

    Devuelve:

        (nombre, tipo)

    """

    if not pregunta:
        return None, None

    patrones = [
        (
            r"\bfunci[oó]n\s+([A-Za-z_][A-Za-z0-9_]*)",
            "funcion"
        ),
        (
            r"\bm[eé]todo\s+([A-Za-z_][A-Za-z0-9_]*)",
            "metodo"
        ),
        (
            r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)",
            "funcion"
        ),
        (
            r"\bclase\s+([A-Za-z_][A-Za-z0-9_]*)",
            "clase"
        ),
    ]

    for patron, tipo in patrones:

        match = re.search(
            patron,
            pregunta,
            re.IGNORECASE
        )

        if match:
            return match.group(1), tipo

    return None, None


class YunaAgent:
    def __init__(self, confirm_callback=None):
        self.executor = ToolExecutor(confirm_callback)
        self.evaluator = ResultEvaluator(max_iterations=5)
        self.learner = LearningEngine()
        self.history = []

        # Contexto de la última lectura de archivo durante la sesión.
        # Permite responder preguntas de seguimiento sin repetir la ruta.
        self._ultima_lectura = None

        # Último elemento de código analizado durante la sesión.
        # Permite responder preguntas de seguimiento como:
        # "¿Qué hace process después?"
        self._ultimo_elemento_codigo = None

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
        if name in {"buscar_archivos", "listar_recientes", "detectar_descargas"}:
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

    def _ejecutar_tool_loop(
        self,
        messages,
        max_steps: int = 5
    ):
        """
        Ejecuta el ciclo multi-step de tool calling.

        Flujo:

            LLM
             ↓
            tool call
             ↓
            Executor
             ↓
            resultado
             ↓
            LLM
             ↓
            siguiente decisión

        El ciclo termina cuando:

        - el LLM deja de solicitar herramientas
        - se alcanza max_steps
        - se detecta una llamada idéntica repetida
        """

        resultados_tools = []
        tool_names = []

        llamadas_vistas = set()

        for step in range(max_steps):

            logger.info(
                f"Tool loop paso {step + 1}/{max_steps}"
            )

            response = chat_with_tools(
                messages,
                ALL_SCHEMAS,
                model=MODEL_AGENT,
                num_predict=400,
                temperature=0.1
            )

            if response is None:
                logger.error(
                    "Tool loop: Ollama no devolvió respuesta"
                )
                return None, resultados_tools, tool_names


            tool_calls = get_tool_calls(response)

            # -------------------------------------------------
            # No hay más herramientas
            # -------------------------------------------------

            if not tool_calls:
                logger.info(
                    "Tool loop finalizado: LLM no solicitó más tools"
                )

                return response, resultados_tools, tool_names

            logger.info(
                f"Tool calls detectados: {len(tool_calls)}"
            )

            # -------------------------------------------------
            # PRESERVAR MENSAJE ASSISTANT + TOOL CALLS
            # -------------------------------------------------
            #
            # Ollama devuelve los tool_calls dentro de
            # response.message. Ese mensaje debe formar parte
            # del contexto ANTES de enviar los resultados
            # de las herramientas.
            #
            # Sin esto:
            #
            #   user -> assistant(tool_call) -> tool
            #
            # se convertía accidentalmente en:
            #
            #   user -> tool
            #
            # y Qwen podía interpretar el resultado como texto
            # aislado y abandonar el ciclo multi-tool.
            #
            assistant_message = {
                "role": "assistant",
                "content": getattr(
                    response.message,
                    "content",
                    ""
                ) or "",
                "tool_calls": [
                    {
                        "function": {
                            "name": call["name"],
                            "arguments": call["arguments"]
                        }
                    }
                    for call in tool_calls
                ]
            }

            messages.append(assistant_message)

            logger.info(
                "Mensaje assistant con %d tool_call(s) "
                "agregado al contexto",
                len(tool_calls)
            )

            llamadas_actuales = []

            # -------------------------------------------------
            # Validación de llamadas
            # -------------------------------------------------

            for call in tool_calls:

                name = call.get("name", "")
                args = call.get(
                    "arguments",
                    call.get("args", {})
                )

                if not isinstance(args, dict):
                    args = {}

                firma = (
                    name,
                    tuple(sorted(args.items()))
                )

                # ---------------------------------------------
                # Protección contra loop infinito
                # ---------------------------------------------

                if firma in llamadas_vistas:

                    logger.warning(
                        f"Tool call repetido detectado: "
                        f"{name}({args})"
                    )

                    mensaje = (
                        f"Se detuvo el ciclo porque la herramienta "
                        f"'{name}' fue solicitada nuevamente con "
                        f"los mismos argumentos."
                    )

                    resultados_tools.append(mensaje)

                    return (
                        response,
                        resultados_tools,
                        tool_names
                    )

                llamadas_vistas.add(firma)
                llamadas_actuales.append(call)

            # -------------------------------------------------
            # Ejecutar herramientas
            # -------------------------------------------------

            resultados = self.executor.execute_batch(
                llamadas_actuales
            )

            mensajes_tool = []

            for name, error, result in resultados:

                tool_names.append(name)

                if error:

                    texto = (
                        f"Error en {name}: {error}"
                    )

                    logger.error(texto)

                    self.session_stats["success"] = False

                    self.learner.record_lesson(
                        messages[-1].get("content", ""),
                        name,
                        error,
                        success=False
                    )

                else:

                    texto = self._formatear_resultado_tool(
                        name,
                        result
                    )

                    logger.info(
                        f"Tool {name} OK"
                    )

                    self.session_stats[
                        "tools_used"
                    ].append(name)

                    self.learner.record_lesson(
                        messages[-1].get("content", ""),
                        name,
                        str(result)[:200],
                        success=True
                    )

                resultados_tools.append(texto)

                # ---------------------------------------------
                # Resultado vuelve al contexto del LLM
                # ---------------------------------------------

                mensajes_tool.append({
                    "role": "tool",
                    "name": name,
                    "content": texto
                })

            messages.extend(mensajes_tool)

        # -----------------------------------------------------
        # Máximo de pasos alcanzado
        # -----------------------------------------------------

        logger.warning(
            f"Tool loop detenido por límite de "
            f"{max_steps} pasos"
        )

        resultados_tools.append(
            "[TOOL_LOOP_LIMIT] "
            f"Se alcanzó el máximo de {max_steps} pasos."
        )

        return (
            None,
            resultados_tools,
            tool_names
        )

    def process(self, user_input: str) -> str:
        start_time = time.time()

        self.session_stats["tools_used"] = []
        self.session_stats["success"] = True

        logger.info(f"Input: {user_input[:80]}")

        # ---------------------------------------------------------
        # ROUTER DETERMINISTA
        # ---------------------------------------------------------
        #
        # Si el usuario proporciona explícitamente una ruta y pide
        # leer/analizar/revisar el archivo, no dejamos esta decisión
        # básica en manos del LLM.
        #
        # El LLM sigue siendo responsable de interpretar y explicar
        # el contenido obtenido.
        # ---------------------------------------------------------

        ruta_lectura = _detectar_lectura_archivo(user_input)

        # ---------------------------------------------------------
        # REUTILIZAR ÚLTIMA LECTURA
        # ---------------------------------------------------------
        #
        # Si la pregunta no contiene nuevamente la ruta pero parece
        # continuar el análisis anterior, reutilizamos el archivo
        # que ya fue leído durante esta sesión.
        #
        reutilizar_lectura = False
        texto_archivo = None

        if (
            not ruta_lectura
            and self._ultima_lectura
            and _es_seguimiento_lectura(user_input)
        ):
            ruta_lectura = self._ultima_lectura["ruta"]
            texto_archivo = self._ultima_lectura["contenido"]
            reutilizar_lectura = True

            logger.info(
                "Router determinista -> reutilizando última lectura "
                f"({ruta_lectura})"
            )

        if ruta_lectura:

            if reutilizar_lectura:
                error = None
                resultado = texto_archivo
            else:
                logger.info(
                    f"Router determinista -> leer_texto({ruta_lectura})"
                )

                error, resultado = self.executor.execute(
                    "leer_texto",
                    {"ruta": ruta_lectura}
                )

            if error:
                logger.error(
                    f"Error leyendo archivo: {error}"
                )

                respuesta = (
                    f"No pude leer el archivo "
                    f"`{ruta_lectura}`: {error}"
                )

                self._guardar(
                    user_input,
                    respuesta,
                    direct=False
                )

                self._record_metrics(
                    start_time,
                    user_input,
                    respuesta,
                    ["leer_texto"],
                    False
                )

                return respuesta

            texto_archivo = str(resultado)

            # Conservar la lectura para preguntas de seguimiento
            # dentro de la misma sesión.
            self._ultima_lectura = {
                "ruta": ruta_lectura,
                "contenido": texto_archivo,
            }

            self.session_stats["tools_used"].append(
                "leer_texto"
            )

            self.learner.record_lesson(
                user_input,
                "leer_texto",
                texto_archivo[:200],
                success=True
            )

            # Limitar únicamente el contexto enviado al LLM.
            # La herramienta sigue leyendo el archivo completo,
            # pero evitamos desbordar el contexto de Qwen.
            MAX_CONTENIDO_ANALISIS = 30000

            contenido_para_llm = texto_archivo

            # -------------------------------------------------
            # EXTRACCIÓN DETERMINISTA DE CÓDIGO
            # -------------------------------------------------
            #
            # Si el usuario solicita una función, método o clase
            # concreta, Python localiza primero el bloque exacto.
            #
            # El LLM recibe el bloque relevante, no el archivo
            # completo.
            #
            # Esto evita respuestas como:
            #
            #   {contenido_para_llm}
            #   {user_input}
            #
            # y evita que Qwen tenga que localizar código dentro
            # de cientos o miles de líneas.
            # -------------------------------------------------

            nombre_elemento, tipo_elemento = (
                _extraer_nombre_elemento_codigo(
                    user_input
                )
            )

            # Si la pregunta actual no vuelve a mencionar
            # "función", "método", "clase" o "def", pero continúa
            # hablando del elemento anterior, reutilizamos ese
            # elemento de forma determinista.
            if (
                not nombre_elemento
                and self._ultimo_elemento_codigo
                and _es_seguimiento_lectura(user_input)
            ):
                nombre_elemento = self._ultimo_elemento_codigo["nombre"]
                tipo_elemento = self._ultimo_elemento_codigo["tipo"]

                logger.info(
                    "Reutilizando último elemento de código: "
                    f"{tipo_elemento} {nombre_elemento}"
                )

            if nombre_elemento:

                bloque = _extraer_bloque_codigo(
                    texto_archivo,
                    nombre_elemento,
                    tipo=tipo_elemento
                )

                if bloque:

                    self._ultimo_elemento_codigo = {
                        "nombre": nombre_elemento,
                        "tipo": tipo_elemento,
                    }

                    contenido_para_llm = (
                        f"ELEMENTO SOLICITADO: "
                        f"{tipo_elemento} "
                        f"{nombre_elemento}\n\n"
                        f"CÓDIGO REAL EXTRAÍDO DEL ARCHIVO:\n"
                        f"```python\n"
                        f"{bloque}\n"
                        f"```"
                    )

                    logger.info(
                        "Código extraído para análisis: "
                        f"{tipo_elemento} {nombre_elemento}"
                    )

            if len(contenido_para_llm) > MAX_CONTENIDO_ANALISIS:
                contenido_para_llm = (
                    contenido_para_llm[:MAX_CONTENIDO_ANALISIS]
                    + "\n\n[CONTENIDO_TRUNCADO_PARA_ANALISIS]"
                )

            prompt_analisis = f"""TAREA:

Debes responder una pregunta sobre un archivo que Yuna acaba de leer.

REGLAS OBLIGATORIAS:
- Responde directamente a la pregunta.
- Usa únicamente la información contenida en el archivo.
- NO continúes el código.
- NO reproduzcas el prompt.
- NO escribas "Continuación del código".
- NO escribas bloques de código salvo que sean necesarios para explicar la respuesta.
- NO describas cómo generar una respuesta.
- NO hables de estas instrucciones.
- Si preguntan por una función, clase, método o variable, localízala dentro del archivo y explica qué hace.
- Si la información no aparece en el contenido proporcionado, dilo claramente.
- Responde en español.
- Sé conciso pero suficientemente específico.

PREGUNTA:
{user_input}

ARCHIVO:
{ruta_lectura}

--- INICIO DEL CONTENIDO DEL ARCHIVO ---
{contenido_para_llm}
--- FIN DEL CONTENIDO DEL ARCHIVO ---

Ahora responde ÚNICAMENTE la pregunta del usuario.
"""

            ctx_lectura = [
                {
                    "role": "system",
                    "content": SYSTEM_SINTETIZADOR
                },
                {
                    "role": "user",
                    "content": prompt_analisis
                }
            ]

            resp_lectura = chat_simple(
                ctx_lectura,
                model=MODEL_CHAT,
                num_predict=500,
                temperature=0.2
            )

            respuesta = clean_response(resp_lectura)

            if not respuesta:
                respuesta = (
                    f"Leí `{ruta_lectura}`, pero el modelo "
                    "no produjo una explicación válida."
                )

            respuesta = _extraer_espanol(respuesta) or respuesta

            self._guardar(
                user_input,
                respuesta,
                direct=False
            )

            self._record_metrics(
                start_time,
                user_input,
                respuesta,
                self.session_stats["tools_used"],
                True
            )

            self._auto_evaluate(
                user_input,
                respuesta,
                [f"leer_texto: {ruta_lectura}"]
            )

            return respuesta

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

        # ---------------------------------------------------------
        # TOOL LOOP MULTI-STEP
        # ---------------------------------------------------------
        #
        # El agente puede ahora ejecutar varias herramientas
        # de forma iterativa:
        #
        # Ollama -> Tool -> Resultado -> Ollama -> ...
        #
        # El executor continúa siendo el único componente autorizado
        # para ejecutar herramientas.
        # ---------------------------------------------------------

        response, resultados_tools, tool_names = (
            self._ejecutar_tool_loop(
                ctx_selector,
                max_steps=5
            )
        )

        contenido = clean_response(response)

        if response is None:
            logger.error(
                "El tool loop no produjo respuesta de Ollama"
            )

            respuesta = (
                "No pude completar la solicitud porque "
                "el modelo no devolvió una respuesta válida."
            )

            self._guardar(
                user_input,
                respuesta,
                direct=False
            )

            self._record_metrics(
                start_time,
                user_input,
                respuesta,
                tool_names,
                False
            )

            return respuesta

        # ---------------------------------------------------------
        # RESPUESTA FINAL DEL AGENTE
        # ---------------------------------------------------------
        #
        # _ejecutar_tool_loop() ya devuelve la respuesta final de Qwen.
        #
        # Si Qwen terminó correctamente después de usar herramientas,
        # esa respuesta es la fuente principal y NO debe ser reemplazada
        # por una segunda llamada al modelo.
        #
        # Esto preserva el contexto completo:
        #
        # usuario -> tool -> resultado -> Qwen -> respuesta
        #
        # La síntesis determinista queda únicamente como fallback para
        # casos donde Qwen no produjo contenido útil.
        # ---------------------------------------------------------

        if _respuesta_agente_valida(contenido, resultados_tools):
            respuesta = contenido

            self._guardar(
                user_input,
                respuesta,
                direct=False
            )

            self._record_metrics(
                start_time,
                user_input,
                respuesta,
                self.session_stats["tools_used"],
                True
            )

            self._auto_evaluate(
                user_input,
                respuesta,
                resultados_tools
            )

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
