from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from core.project_runner import (
    ProjectRunner,
    SessionStore,
)
from core.project_session import (
    ProjectSession,
)


def dt(seconds: int = 0):
    base = datetime(
        2026,
        10,
        6,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    return base + timedelta(
        seconds=seconds
    )


def test_create_session(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    session = ProjectSession.new(
        workspace=workspace,
        objective="Mejorar tests",
        duration_seconds=60,
        max_steps=10,
    )

    assert session.status == "pending"
    assert session.step == 0
    assert session.max_steps == 10
    assert session.objective == "Mejorar tests"


def test_timer_pause_resume(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    session = ProjectSession.new(
        workspace=workspace,
        objective="Probar timer",
        duration_seconds=60,
    )

    session.start(now=dt(0))

    assert session.remaining_seconds(
        now=dt(10)
    ) == pytest.approx(50)

    session.pause(now=dt(10))

    assert session.status == "paused"
    assert session.elapsed_seconds == pytest.approx(10)

    session.start(now=dt(20))

    assert session.remaining_seconds(
        now=dt(25)
    ) == pytest.approx(45)


def test_step_limit(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    session = ProjectSession.new(
        workspace=workspace,
        objective="Dos pasos",
        duration_seconds=60,
        max_steps=2,
    )

    session.start(now=dt(0))

    session.record_step(
        "Paso uno",
        now=dt(1),
    )

    assert session.status == "running"

    session.record_step(
        "Paso dos",
        now=dt(2),
    )

    assert session.step == 2
    assert session.status == "step_limit"


def test_time_limit(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    session = ProjectSession.new(
        workspace=workspace,
        objective="Expirar",
        duration_seconds=10,
    )

    session.start(now=dt(0))

    session.enforce_limits(
        now=dt(11)
    )

    assert session.status == "expired"


def test_checkpoint_and_recovery(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    store = SessionStore(
        tmp_path / "sessions"
    )

    session = ProjectSession.new(
        workspace=workspace,
        objective="Persistencia",
        duration_seconds=60,
    )

    session.start(now=dt(0))

    store.save(
        session,
        now=dt(15),
    )

    loaded = store.load(
        session.session_id,
        recover_running=True,
    )

    assert loaded.status == "paused"
    assert loaded.elapsed_seconds == pytest.approx(15)
    assert loaded.run_started_at is None


def test_runner_start_pause_resume_stop(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    store = SessionStore(
        tmp_path / "sessions"
    )

    runner = ProjectRunner(
        store=store
    )

    session = runner.start_session(
        workspace=workspace,
        objective="Trabajar en proyecto",
        duration_seconds=60,
        max_steps=5,
    )

    assert session.status == "running"

    runner.pause()

    assert runner.session.status == "paused"

    runner.resume()

    assert runner.session.status == "running"

    runner.stop()

    assert runner.session.status == "stopped"


def test_invalid_workspace(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(
        FileNotFoundError
    ):
        ProjectSession.new(
            workspace=missing,
            objective="No existe",
            duration_seconds=60,
        )
