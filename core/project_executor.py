from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


MAX_READ_CHARS = 12_000
MAX_SEARCH_RESULTS = 80
MAX_COMMAND_OUTPUT = 12_000


SAFE_COMMANDS = {
    "pwd",
    "ls",
    "find",
    "grep",
    "rg",
    "git",
    "python",
    "python3",
    "pytest",
}


BLOCKED_GIT_SUBCOMMANDS = {
    "add",
    "commit",
    "push",
    "pull",
    "fetch",
    "merge",
    "rebase",
    "reset",
    "checkout",
    "switch",
    "clean",
    "restore",
    "cherry-pick",
    "revert",
    "tag",
}


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    action: str
    output: str
    returncode: int = 0


class ProjectExecutor:
    """
    Executor seguro para Project Mode.

    Fase 2B:
    - solo lectura
    - comandos diagnósticos
    - tests
    - sandbox dentro del workspace
    """

    def __init__(
        self,
        workspace: str | Path,
    ) -> None:
        self.workspace = (
            Path(workspace)
            .expanduser()
            .resolve()
        )

        if not self.workspace.is_dir():
            raise NotADirectoryError(
                f"Workspace inválido: {self.workspace}"
            )

    def _safe_path(
        self,
        value: str | Path,
    ) -> Path:
        path = Path(value).expanduser()

        if not path.is_absolute():
            path = self.workspace / path

        path = path.resolve()

        try:
            path.relative_to(self.workspace)
        except ValueError:
            raise PermissionError(
                "Ruta fuera del workspace."
            )

        return path

    def read_file(
        self,
        target: str,
    ) -> ExecutionResult:
        path = self._safe_path(target)

        if not path.exists():
            return ExecutionResult(
                ok=False,
                action="read_file",
                output=f"No existe: {target}",
                returncode=1,
            )

        if not path.is_file():
            return ExecutionResult(
                ok=False,
                action="read_file",
                output=f"No es un archivo: {target}",
                returncode=1,
            )

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except Exception as exc:
            return ExecutionResult(
                ok=False,
                action="read_file",
                output=f"Error leyendo archivo: {exc}",
                returncode=1,
            )

        truncated = len(text) > MAX_READ_CHARS

        text = text[:MAX_READ_CHARS]

        relative = path.relative_to(
            self.workspace
        )

        output = (
            f"FILE: {relative}\n"
            f"{'-' * 60}\n"
            f"{text}"
        )

        if truncated:
            output += (
                "\n\n[TRUNCATED: archivo demasiado grande]"
            )

        return ExecutionResult(
            ok=True,
            action="read_file",
            output=output,
        )

    def search_files(
        self,
        query: str,
    ) -> ExecutionResult:
        query = query.strip()

        if not query:
            return ExecutionResult(
                ok=False,
                action="search_files",
                output="Consulta vacía.",
                returncode=1,
            )

        command = None

        if self._has_command("rg"):
            command = [
                "rg",
                "--line-number",
                "--ignore-case",
                "--hidden",
                "--glob",
                "!.git/**",
                "--glob",
                "!.venv/**",
                "--glob",
                "!__pycache__/**",
                "--",
                query,
                ".",
            ]
        else:
            command = [
                "grep",
                "-R",
                "-n",
                "-i",
                "--exclude-dir=.git",
                "--exclude-dir=.venv",
                "--exclude-dir=__pycache__",
                "--",
                query,
                ".",
            ]

        result = self._run(
            command,
            timeout=20,
        )

        lines = result.output.splitlines()

        if len(lines) > MAX_SEARCH_RESULTS:
            result = ExecutionResult(
                ok=result.ok,
                action="search_files",
                returncode=result.returncode,
                output=(
                    "\n".join(
                        lines[:MAX_SEARCH_RESULTS]
                    )
                    + "\n[TRUNCATED]"
                ),
            )

        if (
            result.returncode == 1
            and not result.output.strip()
        ):
            return ExecutionResult(
                ok=True,
                action="search_files",
                output="Sin coincidencias.",
                returncode=0,
            )

        return ExecutionResult(
            ok=result.ok,
            action="search_files",
            output=result.output,
            returncode=result.returncode,
        )

    def run_tests(
        self,
        target: str = "",
    ) -> ExecutionResult:
        command = [
            str(
                self.workspace
                / ".venv"
                / "bin"
                / "python"
            ),
            "-m",
            "pytest",
        ]

        local_python = Path(command[0])

        if not local_python.exists():
            command = [
                os.environ.get(
                    "PYTHON",
                    "python3",
                ),
                "-m",
                "pytest",
            ]

        if target:
            target_path = self._safe_path(
                target
            )

            command.append(
                str(target_path)
            )

        command.append("-q")

        result = self._run(
            command,
            timeout=180,
        )

        return ExecutionResult(
            ok=result.returncode == 0,
            action="run_tests",
            output=result.output,
            returncode=result.returncode,
        )

    def run_safe_command(
        self,
        raw_command: str,
    ) -> ExecutionResult:
        try:
            parts = shlex.split(
                raw_command
            )
        except ValueError as exc:
            return ExecutionResult(
                ok=False,
                action="run_safe_command",
                output=f"Comando inválido: {exc}",
                returncode=1,
            )

        if not parts:
            return ExecutionResult(
                ok=False,
                action="run_safe_command",
                output="Comando vacío.",
                returncode=1,
            )

        executable = Path(
            parts[0]
        ).name

        if executable not in SAFE_COMMANDS:
            return ExecutionResult(
                ok=False,
                action="run_safe_command",
                output=(
                    f"Comando no permitido: "
                    f"{executable}"
                ),
                returncode=126,
            )

        if executable == "git":
            if len(parts) < 2:
                return ExecutionResult(
                    ok=False,
                    action="run_safe_command",
                    output="Falta subcomando Git.",
                    returncode=126,
                )

            subcommand = parts[1]

            if subcommand in BLOCKED_GIT_SUBCOMMANDS:
                return ExecutionResult(
                    ok=False,
                    action="run_safe_command",
                    output=(
                        "Subcomando Git bloqueado "
                        f"en modo lectura: {subcommand}"
                    ),
                    returncode=126,
                )

        dangerous_tokens = {
            ">",
            ">>",
            "|",
            "&&",
            "||",
            ";",
            "$(",
            "`",
        }

        if any(
            token in raw_command
            for token in dangerous_tokens
        ):
            return ExecutionResult(
                ok=False,
                action="run_safe_command",
                output=(
                    "Shell operators bloqueados "
                    "en Project Mode."
                ),
                returncode=126,
            )

        return self._run(
            parts,
            timeout=60,
            action="run_safe_command",
        )

    def _run(
        self,
        command: list[str],
        *,
        timeout: int,
        action: str = "command",
    ) -> ExecutionResult:
        try:
            process = subprocess.run(
                command,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env={
                    **os.environ,
                    "PYTHONUNBUFFERED": "1",
                },
            )

            output = (
                process.stdout
                + process.stderr
            ).strip()

            if not output:
                output = "(sin salida)"

            if len(output) > MAX_COMMAND_OUTPUT:
                output = (
                    output[:MAX_COMMAND_OUTPUT]
                    + "\n[TRUNCATED]"
                )

            return ExecutionResult(
                ok=process.returncode == 0,
                action=action,
                output=output,
                returncode=process.returncode,
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                ok=False,
                action=action,
                output=(
                    f"Timeout después de "
                    f"{timeout}s."
                ),
                returncode=124,
            )

        except Exception as exc:
            return ExecutionResult(
                ok=False,
                action=action,
                output=f"Error ejecutando comando: {exc}",
                returncode=1,
            )

    @staticmethod
    def _has_command(
        command: str,
    ) -> bool:
        from shutil import which

        return which(command) is not None
