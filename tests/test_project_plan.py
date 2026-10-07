from core.project_plan import (
    ProjectPlan,
    ProjectTask,
)
from core.project_runner import (
    ProjectRunner,
    SessionStore,
)


def test_create_plan():
    plan = ProjectPlan.new(
        "Mejorar Yuna"
    )

    plan.add_task(
        "Inspeccionar proyecto"
    )

    plan.add_task(
        "Ejecutar tests"
    )

    assert len(plan.tasks) == 2

    assert (
        plan.tasks[0].status
        == "pending"
    )


def test_plan_task_flow():
    plan = ProjectPlan.new(
        "Test"
    )

    plan.add_task("Primera")
    plan.add_task("Segunda")

    task = plan.start_next()

    assert task is not None
    assert task.title == "Primera"
    assert task.status == "in_progress"

    plan.complete_current(
        "OK"
    )

    assert (
        plan.tasks[0].status
        == "completed"
    )

    task = plan.start_next()

    assert task.title == "Segunda"


def test_plan_complete():
    plan = ProjectPlan.new(
        "Test"
    )

    plan.add_task("A")
    plan.add_task("B")

    plan.start_next()
    plan.complete_current()

    plan.start_next()
    plan.complete_current()

    assert plan.is_complete()


def test_blocked_task():
    plan = ProjectPlan.new(
        "Test"
    )

    plan.add_task("A")

    plan.start_next()

    plan.block_current(
        "Error"
    )

    assert (
        plan.tasks[0].status
        == "blocked"
    )

    assert (
        plan.tasks[0].error
        == "Error"
    )


def test_roundtrip_dict():
    plan = ProjectPlan.new(
        "Persistencia"
    )

    plan.add_task(
        "Leer código",
        "Inspeccionar módulo",
    )

    restored = (
        ProjectPlan.from_dict(
            plan.to_dict()
        )
    )

    assert (
        restored.objective
        == plan.objective
    )

    assert (
        restored.tasks[0].title
        == "Leer código"
    )


def test_runner_persists_plan(
    tmp_path,
):
    workspace = (
        tmp_path
        / "project"
    )

    workspace.mkdir()

    store = SessionStore(
        tmp_path
        / "sessions"
    )

    runner = ProjectRunner(
        store=store
    )

    session = runner.start_session(
        workspace=workspace,
        objective="Mejorar proyecto",
        duration_seconds=300,
    )

    plan = ProjectPlan.new(
        session.objective
    )

    plan.add_task(
        "Inspeccionar"
    )

    plan.add_task(
        "Verificar"
    )

    runner.set_plan(plan)

    session_id = (
        session.session_id
    )

    runner.pause()

    runner2 = ProjectRunner(
        store=store
    )

    runner2.load_session(
        session_id
    )

    restored = (
        runner2.get_plan()
    )

    assert restored is not None

    assert (
        len(restored.tasks)
        == 2
    )

    assert (
        restored.tasks[1].title
        == "Verificar"
    )


def test_progress():
    plan = ProjectPlan.new(
        "Test"
    )

    plan.add_task("A")
    plan.add_task("B")
    plan.add_task("C")

    plan.start_next()
    plan.complete_current()

    progress = plan.progress()

    assert progress == {
        "total": 3,
        "completed": 1,
        "blocked": 0,
        "pending": 2,
        "in_progress": 0,
        "skipped": 0,
    }
