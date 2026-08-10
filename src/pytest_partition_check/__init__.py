"""Check that pytest node-ID patterns partition a test suite."""

from pytest_partition_check._core import (
    PartitionError,
    check_partition,
    collect_node_ids,
)

__all__ = ["PartitionError", "check_partition", "collect_node_ids"]
