pytest-partition-check
======================

``pytest-partition-check`` verifies that a human-maintained set of pytest
node-ID patterns forms a true partition: every pattern selects at least one
test, and every test belongs to exactly one pattern.

Why
---

Repositories often give CI shards different responsibilities. One shard may
need Docker, another may use secrets or a special runner, and another may be
gated by a workflow condition. Their patterns are a deliberate, human-owned
artefact. Pytest, workflow linting, and coverage do not report empty,
overlapping, or missing shards.

The closest project is `pytest-split`_. It owns the split: users commit a
``.test_durations`` file and run ``pytest --splits N --group K``. Related tools
include `pytest-shard`_ and pytest-xdist's distribution modes. This package
instead checks hand-maintained node-ID patterns without replacing them.

.. _pytest-split: https://pypi.org/project/pytest-split/
.. _pytest-shard: https://pypi.org/project/pytest-shard/

Usage
-----

The motivating use case reads shard patterns from a GitHub Actions
workflow. Install the optional YAML extra first
(``pip install pytest-partition-check[yaml]``). Adapt the job and matrix
key names to your workflow; this repository's test job is ``tests`` and
does not expose a dedicated pattern list key, so the example below uses
placeholders:

.. code-block:: python

   from pathlib import Path

   import pytest
   import yaml
   from pytest_partition_check import PartitionError, check_partition

   def test_ci_patterns_partition_test_suite(
       request: pytest.FixtureRequest,
   ) -> None:
       repository_root = request.config.rootpath
       workflow = repository_root / ".github" / "workflows" / "test.yml"
       config = yaml.safe_load(workflow.read_text())
       # Replace "tests" / "shard_pattern" with your job and matrix key.
       matrix = config["jobs"]["tests"]["strategy"]["matrix"]
       try:
           check_partition(
               patterns=matrix["shard_pattern"],
               rootdir=repository_root,
               disable_plugins=("pytest-retry", "pytest_beartype_tests"),
               extra_args=("--disable-warnings",),
           )
       except PartitionError as error:
           pytest.fail(reason=str(error))

The pytest plugin offers repeatable ``--check-partition=PATTERN`` arguments.
Store one pattern per line in a committed file with
``--partition-patterns-path=PATH`` or the ``partition_patterns_path`` ini
option. A standalone check is also available:

.. code-block:: console

   $ pytest-check-partition tests/unit tests/integration

Patterns files support ``#`` comments: full-line comments and lines whose
first non-whitespace character is ``#`` are ignored. The CLI merges
positional patterns, ``--patterns-stdin`` lines, and
``--partition-patterns-path`` entries into one list, for example
``pytest-check-partition shard_a --partition-patterns-path extra.txt``.

Patterns can also be read one per line from standard input, which is useful
when extracting a CI matrix from another configuration file:

.. code-block:: console

   $ generate-patterns | pytest-check-partition --patterns-stdin

Nested pytest collection
------------------------

``check_partition`` runs one nested ``pytest --collect-only`` session per
pattern plus one more for the full-suite baseline (N+1 collections). That
cost is intentional so each shard is evaluated the same way CI will run
it.

Nested collection warnings are not re-emitted to the caller. Pass
``extra_args=("--disable-warnings",)`` when unknown.ini options from
disabled plugins would otherwise warn loudly.

Collection runs in-process through ``pytest.main --collect-only``. The package
reads the final ``session.items`` after collection-modification and deselection
hooks. This answers what a shard will actually run, including ``-m`` filters
and ``--deselect``, rather than reporting raw discovery.

Outer plugins also enter nested runs and can fail or mutate them. In practice,
callers commonly disable ``pytest-retry`` because it can raise ``ValueError:
no option named 'filtered_exceptions'`` and disable
``pytest_beartype_tests`` because repeated collection can trigger
`beartype issue 637`_ on Python 3.14. Disabled plugins may leave unknown ini
options, so ``extra_args=("--disable-warnings",)`` is usually helpful.

``pytest-split``, ``pytest-randomly``, and ``pytest-xdist`` are disabled by
default during nested collection. Configuration ``addopts`` are cleared too.
In particular, inherited ``--splits`` and ``--group`` settings would otherwise
make the full suite look like one group and create bogus uncollected findings.
Put collection filters needed by the check in ``extra_args`` explicitly. To
opt out of a default plugin disable, reload it later in the nested argv, for
example ``extra_args=("-p", "split", "--splits", "2", "--group", "1")``.

Usage and internal pytest failures are raised loudly. Only pytest's explicit
``NO_TESTS_COLLECTED`` result means that a pattern matched nothing.

.. _beartype issue 637: https://github.com/beartype/beartype/issues/637

When not to use this
--------------------

If your shards are interchangeable and you only want balance, use
``pytest-split`` instead. It makes this whole class of bug impossible rather
than detecting it. Use this checker when the pattern list is intentionally a
human-owned artefact.

License
-------

MIT.
