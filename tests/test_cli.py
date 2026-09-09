"""Tests for the standalone command-line interface."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from pytest_partition_check import PartitionError
from pytest_partition_check.cli import main


def _write_suite(*, root: Path, filename: str) -> None:
    """Write a small suite for CLI testing."""
    _ = (root / filename).write_text(
        data="def test_one():\n    pass\n\ndef test_two():\n    pass\n",
        encoding="utf-8",
    )


def test_cli_success(*, runner: CliRunner, tmp_path: Path) -> None:
    """The CLI returns normally for a valid partition."""
    filename = "test_cli_success_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    result = runner.invoke(
        cli=main,
        args=[
            "--rootdir",
            str(object=tmp_path),
            filename,
        ],
    )
    assert result.exit_code == 0, result.output


def test_cli_failure(*, runner: CliRunner, tmp_path: Path) -> None:
    """The CLI exits one and prints the shared report on failure."""
    filename = "test_cli_failure_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    args = [
        "--rootdir",
        str(object=tmp_path),
        f"{filename}::test_one",
    ]
    result = runner.invoke(cli=main, args=args)
    assert result.exit_code == 1


def test_cli_patterns_file(*, runner: CliRunner, tmp_path: Path) -> None:
    """The CLI reads a committed patterns file and accepts extra
    options.
    """
    filename = "test_cli_file_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    patterns = tmp_path / "patterns"
    _ = patterns.write_text(
        data=f"# shard list\n\n{filename}\n", encoding="utf-8"
    )
    result = runner.invoke(
        cli=main,
        args=[
            "--rootdir",
            str(object=tmp_path),
            "--partition-patterns-path",
            str(object=patterns),
            "--disable-plugin",
            "retry",
            "--extra-arg=--disable-warnings",
        ],
    )
    assert result.exit_code == 0, result.output


def test_cli_patterns_stdin(*, runner: CliRunner, tmp_path: Path) -> None:
    """The CLI reads newline-delimited patterns from standard input."""
    filename = "test_cli_stdin_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    result = runner.invoke(
        cli=main,
        args=[
            "--rootdir",
            str(object=tmp_path),
            "--patterns-stdin",
        ],
        input=f"# shard list\n\n{filename}\n",
    )
    assert result.exit_code == 0, result.output


def test_cli_duplicate_patterns(*, runner: CliRunner, tmp_path: Path) -> None:
    """The CLI rejects duplicate patterns."""
    filename = "test_cli_duplicate_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    result = runner.invoke(cli=main, args=[filename, filename])
    assert result.exit_code == 1


def test_cli_whitespace_duplicate_patterns(
    *, runner: CliRunner, tmp_path: Path
) -> None:
    """The CLI rejects patterns that differ only by surrounding whitespace."""
    filename = "test_cli_ws_dup_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    args = [
        "--rootdir",
        str(object=tmp_path),
        filename,
        f" {filename} ",
    ]
    result = runner.invoke(cli=main, args=args)
    assert result.exit_code == 1


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


def test_cli_empty_patterns(*, runner: CliRunner) -> None:
    """The CLI rejects an empty pattern list."""
    result = runner.invoke(cli=main)
    assert result.exit_code == 1


def test_cli_whitespace_pattern(*, runner: CliRunner, tmp_path: Path) -> None:
    """The CLI surfaces core validation errors for blank patterns."""
    filename = "test_cli_blank_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    args = [
        "--rootdir",
        str(object=tmp_path),
        "   ",
    ]
    result = runner.invoke(cli=main, args=args)
    assert result.exit_code == 1


def test_cli_missing_patterns_file(
    *, runner: CliRunner, tmp_path: Path
) -> None:
    """The CLI exits cleanly when the patterns file is missing."""
    missing = tmp_path / "missing-patterns"
    args = [
        "--partition-patterns-path",
        str(object=missing),
    ]
    result = runner.invoke(cli=main, args=args)
    assert result.exit_code == 1


def test_cli_nested_pytest_error(*, runner: CliRunner, tmp_path: Path) -> None:
    """Nested collection failures exit one without an uncaught
    traceback.
    """
    filename = "test_cli_nested_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    _ = (tmp_path / "conftest.py").write_text(
        data=(
            "def pytest_collection(session):\n"
            '    raise RuntimeError("broken collection")\n'
        ),
        encoding="utf-8",
    )
    args = [
        "--rootdir",
        str(object=tmp_path),
        filename,
    ]
    result = runner.invoke(cli=main, args=args)
    assert result.exit_code == 1


def test_cli_version(*, runner: CliRunner) -> None:
    """The CLI prints the installed package version."""
    result = runner.invoke(cli=main, args=["--version"])
    assert result.exit_code == 0
    assert "pytest-check-partition" in result.output


def test_cli_relative_patterns_path_uses_rootdir(
    *, monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path
) -> None:
    """Relative patterns paths resolve against --rootdir."""
    filename = "test_cli_rel_patterns_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    _ = (tmp_path / "patterns").write_text(
        data=filename + "\n", encoding="utf-8"
    )
    monkeypatch.chdir(path=tmp_path / "..")
    result = runner.invoke(
        cli=main,
        args=[
            "--rootdir",
            str(object=tmp_path),
            "--partition-patterns-path",
            "patterns",
        ],
    )
    assert result.exit_code == 0, result.output


def test_cli_stdin_and_positional_patterns(
    *, runner: CliRunner, tmp_path: Path
) -> None:
    """Positional patterns merge with --patterns-stdin lines."""
    filename = "test_cli_merge_sample.py"
    _write_suite(root=tmp_path, filename=filename)
    result = runner.invoke(
        cli=main,
        args=[
            "--rootdir",
            str(object=tmp_path),
            f"{filename}::test_one",
            "--patterns-stdin",
        ],
        input=filename + "::test_two\n",
    )
    assert result.exit_code == 0, result.output
