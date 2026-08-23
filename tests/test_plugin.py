"""Tests for the pytest plugin and console script."""

import pytest


def test_plugin_reports_failure(*, pytester: pytest.Pytester) -> None:
    """The plugin fails a session with the partition report."""
    pytester.makepyfile(
        test_plugin_failure_sample="""
        def test_one():
            pass

        def test_two():
            pass
        """
    )
    result = pytester.runpytest(
        "--check-partition=test_plugin_failure_sample.py::test_one"
    )
    result.assert_outcomes(passed=2)
    result.stdout.fnmatch_lines(
        lines2=[
            "*partition check failed*",
            "*test_plugin_failure_sample.py::test_two*",
        ]
    )
    assert result.ret != 0


def test_patterns_file_ini_option(*, pytester: pytest.Pytester) -> None:
    """The plugin reads patterns from the configured committed file."""
    pytester.makepyfile(
        test_plugin_ini_sample="""
        def test_one():
            pass
        """
    )
    pytester.makefile("", partition_patterns="test_plugin_ini_sample.py\n")
    pytester.makeini(
        source="[pytest]\npartition_patterns_path = partition_patterns\n"
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_absolute_patterns_file_option(*, pytester: pytest.Pytester) -> None:
    """The command-line patterns path may be absolute."""
    pytester.makepyfile(
        test_plugin_absolute_sample="""
        def test_one():
            pass
        """
    )
    patterns = pytester.makefile(
        "", absolute_patterns="test_plugin_absolute_sample.py\n"
    )
    result = pytester.runpytest(f"--partition-patterns-path={patterns}")
    result.assert_outcomes(passed=1)


def test_plugin_missing_patterns_file(*, pytester: pytest.Pytester) -> None:
    """A missing patterns file fails the session with a clear summary."""
    pytester.makepyfile(
        test_plugin_missing_sample="""
        def test_one():
            pass
        """
    )
    result = pytester.runpytest(
        "--partition-patterns-path=does-not-exist"
    )
    result.stdout.fnmatch_lines(
        lines2=["*partition check failed*", "*Patterns file not found*"]
    )
    assert result.ret != 0


def test_plugin_nested_pytest_error(*, pytester: pytest.Pytester) -> None:
    """Nested collection failures are reported without INTERNALERROR."""
    pytester.makepyfile(
        test_plugin_nested_sample="""
        def test_one():
            pass
        """
    )
    pytester.makeconftest(
        source="""
        def pytest_collection(session):
            if session.config.option.collectonly:
                raise RuntimeError("broken nested collection")
        """
    )
    result = pytester.runpytest(
        "--check-partition=test_plugin_nested_sample.py"
    )
    result.stdout.fnmatch_lines(
        lines2=["*partition check failed*", "*Nested pytest collection failed*"]
    )
    assert result.ret != 0
