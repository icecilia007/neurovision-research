"""Normalize patient_unique_id values in CSV files."""

import logging
from pathlib import Path
from typing import List, Optional

import polars as pl

from pipeline_utils import normalize_patient_id, read_csv_arrow


logger = logging.getLogger(__name__)


def _resolve_input(base: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    return candidate if candidate.is_absolute() else (base / candidate)


def run(
    *,
    base: Path,
    inputs: List[str],
    column: str = "patient_unique_id",
    output_dir: Optional[Path] = None,
) -> None:
    """Normalizes ID column in-place or writes normalized copies."""
    for raw_input in inputs:
        input_path = _resolve_input(base, raw_input)
        if not input_path.exists():
            logger.warning("File not found: %s", input_path)
            continue

        df = read_csv_arrow(input_path)
        if column not in df.columns:
            logger.warning("Column %s not found in %s", column, input_path.name)
            continue

        df = df.with_columns(
            pl.col(column)
            .cast(pl.Utf8, strict=False)
            .fill_null("")
            .map_elements(normalize_patient_id, return_dtype=pl.Utf8)
            .alias(column)
        )

        target = input_path
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            target = output_dir / input_path.name

        df.write_csv(target, include_bom=True)
        logger.info("Normalized IDs written to %s", target)
