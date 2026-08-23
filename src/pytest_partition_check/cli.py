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
    parser.add_argument(
        "--version",
        action="version",
        version=version(distribution_name="pytest-partition-check"),
    )
    parser.add_argument("patterns", nargs="*")
    parser.add_argument("--partition-patterns-path", type=Path)
    parser.add_argument(
        "--patterns-stdin",
        action="store_true",
        help="Read one partition pattern per line from standard input.",
    )
    parser.add_argument("--rootdir", type=Path)
    parser.add_argument("-p", "--disable-plugin", action="append", default=[])
    parser.add_argument("--extra-arg", action="append", default=[])
    arguments = parser.parse_args()
    patterns = list(arguments.patterns)
    if arguments.patterns_stdin:
        patterns.extend(
            line.strip()
            for line in sys.stdin
            if line.strip() and not line.lstrip().startswith("#")
        )
    if arguments.partition_patterns_path is not None:
        patterns_path = arguments.partition_patterns_path
        if not patterns_path.is_absolute() and arguments.rootdir is not None:
            patterns_path = arguments.rootdir / patterns_path
        if not patterns_path.is_file():
            parser.exit(
                status=1,
                message=f"Patterns file not found: {patterns_path}\n",
            )
        patterns.extend(
            line.strip()
            for line in patterns_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    patterns = [pattern.strip() for pattern in patterns]
    duplicates = sorted(
        pattern for pattern, count in Counter(patterns).items() if count > 1
    )
    if duplicates:
        formatted = "\n".join(f"  {pattern}" for pattern in duplicates)
        parser.exit(
            status=1,
            message=f"Duplicate partition patterns:\n{formatted}\n",
        )
    if not patterns:
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
