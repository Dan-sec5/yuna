import pytest

from core.project_commands import (
    ProjectCommandController,
    format_duration,
    parse_duration,
)
from core.project_runner import (
    ProjectRunner,
    SessionStore,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("30m", 1800),
        ("1h", 3600),
        ("1h30m", 5400),
        ("90s", 90),
        ("5", 300),
    ],
)
def test_parse_duration(value, expected):
    assert parse_duration(value) == expected


def test_invalid_duration():
    with pytest.raises(ValueError):
        parse_duration("banana")


def test_format_duration():
    assert format_duration(90) == "1m 30s"
    assert format_duration(3661) == "1h 01m 01s"


def test_project_command_flow(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    runner = ProjectRunner(
        store=SessionStore(
            tmp_path / "sessions"
        )
    )

    controller = ProjectCommandController(
        runner=runner
    )

    result = controller.handle(
        f'/project start "{workspace}" 30m '
        '"Mejorar pruebas"'
    )

    assert "PROJECT STARTED" in result
    assert runner.session is not None
    assert runner.session.status == "running"

    result = controller.handle(
        "/project status"
    )

    assert "PROJECT STATUS" in result
    assert "Mejorar pruebas" in result

    result = controller.handle(
        "/project pause"
    )

    assert "PROJECT PAUSED" in result
    assert runner.session.status == "paused"

    result = controller.handle(
        "/project resume"
    )

    assert "PROJECT RESUMED" in result
    assert runner.session.status == "running"

    result = controller.handle(
        "/project stop"
    )

    assert "PROJECT STOPPED" in result
    assert runner.session.status == "stopped"


def test_load_session(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    store = SessionStore(
        tmp_path / "sessions"
    )

    runner1 = ProjectRunner(store=store)

    session = runner1.start_session(
        workspace=workspace,
        objective="Persistir",
        duration_seconds=300,
    )

    session_id = session.session_id

    runner1.pause()

    runner2 = ProjectRunner(store=store)

    controller = ProjectCommandController(
        runner=runner2
    )

    result = controller.handle(
        f"/project load {session_id}"
    )

    assert "PROJECT LOADED" in result
    assert runner2.session is not None
    assert runner2.session.session_id == session_id
