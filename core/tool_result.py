"""
core/tool_result.py

Contrato común para interpretar resultados de herramientas.

Permite convivir temporalmente con:
- strings históricos
- dicts estructurados nuevos

El objetivo futuro es que todas las tools devuelvan dict estructurado.
"""

from typing import Any, Dict


_ERROR_PREFIXES = (
    "error",
    "⚠",
    "⛔",
    "❌",
    "cancelado",
)


def tool_result_ok(result: Any) -> bool:
    """
    Determina si un resultado representa éxito.
    """

    if result is None:
        return False

    if isinstance(result, dict):

        if "ok" in result:
            return result["ok"] is True

        # Dict sin campo ok:
        # conservar compatibilidad por ahora.
        return True

    if isinstance(result, str):

        text = result.strip().lower()

        if not text:
            return False

        return not text.startswith(
            _ERROR_PREFIXES
        )

    return True


def normalize_tool_result(result: Any) -> Dict[str, Any]:
    """
    Convierte cualquier retorno histórico al contrato estándar.

    Formato:

        {
            "ok": bool,
            "data": ...,
            "message": str
        }
    """

    if isinstance(result, dict) and "ok" in result:

        normalized = dict(result)

        normalized.setdefault(
            "data",
            None,
        )

        normalized.setdefault(
            "message",
            str(
                result.get(
                    "error",
                    "",
                )
            ),
        )

        return normalized

    ok = tool_result_ok(
        result
    )

    return {
        "ok": ok,
        "data": result,
        "message": (
            str(result)
            if result is not None
            else ""
        ),
    }
