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
from core.project_executor import (
    ProjectExecutor,
)
from core.project_editor import (
    SafeEditor,
)
from core.project_verifier import (
    ProjectVerifier,
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

        # Evita ejecutar repetidamente la misma acción
        # sobre el mismo objetivo durante una subtarea.
        self._executed_signatures: set[
            tuple[str, str]
        ] = set()

        # Cuando cambia la subtarea del plan,
        # reiniciamos el contexto operacional.
        self._active_plan_task_id: str | None = None

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

    def _decision_signature(
        self,
        decision: ProjectDecision,
    ) -> tuple[str, str]:
        return (
            decision.action.strip().lower(),
            decision.target.strip().lower(),
        )

    def _current_plan_task(self):
        """
        Devuelve (plan, task).

        Si existe un plan pero todavía no tiene una tarea
        activa, inicia automáticamente la siguiente.
        """
        plan = self.runner.get_plan()

        if plan is None:
            return None, None

        task = plan.current_task()

        if task is None:
            task = plan.start_next()

            if task is not None:
                self.runner.save_plan(plan)

        if task is not None:
            if (
                self._active_plan_task_id
                != task.task_id
            ):
                # Nueva subtarea = contexto fresco.
                # Reduce tokens y permite reutilizar acciones
                # válidas como run_tests en fases diferentes.
                self._active_plan_task_id = task.task_id
                self.history.clear()
                self._executed_signatures.clear()

        return plan, task

    def _normalize_task_text(
        self,
        value: str,
    ) -> str:
        import unicodedata

        value = unicodedata.normalize(
            "NFKD",
            value.lower(),
        )

        return "".join(
            char
            for char in value
            if not unicodedata.combining(char)
        )

    def _auto_complete_plan_task(
        self,
        decision: ProjectDecision,
        result: str,
    ) -> bool:
        """
        Cierra automáticamente subtareas cuyo resultado
        ya demuestra de forma suficientemente clara que
        fueron realizadas.

        Python toma esta decisión para evitar otra llamada
        al LLM únicamente para obtener `finish`.
        """

        plan = self.runner.get_plan()

        if plan is None:
            return False

        task = plan.current_task()

        if task is None:
            return False

        task_text = self._normalize_task_text(
            f"{task.title} {task.description}"
        )

        action = decision.action
        result_upper = result.upper()

        satisfied = False

        # -------------------------------------------------
        # Inspección / descubrimiento
        # -------------------------------------------------

        inspection_words = (
            "inspeccionar",
            "identificar",
            "localizar",
            "listar",
            "examinar estructura",
            "revisar estructura",
        )

        if any(
            word in task_text
            for word in inspection_words
        ):
            satisfied = action in {
                "inspect_workspace",
                "list_tests",
                "search_files",
                "read_file",
                "git_status",
            }

        # -------------------------------------------------
        # Modificación
        # -------------------------------------------------

        edit_words = (
            "editar",
            "modificar",
            "cambiar",
            "crear",
            "aplicar",
            "corregir",
            "actualizar",
        )

        if any(
            word in task_text
            for word in edit_words
        ):
            if action in {
                "edit_file",
                "create_file",
            }:
                satisfied = (
                    "STATUS=COMMITTED"
                    in result_upper
                    or "NO_CHANGE"
                    in result_upper
                )

        # -------------------------------------------------
        # Tests / verificación
        # -------------------------------------------------

        verify_words = (
            "verificar",
            "validar",
            "probar",
            "test",
            "prueba",
            "comprobar",
        )

        if any(
            word in task_text
            for word in verify_words
        ):
            if action == "run_tests":
                satisfied = (
                    "RETURNCODE=0"
                    in result_upper
                )

            elif action in {
                "edit_file",
                "create_file",
            }:
                satisfied = (
                    "STATUS=COMMITTED"
                    in result_upper
                    and "FAIL"
                    not in result_upper
                    and "VERIFY="
                    in result_upper
                )

        # -------------------------------------------------
        # Ejecución de comandos/scripts
        # -------------------------------------------------

        if (
            "ejecutar script" in task_text
            or "ejecutar comando" in task_text
        ):
            if action == "run_safe_command":
                satisfied = (
                    "RETURNCODE=0"
                    in result_upper
                )

        if not satisfied:
            return False

        plan.complete_current(
            result=(
                f"Auto-completada tras "
                f"{decision.action}: "
                f"{decision.reason}"
            )
        )

        self.runner.save_plan(
            plan
        )

        session = self.runner.require_session()

        session.notes.append(
            "PLAN_TASK_AUTO_COMPLETED: "
            f"{task.title} | "
            f"{decision.action}"
        )

        self.runner.store.save(
            session
        )

        # La siguiente iteración arrancará con contexto
        # limpio para la siguiente subtarea.
        self._active_plan_task_id = None

        return True

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

        plan, plan_task = (
            self._current_plan_task()
        )

        effective_objective = (
            session.objective
        )

        if plan_task is not None:
            effective_objective = (
                f"OBJETIVO GENERAL:\n"
                f"{session.objective}\n\n"
                f"SUBTAREA ACTUAL:\n"
                f"{plan_task.title}\n"
                f"{plan_task.description}\n\n"
                "Trabaja únicamente en esta subtarea. "
                "Usa finish cuando esta subtarea esté "
                "realmente completada."
            )

        # El modelo tiene varias oportunidades para
        # replantear una decisión duplicada.
        for attempt in range(3):

            decision = self.planner.plan(
                objective=effective_objective,
                step=session.step,
                max_steps=session.max_steps,
                remaining_seconds=(
                    session.remaining_seconds()
                ),
                snapshot=snapshot,
                recent_history=self.history,
            )

            if decision.action == "finish":
                return decision

            signature = self._decision_signature(
                decision
            )

            if signature not in self._executed_signatures:
                return decision

            self.history.append(
                "REJECTED_DUPLICATE\n"
                f"ACTION={decision.action}\n"
                f"TARGET={decision.target or '-'}\n"
                "RESULT=Esta acción con este mismo target "
                "ya fue ejecutada. Debes elegir una acción "
                "o target diferente."
            )

        # Si el LLM insiste tres veces, Python corta
        # el bucle en lugar de quemar pasos/tokens.
        return ProjectDecision(
            action="finish",
            reason=(
                "Se detectaron decisiones duplicadas "
                "persistentes sin progreso."
            ),
            target="",
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

        elif decision.action == "read_file":

            executor = ProjectExecutor(
                workspace
            )

            execution = executor.read_file(
                decision.target
            )

            result = execution.output

        elif decision.action == "search_files":

            executor = ProjectExecutor(
                workspace
            )

            execution = executor.search_files(
                decision.target
            )

            result = execution.output

        elif decision.action == "run_tests":

            executor = ProjectExecutor(
                workspace
            )

            execution = executor.run_tests(
                decision.target
            )

            result = (
                f"returncode={execution.returncode}\n"
                f"{execution.output}"
            )

        elif decision.action == "run_safe_command":

            executor = ProjectExecutor(
                workspace
            )

            execution = executor.run_safe_command(
                decision.target
            )

            result = (
                f"returncode={execution.returncode}\n"
                f"{execution.output}"
            )

        elif decision.action in {
            "edit_file",
            "create_file",
        }:

            if "|||" not in decision.target:
                raise ValueError(
                    "Formato de edición inválido. "
                    "Usa: RUTA ||| CONTENIDO"
                )

            raw_path, raw_content = (
                decision.target.split(
                    "|||",
                    1,
                )
            )

            target_path = raw_path.strip()
            new_content = raw_content.lstrip()

            editor = SafeEditor(
                workspace
            )

            if decision.action == "edit_file":
                full_path = (
                    workspace
                    / target_path
                )

                if not full_path.exists():
                    raise FileNotFoundError(
                        "edit_file requiere "
                        "un archivo existente."
                    )

            if decision.action == "create_file":
                full_path = (
                    workspace
                    / target_path
                )

                if full_path.exists():
                    raise FileExistsError(
                        "create_file requiere "
                        "un archivo nuevo."
                    )

            # -------------------------------------------------
            # NO-OP EDIT
            # -------------------------------------------------
            # Si el archivo ya contiene exactamente lo que el
            # modelo intenta escribir, no es un error fatal.
            # Informamos al planner y continuamos la sesión.
            # -------------------------------------------------
            existing_path = (
                workspace
                / target_path
            ).resolve()

            no_change = False

            if existing_path.exists():
                try:
                    existing_text = (
                        existing_path.read_text(
                            encoding="utf-8"
                        )
                    )

                    no_change = (
                        existing_text
                        == new_content
                    )

                except Exception:
                    no_change = False

            if no_change:
                result = (
                    "NO_CHANGE\n"
                    f"FILE={target_path}\n"
                    "El archivo ya contiene exactamente "
                    "el contenido solicitado. "
                    "No se realizó ninguna modificación."
                )

                return result

            transaction = editor.apply_text(
                target_path,
                new_content,
            )

            verifier = ProjectVerifier(
                workspace
            )

            verification = verifier.verify(
                target_path
            )

            checks_text = ", ".join(
                verification.checks
            )

            if verification.ok:

                transaction = editor.commit(
                    transaction.transaction_id
                )

                result = (
                    "Cambio verificado y confirmado.\n"
                    f"TX={transaction.transaction_id}\n"
                    f"FILE={transaction.relative_target}\n"
                    f"STATUS={transaction.status}\n"
                    f"VERIFY={checks_text}\n"
                    f"TEST={verification.test_target or '-'}\n"
                    f"OLD_SHA={transaction.original_sha256}\n"
                    f"NEW_SHA={transaction.applied_sha256}"
                )

                if verification.output:
                    result += (
                        "\nVERIFY_OUTPUT:\n"
                        + verification.output[:3000]
                    )

            else:

                transaction = editor.rollback(
                    transaction.transaction_id
                )

                result = (
                    "Cambio rechazado y revertido.\n"
                    f"TX={transaction.transaction_id}\n"
                    f"FILE={transaction.relative_target}\n"
                    f"STATUS={transaction.status}\n"
                    f"VERIFY={checks_text}\n"
                    f"TEST={verification.test_target or '-'}"
                )

                if verification.output:
                    result += (
                        "\nVERIFY_OUTPUT:\n"
                        + verification.output[:3000]
                    )

        elif decision.action in {
            "edit_file",
            "create_file",
        }:

            if "|||" not in decision.target:
                raise ValueError(
                    "Formato de edición inválido. "
                    "Usa: RUTA ||| CONTENIDO"
                )

            raw_path, raw_content = (
                decision.target.split(
                    "|||",
                    1,
                )
            )

            target_path = raw_path.strip()
            new_content = raw_content.lstrip()

            editor = SafeEditor(
                workspace
            )

            if decision.action == "edit_file":
                full_path = (
                    workspace
                    / target_path
                )

                if not full_path.exists():
                    raise FileNotFoundError(
                        "edit_file requiere "
                        "un archivo existente."
                    )

            if decision.action == "create_file":
                full_path = (
                    workspace
                    / target_path
                )

                if full_path.exists():
                    raise FileExistsError(
                        "create_file requiere "
                        "un archivo nuevo."
                    )

            transaction = editor.apply_text(
                target_path,
                new_content,
            )

            result = (
                "Cambio aplicado en transacción.\n"
                f"TX={transaction.transaction_id}\n"
                f"FILE={transaction.relative_target}\n"
                f"STATUS={transaction.status}\n"
                f"OLD_SHA={transaction.original_sha256}\n"
                f"NEW_SHA={transaction.applied_sha256}"
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

        if decision.action != "finish":
            self._executed_signatures.add(
                self._decision_signature(
                    decision
                )
            )

        history_entry = (
            f"ACTION={decision.action}\n"
            f"REASON={decision.reason}\n"
            f"TARGET={decision.target or '-'}\n"
            f"RESULT={result[:1500]}"
        )

        self.history.append(
            history_entry
        )

        if decision.action == "finish":

            plan, plan_task = (
                self._current_plan_task()
            )

            # -------------------------------------------------
            # PLAN MODE
            # finish completa la SUBTAREA actual.
            # -------------------------------------------------
            if (
                plan is not None
                and plan_task is not None
            ):
                session.step += 1

                session.current_task = (
                    plan_task.title
                )

                session.completed_tasks.append(
                    plan_task.title
                )

                session.notes.append(
                    f"PLAN_TASK_COMPLETED: "
                    f"{plan_task.title} | "
                    f"{decision.reason}"
                )

                plan.complete_current(
                    result=decision.reason
                )

                self.runner.save_plan(plan)

                # Solo terminamos la sesión cuando
                # TODO el plan esté completado.
                if plan.is_complete():
                    session.complete()

                else:
                    session.enforce_limits()

                self.runner.store.save(
                    session
                )

                # La siguiente llamada arrancará
                # una nueva subtarea y limpiará contexto.
                self._active_plan_task_id = None

            # -------------------------------------------------
            # LEGACY MODE
            # Sin ProjectPlan, finish termina la sesión.
            # -------------------------------------------------
            else:
                session.step += 1
                session.current_task = (
                    decision.action
                )
                session.completed_tasks.append(
                    decision.action
                )
                session.notes.append(
                    f"{decision.reason} | "
                    f"{result[:500]}"
                )

                session.complete()

                self.runner.store.save(
                    session
                )

        else:
            self.runner.record_step(
                decision.action,
                completed=True,
                note=(
                    f"{decision.reason} | "
                    f"{result[:500]}"
                ),
            )

            self._auto_complete_plan_task(
                decision,
                result,
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
