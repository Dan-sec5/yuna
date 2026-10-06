from core.project_planner import (
    ProjectPlanner,
)


def test_planner_parses_json():
    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"git_status",'
            '"reason":"Revisar cambios",'
            '"target":""}'
        )
    )

    decision = planner.plan(
        objective="Mejorar Yuna",
        step=1,
        max_steps=10,
        remaining_seconds=100,
        snapshot={},
    )

    assert decision.action == "git_status"
    assert decision.reason == "Revisar cambios"


def test_planner_extracts_json_from_text():
    planner = ProjectPlanner(
        llm_call=lambda _: (
            'Resultado:\n'
            '{"action":"inspect_workspace",'
            '"reason":"Inspeccionar",'
            '"target":""}'
        )
    )

    decision = planner.plan(
        objective="Test",
        step=0,
        max_steps=5,
        remaining_seconds=100,
        snapshot={},
    )

    assert (
        decision.action
        == "inspect_workspace"
    )


def test_invalid_action_uses_fallback():
    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"rm_everything",'
            '"reason":"Oops"}'
        )
    )

    decision = planner.plan(
        objective="Test",
        step=0,
        max_steps=5,
        remaining_seconds=100,
        snapshot={},
    )

    assert (
        decision.action
        == "inspect_workspace"
    )


def test_fallback_progression():
    planner = ProjectPlanner(
        llm_call=lambda _: "not json"
    )

    decision = planner.plan(
        objective="Test",
        step=1,
        max_steps=10,
        remaining_seconds=100,
        snapshot={
            "tests": [
                "tests/test_a.py"
            ]
        },
        recent_history=[
            "inspect_workspace: done"
        ],
    )

    assert decision.action == "git_status"
