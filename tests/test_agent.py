import sys
import os
sys.path.insert(0, os.path.expanduser("~/yuna"))
import pytest

def test_agent_importa():
    from core.agent import YunaAgent
    agente = YunaAgent()
    assert agente is not None

def test_agent_reset():
    from core.agent import YunaAgent
    agente = YunaAgent()
    agente.reset()
    assert agente is not None

def test_agent_process_simple():
    from core.agent import YunaAgent
    agente = YunaAgent()
    respuesta = agente.process("hola")
    assert isinstance(respuesta, str)
    assert len(respuesta) > 0
