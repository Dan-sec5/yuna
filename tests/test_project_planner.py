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


def test_planner_avoids_repeated_action():
    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"list_tests",'
            '"reason":"Otra vez",'
            '"target":""}'
        )
    )

    decision = planner.plan(
        objective="Investigar",
        step=3,
        max_steps=10,
        remaining_seconds=100,
        snapshot={
            "tests": [
                "tests/test_project_worker.py"
            ]
        },
        recent_history=[
            (
                "ACTION=list_tests\n"
                "RESULT=test_project_worker.py"
            ),
            (
                "ACTION=list_tests\n"
                "RESULT=test_project_worker.py"
            ),
        ],
    )

    assert decision.action != "list_tests"


def test_edit_file_preserves_trailing_newline():
    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"edit_file",'
            '"reason":"Editar",'
            '"target":"sample.py ||| VALUE = 2\\n"}'
        )
    )

    decision = planner.plan(
        objective="Editar archivo",
        step=0,
        max_steps=5,
        remaining_seconds=100,
        snapshot={},
    )

    assert decision.action == "edit_file"

    assert decision.target.endswith(
        "VALUE = 2\n"
    )


def test_create_file_preserves_trailing_newline():
    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"create_file",'
            '"reason":"Crear",'
            '"target":"new.py ||| HELLO = True\\n"}'
        )
    )

    decision = planner.plan(
        objective="Crear archivo",
        step=0,
        max_steps=5,
        remaining_seconds=100,
        snapshot={},
    )

    assert decision.action == "create_file"

    assert decision.target.endswith(
        "HELLO = True\n"
    )
