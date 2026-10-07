from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


VALID_TASK_STATUSES = {
    "pending",
    "in_progress",
    "completed",
    "blocked",
    "skipped",
}


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


@dataclass
class ProjectTask:
    task_id: str
    title: str
    description: str = ""

    status: str = "pending"

    attempts: int = 0
    last_result: str = ""
    error: str = ""

    created_at: str = field(
        default_factory=utc_now
    )
    updated_at: str = field(
        default_factory=utc_now
    )

    @classmethod
    def new(
        cls,
        title: str,
        description: str = "",
    ) -> "ProjectTask":

        title = title.strip()

        if not title:
            raise ValueError(
                "La tarea necesita un título."
            )

        return cls(
            task_id=uuid.uuid4().hex[:8],
            title=title,
            description=description.strip(),
        )

    def set_status(
        self,
        status: str,
    ) -> None:

        if status not in VALID_TASK_STATUSES:
            raise ValueError(
                f"Estado de tarea inválido: {status}"
            )

        self.status = status
        self.updated_at = utc_now()

    def start(self) -> None:

        if self.status not in {
            "pending",
            "blocked",
        }:
            raise RuntimeError(
                "La tarea no puede iniciarse "
                f"desde '{self.status}'."
            )

        self.status = "in_progress"
        self.attempts += 1
        self.error = ""
        self.updated_at = utc_now()

    def complete(
        self,
        result: str = "",
    ) -> None:

        self.status = "completed"
        self.last_result = result.strip()
        self.error = ""
        self.updated_at = utc_now()

    def block(
        self,
        error: str,
    ) -> None:

        self.status = "blocked"
        self.error = error.strip()
        self.updated_at = utc_now()

    def skip(
        self,
        reason: str = "",
    ) -> None:

        self.status = "skipped"
        self.last_result = reason.strip()
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "ProjectTask":

        task = cls(**data)

        if task.status not in VALID_TASK_STATUSES:
            raise ValueError(
                "Estado inválido en tarea: "
                f"{task.status}"
            )

        return task


@dataclass
class ProjectPlan:
    objective: str

    tasks: list[ProjectTask] = field(
        default_factory=list
    )

    current_task_id: str | None = None

    created_at: str = field(
        default_factory=utc_now
    )

    updated_at: str = field(
        default_factory=utc_now
    )

    @classmethod
    def new(
        cls,
        objective: str,
        tasks: list[
            ProjectTask
        ] | None = None,
    ) -> "ProjectPlan":

        objective = objective.strip()

        if not objective:
            raise ValueError(
                "El plan necesita un objetivo."
            )

        return cls(
            objective=objective,
            tasks=tasks or [],
        )

    def add_task(
        self,
        title: str,
        description: str = "",
    ) -> ProjectTask:

        task = ProjectTask.new(
            title,
            description,
        )

        self.tasks.append(task)
        self.updated_at = utc_now()

        return task

    def get_task(
        self,
        task_id: str,
    ) -> ProjectTask:

        for task in self.tasks:
            if task.task_id == task_id:
                return task

        raise KeyError(
            f"Tarea inexistente: {task_id}"
        )

    def current_task(
        self,
    ) -> ProjectTask | None:

        if not self.current_task_id:
            return None

        try:
            return self.get_task(
                self.current_task_id
            )
        except KeyError:
            return None

    def next_task(
        self,
    ) -> ProjectTask | None:

        current = self.current_task()

        if (
            current is not None
            and current.status == "in_progress"
        ):
            return current

        for task in self.tasks:

            if task.status == "pending":
                return task

        return None

    def start_next(
        self,
    ) -> ProjectTask | None:

        task = self.next_task()

        if task is None:
            self.current_task_id = None
            return None

        if task.status != "in_progress":
            task.start()

        self.current_task_id = (
            task.task_id
        )

        self.updated_at = utc_now()

        return task

    def complete_current(
        self,
        result: str = "",
    ) -> ProjectTask:

        task = self.current_task()

        if task is None:
            raise RuntimeError(
                "No existe tarea actual."
            )

        task.complete(result)

        self.current_task_id = None
        self.updated_at = utc_now()

        return task

    def block_current(
        self,
        error: str,
    ) -> ProjectTask:

        task = self.current_task()

        if task is None:
            raise RuntimeError(
                "No existe tarea actual."
            )

        task.block(error)

        self.current_task_id = None
        self.updated_at = utc_now()

        return task

    def progress(
        self,
    ) -> dict[str, int]:

        total = len(self.tasks)

        completed = sum(
            task.status == "completed"
            for task in self.tasks
        )

        blocked = sum(
            task.status == "blocked"
            for task in self.tasks
        )

        pending = sum(
            task.status == "pending"
            for task in self.tasks
        )

        in_progress = sum(
            task.status == "in_progress"
            for task in self.tasks
        )

        skipped = sum(
            task.status == "skipped"
            for task in self.tasks
        )

        return {
            "total": total,
            "completed": completed,
            "blocked": blocked,
            "pending": pending,
            "in_progress": in_progress,
            "skipped": skipped,
        }

    def is_complete(self) -> bool:

        if not self.tasks:
            return False

        return all(
            task.status in {
                "completed",
                "skipped",
            }
            for task in self.tasks
        )

    def summary(self) -> str:

        symbols = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
            "blocked": "[!]",
            "skipped": "[-]",
        }

        lines = []

        for index, task in enumerate(
            self.tasks,
            start=1,
        ):
            symbol = symbols[
                task.status
            ]

            lines.append(
                f"{symbol} {index}. "
                f"{task.title}"
            )

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:

        return {
            "objective": self.objective,
            "tasks": [
                task.to_dict()
                for task in self.tasks
            ],
            "current_task_id": (
                self.current_task_id
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "ProjectPlan":

        return cls(
            objective=data["objective"],
            tasks=[
                ProjectTask.from_dict(
                    item
                )
                for item in data.get(
                    "tasks",
                    [],
                )
            ],
            current_task_id=data.get(
                "current_task_id"
            ),
            created_at=data.get(
                "created_at",
                utc_now(),
            ),
            updated_at=data.get(
                "updated_at",
                utc_now(),
            ),
        )
