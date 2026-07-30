from typing import List, Dict, Any, Tuple

class ResultEvaluator:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.iteration = 0

    def reset(self):
        self.iteration = 0

    def should_continue(self, tool_calls: List[Dict], content: str) -> bool:
        if self.iteration >= self.max_iterations:
            return False
        self.iteration += 1
        return bool(tool_calls)

    def build_context(self, results: List[Tuple]) -> str:
        parts = []
        for name, error, result in results:
            if error:
                parts.append(f"❌ {name}: {error}")
            else:
                parts.append(f"✅ {name}:\n{str(result)[:800]}")
        return "\n\n".join(parts)
