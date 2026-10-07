from core.project_verifier import (
    ProjectVerifier,
)


def test_valid_python_passes(
    tmp_path,
):
    workspace = (
        tmp_path
        / "project"
    )

    workspace.mkdir()

    target = (
        workspace
        / "example.py"
    )

    target.write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    verifier = ProjectVerifier(
        workspace
    )

    result = verifier.verify(
        "example.py"
    )

    assert result.ok
    assert (
        "py_compile: PASS"
        in result.checks
    )


def test_invalid_python_fails(
    tmp_path,
):
    workspace = (
        tmp_path
        / "project"
    )

    workspace.mkdir()

    target = (
        workspace
        / "example.py"
    )

    target.write_text(
        "def broken(\n",
        encoding="utf-8",
    )

    verifier = ProjectVerifier(
        workspace
    )

    result = verifier.verify(
        "example.py"
    )

    assert not result.ok
    assert (
        "py_compile: FAIL"
        in result.checks
    )


def test_related_test_runs(
    tmp_path,
):
    workspace = (
        tmp_path
        / "project"
    )

    workspace.mkdir()

    tests = (
        workspace
        / "tests"
    )

    tests.mkdir()

    (
        workspace
        / "example.py"
    ).write_text(
        "VALUE = 2\n",
        encoding="utf-8",
    )

    (
        tests
        / "test_example.py"
    ).write_text(
        "from example import VALUE\n\n"
        "def test_value():\n"
        "    assert VALUE == 2\n",
        encoding="utf-8",
    )

    verifier = ProjectVerifier(
        workspace
    )

    result = verifier.verify(
        "example.py"
    )

    assert result.ok
    assert (
        "pytest: PASS"
        in result.checks
    )

    assert (
        result.test_target
        == "tests/test_example.py"
    )


def test_failing_related_test(
    tmp_path,
):
    workspace = (
        tmp_path
        / "project"
    )

    workspace.mkdir()

    tests = (
        workspace
        / "tests"
    )

    tests.mkdir()

    (
        workspace
        / "example.py"
    ).write_text(
        "VALUE = 2\n",
        encoding="utf-8",
    )

    (
        tests
        / "test_example.py"
    ).write_text(
        "from example import VALUE\n\n"
        "def test_value():\n"
        "    assert VALUE == 999\n",
        encoding="utf-8",
    )

    verifier = ProjectVerifier(
        workspace
    )

    result = verifier.verify(
        "example.py"
    )

    assert not result.ok
    assert (
        "pytest: FAIL"
        in result.checks
    )
