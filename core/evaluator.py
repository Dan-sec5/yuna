from typing import List, Dict, Any, Tuple

class ResultEvaluator:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.iteration = 0
        self.tool_success_rate = []

    def reset(self):
        self.iteration = 0
        self.tool_success_rate = []

    def should_continue(self, tool_calls: List[Dict], content: str) -> bool:
        if self.iteration >= self.max_iterations:
            return False
        self.iteration += 1
        return bool(tool_calls)

    def evaluate_tool_result(self, tool_name: str, error: Any, result: Any) -> bool:
        success = error is None
        if success and result:
            result_str = str(result).lower()
            if any(x in result_str for x in ["no se encontró", "vacío", "error", "no hay", "[]"]):
                success = False
        self.tool_success_rate.append((tool_name, success))
        return success

    def get_session_quality(self) -> Dict[str, Any]:
        if not self.tool_success_rate:
            return {"success_rate": 1.0, "tools_used": 0, "recommendation": "direct_response"}
        total = len(self.tool_success_rate)
        successful = sum(1 for _, s in self.tool_success_rate if s)
        rate = successful / total
        recommendation = "continue"
        if rate < 0.5 and total >= 2:
            recommendation = "try_different_tools"
        elif rate == 1.0 and total > 0:
            recommendation = "good_pattern"
        return {
            "success_rate": rate,
            "tools_used": total,
            "recommendation": recommendation
        }

    def build_context(self, results: List[Tuple]) -> str:
        parts = []
        for name, error, result in results:
            if error:
                parts.append(f"❌ {name}: {error}")
            else:
                parts.append(f"✅ {name}:\n{str(result)[:800]}")
        return "\n\n".join(parts)
