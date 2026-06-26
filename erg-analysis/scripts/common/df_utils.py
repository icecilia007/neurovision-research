"""DataFrame utility helpers shared across pipeline stages."""

from __future__ import annotations

import logging

import polars as pl


logger = logging.getLogger(__name__)


def dedup_and_log(df: pl.DataFrame, subset: list[str], label: str) -> pl.DataFrame:
    """Deduplicates a DataFrame by subset columns and logs how many rows were removed."""
    before = len(df)
    df = df.unique(subset=subset, keep="first")
    removed = before - len(df)
    if removed:
        logger.info("%s: %d duplicate rows removed (kept %d unique)", label, removed, len(df))
    return df
