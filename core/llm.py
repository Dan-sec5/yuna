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
