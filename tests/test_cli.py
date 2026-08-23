"""Tests for the standalone command-line interface."""

import sys
from io import StringIO
from pathlib import Path

import pytest

from pytest_partition_check import PartitionError
from pytest_partition_check.cli import main


def _write_suite(*, root: Path, filename: str) -> None:
    """Write a small suite for CLI testing."""
    (root / filename).write_text(
        data="def test_one():\n    pass\n\ndef test_two():\n    pass\n",
        encoding="utf-8",
    )


def test_cli_success(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CLI returns normally for a valid partition."""
    filename = "test_cli_success_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=[
            "pytest-check-partition",
            "--rootdir",
            str(object=tmp_path),
            filename,
        ],
    )
    main()


def test_cli_failure(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CLI exits one and prints the shared report on failure."""
    filename = "test_cli_failure_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=[
            "pytest-check-partition",
            "--rootdir",
            str(object=tmp_path),
            f"{filename}::test_one",
        ],
    )
    with pytest.raises(expected_exception=SystemExit, match="1"):
        main()


def test_cli_patterns_file(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CLI reads a committed patterns file and accepts extra
    options.
    """
    filename = "test_cli_file_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    patterns = tmp_path / "patterns"
    patterns.write_text(data=f"# shard list\n\n{filename}\n", encoding="utf-8")
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=[
            "pytest-check-partition",
            "--rootdir",
            str(object=tmp_path),
            "--partition-patterns-path",
            str(object=patterns),
            "--disable-plugin",
            "retry",
            "--extra-arg=--disable-warnings",
        ],
    )
    main()


def test_cli_patterns_stdin(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CLI reads newline-delimited patterns from standard input."""
    filename = "test_cli_stdin_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=[
            "pytest-check-partition",
            "--rootdir",
            str(object=tmp_path),
            "--patterns-stdin",
        ],
    )
    monkeypatch.setattr(
        target=sys,
        name="stdin",
        value=StringIO(initial_value=f"# shard list\n\n{filename}\n"),
    )
    main()


def test_cli_duplicate_patterns(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CLI rejects duplicate patterns."""
    filename = "test_cli_duplicate_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=["pytest-check-partition", filename, filename],
    )
    with pytest.raises(expected_exception=SystemExit, match="1"):
        main()


def test_empty_partition_error_message() -> None:
    """Empty structured sections render explicit stable placeholders."""
    section_count = 3
    error = PartitionError(
        unmatched_patterns=frozenset(),
        overlapping={},
        uncollected=frozenset(),
    )
    assert str(object=error).count("  (none)") == section_count
    assert error.args == (str(object=error),)


def test_cli_empty_patterns(*, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI rejects an empty pattern list."""
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=["pytest-check-partition"],
    )
    with pytest.raises(expected_exception=SystemExit, match="1"):
        main()


def test_cli_whitespace_pattern(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CLI surfaces core validation errors for blank patterns."""
    filename = "test_cli_blank_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=[
            "pytest-check-partition",
            "--rootdir",
            str(object=tmp_path),
            "   ",
        ],
    )
    with pytest.raises(expected_exception=SystemExit, match="1"):
        main()


def test_cli_missing_patterns_file(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CLI exits cleanly when the patterns file is missing."""
    missing = tmp_path / "missing-patterns"
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=[
            "pytest-check-partition",
            "--partition-patterns-path",
            str(object=missing),
        ],
    )
    with pytest.raises(expected_exception=SystemExit, match="1"):
        main()


def test_cli_nested_pytest_error(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Nested collection failures exit one without an uncaught traceback."""
    filename = "test_cli_nested_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    (tmp_path / "conftest.py").write_text(
        data=(
            "def pytest_collection(session):\n"
            '    raise RuntimeError("broken collection")\n'
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=[
            "pytest-check-partition",
            "--rootdir",
            str(object=tmp_path),
            filename,
        ],
    )
    with pytest.raises(expected_exception=SystemExit, match="1"):
        main()


def test_cli_version(*, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI prints the installed package version."""
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=["pytest-check-partition", "--version"],
    )
    with pytest.raises(expected_exception=SystemExit, match="0"):
        main()


def test_cli_relative_patterns_path_uses_rootdir(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Relative patterns paths resolve against --rootdir."""
    filename = "test_cli_rel_patterns_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    (tmp_path / "patterns").write_text(data=filename + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path / "..")
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=[
            "pytest-check-partition",
            "--rootdir",
            str(object=tmp_path),
            "--partition-patterns-path",
            "patterns",
        ],
    )
    main()


def test_cli_stdin_and_positional_patterns(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Positional patterns merge with --patterns-stdin lines."""
    filename = "test_cli_merge_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=[
            "pytest-check-partition",
            "--rootdir",
            str(object=tmp_path),
            f"{filename}::test_one",
            "--patterns-stdin",
        ],
    )
    monkeypatch.setattr(
        target=sys,
        name="stdin",
        value=StringIO(initial_value=filename + "::test_two\n"),
    )
    main()
