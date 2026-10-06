from __future__ import annotations

import re
import shlex
from pathlib import Path

from core.project_runner import ProjectRunner


_DURATION_RE = re.compile(
    r"^(?:(?P<hours>\d+(?:\.\d+)?)h)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)m)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)s)?$",
    re.IGNORECASE,
)


def parse_duration(value: str) -> float:
    value = value.strip().lower()

    if value.isdigit():
        return float(value) * 60

    match = _DURATION_RE.fullmatch(value)

    if not match:
        raise ValueError(
            "Duración inválida. Usa 30m, 1h, 1h30m o 90s."
        )

    hours = float(match.group("hours") or 0)
    minutes = float(match.group("minutes") or 0)
    seconds = float(match.group("seconds") or 0)

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


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"

    if minutes:
        return f"{minutes}m {seconds:02d}s"

    return f"{seconds}s"


class ProjectCommandController:
    def __init__(
        self,
        runner: ProjectRunner | None = None,
    ) -> None:
        self.runner = runner or ProjectRunner()

    def handle(
        self,
        command: str,
    ) -> str:
        try:
            args = shlex.split(command)
        except ValueError as exc:
            return f"PROJECT ERROR\n{exc}"

        if not args:
            return self.help_text()

        if args[0] == "/project":
            args = args[1:]

        if not args:
            return self.help_text()

        action = args[0].lower()

        try:
            if action == "start":
                return self._start(args[1:])

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
                return self._load(args[1:])

            if action in {
                "help",
                "--help",
                "-h",
            }:
                return self.help_text()

            return (
                f"PROJECT ERROR\n"
                f"Comando desconocido: {action}\n\n"
                f"{self.help_text()}"
            )

        except Exception as exc:
            return (
                "PROJECT ERROR\n"
                f"{type(exc).__name__}: {exc}"
            )

    def _start(
        self,
        args: list[str],
    ) -> str:
        if len(args) < 3:
            return (
                "Uso:\n"
                '/project start <ruta> <duración> "objetivo"'
            )

        workspace = (
            Path(args[0])
            .expanduser()
            .resolve()
        )

        duration = parse_duration(args[1])
        objective = " ".join(args[2:]).strip()

        session = self.runner.start_session(
            workspace=workspace,
            objective=objective,
            duration_seconds=duration,
        )

        return (
            "PROJECT STARTED\n"
            f"ID: {session.session_id}\n"
            f"Workspace: {session.workspace}\n"
            f"Objetivo: {session.objective}\n"
            f"Tiempo: {format_duration(duration)}\n"
            f"Pasos máximos: {session.max_steps}"
        )

    def _status(self) -> str:
        data = self.runner.status_summary()

        return (
            "PROJECT STATUS\n"
            f"ID: {data['session_id']}\n"
            f"Estado: {data['status']}\n"
            f"Objetivo: {data['objective']}\n"
            f"Workspace: {data['workspace']}\n"
            f"Paso: {data['step']}/{data['max_steps']}\n"
            f"Restante: "
            f"{format_duration(data['remaining_seconds'])}\n"
            f"Tarea: {data['current_task'] or '-'}"
        )

    def _pause(self) -> str:
        session = self.runner.pause()

        return (
            "PROJECT PAUSED\n"
            f"ID: {session.session_id}\n"
            f"Restante: "
            f"{format_duration(session.remaining_seconds())}"
        )

    def _resume(self) -> str:
        session = self.runner.resume()

        return (
            "PROJECT RESUMED\n"
            f"ID: {session.session_id}\n"
            f"Objetivo: {session.objective}\n"
            f"Restante: "
            f"{format_duration(session.remaining_seconds())}"
        )

    def _stop(self) -> str:
        session = self.runner.stop()

        return (
            "PROJECT STOPPED\n"
            f"ID: {session.session_id}\n"
            f"Pasos: {session.step}"
        )

    def _complete(self) -> str:
        session = self.runner.complete()

        return (
            "PROJECT COMPLETED\n"
            f"ID: {session.session_id}\n"
            f"Pasos: {session.step}"
        )

    def _load(
        self,
        args: list[str],
    ) -> str:
        if len(args) != 1:
            return (
                "Uso:\n"
                "/project load <session_id>"
            )

        session = self.runner.load_session(
            args[0]
        )

        return (
            "PROJECT LOADED\n"
            f"ID: {session.session_id}\n"
            f"Estado: {session.status}\n"
            f"Objetivo: {session.objective}\n"
            f"Restante: "
            f"{format_duration(session.remaining_seconds())}"
        )

    @staticmethod
    def help_text() -> str:
        return (
            "PROJECT COMMANDS\n\n"
            '/project start <ruta> <tiempo> "objetivo"\n'
            "/project status\n"
            "/project pause\n"
            "/project resume\n"
            "/project stop\n"
            "/project complete\n"
            "/project load <session_id>\n\n"
            "Duraciones: 30m, 1h, 1h30m, 90s"
        )


project_commands = ProjectCommandController()
