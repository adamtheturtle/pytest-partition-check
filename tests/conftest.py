"""Test configuration."""

import pytest
from click.testing import CliRunner

pytest_plugins = ["pytester"]


@pytest.fixture
def runner() -> CliRunner:
    """Return a runner for the public command-line interface."""
    return CliRunner()
