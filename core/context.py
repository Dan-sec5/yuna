from typing import List, Dict, Any
from memory.manager import get_relevant_memory


class ContextManager:
    def __init__(self, max_history: int = 6):
        self.max_history = max_history
        self.messages = []

    def add_system(self, content: str):
        if content and content.strip():
            self.messages = [{"role": "system", "content": content.strip()}]
        else:
            self.messages = []

    def add_user(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str):
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_result(self, tool_name: str, result: Any):
        self.messages.append({
            "role": "tool",
            "name": tool_name,
            "content": str(result)[:4000],
        })

    def get_context(self) -> List[Dict]:
        if not self.messages:
            return []
        system = [self.messages[0]] if self.messages[0]["role"] == "system" else []
        history = self.messages[1:][-self.max_history:]
        return system + history

    def enrich_with_memory(self, user_query: str):
        """Añade memoria relevante al system prompt sin acumular."""
        memory = get_relevant_memory(user_query)
        if not memory or not self.messages:
            return
        base = self.messages[0]["content"].split("\n\nMEMORIA RELEVANTE:")[0]
        self.messages[0]["content"] = base + f"\n\nMEMORIA RELEVANTE:\n{memory}"

    def clear_history(self):
        system = [self.messages[0]] if self.messages and self.messages[0]["role"] == "system" else []
        self.messages = system
