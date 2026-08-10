"""Pytest plugin for checking partitions after a test session."""

from __future__ import annotations

from pathlib import Path
from typing import TypeGuard

import pytest
from _pytest.terminal import TerminalReporter
from beartype import beartype
from beartype.door import TypeHint

from pytest_partition_check import PartitionError, check_partition


@beartype
def _is_string_list(value: object) -> TypeGuard[list[str]]:
    """Return whether a value is a list containing only strings."""
    return TypeHint(hint=list[str]).is_bearable(obj=value)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register command-line and configuration options."""
    group = parser.getgroup(name="partition-check")
    group.addoption(
        "--check-partition",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Check that repeatable PATTERN values partition the test suite.",
    )
    group.addoption(
        "--partition-patterns-path",
        default=None,
        metavar="PATH",
        help="Read one partition pattern per line from PATH.",
    )
    parser.addini(
        name="partition_patterns_path",
        help="Path containing one partition pattern per line.",
        default="",
    )


@beartype
def _patterns(*, config: pytest.Config) -> tuple[str, ...]:
    """Return patterns configured on the command line or in a file."""
    direct_value = config.getoption(name="check_partition")
    if not _is_string_list(value=direct_value):  # pragma: no cover
        msg = "pytest returned an invalid --check-partition value"
        raise TypeError(msg)
    direct = tuple(direct_value)
    path_value: str = config.getoption(
        name="partition_patterns_path"
    ) or config.getini(name="partition_patterns_path")
    if not path_value:
        return direct
    path = Path(path_value)
    if not path.is_absolute():
        path = config.rootpath / path
    file_patterns = tuple(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    return (*direct, *file_patterns)


def pytest_sessionfinish(
    session: pytest.Session, exitstatus: int | pytest.ExitCode
) -> None:
    """Check the configured partition after the outer session finishes."""
    del exitstatus
    patterns = _patterns(config=session.config)
    if not patterns:
        return
    try:
        check_partition(patterns=patterns, rootdir=session.config.rootpath)
    except PartitionError as error:
        session.config.stash[_PARTITION_ERROR] = str(object=error)
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


_PARTITION_ERROR = pytest.StashKey[str]()


def pytest_terminal_summary(
    terminalreporter: TerminalReporter, exitstatus: int
) -> None:
    """Show a partition failure in the terminal summary."""
    del exitstatus
    message = terminalreporter.config.stash.get(
        key=_PARTITION_ERROR, default=None
    )
    if message is not None:
        terminalreporter.write_sep(
            sep="=", title="partition check failed", red=True
        )
        terminalreporter.write_line(line=message, red=True)
