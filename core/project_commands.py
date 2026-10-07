from __future__ import annotations

import re
import shlex

from pathlib import Path

from core.project_runner import ProjectRunner
from core.project_runtime import ProjectRuntime
from core.project_plan_builder import ProjectPlanBuilder


_DURATION_RE = re.compile(
    r"^(?:(?P<hours>\d+(?:\.\d+)?)h)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)m)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)s)?$",
    re.IGNORECASE,
)


def parse_duration(
    value: str,
) -> float:

    value = value.strip().lower()

    if value.isdigit():
        return float(value) * 60

    match = _DURATION_RE.fullmatch(
        value
    )

    if not match:
        raise ValueError(
            "Duración inválida. "
            "Usa 30m, 1h, 1h30m o 90s."
        )

    hours = float(
        match.group("hours") or 0
    )

    minutes = float(
        match.group("minutes") or 0
    )

    seconds = float(
        match.group("seconds") or 0
    )

    total = (
        hours * 3600
        + minutes * 60
        + seconds
    )

    if total <= 0:
        raise ValueError(
            "La duración debe ser mayor que cero."
        )

    return total


def format_duration(
    seconds: float,
) -> str:

    seconds = max(
        0,
        int(seconds),
    )

    hours, remainder = divmod(
        seconds,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    if hours:
        return (
            f"{hours}h "
            f"{minutes:02d}m "
            f"{seconds:02d}s"
        )

    if minutes:
        return (
            f"{minutes}m "
            f"{seconds:02d}s"
        )

    return f"{seconds}s"


class ProjectCommandController:

    def __init__(
        self,
        runner: ProjectRunner | None = None,
        runtime: ProjectRuntime | None = None,
    ) -> None:

        self.runner = (
            runner
            or ProjectRunner()
        )

        self.runtime = (
            runtime
            or ProjectRuntime(
                self.runner
            )
        )

    # ---------------------------------------------------------
    # UI integration
    # ---------------------------------------------------------

    def set_event_callback(
        self,
        callback,
    ) -> None:

        self.runtime.set_event_callback(
            callback
        )

    # ---------------------------------------------------------
    # Dispatcher
    # ---------------------------------------------------------

    def handle(
        self,
        command: str,
    ) -> str:

        try:
            args = shlex.split(
                command
            )

        except ValueError as exc:
            return (
                "PROJECT ERROR\n"
                f"{exc}"
            )

        if not args:
            return self.help_text()

        if args[0] == "/project":
            args = args[1:]

        if not args:
            return self.help_text()

        action = args[0].lower()

        try:

            if action == "start":
                return self._start(
                    args[1:]
                )

            if action == "work":
                return self._work(
                    args[1:]
                )

            if action == "run":
                return self._run()

            if action == "status":
                return self._status()

            if action == "pause":
                return self._pause()

            if action == "resume":
                return self._resume()

            if action == "stop":
                return self._stop()

            if action == "complete":
                return self._complete()

            if action == "load":
                return self._load(
                    args[1:]
                )

            if action in {
                "help",
                "--help",
                "-h",
            }:
                return self.help_text()

            return (
                "PROJECT ERROR\n"
                f"Comando desconocido: {action}\n\n"
                f"{self.help_text()}"
            )

        except Exception as exc:

            return (
                "PROJECT ERROR\n"
                f"{type(exc).__name__}: {exc}"
            )

    # ---------------------------------------------------------
    # Session creation
    # ---------------------------------------------------------

    def _parse_start_args(
        self,
        args: list[str],
    ) -> tuple[
        Path,
        float,
        str,
    ]:

        if len(args) < 3:
            raise ValueError(
                'Uso: /project start '
                '<ruta> <duración> "objetivo"'
            )

        workspace = (
            Path(args[0])
            .expanduser()
            .resolve()
        )

        duration = parse_duration(
            args[1]
        )

        objective = " ".join(
            args[2:]
        ).strip()

        return (
            workspace,
            duration,
            objective,
        )

    def _create(
        self,
        args: list[str],
    ):

        (
            workspace,
            duration,
            objective,
        ) = self._parse_start_args(
            args
        )

        session = (
            self.runner.start_session(
                workspace=workspace,
                objective=objective,
                duration_seconds=duration,
            )
        )

        self.runtime.reset_worker()

        # Crear plan inicial una sola vez.
        from core.project_worker import ProjectWorker

        inspector = ProjectWorker(
            self.runner
        )

        snapshot = (
            inspector.workspace_snapshot()
        )

        summary = (
            f"Workspace: {snapshot.get('workspace')}\n"
            f"Top level: {snapshot.get('top_level')}\n"
            f"Tests: {snapshot.get('tests')}\n"
            f"Git: {snapshot.get('git_status')}"
        )

        builder = ProjectPlanBuilder()

        plan = builder.build(
            objective=session.objective,
            workspace_summary=summary,
            max_tasks=6,
        )

        self.runner.set_plan(
            plan
        )

        return (
            session,
            duration,
        )

    def _start(
        self,
        args: list[str],
    ) -> str:

        session, duration = (
            self._create(args)
        )

        return (
            "PROJECT STARTED\n"
            f"ID: {session.session_id}\n"
            f"Workspace: {session.workspace}\n"
            f"Objetivo: {session.objective}\n"
            f"Tiempo: "
            f"{format_duration(duration)}\n"
            f"Pasos máximos: "
            f"{session.max_steps}\n"
            "Worker: detenido\n\n"
            "Usa /project run para comenzar."
        )

    # ---------------------------------------------------------
    # Combined start + run
    # ---------------------------------------------------------

    def _work(
        self,
        args: list[str],
    ) -> str:

        session, duration = (
            self._create(args)
        )

        self.runtime.start_background()

        return (
            "PROJECT WORK STARTED\n"
            f"ID: {session.session_id}\n"
            f"Workspace: {session.workspace}\n"
            f"Objetivo: {session.objective}\n"
            f"Tiempo: "
            f"{format_duration(duration)}\n"
            f"Pasos máximos: "
            f"{session.max_steps}\n"
            "Worker: activo"
        )

    # ---------------------------------------------------------
    # Run
    # ---------------------------------------------------------

    def _run(self) -> str:

        session = (
            self.runner.require_session()
        )

        if session.status == "paused":
            self.runner.resume()

        self.runtime.start_background()

        return (
            "PROJECT RUNNING\n"
            f"ID: {session.session_id}\n"
            "Worker iniciado en segundo plano."
        )

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------

    def _status(self) -> str:

        data = (
            self.runner.status_summary()
        )

        runtime = (
            self.runtime.snapshot()
        )

        last = runtime.get(
            "last_step",
            {},
        )

        last_action = (
            last.get("action")
            or "-"
        )

        last_error = (
            runtime.get(
                "last_error",
                "",
            )
            or "-"
        )

        worker_status = (
            "ACTIVE"
            if runtime["active"]
            else "IDLE"
        )

        plan = self.runner.get_plan()

        plan_text = "-"
        plan_task_text = "-"

        if plan is not None:
            progress = plan.progress()

            plan_text = (
                f"{progress['completed']}/"
                f"{progress['total']} completadas"
            )

            current_plan_task = (
                plan.current_task()
            )

            if current_plan_task is not None:
                plan_task_text = (
                    current_plan_task.title
                )

        return (
            "PROJECT STATUS\n"
            f"ID: {data['session_id']}\n"
            f"Estado: {data['status']}\n"
            f"Worker: {worker_status}\n"
            f"Objetivo: {data['objective']}\n"
            f"Workspace: {data['workspace']}\n"
            f"Paso: "
            f"{data['step']}/"
            f"{data['max_steps']}\n"
            f"Restante: "
            f"{format_duration(data['remaining_seconds'])}\n"
            f"Tarea: "
            f"{data['current_task'] or '-'}\n"
            f"Última acción: {last_action}\n"
            f"Último error: {last_error}\n"
            f"Plan: {plan_text}\n"
            f"Subtarea: {plan_task_text}"
        )

    # ---------------------------------------------------------
    # Pause / resume / stop
    # ---------------------------------------------------------

    def _pause(self) -> str:

        was_active = self.runtime.active

        session = (
            self.runtime.request_pause()
        )

        if was_active:
            return (
                "PROJECT PAUSE REQUESTED\n"
                f"ID: {session.session_id}\n"
                "La pausa se aplicará al terminar "
                "el paso actual."
            )

        return (
            "PROJECT PAUSED\n"
            f"ID: {session.session_id}\n"
            f"Restante: "
            f"{format_duration(session.remaining_seconds())}"
        )

    def _resume(self) -> str:

        session = self.runtime.resume(
            run=False
        )

        return (
            "PROJECT RESUMED\n"
            f"ID: {session.session_id}\n"
            f"Objetivo: {session.objective}\n"
            f"Restante: "
            f"{format_duration(session.remaining_seconds())}\n\n"
            "Usa /project run para continuar trabajando."
        )

    def _stop(self) -> str:

        was_active = self.runtime.active

        session = (
            self.runtime.request_stop()
        )

        if was_active:
            return (
                "PROJECT STOP REQUESTED\n"
                f"ID: {session.session_id}\n"
                "El worker se detendrá de forma segura "
                "al terminar el paso actual."
            )

        return (
            "PROJECT STOPPED\n"
            f"ID: {session.session_id}\n"
            f"Pasos: {session.step}"
        )

    def _complete(self) -> str:

        if self.runtime.active:
            raise RuntimeError(
                "No puede completarse manualmente "
                "mientras el worker está activo."
            )

        session = (
            self.runner.complete()
        )

        return (
            "PROJECT COMPLETED\n"
            f"ID: {session.session_id}\n"
            f"Pasos: {session.step}"
        )

    # ---------------------------------------------------------
    # Load
    # ---------------------------------------------------------

    def _load(
        self,
        args: list[str],
    ) -> str:

        if len(args) != 1:
            return (
                "Uso:\n"
                "/project load <session_id>"
            )

        if self.runtime.active:
            raise RuntimeError(
                "Detén primero la sesión activa."
            )

        session = (
            self.runner.load_session(
                args[0]
            )
        )

        self.runtime.reset_worker()

        return (
            "PROJECT LOADED\n"
            f"ID: {session.session_id}\n"
            f"Estado: {session.status}\n"
            f"Objetivo: {session.objective}\n"
            f"Restante: "
            f"{format_duration(session.remaining_seconds())}"
        )

    # ---------------------------------------------------------
    # Help
    # ---------------------------------------------------------

    @staticmethod
    def help_text() -> str:

        return (
            "PROJECT COMMANDS\n\n"
            '/project start <ruta> <tiempo> "objetivo"\n'
            '/project work <ruta> <tiempo> "objetivo"\n'
            "/project run\n"
            "/project status\n"
            "/project pause\n"
            "/project resume\n"
            "/project stop\n"
            "/project complete\n"
            "/project load <session_id>\n\n"
            "work = crear sesión + ejecutar automáticamente\n"
            "Duraciones: 30m, 1h, 1h30m, 90s"
        )


project_commands = (
    ProjectCommandController()
)
