from core.tool_validation import validate_tool_args
from core.tool_result import (
    normalize_tool_result,
    tool_result_ok,
)


SCHEMA = {
    "name": "demo",
    "parameters": {
        "type": "object",
        "properties": {
            "ruta": {
                "type": "string",
            },
            "cantidad": {
                "type": "integer",
            },
            "activo": {
                "type": "boolean",
            },
            "modo": {
                "type": "string",
                "enum": [
                    "a",
                    "b",
                ],
            },
        },
        "required": [
            "ruta",
        ],
    },
}


def test_valid_arguments():

    errors = validate_tool_args(
        "demo",
        {
            "ruta": "/tmp/a",
            "cantidad": 2,
            "activo": True,
            "modo": "a",
        },
        SCHEMA,
    )

    assert errors == []


def test_missing_required_argument():

    errors = validate_tool_args(
        "demo",
        {},
        SCHEMA,
    )

    assert any(
        "ruta" in error
        for error in errors
    )


def test_unknown_argument():

    errors = validate_tool_args(
        "demo",
        {
            "ruta": "/tmp/a",
            "inventado": 123,
        },
        SCHEMA,
    )

    assert any(
        "inventado" in error
        for error in errors
    )


def test_invalid_type():

    errors = validate_tool_args(
        "demo",
        {
            "ruta": 123,
        },
        SCHEMA,
    )

    assert errors


def test_invalid_enum():

    errors = validate_tool_args(
        "demo",
        {
            "ruta": "/tmp/a",
            "modo": "z",
        },
        SCHEMA,
    )

    assert errors


def test_tool_result_error_strings():

    assert not tool_result_ok(
        "Error leyendo archivo"
    )

    assert not tool_result_ok(
        "⛔ Ruta bloqueada"
    )

    assert not tool_result_ok(
        "⚠ No se pudo procesar"
    )


def test_tool_result_success_string():

    assert tool_result_ok(
        "✓ Archivo creado"
    )


def test_structured_tool_result():

    result = normalize_tool_result({
        "ok": True,
        "data": {
            "x": 1,
        },
    })

    assert result["ok"] is True
    assert result["data"]["x"] == 1
