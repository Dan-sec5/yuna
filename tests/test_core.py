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

def test_evaluator_max_iterations():
    from core.evaluator import ResultEvaluator
    ev = ResultEvaluator(max_iterations=3)
    calls = [{"name": "test", "arguments": {}}]
    assert ev.should_continue(calls, "") == True
    assert ev.should_continue(calls, "") == True
    assert ev.should_continue(calls, "") == True
    assert ev.should_continue(calls, "") == False

def test_evaluator_reset():
    from core.evaluator import ResultEvaluator
    ev = ResultEvaluator(max_iterations=2)
    calls = [{"name": "test"}]
    ev.should_continue(calls, "")
    ev.should_continue(calls, "")
    ev.reset()
    assert ev.should_continue(calls, "") == True

def test_context_manager():
    from core.context import ContextManager
    ctx = ContextManager()
    ctx.add_system("Sistema")
    ctx.add_user("Pregunta")
    ctx.add_assistant("Respuesta")
    context = ctx.get_context()
    assert context[0]["role"] == "system"
    assert len(context) >= 2
