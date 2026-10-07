from __future__ import annotations

import threading
import time

from collections.abc import Callable
from typing import Any

from core.project_runner import ProjectRunner
from core.project_worker import ProjectWorker


EventCallback = Callable[[dict[str, Any]], None]
WorkerFactory = Callable[[ProjectRunner], ProjectWorker]


class ProjectRuntime:
    """
    Runtime cooperativo para Project Mode.

    - Un solo worker.
    - Un solo hilo de trabajo.
    - Pause/stop entre pasos.
    - El LLM nunca controla el loop.
    """

    def __init__(
        self,
        runner: ProjectRunner,
        *,
        worker_factory: WorkerFactory | None = None,
    ) -> None:

        self.runner = runner

        self.worker_factory = (
            worker_factory
            or (lambda r: ProjectWorker(r))
        )

        self._worker: ProjectWorker | None = None
        self._worker_session_id: str | None = None

        self._thread: threading.Thread | None = None

        self._pause_requested = threading.Event()
        self._stop_requested = threading.Event()

        self._lock = threading.RLock()

        self._callback: EventCallback | None = None

        self._last_event: dict[str, Any] = {}
        self._last_step: dict[str, Any] = {}
        self._last_error: str = ""

    # ---------------------------------------------------------
    # Events
    # ---------------------------------------------------------

    def set_event_callback(
        self,
        callback: EventCallback | None,
    ) -> None:
        with self._lock:
            self._callback = callback

    def _emit(
        self,
        event: dict[str, Any],
    ) -> None:

        with self._lock:
            self._last_event = dict(event)

            event_type = event.get(
                "type",
                "",
            )

            if event_type == "step":
                self._last_step = dict(
                    event
                )

            elif event_type == "error":
                self._last_error = str(
                    event.get(
                        "error",
                        "",
                    )
                )

            callback = self._callback

        if callback is None:
            return

        try:
            callback(dict(event))
        except Exception:
            # El callback visual nunca debe tumbar
            # el Project Worker.
            pass

    # ---------------------------------------------------------
    # Worker
    # ---------------------------------------------------------

    def reset_worker(self) -> None:
        with self._lock:
            self._worker = None
            self._worker_session_id = None

    def _get_worker(self) -> ProjectWorker:

        session = self.runner.require_session()

        with self._lock:

            if (
                self._worker is None
                or self._worker_session_id
                != session.session_id
            ):
                self._worker = self.worker_factory(
                    self.runner
                )

                self._worker_session_id = (
                    session.session_id
                )

            return self._worker

    # ---------------------------------------------------------
    # State
    # ---------------------------------------------------------

    @property
    def active(self) -> bool:
        thread = self._thread

        return bool(
            thread
            and thread.is_alive()
        )

    def snapshot(self) -> dict[str, Any]:

        with self._lock:
            last_event = dict(
                self._last_event
            )

            last_step = dict(
                self._last_step
            )

            last_error = (
                self._last_error
            )

        return {
            "active": self.active,
            "pause_requested": (
                self._pause_requested.is_set()
            ),
            "stop_requested": (
                self._stop_requested.is_set()
            ),
            "last_event": last_event,
            "last_step": last_step,
            "last_error": last_error,
        }

    # ---------------------------------------------------------
    # Start
    # ---------------------------------------------------------

    def start_background(
        self,
        *,
        delay_seconds: float = 0.25,
    ) -> None:

        session = self.runner.require_session()

        if session.status != "running":
            raise RuntimeError(
                "La sesión debe estar running "
                "antes de ejecutar el worker."
            )

        with self._lock:

            if self.active:
                raise RuntimeError(
                    "Project Worker ya está activo."
                )

            self._pause_requested.clear()
            self._stop_requested.clear()

            self._thread = threading.Thread(
                target=self._run_loop,
                kwargs={
                    "delay_seconds": delay_seconds,
                },
                daemon=True,
                name="yuna-project-worker",
            )

            self._thread.start()

    # ---------------------------------------------------------
    # Loop
    # ---------------------------------------------------------

    def _run_loop(
        self,
        *,
        delay_seconds: float,
    ) -> None:

        session = self.runner.require_session()

        self._emit({
            "type": "started",
            "session_id": session.session_id,
            "objective": session.objective,
        })

        try:

            worker = self._get_worker()

            while True:

                session = self.runner.require_session()

                session.enforce_limits()

                # ---------------------------------------------
                # Stop solicitado
                # ---------------------------------------------

                if self._stop_requested.is_set():

                    if session.status == "running":
                        self.runner.stop()

                    break

                # ---------------------------------------------
                # Pause solicitado
                # ---------------------------------------------

                if self._pause_requested.is_set():

                    if session.status == "running":
                        self.runner.pause()

                    break

                if not session.can_continue():
                    break

                # ---------------------------------------------
                # Un paso autónomo
                # ---------------------------------------------

                result = worker.run_step()

                session = self.runner.require_session()

                self._emit({
                    "type": "step",
                    "session_id": session.session_id,
                    "step": session.step,
                    "max_steps": session.max_steps,
                    "action": result.get(
                        "action",
                        "",
                    ),
                    "reason": result.get(
                        "reason",
                        "",
                    ),
                    "result": result.get(
                        "result",
                        "",
                    )[:2500],
                    "status": session.status,
                    "remaining_seconds": round(
                        session.remaining_seconds(),
                        2,
                    ),
                })

                # finish puede significar:
                #
                # - fin de una subtarea, si existe ProjectPlan
                # - fin del proyecto, si la sesión ya dejó
                #   de estar running.
                #
                # Solo detenemos el runtime cuando la sesión
                # realmente ha terminado.
                if result.get("action") == "finish":
                    session = (
                        self.runner
                        .require_session()
                    )

                    if session.status != "running":
                        break

                # Permite reaccionar a pause/stop
                # sin usar sleep ciego.
                if delay_seconds > 0:
                    if self._stop_requested.wait(
                        delay_seconds
                    ):
                        continue

        except Exception as exc:

            error_text = (
                f"{type(exc).__name__}: {exc}"
            )

            self._emit({
                "type": "error",
                "error": error_text,
            })

            session = self.runner.session

            if session is not None:
                session.notes.append(
                    "PROJECT_RUNTIME_ERROR: "
                    + error_text
                )

                try:
                    self.runner.store.save(
                        session
                    )
                except Exception:
                    pass

            if (
                session is not None
                and session.status == "running"
            ):
                try:
                    self.runner.pause()
                except Exception:
                    pass

        finally:

            session = self.runner.session

            self._emit({
                "type": "ended",
                "status": (
                    session.status
                    if session
                    else "unknown"
                ),
                "step": (
                    session.step
                    if session
                    else 0
                ),
            })

    # ---------------------------------------------------------
    # Controls
    # ---------------------------------------------------------

    def request_pause(self):
        session = self.runner.require_session()

        if self.active:
            self._pause_requested.set()
        elif session.status == "running":
            self.runner.pause()

        return session

    def resume(
        self,
        *,
        run: bool = False,
    ):
        session = self.runner.require_session()

        if session.status == "paused":
            session = self.runner.resume()

        elif session.status != "running":
            raise RuntimeError(
                "Solo puede reanudarse una sesión "
                "paused/running."
            )

        self._pause_requested.clear()
        self._stop_requested.clear()

        if run:
            self.start_background()

        return session

    def request_stop(self):
        session = self.runner.require_session()

        if self.active:
            self._stop_requested.set()
        elif session.status not in {
            "completed",
            "stopped",
            "expired",
            "step_limit",
        }:
            self.runner.stop()

        return session

    def wait_until_idle(
        self,
        timeout: float = 5.0,
    ) -> bool:

        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:

            if not self.active:
                return True

            time.sleep(0.01)

        return not self.active
