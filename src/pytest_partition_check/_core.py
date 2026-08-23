"""Core partition checking API."""

from __future__ import annotations

import os
import threading
from collections import Counter, defaultdict
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

_CHDIR_LOCK = threading.Lock()


class NestedPytestError(RuntimeError):
    """A nested pytest collection failed."""


class PatternValidationError(ValueError):
    """The given partition patterns are invalid."""


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
def _resolve_rootdir(*, rootdir: Path | None) -> Path:
    """Return an absolute existing directory for nested collection."""
    resolved = Path.cwd() if rootdir is None else rootdir
    resolved = resolved.resolve()
    if not resolved.is_dir():
        message = f"rootdir does not exist or is not a directory: {resolved}"
        raise PatternValidationError(message)
    return resolved


@beartype
def _absolute_pattern(*, pattern: str, rootdir: Path) -> str:
    """Return ``pattern`` with its path portion resolved under
    ``rootdir``.
    """
    path_part, separator, rest = pattern.partition("::")
    if not path_part:
        return pattern
    absolute = str(object=(rootdir / path_part).resolve())
    if separator:
        return f"{absolute}{separator}{rest}"
    return absolute


@beartype
def collect_node_ids(
    *,
    pattern: str | None = None,
    rootdir: Path | None = None,
    disable_plugins: Iterable[str] = (),
    extra_args: Iterable[str] = (),
) -> frozenset[str]:
    """Return the node IDs of every test ``pytest`` collects for
    ``pattern``.

    When ``pattern`` is ``None``, collect the default suite (respecting
    ``testpaths``) rather than forcing ``"."``.
    """
    recorder = _CollectionRecorder()
    disabled = dict.fromkeys((*_COLLECTION_MUTATING_PLUGINS, *disable_plugins))
    # Resolve rootdir under the lock so concurrent callers with
    # rootdir=None do not read another thread's temporary cwd.
    with _CHDIR_LOCK:
        resolved_rootdir = _resolve_rootdir(rootdir=rootdir)
        argv = [
            "--collect-only",
            "--rootdir",
            str(object=resolved_rootdir),
            "-o",
            "addopts=",
            *(
                argument
                for name in disabled
                for argument in ("-p", f"no:{name}")
            ),
            *extra_args,
        ]
        if pattern is not None:
            argv.append(
                _absolute_pattern(pattern=pattern, rootdir=resolved_rootdir)
            )
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
    display_pattern = "." if pattern is None else pattern
    message = (
        "Nested pytest collection failed for pattern "
        f"{display_pattern!r} with exit code {exit_code.name} "
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
    pattern_list = tuple(pattern.strip() for pattern in patterns)
    if not pattern_list:
        message = "no patterns provided"
        raise PatternValidationError(message)
    if any(not pattern for pattern in pattern_list):
        message = "patterns must be non-empty after stripping whitespace"
        raise PatternValidationError(message)
    duplicates = sorted(
        pattern
        for pattern, count in Counter(pattern_list).items()
        if count > 1
    )
    if duplicates:
        formatted = ", ".join(duplicates)
        message = f"duplicate partition patterns: {formatted}"
        raise PatternValidationError(message)
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
        pattern=None,
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
