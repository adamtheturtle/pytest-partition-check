"""Core partition checking API."""

from __future__ import annotations

import os
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest
from beartype import beartype

_COLLECTION_MUTATING_PLUGINS = (
    "split",
    "randomly",
    "xdist",
    "pytest_partition_check",
)


class NestedPytestError(RuntimeError):
    """A nested pytest collection failed."""


class PartitionError(Exception):
    """The given patterns do not partition the test suite."""

    @beartype
    def __init__(
        self,
        *,
        unmatched_patterns: frozenset[str],
        overlapping: Mapping[str, frozenset[str]],
        uncollected: frozenset[str],
    ) -> None:
        """Initialize a partition error with structured problem
        details.
        """
        self.unmatched_patterns = unmatched_patterns
        self.overlapping: Mapping[str, frozenset[str]] = dict(overlapping)
        self.uncollected = uncollected
        super().__init__(self.__str__())

    def __str__(self) -> str:
        """Return a stable, human-readable report of every problem."""
        lines = ["Patterns that matched no tests:"]
        lines.extend(
            f"  {pattern}" for pattern in sorted(self.unmatched_patterns)
        )
        if not self.unmatched_patterns:
            lines.append("  (none)")
        lines.append("Tests collected by more than one pattern:")
        for node_id in sorted(self.overlapping):
            patterns = ", ".join(sorted(self.overlapping[node_id]))
            lines.append(f"  {node_id}: {patterns}")
        if not self.overlapping:
            lines.append("  (none)")
        lines.append("Tests in the full suite that no pattern collects:")
        lines.extend(f"  {node_id}" for node_id in sorted(self.uncollected))
        if not self.uncollected:
            lines.append("  (none)")
        return "\n".join(lines)


class _CollectionRecorder:
    """Record the final item list after collection hooks and
    deselection.
    """

    def __init__(self) -> None:
        """Initialize an empty recorder."""
        self.node_ids: frozenset[str] = frozenset()
        self.collection_finished = False

    @pytest.hookimpl(trylast=True)
    def pytest_collection_finish(self, session: pytest.Session) -> None:
        """Record final node IDs after collection modification hooks
        run.
        """
        self.node_ids = frozenset(item.nodeid for item in session.items)
        self.collection_finished = True


@beartype
def collect_node_ids(
    *,
    pattern: str,
    rootdir: Path | None = None,
    disable_plugins: Iterable[str] = (),
    extra_args: Iterable[str] = (),
) -> frozenset[str]:
    """Return the node IDs of every test ``pytest`` collects for
    ``pattern``.
    """
    resolved_rootdir = Path.cwd() if rootdir is None else rootdir
    recorder = _CollectionRecorder()
    disabled = dict.fromkeys((*_COLLECTION_MUTATING_PLUGINS, *disable_plugins))
    argv = [
        "--collect-only",
        "--rootdir",
        str(object=resolved_rootdir),
        "-o",
        "addopts=",
        *(argument for name in disabled for argument in ("-p", f"no:{name}")),
        *extra_args,
        pattern,
    ]
    previous_directory = Path.cwd()
    os.chdir(path=resolved_rootdir)
    try:
        exit_code = pytest.ExitCode(
            value=pytest.main(args=argv, plugins=[recorder])
        )
    finally:
        os.chdir(path=previous_directory)
    normal_codes = {pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED}
    unmatched_selector = (
        exit_code is pytest.ExitCode.USAGE_ERROR
        and recorder.collection_finished
    )
    if exit_code in normal_codes or unmatched_selector:
        return recorder.node_ids
    message = (
        "Nested pytest collection failed for pattern "
        f"{pattern!r} with exit code {exit_code.name} "
        f"({int(exit_code)})."
    )
    raise NestedPytestError(message)


@beartype
def check_partition(
    *,
    patterns: Iterable[str],
    rootdir: Path | None = None,
    disable_plugins: Iterable[str] = (),
    extra_args: Iterable[str] = (),
) -> None:
    """Raise ``PartitionError`` unless ``patterns`` partition the test
    suite.
    """
    pattern_list = tuple(patterns)
    disabled = tuple(disable_plugins)
    arguments = tuple(extra_args)
    collected_by_pattern = {
        pattern: collect_node_ids(
            pattern=pattern,
            rootdir=rootdir,
            disable_plugins=disabled,
            extra_args=arguments,
        )
        for pattern in pattern_list
    }
    full_suite = collect_node_ids(
        pattern=".",
        rootdir=rootdir,
        disable_plugins=disabled,
        extra_args=arguments,
    )
    matched_by: defaultdict[str, set[str]] = defaultdict(set)
    for pattern, node_ids in collected_by_pattern.items():
        for node_id in node_ids:
            matched_by[node_id].add(pattern)
    unmatched = frozenset(
        pattern
        for pattern, node_ids in collected_by_pattern.items()
        if not node_ids
    )
    overlapping = {
        node_id: frozenset(matched_patterns)
        for node_id, matched_patterns in matched_by.items()
        if len(matched_patterns) > 1
    }
    uncollected = full_suite.difference(matched_by)
    if unmatched or overlapping or uncollected:
        raise PartitionError(
            unmatched_patterns=unmatched,
            overlapping=overlapping,
            uncollected=uncollected,
        )
