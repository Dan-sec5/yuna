from typing import List, Dict, Any, Optional

class ResultEvaluator:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.iteration = 0
    
    def should_continue(self, results: List[Dict], last_response: str) -> bool:
        self.iteration += 1
        
        if self.iteration >= self.max_iterations:
            return False
        
        if not results:
            return False
        
        has_errors = any(r.get("error") for r in results)
        if has_errors:
            return True
        
        return False
    
    def build_context(self, results: List[Dict]) -> str:
        parts = []
        for r in results:
            name = r.get("tool", "unknown")
            error = r.get("error")
            result = r.get("result")
            
            if error:
                parts.append(f"[ERROR en {name}]:\n{error}")
            else:
                content = str(result)[:600]
                parts.append(f"[RESULTADO de {name}]:\n{content}")
        
        return "\n\n".join(parts)
    
    def reset(self):
        self.iteration = 0
