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


def test_worker_read_file(tmp_path):
    runner = make_runner(
        tmp_path
    )

    workspace = (
        tmp_path
        / "project"
    )

    (
        workspace
        / "example.py"
    ).write_text(
        "VALUE = 42\n",
        encoding="utf-8",
    )

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"read_file",'
            '"reason":"Leer archivo",'
            '"target":"example.py"}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    assert result["action"] == "read_file"
    assert "VALUE = 42" in result["result"]


def test_worker_search_files(tmp_path):
    runner = make_runner(
        tmp_path
    )

    workspace = (
        tmp_path
        / "project"
    )

    (
        workspace
        / "special.py"
    ).write_text(
        "MAGIC_SYMBOL = 123\n",
        encoding="utf-8",
    )

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"search_files",'
            '"reason":"Buscar símbolo",'
            '"target":"MAGIC_SYMBOL"}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    assert (
        result["action"]
        == "search_files"
    )

    assert (
        "MAGIC_SYMBOL"
        in result["result"]
    )


def test_worker_blocks_duplicate_action_target(
    tmp_path,
):
    runner = make_runner(
        tmp_path
    )

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"list_tests",'
            '"reason":"Listar otra vez",'
            '"target":""}'
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

    actions = [
        item["action"]
        for item in results
    ]

    assert actions.count("list_tests") == 1
    assert actions[-1] == "finish"
    assert runner.session.status == "completed"


def test_worker_edit_file_transaction(tmp_path):
    runner = make_runner(tmp_path)

    workspace = tmp_path / "project"

    target = workspace / "sample.py"
    target.write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"edit_file",'
            '"reason":"Actualizar valor",'
            '"target":"sample.py ||| VALUE = 2\\n"}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    assert result["action"] == "edit_file"
    assert "TX=" in result["result"]

    assert target.read_text(
        encoding="utf-8"
    ) == "VALUE = 2\n"


def test_worker_create_file_transaction(tmp_path):
    runner = make_runner(tmp_path)

    workspace = tmp_path / "project"

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"create_file",'
            '"reason":"Crear archivo",'
            '"target":"new.py ||| HELLO = True\\n"}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    target = workspace / "new.py"

    assert result["action"] == "create_file"
    assert target.exists()

    assert target.read_text(
        encoding="utf-8"
    ) == "HELLO = True\n"


def test_worker_edit_missing_file_fails(
    tmp_path,
):
    runner = make_runner(tmp_path)

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"edit_file",'
            '"reason":"Editar faltante",'
            '"target":"missing.py ||| X = 1"}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    import pytest

    with pytest.raises(
        FileNotFoundError
    ):
        worker.run_step()


def test_worker_valid_edit_is_committed(
    tmp_path,
):
    runner = make_runner(
        tmp_path
    )

    workspace = (
        tmp_path
        / "project"
    )

    target = (
        workspace
        / "valid.py"
    )

    target.write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"edit_file",'
            '"reason":"Cambio válido",'
            '"target":"valid.py ||| VALUE = 2\\n"}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    assert (
        "STATUS=committed"
        in result["result"]
    )

    assert target.read_text(
        encoding="utf-8"
    ) == "VALUE = 2\n"


def test_worker_invalid_python_rolls_back(
    tmp_path,
):
    runner = make_runner(
        tmp_path
    )

    workspace = (
        tmp_path
        / "project"
    )

    target = (
        workspace
        / "broken.py"
    )

    original = (
        "VALUE = 1\n"
    )

    target.write_text(
        original,
        encoding="utf-8",
    )

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"edit_file",'
            '"reason":"Crear error",'
            '"target":"broken.py ||| def broken(\\n"}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    assert (
        "STATUS=rolled_back"
        in result["result"]
    )

    assert (
        "py_compile: FAIL"
        in result["result"]
    )

    assert target.read_text(
        encoding="utf-8"
    ) == original


def test_plan_finish_advances_to_next_task(
    tmp_path,
):
    from core.project_plan import (
        ProjectPlan,
    )

    runner = make_runner(
        tmp_path
    )

    plan = ProjectPlan.new(
        runner.session.objective
    )

    plan.add_task("Primera tarea")
    plan.add_task("Segunda tarea")

    runner.set_plan(plan)

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"finish",'
            '"reason":"Subtarea terminada",'
            '"target":""}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    worker.run_step()

    restored = runner.get_plan()

    assert restored is not None

    assert (
        restored.tasks[0].status
        == "completed"
    )

    assert (
        restored.tasks[1].status
        == "pending"
    )

    # El proyecto NO debe terminar aún.
    assert (
        runner.session.status
        == "running"
    )


def test_plan_finishes_session_after_last_task(
    tmp_path,
):
    from core.project_plan import (
        ProjectPlan,
    )

    runner = make_runner(
        tmp_path
    )

    plan = ProjectPlan.new(
        runner.session.objective
    )

    plan.add_task("Primera")
    plan.add_task("Segunda")

    runner.set_plan(plan)

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"finish",'
            '"reason":"Terminada",'
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
        == "running"
    )

    worker.run_step()

    restored = runner.get_plan()

    assert restored is not None
    assert restored.is_complete()

    assert (
        runner.session.status
        == "completed"
    )


def test_plan_progress_after_finish(
    tmp_path,
):
    from core.project_plan import (
        ProjectPlan,
    )

    runner = make_runner(
        tmp_path
    )

    plan = ProjectPlan.new(
        "Proyecto"
    )

    plan.add_task("A")
    plan.add_task("B")
    plan.add_task("C")

    runner.set_plan(plan)

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"finish",'
            '"reason":"OK",'
            '"target":""}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    worker.run_step()

    progress = (
        runner.get_plan()
        .progress()
    )

    assert progress["completed"] == 1
    assert progress["total"] == 3


def test_worker_noop_edit_does_not_fail(
    tmp_path,
):
    runner = make_runner(
        tmp_path
    )

    workspace = (
        tmp_path
        / "project"
    )

    target = (
        workspace
        / "same.py"
    )

    target.write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"edit_file",'
            '"reason":"Aplicar contenido",'
            '"target":"same.py ||| VALUE = 1\\n"}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    assert result["action"] == "edit_file"

    assert (
        "NO_CHANGE"
        in result["result"]
    )

    assert (
        runner.session.status
        == "running"
    )

    assert target.read_text(
        encoding="utf-8"
    ) == "VALUE = 1\n"


def test_successful_edit_auto_completes_plan_task(
    tmp_path,
):
    from core.project_plan import ProjectPlan

    runner = make_runner(
        tmp_path
    )

    workspace = tmp_path / "project"

    target = workspace / "value.py"

    target.write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    plan = ProjectPlan.new(
        "Cambiar valor"
    )

    plan.add_task(
        "Editar value.py"
    )

    runner.set_plan(plan)

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"edit_file",'
            '"reason":"Cambiar valor",'
            '"target":"value.py ||| VALUE = 2\\n"}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    assert (
        "STATUS=committed"
        in result["result"]
    )

    restored = runner.get_plan()

    assert restored is not None

    assert (
        restored.tasks[0].status
        == "completed"
    )


def test_successful_tests_auto_complete_verify_task(
    tmp_path,
):
    from core.project_plan import ProjectPlan

    runner = make_runner(
        tmp_path
    )

    plan = ProjectPlan.new(
        "Verificar proyecto"
    )

    plan.add_task(
        "Verificar tests"
    )

    runner.set_plan(plan)

    planner = ProjectPlanner(
        llm_call=lambda _: (
            '{"action":"run_tests",'
            '"reason":"Ejecutar pruebas",'
            '"target":"tests/test_example.py"}'
        )
    )

    worker = ProjectWorker(
        runner,
        planner,
    )

    result = worker.run_step()

    assert (
        "returncode=0"
        in result["result"]
    )

    restored = runner.get_plan()

    assert restored is not None

    assert (
        restored.tasks[0].status
        == "completed"
    )
