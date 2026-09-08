"""Standalone command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from importlib.metadata import version
from pathlib import Path

from beartype import beartype

from pytest_partition_check import (
    NestedPytestError,
    PartitionError,
    PatternValidationError,
    check_partition,
)


@beartype
def main() -> None:
    """Run the partition check and exit non-zero when it fails."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument(
        "--version",
        action="version",
        version=version(distribution_name="pytest-partition-check"),
    )
    _ = parser.add_argument("patterns", nargs="*")
    _ = parser.add_argument("--partition-patterns-path", type=Path)
    _ = parser.add_argument(
        "--patterns-stdin",
        action="store_true",
        help="Read one partition pattern per line from standard input.",
    )
    _ = parser.add_argument("--rootdir", type=Path)
    _ = parser.add_argument(
        "-p", "--disable-plugin", action="append", default=[]
    )
    _ = parser.add_argument("--extra-arg", action="append", default=[])
    arguments = parser.parse_args()
    patterns = list(arguments.patterns)
    if arguments.patterns_stdin is True:
        patterns.extend(
            line.strip()
            for line in sys.stdin
            if line.strip() != "" and not line.lstrip().startswith("#")
        )
    if arguments.partition_patterns_path is not None:
        patterns_path = Path(str(object=arguments.partition_patterns_path))
        if not patterns_path.is_absolute() and arguments.rootdir is not None:
            rootdir = Path(str(object=arguments.rootdir))
            patterns_path = rootdir / patterns_path
        if not patterns_path.is_file():
            parser.exit(
                status=1,
                message=f"Patterns file not found: {patterns_path}\n",
            )
        patterns.extend(
            line.strip()
            for line in patterns_path.read_text(encoding="utf-8").splitlines()
            if line.strip() != "" and not line.lstrip().startswith("#")
        )
    patterns = [pattern.strip() for pattern in patterns]
    duplicates = sorted(
        pattern for pattern, count in Counter(patterns).items() if count > 1
    )
    if len(duplicates) > 0:
        formatted = "\n".join(f"  {pattern}" for pattern in duplicates)
        parser.exit(
            status=1,
            message=f"Duplicate partition patterns:\n{formatted}\n",
        )
    if len(patterns) == 0:
        parser.exit(status=1, message="no patterns provided\n")
    try:
        check_partition(
            patterns=patterns,
            rootdir=arguments.rootdir,
            disable_plugins=arguments.disable_plugin,
            extra_args=arguments.extra_arg,
        )
    except (
        NestedPytestError,
        PatternValidationError,
        PartitionError,
    ) as error:
        parser.exit(status=1, message=f"{error}\n")
