from __future__ import annotations

import subprocess
import sys

from dataclasses import dataclass, field
from pathlib import Path


MAX_OUTPUT = 8_000


@dataclass
class VerificationResult:
    ok: bool
    checks: list[str] = field(
        default_factory=list
    )
    output: str = ""
    test_target: str = ""


class ProjectVerifier:
    """
    Verificador ligero posterior a edición.

    Estrategia:
    1. valida existencia
    2. py_compile para .py
    3. ejecuta test relacionado si existe
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
                f"Workspace inválido: "
                f"{self.workspace}"
            )

    def _safe_path(
        self,
        target: str | Path,
    ) -> Path:

        path = Path(target)

        if not path.is_absolute():
            path = (
                self.workspace
                / path
            )

        path = path.resolve()

        try:
            path.relative_to(
                self.workspace
            )
        except ValueError:
            raise PermissionError(
                "Ruta fuera del workspace."
            )

        return path

    def verify(
        self,
        target: str | Path,
    ) -> VerificationResult:

        path = self._safe_path(
            target
        )

        if not path.exists():
            return VerificationResult(
                ok=False,
                checks=[
                    "exists: FAIL"
                ],
                output=(
                    f"El archivo no existe: "
                    f"{path}"
                ),
            )

        checks = [
            "exists: PASS"
        ]

        outputs: list[str] = []

        # --------------------------------------------------
        # Python syntax
        # --------------------------------------------------

        if path.suffix == ".py":

            compile_result = self._run(
                [
                    sys.executable,
                    "-m",
                    "py_compile",
                    str(path),
                ],
                timeout=30,
            )

            if compile_result.returncode != 0:
                checks.append(
                    "py_compile: FAIL"
                )

                outputs.append(
                    compile_result.output
                )

                return VerificationResult(
                    ok=False,
                    checks=checks,
                    output=self._join_output(
                        outputs
                    ),
                )

            checks.append(
                "py_compile: PASS"
            )

        # --------------------------------------------------
        # Related pytest
        # --------------------------------------------------

        test_target = (
            self._related_test(
                path
            )
        )

        if test_target is not None:

            relative_test = str(
                test_target.relative_to(
                    self.workspace
                )
            )

            test_result = self._run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    relative_test,
                    "-q",
                ],
                timeout=180,
            )

            outputs.append(
                test_result.output
            )

            if test_result.returncode != 0:
                checks.append(
                    "pytest: FAIL"
                )

                return VerificationResult(
                    ok=False,
                    checks=checks,
                    output=self._join_output(
                        outputs
                    ),
                    test_target=relative_test,
                )

            checks.append(
                "pytest: PASS"
            )

            return VerificationResult(
                ok=True,
                checks=checks,
                output=self._join_output(
                    outputs
                ),
                test_target=relative_test,
            )

        checks.append(
            "pytest: SKIP"
        )

        return VerificationResult(
            ok=True,
            checks=checks,
            output=self._join_output(
                outputs
            ),
        )

    def _related_test(
        self,
        path: Path,
    ) -> Path | None:

        relative = path.relative_to(
            self.workspace
        )

        # Si Yuna editó directamente un test,
        # verificamos ese mismo archivo.
        if (
            relative.parts
            and relative.parts[0] == "tests"
            and path.name.startswith("test_")
            and path.suffix == ".py"
        ):
            return path

        if path.suffix != ".py":
            return None

        # core/foo.py -> tests/test_foo.py
        candidate = (
            self.workspace
            / "tests"
            / f"test_{path.stem}.py"
        )

        if candidate.is_file():
            return candidate

        return None

    def _run(
        self,
        command: list[str],
        *,
        timeout: int,
    ):
        try:
            process = subprocess.run(
                command,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            output = (
                process.stdout
                + process.stderr
            ).strip()

            return _CommandResult(
                returncode=(
                    process.returncode
                ),
                output=output,
            )

        except subprocess.TimeoutExpired:
            return _CommandResult(
                returncode=124,
                output=(
                    f"Timeout después "
                    f"de {timeout}s."
                ),
            )

        except Exception as exc:
            return _CommandResult(
                returncode=1,
                output=(
                    f"Error de verificación: "
                    f"{exc}"
                ),
            )

    @staticmethod
    def _join_output(
        outputs: list[str],
    ) -> str:

        text = "\n".join(
            item
            for item in outputs
            if item
        )

        if len(text) > MAX_OUTPUT:
            return (
                text[:MAX_OUTPUT]
                + "\n[TRUNCATED]"
            )

        return text


@dataclass
class _CommandResult:
    returncode: int
    output: str
