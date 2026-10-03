"""
core/tool_validation.py

Validación ligera de argumentos para tools de Yuna.

No depende de jsonschema porque los schemas actuales usan un
subconjunto sencillo de JSON Schema:
- object
- string
- integer
- number
- boolean
- array
- enum
- required
"""

from typing import Any, Dict, List


_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def validate_tool_args(
    tool_name: str,
    args: Any,
    schema: Dict,
) -> List[str]:
    """
    Devuelve una lista de errores.

    Lista vacía = argumentos válidos.
    """

    errors: List[str] = []

    if not schema:
        return [
            f"La herramienta '{tool_name}' no tiene schema registrado."
        ]

    parameters = schema.get("parameters", {})

    if not isinstance(args, dict):
        return [
            f"Los argumentos de '{tool_name}' deben ser un objeto/dict."
        ]

    properties = parameters.get("properties", {}) or {}
    required = parameters.get("required", []) or []

    # ---------------------------------------------------------
    # Campos obligatorios
    # ---------------------------------------------------------

    for field in required:
        if field not in args:
            errors.append(
                f"Falta argumento obligatorio: '{field}'."
            )

    # ---------------------------------------------------------
    # Argumentos desconocidos
    # ---------------------------------------------------------

    unknown = set(args) - set(properties)

    for field in sorted(unknown):
        errors.append(
            f"Argumento no reconocido: '{field}'."
        )

    # ---------------------------------------------------------
    # Tipos y enums
    # ---------------------------------------------------------

    for field, value in args.items():

        spec = properties.get(field)

        if not spec:
            continue

        expected = spec.get("type")

        if expected:

            py_type = _TYPE_MAP.get(expected)

            if py_type is not None:

                # bool es subclase de int en Python.
                # Evitar aceptar True como integer/number.
                if expected in {"integer", "number"} and isinstance(
                    value,
                    bool,
                ):
                    valid_type = False
                else:
                    valid_type = isinstance(
                        value,
                        py_type,
                    )

                if not valid_type:
                    errors.append(
                        f"'{field}' debe ser de tipo "
                        f"{expected}; recibido "
                        f"{type(value).__name__}."
                    )
                    continue

        enum = spec.get("enum")

        if enum is not None and value not in enum:
            errors.append(
                f"'{field}' debe ser uno de: "
                + ", ".join(map(str, enum))
            )

    return errors
