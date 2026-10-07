from core.project_plan_builder import (
    ProjectPlanBuilder,
)


def test_builder_parses_plan():
    builder = ProjectPlanBuilder(
        llm_call=lambda _: """
{
  "tasks": [
    {
      "title": "Inspeccionar",
      "description": "Ver estructura"
    },
    {
      "title": "Probar",
      "description": "Ejecutar tests"
    },
    {
      "title": "Verificar",
      "description": "Revisar resultado"
    }
  ]
}
"""
    )

    plan = builder.build(
        objective="Mejorar Yuna",
        workspace_summary="Repo Python",
    )

    assert len(plan.tasks) == 3
    assert plan.tasks[0].title == "Inspeccionar"


def test_builder_fallback():
    builder = ProjectPlanBuilder(
        llm_call=lambda _: "garbage"
    )

    plan = builder.build(
        objective="Mejorar Yuna",
        workspace_summary="Repo",
    )

    assert len(plan.tasks) >= 3


def test_builder_limits_tasks():
    builder = ProjectPlanBuilder(
        llm_call=lambda _: """
{
  "tasks": [
    {"title":"1"},
    {"title":"2"},
    {"title":"3"},
    {"title":"4"},
    {"title":"5"},
    {"title":"6"},
    {"title":"7"}
  ]
}
"""
    )

    plan = builder.build(
        objective="Test",
        workspace_summary="Repo",
        max_tasks=4,
    )

    assert len(plan.tasks) == 4
