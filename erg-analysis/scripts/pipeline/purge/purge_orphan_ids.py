"""Purge orphan patient IDs from consolidated datasets.

Reads unique_ids_only_one_base_counts.csv produced by audit_unique_patient_ids
and removes every row that references those IDs from the target datasets:
  - output/patients/                  (presence == only_patients)
  - output/waveforms/consolidated/    (presence == only_metadata)

All Spark-style parquet directories (dir ending in .parquet) are rewritten
in-place via a tmp directory swap.  Plain single-file parquets use PyArrow.

A purge audit log CSV is written to --audit-log-output after each run.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.logging_utils import configure_logging
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir


logger = logging.getLogger(__name__)

ID_COL = "patient_unique_id"

PATIENTS_PATTERNS = [
    "patients-*.parquet",
    "patients_id_mapping-*.parquet",
]

WAVEFORMS_PATTERNS = [
    "consolidated_metadata.parquet",
    "consolidated_waveforms.parquet",
]

# Columns carried into the audit log when present in the source dataset.
_AUDIT_CONTEXT_COLS = [
    "nome_paciente",
    "nome_completo",
    "id_prontuario",
    "prontuario",
    "data_nascimento",
    "PatientBirthdate",
    "data_realizada_do_teste",
    "data_teste",
    "TestingDate",
    "test_id",
    "PatientID",
]


class PurgeRecord(NamedTuple):
    patient_unique_id: str
    presence: str
    source_file: str
    rows_removed: int
    context: dict  # extra columns from the removed rows (first occurrence)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _read_audit_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig")


def _ids_for_presence(df: pd.DataFrame, presence: str) -> list[str]:
    mask = df["presence"].str.strip() == presence
    ids = df.loc[mask, ID_COL].dropna().str.strip().tolist()
    return [i for i in ids if i]


def _presence_map(df: pd.DataFrame) -> dict[str, str]:
    return dict(zip(df[ID_COL].str.strip(), df["presence"].str.strip()))


def _find_parquet_targets(root: Path, patterns: list[str]) -> list[Path]:
    targets: list[Path] = []
    for pattern in patterns:
        for match in root.rglob(pattern):
            if match.exists():
                targets.append(match.resolve())
    return sorted(set(targets))


def _is_spark_dir(path: Path) -> bool:
    return path.is_dir()


def _extract_context(row: dict) -> dict:
    return {col: row.get(col, "") for col in _AUDIT_CONTEXT_COLS}


def _write_purge_log(records: list[PurgeRecord], log_path: Path, dry_run: bool) -> None:
    if not records:
        logger.info("No rows removed — purge log not written.")
        return

    context_cols = _AUDIT_CONTEXT_COLS
    fieldnames = [
        "patient_unique_id",
        "presence",
        "source_file",
        "rows_removed",
        "dry_run",
    ] + context_cols

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            row = {
                "patient_unique_id": rec.patient_unique_id,
                "presence": rec.presence,
                "source_file": rec.source_file,
                "rows_removed": rec.rows_removed,
                "dry_run": "yes" if dry_run else "no",
            }
            row.update({col: rec.context.get(col, "") for col in context_cols})
            writer.writerow(row)

    logger.info("Purge audit log written: %s (%d records)", log_path, len(records))


# ---------------------------------------------------------------------------
# PyArrow purge
# ---------------------------------------------------------------------------

def _purge_pyarrow(
    path: Path,
    ids_to_remove: list[str],
    presence_map: dict[str, str],
    dry_run: bool,
) -> list[PurgeRecord]:
    dataset = ds.dataset(str(path), format="parquet")
    schema = dataset.schema

    if ID_COL not in schema.names:
        logger.warning("Column '%s' not found in %s — skipped", ID_COL, path)
        return []

    id_set = set(ids_to_remove)
    before_rows = dataset.count_rows()

    batches_kept: list[pa.RecordBatch] = []
    removed_rows: list[dict] = []

    for batch in dataset.to_batches():
        col = batch.column(ID_COL).to_pylist()
        keep_mask = [v not in id_set for v in col]
        kept = batch.filter(pa.array(keep_mask, type=pa.bool_()))
        batches_kept.append(kept)

        # collect removed rows for audit log
        for i, (pid, keep) in enumerate(zip(col, keep_mask)):
            if not keep:
                row = {name: batch.column(name)[i].as_py() for name in batch.schema.names}
                removed_rows.append(row)

    removed = before_rows - sum(len(b) for b in batches_kept)
    logger.info("%s: %d rows before, removing %d, %d rows after", path.name, before_rows, removed, before_rows - removed)

    if removed == 0:
        return []

    if not dry_run:
        table = pa.Table.from_batches(batches_kept, schema=schema)
        if _is_spark_dir(path):
            tmp_dir = path.parent / (path.name + ".purge_tmp")
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)
            pq.write_to_dataset(table, root_path=str(tmp_dir), use_legacy_dataset=False)
            shutil.rmtree(path)
            tmp_dir.rename(path)
        else:
            tmp_file = path.with_suffix(".purge_tmp.parquet")
            pq.write_table(table, str(tmp_file))
            path.unlink()
            tmp_file.rename(path)

    # build one PurgeRecord per unique ID found in removed rows
    by_id: dict[str, list[dict]] = {}
    for row in removed_rows:
        pid = str(row.get(ID_COL, "")).strip()
        by_id.setdefault(pid, []).append(row)

    records: list[PurgeRecord] = []
    for pid, rows in by_id.items():
        records.append(PurgeRecord(
            patient_unique_id=pid,
            presence=presence_map.get(pid, ""),
            source_file=str(path),
            rows_removed=len(rows),
            context=_extract_context(rows[0]),
        ))
    return records


# ---------------------------------------------------------------------------
# Spark purge
# ---------------------------------------------------------------------------

def _build_spark(workers: int | None):
    try:
        from pyspark.sql import SparkSession
    except Exception as exc:
        raise RuntimeError("PySpark is required. Install pyspark and retry.") from exc

    builder = SparkSession.builder.appName("erg-purge-orphan-ids")
    if workers and workers > 0:
        builder = builder.master(f"local[{workers}]")
        shuffle_parts = max(2, workers * 2)
    else:
        builder = builder.master("local[*]")
        shuffle_parts = max(8, os.cpu_count() or 4)

    return (
        builder
        .config("spark.sql.shuffle.partitions", str(shuffle_parts))
        .config("spark.default.parallelism", str(shuffle_parts))
        .getOrCreate()
    )


def _purge_spark(
    path: Path,
    ids_to_remove: list[str],
    presence_map: dict[str, str],
    spark,
    dry_run: bool,
) -> list[PurgeRecord]:
    from pyspark.sql.functions import col as spark_col

    df = spark.read.parquet(str(path))

    if ID_COL not in df.columns:
        logger.warning("Column '%s' not found in %s — skipped", ID_COL, path)
        return []

    before = df.count()
    removed_df = df.filter(spark_col(ID_COL).isin(ids_to_remove))
    df_clean = df.filter(~spark_col(ID_COL).isin(ids_to_remove))
    after = df_clean.count()
    removed = before - after

    logger.info("%s: %d rows before, removing %d, %d rows after", path.name, before, removed, after)

    if removed == 0:
        return []

    # collect audit context — only context cols + ID to keep it light
    audit_cols = [ID_COL] + [c for c in _AUDIT_CONTEXT_COLS if c in df.columns]
    removed_rows = removed_df.select(audit_cols).limit(10000).toPandas().to_dict("records")

    if not dry_run:
        tmp_dir = path.parent / (path.name + ".purge_tmp")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        df_clean.write.mode("overwrite").parquet(str(tmp_dir))
        shutil.rmtree(path)
        tmp_dir.rename(path)

    by_id: dict[str, list[dict]] = {}
    for row in removed_rows:
        pid = str(row.get(ID_COL, "")).strip()
        by_id.setdefault(pid, []).append(row)

    records: list[PurgeRecord] = []
    for pid, rows in by_id.items():
        records.append(PurgeRecord(
            patient_unique_id=pid,
            presence=presence_map.get(pid, ""),
            source_file=str(path),
            rows_removed=len(rows),
            context=_extract_context(rows[0]),
        ))
    return records


# ---------------------------------------------------------------------------
# main run
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> None:
    base_dir = resolve_base_dir(args.base)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    audit_path = resolve_input_path(base_dir, args.audit_input, must_exist=True)
    patients_root = resolve_input_path(base_dir, args.patients_root, must_exist=False)
    waveforms_root = resolve_input_path(base_dir, args.waveforms_root, must_exist=False)

    log_rel = args.audit_log_output or "output/reports/id_audit"
    log_dir = resolve_output_dir(base_dir, log_rel, create=True)
    log_path = log_dir / f"purge_log_{run_tag}.csv"

    audit_df = _read_audit_csv(audit_path)
    logger.info("Loaded audit file: %s (%d rows)", audit_path, len(audit_df))

    only_patients_ids = _ids_for_presence(audit_df, "only_patients")
    only_metadata_ids = _ids_for_presence(audit_df, "only_metadata")
    presence_map = _presence_map(audit_df)

    logger.info(
        "IDs to purge: only_patients=%d  only_metadata=%d",
        len(only_patients_ids),
        len(only_metadata_ids),
    )

    if not only_patients_ids and not only_metadata_ids:
        logger.info("No orphan IDs found — nothing to purge.")
        return

    use_spark = not args.no_spark
    spark = _build_spark(args.workers) if use_spark else None

    all_records: list[PurgeRecord] = []

    if only_patients_ids and patients_root.exists():
        targets = _find_parquet_targets(patients_root, PATIENTS_PATTERNS)
        if not targets:
            logger.warning("No patient parquet files found under %s", patients_root)
        for target in targets:
            logger.info("Purging only_patients IDs from %s", target)
            if use_spark:
                records = _purge_spark(target, only_patients_ids, presence_map, spark, args.dry_run)
            else:
                records = _purge_pyarrow(target, only_patients_ids, presence_map, args.dry_run)
            all_records.extend(records)
    elif only_patients_ids:
        logger.warning("patients_root does not exist: %s", patients_root)

    if only_metadata_ids and waveforms_root.exists():
        targets = _find_parquet_targets(waveforms_root, WAVEFORMS_PATTERNS)
        if not targets:
            logger.warning("No waveform parquet files found under %s", waveforms_root)
        for target in targets:
            logger.info("Purging only_metadata IDs from %s", target)
            if use_spark:
                records = _purge_spark(target, only_metadata_ids, presence_map, spark, args.dry_run)
            else:
                records = _purge_pyarrow(target, only_metadata_ids, presence_map, args.dry_run)
            all_records.extend(records)
    elif only_metadata_ids:
        logger.warning("waveforms_root does not exist: %s", waveforms_root)

    if spark:
        spark.stop()

    _write_purge_log(all_records, log_path, args.dry_run)

    total_removed = sum(r.rows_removed for r in all_records)
    if args.dry_run:
        logger.info("PURGE [dry-run] complete — %d rows would be removed", total_removed)
    else:
        logger.info("PURGE complete — %d rows removed across all targets", total_removed)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Remove orphan patient IDs from consolidated datasets. "
            "Reads unique_ids_only_one_base_counts.csv and drops matching rows "
            "from patients/ and waveforms/consolidated/ parquet files. "
            "Writes a purge audit log CSV after each run."
        )
    )
    parser.add_argument("--base", default=".", help="Base directory")
    parser.add_argument(
        "--audit-input",
        default="output/reports/id_audit/unique_ids_only_one_base_counts.csv",
        help="Path to unique_ids_only_one_base_counts.csv",
    )
    parser.add_argument(
        "--patients-root",
        default="output/patients",
        help="Root directory containing patients parquet files",
    )
    parser.add_argument(
        "--waveforms-root",
        default="output/waveforms/consolidated",
        help="Root directory containing consolidated_metadata and consolidated_waveforms parquet files",
    )
    parser.add_argument(
        "--audit-log-output",
        default=None,
        help="Directory for purge audit log CSV (default: output/reports/id_audit)",
    )
    parser.add_argument("--workers", type=int, default=None, help="Spark local workers")
    parser.add_argument(
        "--no-spark",
        action="store_true",
        help="Use PyArrow instead of Spark (suitable for smaller datasets)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be removed without writing any files",
    )
    return parser
