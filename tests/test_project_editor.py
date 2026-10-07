import os

import pytest

from core.project_editor import (
    SafeEditor,
)


def make_editor(tmp_path):
    workspace = (
        tmp_path
        / "project"
    )

    workspace.mkdir()

    transactions = (
        tmp_path
        / "transactions"
    )

    editor = SafeEditor(
        workspace,
        transaction_dir=transactions,
    )

    return (
        workspace,
        editor,
    )


def test_edit_existing_and_rollback(
    tmp_path,
):
    workspace, editor = make_editor(
        tmp_path
    )

    target = (
        workspace
        / "example.py"
    )

    target.write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    tx = editor.apply_text(
        "example.py",
        "VALUE = 2\n",
    )

    assert tx.status == "applied"

    assert target.read_text(
        encoding="utf-8"
    ) == "VALUE = 2\n"

    editor.rollback(
        tx.transaction_id
    )

    assert target.read_text(
        encoding="utf-8"
    ) == "VALUE = 1\n"

    loaded = editor.load(
        tx.transaction_id
    )

    assert (
        loaded.status
        == "rolled_back"
    )


def test_create_and_rollback(
    tmp_path,
):
    workspace, editor = make_editor(
        tmp_path
    )

    tx = editor.apply_text(
        "new_file.py",
        "HELLO = True\n",
    )

    target = (
        workspace
        / "new_file.py"
    )

    assert target.exists()

    editor.rollback(
        tx.transaction_id
    )

    assert not target.exists()


def test_commit_existing_change(
    tmp_path,
):
    workspace, editor = make_editor(
        tmp_path
    )

    target = (
        workspace
        / "example.py"
    )

    target.write_text(
        "A = 1\n",
        encoding="utf-8",
    )

    tx = editor.apply_text(
        "example.py",
        "A = 2\n",
    )

    committed = editor.commit(
        tx.transaction_id
    )

    assert (
        committed.status
        == "committed"
    )

    assert target.read_text(
        encoding="utf-8"
    ) == "A = 2\n"


def test_outside_workspace_blocked(
    tmp_path,
):
    workspace, editor = make_editor(
        tmp_path
    )

    outside = (
        tmp_path
        / "secret.txt"
    )

    outside.write_text(
        "SECRET",
        encoding="utf-8",
    )

    with pytest.raises(
        PermissionError
    ):
        editor.apply_text(
            "../secret.txt",
            "CHANGED",
        )


def test_git_directory_blocked(
    tmp_path,
):
    workspace, editor = make_editor(
        tmp_path
    )

    git_dir = (
        workspace
        / ".git"
    )

    git_dir.mkdir()

    config = (
        git_dir
        / "config"
    )

    config.write_text(
        "ORIGINAL",
        encoding="utf-8",
    )

    with pytest.raises(
        PermissionError
    ):
        editor.apply_text(
            ".git/config",
            "CHANGED",
        )


def test_sensitive_file_blocked(
    tmp_path,
):
    workspace, editor = make_editor(
        tmp_path
    )

    env_file = (
        workspace
        / ".env"
    )

    env_file.write_text(
        "SECRET=123\n",
        encoding="utf-8",
    )

    with pytest.raises(
        PermissionError
    ):
        editor.apply_text(
            ".env",
            "SECRET=999\n",
        )


def test_identical_change_rejected(
    tmp_path,
):
    workspace, editor = make_editor(
        tmp_path
    )

    target = (
        workspace
        / "example.py"
    )

    target.write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError
    ):
        editor.apply_text(
            "example.py",
            "VALUE = 1\n",
        )


def test_rollback_refuses_external_change(
    tmp_path,
):
    workspace, editor = make_editor(
        tmp_path
    )

    target = (
        workspace
        / "example.py"
    )

    target.write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    tx = editor.apply_text(
        "example.py",
        "VALUE = 2\n",
    )

    # Simula que otra persona/proceso
    # modificó el archivo después.
    target.write_text(
        "VALUE = 999\n",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError
    ):
        editor.rollback(
            tx.transaction_id
        )

    # SafeEditor NO debe borrar
    # el cambio externo.
    assert target.read_text(
        encoding="utf-8"
    ) == "VALUE = 999\n"


def test_commit_refuses_external_change(
    tmp_path,
):
    workspace, editor = make_editor(
        tmp_path
    )

    target = (
        workspace
        / "example.py"
    )

    target.write_text(
        "A = 1\n",
        encoding="utf-8",
    )

    tx = editor.apply_text(
        "example.py",
        "A = 2\n",
    )

    target.write_text(
        "A = 3\n",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError
    ):
        editor.commit(
            tx.transaction_id
        )


def test_file_permissions_preserved(
    tmp_path,
):
    workspace, editor = make_editor(
        tmp_path
    )

    target = (
        workspace
        / "script.sh"
    )

    target.write_text(
        "#!/bin/sh\n"
        "echo old\n",
        encoding="utf-8",
    )

    os.chmod(
        target,
        0o755,
    )

    tx = editor.apply_text(
        "script.sh",
        "#!/bin/sh\n"
        "echo new\n",
    )

    mode = (
        target.stat().st_mode
        & 0o777
    )

    assert mode == 0o755

    editor.rollback(
        tx.transaction_id
    )

    mode = (
        target.stat().st_mode
        & 0o777
    )

    assert mode == 0o755
