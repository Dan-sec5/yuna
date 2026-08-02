#!/bin/zsh
# fix_yuna.sh — Aplica todas las correcciones a Yuna en macOS
# Ejecutar: cd ~/yuna && zsh fix_yuna.sh

set -e

echo "🔧 Aplicando correcciones a Yuna..."

# ============================================
# 1. core/llm.py — Regex corregido, timeouts
# ============================================
cat > core/llm.py << 'PYEOF'
"""
core/llm.py — Wrapper Ollama con think=False para Qwen3
"""
import ollama
import logging
import re
from core.logger import get_logger
from typing import List, Dict, Any, Optional
from config import CONFIG

logger = get_logger(__name__)

MODEL_AGENT = CONFIG["models"].get("agent", "qwen3:8b")
MODEL_CHAT = CONFIG["models"].get("chat", "qwen3:8b")
OLLAMA_HOST = CONFIG["ollama"].get("host", "http://localhost:11434")
KEEP_ALIVE = CONFIG["ollama"].get("keep_alive", "30m")

client = ollama.Client(host=OLLAMA_HOST)

def _is_thinking_model(model: str) -> bool:
    thinking_models = ["qwen3", "deepseek-r1", "deepseek-v3", "gemma4", "gpt-oss"]
    return any(tm in model.lower() for tm in thinking_models)

def _get_options(model: str, extra_options: dict) -> dict:
    opts = {
        "num_predict": 400,
        "temperature": 0.2,
        "num_ctx": 4096,
        "keep_alive": KEEP_ALIVE,
    }
    opts.update(extra_options)
    if _is_thinking_model(model):
        opts["think"] = False
        logger.debug(f"Thinking desactivado para {model}")
    return opts

def preload_model(model: str = None):
    model = model or MODEL_AGENT
    try:
        client.chat(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            options={"num_predict": 1, "keep_alive": KEEP_ALIVE},
            think=False if _is_thinking_model(model) else None,
        )
        logger.info(f"Modelo {model} precargado en RAM")
    except Exception as e:
        logger.warning(f"No se pudo precargar {model}: {e}")

def chat_with_tools(
    messages: List[Dict],
    tools: List[Dict],
    model: str = None,
    **options
) -> Any:
    model = model or MODEL_AGENT
    opts = _get_options(model, options)
    kwargs = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "options": opts,
    }
    if _is_thinking_model(model):
        kwargs["think"] = False
    try:
        import socket
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(opts.get("timeout", 120))
        try:
            return client.chat(**kwargs)
        finally:
            socket.setdefaulttimeout(original_timeout)
    except ollama.ResponseError as e:
        logger.error(f"Ollama error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return None

def chat_simple(
    messages: List[Dict],
    model: str = None,
    **options
) -> Any:
    model = model or MODEL_CHAT
    opts = _get_options(model, options)
    kwargs = {
        "model": model,
        "messages": messages,
        "options": opts,
    }
    if _is_thinking_model(model):
        kwargs["think"] = False
    try:
        import socket
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(opts.get("timeout", 120))
        try:
            return client.chat(**kwargs)
        finally:
            socket.setdefaulttimeout(original_timeout)
    except Exception as e:
        logger.error(f"Error en chat simple: {e}")
        return None

def clean_response(response: Any) -> str:
    if response is None:
        return ""
    if hasattr(response, "message"):
        content = getattr(response.message, "content", "") or ""
    elif isinstance(response, dict):
        content = response.get("message", {}).get("content", "") or ""
    else:
        content = str(response)
    # FIX: Regex correcto para thinking tags
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    content = re.sub(r'^(Okay[,]?|Alright|Sure|Let me|So[,]?|First|Hmm|Well)[,\s]*', '', content, flags=re.IGNORECASE)
    if "...done thinking." in content:
        content = content.split("...done thinking.")[-1]
    return content.strip()

def get_tool_calls(response: Any) -> List[Dict]:
    if response is None:
        return []
    if hasattr(response, "message"):
        calls = getattr(response.message, "tool_calls", None) or []
        result = []
        for call in calls:
            func = getattr(call, "function", None)
            if not func:
                continue
            name = getattr(func, "name", None)
            arguments = getattr(func, "arguments", {}) or {}
            if name:
                result.append({"name": name, "arguments": arguments})
        return result
    if isinstance(response, dict):
        msg = response.get("message", {})
        calls = msg.get("tool_calls") or []
        result = []
        for call in calls:
            func = call.get("function", {})
            name = func.get("name")
            if name:
                result.append({
                    "name": name,
                    "arguments": func.get("arguments", {})
                })
        return result
    return []
PYEOF

# ============================================
# 2. core/learning.py — Motor de auto-mejora (NUEVO)
# ============================================
cat > core/learning.py << 'PYEOF'
"""
core/learning.py — Sistema de auto-mejora de Yuna
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from config import get

DB_PATH = Path(get("paths.memory_db", "~/yuna/data/yuna.db")).expanduser()

class LearningEngine:
    def __init__(self):
        self._init_tables()

    def _init_tables(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    query_pattern TEXT,
                    tool_name TEXT,
                    outcome TEXT,
                    success BOOLEAN,
                    count INTEGER DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS idx_lessons_pattern ON lessons(query_pattern);
                CREATE INDEX IF NOT EXISTS idx_lessons_tool ON lessons(tool_name);
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    query TEXT,
                    response TEXT,
                    feedback TEXT,
                    score INTEGER
                );
                CREATE TABLE IF NOT EXISTS interaction_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    query TEXT,
                    response TEXT,
                    tools_used TEXT,
                    success BOOLEAN,
                    latency_ms REAL
                );
            """)

    def record_lesson(self, query: str, tool_name: str, outcome: str, success: bool):
        pattern = self._extract_pattern(query)
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                "SELECT id, count FROM lessons WHERE query_pattern = ? AND tool_name = ? AND success = ?",
                (pattern, tool_name, success)
            )
            row = cur.fetchone()
            if row:
                conn.execute(
                    "UPDATE lessons SET count = count + 1, timestamp = CURRENT_TIMESTAMP WHERE id = ?",
                    (row[0],)
                )
            else:
                conn.execute(
                    "INSERT INTO lessons (query_pattern, tool_name, outcome, success) VALUES (?, ?, ?, ?)",
                    (pattern, tool_name, outcome, success)
                )

    def record_user_feedback(self, query: str, feedback: str, response: str = ""):
        score = 1 if feedback in ("up", "positive", "👍", "bueno", "util") else -1
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO user_feedback (query, response, feedback, score) VALUES (?, ?, ?, ?)",
                (query[:500], response[:500], feedback, score)
            )

    def get_lessons_for_query(self, query: str, limit: int = 3) -> List[Dict]:
        pattern = self._extract_pattern(query)
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                """SELECT query_pattern, tool_name, success, count FROM lessons
                   WHERE query_pattern LIKE ? OR ? LIKE '%' || query_pattern || '%'
                   ORDER BY count DESC, timestamp DESC LIMIT ?""",
                (f"%{pattern}%", pattern, limit)
            )
            return [
                {"pattern": r[0], "tool": r[1], "success": bool(r[2]), "count": r[3]}
                for r in cur.fetchall()
            ]

    def get_best_tools_for(self, query: str) -> List[str]:
        lessons = self.get_lessons_for_query(query, limit=10)
        tool_scores = {}
        for l in lessons:
            if l["tool"] not in tool_scores:
                tool_scores[l["tool"]] = {"success": 0, "fail": 0}
            if l["success"]:
                tool_scores[l["tool"]]["success"] += l["count"]
            else:
                tool_scores[l["tool"]]["fail"] += l["count"]
        ranked = []
        for tool, scores in tool_scores.items():
            total = scores["success"] + scores["fail"]
            if total > 0:
                rate = scores["success"] / total
                ranked.append((tool, rate, total))
        ranked.sort(key=lambda x: (-x[1], -x[2]))
        return [t[0] for t in ranked[:3]]

    def _extract_pattern(self, query: str) -> str:
        stopwords = {"el", "la", "los", "las", "un", "una", "de", "en", "con", "por", "para", "que", "me", "mi", "yo"}
        words = [w.lower() for w in query.split() if len(w) > 3 and w.lower() not in stopwords]
        return " ".join(words[:3])
PYEOF

# ============================================
# 3. core/agent.py — Agente con auto-mejora
# ============================================
cat > core/agent.py << 'PYEOF'
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
PYEOF

# ============================================
# 4. core/evaluator.py — Evaluación real
# ============================================
cat > core/evaluator.py << 'PYEOF'
from typing import List, Dict, Any, Tuple

class ResultEvaluator:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.iteration = 0
        self.tool_success_rate = []

    def reset(self):
        self.iteration = 0
        self.tool_success_rate = []

    def should_continue(self, tool_calls: List[Dict], content: str) -> bool:
        if self.iteration >= self.max_iterations:
            return False
        self.iteration += 1
        return bool(tool_calls)

    def evaluate_tool_result(self, tool_name: str, error: Any, result: Any) -> bool:
        success = error is None
        if success and result:
            result_str = str(result).lower()
            if any(x in result_str for x in ["no se encontró", "vacío", "error", "no hay", "[]"]):
                success = False
        self.tool_success_rate.append((tool_name, success))
        return success

    def get_session_quality(self) -> Dict[str, Any]:
        if not self.tool_success_rate:
            return {"success_rate": 1.0, "tools_used": 0, "recommendation": "direct_response"}
        total = len(self.tool_success_rate)
        successful = sum(1 for _, s in self.tool_success_rate if s)
        rate = successful / total
        recommendation = "continue"
        if rate < 0.5 and total >= 2:
            recommendation = "try_different_tools"
        elif rate == 1.0 and total > 0:
            recommendation = "good_pattern"
        return {
            "success_rate": rate,
            "tools_used": total,
            "recommendation": recommendation
        }

    def build_context(self, results: List[Tuple]) -> str:
        parts = []
        for name, error, result in results:
            if error:
                parts.append(f"❌ {name}: {error}")
            else:
                parts.append(f"✅ {name}:\n{str(result)[:800]}")
        return "\n\n".join(parts)
PYEOF

# ============================================
# 5. memory/manager.py — Memoria semántica
# ============================================
cat > memory/manager.py << 'PYEOF'
import sqlite3
import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from config import get

DB_PATH = Path(get("paths.memory_db", "~/yuna/data/yuna.db")).expanduser()

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS preferencias (
                clave TEXT PRIMARY KEY,
                valor TEXT,
                actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                evento TEXT,
                detalles TEXT
            );
            CREATE TABLE IF NOT EXISTS tarea_actual (
                id TEXT PRIMARY KEY,
                estado TEXT,
                datos JSON,
                actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_episodic_fecha ON episodic(fecha);
            CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation_history(session_id, timestamp);
            CREATE TABLE IF NOT EXISTS entity_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT UNIQUE,
                relation TEXT,
                value TEXT,
                confidence REAL DEFAULT 1.0,
                updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_entity ON entity_memory(entity);
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                query_pattern TEXT,
                tool_name TEXT,
                outcome TEXT,
                success BOOLEAN,
                count INTEGER DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_lessons_pattern ON lessons(query_pattern);
            CREATE INDEX IF NOT EXISTS idx_lessons_tool ON lessons(tool_name);
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                query TEXT,
                response TEXT,
                feedback TEXT,
                score INTEGER
            );
            CREATE TABLE IF NOT EXISTS interaction_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                query TEXT,
                response TEXT,
                tools_used TEXT,
                success BOOLEAN,
                latency_ms REAL
            );
        """)

def set_preferencia(clave: str, valor: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO preferencias (clave, valor) VALUES (?, ?)",
            (clave, valor)
        )

def get_preferencia(clave: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT valor FROM preferencias WHERE clave = ?", (clave,))
        row = cur.fetchone()
        return row[0] if row else None

def get_all_preferencias() -> Dict[str, str]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT clave, valor FROM preferencias")
        return {row[0]: row[1] for row in cur.fetchall()}

def add_episodic(evento: str, detalles: str = ""):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO episodic (evento, detalles) VALUES (?, ?)",
            (evento, detalles)
        )

def get_episodic(limit: int = 50) -> List[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT fecha, evento, detalles FROM episodic ORDER BY fecha DESC LIMIT ?",
            (limit,)
        )
        return [{"fecha": r[0], "evento": r[1], "detalles": r[2]} for r in cur.fetchall()]

def set_tarea_actual(tarea_id: str, estado: str, datos: Dict = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tarea_actual (id, estado, datos) VALUES (?, ?, ?)",
            (tarea_id, estado, json.dumps(datos or {}))
        )

def get_tarea_actual(tarea_id: str) -> Optional[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT estado, datos FROM tarea_actual WHERE id = ?", (tarea_id,)
        )
        row = cur.fetchone()
        if row:
            return {"estado": row[0], "datos": json.loads(row[1])}
        return None

def set_entity(entity: str, relation: str, value: str, confidence: float = 1.0):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO entity_memory
               (entity, relation, value, confidence, updated)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (entity.lower(), relation, value, confidence)
        )

def get_entity(entity: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT value, relation FROM entity_memory WHERE entity = ?",
            (entity.lower(),)
        )
        row = cur.fetchone()
        return f"{row[1]}: {row[0]}" if row else None

def add_conversation_turn(session_id: str, role: str, content: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO conversation_history (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content[:2000])
        )

def get_conversation_history(session_id: str, limit: int = 10) -> List[Dict]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                "SELECT role, content, timestamp FROM conversation_history "
                "WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
            rows = cur.fetchall()
            return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in reversed(rows)]
    except sqlite3.OperationalError:
        return []

def get_last_session_id() -> Optional[str]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                "SELECT session_id FROM conversation_history ORDER BY timestamp DESC LIMIT 1"
            )
            row = cur.fetchone()
            return row[0] if row else None
    except sqlite3.OperationalError:
        return None

def get_relevant_memory(query: str, top_k: int = 5) -> str:
    partes = []
    query_lower = query.lower()

    # Entidades explícitas: nombres propios y texto entre comillas.
    entities = re.findall(r"\b[A-Z][a-z]+\b", query)
    entities += re.findall(r'"([^"]+)"', query)

    entity_data = []
    for ent in entities:
        val = get_entity(ent)
        if val:
            entity_data.append(f"{ent} -> {val}")

    if entity_data:
        partes.append(
            "ENTIDADES CONOCIDAS:\n" +
            "\n".join(entity_data)
        )

    # Preferencias relacionadas con palabras de la consulta.
    prefs = get_all_preferencias()
    relevant_prefs = {}

    for k, v in prefs.items():
        k_lower = k.lower()
        v_lower = str(v).lower()

        if any(
            word in k_lower or word in v_lower
            for word in query_lower.split()
            if len(word) > 3
        ):
            relevant_prefs[k] = v

    if relevant_prefs:
        partes.append(
            "PREFERENCIAS RELEVANTES:\n" +
            "\n".join(
                f"- {k}: {v}"
                for k, v in list(relevant_prefs.items())[:top_k]
            )
        )

    # Memoria episódica.
    episodic = get_episodic(20)
    relevant_episodes = []

    query_words = {
        w for w in query_lower.split()
        if len(w) > 3
    }

    for e in episodic:
        content = f"{e['evento']} {e['detalles']}".lower()
        score = len(query_words & set(content.split()))

        if score > 0 or len(relevant_episodes) < 3:
            relevant_episodes.append((score, e))

    relevant_episodes.sort(
        key=lambda x: x[0],
        reverse=True
    )

    top_episodes = [
        e for _, e in relevant_episodes[:top_k]
    ]

    if top_episodes:
        partes.append(
            "HISTORIAL RELEVANTE:\n" +
            "\n".join(
                f"- [{e['fecha']}] {e['evento']}"
                for e in top_episodes
            )
        )

    return "\n\n".join(partes) if partes else ""

def migrar_memoria_txt():
    init_db()
    txt_path = Path(get("paths.memory_txt_legacy", "~/yuna/memoria.txt")).expanduser()
    if not txt_path.exists():
        return
    print(f"📦 Migrando memoria desde {txt_path}...")
    with open(txt_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("[P]"):
                partes = line[3:].split(":", 1)
                if len(partes) == 2:
                    set_preferencia(partes[0].strip(), partes[1].strip())
    backup = txt_path.with_suffix(".txt.bak")
    txt_path.rename(backup)
    print(f"✓ Migracion completa. Backup en {backup}")

def consultar_memoria(tabla: str, clave: str = "") -> str:
    if tabla == "preferencias":
        if clave:
            val = get_preferencia(clave)
            return f"{clave}: {val}" if val else f"Clave '{clave}' no encontrada"
        prefs = get_all_preferencias()
        return "\n".join(f"{k}: {v}" for k, v in prefs.items()) if prefs else "Sin preferencias"
    if tabla == "episodic":
        episodic = get_episodic(20)
        return "\n".join(f"[{e['fecha']}] {e['evento']}: {e['detalles']}" for e in episodic) if episodic else "Historial vacio"
    if tabla == "entities":
        ent = get_entity(clave)
        return ent or f"Entidad '{clave}' no encontrada"
    return f"Tabla '{tabla}' no valida"

def escribir_memoria(clave: str, valor: str) -> str:
    set_preferencia(clave, valor)
    return f"✓ Memoria guardada: {clave} = {valor}"

def escribir_entidad(entidad: str, relacion: str, valor: str) -> str:
    set_entity(entidad, relacion, valor)
    return f"✓ Entidad guardada: {entidad} es {relacion} de {valor}"

def add_interaction_metric(query: str, response: str, tools: list, success: bool, latency: float):
    import json
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO interaction_metrics (query, response, tools_used, success, latency_ms)
               VALUES (?, ?, ?, ?, ?)""",
            (query[:500], response[:500], json.dumps(tools), success, latency * 1000)
        )
PYEOF

# ============================================
# 6. tools/sistema.py — Seguridad crítica
# ============================================
cat > tools/sistema.py << 'PYEOF'
import os
import re
import subprocess
import platform
from datetime import datetime
from tools.permisos import is_bash_allowed

def ejecutar_bash_seguro(comando: str) -> str:
    """Ejecuta comandos Bash simples previamente autorizados."""
    if not is_bash_allowed(comando):
        cmd = comando.strip().split()[0] if comando.strip() else ""
        return (
            f"⛔ Comando '{cmd}' no permitido. "
            "Revisa la whitelist y las rutas autorizadas."
        )

    comando_limpio = comando.strip()

    if re.search(r"[;&|`$()<>]", comando_limpio):
        return "⛔ Detectados caracteres de shell injection."

    try:
        import shlex
        partes = shlex.split(comando_limpio)
    except ValueError:
        return "⛔ Sintaxis de comando invalida."

    if not partes:
        return "⛔ Comando vacio."

    if len(partes) > 5:
        return "⛔ Comando demasiado complejo. Maximo 5 argumentos."

    # Resolver ~ de forma independiente para cada argumento.
    partes = [os.path.expanduser(p) for p in partes]

    try:
        resultado = subprocess.run(
            partes,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
            cwd=os.path.expanduser("~/yuna"),
        )

        return (
            resultado.stdout.strip()
            or resultado.stderr.strip()
            or "✓ Sin salida"
        )

    except subprocess.TimeoutExpired:
        return "⏱ Timeout: el comando tardo demasiado"

    except Exception as e:
        return f"Error: {e}"

def notificar(titulo: str, mensaje: str) -> str:
    sistema = platform.system()
    try:
        if sistema == "Darwin":
            script = f'display notification "{mensaje}" with title "{titulo}"'
            os.system(f"osascript -e '{script}'")
        elif sistema == "Linux":
            os.system(f'notify-send "{titulo}" "{mensaje}"')
        else:
            return f"Notificacion: {titulo} - {mensaje}"
        return f"✓ Notificacion enviada: {titulo}"
    except Exception as e:
        return f"⚠ Error notificando: {e}"

def crear_archivo(ruta: str, contenido: str) -> str:
    """Crea archivos únicamente dentro de directorios autorizados."""

    from pathlib import Path

    home = Path.home().resolve()

    directorios_permitidos = [
        (home / "yuna").resolve(),
        (home / "Downloads").resolve(),
        (home / "Desktop").resolve(),
        (home / "Documents").resolve(),
        (home / "Pictures").resolve(),
        (home / "Movies").resolve(),
        (home / "Music").resolve(),
        Path("/tmp").resolve(),
    ]

    rutas_sensibles = [
        (home / ".ssh").resolve(),
        (home / ".aws").resolve(),
        (home / ".config").resolve(),
        Path("/etc").resolve(),
        Path("/System").resolve(),
        Path("/private").resolve(),
        Path("/var").resolve(),
    ]

    ruta_expandida = Path(os.path.expanduser(ruta))

    try:
        ruta_abs = ruta_expandida.resolve()
    except OSError:
        return f"⛔ Ruta no permitida: {ruta}"

    # macOS: /tmp normalmente resuelve físicamente a /private/tmp.
    tmp_real = Path("/tmp").resolve()

    try:
        ruta_abs.relative_to(tmp_real)
        es_tmp = True
    except ValueError:
        es_tmp = False

    # Bloquear rutas sensibles, excepto /private/tmp.
    if not es_tmp:
        for sensible in rutas_sensibles:
            try:
                ruta_abs.relative_to(sensible)
                return f"⛔ Ruta no permitida: {ruta}"
            except ValueError:
                pass

    # La ruta debe estar dentro de un directorio autorizado.
    permitida = False

    for base in directorios_permitidos:
        try:
            ruta_abs.relative_to(base)
            permitida = True
            break
        except ValueError:
            pass

    if not permitida:
        return (
            f"⛔ Ruta no permitida: {ruta}. "
            "Solo dentro de los directorios autorizados."
        )

    try:
        ruta_abs.parent.mkdir(parents=True, exist_ok=True)

        if ruta_abs.exists():
            backup = Path(str(ruta_abs) + ".bak")
            ruta_abs.replace(backup)

        ruta_abs.write_text(contenido, encoding="utf-8")

        return f"✓ Archivo creado: {ruta_abs}"

    except Exception as e:
        return f"⚠ Error creando archivo: {e}"

def info_sistema() -> str:
    try:
        disco = subprocess.run(["df", "-h", os.path.expanduser("~")], capture_output=True, text=True).stdout.strip()
        fecha = datetime.now().strftime("%A %d de %B, %Y — %H:%M")
        return f"📅 {fecha}\n💾 Disco:\n{disco}"
    except Exception as e:
        return f"Error obteniendo info: {e}"
PYEOF

# ============================================
# 7. tools/permisos.py — Auditoría
# ============================================
cat > tools/permisos.py << 'PYEOF'
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class PermissionLevel(Enum):
    SAFE = "safe"
    CONFIRM = "confirm"
    DANGEROUS = "dangerous"

_PERMISSIONS = {
    "buscar_archivos": PermissionLevel.SAFE,
    "listar_recientes": PermissionLevel.SAFE,
    "leer_texto": PermissionLevel.SAFE,
    "leer_excel": PermissionLevel.SAFE,
    "leer_csv": PermissionLevel.SAFE,
    "leer_pdf": PermissionLevel.SAFE,
    "buscar_web": PermissionLevel.SAFE,
    "precio_activo": PermissionLevel.SAFE,
    "noticias_financieras_mx": PermissionLevel.SAFE,
    "info_sistema": PermissionLevel.SAFE,
    "consultar_memoria": PermissionLevel.SAFE,
    "escribir_memoria": PermissionLevel.SAFE,
    "notificar": PermissionLevel.SAFE,
    "organizar_archivos": PermissionLevel.CONFIRM,
    "crear_archivo": PermissionLevel.CONFIRM,
    "ejecutar_bash_seguro": PermissionLevel.CONFIRM,
}

_BASH_WHITELIST = {"ls", "cat", "echo", "pwd", "head", "tail", "grep", "find", "wc", "date", "du", "df", "top", "ps", "lsof", "uname", "uptime", "whoami", "which"}

def check_permission(tool_name: str) -> PermissionLevel:
    perm = _PERMISSIONS.get(tool_name, PermissionLevel.DANGEROUS)
    logger.info(f"Permiso consultado: {tool_name} -> {perm.value}")
    return perm

def is_bash_allowed(comando: str) -> bool:
    """Valida comandos Bash simples y restringe el acceso a rutas sensibles."""

    import re
    import shlex
    from pathlib import Path

    if not comando or not comando.strip():
        return False

    comando = comando.strip()

    # Nunca permitir operadores o construcciones del shell.
    if re.search(r"[;&|`$()<>]", comando):
        logger.warning(f"Bash bloqueado por operador shell: {comando}")
        return False

    try:
        partes = shlex.split(comando)
    except ValueError:
        logger.warning(f"Bash bloqueado por sintaxis invalida: {comando}")
        return False

    if not partes:
        return False

    cmd = partes[0]

    if cmd not in _BASH_WHITELIST:
        logger.warning(f"Bash bloqueado: {comando}")
        return False

    home = Path.home().resolve()
    yuna = (home / "yuna").resolve()
    downloads = (home / "Downloads").resolve()
    desktop = (home / "Desktop").resolve()
    documents = (home / "Documents").resolve()
    pictures = (home / "Pictures").resolve()
    movies = (home / "Movies").resolve()
    music = (home / "Music").resolve()
    tmp = Path("/tmp").resolve()

    root = Path("/").resolve()

    rutas_sensibles = {
        Path("/etc").resolve(),
        Path("/System").resolve(),
        Path("/private").resolve(),
        Path("/var").resolve(),
        (home / ".ssh").resolve(),
        (home / ".aws").resolve(),
        (home / ".config").resolve(),
    }

    def ruta_permitida(valor: str) -> bool:
        """Comprueba que una ruta quede dentro de un directorio autorizado."""

        ruta = Path(valor).expanduser()

        # Las rutas relativas se interpretan respecto al workspace de Yuna.
        if not ruta.is_absolute():
            ruta = yuna / ruta

        try:
            ruta = ruta.resolve()
        except OSError:
            return False

        # Nunca permitir la raiz del sistema ni rutas sensibles.
        if ruta == root:
            return False

        for sensible in rutas_sensibles:
            try:
                ruta.relative_to(sensible)
                return False
            except ValueError:
                pass

        # Directorios de trabajo autorizados.
        for base in (
            yuna,
            downloads,
            desktop,
            documents,
            pictures,
            movies,
            music,
            tmp,
        ):
            try:
                ruta.relative_to(base)
                return True
            except ValueError:
                pass

        return False

    # Argumentos que parecen rutas deben permanecer dentro
    # de los directorios autorizados.
    for argumento in partes[1:]:
        if argumento.startswith("-"):
            continue

        # Argumentos de grep/find pueden ser patrones, no rutas.
        if cmd in {"grep", "find"} and argumento.startswith("*"):
            continue

        if not ruta_permitida(argumento):
            logger.warning(
                f"Bash bloqueado por ruta no permitida: {comando}"
            )
            return False

    return True

def confirm_user(tool_name: str, args: dict) -> bool:
    print(f"\n⚠ Confirmacion: {tool_name}({args})")
    resp = input("¿Ejecutar? (s/n) -> ").strip().lower()
    logger.info(f"Confirmacion usuario para {tool_name}: {resp}")
    return resp == "s"
PYEOF

# ============================================
# 8. tools/archivos.py — Manejo de errores
# ============================================
cat > tools/archivos.py << 'PYEOF'
import os
import glob
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def buscar_archivos(patron: str = "*", carpeta: str = "~/Downloads") -> list:
    carpeta = os.path.expanduser(carpeta)
    if not os.path.exists(carpeta):
        return []
    resultados = glob.glob(os.path.join(carpeta, patron))
    return sorted(resultados, key=os.path.getmtime, reverse=True)

def listar_recientes(carpeta: str = "~/Downloads", dias: int = 7) -> list:
    carpeta = os.path.expanduser(carpeta)
    dias = int(dias)
    if not os.path.exists(carpeta):
        return []
    limite = datetime.now() - timedelta(days=dias)
    archivos = []
    for f in os.listdir(carpeta):
        ruta = os.path.join(carpeta, f)
        if os.path.isfile(ruta):
            try:
                modificado = datetime.fromtimestamp(os.path.getmtime(ruta))
                if modificado > limite:
                    archivos.append({
                        "nombre": f,
                        "ruta": ruta,
                        "modificado": modificado.strftime("%Y-%m-%d %H:%M"),
                        "tamano_kb": round(os.path.getsize(ruta) / 1024, 1)
                    })
            except OSError:
                continue
    return sorted(archivos, key=lambda x: x["modificado"], reverse=True)

def organizar_por_tipo(carpeta_origen: str = "~/Downloads") -> list:
    carpeta = os.path.expanduser(carpeta_origen)
    if not os.path.exists(carpeta):
        return ["Error: carpeta no existe"]
    destinos = {
        "PDF": ["pdf"],
        "Excel": ["xlsx", "xls"],
        "Datos": ["csv", "json"],
        "Imagenes": ["png", "jpg", "jpeg", "gif", "webp"],
        "Documentos": ["docx", "doc", "txt", "md"],
        "Codigo": ["py", "js", "ts", "html", "css", "json"],
    }
    movidos = []
    for archivo in os.listdir(carpeta):
        ruta = os.path.join(carpeta, archivo)
        if not os.path.isfile(ruta):
            continue
        ext = archivo.split(".")[-1].lower()
        for carpeta_destino, extensiones in destinos.items():
            if ext in extensiones:
                destino = os.path.join(carpeta, carpeta_destino)
                os.makedirs(destino, exist_ok=True)
                nuevo = os.path.join(destino, archivo)
                if os.path.exists(nuevo):
                    base, ext = os.path.splitext(archivo)
                    nuevo = os.path.join(destino, f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
                try:
                    shutil.move(ruta, nuevo)
                    movidos.append(f"{archivo} -> {carpeta_destino}/")
                except Exception as e:
                    movidos.append(f"Error moviendo {archivo}: {e}")
                break
    return movidos

def leer_texto(ruta: str) -> str:
    """Lee un archivo de texto. Lanza FileNotFoundError si no existe."""
    ruta = os.path.expanduser(ruta)

    if not os.path.exists(ruta):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

    if os.path.getsize(ruta) > 10 * 1024 * 1024:
        raise ValueError("Archivo demasiado grande (>10MB)")

    with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
PYEOF

# ============================================
# 9. automation/watchers.py — Fix path
# ============================================
cat > automation/watchers.py << 'PYEOF'
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable, Dict, Any
import logging
import threading
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class YunaFileHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str, str], None], patterns: list = None):
        self.callback = callback
        self.patterns = patterns or ["*.xlsx", "*.csv", "*.pdf", "*.txt"]

    def on_created(self, event):
        if not event.is_directory:
            for pattern in self.patterns:
                if self._match(event.src_path, pattern):
                    self.callback("created", event.src_path)
                    break

    def on_modified(self, event):
        if not event.is_directory:
            for pattern in self.patterns:
                if self._match(event.src_path, pattern):
                    self.callback("modified", event.src_path)
                    break

    def _match(self, path: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

class FileWatcher:
    def __init__(self):
        self.observer = Observer()
        self.watches: Dict[str, Any] = {}

    def watch(self, path: str, callback: Callable[[str, str], None], patterns: list = None, recursive: bool = True):
        path_obj = Path(path).expanduser()
        handler = YunaFileHandler(callback, patterns)
        watch = self.observer.schedule(handler, str(path_obj), recursive=recursive)
        self.watches[str(path_obj)] = watch
        logger.info(f"Vigilando: {path_obj} (patrones: {patterns})")

    def start(self):
        self.observer.start()
        logger.info("File watcher iniciado")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("File watcher detenido")
PYEOF

# ============================================
# 10. interface/agent_cli.py — Feedback loop
# ============================================
cat > interface/agent_cli.py << 'PYEOF'
import sys
import os
import subprocess
import threading
sys.path.insert(0, os.path.expanduser("~/yuna"))

from core.agent import YunaAgent
from core.llm import preload_model
from memory.manager import init_db, add_episodic
from config import get

VOICE = get("voice.voice", "es-MX-DaliaNeural")
MAX_CHARS = get("voice.max_chars", 300)

def hablar(texto: str):
    def _hablar():
        if not texto or not texto.strip():
            return
        try:
            resultado = subprocess.run([
                "edge-tts", "--voice", VOICE,
                "--text", str(texto).strip()[:MAX_CHARS],
                "--write-media", "/tmp/yuna_agent.mp3"
            ], capture_output=True, timeout=15)
            if resultado.returncode != 0:
                return
            if os.path.getsize("/tmp/yuna_agent.mp3") < 1024:
                return
            sistema = os.name
            if sistema == 'posix' and os.uname().sysname == 'Darwin':
                subprocess.run(["afplay", "/tmp/yuna_agent.mp3"], timeout=60)
            else:
                subprocess.run(["mpg123", "-q", "/tmp/yuna_agent.mp3"], timeout=60)
        except Exception:
            pass
    threading.Thread(target=_hablar, daemon=True).start()

def main():
    init_db()
    print("⏳ Precargando modelo en RAM...")
    preload_model()
    print("✅ Modelo listo.\n")

    agente = YunaAgent()
    saludo = "Hola Luis, modo agente activo. Puedo buscar archivos, analizar datos, consultar precios y mas."
    print(f"🤖 Yuna Agente\n")
    print(f"Yuna -> {saludo}\n")
    hablar(saludo)
    print("(escribe 'salir' para terminar, 'reset' para nueva sesion, '👍' o '👎' despues de una respuesta)\n")

    ultima_query = ""
    while True:
        try:
            entrada = input("Luis -> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not entrada:
            continue
        if entrada.lower() == "salir":
            hablar("Hasta luego Luis.")
            print("Yuna -> Hasta luego Luis.")
            break
        if entrada.lower() == "reset":
            agente.reset()
            print("✓ Sesion reiniciada\n")
            continue
        if entrada in ("👍", "bien", "util", "up"):
            if ultima_query:
                agente.provide_feedback(ultima_query, "positive")
                print("✓ Feedback positivo registrado para aprendizaje\n")
            continue
        if entrada in ("👎", "mal", "inutil", "down"):
            if ultima_query:
                agente.provide_feedback(ultima_query, "negative")
                print("✓ Feedback negativo registrado. Intentare mejorar.\n")
            continue
        print("⏳ Procesando...\n")
        ultima_query = entrada
        respuesta = agente.process(entrada)
        add_episodic("agente", f"Luis: {entrada[:100]} | Yuna: {respuesta[:100]}")
        print(f"Yuna -> {respuesta}\n")
        hablar(respuesta)

if __name__ == "__main__":
    main()
PYEOF

# ============================================
# 11. config/config.json — Consistencia
# ============================================
cat > config/config.json << 'PYEOF'
{
  "models": {
    "agent": "qwen3:8b",
    "chat": "qwen3:8b",
    "fast": "qwen3:8b"
  },
  "ollama": {
    "host": "http://localhost:11434",
    "timeout": 120,
    "stream": false,
    "keep_alive": "30m"
  },
  "paths": {
    "memory_db": "~/yuna/data/yuna.db",
    "logs": "~/yuna/logs/",
    "data_folder": "~/yuna/data/",
    "memory_txt_legacy": "~/yuna/memoria.txt"
  },
  "permissions": {
    "interactive": true,
    "confirmations": true
  },
  "voice": {
    "enabled": true,
    "voice": "es-MX-DaliaNeural",
    "max_chars": 300
  },
  "agent": {
    "max_iterations": 5,
    "temperature_plan": 0.2,
    "temperature_execute": 0.4,
    "context_window": 4096,
    "parallel_tools": true,
    "tool_cache_ttl": 300
  }
}
PYEOF

# ============================================
# 12. Inicializar DB y verificar
# ============================================
echo "📦 Inicializando base de datos..."
python3 -c "from memory.manager import init_db; init_db(); print('✓ BD lista')"

echo ""
echo "✅ Correcciones aplicadas. Ahora prueba con:"
echo "   python3 app.py migrate"
echo "   python3 app.py agent"
echo ""
