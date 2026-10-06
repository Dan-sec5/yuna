from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from core.project_planner import (
    ProjectDecision,
    ProjectPlanner,
)
from core.project_runner import (
    ProjectRunner,
)


class ProjectWorker:
    """
    Ejecuta ciclos de Project Mode.

    Fase 2A:
    - solo lectura
    - un planner
    - una acción por iteración
    - checkpoint después de cada paso
    """

    def __init__(
        self,
        runner: ProjectRunner,
        planner: ProjectPlanner | None = None,
    ) -> None:

        self.runner = runner

        self.planner = (
            planner
            if planner is not None
            else ProjectPlanner()
        )

        self.history: list[str] = []

    def workspace_snapshot(
        self,
    ) -> dict[str, Any]:

        session = self.runner.require_session()

        workspace = Path(
            session.workspace
        )

        files = []

        try:
            for item in sorted(
                workspace.iterdir(),
                key=lambda p: p.name.lower(),
            )[:80]:

                name = item.name

                if item.is_dir():
                    name += "/"

                files.append(name)

        except Exception as exc:
            files = [
                f"<error: {exc}>"
            ]

        tests = []

        test_dir = (
            workspace
            / "tests"
        )

        if test_dir.exists():
            try:
                tests = [
                    str(
                        path.relative_to(
                            workspace
                        )
                    )
                    for path in sorted(
                        test_dir.glob(
                            "test_*.py"
                        )
                    )[:50]
                ]
            except Exception:
                tests = []

        git_status = self._git_status(
            workspace
        )

        return {
            "workspace": str(workspace),
            "top_level": files,
            "tests": tests,
            "git_status": git_status[
                :4000
            ],
        }

    def _git_status(
        self,
        workspace: Path,
    ) -> str:

        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace),
                    "status",
                    "--short",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            output = (
                result.stdout.strip()
                or result.stderr.strip()
            )

            return (
                output
                if output
                else "clean"
            )

        except Exception as exc:
            return (
                f"git status unavailable: {exc}"
            )

    def plan_next(
        self,
    ) -> ProjectDecision:

        session = self.runner.require_session()

        session.enforce_limits()

        if not session.can_continue():
            raise RuntimeError(
                f"La sesión no puede continuar: "
                f"{session.status}"
            )

        snapshot = self.workspace_snapshot()

        return self.planner.plan(
            objective=session.objective,
            step=session.step,
            max_steps=session.max_steps,
            remaining_seconds=(
                session.remaining_seconds()
            ),
            snapshot=snapshot,
            recent_history=self.history,
        )

    def execute_decision(
        self,
        decision: ProjectDecision,
    ) -> str:

        session = self.runner.require_session()

        workspace = Path(
            session.workspace
        )

        if decision.action == "inspect_workspace":

            snapshot = self.workspace_snapshot()

            result = (
                "Workspace inspeccionado. "
                f"Elementos principales: "
                f"{len(snapshot['top_level'])}. "
                f"Tests detectados: "
                f"{len(snapshot['tests'])}."
            )

        elif decision.action == "git_status":

            result = self._git_status(
                workspace
            )

            if result == "clean":
                result = (
                    "Repositorio Git limpio."
                )
            else:
                result = (
                    "Estado Git:\n"
                    + result[:3000]
                )

        elif decision.action == "list_tests":

            snapshot = self.workspace_snapshot()

            tests = snapshot.get(
                "tests",
                [],
            )

            if tests:
                result = (
                    "Tests detectados:\n"
                    + "\n".join(
                        tests[:50]
                    )
                )
            else:
                result = (
                    "No se detectaron "
                    "tests/test_*.py."
                )

        elif decision.action == "finish":

            result = (
                "El planner considera terminada "
                "la inspección inicial."
            )

        else:
            raise RuntimeError(
                f"Acción no soportada: "
                f"{decision.action}"
            )

        return result

    def run_step(
        self,
    ) -> dict[str, str]:

        session = self.runner.require_session()

        session.enforce_limits()

        if not session.can_continue():
            return {
                "status": session.status,
                "action": "",
                "reason": "",
                "result": "",
            }

        decision = self.plan_next()

        result = self.execute_decision(
            decision
        )

        history_entry = (
            f"{decision.action}: "
            f"{decision.reason}"
        )

        self.history.append(
            history_entry
        )

        if decision.action == "finish":
            # Registrar el paso final sin permitir que el límite
            # de pasos gane antes que la finalización explícita.
            session.step += 1
            session.current_task = decision.action
            session.completed_tasks.append(decision.action)
            session.notes.append(
                f"{decision.reason} | "
                f"{result[:500]}"
            )

            session.complete()
            self.runner.store.save(session)

        else:
            self.runner.record_step(
                decision.action,
                completed=True,
                note=(
                    f"{decision.reason} | "
                    f"{result[:500]}"
                ),
            )

        return {
            "status": (
                self.runner
                .require_session()
                .status
            ),
            "action": decision.action,
            "reason": decision.reason,
            "result": result,
        }

    def run(
        self,
        *,
        max_iterations: int = 5,
        delay_seconds: float = 0.2,
    ) -> list[dict[str, str]]:

        if max_iterations <= 0:
            raise ValueError(
                "max_iterations debe ser > 0."
            )

        results: list[
            dict[str, str]
        ] = []

        for _ in range(
            max_iterations
        ):

            session = (
                self.runner
                .require_session()
            )

            session.enforce_limits()

            if not session.can_continue():
                break

            result = self.run_step()

            results.append(
                result
            )

            if (
                result["action"]
                == "finish"
            ):
                break

            if delay_seconds > 0:
                time.sleep(
                    delay_seconds
                )

        self.runner.checkpoint()

        return results
