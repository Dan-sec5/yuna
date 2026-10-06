from core.project_planner import (
    ProjectPlanner,
)
from core.project_runner import (
    ProjectRunner,
    SessionStore,
)
from core.project_worker import (
    ProjectWorker,
)


def make_runner(tmp_path):
    workspace = (
        tmp_path
        / "project"
    )

    workspace.mkdir()

    tests = (
        workspace
        / "tests"
    )

    tests.mkdir()

    (
        tests
        / "test_example.py"
    ).write_text(
        "def test_ok():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    runner = ProjectRunner(
        store=SessionStore(
            tmp_path
            / "sessions"
        )
    )

    runner.start_session(
        workspace=workspace,
        objective="Inspeccionar proyecto",
        duration_seconds=300,
        max_steps=10,
    )

    return runner


def test_worker_inspect(tmp_path):
    runner = make_runner(
        tmp_path
    )

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"inspect_workspace",'
            '"reason":"Primera inspección",'
            '"target":""}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    assert (
        result["action"]
        == "inspect_workspace"
    )

    assert runner.session.step == 1


def test_worker_list_tests(tmp_path):
    runner = make_runner(
        tmp_path
    )

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"list_tests",'
            '"reason":"Buscar pruebas",'
            '"target":""}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    assert (
        "test_example.py"
        in result["result"]
    )


def test_finish_pauses_session(tmp_path):
    runner = make_runner(
        tmp_path
    )

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"finish",'
            '"reason":"Inspección suficiente",'
            '"target":""}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    worker.run_step()

    assert (
        runner.session.status
        == "completed"
    )


def test_worker_multiple_steps(tmp_path):
    runner = make_runner(
        tmp_path
    )

    actions = iter([
        (
            '{"action":"inspect_workspace",'
            '"reason":"Inspección",'
            '"target":""}'
        ),
        (
            '{"action":"git_status",'
            '"reason":"Git",'
            '"target":""}'
        ),
        (
            '{"action":"finish",'
            '"reason":"Terminado",'
            '"target":""}'
        ),
    ])

    planner = ProjectPlanner(
        llm_call=lambda _: next(
            actions
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    results = worker.run(
        max_iterations=5,
        delay_seconds=0,
    )

    assert len(results) == 3

    assert (
        results[-1]["action"]
        == "finish"
    )

    assert (
        runner.session.status
        == "completed"
    )
