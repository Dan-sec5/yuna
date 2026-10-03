import sys, os
sys.path.insert(0, os.path.expanduser("~/yuna"))
import pytest

def test_clean_response_dict():
    from core.llm import clean_response
    resp = {"message": {"content": "Hola Luis"}}
    assert clean_response(resp) == "Hola Luis"

def test_clean_response_none():
    from core.llm import clean_response
    assert clean_response(None) == ""

def test_clean_response_thinking():
    from core.llm import clean_response
    resp = {"message": {"content": "<think>pensando...</think>Respuesta final"}}
    resultado = clean_response(resp)
    assert "pensando" not in resultado
    assert "Respuesta final" in resultado

def test_get_tool_calls_empty():
    from core.llm import get_tool_calls
    assert get_tool_calls(None) == []
    assert get_tool_calls({}) == []
    assert get_tool_calls({"message": {}}) == []

def test_get_tool_calls_dict():
    from core.llm import get_tool_calls
    resp = {
        "message": {
            "tool_calls": [
                {"function": {"name": "precio_activo", "arguments": {"ticker": "AAPL"}}}
            ]
        }
    }
    calls = get_tool_calls(resp)
    assert len(calls) == 1
    assert calls[0]["name"] == "precio_activo"
    assert calls[0]["arguments"]["ticker"] == "AAPL"


def test_get_tool_calls_textual_fallback():
    from core.llm import get_tool_calls

    resp = {
        "message": {
            "content": """
<tool>
{"name": "info_sistema", "arguments": {}}
</tool>
"""
        }
    }

    calls = get_tool_calls(resp)

    assert len(calls) == 1
    assert calls[0]["name"] == "info_sistema"
    assert calls[0]["arguments"] == {}


def test_get_tool_calls_textual_with_args():
    from core.llm import get_tool_calls

    resp = {
        "message": {
            "content": """
<tool>
{"name": "crear_archivo", "arguments": {
    "ruta": "~/yuna/test.txt",
    "contenido": "hola"
}}
</tool>
"""
        }
    }

    calls = get_tool_calls(resp)

    assert len(calls) == 1
    assert calls[0]["name"] == "crear_archivo"
    assert calls[0]["arguments"]["ruta"] == "~/yuna/test.txt"


def test_native_tool_calls_have_priority():
    from core.llm import get_tool_calls

    resp = {
        "message": {
            "content": """
<tool>
{"name": "info_sistema", "arguments": {}}
</tool>
""",
            "tool_calls": [
                {
                    "function": {
                        "name": "precio_activo",
                        "arguments": {
                            "ticker": "AAPL"
                        }
                    }
                }
            ]
        }
    }

    calls = get_tool_calls(resp)

    assert len(calls) == 1
    assert calls[0]["name"] == "precio_activo"
