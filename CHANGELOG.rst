Changelog
=========

.. towncrier release notes start

2026.8.23
---------

- Open a changelog pull request from the Release workflow so main branch rulesets are respected.

- Publish to PyPI from a workflow triggered by GitHub Releases.

- Fix CI by combining parallel coverage before reporting and formatting long docstrings.

- Address follow-up PR review comments on validation errors, coverage upload, lint matrix, and ini extra-arg parsing.

- Resolve collection rootdirs so macOS temporary paths produce stable node IDs.

- Collect the full-suite baseline with pytest defaults so testpaths is respected.

- Catch ``NestedPytestError`` in the pytest plugin and report it in the terminal summary.

- Catch ``NestedPytestError`` in the CLI and exit with status 1.

- Reject an empty patterns list before running nested collections.

- Make the CLI exit with a clear error when no patterns are provided.

- Reject duplicate patterns in ``check_partition`` so the API and plugin match the CLI.

- Report a clear error when the plugin patterns file is missing.

- Report a clear error when the CLI patterns file is missing.

- Forward ``disable_plugins`` from the pytest plugin into nested collection.

- Forward ``extra_args`` from the pytest plugin into nested collection.

- Serialize nested collection chdir under a lock and resolve patterns to absolute paths.

- Raise ValueError when rootdir does not exist or is not a directory.

- Populate ``PartitionError.args`` with the human-readable report.

- Export ``NestedPytestError`` from the package public API.

- Reject whitespace-only partition patterns as empty.

- Reject empty-string patterns with a validation error.

- Skip partition checks during ``--collect-only`` sessions.

- Skip partition checks when the outer test session already failed.

- Correct the README workflow example job name.

- Document placeholder matrix keys in the README workflow example.

- Clarify that the README workflow example needs the optional YAML extra.

- Document plugin options for disabling plugins and forwarding extra args.

- Remove the invalid ``cumulative_timing`` pytest setting and use ``[tool.pytest.ini_options]``.

- Align the lint workflow prek version with the version pinned in pyproject.toml.

- Track ``uv.lock`` so CI and local installs share a reproducible dependency set.

- Include ``uv.lock`` in the CI uv cache dependency glob.

- Pin the release workflow calendar-version action to a released tag instead of ``@master``.

- Run the CI test matrix on macOS as well as Ubuntu and Windows.

- Run lint CI on Python 3.10 as well as 3.14.

- Add coverage for unresolved temporary rootdirs on macOS-style paths.

- Add a plugin test for a successful multi-pattern partition check.

- Add a CLI test for ``NestedPytestError`` handling.

- Add a CLI test that merges positional patterns with ``--patterns-stdin``.

- Add a plugin test for duplicates across ``--check-partition`` and a patterns file.

- Add a test that ``collect_node_ids`` defaults ``rootdir`` to the cwd.

- Add a plugin test that successful partition checks stay silent.

- Stash the ``PartitionError`` instance from the plugin for structured inspection.

- Document that partition checks run N+1 nested collections.

- Document that nested collection warnings are not re-emitted.

- Add ``--version`` to the ``pytest-check-partition`` CLI.

- Document ``#`` comment syntax for patterns files.

- Document that the CLI merges patterns from multiple sources.

- Add an optional ``yaml`` extra for the README workflow example.

- Reject duplicate patterns merged from plugin CLI flags and patterns files.

- Upload per-matrix ``.coverage`` artifacts from the test workflow.

- Run the test suite on the release tag before publishing to PyPI.

- Resolve relative CLI patterns paths against ``--rootdir``.

- Add a test that collection records items after ``pytest_collection_modifyitems``.

2026.8.10.1
-----------

- Rename the standalone command to ``pytest-check-partition`` and add
  ``--patterns-stdin`` for newline-delimited patterns.

2026.08.10
----------

- Move the GitHub repository to the ``adamtheturtle`` account.

2026.8.10
---------

- Add the functional API, pytest plugin, and standalone partition checker.
