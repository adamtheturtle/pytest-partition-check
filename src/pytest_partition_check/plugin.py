"""Pytest plugin for checking partitions after a test session."""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest
from _pytest.terminal import TerminalReporter
from beartype import beartype

from pytest_partition_check import (
    NestedPytestError,
    PartitionError,
    PatternValidationError,
    check_partition,
)


@beartype
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
    group.addoption(
        "--partition-disable-plugin",
        action="append",
        default=[],
        metavar="NAME",
        help="Disable NAME during nested partition collection.",
    )
    group.addoption(
        "--partition-extra-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="Forward ARG to nested partition collection.",
    )
    parser.addini(
        name="partition_disable_plugins",
        help="Comma-separated plugins to disable during nested collection.",
        default="",
    )
    parser.addini(
        name="partition_extra_args",
        help="Whitespace-separated extra args for nested collection.",
        default="",
    )


@beartype
def _patterns(*, config: pytest.Config) -> tuple[str, ...]:
    """Return patterns configured on the command line or in a file."""
    direct_value = config.getoption(name="check_partition")
    direct = tuple(str(object=value) for value in direct_value or ())
    cli_path_value = config.getoption(name="partition_patterns_path")
    ini_path = str(object=config.getini(name="partition_patterns_path"))
    if cli_path_value is not None and cli_path_value != "":
        path_value = str(object=cli_path_value)
    else:
        path_value = ini_path
    if path_value == "":
        return direct
    path = Path(path_value)
    if not path.is_absolute():
        path = config.rootpath / path
    if not path.is_file():
        message = f"Patterns file not found: {path}"
        raise FileNotFoundError(message)
    file_patterns = tuple(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() != "" and not line.lstrip().startswith("#")
    )
    return (*direct, *file_patterns)


@beartype
def _disable_plugins(*, config: pytest.Config) -> tuple[str, ...]:
    """Return plugins to disable during nested collection."""
    cli_value = config.getoption(name="partition_disable_plugin")
    ini_value = str(object=config.getini(name="partition_disable_plugins"))
    ini_plugins = tuple(
        part.strip()
        for part in str(object=ini_value).split(sep=",")
        if part.strip() != ""
    )
    return (
        *(str(object=value) for value in cli_value or ()),
        *ini_plugins,
    )


@beartype
def _extra_args(*, config: pytest.Config) -> tuple[str, ...]:
    """Return extra args for nested collection."""
    cli_value = config.getoption(name="partition_extra_arg")
    ini_value = str(object=config.getini(name="partition_extra_args"))
    ini_args = (
        tuple(shlex.split(s=str(object=ini_value))) if ini_value != "" else ()
    )
    return (
        *(str(object=value) for value in cli_value or ()),
        *ini_args,
    )


@beartype
def pytest_sessionfinish(
    session: pytest.Session, exitstatus: int | pytest.ExitCode
) -> None:
    """Check the configured partition after the outer session finishes."""
    if session.config.option.collectonly:
        return
    if exitstatus not in {0, pytest.ExitCode.OK}:
        return
    try:
        patterns = _patterns(config=session.config)
    except FileNotFoundError as error:
        session.config.stash[_PARTITION_ERROR] = error
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        return
    if len(patterns) == 0:
        return
    try:
        check_partition(
            patterns=patterns,
            rootdir=session.config.rootpath,
            disable_plugins=_disable_plugins(config=session.config),
            extra_args=_extra_args(config=session.config),
        )
    except (
        NestedPytestError,
        PatternValidationError,
        PartitionError,
    ) as error:
        session.config.stash[_PARTITION_ERROR] = error
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


_PARTITION_ERROR = pytest.StashKey[BaseException]()


@beartype
def pytest_terminal_summary(
    terminalreporter: TerminalReporter, exitstatus: int
) -> None:
    """Show a partition failure in the terminal summary."""
    del exitstatus
    error = terminalreporter.config.stash.get(
        key=_PARTITION_ERROR, default=None
    )
    if error is not None:
        terminalreporter.write_sep(
            sep="=", title="partition check failed", red=True
        )
        terminalreporter.write_line(line=str(object=error), red=True)
