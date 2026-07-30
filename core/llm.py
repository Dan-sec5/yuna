"""
core/llm.py — Wrapper Ollama optimizado para baja latencia
Cambios: streaming, keep-alive, batch processing, carga asíncrona
"""
import ollama
import logging
from typing import List, Dict, Any, Optional, Iterator
from config import CONFIG

logger = logging.getLogger(__name__)

MODEL_AGENT = CONFIG["models"].get("agent", "qwen3:4b")
MODEL_CHAT = CONFIG["models"].get("chat", "llama3.2:3b")
OLLAMA_HOST = CONFIG["ollama"].get("host", "http://localhost:11434")
KEEP_ALIVE = CONFIG["ollama"].get("keep_alive", "30m")  # Mantener modelo en RAM

client = ollama.Client(host=OLLAMA_HOST)

# ─── Keep-alive: precargar modelo al iniciar ─────────────────
def preload_model(model: str = None):
    """Precarga el modelo en RAM para evitar latencia de carga."""
    model = model or MODEL_AGENT
    try:
        # Petición mínima para cargar el modelo en memoria
        client.chat(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            options={"num_predict": 1},
            keep_alive=KEEP_ALIVE
        )
        logger.info(f"Modelo {model} precargado en RAM")
    except Exception as e:
        logger.warning(f"No se pudo precargar {model}: {e}")

# ─── Chat con tools — SIN streaming (tool calling requiere respuesta completa) ───
def chat_with_tools(
    messages: List[Dict],
    tools: List[Dict],
    model: str = None,
    **options
) -> Any:
    model = model or MODEL_AGENT
    default_opts = {
        "num_predict": 400,
        "temperature": 0.2,
        "num_ctx": 4096,
        "keep_alive": KEEP_ALIVE,
    }
    default_opts.update(options)

    try:
        return client.chat(
            model=model,
            messages=messages,
            tools=tools,
            options=default_opts
        )
    except ollama.ResponseError as e:
        logger.error(f"Ollama error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return None

# ─── Chat simple — CON streaming para respuesta inmediata ────
def chat_simple_stream(
    messages: List[Dict],
    model: str = None,
    **options
) -> Iterator[str]:
    """
    Streaming para chat.py — el usuario ve texto aparecer token por token
    en lugar de esperar la respuesta completa.
    """
    model = model or MODEL_CHAT
    default_opts = {
        "num_predict": 600,
        "temperature": 0.7,
        "num_ctx": 4096,
        "keep_alive": KEEP_ALIVE,
    }
    default_opts.update(options)

    try:
        stream = client.chat(
            model=model,
            messages=messages,
            stream=True,
            options=default_opts
        )
        for chunk in stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content
    except Exception as e:
        logger.error(f"Error en streaming: {e}")
        yield f"⚠️ Error: {e}"

# ─── Chat simple tradicional (sin streaming) ────────────────
def chat_simple(
    messages: List[Dict],
    model: str = None,
    **options
) -> Any:
    model = model or MODEL_CHAT
    default_opts = {
        "num_predict": 600,
        "temperature": 0.7,
        "num_ctx": 4096,
        "keep_alive": KEEP_ALIVE,
    }
    default_opts.update(options)

    try:
        return client.chat(model=model, messages=messages, options=default_opts)
    except Exception as e:
        logger.error(f"Error en chat simple: {e}")
        return None

def clean_response(response: Any) -> str:
    import re
    if response is None:
        return ""

    if hasattr(response, "message"):
        content = getattr(response.message, "content", "") or ""
    elif isinstance(response, dict):
        content = response.get("message", {}).get("content", "") or ""
    else:
        content = str(response)

    content = re.sub(r'\<think\>.*?\</think\>', '', content, flags=re.DOTALL)
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
