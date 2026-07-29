import logging
from typing import List, Dict, Any, Tuple
from tools.registry import TOOLS
from tools.permisos import check_permission, PermissionLevel
from tools.schemas import get_schema

logger = logging.getLogger(__name__)

class ToolExecutor:
    def __init__(self, confirm_callback=None):
        self.confirm_callback = confirm_callback or self._default_confirm
    
    def _default_confirm(self, tool_name: str, args: dict) -> bool:
        print(f"\n⚠ Confirmación requerida para: {tool_name}({args})")
        resp = input("¿Ejecutar? (s/n) → ").strip().lower()
        return resp == 's'
    
    def execute(self, tool_name: str, args: list) -> Tuple[str, Any]:
        if tool_name not in TOOLS:
            return f"Error: herramienta '{tool_name}' no existe", None
        
        perm = check_permission(tool_name)
        
        if perm == PermissionLevel.DANGEROUS:
            return f"Error: herramienta '{tool_name}' es peligrosa y requiere autorización explícita", None
        
        if perm == PermissionLevel.CONFIRM:
            if not self.confirm_callback(tool_name, dict(zip(get_schema(tool_name).get("parameters", {}).get("properties", {}).keys(), args))):
                return "Cancelado por el usuario", None
        
        try:
            func = TOOLS[tool_name]
            result = func(*args) if args else func()
            return None, result
        except Exception as e:
            logger.error(f"Error ejecutando {tool_name}: {e}")
            return f"Error: {e}", None
    
    def execute_batch(self, calls: List[Dict]) -> List[Tuple[str, Any, Any]]:
        results = []
        for call in calls:
            name = call["name"]
            args = call.get("args", [])
            error, result = self.execute(name, args)
            results.append((name, error, result))
        return results
