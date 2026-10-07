from pathlib import Path

from core.project_executor import (
    ProjectExecutor,
)


def make_workspace(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()

    (workspace / "hello.py").write_text(
        "def hello():\n"
        "    return 'hello'\n",
        encoding="utf-8",
    )

    tests = workspace / "tests"
    tests.mkdir()

    (tests / "test_hello.py").write_text(
        "def test_ok():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    return workspace


def test_read_file(tmp_path):
    workspace = make_workspace(
        tmp_path
    )

    executor = ProjectExecutor(
        workspace
    )

    result = executor.read_file(
        "hello.py"
    )

    assert result.ok
    assert "def hello" in result.output


def test_read_outside_workspace_blocked(
    tmp_path,
):
    workspace = make_workspace(
        tmp_path
    )

    outside = tmp_path / "secret.txt"

    outside.write_text(
        "secret",
        encoding="utf-8",
    )

    executor = ProjectExecutor(
        workspace
    )

    try:
        executor.read_file(
            "../secret.txt"
        )
        assert False
    except PermissionError:
        pass


def test_search_files(tmp_path):
    workspace = make_workspace(
        tmp_path
    )

    executor = ProjectExecutor(
        workspace
    )

    result = executor.search_files(
        "hello"
    )

    assert result.ok
    assert "hello.py" in result.output


def test_safe_git_status(tmp_path):
    workspace = make_workspace(
        tmp_path
    )

    executor = ProjectExecutor(
        workspace
    )

    result = executor.run_safe_command(
        "git status --short"
    )

    # Puede devolver error porque el tmp
    # no necesariamente es repo Git,
    # pero el comando sí debe ser permitido.
    assert result.returncode != 126


def test_git_push_blocked(tmp_path):
    workspace = make_workspace(
        tmp_path
    )

    executor = ProjectExecutor(
        workspace
    )

    result = executor.run_safe_command(
        "git push"
    )

    assert not result.ok
    assert result.returncode == 126


def test_shell_operator_blocked(tmp_path):
    workspace = make_workspace(
        tmp_path
    )

    executor = ProjectExecutor(
        workspace
    )

    result = executor.run_safe_command(
        "ls && rm something"
    )

    assert not result.ok
    assert result.returncode == 126


def test_unknown_command_blocked(tmp_path):
    workspace = make_workspace(
        tmp_path
    )

    executor = ProjectExecutor(
        workspace
    )

    result = executor.run_safe_command(
        "rm -rf ."
    )

    assert not result.ok
    assert result.returncode == 126
