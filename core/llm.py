import ollama
import logging
from typing import List, Dict, Any, Optional
from config import CONFIG

logger = logging.getLogger(__name__)

MODEL_AGENT = CONFIG["models"].get("agent", "qwen3:8b")
MODEL_CHAT = CONFIG["models"].get("chat", "gemma2b")
OLLAMA_HOST = CONFIG["ollama"].get("host", "http://localhost:11434")

client = ollama.Client(host=OLLAMA_HOST)

def chat_with_tools(
    messages: List[Dict],
    tools: List[Dict],
    model: str = None,
    think: bool = True,
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
            think=think,
            options=default_opts
        )
    except ollama.ResponseError as e:
        if "not found" in str(e).lower():
            return {"message": {"content": f"Modelo '{model}' no disponible. Ejecuta: ollama pull {model}"}}
        logger.error(f"Ollama error: {e}")
        return {"message": {"content": f"Error de Ollama: {e}"}}
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return {"message": {"content": f"Error: {e}"}}

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
        return {"message": {"content": f"Error: {e}"}}

def clean_response(response: Any) -> str:
    import re
    content = response.get("message", {}).get("content", "")
    content = re.sub(r'', '', content, flags=re.DOTALL)
    if "...done thinking." in content:
        content = content.split("...done thinking.")[-1]
    return content.strip()

def get_tool_calls(response: Any) -> List[Dict]:
    msg = response.get("message", {})
    calls = msg.get("tool_calls", [])
    result = []
    for call in calls:
        func = call.get("function", {})
        result.append({
            "name": func.get("name"),
            "arguments": func.get("arguments", {})
        })
    return result
