"""Purge submodule: remove orphan IDs from consolidated datasets."""

from pipeline.purge.purge_orphan_ids import run as run_purge_orphan_ids

__all__ = ["run_purge_orphan_ids"]
