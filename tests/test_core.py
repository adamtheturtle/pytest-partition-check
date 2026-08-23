"""Tests for the functional API."""

from pathlib import Path

import pytest

from pytest_partition_check import (
    NestedPytestError,
    PartitionError,
    check_partition,
    collect_node_ids,
)


def _suite(*, pytester: pytest.Pytester) -> Path:
    """Create and return a small test suite root."""
    pytester.makepyfile(
        test_alpha="""
        def test_one():
            pass

        def test_two():
            pass
        """,
        test_beta="""
        def test_three():
            pass
        """,
    )
    return pytester.path


def test_collect_node_ids(*, pytester: pytest.Pytester) -> None:
    """The collector returns node IDs for a pattern."""
    root = _suite(pytester=pytester)
    assert collect_node_ids(pattern="test_alpha.py", rootdir=root) == {
        "test_alpha.py::test_one",
        "test_alpha.py::test_two",
    }


def test_good_partition(*, pytester: pytest.Pytester) -> None:
    """A valid partition does not raise an exception."""
    root = _suite(pytester=pytester)
    check_partition(patterns=("test_alpha.py", "test_beta.py"), rootdir=root)


def test_all_partition_problems(*, pytester: pytest.Pytester) -> None:
    """Every partition problem is reported together and structurally."""
    root = _suite(pytester=pytester)
    with pytest.raises(expected_exception=PartitionError) as raised:
        check_partition(
            patterns=(
                "test_alpha.py::test_missing",
                "test_alpha.py",
                "test_alpha.py::test_one",
            ),
            rootdir=root,
        )
    error = raised.value
    assert error.unmatched_patterns == {"test_alpha.py::test_missing"}
    assert error.overlapping == {
        "test_alpha.py::test_one": {
            "test_alpha.py",
            "test_alpha.py::test_one",
        }
    }
    assert error.uncollected == {"test_beta.py::test_three"}
    assert (
        str(object=error)
        == """Patterns that matched no tests:
  test_alpha.py::test_missing
Tests collected by more than one pattern:
  test_alpha.py::test_one: test_alpha.py, test_alpha.py::test_one
Tests in the full suite that no pattern collects:
  test_beta.py::test_three"""
    )


def test_extra_args_apply_post_deselection(
    *, pytester: pytest.Pytester
) -> None:
    """Extra arguments affect the final post-deselection item list."""
    root = _suite(pytester=pytester)
    assert collect_node_ids(
        pattern=".",
        rootdir=root,
        extra_args=("--deselect=test_alpha.py::test_one",),
    ) == {"test_alpha.py::test_two", "test_beta.py::test_three"}


def test_disable_plugins_is_honoured(*, pytester: pytest.Pytester) -> None:
    """Callers can disable a plugin that would break collection."""
    root = _suite(pytester=pytester)
    pytester.makeconftest(
        source="""
        def pytest_collection_modifyitems(config, items):
            if config.pluginmanager.hasplugin("break_collection"):
                raise RuntimeError("plugin remained active")
        """
    )
    assert collect_node_ids(
        pattern=".", rootdir=root, disable_plugins=("break_collection",)
    )


def test_internal_error_is_loud(*, pytester: pytest.Pytester) -> None:
    """An internal collection error is not treated as no tests."""
    root = _suite(pytester=pytester)
    pytester.makeconftest(
        source="""
        def pytest_collection(session):
            raise RuntimeError("broken collection")
        """
    )
    with pytest.raises(
        expected_exception=NestedPytestError, match="INTERNAL_ERROR"
    ):
        collect_node_ids(pattern=".", rootdir=root)


def test_pytest_split_is_disabled_by_default(
    *, pytester: pytest.Pytester
) -> None:
    """Active pytest-split configuration cannot truncate nested collection."""
    root = _suite(pytester=pytester)
    pytester.makeini(source="[pytest]\naddopts = --splits 2 --group 1\n")
    assert collect_node_ids(pattern=".", rootdir=root) == {
        "test_alpha.py::test_one",
        "test_alpha.py::test_two",
        "test_beta.py::test_three",
    }
