from core.project_runner import (
    ProjectRunner,
    SessionStore,
)
from core.project_runtime import (
    ProjectRuntime,
)


class FinishWorker:

    def __init__(
        self,
        runner,
    ):
        self.runner = runner

    def run_step(self):

        session = (
            self.runner
            .require_session()
        )

        session.step += 1
        session.current_task = "finish"
        session.completed_tasks.append(
            "finish"
        )

        session.complete()

        self.runner.store.save(
            session
        )

        return {
            "status": "completed",
            "action": "finish",
            "reason": "Terminado",
            "result": "OK",
        }


def make_runner(tmp_path):

    workspace = (
        tmp_path
        / "project"
    )

    workspace.mkdir()

    runner = ProjectRunner(
        store=SessionStore(
            tmp_path
            / "sessions"
        )
    )

    runner.start_session(
        workspace=workspace,
        objective="Test runtime",
        duration_seconds=60,
        max_steps=5,
    )

    return runner


def test_runtime_background_finishes(
    tmp_path,
):

    runner = make_runner(
        tmp_path
    )

    runtime = ProjectRuntime(
        runner,
        worker_factory=FinishWorker,
    )

    runtime.start_background(
        delay_seconds=0,
    )

    assert runtime.wait_until_idle(
        timeout=2
    )

    assert (
        runner.session.status
        == "completed"
    )

    assert (
        runner.session.step
        == 1
    )


def test_runtime_emits_events(
    tmp_path,
):

    runner = make_runner(
        tmp_path
    )

    events = []

    runtime = ProjectRuntime(
        runner,
        worker_factory=FinishWorker,
    )

    runtime.set_event_callback(
        events.append
    )

    runtime.start_background(
        delay_seconds=0,
    )

    assert runtime.wait_until_idle(
        timeout=2
    )

    types = [
        event["type"]
        for event in events
    ]

    assert "started" in types
    assert "step" in types
    assert "ended" in types


def test_runtime_status_inactive_after_finish(
    tmp_path,
):

    runner = make_runner(
        tmp_path
    )

    runtime = ProjectRuntime(
        runner,
        worker_factory=FinishWorker,
    )

    runtime.start_background(
        delay_seconds=0,
    )

    runtime.wait_until_idle(
        timeout=2
    )

    assert not runtime.active
