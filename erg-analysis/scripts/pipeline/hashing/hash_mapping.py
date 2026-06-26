"""Builds patient_unique_id -> patient_unique_id_hashed mapping parquet."""

import logging
from pathlib import Path

import polars as pl

from pipeline_utils import (
    PatientIDHasher,
    dedupe_mapping,
    normalize_patient_id,
    read_csv_arrow,
)


logger = logging.getLogger(__name__)


def run(
    *,
    base: Path,
    input_csv: str,
    output_parquet: str,
    column: str = "patient_unique_id",
    salt: str | None = None,
) -> None:
    """Reads mapping source CSV and writes hashed mapping parquet."""
    input_path = Path(input_csv)
    if not input_path.is_absolute():
        input_path = base / input_path

    output_path = Path(output_parquet)
    if not output_path.is_absolute():
        output_path = base / output_path

    df = read_csv_arrow(input_path)
    if column not in df.columns:
        raise ValueError(f"Column {column} not found in {input_path}")

    df = df.with_columns(
        pl.col(column)
        .cast(pl.Utf8, strict=False)
        .fill_null("")
        .map_elements(normalize_patient_id, return_dtype=pl.Utf8)
        .alias(column)
    )
    df = dedupe_mapping(df.select([column]))

    hasher = PatientIDHasher(salt=salt)
    df = df.with_columns(
        pl.col(column)
        .map_elements(hasher.hash_patient_id, return_dtype=pl.Utf8)
        .alias("patient_unique_id_hashed")
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)
    logger.info("Hash mapping written to %s (rows=%d)", output_path, df.height)
