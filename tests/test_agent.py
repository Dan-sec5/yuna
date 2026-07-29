import sys
sys.path.insert(0, os.path.expanduser("~/yuna"))

import pytest
from core.agent import YunaAgent
from core.llm import chat_with_tools

class TestAgent:
    def test_agent_creation(self):
        agent = YunaAgent()
        assert agent is not None
    
    def test_agent_simple(self):
        agent = YunaAgent()
        # Test sin tools (solo conversación)
        # Esto requiere Ollama corriendo
        pass
