"""
Tests estructurales de las herramientas de Yuna.

Una tool válida debe existir simultáneamente en:
- registry
- schemas
- permissions
"""

from tools.registry import TOOLS
from tools.schemas import ALL_SCHEMAS
from tools.permisos import (
    _PERMISSIONS,
    PermissionLevel,
)


def _schema_names():
    return [
        item["function"]["name"]
        for item in ALL_SCHEMAS
    ]


def test_tool_names_are_unique():
    names = _schema_names()

    assert len(names) == len(set(names)), (
        "Hay schemas duplicados: "
        f"{names}"
    )


def test_registry_and_schemas_match():

    registry = set(TOOLS)
    schemas = set(_schema_names())

    assert registry == schemas, (
        "\nRegistry y schemas están desincronizados.\n"
        f"Solo registry: {sorted(registry - schemas)}\n"
        f"Solo schemas: {sorted(schemas - registry)}"
    )


def test_registry_and_permissions_match():

    registry = set(TOOLS)
    permissions = set(_PERMISSIONS)

    assert registry == permissions, (
        "\nRegistry y permisos están desincronizados.\n"
        f"Sin permiso: {sorted(registry - permissions)}\n"
        f"Permiso sin tool: {sorted(permissions - registry)}"
    )


def test_every_permission_is_valid():

    for name, permission in _PERMISSIONS.items():
        assert isinstance(
            permission,
            PermissionLevel,
        ), (
            f"{name} tiene un permiso inválido: "
            f"{permission!r}"
        )


def test_every_schema_is_function():

    for schema in ALL_SCHEMAS:

        assert schema.get("type") == "function"

        function = schema.get("function")

        assert isinstance(
            function,
            dict,
        )

        assert function.get("name")
        assert function.get("description")

        parameters = function.get(
            "parameters",
        )

        assert isinstance(
            parameters,
            dict,
        )

        assert parameters.get(
            "type"
        ) == "object"
