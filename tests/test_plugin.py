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


def test_plugin_forwards_disable_and_extra_args(
    *, pytester: pytest.Pytester
) -> None:
    """Plugin options reach nested collection."""
    pytester.makepyfile(
        test_plugin_forward_sample="""
        def test_one():
            pass

        def test_two():
            pass
        """
    )
    result = pytester.runpytest(
        "--check-partition=test_plugin_forward_sample.py::test_one",
        "--check-partition=test_plugin_forward_sample.py::test_two",
        "--partition-extra-arg=--disable-warnings",
        "--partition-disable-plugin=break_collection",
    )
    result.assert_outcomes(passed=2)


def test_plugin_duplicate_patterns_across_sources(
    *, pytester: pytest.Pytester
) -> None:
    """Duplicates across CLI and patterns file fail the session."""
    pytester.makepyfile(
        test_plugin_dup_sample="""
        def test_one():
            pass
        """
    )
    patterns = pytester.makefile(
        "", dup_patterns="test_plugin_dup_sample.py\n"
    )
    result = pytester.runpytest(
        "--check-partition=test_plugin_dup_sample.py",
        f"--partition-patterns-path={patterns}",
    )
    result.stdout.fnmatch_lines(
        lines2=["*partition check failed*", "*duplicate*"]
    )
    assert result.ret != 0


def test_plugin_missing_patterns_file(*, pytester: pytest.Pytester) -> None:
    """A missing patterns file fails the session with a clear summary."""
    pytester.makepyfile(
        test_plugin_missing_sample="""
        def test_one():
            pass
        """
    )
    result = pytester.runpytest("--partition-patterns-path=does-not-exist")
    result.stdout.fnmatch_lines(
        lines2=["*partition check failed*", "*Patterns file not found*"]
    )
    assert result.ret != 0


def test_plugin_nested_pytest_error(*, pytester: pytest.Pytester) -> None:
    """Nested collection failures are reported in the terminal summary."""
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
        lines2=[
            "*partition check failed*",
            "*Nested pytest collection failed*",
        ]
    )
    assert result.ret != 0


def test_plugin_skips_collect_only(*, pytester: pytest.Pytester) -> None:
    """Partition checks are skipped during --collect-only."""
    pytester.makepyfile(
        test_plugin_collect_only_sample="""
        def test_one():
            pass

        def test_two():
            pass
        """
    )
    result = pytester.runpytest(
        "--collect-only",
        "--check-partition=test_plugin_collect_only_sample.py::test_one",
    )
    assert "partition check failed" not in result.stdout.str()
    assert result.ret == 0


def test_plugin_skips_when_tests_failed(*, pytester: pytest.Pytester) -> None:
    """Partition checks are skipped when the outer session already failed."""
    pytester.makepyfile(
        test_plugin_failed_outer_sample="""
        def test_one():
            assert False

        def test_two():
            pass
        """
    )
    result = pytester.runpytest(
        "--check-partition=test_plugin_failed_outer_sample.py::test_one",
    )
    assert "partition check failed" not in result.stdout.str()
    assert result.ret != 0


def test_plugin_success_multiple_patterns(
    *, pytester: pytest.Pytester
) -> None:
    """Multiple valid --check-partition patterns succeed silently."""
    pytester.makepyfile(
        test_plugin_multi_sample="""
        def test_one():
            pass

        def test_two():
            pass
        """
    )
    result = pytester.runpytest(
        "--check-partition=test_plugin_multi_sample.py::test_one",
        "--check-partition=test_plugin_multi_sample.py::test_two",
    )
    result.assert_outcomes(passed=2)
    assert "partition check failed" not in result.stdout.str()
    assert result.ret == 0
