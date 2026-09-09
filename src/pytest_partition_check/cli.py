"""Standalone command-line interface."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import click
from beartype import beartype

from pytest_partition_check import (
    NestedPytestError,
    PartitionError,
    PatternValidationError,
    check_partition,
)


@click.command(name="pytest-check-partition")
@click.version_option(package_name="pytest-partition-check")
@click.argument("patterns", nargs=-1)
@click.option(
    "--partition-patterns-path",
    type=click.Path(path_type=Path),
)
@click.option(
    "--patterns-stdin",
    is_flag=True,
    help="Read one partition pattern per line from standard input.",
)
@click.option("--rootdir", type=click.Path(path_type=Path))
@click.option("-p", "--disable-plugin", multiple=True)
@click.option("--extra-arg", multiple=True)
@beartype
def main(
    *,
    patterns: tuple[str, ...],
    partition_patterns_path: Path | None,
    patterns_stdin: bool,
    rootdir: Path | None,
    disable_plugin: tuple[str, ...],
    extra_arg: tuple[str, ...],
) -> None:
    """Run the partition check and exit non-zero when it fails."""
    all_patterns = list(patterns)
    if patterns_stdin is True:
        all_patterns.extend(
            line.strip()
            for line in sys.stdin
            if line.strip() != "" and not line.lstrip().startswith("#")
        )
    if partition_patterns_path is not None:
        patterns_path = partition_patterns_path
        if not patterns_path.is_absolute() and rootdir is not None:
            patterns_path = rootdir / patterns_path
        if not patterns_path.is_file():
            raise click.ClickException(
                message=f"Patterns file not found: {patterns_path}",
            )
        all_patterns.extend(
            line.strip()
            for line in patterns_path.read_text(encoding="utf-8").splitlines()
            if line.strip() != "" and not line.lstrip().startswith("#")
        )
    all_patterns = [pattern.strip() for pattern in all_patterns]
    duplicates = sorted(
        pattern
        for pattern, count in Counter(all_patterns).items()
        if count > 1
    )
    if len(duplicates) > 0:
        formatted = "\n".join(f"  {pattern}" for pattern in duplicates)
        raise click.ClickException(
            message=f"Duplicate partition patterns:\n{formatted}",
        )
    if len(all_patterns) == 0:
        raise click.ClickException(message="no patterns provided")
    try:
        check_partition(
            patterns=all_patterns,
            rootdir=rootdir,
            disable_plugins=disable_plugin,
            extra_args=extra_arg,
        )
    except (
        NestedPytestError,
        PatternValidationError,
        PartitionError,
    ) as error:
        raise click.ClickException(message=str(object=error)) from error
