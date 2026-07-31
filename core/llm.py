"""
core/llm.py — Wrapper Ollama con think=False para Qwen3
Documentación: https://docs.ollama.com/capabilities/thinking
"""
import ollama
import logging
from core.logger import get_logger
from typing import List, Dict, Any, Optional
from config import CONFIG

logger = get_logger(__name__)

MODEL_AGENT = CONFIG["models"].get("agent", "qwen3:4b")
MODEL_CHAT = CONFIG["models"].get("chat", "qwen3:4b")
OLLAMA_HOST = CONFIG["ollama"].get("host", "http://localhost:11434")
KEEP_ALIVE = CONFIG["ollama"].get("keep_alive", "30m")

client = ollama.Client(host=OLLAMA_HOST)


def _is_thinking_model(model: str) -> bool:
    """Detecta si el modelo tiene modo thinking nativo."""
    thinking_models = ["qwen3", "deepseek-r1", "deepseek-v3", "gemma4", "gpt-oss"]
    return any(tm in model.lower() for tm in thinking_models)


def _get_options(model: str, extra_options: dict) -> dict:
    """Construye opciones de Ollama, desactivando thinking si aplica."""
    opts = {
        "num_predict": 400,
        "temperature": 0.2,
        "num_ctx": 4096,
        "keep_alive": KEEP_ALIVE,
    }
    opts.update(extra_options)

    # CRÍTICO: Desactivar thinking para modelos que lo soportan
    # Esto reduce la latencia de 30s a ~2s en Qwen3
    if _is_thinking_model(model):
        opts["think"] = False  # ← FIX DEFINITIVO
        logger.debug(f"Thinking desactivado para {model}")

    return opts


def preload_model(model: str = None):
    """Precarga el modelo en RAM para evitar latencia de carga."""
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

    # Parámetro think va al nivel superior, no en options
    kwargs = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "options": opts,
    }
    if _is_thinking_model(model):
        kwargs["think"] = False

    try:
        return client.chat(**kwargs)
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
        return client.chat(**kwargs)
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
