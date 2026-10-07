from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid


VALID_STATUSES = {
    "pending",
    "running",
    "paused",
    "completed",
    "stopped",
    "expired",
    "step_limit",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


@dataclass
class ProjectSession:
    session_id: str
    workspace: str
    objective: str
    duration_seconds: float

    max_steps: int = 30
    status: str = "pending"
    step: int = 0

    created_at: str = field(
        default_factory=lambda: utc_now().isoformat()
    )
    started_at: str | None = None
    run_started_at: str | None = None
    stopped_at: str | None = None

    elapsed_seconds: float = 0.0

    current_task: str = ""
    completed_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    # Plan persistente de Project Mode.
    # Se almacena como dict para mantener ProjectSession
    # desacoplado de la implementación del planner.
    plan: dict[str, Any] | None = None

    @classmethod
    def new(
        cls,
        workspace: str | Path,
        objective: str,
        duration_seconds: float,
        max_steps: int = 30,
    ) -> "ProjectSession":
        path = Path(workspace).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"Workspace no existe: {path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                f"Workspace no es un directorio: {path}"
            )

        objective = objective.strip()

        if not objective:
            raise ValueError(
                "El objetivo no puede estar vacío."
            )

        if duration_seconds <= 0:
            raise ValueError(
                "duration_seconds debe ser mayor que 0."
            )

        if max_steps <= 0:
            raise ValueError(
                "max_steps debe ser mayor que 0."
            )

        stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
        short_id = uuid.uuid4().hex[:8]

        return cls(
            session_id=f"{stamp}-{short_id}",
            workspace=str(path),
            objective=objective,
            duration_seconds=float(duration_seconds),
            max_steps=int(max_steps),
        )

    def _effective_elapsed(
        self,
        now: datetime | None = None,
    ) -> float:
        elapsed = float(self.elapsed_seconds)

        if (
            self.status == "running"
            and self.run_started_at
        ):
            now = now or utc_now()
            run_started = parse_datetime(
                self.run_started_at
            )

            if run_started is not None:
                elapsed += max(
                    0.0,
                    (now - run_started).total_seconds(),
                )

        return elapsed

    def remaining_seconds(
        self,
        now: datetime | None = None,
    ) -> float:
        return max(
            0.0,
            self.duration_seconds
            - self._effective_elapsed(now),
        )

    def can_continue(
        self,
        now: datetime | None = None,
    ) -> bool:
        return (
            self.status == "running"
            and self.remaining_seconds(now) > 0
            and self.step < self.max_steps
        )

    def start(
        self,
        now: datetime | None = None,
    ) -> None:
        if self.status not in {
            "pending",
            "paused",
        }:
            raise RuntimeError(
                f"No se puede iniciar una sesión "
                f"con estado '{self.status}'."
            )

        now = now or utc_now()

        if self.started_at is None:
            self.started_at = now.isoformat()

        self.run_started_at = now.isoformat()
        self.status = "running"
        self.stopped_at = None

    def _freeze_elapsed(
        self,
        now: datetime | None = None,
    ) -> None:
        if not self.run_started_at:
            return

        now = now or utc_now()

        run_started = parse_datetime(
            self.run_started_at
        )

        if run_started is not None:
            self.elapsed_seconds += max(
                0.0,
                (now - run_started).total_seconds(),
            )

        self.run_started_at = None

    def pause(
        self,
        now: datetime | None = None,
    ) -> None:
        if self.status != "running":
            return

        self._freeze_elapsed(now)
        self.status = "paused"

    def stop(
        self,
        status: str = "stopped",
        now: datetime | None = None,
    ) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Estado inválido: {status}"
            )

        now = now or utc_now()

        if self.status == "running":
            self._freeze_elapsed(now)

        self.status = status
        self.stopped_at = now.isoformat()

    def complete(
        self,
        now: datetime | None = None,
    ) -> None:
        self.stop(
            status="completed",
            now=now,
        )

    def record_step(
        self,
        task: str,
        *,
        completed: bool = True,
        note: str | None = None,
        now: datetime | None = None,
    ) -> None:
        self.enforce_limits(now)

        if not self.can_continue(now):
            raise RuntimeError(
                "La sesión ya no puede continuar."
            )

        task = task.strip()

        self.step += 1
        self.current_task = task

        if completed and task:
            self.completed_tasks.append(task)

        if note:
            self.notes.append(note.strip())

        self.enforce_limits(now)

    def enforce_limits(
        self,
        now: datetime | None = None,
    ) -> None:
        if self.status != "running":
            return

        if self.remaining_seconds(now) <= 0:
            self.stop(
                status="expired",
                now=now,
            )
            return

        if self.step >= self.max_steps:
            self.stop(
                status="step_limit",
                now=now,
            )

    def checkpoint(
        self,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or utc_now()

        if (
            self.status == "running"
            and self.run_started_at
        ):
            self._freeze_elapsed(now)
            self.run_started_at = now.isoformat()

        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "ProjectSession":
        session = cls(**data)

        if session.status not in VALID_STATUSES:
            raise ValueError(
                f"Estado inválido en checkpoint: "
                f"{session.status}"
            )

        return session
