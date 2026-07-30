import ollama
import logging
from typing import List, Dict, Any, Optional
from config import CONFIG

logger = logging.getLogger(__name__)

MODEL_AGENT = CONFIG["models"].get("agent", "qwen2.5:7b")
MODEL_CHAT = CONFIG["models"].get("chat", "llama3.2:3b")
OLLAMA_HOST = CONFIG["ollama"].get("host", "http://localhost:11434")

client = ollama.Client(host=OLLAMA_HOST)

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
        "num_ctx": 4096
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

def chat_simple(
    messages: List[Dict],
    model: str = None,
    **options
) -> Any:
    model = model or MODEL_CHAT
    default_opts = {
        "num_predict": 600,
        "temperature": 0.7,
        "num_ctx": 4096
    }
    default_opts.update(options)

    try:
        return client.chat(model=model, messages=messages, options=default_opts)
    except Exception as e:
        logger.error(f"Error en chat simple: {e}")
        return None

def clean_response(response: Any) -> str:
    """Extrae contenido de respuesta — soporta dict y objeto Pydantic de Ollama"""
    import re
    if response is None:
        return ""

    # Objeto Pydantic de Ollama (ChatResponse)
    if hasattr(response, "message"):
        content = getattr(response.message, "content", "") or ""
    # Diccionario legacy
    elif isinstance(response, dict):
        content = response.get("message", {}).get("content", "") or ""
    else:
        content = str(response)

    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    if "...done thinking." in content:
        content = content.split("...done thinking.")[-1]
    return content.strip()

def get_tool_calls(response: Any) -> List[Dict]:
    """Extrae tool calls — soporta dict y objeto Pydantic de Ollama"""
    if response is None:
        return []

    # Objeto Pydantic de Ollama
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

    # Diccionario legacy
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
