import logging
from core.logger import get_logger
from typing import List, Dict, Any, Tuple
from tools.registry import TOOLS
from tools.permisos import check_permission, PermissionLevel
from tools.schemas import get_schema
from core.tool_validation import validate_tool_args
from core.tool_result import tool_result_ok

logger = get_logger(__name__)

class ToolExecutor:
    def __init__(self, confirm_callback=None):
        self.confirm_callback = confirm_callback or self._default_confirm

    def _default_confirm(self, tool_name: str, args: dict) -> bool:
        print(f"\n⚠ Confirmación requerida para: {tool_name}({args})")
        resp = input("¿Ejecutar? (s/n) → ").strip().lower()
        return resp == "s"

    def execute(self, tool_name: str, args: dict) -> Tuple[Any, Any]:

        # -----------------------------------------------------
        # Existencia
        # -----------------------------------------------------

        if tool_name not in TOOLS:
            return (
                f"Error: herramienta '{tool_name}' no existe",
                None,
            )

        # -----------------------------------------------------
        # Validación de argumentos ANTES de permisos/ejecución
        # -----------------------------------------------------

        schema = get_schema(tool_name)

        validation_errors = validate_tool_args(
            tool_name,
            args,
            schema,
        )

        if validation_errors:

            detalle = " | ".join(
                validation_errors
            )

            logger.error(
                "Argumentos inválidos para %s: %s",
                tool_name,
                detalle,
            )

            return (
                f"Error de validación: {detalle}",
                None,
            )

        # -----------------------------------------------------
        # Permisos
        # -----------------------------------------------------

        perm = check_permission(tool_name)

        if perm == PermissionLevel.DANGEROUS:
            return (
                f"Error: '{tool_name}' es peligrosa "
                "y no está autorizada",
                None,
            )

        if perm == PermissionLevel.CONFIRM:
            if not self.confirm_callback(
                tool_name,
                args,
            ):
                return (
                    "Cancelado por el usuario",
                    None,
                )

        # Seguridad: organizar_archivos sin carpeta = cancelar
        if tool_name == "organizar_archivos" and not args.get("carpeta_origen"):
            return "Cancelado: debes especificar la carpeta a organizar", None

        try:
            logger.info(f"Ejecutando tool: {tool_name} | args: {list(args.keys()) if isinstance(args, dict) else args}")
            func = TOOLS[tool_name]
            # Pasar argumentos como kwargs (dict) — formato nativo de Ollama tool calling
            result = func(**args) if args else func()

            # Una tool histórica puede devolver un string que comienza
            # con "Error", "⚠", "⛔", etc. Eso NO debe registrarse
            # como ejecución exitosa.
            if not tool_result_ok(result):

                logger.error(
                    "Tool %s devolvió resultado de error: %s",
                    tool_name,
                    str(result)[:200],
                )

                return (
                    f"Error reportado por la herramienta: {result}",
                    result,
                )

            logger.info(
                "Tool %s OK | resultado: %s",
                tool_name,
                str(result)[:100],
            )

            return None, result
        except TypeError as e:
            logger.error(f"Error de argumentos en {tool_name}: {e} | args: {args}")
            return f"Error de argumentos: {e}", None
        except Exception as e:
            logger.error(f"Error ejecutando {tool_name}: {e} | args: {args}")
            return f"Error: {e}", None

    def execute_batch(self, calls: List[Dict]) -> List[Tuple[str, Any, Any]]:
        results = []
        for call in calls:
            name = call.get("name", "")
            # Ollama devuelve argumentos como dict en "arguments"
            args = call.get("arguments", call.get("args", {}))
            if isinstance(args, list):
                # Convertir lista a dict usando el schema
                schema = get_schema(name)
                keys = list(schema.get("parameters", {}).get("properties", {}).keys())
                args = dict(zip(keys, args))
            error, result = self.execute(name, args)
            results.append((name, error, result))
        return results
