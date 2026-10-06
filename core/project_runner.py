from __future__ import annotations

import json
from pathlib import Path

from core.project_session import (
    ProjectSession,
    utc_now,
)


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_SESSION_DIR = (
    ROOT_DIR
    / "data"
    / "projects"
    / "sessions"
)


class SessionStore:
    def __init__(
        self,
        directory: str | Path = DEFAULT_SESSION_DIR,
    ) -> None:
        self.directory = (
            Path(directory)
            .expanduser()
            .resolve()
        )

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def path_for(
        self,
        session_id: str,
    ) -> Path:
        return self.directory / f"{session_id}.json"

    def save(
        self,
        session: ProjectSession,
        *,
        now=None,
    ) -> Path:
        data = session.checkpoint(
            now=now,
        )

        path = self.path_for(
            session.session_id
        )

        temp_path = path.with_suffix(
            ".json.tmp"
        )

        temp_path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        temp_path.replace(path)

        return path

    def load(
        self,
        session_id: str,
        *,
        recover_running: bool = True,
    ) -> ProjectSession:
        path = self.path_for(session_id)

        if not path.exists():
            raise FileNotFoundError(
                f"No existe la sesión: "
                f"{session_id}"
            )

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        session = ProjectSession.from_dict(
            data
        )

        if (
            recover_running
            and session.status == "running"
        ):
            # Una sesión que quedó "running"
            # probablemente terminó por cierre/crash.
            #
            # La recuperamos como PAUSED.
            # No contamos como trabajo el tiempo
            # durante el cual Yuna estuvo apagada.
            session.run_started_at = None
            session.status = "paused"

            self.save(session)

        return session


class ProjectRunner:
    def __init__(
        self,
        store: SessionStore | None = None,
    ) -> None:
        self.store = (
            store
            if store is not None
            else SessionStore()
        )

        self.session: ProjectSession | None = None

    def start_session(
        self,
        *,
        workspace: str | Path,
        objective: str,
        duration_seconds: float,
        max_steps: int = 30,
    ) -> ProjectSession:
        if (
            self.session is not None
            and self.session.status == "running"
        ):
            raise RuntimeError(
                "Ya existe una sesión activa."
            )

        session = ProjectSession.new(
            workspace=workspace,
            objective=objective,
            duration_seconds=duration_seconds,
            max_steps=max_steps,
        )

        session.start()

        self.session = session
        self.store.save(session)

        return session

    def load_session(
        self,
        session_id: str,
    ) -> ProjectSession:
        self.session = self.store.load(
            session_id,
            recover_running=True,
        )

        return self.session

    def require_session(
        self,
    ) -> ProjectSession:
        if self.session is None:
            raise RuntimeError(
                "No hay una sesión cargada."
            )

        return self.session

    def pause(self) -> ProjectSession:
        session = self.require_session()

        session.pause()
        self.store.save(session)

        return session

    def resume(self) -> ProjectSession:
        session = self.require_session()

        session.start()
        self.store.save(session)

        return session

    def stop(self) -> ProjectSession:
        session = self.require_session()

        session.stop()
        self.store.save(session)

        return session

    def complete(self) -> ProjectSession:
        session = self.require_session()

        session.complete()
        self.store.save(session)

        return session

    def checkpoint(self) -> Path:
        session = self.require_session()

        session.enforce_limits()

        return self.store.save(session)

    def record_step(
        self,
        task: str,
        *,
        completed: bool = True,
        note: str | None = None,
    ) -> ProjectSession:
        session = self.require_session()

        session.record_step(
            task,
            completed=completed,
            note=note,
        )

        self.store.save(session)

        return session

    def remaining_seconds(self) -> float:
        session = self.require_session()

        session.enforce_limits()

        return session.remaining_seconds()

    def status_summary(self) -> dict:
        session = self.require_session()

        session.enforce_limits()

        return {
            "session_id": session.session_id,
            "workspace": session.workspace,
            "objective": session.objective,
            "status": session.status,
            "step": session.step,
            "max_steps": session.max_steps,
            "elapsed_seconds": round(
                session._effective_elapsed(),
                2,
            ),
            "remaining_seconds": round(
                session.remaining_seconds(),
                2,
            ),
            "current_task": session.current_task,
        }
