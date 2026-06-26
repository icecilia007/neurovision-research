"""Applies hash mapping to CSV inputs and writes Parquet outputs."""

import logging
from pathlib import Path
from typing import Dict, Iterable, List

import polars as pl
import pyarrow as pa
import pyarrow.dataset as pa_ds

from pipeline_utils import (
    MissingIdCsvWriter,
    ParquetChunkWriter,
    drop_columns_if_present,
    iter_csv_arrow,
    load_hash_mapping,
    normalize_patient_id,
    read_csv_arrow,
)


logger = logging.getLogger(__name__)


def _resolve_parquet_files(path: Path) -> List[str]:
    """Resolves only parquet data files, skipping Spark crc/marker files."""
    if path.is_file():
        return [str(path)]

    files = sorted(path.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet data files found under {path}")
    return [str(file_path) for file_path in files]


def _output_filename_for_input(input_path: Path, name_suffix: str = "") -> str:
    """Builds short, intuitive output names for hashed staging files."""
    suffix = f"_{name_suffix}" if name_suffix else ""
    stem = input_path.stem.lower()

    if "consolidated_metadata" in stem or stem.endswith("_metadata"):
        return f"metadata{suffix}.parquet"

    if "consolidated_waveforms" in stem or stem.endswith("_waveforms"):
        return f"waveforms{suffix}.parquet"

    if stem.startswith("patients-") or stem == "patients" or "patients" in stem:
        return f"patients{suffix}.parquet"

    return f"{input_path.stem}{suffix}.parquet"


def _is_empty_like_expr(column: str) -> pl.Expr:
    cleaned = pl.col(column).cast(pl.Utf8, strict=False).str.strip_chars()
    return (
        cleaned.is_null()
        | (cleaned == "")
        | cleaned.str.to_lowercase().is_in(["nan", "none", "null", "<na>", "nat"])
    )


def _coerce_numeric_columns(df: pl.DataFrame, float_columns: List[str], int_columns: List[str]) -> pl.DataFrame:
    for col in float_columns:
        if col in df.columns:
            invalid = (
                (~_is_empty_like_expr(col))
                & pl.col(col).cast(pl.Float64, strict=False).is_null()
            )
            bad_count = int(df.select(invalid.sum()).item(0, 0) or 0)
            if bad_count > 0:
                logger.warning("Column %s had %d invalid numeric values", col, bad_count)
            df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False).alias(col))

    for col in int_columns:
        if col in df.columns:
            invalid = (
                (~_is_empty_like_expr(col))
                & pl.col(col).cast(pl.Int64, strict=False).is_null()
            )
            bad_count = int(df.select(invalid.sum()).item(0, 0) or 0)
            if bad_count > 0:
                logger.warning("Column %s had %d invalid integer values", col, bad_count)
            df = df.with_columns(pl.col(col).cast(pl.Int64, strict=False).alias(col))

    return df


def _read_dataset_as_polars(path: Path) -> pl.DataFrame:
    if path.suffix.lower() == ".parquet":
        parquet_files = _resolve_parquet_files(path)
        return pl.read_parquet(parquet_files)
    if path.is_dir():
        parquet_files = _resolve_parquet_files(path)
        return pl.read_parquet(parquet_files)
    return read_csv_arrow(path)


def _build_id_map(metadata_path: Path) -> Dict[str, str]:
    """Builds source_file|test_id -> patient_unique_id map from corrected metadata."""
    df = _read_dataset_as_polars(metadata_path)
    if df.height == 0:
        return {}

    required = {"source_file", "test_id", "patient_unique_id"}
    if not required.issubset(df.columns):
        raise ValueError(f"Metadata file missing required columns: {required}")

    work = df.with_columns(
        [
            pl.concat_str(
                [
                    pl.col("source_file").cast(pl.Utf8, strict=False).fill_null(""),
                    pl.col("test_id").cast(pl.Utf8, strict=False).fill_null(""),
                ],
                separator="|",
            ).alias("__key"),
            pl.col("patient_unique_id")
            .cast(pl.Utf8, strict=False)
            .fill_null("")
            .map_elements(normalize_patient_id, return_dtype=pl.Utf8)
            .alias("__pid"),
        ]
    ).select(["__key", "__pid"])

    data = work.to_dict(as_series=False)
    return dict(zip(data["__key"], data["__pid"]))


def _build_id_map_before_after(before_path: Path, after_path: Path) -> Dict[str, str]:
    """Builds source_file|test_id -> corrected_id map comparing metadata before/after."""
    before_df = _read_dataset_as_polars(before_path)
    after_df = _read_dataset_as_polars(after_path)

    required = {"source_file", "test_id", "patient_unique_id"}
    if not required.issubset(before_df.columns) or not required.issubset(after_df.columns):
        raise ValueError(f"Metadata before/after must contain columns: {required}")

    before_pairs = before_df.with_columns(
        [
            pl.concat_str(
                [
                    pl.col("source_file").cast(pl.Utf8, strict=False).fill_null(""),
                    pl.col("test_id").cast(pl.Utf8, strict=False).fill_null(""),
                ],
                separator="|",
            ).alias("__key"),
            pl.col("patient_unique_id")
            .cast(pl.Utf8, strict=False)
            .fill_null("")
            .map_elements(normalize_patient_id, return_dtype=pl.Utf8)
            .alias("__pid"),
        ]
    ).select(["__key", "__pid"])

    after_pairs = after_df.with_columns(
        [
            pl.concat_str(
                [
                    pl.col("source_file").cast(pl.Utf8, strict=False).fill_null(""),
                    pl.col("test_id").cast(pl.Utf8, strict=False).fill_null(""),
                ],
                separator="|",
            ).alias("__key"),
            pl.col("patient_unique_id")
            .cast(pl.Utf8, strict=False)
            .fill_null("")
            .map_elements(normalize_patient_id, return_dtype=pl.Utf8)
            .alias("__pid"),
        ]
    ).select(["__key", "__pid"])

    after_lookup = dict(zip(after_pairs["__key"].to_list(), after_pairs["__pid"].to_list()))
    id_map: Dict[str, str] = {}
    for key, old_id in zip(before_pairs["__key"].to_list(), before_pairs["__pid"].to_list()):
        new_id = after_lookup.get(key)
        if new_id and new_id != old_id:
            id_map[key] = new_id
    return id_map


def _iter_input_chunks(input_path: Path, chunk_size: int):
    """Iterates CSV or Parquet datasets and yields Polars DataFrames."""
    if input_path.is_dir() or input_path.suffix.lower() == ".parquet":
        dataset = pa_ds.dataset(_resolve_parquet_files(input_path), format="parquet")
        batch_size = max(50000, chunk_size)
        for batch in dataset.to_batches(batch_size=batch_size, use_threads=True):
            yield pl.from_arrow(pa.Table.from_batches([batch]))
        return

    for chunk in iter_csv_arrow(input_path, block_size_mb=max(1, chunk_size // 1000), use_threads=True):
        yield chunk


def _apply_single_input(
    *,
    input_path: Path,
    output_path: Path,
    mapping: Dict[str, str],
    debug_writer: MissingIdCsvWriter,
    column: str,
    drop_columns: Iterable[str],
    chunk_size: int,
    float_columns: List[str],
    int_columns: List[str],
    metadata_id_map: Dict[str, str] | None,
) -> None:
    writer = ParquetChunkWriter(output_path, force_string_schema=False)
    total_rows = 0
    total_missing = 0

    try:
        for chunk in _iter_input_chunks(input_path, chunk_size=chunk_size):
            if column not in chunk.columns:
                raise ValueError(f"Column {column} not found in {input_path}")

            chunk = chunk.with_columns(
                pl.col(column)
                .cast(pl.Utf8, strict=False)
                .fill_null("")
                .map_elements(normalize_patient_id, return_dtype=pl.Utf8)
                .alias(column)
            )

            if metadata_id_map and {"source_file", "test_id"}.issubset(chunk.columns):
                chunk = chunk.with_columns(
                    [
                        pl.concat_str(
                            [
                                pl.col("source_file").cast(pl.Utf8, strict=False).fill_null(""),
                                pl.col("test_id").cast(pl.Utf8, strict=False).fill_null(""),
                            ],
                            separator="|",
                        ).alias("__merge_key")
                    ]
                )
                chunk = chunk.with_columns(
                    pl.col("__merge_key")
                    .map_elements(lambda key: metadata_id_map.get(key), return_dtype=pl.Utf8)
                    .alias("__fixed")
                )
                chunk = chunk.with_columns(
                    pl.when(pl.col("__fixed").is_not_null())
                    .then(pl.col("__fixed"))
                    .otherwise(pl.col(column))
                    .alias(column)
                ).drop(["__merge_key", "__fixed"])

            chunk = chunk.with_columns(
                pl.col(column)
                .map_elements(lambda patient_id: mapping.get(patient_id), return_dtype=pl.Utf8)
                .alias("__mapped")
            )

            missing_df = chunk.filter(pl.col("__mapped").is_null()).select(
                pl.col(column).cast(pl.Utf8, strict=False).alias("patient_unique_id")
            )
            if missing_df.height > 0:
                total_missing += missing_df.height
                missing_rows = [
                    {"source_file": input_path.name, "patient_unique_id": pid}
                    for pid in missing_df["patient_unique_id"].to_list()
                ]
                debug_writer.write_rows(missing_rows)

            chunk = chunk.with_columns(pl.coalesce([pl.col("__mapped"), pl.col(column)]).alias(column)).drop("__mapped")
            chunk = _coerce_numeric_columns(chunk, float_columns=float_columns, int_columns=int_columns)
            chunk = drop_columns_if_present(chunk, drop_columns)

            writer.write(chunk)
            total_rows += chunk.height
    finally:
        writer.close()

    logger.info("Hashed %s -> %s (rows=%d, missing=%d)", input_path.name, output_path.name, total_rows, total_missing)


def run(
    *,
    base: Path,
    inputs: List[str],
    mapping_path: str,
    output_dir: str,
    debug_csv: str,
    column: str,
    drop_columns: List[str],
    chunk_size: int,
    float_columns: List[str] | None = None,
    int_columns: List[str] | None = None,
    metadata_before: str | None = None,
    metadata_after: str | None = None,
    metadata: str | None = None,
    name_suffix: str = "",
) -> None:
    mapping_full = Path(mapping_path)
    if not mapping_full.is_absolute():
        mapping_full = base / mapping_full

    output_dir_path = Path(output_dir)
    if not output_dir_path.is_absolute():
        output_dir_path = base / output_dir_path
    output_dir_path.mkdir(parents=True, exist_ok=True)

    debug_path = Path(debug_csv)
    if not debug_path.is_absolute():
        debug_path = base / debug_path
    debug_path.parent.mkdir(parents=True, exist_ok=True)

    mapping = load_hash_mapping(mapping_full)
    debug_writer = MissingIdCsvWriter(output_path=debug_path)

    float_columns = float_columns or ["voltage_uV", "pupil_mm", "time_ms"]
    int_columns = int_columns or ["test_id"]

    metadata_id_map = None
    if metadata:
        metadata_full = Path(metadata)
        if not metadata_full.is_absolute():
            metadata_full = base / metadata_full
        metadata_id_map = _build_id_map(metadata_full)
    elif metadata_before and metadata_after:
        before_full = Path(metadata_before)
        if not before_full.is_absolute():
            before_full = base / before_full
        after_full = Path(metadata_after)
        if not after_full.is_absolute():
            after_full = base / after_full
        metadata_id_map = _build_id_map_before_after(before_full, after_full)

    for raw_input in inputs:
        input_path = Path(raw_input)
        if not input_path.is_absolute():
            input_path = base / input_path
        if not input_path.exists():
            logger.warning("Input file not found: %s", input_path)
            continue

        output_path = output_dir_path / _output_filename_for_input(input_path, name_suffix=name_suffix)
        _apply_single_input(
            input_path=input_path,
            output_path=output_path,
            mapping=mapping,
            debug_writer=debug_writer,
            column=column,
            drop_columns=drop_columns,
            chunk_size=chunk_size,
            float_columns=float_columns,
            int_columns=int_columns,
            metadata_id_map=metadata_id_map,
        )
